/**
 * @file apple_a19_platform.h
 * @brief Unified Apple Silicon A19 Pro (t8150) Platform Topology & Register Specification
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 *
 * Clean-Room Bare-Metal QEMU / Virtualization Platform Interface
 * Defines:
 *  - 36-bit Physical DRAM Map & CTRR / SPTM / TXM / Exclave / SEP Carveouts
 *  - MMIO Bus Apertures (Low, PMP/Core Fabric, Mid, High)
 *  - Apple Interrupt Controller (AIC v3/v4) Vector Table (0..1023)
 *  - ASCwrap-v6 Mailbox & Doorbell Engine Register Offsets
 *  - DART Gen3/Gen4 IOMMU Translation & Stream ID Geometry
 */

#ifndef APPLE_A19_PLATFORM_H
#define APPLE_A19_PLATFORM_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Global Physical Memory Map (36-bit Physical Addressing)                */
/* ========================================================================= */

#define A19_PA_BITS                         36U
#define A19_PAGE_SIZE_16K                   16384ULL
#define A19_PAGE_MASK_16K                   (A19_PAGE_SIZE_16K - 1ULL)
#define A19_PAGE_SHIFT_16K                  14U

#define A19_DRAM_BASE                       0x0000000800000000ULL
#define A19_DRAM_SIZE                       0x0000000800000000ULL /* 32 GB */
#define A19_DRAM_LIMIT                      (A19_DRAM_BASE + A19_DRAM_SIZE - 1ULL)

/* Hardware-Enforced DRAM Carveouts */
#define A19_SPTM_RESERVED_BASE              0x0000000800000000ULL
#define A19_SPTM_RESERVED_SIZE              0x0000000020000000ULL /* 512 MB */

#define A19_TXM_RESERVED_BASE               0x0000000820000000ULL
#define A19_TXM_RESERVED_SIZE               0x0000000004000000ULL /* 64 MB */

#define A19_EXCLAVE_POOL_BASE               0x0000000824000000ULL
#define A19_EXCLAVE_POOL_SIZE               0x0000000040000000ULL /* 1 GB */

#define A19_SEP_TZ0S_BASE                   0x0000000864000000ULL
#define A19_SEP_TZ0S_SIZE                   0x00000000061b0000ULL /* 97.6875 MB */

#define A19_SEP_TZ1S_BASE                   0x000000086a1b0000ULL
#define A19_SEP_TZ1S_SIZE                   0x0000000005060000ULL /* 80.375 MB (Pearl NIR) */

#define A19_DARWIN_HOST_BASE                0x000000086f210000ULL
#define A19_DARWIN_HOST_SIZE                0x0000000790df0000ULL /* ~30.26 GB */

/* On-Chip Coprocessor Retention SRAMs */
#define A19_SEP_SRAM_BASE                   0x0000000070000000ULL
#define A19_SEP_SRAM_SIZE                   0x0000000000080000ULL /* 512 KB */

#define A19_AOP2_SRAM_BASE                  0x0000000100000000ULL
#define A19_AOP2_SRAM_SIZE                  0x0000000000558000ULL /* 5.34 MB */

#define A19_AGX_TILE_SRAM_BASE              0x0000000230000000ULL
#define A19_AGX_TILE_SRAM_SIZE              0x0000000001000000ULL /* 16 MB */

#define A19_ANE_SRAM_BASE                   0x0000000270000000ULL
#define A19_ANE_SRAM_SIZE                   0x0000000002000000ULL /* 32 MB */

/* ========================================================================= */
/* 2. MMIO Peripheral Base Addresses                                         */
/* ========================================================================= */

/* Low MMIO Aperture (System Peripherals & Hardware Security) */
#define MMIO_DART_SEP_BASE                  0x0000000070c80000ULL
#define MMIO_ASCWRAP_SEP_BASE               0x0000000072600000ULL
#define MMIO_DOORBELL_SEP_BASE              0x000000007262c000ULL
#define MMIO_DART_AVE_BASE                  0x0000000077020000ULL
#define MMIO_PRORES_HW_BASE                 0x0000000077080000ULL
#define MMIO_PRORES_HW_SIZE                 0x0000000000040000ULL /* 256 KB */
#define MMIO_DART_JPEG_BASE                 0x000000007d020000ULL

/* PMP & Core Fabric Aperture */
#define MMIO_DART_PMP_BASE                  0x00000000f0300000ULL
#define MMIO_ASCWRAP_PMP_BASE               0x00000000f0300000ULL
#define MMIO_DOORBELL_PMP_BASE              0x00000000f032c000ULL
#define MMIO_PMGR_BASE                      0x00000000f3400000ULL
#define MMIO_AIC_BASE                       0x00000000f3c00000ULL
#define MMIO_AIC_SIZE                       0x0000000000010000ULL /* 64 KB */

/* Mid MMIO Aperture (Coprocessors, Display & Camera) */
#define MMIO_ASCWRAP_AOP1_BASE              0x0000000100600000ULL
#define MMIO_DOORBELL_AOP1_BASE             0x000000010062c000ULL
#define MMIO_DART_AOP_BASE                  0x0000000100fc0000ULL
#define MMIO_ASCWRAP_AOP2_BASE              0x0000000101600000ULL
#define MMIO_DOORBELL_AOP2_BASE             0x000000010162c000ULL

#define MMIO_DART_ISP_BASE                  0x00000001128c0000ULL
#define MMIO_DART_ISP_SIZE                  0x0000000000010000ULL /* 64 KB */
#define MMIO_ISP_SIF_BASE                   0x00000000f0724000ULL
#define MMIO_ISP_CORE_SRAM_BASE             0x0000000101000000ULL

#define MMIO_ASCWRAP_DCP_BASE               0x00000001fa000000ULL
#define MMIO_DOORBELL_DCP_BASE              0x00000001fa02c000ULL
#define MMIO_DART_DCP_BASE                  0x00000001fa340000ULL

/* High MMIO Aperture (GPU, ANE & Exclave Proxies) */
#define MMIO_AGX_GPU_BASE                   0x0000000230000000ULL
#define MMIO_AGX_DOORBELL_BASE              0x000000023a000000ULL
#define MMIO_ASCWRAP_AGX_CORE0_BASE         0x000000023b800000ULL
#define MMIO_ASCWRAP_AGX_CORE1_BASE         0x000000023bc00000ULL
#define MMIO_DART_ANE_BASE                  0x0000000271800000ULL
#define MMIO_EXCLAVE_AOP2_PROXY_BASE        0x000000035167c000ULL

/* ========================================================================= */
/* 3. Apple Interrupt Controller (AIC v3/v4) Vector Table                    */
/* ========================================================================= */

#define AIC_MAX_IRQ                         1024U

/* Target Vector Assignments */
#ifndef AIC_IRQ_PRORES_COMPLETE
#define AIC_IRQ_PRORES_COMPLETE             256     /* 0x0100: AppleProResHW Slice Done */
#endif
#ifndef AIC_IRQ_ISP_FRAME_DONE
#define AIC_IRQ_ISP_FRAME_DONE              284     /* 0x011c: Silenus Frame Complete   */
#endif
#ifndef AIC_IRQ_ISP_STATS_READY
#define AIC_IRQ_ISP_STATS_READY             285     /* 0x011d: 3A Stats Ready           */
#endif
#ifndef AIC_IRQ_ISP_DMA_ERROR
#define AIC_IRQ_ISP_DMA_ERROR               286     /* 0x011e: Camera DMA Error         */
#endif
#ifndef AIC_IRQ_ISP_CIL_BREAKER
#define AIC_IRQ_ISP_CIL_BREAKER             287     /* 0x011f: MIPI CIL Trip            */
#endif
#ifndef AIC_IRQ_ISP_MAILBOX_EVENT
#define AIC_IRQ_ISP_MAILBOX_EVENT           297     /* 0x0129: ISP Mailbox Event        */
#endif
#ifndef AIC_IRQ_DART_ISP_FAULT
#define AIC_IRQ_DART_ISP_FAULT              302     /* 0x012e: DART-ISP Fault           */
#endif

#ifndef AIC_IRQ_SEP_INBOX
#define AIC_IRQ_SEP_INBOX                   304U    /* 0x0130: SEP Mailbox Inbox        */
#define AIC_IRQ_SEP_OUTBOX                  305U    /* 0x0131: SEP Mailbox Outbox       */
#define AIC_IRQ_SEP_DOORBELL                306U    /* 0x0132: SEP Doorbell             */
#define AIC_IRQ_DART_SEP_FAULT              314U    /* 0x013a: DART-SEP Fault           */
#endif

#ifndef AIC_IRQ_AOP1_INBOX
#define AIC_IRQ_AOP1_INBOX                  349U    /* 0x015d: AOP1 Mailbox Inbox       */
#define AIC_IRQ_AOP1_OUTBOX                 350U    /* 0x015e: AOP1 Mailbox Outbox      */
#define AIC_IRQ_AOP1_DOORBELL               351U    /* 0x015f: AOP1 Doorbell            */
#endif

#ifndef AIC_IRQ_AOP2_INBOX
#define AIC_IRQ_AOP2_INBOX                  357U    /* 0x0165: AOP2 Mailbox Inbox       */
#define AIC_IRQ_AOP2_OUTBOX                 358U    /* 0x0166: AOP2 Mailbox Outbox      */
#define AIC_IRQ_AOP2_DOORBELL               359U    /* 0x0167: AOP2 Doorbell            */
#define AIC_IRQ_EXCLAVE_AOP2_INBOX          361U    /* 0x0169: Exclave AOP2 Proxy In    */
#define AIC_IRQ_EXCLAVE_AOP2_OUTBOX         364U    /* 0x016c: Exclave AOP2 Proxy Out   */
#endif

#ifndef AIC_IRQ_DCP_INBOX
#define AIC_IRQ_DCP_INBOX                   632U    /* 0x0278: DCP Mailbox Inbox        */
#define AIC_IRQ_DCP_OUTBOX                  633U    /* 0x0279: DCP Mailbox Outbox       */
#define AIC_IRQ_DCP_DOORBELL                634U    /* 0x027a: DCP Doorbell             */
#endif

#ifndef AIC_IRQ_PMP_INBOX
#define AIC_IRQ_PMP_INBOX                   776U    /* 0x0308: PMP Mailbox Inbox        */
#define AIC_IRQ_PMP_OUTBOX                  777U    /* 0x0309: PMP Mailbox Outbox       */
#define AIC_IRQ_PMP_DOORBELL                778U    /* 0x030a: PMP Doorbell             */
#endif

#ifndef AIC_IRQ_AGX_CORE0_INBOX
#define AIC_IRQ_AGX_CORE0_INBOX             952U    /* 0x03b8: AGX RTBuddy 0 Inbox      */
#define AIC_IRQ_AGX_CORE0_OUTBOX            953U    /* 0x03b9: AGX RTBuddy 0 Outbox     */
#define AIC_IRQ_AGX_CORE0_DOORBELL          954U    /* 0x03ba: AGX RTBuddy 0 Doorbell   */
#define AIC_IRQ_AGX_CORE1_INBOX             956U    /* 0x03bc: AGX RTBuddy 1 Inbox      */
#define AIC_IRQ_AGX_CORE1_OUTBOX            957U    /* 0x03bd: AGX RTBuddy 1 Outbox     */
#define AIC_IRQ_AGX_CORE1_DOORBELL          958U    /* 0x03be: AGX RTBuddy 1 Doorbell   */
#endif

#ifndef AIC_IRQ_DART_AVE_FAULT
#define AIC_IRQ_DART_AVE_FAULT              917U    /* 0x0395: DART-AVE Fault           */
#define AIC_IRQ_DART_DCP_FAULT              632U    /* 0x0278: DART-DCP Fault           */
#define AIC_IRQ_DART_ANE_FAULT              800U    /* 0x0320: DART-ANE Fault           */
#endif

/* ========================================================================= */
/* 4. ASCwrap-v6 Mailbox & Doorbell Hardware Registers                       */
/* ========================================================================= */

#define ASCWRAP_REG_INBOX_CTRL              0x0000U
#define ASCWRAP_REG_INBOX_DATA              0x0008U
#define ASCWRAP_REG_OUTBOX_CTRL             0x0020U
#define ASCWRAP_REG_OUTBOX_DATA             0x0028U
#define ASCWRAP_REG_STATUS                  0x0040U

#define ASCWRAP_STATUS_INBOX_EMPTY          (1U << 0)
#define ASCWRAP_STATUS_INBOX_FULL           (1U << 1)
#define ASCWRAP_STATUS_OUTBOX_EMPTY         (1U << 16)
#define ASCWRAP_STATUS_OUTBOX_FULL          (1U << 17)

#define DOORBELL_REG_SET                    0x0000U
#define DOORBELL_REG_CLEAR                  0x0004U
#define DOORBELL_REG_STATUS                 0x0008U

/* 64-bit ASCwrap Mailbox Message Format */
#define ASCWRAP_MSG_EP_MASK                 0xFFFF000000000000ULL
#define ASCWRAP_MSG_EP_SHIFT                48U
#define ASCWRAP_MSG_PAYLOAD_MASK            0x0000FFFFFFFFFFFFULL

static inline uint16_t ascwrap_msg_get_ep(uint64_t msg) {
    return (uint16_t)((msg & ASCWRAP_MSG_EP_MASK) >> ASCWRAP_MSG_EP_SHIFT);
}

static inline uint64_t ascwrap_msg_get_payload(uint64_t msg) {
    return (msg & ASCWRAP_MSG_PAYLOAD_MASK);
}

static inline uint64_t ascwrap_msg_compose(uint16_t ep, uint64_t payload) {
    return (((uint64_t)ep << ASCWRAP_MSG_EP_SHIFT) | (payload & ASCWRAP_MSG_PAYLOAD_MASK));
}

/* ========================================================================= */
/* 5. Apple DART Gen3/Gen4 IOMMU Hardware Registers                          */
/* ========================================================================= */

#define DART_REG_CONFIG                     0x0000U
#define DART_REG_TLB_INVAL                  0x0004U
#define DART_REG_TLB_INVAL_ADDR             0x0008U
#define DART_REG_FAULT_STATUS               0x0010U
#define DART_REG_FAULT_ADDR_LO              0x0014U
#define DART_REG_FAULT_ADDR_HI              0x0018U
#define DART_REG_FAULT_SID                  0x001CU
#define DART_REG_TTBR_BASE(sid)             (0x0020U + ((sid) * 4U))

#define DART_MAX_STREAMS                    16U
#define DART_CONFIG_ENABLE                  (1U << 0)
#define DART_CONFIG_BYPASS                  (1U << 1)
#define DART_FAULT_FLAG                     (1U << 31)

#ifdef __cplusplus
}
#endif

#endif /* APPLE_A19_PLATFORM_H */
