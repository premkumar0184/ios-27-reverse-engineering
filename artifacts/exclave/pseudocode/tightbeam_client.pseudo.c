/**
 * tightbeam_client.pseudo.c — Clean-Room Standalone C Client Runtime
 * iOS 27.2 (Darwin 24.2.0, Build 24B119) — Apple Silicon A19 Pro (t8150)
 *
 * Demonstrates:
 * 1. cL4 microkernel system call invocation via ARM64 immediate traps (svc #0).
 * 2. Tightbeam binary message construction (struct tb_message_s, 88-byte header).
 * 3. Positional parameter serialization with hardware alignment constraints.
 * 4. cL4 inline register transport IPC dispatch and server reply unpacking.
 *
 * Designed for clean-room implementation of ExclaveOS Conclave clients.
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ========================================================================= */
/* cL4 Microkernel Constants & ABI                                           */
/* ========================================================================= */

#define L4_SUCCESS                          0
#define L4_ERROR_PREEMPTED                  1
#define L4_ERROR_CANCELED                   2
#define L4_ERROR_TRUNCATED                  3
#define L4_ERROR_CAP_INVALID                4
#define L4_ERROR_SLOT_INVALID               5
#define L4_ERROR_METHOD_INVALID             6
#define L4_ERROR_ARGUMENT_INVALID           7
#define L4_ERROR_OPERATION_INVALID          8
#define L4_ERROR_PERMISSION_INVALID         9

#define L4_NIL                              0x0000000000000000ULL

/* Capability Rights Bitmask */
#define L4_CAN_READ                         (1ULL << 0) /* 0x01: Send / Read    */
#define L4_CAN_WRITE                        (1ULL << 1) /* 0x02: Receive / Write */
#define L4_CAN_GRANT                        (1ULL << 2) /* 0x04: Delegate Cap   */
#define L4_CAN_GRANT_REPLY                  (1ULL << 3) /* 0x08: Pass Reply Cap */
#define L4_CAN_BADGE                        (1ULL << 4) /* 0x10: Mint Badge     */

/* IPC Buffer Limits */
#define L4_IPC_BUFFER_MAX_MRS               32
#define L4_IPC_BUFFER_MAX_CRS               8
#define TB_MAX_CAPS                         8

typedef uint64_t L4_Cap_t;
typedef uint64_t L4_Word_t;

/* cL4 Message Tag Bitfield */
typedef union {
    uint64_t raw;
    struct {
        uint64_t mrs_count       : 6;   /* Bits 0..5:  Message Register count (0..32) */
        uint64_t crs_count       : 4;   /* Bits 6..9:  Capability Register count (0..8) */
        uint64_t flags           : 6;   /* Bits 10..15: Transfer flags                */
        uint64_t protocol_label  : 48;  /* Bits 16..63: RPC Interface / Method Token  */
    };
} L4_MsgTag_t;

/* Per-thread IPC Buffer located at register tpidrro_el0 */
typedef struct {
    L4_MsgTag_t tag;                             /* +0x00: Message descriptor tag     */
    uint64_t    mr[L4_IPC_BUFFER_MAX_MRS];       /* +0x08: Message registers (MR0..31) */
    L4_Cap_t    cr[L4_IPC_BUFFER_MAX_CRS];       /* +0x108: Capability registers (0..7)*/
} __attribute__((aligned(16))) L4_IpcBuffer_t;

/* ========================================================================= */
/* Tightbeam Binary Wire Protocol Structures                                 */
/* ========================================================================= */

#define TB_MESSAGE_STATE_UNINITIALIZED      0
#define TB_MESSAGE_STATE_PREPARING          1
#define TB_MESSAGE_STATE_READY              2
#define TB_MESSAGE_STATE_SENT               3
#define TB_MESSAGE_STATE_RECEIVED           4

#define TB_MESSAGE_DISPOSITION_QUERY        1
#define TB_MESSAGE_DISPOSITION_REPLY        2
#define TB_MESSAGE_DISPOSITION_ERROR        3
#define TB_MESSAGE_DISPOSITION_INIT_ARGS    4

/* Unforgeable Client Badge */
typedef struct {
    uint16_t client_id;
    uint16_t isolation_domain;
    uint32_t session_nonce;
} TightbeamBadge_t;

/* 88-byte Message Header: ^{tb_message_s=ICQQQQ[4Q]Q^{tb_transport_message_buffer_s}} */
typedef struct tb_message_s {
    uint32_t state_and_flags;                    /* +0x00: Lifecycle state and flags  */
    uint8_t  disposition;                        /* +0x04: Query/Reply/Error/Init     */
    uint8_t  reserved_padding[3];                /* +0x05: Alignment padding          */
    uint64_t invocation_id;                      /* +0x08: Monotonic correlation ID   */
    uint64_t endpoint_token;                     /* +0x10: Target method selector ID  */
    uint64_t payload_length;                     /* +0x18: Payload byte count         */
    uint64_t capabilities_count;                 /* +0x20: Delegated caps count       */
    uint64_t inline_payload[4];                  /* +0x28: Inline payload words       */
    uint64_t cursor_position;                    /* +0x48: Read/write cursor          */
    void    *transport_buffer;                   /* +0x50: Pointer to extended buffer */
} __attribute__((packed)) tb_message_t;

/* ========================================================================= */
/* ARM64 Low-Level Trap Wrappers                                             */
/* ========================================================================= */

/**
 * Reads the per-thread IPC buffer virtual base address from tpidrro_el0.
 */
static inline L4_IpcBuffer_t *tb_get_ipc_buffer(void) {
    L4_IpcBuffer_t *ipcb;
    __asm__ volatile("mrs %0, tpidrro_el0" : "=r"(ipcb));
    return ipcb;
}

/**
 * Executes a cL4 synchronous IPC call via svc #0.
 * In:  x0 = target_cap, x1 = msg_tag, x2 = badge_arg
 * Out: x0 = error_code, x2 = reply_tag
 */
static inline uint64_t cl4_ipc_call(L4_Cap_t target_cap, L4_MsgTag_t tag, uint64_t badge_arg, L4_MsgTag_t *out_tag) {
    register uint64_t r0 __asm__("x0") = target_cap;
    register uint64_t r1 __asm__("x1") = tag.raw;
    register uint64_t r2 __asm__("x2") = badge_arg;

    __asm__ volatile(
        "svc #0\n\t"
        : "+r"(r0), "+r"(r1), "+r"(r2)
        :
        : "memory", "cc"
    );

    if (out_tag) {
        out_tag->raw = r2;
    }
    return r0;
}

/* ========================================================================= */
/* Tightbeam Client Runtime Functions                                        */
/* ========================================================================= */

/**
 * Initializes a new Tightbeam query message in preparing state.
 */
void tb_client_message_init(tb_message_t *msg, uint64_t endpoint_token, uint64_t invocation_id) {
    msg->state_and_flags = TB_MESSAGE_STATE_PREPARING;
    msg->disposition = TB_MESSAGE_DISPOSITION_QUERY;
    msg->reserved_padding[0] = 0;
    msg->reserved_padding[1] = 0;
    msg->reserved_padding[2] = 0;
    msg->invocation_id = invocation_id;
    msg->endpoint_token = endpoint_token;
    msg->payload_length = 0;
    msg->capabilities_count = 0;
    msg->inline_payload[0] = 0;
    msg->inline_payload[1] = 0;
    msg->inline_payload[2] = 0;
    msg->inline_payload[3] = 0;
    msg->cursor_position = 0;
    msg->transport_buffer = NULL;
}

/**
 * Serializes a 64-bit unsigned integer into the inline message payload.
 */
bool tb_client_encode_u64(tb_message_t *msg, uint64_t val) {
    if (msg->cursor_position + sizeof(uint64_t) > sizeof(msg->inline_payload)) {
        return false; /* Inline capacity exceeded (fallback to cL4_large required) */
    }

    uint8_t *dest = ((uint8_t *)msg->inline_payload) + msg->cursor_position;
    *((uint64_t *)dest) = val;

    msg->cursor_position += sizeof(uint64_t);
    msg->payload_length += sizeof(uint64_t);
    return true;
}

/**
 * Serializes an IEEE 754 32-bit float into the message payload.
 */
bool tb_client_encode_f32(tb_message_t *msg, float val) {
    if (msg->cursor_position + sizeof(float) > sizeof(msg->inline_payload)) {
        return false;
    }

    uint8_t *dest = ((uint8_t *)msg->inline_payload) + msg->cursor_position;
    *((float *)dest) = val;

    msg->cursor_position += sizeof(float);
    msg->payload_length += sizeof(float);
    return true;
}

/**
 * Delegates a cL4 capability in the message.
 */
bool tb_client_encode_capability(tb_message_t *msg, L4_Cap_t cap) {
    if (msg->capabilities_count >= TB_MAX_CAPS) {
        return false;
    }

    L4_IpcBuffer_t *ipcb = tb_get_ipc_buffer();
    ipcb->cr[msg->capabilities_count] = cap;
    msg->capabilities_count++;
    return true;
}

/**
 * Seals the message and dispatches it over the cL4 inline register transport.
 */
int tb_client_dispatch_call(L4_Cap_t server_ep, tb_message_t *req, tb_message_t *resp) {
    L4_IpcBuffer_t *ipcb = tb_get_ipc_buffer();

    /* 1. Mark message ready */
    req->state_and_flags = TB_MESSAGE_STATE_READY;

    /* 2. Populate IPC buffer message registers with header and inline payload */
    ipcb->mr[0] = ((uint64_t)req->state_and_flags) | (((uint64_t)req->disposition) << 32);
    ipcb->mr[1] = req->invocation_id;
    ipcb->mr[2] = req->endpoint_token;
    ipcb->mr[3] = req->payload_length | (req->capabilities_count << 32);
    ipcb->mr[4] = req->inline_payload[0];
    ipcb->mr[5] = req->inline_payload[1];
    ipcb->mr[6] = req->inline_payload[2];
    ipcb->mr[7] = req->inline_payload[3];

    /* 3. Configure cL4 MsgTag */
    L4_MsgTag_t tag;
    tag.raw = 0;
    tag.mrs_count = 8; /* Header (4 words) + Inline Payload (4 words) */
    tag.crs_count = req->capabilities_count;
    tag.protocol_label = req->endpoint_token >> 16;
    ipcb->tag = tag;

    /* 4. Issue synchronous IPC trap */
    req->state_and_flags = TB_MESSAGE_STATE_SENT;
    L4_MsgTag_t reply_tag;
    uint64_t err = cl4_ipc_call(server_ep, tag, 0, &reply_tag);

    if (err != L4_SUCCESS) {
        return (int)err;
    }

    /* 5. Unpack server response from IPC buffer */
    if (resp) {
        resp->state_and_flags = TB_MESSAGE_STATE_RECEIVED;
        resp->disposition = (uint8_t)(ipcb->mr[0] >> 32);
        resp->invocation_id = ipcb->mr[1];
        resp->endpoint_token = ipcb->mr[2];
        resp->payload_length = (uint32_t)ipcb->mr[3];
        resp->capabilities_count = (uint32_t)(ipcb->mr[3] >> 32);
        resp->inline_payload[0] = ipcb->mr[4];
        resp->inline_payload[1] = ipcb->mr[5];
        resp->inline_payload[2] = ipcb->mr[6];
        resp->inline_payload[3] = ipcb->mr[7];
        resp->cursor_position = 0;
        resp->transport_buffer = NULL;
    }

    return L4_SUCCESS;
}

/**
 * Example End-to-End Client Invocation
 */
int example_tightbeam_client_call(L4_Cap_t service_endpoint) {
    tb_message_t request;
    tb_message_t response;

    /* Initialize query with method token 0x00010002 and transaction ID 42 */
    tb_client_message_init(&request, 0x00010002ULL, 42ULL);

    /* Serialize arguments */
    tb_client_encode_u64(&request, 0xdeadbeefcafebabeULL);
    tb_client_encode_f32(&request, 3.14159f);

    /* Dispatch synchronous RPC call */
    int rc = tb_client_dispatch_call(service_endpoint, &request, &response);
    if (rc != L4_SUCCESS) {
        return rc; /* cL4 error code */
    }

    /* Verify response */
    if (response.disposition == TB_MESSAGE_DISPOSITION_REPLY) {
        uint64_t return_val = response.inline_payload[0];
        (void)return_val;
        return 0;
    }

    return -1;
}
