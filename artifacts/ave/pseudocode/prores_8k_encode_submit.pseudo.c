/**
 * prores_8k_encode_submit.pseudo.c - Production-Grade Hardware Submission Pipeline
 * Demonstrating Real-Time 8K ProRes 422 HQ, ProRes RAW, and AVE2 Motion Estimation
 * Hardware Platform: Apple Silicon A19 Pro (t8150) / Apple H18 Generation
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "../include/apple_prores_hw.h"
#include "../include/ave2_motion_estimation.h"

// Memory Mapped I/O Access Macros
#define MMIO_READ32(addr)           (*(volatile uint32_t *)(addr))
#define MMIO_WRITE32(addr, val)     (*(volatile uint32_t *)(addr) = (uint32_t)(val))
#define MMIO_READ64(addr)           (*(volatile uint64_t *)(addr))
#define MMIO_WRITE64(addr, val)     (*(volatile uint64_t *)(addr) = (uint64_t)(val))

/**
 * 1. Submit 8K ProRes 422 HQ Frame Encoding across Dual Cores (apr,a1 and apr,a2)
 */
int SubmitProRes422HQ_8K_Frame(
    uint32_t frameId,
    uint64_t lumaDartVA,
    uint64_t chromaDartVA,
    uint64_t outputBitstreamDartVA,
    uint32_t maxOutputBytes
) {
    sProRes_EncodeFrame_UserKernel_In_Info_t encodeCmd;
    memset(&encodeCmd, 0, sizeof(encodeCmd));

    encodeCmd.frameId = frameId;
    encodeCmd.fastPass = 1;                 // Real-time 60fps single-pass rate control
    encodeCmd.interruptEnable = 1;
    encodeCmd.encodeMode = 1;               // 1 = Hardware Encode
    encodeCmd.alphaPresent = 0;             // 422 standard (no alpha plane)
    encodeCmd.compressionEnable = 0;        // Linear raster surfaces
    encodeCmd.numPasses = 1;
    encodeCmd.chromaFormat = 0;             // 0 = 4:2:2 YCbCr
    encodeCmd.bitDepth = 10;                // 10-bit mastering precision

    // 8K Active Frame Geometry
    encodeCmd.width = 8192;
    encodeCmd.height = 4320;
    encodeCmd.sizeH = 8192;
    encodeCmd.sizeV = 4320;
    encodeCmd.offsetH = 0;
    encodeCmd.offsetV = 0;

    // Strides (64-byte cache line aligned)
    encodeCmd.strideY0 = 8192 * 2;          // 10-bit unpacked in 16-bit word = 16384 bytes
    encodeCmd.strideC0 = 8192 * 2;          // Interleaved CbCr = 16384 bytes
    encodeCmd.dataY0 = lumaDartVA;
    encodeCmd.dataC0 = chromaDartVA;

    // Output Bitstream Buffer
    encodeCmd.outputDartVA = outputBitstreamDartVA;
    encodeCmd.maxOutputSize = maxOutputBytes;

    // Rate Control Configuration for ProRes 422 HQ (~1768 Mbps @ 60fps = 3.68 MB/frame)
    encodeCmd.qIndex = 1;                   // High quality base quantization index
    encodeCmd.targetSize = 2949120;         // Target: ~2.95 MB per frame
    encodeCmd.maxSize = 3686400;            // Max ceiling: ~3.68 MB per frame
    encodeCmd.mbCategoryThr[0] = 128;
    encodeCmd.mbCategoryThr[1] = 256;
    encodeCmd.mbCategoryThr[2] = 512;
    encodeCmd.mbCategoryThr[3] = 1024;
    encodeCmd.mbCategoryThr[4] = 2048;
    encodeCmd.mbCategoryThr[5] = 4096;

    // Multi-Core Split: Dispatch Core 0 (apr,a1) for Slices 0..7 and Core 1 (apr,a2) for Slices 8..15
    uint64_t mmioBaseA1 = APR_HW_MMIO_BASE + APR_CORE_A1_OFFSET;
    uint64_t mmioBaseA2 = APR_HW_MMIO_BASE + APR_CORE_A2_OFFSET;

    // Program Core A1 (Upper Half of 8K)
    MMIO_WRITE32(mmioBaseA1 + 0x0010, (uint32_t)(lumaDartVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x0014, (uint32_t)(lumaDartVA >> 32));
    MMIO_WRITE32(mmioBaseA1 + 0x0018, (uint32_t)(chromaDartVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x001C, (uint32_t)(chromaDartVA >> 32));
    MMIO_WRITE32(mmioBaseA1 + 0x0030, (uint32_t)(outputBitstreamDartVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x0034, (uint32_t)(outputBitstreamDartVA >> 32));
    MMIO_WRITE32(mmioBaseA1 + 0x0048, encodeCmd.targetSize / 2); // 50% slice budget
    MMIO_WRITE32(mmioBaseA1 + 0x0000, 0x00000001);               // Trigger Core A1 Start

    // Program Core A2 (Lower Half of 8K)
    uint64_t lumaLowerVA = lumaDartVA + (encodeCmd.strideY0 * 2160);
    uint64_t chromaLowerVA = chromaDartVA + (encodeCmd.strideC0 * 2160);
    uint64_t bitstreamLowerVA = outputBitstreamDartVA + (encodeCmd.maxOutputSize / 2);

    MMIO_WRITE32(mmioBaseA2 + 0x0010, (uint32_t)(lumaLowerVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x0014, (uint32_t)(lumaLowerVA >> 32));
    MMIO_WRITE32(mmioBaseA2 + 0x0018, (uint32_t)(chromaLowerVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x001C, (uint32_t)(chromaLowerVA >> 32));
    MMIO_WRITE32(mmioBaseA2 + 0x0030, (uint32_t)(bitstreamLowerVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x0034, (uint32_t)(bitstreamLowerVA >> 32));
    MMIO_WRITE32(mmioBaseA2 + 0x0048, encodeCmd.targetSize / 2);
    MMIO_WRITE32(mmioBaseA2 + 0x0000, 0x00000001);               // Trigger Core A2 Start

    return 0; // Dispatched to hardware
}

/**
 * 2. Submit 8K ProRes RAW 14-bit CFA Bayer Frame Encoding
 */
int SubmitProResRAW_8K_Frame(
    uint32_t frameId,
    uint64_t bayerPlanesDartVA[4], // [0]=R, [1]=Gr, [2]=Gb, [3]=B
    uint32_t bayerStrideBytes,
    eAppleProResCfaPattern_t cfaPattern,
    uint64_t outputBitstreamDartVA,
    uint32_t maxOutputBytes
) {
    // 1. Construct 128-byte ProRes RAW FrameHeader Packet
    sAppleProResRawFrameHeader_t rawHeader;
    memset(&rawHeader, 0, sizeof(rawHeader));

    rawHeader.size = sizeof(sAppleProResRawFrameHeader_t);
    rawHeader.ver = 2;                      // ProRes RAW Version 2
    rawHeader.id = frameId;
    rawHeader.hsize = 8192;
    rawHeader.vsize = 4320;
    rawHeader.crop[0] = 0;
    rawHeader.crop[1] = 0;
    rawHeader.crop[2] = 8192;
    rawHeader.crop[3] = 4320;
    rawHeader.cfa = cfaPattern;             // 0=RGGB
    rawHeader.svr = 0x56353731;             // 'V571' - Silicon generation tag
    rawHeader.wbr = 0x00018000;             // Red gain = 1.5x (Q16.16)
    rawHeader.wbb = 0x0001C000;             // Blue gain = 1.75x (Q16.16)
    rawHeader.wbcct = 5500;                 // 5500 Kelvin Daylight
    rawHeader.QuantizationScaling = 1;
    rawHeader.QuantMatrixIndex = 0;

    // 2. Configure Hardware Dual-Core Command Queue
    uint64_t mmioBaseA1 = APR_HW_MMIO_BASE + APR_CORE_A1_OFFSET;
    uint64_t mmioBaseA2 = APR_HW_MMIO_BASE + APR_CORE_A2_OFFSET;

    // Write R and Gr channels to Core A1
    MMIO_WRITE32(mmioBaseA1 + 0x0010, (uint32_t)(bayerPlanesDartVA[0] & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x0014, (uint32_t)(bayerPlanesDartVA[0] >> 32));
    MMIO_WRITE32(mmioBaseA1 + 0x0018, (uint32_t)(bayerPlanesDartVA[1] & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x001C, (uint32_t)(bayerPlanesDartVA[1] >> 32));

    // Write Gb and B channels to Core A2
    MMIO_WRITE32(mmioBaseA2 + 0x0010, (uint32_t)(bayerPlanesDartVA[2] & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x0014, (uint32_t)(bayerPlanesDartVA[2] >> 32));
    MMIO_WRITE32(mmioBaseA2 + 0x0018, (uint32_t)(bayerPlanesDartVA[3] & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x001C, (uint32_t)(bayerPlanesDartVA[3] >> 32));

    // Output Bitstream Buffer Programming
    MMIO_WRITE32(mmioBaseA1 + 0x0030, (uint32_t)(outputBitstreamDartVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA1 + 0x0034, (uint32_t)(outputBitstreamDartVA >> 32));
    uint64_t bitstreamLowerVA = outputBitstreamDartVA + (maxOutputBytes / 2);
    MMIO_WRITE32(mmioBaseA2 + 0x0030, (uint32_t)(bitstreamLowerVA & 0xFFFFFFFF));
    MMIO_WRITE32(mmioBaseA2 + 0x0034, (uint32_t)(bitstreamLowerVA >> 32));

    // Stride Configuration
    MMIO_WRITE32(mmioBaseA1 + 0x0028, bayerStrideBytes);
    MMIO_WRITE32(mmioBaseA2 + 0x0028, bayerStrideBytes);

    // Arm RAW Rate Control Register
    MMIO_WRITE32(mmioBaseA1 + 0x0048, 0x00020000); // 128 KB max row budget
    MMIO_WRITE32(mmioBaseA2 + 0x0048, 0x00020000);

    // Trigger Concurrent Execution
    MMIO_WRITE32(mmioBaseA1 + 0x0000, 0x00000005); // Bit 0: Go, Bit 2: RAW CFA Direct Mode
    MMIO_WRITE32(mmioBaseA2 + 0x0000, 0x00000005);

    return 0;
}

/**
 * 3. Concurrent Motion Estimation Pipeline Trigger (AVE2 Hardware Coprocessors)
 */
int TriggerAVE2MotionEstimation(
    uint64_t srcPixelAddr,
    uint32_t srcStride,
    uint64_t refPixelAddr,
    uint64_t mvOutputBufferAddr
) {
    uint64_t aveBase = AVE2_MMIO_BASE;

    // Step A: Hierarchical Motion Estimation and Spatial Complexity (HMESC)
    MMIO_WRITE64(aveBase + AVE2_REG_HMESC_SRC_ADDR, srcPixelAddr);
    MMIO_WRITE32(aveBase + AVE2_REG_HMESC_SRC_STRIDE, srcStride);
    MMIO_WRITE32(aveBase + AVE2_REG_HMESC_CTRL_START, 0x1); // Trigger HMESC

    // Step B: Low-Resolution Motion Estimation (LRME 16:1 downsampled luma)
    MMIO_WRITE64(aveBase + AVE2_REG_LRME_SRC_ADDR, srcPixelAddr);
    MMIO_WRITE64(aveBase + AVE2_REG_LRME_REF_ADDR, refPixelAddr);
    MMIO_WRITE64(aveBase + AVE2_REG_LRME_MV_OUT_ADDR, mvOutputBufferAddr);
    MMIO_WRITE32(aveBase + AVE2_REG_LRME_CTRL_GO, 0x1);    // Trigger LRME Full Search

    // Step C: Dense Motion Vector (DMV) Quarter-Pel Refinement
    MMIO_WRITE32(aveBase + AVE2_REG_DMV_MV_DENSITY_CFG, 0x00000004); // 4x4 sub-block density
    MMIO_WRITE32(aveBase + AVE2_REG_DMV_CTRL_START, 0x1);            // Trigger DMV

    // Step D: Motion-Compensated Temporal Filtering (MCTF Denoising)
    MMIO_WRITE32(aveBase + AVE2_REG_MCTF_REF_COUNT, 3);              // 3 temporal reference frames
    MMIO_WRITE32(aveBase + AVE2_REG_MCTF_FILTER_GATING, 0x1);        // Enable adaptive gating

    return 0;
}
