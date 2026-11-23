/**
 * @file apple_ascwrap.h
 * @brief Apple ASCwrap-v6 Mailbox & Doorbell Peripheral Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_ASCWRAP_H
#define APPLE_ASCWRAP_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASCWRAP_FIFO_CAPACITY               64U

typedef struct AppleASCwrapState {
    const char     *name;
    AppleAICState  *aic;
    uint32_t        irq_inbox;
    uint32_t        irq_outbox;
    uint32_t        irq_doorbell;

    /* Host Inbox FIFO (Coprocessor -> Host) */
    uint64_t        inbox_fifo[ASCWRAP_FIFO_CAPACITY];
    uint32_t        inbox_head;
    uint32_t        inbox_tail;
    uint32_t        inbox_count;
    uint32_t        inbox_ctrl;

    /* Host Outbox FIFO (Host -> Coprocessor) */
    uint64_t        outbox_fifo[ASCWRAP_FIFO_CAPACITY];
    uint32_t        outbox_head;
    uint32_t        outbox_tail;
    uint32_t        outbox_count;
    uint32_t        outbox_ctrl;

    /* Doorbell registers */
    uint32_t        doorbell_status;

    /* 32-bit MMIO staging latches */
    uint32_t        inbox_latched_hi;
    uint32_t        outbox_latched_lo;
    bool            outbox_lo_valid;

    /* Coprocessor hook / callback */
    void (*coproc_recv_cb)(void *opaque, uint16_t ep, uint64_t payload);
    void *coproc_opaque;

    /* Statistics */
    uint64_t        total_msgs_sent_to_coproc;
    uint64_t        total_msgs_recv_from_coproc;
    uint64_t        total_doorbells_kicked;
} AppleASCwrapState;

void ascwrap_init(AppleASCwrapState *s, const char *name, AppleAICState *aic,
                  uint32_t irq_inbox, uint32_t irq_outbox, uint32_t irq_doorbell);

void ascwrap_set_coproc_handler(AppleASCwrapState *s,
                                void (*cb)(void *opaque, uint16_t ep, uint64_t payload),
                                void *opaque);

/* Host Interface (MMIO reads/writes from Host CPU) */
uint32_t ascwrap_read32(AppleASCwrapState *s, uint64_t offset);
void ascwrap_write32(AppleASCwrapState *s, uint64_t offset, uint32_t val);
uint64_t ascwrap_read64(AppleASCwrapState *s, uint64_t offset);
void ascwrap_write64(AppleASCwrapState *s, uint64_t offset, uint64_t val);

/* Doorbell MMIO */
uint32_t ascwrap_doorbell_read32(AppleASCwrapState *s, uint64_t offset);
void ascwrap_doorbell_write32(AppleASCwrapState *s, uint64_t offset, uint32_t val);

/* Coprocessor Interface (Called by Stub RTKit Coprocessor) */
bool ascwrap_coproc_send(AppleASCwrapState *s, uint16_t ep, uint64_t payload);
bool ascwrap_coproc_recv(AppleASCwrapState *s, uint16_t *out_ep, uint64_t *out_payload);
void ascwrap_coproc_ring_doorbell(AppleASCwrapState *s, uint32_t bit);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_ASCWRAP_H */
