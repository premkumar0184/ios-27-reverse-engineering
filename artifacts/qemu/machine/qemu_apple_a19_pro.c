/**
 * @file qemu_apple_a19_pro.c
 * @brief Unified Apple Silicon A19 Pro (t8150) QEMU MachineClass Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 *
 * Integrates:
 *   - 36-bit Physical DRAM Map & CTRR / SPTM / TXM / Exclave Carveouts
 *   - Apple Interrupt Controller (AIC v3/v4, 1024 IRQ lines)
 *   - ASCwrap-v6 Mailbox & Doorbell Engines (SEP, AOP2, AGX RTBuddy, DCP)
 *   - Apple DART Gen3/Gen4 IOMMUs (16 KB pages, Stream IDs 0x00..0x0C)
 *   - Clean-Room Accelerators:
 *       * AppleMetalDirect (AGX G18 Pro GPU)
 *       * Silenus Camera ISP & Bayer Neural Interface (BNI)
 *       * AppleProResHW (AVE2 Video Accelerator)
 *       * ExclaveOS cL4 Microkernel & Tightbeam IPC Bridge
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "../include/apple_a19_platform.h"
#include "../devices/apple_aic.h"
#include "../devices/apple_ascwrap.h"
#include "../devices/apple_dart.h"
#include "../devices/apple_agx_direct.h"
#include "../devices/apple_silenus_dma.h"
#include "../devices/apple_prores_hw.h"
#include "../devices/apple_tightbeam_ipc.h"

#define TYPE_APPLE_A19_PRO_MACHINE "apple-a19-pro"

/* QEMU QOM Type & Machine Compatibility Declarations */
typedef struct MachineClass {
    const char *name;
    const char *desc;
    void (*init)(void *machine);
    uint32_t max_cpus;
    uint32_t default_cpus;
    uint64_t default_ram_size;
} MachineClass;

typedef struct MachineState {
    const char *cpu_type;
    uint32_t    smp_cpus;
    uint64_t    ram_size;
} MachineState;

/* Unified Machine Instance State */
typedef struct AppleA19ProMachineState {
    MachineState parent;

    /* Platform Subsystems */
    AppleAICState        aic;
    AppleDARTState       dart_isp;
    AppleDARTState       dart_ave;
    AppleDARTState       dart_sep;

    /* Mailbox Engines */
    AppleASCwrapState    asc_sep;
    AppleASCwrapState    asc_aop1;
    AppleASCwrapState    asc_aop2;
    AppleASCwrapState    asc_dcp;
    AppleASCwrapState    asc_pmp;
    AppleASCwrapState    asc_agx_core0;
    AppleASCwrapState    asc_agx_core1;

    /* Clean-Room Hardware Accelerators */
    AppleAGXState        agx_gpu;
    AppleSilenusState    silenus_isp;
    AppleProResHWState   prores_hw;
    AppleTightbeamState  tightbeam_ipc;

    /* Memory Buffers */
    uint8_t             *dram_base;
    uint8_t             *aop2_sram;
    uint8_t             *sep_tz1s_buffer;

    bool                 initialized;
} AppleA19ProMachineState;

static AppleA19ProMachineState g_apple_a19_machine;

/**
 * @brief Initialize all platform memory, interrupts, mailboxes, and accelerators
 */
void apple_a19_pro_machine_init(void *opaque) {
    AppleA19ProMachineState *s = (AppleA19ProMachineState *)opaque;
    if (!s) s = &g_apple_a19_machine;

    memset(s, 0, sizeof(*s));

    /* 1. Initialize AIC v3/v4 Interrupt Controller */
    aic_init(&s->aic);

    /* 2. Initialize ASCwrap-v6 Mailbox Instances */
    ascwrap_init(&s->asc_sep, "ascwrap_sep", &s->aic,
                 AIC_IRQ_SEP_INBOX, AIC_IRQ_SEP_OUTBOX, AIC_IRQ_SEP_DOORBELL);

    ascwrap_init(&s->asc_aop1, "ascwrap_aop1", &s->aic,
                 AIC_IRQ_AOP1_INBOX, AIC_IRQ_AOP1_OUTBOX, AIC_IRQ_AOP1_DOORBELL);

    ascwrap_init(&s->asc_aop2, "ascwrap_aop2", &s->aic,
                 AIC_IRQ_AOP2_INBOX, AIC_IRQ_AOP2_OUTBOX, AIC_IRQ_AOP2_DOORBELL);

    ascwrap_init(&s->asc_dcp, "ascwrap_dcp", &s->aic,
                 AIC_IRQ_DCP_INBOX, AIC_IRQ_DCP_OUTBOX, AIC_IRQ_DCP_DOORBELL);

    ascwrap_init(&s->asc_pmp, "ascwrap_pmp", &s->aic,
                 AIC_IRQ_PMP_INBOX, AIC_IRQ_PMP_OUTBOX, AIC_IRQ_PMP_DOORBELL);

    ascwrap_init(&s->asc_agx_core0, "ascwrap_agx0", &s->aic,
                 AIC_IRQ_AGX_CORE0_INBOX, AIC_IRQ_AGX_CORE0_OUTBOX, AIC_IRQ_AGX_CORE0_DOORBELL);

    ascwrap_init(&s->asc_agx_core1, "ascwrap_agx1", &s->aic,
                 AIC_IRQ_AGX_CORE1_INBOX, AIC_IRQ_AGX_CORE1_OUTBOX, AIC_IRQ_AGX_CORE1_DOORBELL);

    /* 3. Initialize Apple DART Gen3/Gen4 IOMMUs */
    dart_init(&s->dart_isp, "dart_isp", &s->aic, AIC_IRQ_DART_ISP_FAULT);
    dart_init(&s->dart_ave, "dart_ave", &s->aic, AIC_IRQ_DART_AVE_FAULT);
    dart_init(&s->dart_sep, "dart_sep", &s->aic, AIC_IRQ_DART_SEP_FAULT);

    /* 4. Initialize Clean-Room Accelerators */
    agx_direct_init(&s->agx_gpu, "agx_g18p", &s->aic, &s->asc_agx_core0, &s->dart_isp);
    silenus_dma_init(&s->silenus_isp, "silenus_isp", &s->aic, &s->asc_aop2, &s->dart_isp);
    prores_hw_init(&s->prores_hw, "apple_prores_hw", &s->aic, &s->dart_ave);
    tightbeam_ipc_init(&s->tightbeam_ipc, "tightbeam_relay", &s->aic);

    s->initialized = true;
}

AppleA19ProMachineState *qemu_apple_a19_pro_get_instance(void) {
    if (!g_apple_a19_machine.initialized) {
        apple_a19_pro_machine_init(&g_apple_a19_machine);
    }
    return &g_apple_a19_machine;
}

static void apple_a19_pro_class_init(MachineClass *mc) {
    if (!mc) return;
    mc->name = TYPE_APPLE_A19_PRO_MACHINE;
    mc->desc = "Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)";
    mc->init = apple_a19_pro_machine_init;
    mc->max_cpus = 8;
    mc->default_cpus = 8;
    mc->default_ram_size = A19_DRAM_SIZE;
}
