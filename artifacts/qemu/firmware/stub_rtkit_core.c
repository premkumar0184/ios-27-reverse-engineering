/**
 * @file stub_rtkit_core.c
 * @brief RTKit Coprocessor State Machine & Bare-Metal Runtime Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "stub_rtkit_core.h"

#if defined(__STDC_HOSTED__) && __STDC_HOSTED__
#include <string.h>
#define rtk_strlen strlen
#define rtk_strncpy strncpy
#else
/* Freestanding helper routines for bare-metal ARM64 */
void *memset(void *dst, int c, size_t n) {
    volatile uint8_t *p = (volatile uint8_t *)dst;
    while (n--) *p++ = (uint8_t)c;
    return dst;
}

void *memcpy(void *dst, const void *src, size_t n) {
    volatile uint8_t *d = (volatile uint8_t *)dst;
    const volatile uint8_t *s = (const volatile uint8_t *)src;
    while (n--) *d++ = *s++;
    return dst;
}

static size_t rtk_strlen(const char *s) {
    size_t len = 0;
    while (s && s[len]) len++;
    return len;
}

static char *rtk_strncpy(char *dst, const char *src, size_t n) {
    size_t i;
    for (i = 0; i < n && src[i] != '\0'; i++) {
        dst[i] = src[i];
    }
    for (; i < n; i++) {
        dst[i] = '\0';
    }
    return dst;
}
#endif

static AppleRTKitState g_rtkit_state;

void rtkit_init(AppleRTKitState *rtk, uint32_t coproc_id, uint64_t ascwrap_base, uint64_t doorbell_base) {
    if (!rtk) return;
    memset(rtk, 0, sizeof(*rtk));
    rtk->coproc_id = coproc_id;
    rtk->state = RTK_STATE_HELLO_WAIT;
    rtk->version = (uint32_t)RTK_PROTOCOL_VERSION_V2;
    rtk->ascwrap_base = ascwrap_base;
    rtk->doorbell_base = doorbell_base;

    /* Base endpoints: EP0 (Mgmt), EP1 (Syslog), EP16 (App) */
    rtk->active_endpoints_mask = (1ULL << RTK_EP_MGMT) |
                                 (1ULL << RTK_EP_SYSLOG) |
                                 (1ULL << RTK_EP_APP_BASE);

    if (coproc_id == RTK_COPROC_AOP2) {
        rtk->active_endpoints_mask |= (1ULL << RTK_EP_EXCLAVE);
    } else if (coproc_id == RTK_COPROC_SILENUS) {
        rtk->active_endpoints_mask |= (1ULL << RTK_EP_SILENUS);
    } else if (coproc_id == RTK_COPROC_RTBUDDY) {
        rtk->active_endpoints_mask |= (1ULL << RTK_EP_AGX_RTBUDDY);
    }

    const char *boot_msg = "RTKitOS: [BOOT] Coprocessor ready, SMP 2 cores active, MMU enabled\n";
    rtk_strncpy(rtk->syslog_buffer, boot_msg, sizeof(rtk->syslog_buffer) - 1);
    rtk->syslog_len = (uint32_t)rtk_strlen(rtk->syslog_buffer);
}

void rtkit_handle_msg(AppleRTKitState *rtk, uint16_t ep, uint64_t payload,
                      void (*tx_func)(void *opaque, uint16_t ep, uint64_t payload), void *opaque) {
    if (!rtk) return;
    rtk->total_rx_msgs++;

    /* Endpoint 0: Management Protocol */
    if (ep == RTK_EP_MGMT) {
        uint64_t cmd = payload & 0xFFFFULL;
        if (cmd == RTK_EP0_MSG_HELLO) {
            /* 1. Reply with HELLO_ACK and protocol version */
            uint64_t ack_payload = (RTK_EP0_MSG_HELLO_ACK << 32) | RTK_PROTOCOL_VERSION_V2;
            if (tx_func) {
                tx_func(opaque, RTK_EP_MGMT, ack_payload);
                rtk->total_tx_msgs++;
            }

            /* 2. Advertise active endpoint bitmask */
            uint64_t ep_map_payload = (RTK_EP0_MSG_EP_MAP << 32) | (rtk->active_endpoints_mask & 0xFFFFFFFFULL);
            if (tx_func) {
                tx_func(opaque, RTK_EP_MGMT, ep_map_payload);
                rtk->total_tx_msgs++;
            }

            rtk->state = RTK_STATE_RUNNING;
        }
        return;
    }

    /* Endpoint 1: Syslog Protocol */
    if (ep == RTK_EP_SYSLOG) {
        /* Acknowledge syslog configuration / drain */
        if (tx_func) {
            tx_func(opaque, RTK_EP_SYSLOG, 0x0000000000000001ULL);
            rtk->total_tx_msgs++;
        }
        return;
    }

    /* Application Endpoints */
    if (ep >= RTK_EP_APP_BASE) {
        rtk->total_app_cmds++;
        if (tx_func) {
            /* Echo command token back with completion bit set */
            tx_func(opaque, ep, payload | 0x8000000000000000ULL);
            rtk->total_tx_msgs++;
        }
        return;
    }
}

#ifndef DEFAULT_COPROC_ID
#define DEFAULT_COPROC_ID RTK_COPROC_AOP2
#endif

void rtkit_main(void) {
    uint64_t asc_base = 0x101600000ULL;
    uint64_t db_base = 0x10162c000ULL;

    if (DEFAULT_COPROC_ID == RTK_COPROC_SILENUS) {
        asc_base = 0x1128c0000ULL;
        db_base  = 0x1128c4000ULL;
    } else if (DEFAULT_COPROC_ID == RTK_COPROC_RTBUDDY) {
        asc_base = 0x23b800000ULL;
        db_base  = 0x23a000000ULL;
    }

    /* Initialize designated coprocessor instance */
    rtkit_init(&g_rtkit_state, DEFAULT_COPROC_ID, asc_base, db_base);

    /* Poll / wait for mailbox events on bare-metal hardware */
    volatile uint64_t *inbox_ctrl = (volatile uint64_t *)(uintptr_t)(g_rtkit_state.ascwrap_base);
    while (1) {
        if (inbox_ctrl) {
            /* Keep core in low power state while waiting */
#if defined(__aarch64__)
            __asm__ volatile("wfi");
#endif
        }
    }
}
