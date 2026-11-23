/**
 * @file apple_dart.h
 * @brief Apple DART Gen3/Gen4 IOMMU Emulation Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_DART_H
#define APPLE_DART_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"

#ifdef __cplusplus
extern "C" {
#endif

#define DART_MAX_MAP_ENTRIES                1024U
#define DART_PERM_READ                      (1U << 0)
#define DART_PERM_WRITE                     (1U << 1)

typedef struct AppleDARTMapEntry {
    uint64_t dva_start;
    uint64_t pa_start;
    uint64_t size;
    uint32_t perm;
    bool     valid;
} AppleDARTMapEntry;

typedef struct AppleDARTStream {
    uint32_t ttbr;
    bool     enabled;
    AppleDARTMapEntry mappings[DART_MAX_MAP_ENTRIES];
    uint32_t num_mappings;
} AppleDARTStream;

typedef struct AppleDARTState {
    const char       *name;
    AppleAICState    *aic;
    uint32_t          irq_fault;
    uint32_t          config;
    uint32_t          fault_status;
    uint64_t          fault_addr;
    uint32_t          fault_sid;

    AppleDARTStream   streams[DART_MAX_STREAMS];

    /* Telemetry */
    uint64_t          total_translations;
    uint64_t          total_faults;
    uint64_t          total_tlb_invals;
} AppleDARTState;

void dart_init(AppleDARTState *s, const char *name, AppleAICState *aic, uint32_t irq_fault);
bool dart_map(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t pa, uint64_t size, uint32_t perm);
bool dart_unmap(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t size);
bool dart_translate(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t *out_pa, uint32_t perm);

uint32_t dart_read32(AppleDARTState *s, uint64_t offset);
void dart_write32(AppleDARTState *s, uint64_t offset, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_DART_H */
