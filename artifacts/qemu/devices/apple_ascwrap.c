/**
 * @file apple_ascwrap.c
 * @brief Apple ASCwrap-v6 Mailbox & Doorbell Peripheral Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_ascwrap.h"
#include <string.h>

void ascwrap_init(AppleASCwrapState *s, const char *name, AppleAICState *aic,
                  uint32_t irq_inbox, uint32_t irq_outbox, uint32_t irq_doorbell) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name;
    s->aic = aic;
    s->irq_inbox = irq_inbox;
    s->irq_outbox = irq_outbox;
    s->irq_doorbell = irq_doorbell;
}

void ascwrap_set_coproc_handler(AppleASCwrapState *s,
                                void (*cb)(void *opaque, uint16_t ep, uint64_t payload),
                                void *opaque) {
    if (!s) return;
    s->coproc_recv_cb = cb;
    s->coproc_opaque = opaque;
}

uint32_t ascwrap_read32(AppleASCwrapState *s, uint64_t offset) {
    if (!s) return 0;

    switch (offset) {
        case ASCWRAP_REG_INBOX_CTRL:
            return s->inbox_ctrl | (s->inbox_count << 16);

        case ASCWRAP_REG_INBOX_DATA: {
            /* Low 32 bits of 64-bit inbox data */
            uint64_t msg = ascwrap_read64(s, offset);
            s->inbox_latched_hi = (uint32_t)((msg >> 32) & 0xFFFFFFFFULL);
            return (uint32_t)(msg & 0xFFFFFFFFULL);
        }

        case ASCWRAP_REG_INBOX_DATA + 4:
            /* High 32 bits (contains 16-bit Endpoint ID) */
            return s->inbox_latched_hi;

        case ASCWRAP_REG_OUTBOX_CTRL:
            return s->outbox_ctrl | (s->outbox_count << 16);

        case ASCWRAP_REG_STATUS: {
            uint32_t st = 0;
            if (s->inbox_count == 0)                      st |= ASCWRAP_STATUS_INBOX_EMPTY;
            if (s->inbox_count >= ASCWRAP_FIFO_CAPACITY)  st |= ASCWRAP_STATUS_INBOX_FULL;
            if (s->outbox_count == 0)                     st |= ASCWRAP_STATUS_OUTBOX_EMPTY;
            if (s->outbox_count >= ASCWRAP_FIFO_CAPACITY) st |= ASCWRAP_STATUS_OUTBOX_FULL;
            return st;
        }

        default:
            return 0;
    }
}

void ascwrap_write32(AppleASCwrapState *s, uint64_t offset, uint32_t val) {
    if (!s) return;

    switch (offset) {
        case ASCWRAP_REG_INBOX_CTRL:
            s->inbox_ctrl = val;
            break;

        case ASCWRAP_REG_OUTBOX_CTRL:
            s->outbox_ctrl = val;
            break;

        case ASCWRAP_REG_OUTBOX_DATA:
            /* Low 32 bits of outbox write - staged until high word written */
            s->outbox_latched_lo = val;
            s->outbox_lo_valid = true;
            break;

        case ASCWRAP_REG_OUTBOX_DATA + 4: {
            /* High 32 bits written - assemble 64-bit message and send */
            uint64_t lo = s->outbox_lo_valid ? (uint64_t)s->outbox_latched_lo : 0ULL;
            uint64_t full_msg = ((uint64_t)val << 32) | lo;
            s->outbox_lo_valid = false;
            ascwrap_write64(s, ASCWRAP_REG_OUTBOX_DATA, full_msg);
            break;
        }

        default:
            break;
    }
}

uint64_t ascwrap_read64(AppleASCwrapState *s, uint64_t offset) {
    if (!s) return 0;

    if (offset == ASCWRAP_REG_INBOX_DATA) {
        if (s->inbox_count == 0) {
            return 0;
        }
        uint64_t msg = s->inbox_fifo[s->inbox_head];
        s->inbox_head = (s->inbox_head + 1U) % ASCWRAP_FIFO_CAPACITY;
        s->inbox_count--;

        /* If inbox is now empty, lower the inbox interrupt line */
        if (s->inbox_count == 0 && s->aic) {
            aic_set_irq(s->aic, s->irq_inbox, 0);
        }
        return msg;
    }

    return (uint64_t)ascwrap_read32(s, offset);
}

void ascwrap_write64(AppleASCwrapState *s, uint64_t offset, uint64_t val) {
    if (!s) return;

    if (offset == ASCWRAP_REG_OUTBOX_DATA) {
        if (s->outbox_count >= ASCWRAP_FIFO_CAPACITY) {
            return; /* Outbox FIFO full */
        }
        s->outbox_fifo[s->outbox_tail] = val;
        s->outbox_tail = (s->outbox_tail + 1U) % ASCWRAP_FIFO_CAPACITY;
        s->outbox_count++;
        s->total_msgs_sent_to_coproc++;

        /* If a coprocessor callback is installed, notify immediately */
        if (s->coproc_recv_cb) {
            uint16_t ep = ascwrap_msg_get_ep(val);
            uint64_t payload = ascwrap_msg_get_payload(val);
            s->coproc_recv_cb(s->coproc_opaque, ep, payload);
        }
    } else {
        ascwrap_write32(s, offset, (uint32_t)(val & 0xFFFFFFFFULL));
    }
}

uint32_t ascwrap_doorbell_read32(AppleASCwrapState *s, uint64_t offset) {
    if (!s) return 0;
    if (offset == DOORBELL_REG_STATUS) {
        return s->doorbell_status;
    }
    return 0;
}

void ascwrap_doorbell_write32(AppleASCwrapState *s, uint64_t offset, uint32_t val) {
    if (!s) return;

    if (offset == DOORBELL_REG_SET) {
        s->doorbell_status |= val;
        s->total_doorbells_kicked++;
        if (s->doorbell_status != 0 && s->aic) {
            aic_set_irq(s->aic, s->irq_doorbell, 1);
        }
    } else if (offset == DOORBELL_REG_CLEAR) {
        s->doorbell_status &= ~val;
        if (s->doorbell_status == 0) {
            if (s->aic) aic_set_irq(s->aic, s->irq_doorbell, 0);
        } else {
            if (s->aic) aic_set_irq(s->aic, s->irq_doorbell, 1);
        }
    }
}

bool ascwrap_coproc_send(AppleASCwrapState *s, uint16_t ep, uint64_t payload) {
    if (!s) return false;
    if (s->inbox_count >= ASCWRAP_FIFO_CAPACITY) {
        return false;
    }

    uint64_t msg = ascwrap_msg_compose(ep, payload);
    s->inbox_fifo[s->inbox_tail] = msg;
    s->inbox_tail = (s->inbox_tail + 1U) % ASCWRAP_FIFO_CAPACITY;
    s->inbox_count++;
    s->total_msgs_recv_from_coproc++;

    /* Assert host inbox IRQ */
    if (s->aic) {
        aic_set_irq(s->aic, s->irq_inbox, 1);
    }
    return true;
}

bool ascwrap_coproc_recv(AppleASCwrapState *s, uint16_t *out_ep, uint64_t *out_payload) {
    if (!s || s->outbox_count == 0) return false;

    uint64_t msg = s->outbox_fifo[s->outbox_head];
    s->outbox_head = (s->outbox_head + 1U) % ASCWRAP_FIFO_CAPACITY;
    s->outbox_count--;

    if (out_ep) {
        *out_ep = ascwrap_msg_get_ep(msg);
    }
    if (out_payload) {
        *out_payload = ascwrap_msg_get_payload(msg);
    }
    return true;
}

void ascwrap_coproc_ring_doorbell(AppleASCwrapState *s, uint32_t bit) {
    if (!s) return;
    s->doorbell_status |= bit;
    s->total_doorbells_kicked++;
    if (s->aic) {
        aic_set_irq(s->aic, s->irq_doorbell, 1);
    }
}
