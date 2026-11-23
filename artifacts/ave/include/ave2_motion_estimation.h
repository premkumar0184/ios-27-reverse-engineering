#ifndef AVE2_MOTION_ESTIMATION_H
#define AVE2_MOTION_ESTIMATION_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// AVE2 Coprocessor Hardware MMIO Register Offsets
#define AVE2_MMIO_BASE                  0x77020000ULL

#define AVE2_REG_HMESC_SRC_ADDR         0x00010100ULL
#define AVE2_REG_HMESC_SRC_STRIDE       0x00010108ULL
#define AVE2_REG_HMESC_HDR_ADDR         0x00010110ULL
#define AVE2_REG_HMESC_CMP_ADDR         0x00010118ULL
#define AVE2_REG_HMESC_CTRL_START       0x00010120ULL
#define AVE2_REG_HMESC_STATUS_DONE      0x00010124ULL

#define AVE2_REG_LRME_SRC_ADDR          0x00020100ULL
#define AVE2_REG_LRME_REF_ADDR          0x00020108ULL
#define AVE2_REG_LRME_PRV_RSLTS_ADDR    0x00020110ULL
#define AVE2_REG_LRME_MV_OUT_ADDR       0x00020118ULL
#define AVE2_REG_LRME_CTRL_GO           0x00020120ULL

#define AVE2_REG_DMV_CTRL_START         0x00030100ULL
#define AVE2_REG_DMV_STATUS_DONE        0x00030104ULL
#define AVE2_REG_DMV_MV_DENSITY_CFG     0x00030108ULL

#define AVE2_REG_MCTF_REF_COUNT         0x00040100ULL
#define AVE2_REG_MCTF_FILTER_GATING     0x00040104ULL
#define AVE2_REG_MCTF_STRENGTH_LUT_BASE 0x00040110ULL

// Low-Resolution Motion Vector (16:1 downsampled luma)
typedef struct sAveLrmeMotionVector {
    int16_t mvX;                        // Horizontal displacement in integer pel [-128, +127]
    int16_t mvY;                        // Vertical displacement in integer pel [-64, +63]
    uint16_t sadCost;                   // Sum of Absolute Differences match cost
    uint16_t flags;                     // Intraprediction / early-skip flags
} sAveLrmeMotionVector_t;

// Dense Motion Vector (Quarter-pel precision)
typedef struct sAveDmvMotionVector {
    int16_t qpelMvX;                    // Quarter-pel horizontal vector (1/4 pel resolution)
    int16_t qpelMvY;                    // Quarter-pel vertical vector (1/4 pel resolution)
    uint32_t rdoCost;                   // Lagrangian rate-distortion cost metric
} sAveDmvMotionVector_t;

// Hierarchical Motion Estimation and Spatial Complexity descriptor
typedef struct sAveHmescContext {
    uint64_t srcPixelAddr;
    uint32_t srcStride;
    uint32_t isCompressedInput;
    uint64_t cmpHdrAddr;
    uint64_t cmpPayloadAddr;
    uint32_t cmpStride;
    uint32_t spatialVarianceH;
    uint32_t spatialVarianceV;
    uint32_t spatialVarianceD45;
    uint32_t spatialVarianceD135;
} sAveHmescContext_t;

// MCTF Reference Frame Management descriptor
typedef struct sAveMctfFrameDescriptor {
    uint32_t frameId;
    uint32_t isFutureReference;
    uint64_t lfsRefBufferAddr;
    uint64_t mctfOutputBufferAddr;
    uint32_t filterStrength;
    uint32_t motionTrajectoryConfidence;
} sAveMctfFrameDescriptor_t;

#ifdef __cplusplus
}
#endif

#endif // AVE2_MOTION_ESTIMATION_H
