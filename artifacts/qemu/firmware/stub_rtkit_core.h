/**
 * @file stub_rtkit_core.h
 * @brief RTKit Coprocessor State Machine & Wire Protocol Definitions
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef STUB_RTKIT_CORE_H
#define STUB_RTKIT_CORE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RTK_STACK_CANARY                    0x52544B535441434BULL /* 'RTKSTACK' */
#define RTK_PROTOCOL_VERSION_V2             0x00020000ULL

/* RTKit Endpoints */
#define RTK_EP_MGMT                         0U   /* Endpoint 0: Protocol Handshake */
#define RTK_EP_SYSLOG                       1U   /* Endpoint 1: Diagnostic Logging */
#define RTK_EP_APP_BASE                     16U  /* Endpoint 16: Generic App Engine */
#define RTK_EP_SILENUS                      32U  /* Endpoint 32: Silenus Camera ISP */
#define RTK_EP_AGX_RTBUDDY                  48U  /* Endpoint 48: AGX RTBuddy GPU */
#define RTK_EP_EXCLAVE                      53U  /* Endpoint 53: ExclaveOS Proxy */

/* Endpoint 0 Management Messages */
#define RTK_EP0_MSG_HELLO                   0x0001ULL
#define RTK_EP0_MSG_HELLO_ACK               0x0002ULL
#define RTK_EP0_MSG_EP_MAP                  0x0003ULL
#define RTK_EP0_MSG_CONFIG                  0x0004ULL
#define RTK_EP0_MSG_EP_MAP_HI               0x0005ULL

/* Coprocessor IDs */
#define RTK_COPROC_AOP2                     1U
#define RTK_COPROC_SILENUS                  2U
#define RTK_COPROC_RTBUDDY                  3U

typedef enum {
    RTK_STATE_RESET         = 0,
    RTK_STATE_HELLO_WAIT    = 1,
    RTK_STATE_RUNNING       = 2,
    RTK_STATE_ERROR         = 3
} rtk_state_t;

typedef struct AppleRTKitState {
    uint32_t    coproc_id;
    rtk_state_t state;
    uint32_t    version;
    uint64_t    active_endpoints_mask;
    uint64_t    ascwrap_base;
    uint64_t    doorbell_base;

    /* Syslog Buffer */
    char        syslog_buffer[512];
    uint32_t    syslog_len;

    /* Counters */
    uint64_t    total_rx_msgs;
    uint64_t    total_tx_msgs;
    uint64_t    total_app_cmds;
} AppleRTKitState;

void rtkit_init(AppleRTKitState *rtk, uint32_t coproc_id, uint64_t ascwrap_base, uint64_t doorbell_base);
void rtkit_handle_msg(AppleRTKitState *rtk, uint16_t ep, uint64_t payload,
                      void (*tx_func)(void *opaque, uint16_t ep, uint64_t payload), void *opaque);
void rtkit_main(void);

#ifdef __cplusplus
}
#endif

#endif /* STUB_RTKIT_CORE_H */
