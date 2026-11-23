/**
 * @file apple_agx_direct.c
 * @brief Apple AGX G18 Pro / AppleMetalDirect Hardware Emulation Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_agx_direct.h"
#include <string.h>

void agx_direct_init(AppleAGXState *s, const char *name, AppleAICState *aic,
                     AppleASCwrapState *ascwrap, AppleDARTState *dart) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name ? name : "agx_g18p";
    s->aic = aic;
    s->ascwrap = ascwrap;
    s->dart = dart;
    s->gpu_status = 0x00000001U; /* Powered on, ready */
}

void agx_direct_attach_buffers(AppleAGXState *s,
                               struct agx_ring_buffer *ring,
                               struct agx_status_page *status) {
    if (!s) return;
    s->ring_buffer = ring;
    s->status_page = status;
    s->current_read_index = 0;

    if (s->status_page) {
        memset((void *)s->status_page, 0, sizeof(*s->status_page));
        s->status_page->firmware_heartbeat = 1U;
        s->total_heartbeats = 1U;
    }
}

void agx_direct_process_descriptor(AppleAGXState *s, const struct agx_command_descriptor *desc) {
    if (!s || !desc) return;

    s->total_commands_processed++;
    uint8_t opcode = desc->hdr.bits.opcode;

    switch (opcode) {
        case AGX_CMD_3D_RENDER_PASS:
            s->total_renders++;
            break;
        case AGX_CMD_COMPUTE_DISPATCH:
            s->total_computes++;
            break;
        case AGX_CMD_BLIT_2D:
        case AGX_CMD_BLIT_COPY:
            s->total_blits++;
            break;
        default:
            break;
    }

    if (s->status_page) {
        s->status_page->firmware_heartbeat++;
        s->total_heartbeats++;
    }
}

void agx_direct_kick(AppleAGXState *s, uint16_t queue_id, uint32_t tail_offset, uint16_t flags) {
    if (!s) return;
    (void)queue_id;
    (void)flags;

    s->total_kicks++;
    uint32_t target_index = (tail_offset / sizeof(struct agx_command_descriptor)) & AGX_RING_INDEX_MASK;

    if (s->ring_buffer) {
        while (s->current_read_index != target_index) {
            const struct agx_command_descriptor *desc = &s->ring_buffer->entries[s->current_read_index];
            agx_direct_process_descriptor(s, desc);

            if (s->status_page) {
                uint32_t stamp = desc->stamp_token.stamp.stamp_value;
                if (stamp == 0) {
                    stamp = s->current_read_index + 1U;
                }
                s->status_page->completed_stamps[s->current_read_index] = stamp;
            }

            s->current_read_index = (s->current_read_index + 1U) & AGX_RING_INDEX_MASK;
        }

        if (s->status_page) {
            s->status_page->firmware_read_index = s->current_read_index;
            s->status_page->firmware_heartbeat++;
            s->total_heartbeats++;
        }
    }

    /* Assert completion interrupt via AIC Vector 952 / 954 */
    if (s->aic) {
        aic_set_irq(s->aic, AIC_IRQ_AGX_CORE0_INBOX, 1);
    }
    if (s->ascwrap) {
        ascwrap_coproc_ring_doorbell(s->ascwrap, 1U << 0);
    }
}

uint32_t agx_mmio_read32(AppleAGXState *s, uint64_t offset) {
    if (!s) return 0;
    switch (offset) {
        case 0x0000: return s->gpu_control;
        case 0x0004: return s->gpu_status;
        case 0x0010: return s->current_read_index;
        case 0x0014: return (uint32_t)s->total_commands_processed;
        default: return 0;
    }
}

void agx_mmio_write32(AppleAGXState *s, uint64_t offset, uint32_t val) {
    if (!s) return;
    switch (offset) {
        case 0x0000: s->gpu_control = val; break;
        case 0x0004: s->gpu_status = val; break;
        default: break;
    }
}

void agx_doorbell_write64(AppleAGXState *s, uint64_t offset, uint64_t val) {
    if (!s) return;
    (void)offset;
    s->doorbell_val = val;
    agx_doorbell_token_t token;
    token.raw_token = val;
    agx_direct_kick(s, token.fields.queue_id, token.fields.tail_offset, token.fields.flags);
}
