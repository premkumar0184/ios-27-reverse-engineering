/**
 * @file apple_tightbeam_ipc.h
 * @brief ExclaveOS cL4 Microkernel & Tightbeam IPC Relay Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_TIGHTBEAM_IPC_H
#define APPLE_TIGHTBEAM_IPC_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"

#ifdef __cplusplus
extern "C" {
#endif

/* cL4 Microkernel Constants */
#define L4_SUCCESS                          0
#define L4_ERROR_CAP_INVALID                4
#define L4_ERROR_ARGUMENT_INVALID           7
#define L4_ERROR_PERMISSION_INVALID         9

#define L4_IPC_BUFFER_MAX_MRS               32
#define L4_IPC_BUFFER_MAX_CRS               8
#define TB_MAX_CAPS                         8

typedef uint64_t L4_Cap_t;
typedef uint64_t L4_Word_t;

typedef union {
    uint64_t raw;
    struct {
        uint64_t mrs_count      : 6;
        uint64_t crs_count      : 4;
        uint64_t flags          : 6;
        uint64_t protocol_label : 48;
    };
} L4_MsgTag_t;

typedef struct {
    L4_MsgTag_t tag;
    uint64_t    mr[L4_IPC_BUFFER_MAX_MRS];
    L4_Cap_t    cr[L4_IPC_BUFFER_MAX_CRS];
} __attribute__((aligned(16))) L4_IpcBuffer_t;

/* Tightbeam Wire Constants */
#define TB_MESSAGE_STATE_UNINITIALIZED      0
#define TB_MESSAGE_STATE_PREPARING          1
#define TB_MESSAGE_STATE_READY              2
#define TB_MESSAGE_STATE_SENT               3
#define TB_MESSAGE_STATE_RECEIVED           4

#define TB_MESSAGE_DISPOSITION_QUERY        1
#define TB_MESSAGE_DISPOSITION_REPLY        2
#define TB_MESSAGE_DISPOSITION_ERROR        3
#define TB_MESSAGE_DISPOSITION_INIT_ARGS    4

typedef struct {
    uint16_t client_id;
    uint16_t isolation_domain;
    uint32_t session_nonce;
} TightbeamBadge_t;

/* 88-byte struct tb_message_s */
typedef struct tb_message_s {
    uint32_t state_and_flags;
    uint8_t  disposition;
    uint8_t  reserved_padding[3];
    uint64_t invocation_id;
    uint64_t endpoint_token;
    uint64_t payload_length;
    uint64_t capabilities_count;
    uint64_t inline_payload[4];
    uint64_t cursor_position;
    void    *transport_buffer;
} __attribute__((aligned(8))) tb_message_t;

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct tb_message_s) == 88, "struct tb_message_s must be exactly 88 bytes");
#endif

typedef struct AppleTightbeamState {
    const char       *name;
    AppleAICState    *aic;
    uint32_t          proxy_status;
    uint32_t          last_error;

    /* Telemetry */
    uint64_t          total_syscall_traps;
    uint64_t          total_queries_routed;
    uint64_t          total_replies_generated;
    uint64_t          total_caps_minted;
} AppleTightbeamState;

void tightbeam_ipc_init(AppleTightbeamState *s, const char *name, AppleAICState *aic);

int tightbeam_handle_syscall(AppleTightbeamState *s,
                             L4_Word_t syscall_num,
                             L4_IpcBuffer_t *ipc_buf,
                             struct tb_message_s *msg);

bool tightbeam_route_query(AppleTightbeamState *s,
                           const struct tb_message_s *query,
                           struct tb_message_s *reply_out,
                           L4_IpcBuffer_t *ipc_buf);

uint32_t tightbeam_mmio_read32(AppleTightbeamState *s, uint64_t offset);
void tightbeam_mmio_write32(AppleTightbeamState *s, uint64_t offset, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_TIGHTBEAM_IPC_H */
