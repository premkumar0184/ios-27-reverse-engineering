/**
 * @file apple_aic.h
 * @brief Apple Interrupt Controller (AIC v3/v4) Emulation Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_AIC_H
#define APPLE_AIC_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"

#ifdef __cplusplus
extern "C" {
#endif

#define AIC_REG_INFO                        0x0000U
#define AIC_REG_WHOAMI                      0x0004U
#define AIC_REG_EVENT                       0x0010U
#define AIC_REG_MASK_SET_BASE               0x0100U
#define AIC_REG_MASK_CLR_BASE               0x0180U
#define AIC_REG_PENDING_BASE                0x0200U
#define AIC_REG_TARGET_BASE                 0x0400U

typedef struct AppleAICState {
    uint32_t pending[32];   /* 32 * 32 = 1024 interrupt lines */
    uint32_t mask[32];      /* 1 = masked, 0 = enabled        */
    uint8_t  target[1024];  /* Affinity CPU ID per vector      */
    uint32_t active_vector; /* Currently serviced vector       */
    bool     fiq_asserted;  /* FIQ line status to CPU core     */
    bool     irq_asserted;  /* IRQ line status to CPU core     */
    uint64_t total_irqs_raised;
    uint64_t total_irqs_acked;
} AppleAICState;

void aic_init(AppleAICState *s);
void aic_set_irq(AppleAICState *s, uint32_t irq, int level);
uint32_t aic_get_pending_irq(AppleAICState *s);
void aic_ack_irq(AppleAICState *s, uint32_t irq);

uint32_t aic_read32(AppleAICState *s, uint64_t offset);
void aic_write32(AppleAICState *s, uint64_t offset, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_AIC_H */
