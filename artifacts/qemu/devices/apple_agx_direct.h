/**
 * @file apple_agx_direct.h
 * @brief Apple AGX G18 Pro / AppleMetalDirect Hardware Emulation Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_AGX_DIRECT_H
#define APPLE_AGX_DIRECT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"
#include "apple_ascwrap.h"
#include "apple_dart.h"
#include "../../gpu/driver/agx_host_interface.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct AppleAGXState {
    const char             *name;
    AppleAICState          *aic;
    AppleASCwrapState      *ascwrap;
    AppleDARTState         *dart;

    /* Attached memory / ring buffer pointers */
    struct agx_ring_buffer *ring_buffer;
    struct agx_status_page *status_page;
    uint32_t                current_read_index;

    /* MMIO Registers */
    uint32_t                gpu_control;
    uint32_t                gpu_status;
    uint64_t                doorbell_val;

    /* Telemetry Counters */
    uint64_t                total_kicks;
    uint64_t                total_commands_processed;
    uint64_t                total_renders;
    uint64_t                total_computes;
    uint64_t                total_blits;
    uint64_t                total_heartbeats;
} AppleAGXState;

void agx_direct_init(AppleAGXState *s, const char *name, AppleAICState *aic,
                     AppleASCwrapState *ascwrap, AppleDARTState *dart);

void agx_direct_attach_buffers(AppleAGXState *s,
                               struct agx_ring_buffer *ring,
                               struct agx_status_page *status);

void agx_direct_process_descriptor(AppleAGXState *s, const struct agx_command_descriptor *desc);
void agx_direct_kick(AppleAGXState *s, uint16_t queue_id, uint32_t tail_offset, uint16_t flags);

uint32_t agx_mmio_read32(AppleAGXState *s, uint64_t offset);
void agx_mmio_write32(AppleAGXState *s, uint64_t offset, uint32_t val);
void agx_doorbell_write64(AppleAGXState *s, uint64_t offset, uint64_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_AGX_DIRECT_H */
