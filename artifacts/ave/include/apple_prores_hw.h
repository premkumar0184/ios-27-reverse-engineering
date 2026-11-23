#ifndef APPLE_PRORES_HW_H
#define APPLE_PRORES_HW_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Base MMIO Address for AppleProResHW Accelerator (A19 Pro t8150)
#define APR_HW_MMIO_BASE                0x77080000ULL
#define APR_HW_MMIO_SIZE                0x00040000ULL

// Core offsets
#define APR_CORE_M0_OFFSET              0x00000000ULL
#define APR_CORE_A1_OFFSET              0x00010000ULL
#define APR_CORE_A2_OFFSET              0x00020000ULL

// Codec formats supported by AppleProResHW
typedef enum eAppleProResCodecFormat {
    APR_CODEC_PRORES_422_PROXY          = 0,
    APR_CODEC_PRORES_422_LT             = 1,
    APR_CODEC_PRORES_422_STANDARD       = 2,
    APR_CODEC_PRORES_422_HQ             = 3,
    APR_CODEC_PRORES_4444               = 4,
    APR_CODEC_PRORES_4444_XQ            = 5,
    APR_CODEC_PRORES_RAW                = 6,
    APR_CODEC_PRORES_RAW_HQ             = 7
} eAppleProResCodecFormat_t;

// Color Filter Array (CFA) Bayer patterns for ProRes RAW
typedef enum eAppleProResCfaPattern {
    APR_CFA_PATTERN_RGGB                = 0,
    APR_CFA_PATTERN_BGGR                = 1,
    APR_CFA_PATTERN_GRBG                = 2,
    APR_CFA_PATTERN_GBRG                = 3
} eAppleProResCfaPattern_t;

// ProRes RAW FrameHeader metadata packet layout (128 bytes)
typedef struct __attribute__((aligned(8))) sAppleProResRawFrameHeader {
    uint32_t size;                      // +0x00: Total packet byte size
    uint32_t ver;                       // +0x04: Format version
    uint32_t id;                        // +0x08: Sequential frame ID
    uint32_t hsize;                     // +0x0C: Active width (e.g., 8192)
    uint32_t vsize;                     // +0x10: Active height (e.g., 4320)
    uint32_t crop[4];                   // +0x14: Sensor crop rect [left, top, right, bottom]
    uint32_t cfa;                       // +0x24: CFA Bayer pattern enum
    uint32_t svr;                       // +0x28: Sensor vendor revision tag
    uint32_t wbr;                       // +0x2C: White balance Red gain (Q16.16)
    uint32_t wbb;                       // +0x30: White balance Blue gain (Q16.16)
    uint32_t cm[9];                     // +0x34: 3x3 Color Matrix coefficients
    uint32_t gf;                        // +0x58: Global flags
    uint32_t wbcct;                     // +0x5C: White balance CCT (Kelvin)
    uint32_t hme;                       // +0x60: HDR metadata extension enable
    uint32_t ltf;                       // +0x64: Look-up table flag
    uint32_t dss;                       // +0x68: Demosaic suggestion strength
    uint32_t lqm;                       // +0x6C: Load quantization matrix flag
    uint32_t tf[8];                     // +0x70: Transfer curve descriptors
    uint32_t QuantizationScaling;       // +0x90: Quantization scale factor
    uint32_t CRC;                       // +0x94: Hardware CRC checksum
    uint32_t QuantMatrixIndex;          // +0x98: Quantization matrix index
    uint32_t _reserved[9];              // +0x9C: Padding to 128 bytes
} sAppleProResRawFrameHeader_t;

// InInfo parameter block passed from IOUserClient to kernel
typedef struct sProRes_EncodeFrame_UserKernel_In_Info {
    uint32_t frameId;
    uint32_t fastPass;
    uint32_t interruptEnable;
    uint32_t encodeMode;                // 1=Encode, 0=Decode
    uint32_t alphaPresent;
    uint32_t compressionEnable;
    uint32_t numPasses;
    uint32_t chromaFormat;              // 0=422, 1=444, 2=RAW
    uint32_t bitDepth;                  // 10 or 14
    
    // Virtual and physical buffer addresses
    uint64_t outputDartVA;
    uint64_t outputPhysAddr;
    uint32_t maxOutputSize;
    
    // Frame geometry
    uint32_t offsetH;
    uint32_t offsetV;
    uint32_t sizeH;
    uint32_t sizeV;
    uint32_t width;
    uint32_t height;
    
    // Plane strides and pointers
    uint32_t strideY0;
    uint32_t strideC0;
    uint32_t strideA0;
    uint64_t dataY0;
    uint64_t metaY0;
    uint64_t dataC0;
    uint64_t metaC0;
    uint64_t dataA0;
    uint64_t metaA0;
    
    // Rate control parameters
    uint32_t qIndex;
    uint32_t targetSize;
    uint32_t maxSize;
    uint32_t mbCategoryThr[6];
    uint32_t disQuantRefin;
    uint32_t alpha;
    uint32_t alpha0;
    uint32_t gamma0;
    uint32_t beta[4];
    uint32_t corrRatio_quantThr[4][4];
    uint32_t controlCrc;
    uint32_t quantMatrixIndex;
    
    // Command words
    uint32_t cmdWord;
    uint32_t cmdXWord;
    uint32_t lca;
    uint32_t lcc;
    uint32_t lcy;
    uint32_t brWrDis;
} sProRes_EncodeFrame_UserKernel_In_Info_t;

// Device feature flags structure
typedef struct sAppleProResDevFeatureList {
    int32_t numFramesPendingMultiplier;
    int32_t bUseLegacyTargetSize;
    int32_t bRAWCodec;
    int32_t bAlphaOnlyCodec;
    int32_t bFrameMaxSizeLimit;
    int32_t bLossyInterchangeFormat;
    int32_t bMBsPerSlice;
    int32_t bRAWRateControl;
    int32_t bHWStatsQPMap;
    int32_t bSwapBRRaw;
    int32_t bAlphaProcessing;
    int32_t bDisableBitstream;
    int32_t bRAWV2;
    int32_t bCommandSplitterFix;
    int32_t isDevBinned;
    int32_t eAprDesc;
    int32_t bUseLegacyEncoderID;
    int32_t bWriteDMAStatsReg;
    int32_t bisFastsim;
} sAppleProResDevFeatureList_t;

#ifdef __cplusplus
}
#endif

#endif // APPLE_PRORES_HW_H
