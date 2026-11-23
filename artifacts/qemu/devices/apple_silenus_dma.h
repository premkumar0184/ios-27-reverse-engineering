/**
 * @file apple_silenus_dma.h
 * @brief Silenus Camera ISP & Bayer Neural Interface (BNI) Hardware Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_SILENUS_DMA_H
#define APPLE_SILENUS_DMA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../../silenus/driver/silenus_host_interface.h"
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"
#include "apple_ascwrap.h"
#include "apple_dart.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct AppleSilenusState {
    const char           *name;
    AppleAICState        *aic;
    AppleASCwrapState    *ascwrap;
    AppleDARTState       *dart;

    /* Direct memory sink for SEP TZ1S (Pearl NIR) */
    uint8_t              *tz1s_target_buffer;
    size_t                tz1s_buffer_size;

    /* Hardware register state */
    uint32_t              sif_status;
    uint32_t              isp_control;
    uint32_t              frame_counter;

    /* Telemetry */
    uint64_t              total_commands;
    uint64_t              total_frames_processed;
    uint64_t              total_bni_packets_routed;
    uint64_t              total_3a_stats_generated;
} AppleSilenusState;

void silenus_dma_init(AppleSilenusState *s, const char *name, AppleAICState *aic,
                      AppleASCwrapState *ascwrap, AppleDARTState *dart);

void silenus_set_tz1s_buffer(AppleSilenusState *s, uint8_t *buf, size_t size);

bool silenus_process_cisp_packet(AppleSilenusState *s, const struct cisp_command_packet *pkt);

uint32_t silenus_mmio_read32(AppleSilenusState *s, uint64_t offset);
void silenus_mmio_write32(AppleSilenusState *s, uint64_t offset, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_SILENUS_DMA_H */
