/**
 * @file apple_prores_hw.h
 * @brief AppleProResHW / AVE2 Video Accelerator Hardware Model
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

#ifndef APPLE_PRORES_EMU_HW_H
#define APPLE_PRORES_EMU_HW_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/apple_a19_platform.h"
#include "apple_aic.h"
#include "apple_dart.h"
#include "../../ave/include/apple_prores_hw.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PRORES_NUM_SLICES                   16U
#define PRORES_CORE_A1_SLICES               8U
#define PRORES_CORE_A2_SLICES               8U

typedef struct AppleProResHWState {
    const char           *name;
    AppleAICState        *aic;
    AppleDARTState       *dart;

    /* MMIO Registers */
    uint32_t              m0_control;
    uint32_t              m0_status;
    uint32_t              a1_control;
    uint32_t              a1_status;
    uint32_t              a2_control;
    uint32_t              a2_status;

    /* Current Frame Parameters */
    sAppleProResRawFrameHeader_t last_frame_header;
    uint32_t              computed_crc;
    bool                  header_valid;

    /* Telemetry */
    uint64_t              total_frames_encoded;
    uint64_t              total_slices_processed;
    uint64_t              total_a1_slices;
    uint64_t              total_a2_slices;
    uint64_t              total_bytes_encoded;
} AppleProResHWState;

void prores_hw_init(AppleProResHWState *s, const char *name, AppleAICState *aic, AppleDARTState *dart);

bool prores_hw_encode_raw_frame(AppleProResHWState *s,
                                const sAppleProResRawFrameHeader_t *header,
                                const uint8_t *input_bayer,
                                uint8_t *output_bitstream,
                                size_t max_output_size,
                                size_t *out_encoded_bytes);

uint32_t prores_hw_mmio_read32(AppleProResHWState *s, uint64_t offset);
void prores_hw_mmio_write32(AppleProResHWState *s, uint64_t offset, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_PRORES_EMU_HW_H */
