/**
 * dcp_mailbox_client.pseudo.c — Clean-Room Apple Display Coprocessor (DCP) Client
 * Architecture: Apple Silicon A19 Pro (t8150) / iOS 27.2 (24B119)
 *
 * Implements low-level ASCwrap-v6 mailbox interaction, frame swap queuing,
 * ProMotion dynamic refresh rate configuration, and Always-On Display handoff.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

/* ASCwrap-v6 Hardware MMIO Offsets (A19 Pro DCP) */
#define DCP_ASC_BASE_PADDR               0x0000000100600000ULL
#define DCP_REG_INBOX_DATA               0x0000
#define DCP_REG_INBOX_STATUS             0x0008
#define DCP_REG_DOORBELL_AP_TO_DCP       0x0040
#define DCP_REG_OUTBOX_DATA              0x0100
#define DCP_REG_OUTBOX_STATUS            0x0108
#define DCP_REG_DOORBELL_DCP_TO_AP       0x0140
#define DCP_REG_INTERRUPT_ENABLE         0x0200

/* FIFO Status Bitmasks */
#define ASC_STATUS_COUNT_MASK            0x0000007FU
#define ASC_STATUS_FULL_BIT              (1U << 16)
#define ASC_STATUS_EMPTY_BIT             (1U << 17)

/* DCP AFK Endpoints */
typedef enum {
    DCP_EP_FRAME_MANAGEMENT              = 0x01,
    DCP_EP_AOP_FLIPBOOK                  = 0x02,
    DCP_EP_EXCLAVE_BRIDGE                = 0x03,
    DCP_EP_TRUSTED_SECURITY              = 0x04
} dcp_endpoint_t;

/* DCP Core Command Opcodes */
typedef enum {
    DCP_CMD_SUBMIT_FRAME_SWAP            = 0x0101,
    DCP_CMD_SET_REFRESH_RATE_POLICY      = 0x0102,
    DCP_CMD_UPDATE_CALIBRATION_LUT       = 0x0103,
    DCP_CMD_ENTER_AOD_MODE               = 0x0104,
    DCP_CMD_GET_TELEMETRY_STATS          = 0x0105
} dcp_opcode_t;

/* Return Status Codes */
typedef enum {
    DCP_SUCCESS                          = 0x0000,
    DCP_ERR_INVALID_ARGUMENT             = 0x0001,
    DCP_ERR_FIFO_TIMEOUT                 = 0x0002,
    DCP_ERR_FRAME_LATE                   = 0x0003,
    DCP_ERR_DART_FAULT                   = 0x0004,
    DCP_ERR_INTERNAL_FAULT               = 0x0005
} dcp_status_t;

/* 64-Bit Message Header (Aligned with ASCwrap-v6 framing) */
typedef union {
    uint64_t raw;
    struct {
        uint64_t length_words   : 8;   /* Total packet 64-bit words (1..64) */
        uint64_t endpoint_id    : 8;   /* Target service endpoint */
        uint64_t sequence_tag   : 16;  /* Asynchronous correlation tag */
        uint64_t command_opcode : 16;  /* Service operation code */
        uint64_t flags          : 16;  /* Control flags */
    } bits;
} dcp_msg_header_t;

/* 64-Word Maximum Hardware FIFO Packet */
typedef struct {
    dcp_msg_header_t header;
    uint64_t         payload[63];
} dcp_packet_t;

/* Surface Swap Presentation Descriptor */
typedef struct {
    uint64_t frame_dva;           /* DART-DISP0 Device Virtual Address */
    uint32_t width;               /* 2868 */
    uint32_t height;              /* 1320 */
    uint32_t stride_bytes;        /* Pitch (e.g. 2868 * 4 = 11472) */
    uint32_t pixel_format;        /* RGBA 10-bit or BGRA 8-bit */
    uint32_t target_refresh_hz;   /* Desired refresh rate (10..120) */
    uint64_t vsync_deadline_ns;   /* Host presentation timestamp */
} dcp_swap_descriptor_t;

/* Client Hardware Context */
typedef struct {
    volatile uint8_t *mmio_base;
    uint32_t          next_sequence_tag;
    bool              initialized;
} dcp_client_t;

/* Hardware MMIO Helper Inlines */
static inline uint32_t dcp_read32(volatile uint8_t *base, uint32_t offset) {
    return *(volatile uint32_t *)(base + offset);
}

static inline void dcp_write32(volatile uint8_t *base, uint32_t offset, uint32_t val) {
    *(volatile uint32_t *)(base + offset) = val;
}

static inline uint64_t dcp_read64(volatile uint8_t *base, uint32_t offset) {
    return *(volatile uint64_t *)(base + offset);
}

static inline void dcp_write64(volatile uint8_t *base, uint32_t offset, uint64_t val) {
    *(volatile uint64_t *)(base + offset) = val;
}

/**
 * dcp_client_init: Sets up memory-mapped base address and enables interrupts.
 */
int dcp_client_init(dcp_client_t *client, void *mapped_mmio_vaddr) {
    if (!client || !mapped_mmio_vaddr) return -1;
    client->mmio_base = (volatile uint8_t *)mapped_mmio_vaddr;
    client->next_sequence_tag = 1;
    client->initialized = true;

    /* Enable Inbox and Outbox interrupts */
    dcp_write32(client->mmio_base, DCP_REG_INTERRUPT_ENABLE, 0x03);
    return 0;
}

/**
 * dcp_send_packet: Posts a framed packet into the ASCwrap inbox FIFO.
 */
dcp_status_t dcp_send_packet(dcp_client_t *client, const dcp_packet_t *pkt) {
    if (!client || !client->initialized || !pkt) return DCP_ERR_INVALID_ARGUMENT;

    uint32_t length_words = pkt->header.bits.length_words;
    if (length_words == 0 || length_words > 64) return DCP_ERR_INVALID_ARGUMENT;

    /* Spin-wait until inbox FIFO has sufficient free slots */
    uint32_t attempts = 1000000;
    while (attempts--) {
        uint32_t status = dcp_read32(client->mmio_base, DCP_REG_INBOX_STATUS);
        if (!(status & ASC_STATUS_FULL_BIT)) {
            uint32_t free_words = status & ASC_STATUS_COUNT_MASK;
            if (free_words >= length_words) {
                break;
            }
        }
    }
    if (attempts == 0) return DCP_ERR_FIFO_TIMEOUT;

    /* Write Header Word */
    dcp_write64(client->mmio_base, DCP_REG_INBOX_DATA, pkt->header.raw);

    /* Write Subsequent Payload Words */
    for (uint32_t i = 1; i < length_words; i++) {
        dcp_write64(client->mmio_base, DCP_REG_INBOX_DATA, pkt->payload[i - 1]);
    }

    /* Memory Barrier: Ensure all FIFO writes commit prior to doorbell */
#if defined(__arm64__) || defined(__aarch64__)
    __asm__ volatile("dmb oshst" ::: "memory");
#endif

    /* Assert Doorbell to wake DCP core */
    dcp_write32(client->mmio_base, DCP_REG_DOORBELL_AP_TO_DCP, 0x1);

    return DCP_SUCCESS;
}

/**
 * dcp_recv_packet: Reads a framed response packet from the ASCwrap outbox FIFO.
 */
dcp_status_t dcp_recv_packet(dcp_client_t *client, dcp_packet_t *resp) {
    if (!client || !client->initialized || !resp) return DCP_ERR_INVALID_ARGUMENT;

    /* Spin-wait until outbox contains at least 1 word */
    uint32_t attempts = 1000000;
    while (attempts--) {
        uint32_t status = dcp_read32(client->mmio_base, DCP_REG_OUTBOX_STATUS);
        if (!(status & ASC_STATUS_EMPTY_BIT)) {
            break;
        }
    }
    if (attempts == 0) return DCP_ERR_FIFO_TIMEOUT;

    /* Read Header Word */
    resp->header.raw = dcp_read64(client->mmio_base, DCP_REG_OUTBOX_DATA);
    uint32_t length_words = resp->header.bits.length_words;

    if (length_words == 0 || length_words > 64) return DCP_ERR_INTERNAL_FAULT;

    /* Read Remaining Payload Words */
    for (uint32_t i = 1; i < length_words; i++) {
        resp->payload[i - 1] = dcp_read64(client->mmio_base, DCP_REG_OUTBOX_DATA);
    }

    /* Acknowledge doorbell interrupt */
    dcp_write32(client->mmio_base, DCP_REG_DOORBELL_DCP_TO_AP, 0x1);

    return DCP_SUCCESS;
}

/**
 * dcp_submit_surface_swap: Submits a new frame to GenPipe_v33 for scanout.
 */
dcp_status_t dcp_submit_surface_swap(
    dcp_client_t *client,
    const dcp_swap_descriptor_t *swap
) {
    if (!client || !swap) return DCP_ERR_INVALID_ARGUMENT;

    dcp_packet_t pkt;
    memset(&pkt, 0, sizeof(pkt));

    uint16_t seq = (uint16_t)__atomic_fetch_add(&client->next_sequence_tag, 1, __ATOMIC_RELAXED);

    pkt.header.bits.length_words = 6; /* Header + 5 payload words */
    pkt.header.bits.endpoint_id = DCP_EP_FRAME_MANAGEMENT;
    pkt.header.bits.sequence_tag = seq;
    pkt.header.bits.command_opcode = DCP_CMD_SUBMIT_FRAME_SWAP;
    pkt.header.bits.flags = 0x01; /* Reply expected */

    /* Safe copy of swap descriptor */
    memcpy(&pkt.payload[0], swap, sizeof(dcp_swap_descriptor_t));

    dcp_status_t status = dcp_send_packet(client, &pkt);
    if (status != DCP_SUCCESS) return status;

    dcp_packet_t resp;
    status = dcp_recv_packet(client, &resp);
    if (status != DCP_SUCCESS) return status;

    return (dcp_status_t)resp.payload[0];
}

/**
 * dcp_set_promotion_rate: Programs the target ProMotion refresh rate (10Hz to 120Hz).
 */
dcp_status_t dcp_set_promotion_rate(dcp_client_t *client, uint32_t target_hz) {
    if (!client || (target_hz < 10 && target_hz != 1) || target_hz > 120) {
        return DCP_ERR_INVALID_ARGUMENT;
    }

    dcp_packet_t pkt;
    memset(&pkt, 0, sizeof(pkt));

    uint16_t seq = (uint16_t)__atomic_fetch_add(&client->next_sequence_tag, 1, __ATOMIC_RELAXED);

    pkt.header.bits.length_words = 2; /* Header + 1 payload word */
    pkt.header.bits.endpoint_id = DCP_EP_FRAME_MANAGEMENT;
    pkt.header.bits.sequence_tag = seq;
    pkt.header.bits.command_opcode = DCP_CMD_SET_REFRESH_RATE_POLICY;
    pkt.header.bits.flags = 0x01;
    pkt.payload[0] = (uint64_t)target_hz;

    dcp_status_t status = dcp_send_packet(client, &pkt);
    if (status != DCP_SUCCESS) return status;

    dcp_packet_t resp;
    status = dcp_recv_packet(client, &resp);
    if (status != DCP_SUCCESS) return status;

    return (dcp_status_t)resp.payload[0];
}
