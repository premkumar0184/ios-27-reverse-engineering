/**
 * @file apple_prores_hw.c
 * @brief AppleProResHW / AVE2 Video Accelerator Hardware Model Implementation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#include "apple_prores_hw.h"
#include <string.h>

/* Simple hardware CRC32 implementation */
static uint32_t prores_calc_crc32(const uint8_t *data, size_t length) {
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < length; i++) {
        crc ^= (uint32_t)data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1U) {
                crc = (crc >> 1U) ^ 0xEDB88320U;
            } else {
                crc >>= 1U;
            }
        }
    }
    return ~crc;
}

void prores_hw_init(AppleProResHWState *s, const char *name, AppleAICState *aic, AppleDARTState *dart) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    s->name = name ? name : "apple_prores_hw";
    s->aic = aic;
    s->dart = dart;
    s->m0_status = 0x00000001U; /* Ready */
    s->a1_status = 0x00000001U; /* Core A1 idle/ready */
    s->a2_status = 0x00000001U; /* Core A2 idle/ready */
}

bool prores_hw_encode_raw_frame(AppleProResHWState *s,
                                const sAppleProResRawFrameHeader_t *header,
                                const uint8_t *input_bayer,
                                uint8_t *output_bitstream,
                                size_t max_output_size,
                                size_t *out_encoded_bytes) {
    if (!s || !header || !output_bitstream || max_output_size < 256) {
        return false;
    }

    /* 1. Header Validation */
    if (header->size != sizeof(sAppleProResRawFrameHeader_t) ||
        header->hsize == 0 || header->vsize == 0) {
        return false;
    }

    if (header->cfa > APR_CFA_PATTERN_GBRG) {
        return false;
    }

    memcpy(&s->last_frame_header, header, sizeof(*header));
    s->header_valid = true;

    /* 2. Dual-Core Slice Encoding Simulation */
    /* Core A1: Slices 0..7 (Upper Frame) */
    s->a1_status = 0x00000002U; /* Busy encoding */
    s->total_a1_slices += PRORES_CORE_A1_SLICES;

    /* Core A2: Slices 8..15 (Lower Frame) */
    s->a2_status = 0x00000002U; /* Busy encoding */
    s->total_a2_slices += PRORES_CORE_A2_SLICES;

    s->total_slices_processed += PRORES_NUM_SLICES;
    s->total_frames_encoded++;

    /* 3. Bitstream Generation & Hardware CRC Calculation */
    memset(output_bitstream, 0, (max_output_size < 256) ? max_output_size : 256);
    uint32_t *out_words = (uint32_t *)output_bitstream;
    out_words[0] = 0x7072386BU; /* 'pr8k' ProRes 8K RAW Magic */
    out_words[1] = header->id;
    out_words[2] = header->hsize;
    out_words[3] = header->vsize;
    out_words[4] = header->cfa;
    out_words[5] = header->wbr;
    out_words[6] = header->wbb;
    out_words[7] = PRORES_NUM_SLICES;

    /* Fill mock compressed payload */
    size_t payload_bytes = 256;
    if (input_bayer) {
        /* Incorporate sample bytes into output */
        size_t copy_len = (max_output_size > 512) ? 128 : (max_output_size - 128);
        memcpy(output_bitstream + 64, input_bayer, copy_len);
        payload_bytes += copy_len;
    }

    s->computed_crc = prores_calc_crc32(output_bitstream, 64);
    out_words[8] = s->computed_crc;

    if (out_encoded_bytes) {
        *out_encoded_bytes = payload_bytes;
    }
    s->total_bytes_encoded += payload_bytes;

    s->a1_status = 0x00000001U; /* Ready */
    s->a2_status = 0x00000001U; /* Ready */

    /* 4. Fire AIC IRQ 256 (AIC_IRQ_PRORES_COMPLETE) */
    if (s->aic) {
        aic_set_irq(s->aic, AIC_IRQ_PRORES_COMPLETE, 1);
    }

    return true;
}

uint32_t prores_hw_mmio_read32(AppleProResHWState *s, uint64_t offset) {
    if (!s) return 0;

    switch (offset) {
        case APR_CORE_M0_OFFSET:
            return s->m0_control;
        case APR_CORE_M0_OFFSET + 0x04:
            return s->m0_status;
        case APR_CORE_A1_OFFSET:
            return s->a1_control;
        case APR_CORE_A1_OFFSET + 0x04:
            return s->a1_status;
        case APR_CORE_A2_OFFSET:
            return s->a2_control;
        case APR_CORE_A2_OFFSET + 0x04:
            return s->a2_status;
        case 0x100:
            return (uint32_t)s->total_frames_encoded;
        case 0x104:
            return s->computed_crc;
        default:
            return 0;
    }
}

void prores_hw_mmio_write32(AppleProResHWState *s, uint64_t offset, uint32_t val) {
    if (!s) return;

    switch (offset) {
        case APR_CORE_M0_OFFSET:
            s->m0_control = val;
            break;
        case APR_CORE_A1_OFFSET:
            s->a1_control = val;
            break;
        case APR_CORE_A2_OFFSET:
            s->a2_control = val;
            break;
        default:
            break;
    }
}
