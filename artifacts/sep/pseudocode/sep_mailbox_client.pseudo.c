/**
 * sep_mailbox_client.pseudo.c — Clean-Room Apple ASCwrap-v6 Mailbox Client Runtime
 * Target Architecture: Apple Silicon A19 Pro (t8150) / iOS 27.2 (24B119)
 *
 * Implements low-level register interaction, packet framing, and cryptographic
 * command dispatch across the ASCwrap-v6 hardware mailbox boundary.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ASCwrap-v6 MMIO Base & Register Offsets */
#define ASC_MAILBOX_BASE_PADDR           0x0000000072600000ULL
#define ASC_REG_INBOX_DATA               0x0000
#define ASC_REG_INBOX_STATUS             0x0008
#define ASC_REG_DOORBELL_AP_TO_SEP       0x0040
#define ASC_REG_OUTBOX_DATA              0x0100
#define ASC_REG_OUTBOX_STATUS            0x0108
#define ASC_REG_DOORBELL_SEP_TO_AP       0x0140
#define ASC_REG_INTERRUPT_ENABLE         0x0200

/* Status Register Bitmasks */
#define ASC_STATUS_COUNT_MASK            0x0000007FU
#define ASC_STATUS_FULL_BIT              (1U << 16)
#define ASC_STATUS_EMPTY_BIT             (1U << 17)

/* Service Endpoints */
typedef enum {
    SEP_EP_CONTROL                       = 0x01,
    SEP_EP_KEYSTORE                      = 0x02,
    SEP_EP_BIOMETRIC                     = 0x03,
    SEP_EP_STORAGE                       = 0x04,
    SEP_EP_SECURE_ELEMENT                = 0x05,
    SEP_EP_CREDENTIAL                    = 0x06,
    SEP_EP_ENTROPY                       = 0x07,
    SEP_EP_EXCLAVE_BRIDGE                = 0x08
} sep_endpoint_t;

/* Core Command Opcodes */
typedef enum {
    CMSG_LOAD_KEYBAG                     = 0x0201,
    CMSG_SAVE_KEYBAG                     = 0x0202,
    CMSG_UNWRAP_KEY                      = 0x0203,
    CMSG_WRAP_KEY                        = 0x0204,
    CMSG_DROP_CLASS_KEYS                 = 0x0205,
    CMSG_VERIFY_PASSCODE                 = 0x0206,
    CMSG_GET_ENTROPY_FOR_XNU_PRNG        = 0x0701,
    CMSG_ART_LOAD_TOKENS                 = 0x0401,
    CMSG_ART_COMMIT_TOKENS               = 0x0402
} sep_opcode_t;

/* Status / Return Codes */
typedef enum {
    SEP_SUCCESS                          = 0x0000,
    SEP_ERR_INVALID_ARGUMENT             = 0x0001,
    SEP_ERR_BUFFER_TOO_SMALL             = 0x0002,
    SEP_ERR_KEY_NOT_FOUND                = 0x0003,
    SEP_ERR_CLASS_LOCKED                 = 0x0004,
    SEP_ERR_PASSCODE_BACKOFF             = 0x0005,
    SEP_ERR_FIFO_TIMEOUT                 = 0x0006,
    SEP_ERR_INTERNAL_FAULT               = 0x0007
} sep_status_t;

/* Message Control Flags */
#define SEP_FLAG_OOL_PAYLOAD             (1U << 0)
#define SEP_FLAG_REPLY_EXPECTED          (1U << 1)
#define SEP_FLAG_HIGH_PRIORITY           (1U << 2)

/* 64-Bit Primary Message Header */
typedef union {
    uint64_t raw;
    struct {
        uint64_t length_words   : 8;   /* Bits 0..7   : Total packet words (1..64) */
        uint64_t endpoint_id    : 8;   /* Bits 8..15  : Target service endpoint */
        uint64_t sequence_tag   : 16;  /* Bits 16..31 : Asynchronous correlation tag */
        uint64_t command_opcode : 16;  /* Bits 32..47 : Service operation code */
        uint64_t flags          : 16;  /* Bits 48..63 : Message control flags */
    } bits;
} sep_msg_header_t;

/* Maximum FIFO Packet (64 words / 512 bytes) */
typedef struct {
    sep_msg_header_t header;
    uint64_t         payload[63];
} sep_packet_t;

/* Hardware MMIO Context */
typedef struct {
    volatile uint8_t *mmio_base;
    uint16_t          next_sequence_tag;
} sep_mailbox_context_t;

/* Memory-Mapped I/O Helper Functions */
static inline uint32_t mmio_read32(volatile uint8_t *base, uint32_t offset) {
    return *(volatile uint32_t *)(base + offset);
}

static inline void mmio_write32(volatile uint8_t *base, uint32_t offset, uint32_t val) {
    *(volatile uint32_t *)(base + offset) = val;
}

static inline uint64_t mmio_read64(volatile uint8_t *base, uint32_t offset) {
    return *(volatile uint64_t *)(base + offset);
}

static inline void mmio_write64(volatile uint8_t *base, uint32_t offset, uint64_t val) {
    *(volatile uint64_t *)(base + offset) = val;
}

/**
 * sep_init_mailbox: Initializes local mailbox context pointer.
 */
int sep_init_mailbox(sep_mailbox_context_t *ctx, void *mapped_mmio_vaddr) {
    if (!ctx || !mapped_mmio_vaddr) return -1;
    ctx->mmio_base = (volatile uint8_t *)mapped_mmio_vaddr;
    ctx->next_sequence_tag = 1;
    return 0;
}

/**
 * sep_send_packet: Writes a framed packet into the ASCwrap inbox FIFO.
 */
sep_status_t sep_send_packet(sep_mailbox_context_t *ctx, const sep_packet_t *pkt) {
    if (!ctx || !pkt) return SEP_ERR_INVALID_ARGUMENT;

    uint32_t length_words = pkt->header.bits.length_words;
    if (length_words == 0 || length_words > 64) return SEP_ERR_INVALID_ARGUMENT;

    /* Spin-wait until inbox FIFO has sufficient free slots */
    uint32_t attempts = 1000000;
    while (attempts--) {
        uint32_t status = mmio_read32(ctx->mmio_base, ASC_REG_INBOX_STATUS);
        if (!(status & ASC_STATUS_FULL_BIT)) {
            uint32_t free_words = status & ASC_STATUS_COUNT_MASK;
            if (free_words >= length_words) {
                break;
            }
        }
    }
    if (attempts == 0) return SEP_ERR_FIFO_TIMEOUT;

    /* Write Header Word */
    mmio_write64(ctx->mmio_base, ASC_REG_INBOX_DATA, pkt->header.raw);

    /* Write Subsequent Payload Words */
    for (uint32_t i = 1; i < length_words; i++) {
        mmio_write64(ctx->mmio_base, ASC_REG_INBOX_DATA, pkt->payload[i - 1]);
    }

    /* Assert Doorbell to trigger SEP interrupt */
    mmio_write32(ctx->mmio_base, ASC_REG_DOORBELL_AP_TO_SEP, 0x1);

    return SEP_SUCCESS;
}

/**
 * sep_recv_packet: Reads a framed response packet from the ASCwrap outbox FIFO.
 */
sep_status_t sep_recv_packet(sep_mailbox_context_t *ctx, sep_packet_t *resp) {
    if (!ctx || !resp) return SEP_ERR_INVALID_ARGUMENT;

    /* Spin-wait until outbox contains at least 1 word */
    uint32_t attempts = 1000000;
    while (attempts--) {
        uint32_t status = mmio_read32(ctx->mmio_base, ASC_REG_OUTBOX_STATUS);
        if (!(status & ASC_STATUS_EMPTY_BIT)) {
            break;
        }
    }
    if (attempts == 0) return SEP_ERR_FIFO_TIMEOUT;

    /* Read Header Word */
    resp->header.raw = mmio_read64(ctx->mmio_base, ASC_REG_OUTBOX_DATA);
    uint32_t length_words = resp->header.bits.length_words;

    if (length_words == 0 || length_words > 64) return SEP_ERR_INTERNAL_FAULT;

    /* Read Remaining Payload Words */
    for (uint32_t i = 1; i < length_words; i++) {
        resp->payload[i - 1] = mmio_read64(ctx->mmio_base, ASC_REG_OUTBOX_DATA);
    }

    /* Acknowledge / clear doorbell */
    mmio_write32(ctx->mmio_base, ASC_REG_DOORBELL_SEP_TO_AP, 0x1);

    return SEP_SUCCESS;
}

/**
 * sep_unwrap_key: Requests sepOS KeyStoreServer to unwrap a per-file media key.
 */
sep_status_t sep_unwrap_key(
    sep_mailbox_context_t *ctx,
    uint32_t protection_class,
    const uint8_t wrapped_key_in[40],
    uint8_t unwrapped_key_out[32]
) {
    if (!ctx || !wrapped_key_in || !unwrapped_key_out) return SEP_ERR_INVALID_ARGUMENT;

    sep_packet_t req;
    req.header.raw = 0;
    req.header.bits.length_words = 7;
    req.header.bits.endpoint_id = SEP_EP_KEYSTORE;
    req.header.bits.sequence_tag = ctx->next_sequence_tag++;
    req.header.bits.command_opcode = CMSG_UNWRAP_KEY;
    req.header.bits.flags = SEP_FLAG_REPLY_EXPECTED;

    req.payload[0] = (uint64_t)protection_class;
    /* Copy 40-byte wrapped key into words 1..5 */
    const uint64_t *wrapped_words = (const uint64_t *)wrapped_key_in;
    for (int i = 0; i < 5; i++) {
        req.payload[1 + i] = wrapped_words[i];
    }

    sep_status_t status = sep_send_packet(ctx, &req);
    if (status != SEP_SUCCESS) return status;

    sep_packet_t resp;
    status = sep_recv_packet(ctx, &resp);
    if (status != SEP_SUCCESS) return status;

    /* Verify response status code in payload[0] */
    uint32_t result_code = (uint32_t)resp.payload[0];
    if (result_code != 0) return (sep_status_t)result_code;

    /* Extract 32-byte unwrapped key from words 1..4 */
    uint64_t *out_words = (uint64_t *)unwrapped_key_out;
    for (int i = 0; i < 4; i++) {
        out_words[i] = resp.payload[1 + i];
    }

    return SEP_SUCCESS;
}

/**
 * sep_drop_class_keys: Evicts Class A keys immediately upon device lock.
 */
sep_status_t sep_drop_class_keys(sep_mailbox_context_t *ctx) {
    if (!ctx) return SEP_ERR_INVALID_ARGUMENT;

    sep_packet_t req;
    req.header.raw = 0;
    req.header.bits.length_words = 2;
    req.header.bits.endpoint_id = SEP_EP_KEYSTORE;
    req.header.bits.sequence_tag = ctx->next_sequence_tag++;
    req.header.bits.command_opcode = CMSG_DROP_CLASS_KEYS;
    req.header.bits.flags = SEP_FLAG_REPLY_EXPECTED;
    req.payload[0] = 1; /* Class A identifier */

    sep_status_t status = sep_send_packet(ctx, &req);
    if (status != SEP_SUCCESS) return status;

    sep_packet_t resp;
    status = sep_recv_packet(ctx, &resp);
    if (status != SEP_SUCCESS) return status;

    return (sep_status_t)resp.payload[0];
}

/**
 * sep_get_entropy: Requests 64 true random bytes from SEP TRNG.
 */
sep_status_t sep_get_entropy(sep_mailbox_context_t *ctx, uint8_t entropy_out[64]) {
    if (!ctx || !entropy_out) return SEP_ERR_INVALID_ARGUMENT;

    sep_packet_t req;
    req.header.raw = 0;
    req.header.bits.length_words = 2;
    req.header.bits.endpoint_id = SEP_EP_ENTROPY;
    req.header.bits.sequence_tag = ctx->next_sequence_tag++;
    req.header.bits.command_opcode = CMSG_GET_ENTROPY_FOR_XNU_PRNG;
    req.header.bits.flags = SEP_FLAG_REPLY_EXPECTED;
    req.payload[0] = 64; /* Requested byte count */

    sep_status_t status = sep_send_packet(ctx, &req);
    if (status != SEP_SUCCESS) return status;

    sep_packet_t resp;
    status = sep_recv_packet(ctx, &resp);
    if (status != SEP_SUCCESS) return status;

    uint32_t result_code = (uint32_t)resp.payload[0];
    if (result_code != 0) return (sep_status_t)result_code;

    /* Copy 64 bytes (8 words) from response payload[1..8] */
    uint64_t *out_words = (uint64_t *)entropy_out;
    for (int i = 0; i < 8; i++) {
        out_words[i] = resp.payload[1 + i];
    }

    return SEP_SUCCESS;
}
