/**
 * @file apple_tightbeam_ipc.c
 * @brief ExclaveOS cL4 Microkernel & Tightbeam IPC Relay Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_tightbeam_ipc.h"
#include <string.h>

void tightbeam_ipc_init(AppleTightbeamState *s, const char *name, AppleAICState *aic) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name ? name : "tightbeam_relay";
    s->aic = aic;
    s->proxy_status = 0x00000001U; /* Microkernel IPC proxy active */
}

bool tightbeam_route_query(AppleTightbeamState *s,
                           const struct tb_message_s *query,
                           struct tb_message_s *reply_out,
                           L4_IpcBuffer_t *ipc_buf) {
    if (!s || !query || !reply_out) return false;

    /* Enforce capability constraints & header sanity */
    if (query->capabilities_count > TB_MAX_CAPS) {
        s->last_error = L4_ERROR_CAP_INVALID;
        return false;
    }

    if (query->disposition != TB_MESSAGE_DISPOSITION_QUERY ||
        (query->state_and_flags & 0xFF) != TB_MESSAGE_STATE_READY) {
        s->last_error = L4_ERROR_ARGUMENT_INVALID;
        return false;
    }

    s->total_queries_routed++;

    /* Prepare reply packet */
    memset(reply_out, 0, sizeof(*reply_out));
    reply_out->state_and_flags = TB_MESSAGE_STATE_READY;
    reply_out->disposition = TB_MESSAGE_DISPOSITION_REPLY;
    reply_out->invocation_id = query->invocation_id;
    reply_out->endpoint_token = query->endpoint_token;
    reply_out->payload_length = 32U;
    reply_out->capabilities_count = 1U;

    /* Process service method dispatch (e.g. secure math / enclave echo) */
    reply_out->inline_payload[0] = 0x0ULL; /* Return code 0 (Success) */
    reply_out->inline_payload[1] = query->inline_payload[0] * 2ULL;
    reply_out->inline_payload[2] = 0x434F4E434C415645ULL; /* 'CONCLAVE' token */
    reply_out->inline_payload[3] = query->invocation_id + 100ULL;

    /* Update thread IPC buffer */
    if (ipc_buf) {
        ipc_buf->tag.mrs_count = 4U;
        ipc_buf->tag.crs_count = 1U;
        ipc_buf->tag.protocol_label = query->endpoint_token;

        ipc_buf->mr[0] = reply_out->inline_payload[0];
        ipc_buf->mr[1] = reply_out->inline_payload[1];
        ipc_buf->mr[2] = reply_out->inline_payload[2];
        ipc_buf->mr[3] = reply_out->inline_payload[3];

        /* Mint unforgeable reply capability badge */
        ipc_buf->cr[0] = 0xCAFEBABE00000001ULL | (query->invocation_id & 0xFFFFULL);
        s->total_caps_minted++;
    }

    s->total_replies_generated++;

    /* Fire Exclave AOP2 Proxy interrupt if wired */
    if (s->aic) {
        aic_set_irq(s->aic, AIC_IRQ_EXCLAVE_AOP2_INBOX, 1);
    }

    return true;
}

int tightbeam_handle_syscall(AppleTightbeamState *s,
                             L4_Word_t syscall_num,
                             L4_IpcBuffer_t *ipc_buf,
                             struct tb_message_s *msg) {
    if (!s) return L4_ERROR_ARGUMENT_INVALID;

    s->total_syscall_traps++;

    /* cL4 svc #0 handler */
    if (syscall_num == 0) {
        if (!msg) return L4_ERROR_ARGUMENT_INVALID;

        struct tb_message_s reply;
        if (tightbeam_route_query(s, msg, &reply, ipc_buf)) {
            memcpy(msg, &reply, sizeof(reply));
            return L4_SUCCESS;
        }
        return (int)s->last_error;
    }

    return L4_ERROR_PERMISSION_INVALID;
}

uint32_t tightbeam_mmio_read32(AppleTightbeamState *s, uint64_t offset) {
    if (!s) return 0;
    switch (offset) {
        case 0x0000: return s->proxy_status;
        case 0x0004: return (uint32_t)s->total_syscall_traps;
        case 0x0008: return (uint32_t)s->total_queries_routed;
        case 0x000C: return (uint32_t)s->total_replies_generated;
        default: return 0;
    }
}

void tightbeam_mmio_write32(AppleTightbeamState *s, uint64_t offset, uint32_t val) {
    if (!s) return;
    switch (offset) {
        case 0x0000: s->proxy_status = val; break;
        default: break;
    }
}
