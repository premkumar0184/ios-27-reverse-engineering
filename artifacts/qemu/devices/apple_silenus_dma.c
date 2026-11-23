/**
 * @file apple_silenus_dma.c
 * @brief Silenus Camera ISP & Bayer Neural Interface (BNI) Hardware Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_silenus_dma.h"
#include <string.h>

void silenus_dma_init(AppleSilenusState *s, const char *name, AppleAICState *aic,
                      AppleASCwrapState *ascwrap, AppleDARTState *dart) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name ? name : "silenus_isp";
    s->aic = aic;
    s->ascwrap = ascwrap;
    s->dart = dart;
    s->sif_status = 0x00000001U; /* SIF PHY locked & streaming */
    s->isp_control = 0x00000001U;
}

void silenus_set_tz1s_buffer(AppleSilenusState *s, uint8_t *buf, size_t size) {
    if (!s) return;
    s->tz1s_target_buffer = buf;
    s->tz1s_buffer_size = size;
}

bool silenus_process_cisp_packet(AppleSilenusState *s, const struct cisp_command_packet *pkt) {
    if (!s || !pkt) return false;

    if (pkt->header.magic != CISP_MAGIC) {
        return false;
    }

    s->total_commands++;
    uint16_t opcode = pkt->header.opcode;

    if (opcode == CISP_CMD_PING) {
        return true;
    }

    if (opcode == CISP_CMD_CH_PROCESS_BUFFERS) {
        s->total_frames_processed++;
        s->frame_counter++;

        /* 1. DART translation checks for sensor input and display/preview output */
        if (s->dart) {
            uint64_t raw_pa = 0;
            bool ok_raw = dart_translate(s->dart, DART_ISP_SID_RAW_STREAM,
                                         pkt->payload.buffer_process.dva_luma, &raw_pa, DART_PERM_READ);

            uint64_t bni_pa = 0;
            bool ok_bni = dart_translate(s->dart, DART_ISP_SID_BNI_PEARL,
                                         A19_SEP_TZ1S_BASE, &bni_pa, DART_PERM_WRITE);

            uint64_t preview_pa = 0;
            bool ok_prev = dart_translate(s->dart, DART_ISP_SID_YUV_PREVIEW,
                                          pkt->payload.buffer_process.dva_chroma, &preview_pa, DART_PERM_WRITE);

            if (!ok_raw || !ok_bni || !ok_prev) {
                if (s->aic) {
                    aic_set_irq(s->aic, AIC_IRQ_ISP_DMA_ERROR, 1);
                }
                return false;
            }
        }

        /* 2. Route BNI FaceID NIR data directly to SEP TZ1S */
        if (s->tz1s_target_buffer && s->tz1s_buffer_size >= 64) {
            /* Write FaceID NIR frame descriptor token into TZ1S sink */
            uint32_t *tz1s_hdr = (uint32_t *)s->tz1s_target_buffer;
            tz1s_hdr[0] = 0x4E495230; /* 'NIR0' Magic */
            tz1s_hdr[1] = s->frame_counter;
            tz1s_hdr[2] = pkt->payload.buffer_process.width;
            tz1s_hdr[3] = pkt->payload.buffer_process.height;
            s->total_bni_packets_routed++;
        }

        /* 3. 3A Statistics Engine */
        s->total_3a_stats_generated++;

        /* 4. Trigger Interrupts */
        if (s->aic) {
            aic_set_irq(s->aic, AIC_IRQ_ISP_FRAME_DONE, 1);
            aic_set_irq(s->aic, AIC_IRQ_ISP_STATS_READY, 1);
        }

        if (s->ascwrap) {
            ascwrap_coproc_ring_doorbell(s->ascwrap, 1U << 1);
        }

        return true;
    }

    return true;
}

uint32_t silenus_mmio_read32(AppleSilenusState *s, uint64_t offset) {
    if (!s) return 0;
    switch (offset) {
        case 0x0000: return s->isp_control;
        case 0x0004: return s->sif_status;
        case 0x0010: return s->frame_counter;
        case 0x0014: return (uint32_t)s->total_frames_processed;
        default: return 0;
    }
}

void silenus_mmio_write32(AppleSilenusState *s, uint64_t offset, uint32_t val) {
    if (!s) return;
    switch (offset) {
        case 0x0000: s->isp_control = val; break;
        case 0x0004: s->sif_status = val; break;
        default: break;
    }
}
