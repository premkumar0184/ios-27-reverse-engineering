/**
 * @file apple_aic.c
 * @brief Apple Interrupt Controller (AIC v3/v4) Emulation Model Implementation
 */

#include "apple_aic.h"
#include <string.h>

void aic_init(AppleAICState *s) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    /* By default, all interrupts are unmasked */
    for (int i = 0; i < 32; i++) {
        s->mask[i] = 0x00000000U;
    }
}

void aic_set_irq(AppleAICState *s, uint32_t irq, int level) {
    if (!s || irq >= AIC_MAX_IRQ) return;

    uint32_t idx = irq / 32U;
    uint32_t bit = 1U << (irq % 32U);

    if (level) {
        s->pending[idx] |= bit;
        s->total_irqs_raised++;
    } else {
        s->pending[idx] &= ~bit;
    }

    /* Check if any unmasked interrupt is pending */
    uint32_t pending_vector = aic_get_pending_irq(s);
    if (pending_vector != 0) {
        s->irq_asserted = true;
    } else {
        s->irq_asserted = false;
    }
}

uint32_t aic_get_pending_irq(AppleAICState *s) {
    if (!s) return 0;
    for (uint32_t idx = 0; idx < 32; idx++) {
        uint32_t unmasked = s->pending[idx] & (~s->mask[idx]);
        if (unmasked != 0) {
            for (uint32_t b = 0; b < 32; b++) {
                if (unmasked & (1U << b)) {
                    return (idx * 32U) + b;
                }
            }
        }
    }
    return 0;
}

void aic_ack_irq(AppleAICState *s, uint32_t irq) {
    if (!s || irq >= AIC_MAX_IRQ) return;
    uint32_t idx = irq / 32U;
    uint32_t bit = 1U << (irq % 32U);
    s->pending[idx] &= ~bit;
    s->total_irqs_acked++;

    if (aic_get_pending_irq(s) == 0) {
        s->irq_asserted = false;
    }
}

uint32_t aic_read32(AppleAICState *s, uint64_t offset) {
    if (!s) return 0;

    if (offset == AIC_REG_INFO) {
        return (4U << 24) | AIC_MAX_IRQ; /* Version 4, 1024 IRQs */
    }
    if (offset == AIC_REG_WHOAMI) {
        return 0; /* Boot core ID 0 */
    }
    if (offset == AIC_REG_EVENT) {
        uint32_t p = aic_get_pending_irq(s);
        if (p != 0) {
            aic_ack_irq(s, p);
        }
        return p;
    }

    if (offset >= AIC_REG_PENDING_BASE && offset < AIC_REG_PENDING_BASE + (32 * 4)) {
        uint32_t idx = (uint32_t)(offset - AIC_REG_PENDING_BASE) / 4U;
        return s->pending[idx];
    }

    if (offset >= AIC_REG_TARGET_BASE && offset < AIC_REG_TARGET_BASE + AIC_MAX_IRQ) {
        uint32_t irq = (uint32_t)(offset - AIC_REG_TARGET_BASE);
        return s->target[irq];
    }

    return 0;
}

void aic_write32(AppleAICState *s, uint64_t offset, uint32_t val) {
    if (!s) return;

    if (offset >= AIC_REG_MASK_SET_BASE && offset < AIC_REG_MASK_SET_BASE + (32 * 4)) {
        uint32_t idx = (uint32_t)(offset - AIC_REG_MASK_SET_BASE) / 4U;
        s->mask[idx] |= val;
        return;
    }

    if (offset >= AIC_REG_MASK_CLR_BASE && offset < AIC_REG_MASK_CLR_BASE + (32 * 4)) {
        uint32_t idx = (uint32_t)(offset - AIC_REG_MASK_CLR_BASE) / 4U;
        s->mask[idx] &= ~val;
        return;
    }

    if (offset >= AIC_REG_TARGET_BASE && offset < AIC_REG_TARGET_BASE + AIC_MAX_IRQ) {
        uint32_t irq = (uint32_t)(offset - AIC_REG_TARGET_BASE);
        s->target[irq] = (uint8_t)(val & 0xFF);
        return;
    }
}
