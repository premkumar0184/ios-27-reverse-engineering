/*
 * Apple U2 / U3 Ultra-Wideband (UWB) — Firmware Container & Memory Map
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Rose 2 (r2p1 / hammerfest) — iPhone 18,3 (v57ap)
 * Subsystems: rkosftab, RTKitOS ARM Cortex-M, MMS32 DSP Baseband
 */

#ifndef ROSE_RKOS_FTAB_H
#define ROSE_RKOS_FTAB_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. FTAB Container Magic & Layout
 * ========================================================================= */

#define ROSE_FTAB_MAGIC_OFFSET        0x00000020U
#define ROSE_FTAB_MAGIC               0x726b6f7366746162ULL /* "rkosftab" */
#define ROSE_FTAB_MAX_ENTRIES         5U

typedef struct __attribute__((packed)) {
    uint64_t magic;           /* "rkosftab" (0x726b6f7366746162) */
    uint32_t num_entries;     /* Number of partition entries (5) */
    uint32_t reserved;        /* Reserved flags (0x00000000) */
} rose_ftab_header_t;

typedef struct __attribute__((packed)) {
    uint32_t tag;             /* FourCC partition tag (e.g., 'rkos', 'sbd1') */
    uint32_t offset;          /* Absolute byte offset within ftab.bin */
    uint32_t length;          /* Partition payload length in bytes */
    uint32_t flags_pad;       /* Partition attributes / padding */
} rose_ftab_entry_t;

/* Partition FourCC Identifiers */
#define ROSE_TAG_RKOS                 0x736f6b72U /* 'rkos' - RTKitOS Microkernel */
#define ROSE_TAG_SBD1                 0x31646273U /* 'sbd1' - MMS32 Baseband PHY */
#define ROSE_TAG_ICNF                 0x666e6369U /* 'icnf' - rkosioss I/O Config */
#define ROSE_TAG_BVER                 0x72657662U /* 'bver' - Build Version */
#define ROSE_TAG_OSL                  0x6c736f5fU /* '_osl' - OS_log Symbol Table */

/* =========================================================================
 * 2. 32-bit ARM Cortex-M Memory Mapping & Vector Table
 * ========================================================================= */

#define ROSE_RKOS_BASE_ADDR           0x00400000U /* SRAM / TCM execution window */
#define ROSE_RKOS_ENTRY_POINT         0x00400221U /* Thumb-2 reset vector */
#define ROSE_MMS32_DSP_BASE_ADDR      0x00800000U /* DSP microcode load address */
#define ROSE_CIR_BUFFER_BASE          0x20010000U /* Hardware CIR sample buffer */

typedef struct __attribute__((packed)) {
    uint32_t initial_sp;       /* Staged via ROM bootloader */
    uint32_t reset_handler;    /* 0x00400221 */
    uint32_t nmi_handler;      /* 0x00400159 */
    uint32_t hardfault_handler;/* 0x00400109 */
    uint32_t memmanage_handler;/* 0x00400109 */
    uint32_t busfault_handler; /* 0x00400109 */
    uint32_t usagefault_handler;/* 0x00400109 */
    uint32_t reserved7;
    uint32_t reserved8;
    uint32_t reserved9;
    uint32_t reserved10;
    uint32_t svcall_handler;   /* 0x004001ed */
    uint32_t debugmon_handler; /* 0x00400109 */
    uint32_t reserved13;
    uint32_t pendsv_handler;   /* 0x004001ed */
    uint32_t systick_handler;  /* 0x0040975d */
    uint32_t irq_handlers[32]; /* Peripheral IRQ dispatch table -> 0x0040975d */
} rose_cortex_m_vectors_t;

/* =========================================================================
 * 3. SPMI Host Bus & In-Device Coexistence Interface
 * ========================================================================= */

#define ROSE_SPMI_DEVICE_ADDR         0x03U       /* Slave ID on aop-spmi1 */
#define ROSE_SPMI_REG_GPR0            0x0010U     /* General Purpose Register 0 */
#define ROSE_SPMI_REG_AR_BUF_START    0x0100U     /* Auto-Read Ranging Buffer */
#define ROSE_SPMI_REG_COEX_STATE      0x0200U     /* Real-Time Coexistence Status */

typedef enum {
    ROSE_COEX_RADIO_UWB               = 0x01,
    ROSE_COEX_RADIO_WIFI              = 0x02,
    ROSE_COEX_RADIO_BLUETOOTH         = 0x03,
    ROSE_COEX_RADIO_CELLULAR          = 0x04
} rose_coex_radio_type_t;

typedef struct {
    uint8_t  uwb_state;
    uint8_t  wifi_state;
    uint8_t  cnv_state;
    uint8_t  active_channel;
    bool     is_disallowed;
    uint32_t lte_blanking_request;
} rose_coex_status_t;

#ifdef __cplusplus
}
#endif

#endif /* ROSE_RKOS_FTAB_H */
