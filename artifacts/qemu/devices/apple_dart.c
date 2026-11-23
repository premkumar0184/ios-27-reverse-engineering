/**
 * @file apple_dart.c
 * @brief Apple DART Gen3/Gen4 IOMMU Emulation Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_dart.h"
#include <string.h>

void dart_init(AppleDARTState *s, const char *name, AppleAICState *aic, uint32_t irq_fault) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name;
    s->aic = aic;
    s->irq_fault = irq_fault;
    s->config = DART_CONFIG_ENABLE;
}

bool dart_map(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t pa, uint64_t size, uint32_t perm) {
    if (!s || sid >= DART_MAX_STREAMS || size == 0) return false;

    AppleDARTStream *st = &s->streams[sid];
    /* Find existing matching or first free entry */
    int free_idx = -1;
    for (uint32_t i = 0; i < DART_MAX_MAP_ENTRIES; i++) {
        if (st->mappings[i].valid && st->mappings[i].dva_start == dva) {
            free_idx = (int)i;
            break;
        }
        if (!st->mappings[i].valid && free_idx < 0) {
            free_idx = (int)i;
        }
    }

    if (free_idx < 0) return false;

    st->mappings[free_idx].dva_start = dva;
    st->mappings[free_idx].pa_start = pa;
    st->mappings[free_idx].size = size;
    st->mappings[free_idx].perm = perm;
    st->mappings[free_idx].valid = true;
    st->enabled = true;
    if (free_idx >= (int)st->num_mappings) {
        st->num_mappings = (uint32_t)free_idx + 1U;
    }

    return true;
}

bool dart_unmap(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t size) {
    if (!s || sid >= DART_MAX_STREAMS) return false;

    AppleDARTStream *st = &s->streams[sid];
    bool unmapped = false;

    for (uint32_t i = 0; i < st->num_mappings; i++) {
        if (st->mappings[i].valid &&
            st->mappings[i].dva_start >= dva &&
            (st->mappings[i].dva_start + st->mappings[i].size) <= (dva + size)) {
            st->mappings[i].valid = false;
            unmapped = true;
        }
    }

    return unmapped;
}

bool dart_translate(AppleDARTState *s, uint32_t sid, uint64_t dva, uint64_t *out_pa, uint32_t perm) {
    if (!s || !out_pa) return false;

    /* Handle bypass mode */
    if (s->config & DART_CONFIG_BYPASS) {
        *out_pa = dva;
        s->total_translations++;
        return true;
    }

    /* Check global enable */
    if (!(s->config & DART_CONFIG_ENABLE) || sid >= DART_MAX_STREAMS) {
        s->fault_status = DART_FAULT_FLAG | 0x01U;
        s->fault_addr = dva;
        s->fault_sid = sid;
        s->total_faults++;
        if (s->aic) aic_set_irq(s->aic, s->irq_fault, 1);
        return false;
    }

    AppleDARTStream *st = &s->streams[sid];
    if (!st->enabled) {
        s->fault_status = DART_FAULT_FLAG | 0x01U; /* Stream disabled fault */
        s->fault_addr = dva;
        s->fault_sid = sid;
        s->total_faults++;
        if (s->aic) aic_set_irq(s->aic, s->irq_fault, 1);
        return false;
    }

    for (uint32_t i = 0; i < st->num_mappings; i++) {
        AppleDARTMapEntry *e = &st->mappings[i];
        if (e->valid && dva >= e->dva_start && dva < (e->dva_start + e->size)) {
            /* Check permissions */
            if ((e->perm & perm) != perm) {
                s->fault_status = DART_FAULT_FLAG | 0x02U; /* Permission fault */
                s->fault_addr = dva;
                s->fault_sid = sid;
                s->total_faults++;
                if (s->aic) aic_set_irq(s->aic, s->irq_fault, 1);
                return false;
            }
            uint64_t offset = dva - e->dva_start;
            *out_pa = e->pa_start + offset;
            s->total_translations++;
            return true;
        }
    }

    /* Translation fault (unmapped address) */
    s->fault_status = DART_FAULT_FLAG | 0x04U;
    s->fault_addr = dva;
    s->fault_sid = sid;
    s->total_faults++;
    if (s->aic) aic_set_irq(s->aic, s->irq_fault, 1);
    return false;
}

uint32_t dart_read32(AppleDARTState *s, uint64_t offset) {
    if (!s) return 0;

    switch (offset) {
        case DART_REG_CONFIG:
            return s->config;
        case DART_REG_FAULT_STATUS:
            return s->fault_status;
        case DART_REG_FAULT_ADDR_LO:
            return (uint32_t)(s->fault_addr & 0xFFFFFFFFULL);
        case DART_REG_FAULT_ADDR_HI:
            return (uint32_t)((s->fault_addr >> 32) & 0xFFFFFFFFULL);
        case DART_REG_FAULT_SID:
            return s->fault_sid;
        default:
            if (offset >= DART_REG_TTBR_BASE(0) && offset < DART_REG_TTBR_BASE(DART_MAX_STREAMS)) {
                uint32_t sid = (uint32_t)(offset - DART_REG_TTBR_BASE(0)) / 4U;
                return s->streams[sid].ttbr;
            }
            return 0;
    }
}

void dart_write32(AppleDARTState *s, uint64_t offset, uint32_t val) {
    if (!s) return;

    switch (offset) {
        case DART_REG_CONFIG:
            s->config = val;
            break;
        case DART_REG_TLB_INVAL:
            s->total_tlb_invals++;
            break;
        case DART_REG_FAULT_STATUS:
            /* W1C to clear fault status */
            s->fault_status &= ~val;
            if (s->fault_status == 0 && s->aic) {
                aic_set_irq(s->aic, s->irq_fault, 0);
            }
            break;
        default:
            if (offset >= DART_REG_TTBR_BASE(0) && offset < DART_REG_TTBR_BASE(DART_MAX_STREAMS)) {
                uint32_t sid = (uint32_t)(offset - DART_REG_TTBR_BASE(0)) / 4U;
                s->streams[sid].ttbr = val;
                s->streams[sid].enabled = true;
            }
            break;
    }
}
