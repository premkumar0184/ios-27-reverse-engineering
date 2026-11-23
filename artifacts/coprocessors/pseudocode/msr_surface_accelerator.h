/**
 * @file msr_surface_accelerator.h
 * @brief Clean-room C definitions for MSR IOSurfaceAccelerator & Pixel Pipeline.
 *
 * Extracted from Apple Silicon A19 Pro (t8150) / iPhone 18,3 (v57ap).
 * Binary Provenance: Firmware/msr/t8150.msrf.im4p
 * Target Core: ARMv7-M (Cortex-M) 32-bit Mach-O (MH_PRELOAD)
 */

#ifndef MSR_SURFACE_ACCELERATOR_H
#define MSR_SURFACE_ACCELERATOR_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MSR_TEXT_VMADDR         0x00100000
#define MSR_DATA_VMADDR         0x10000200
#define MSR_DMEM_VMADDR         0x10000000

/* Pixel Accelerator Pixel Formats */
typedef enum {
    MSR_FMT_ARGB8888            = 0x01,
    MSR_FMT_BGRA8888            = 0x02,
    MSR_FMT_RGBA1010102         = 0x03,
    MSR_FMT_NV12_420_8B         = 0x10,
    MSR_FMT_P010_420_10B        = 0x11,
    MSR_FMT_AYUV4444            = 0x12
} msr_pixel_format_t;

/* Pixel Accelerator Scaling Filter Modes */
typedef enum {
    MSR_SCALE_NEAREST           = 0,
    MSR_SCALE_BILINEAR          = 1,
    MSR_SCALE_BICUBIC           = 2,
    MSR_SCALE_LANCZOS3          = 3
} msr_scale_mode_t;

/* Pixel Accelerator Pipeline Configuration */
typedef struct __attribute__((packed)) {
    uint32_t src_width;
    uint32_t src_height;
    uint32_t src_format;
    uint64_t src_luma_dma_addr;
    uint64_t src_chroma_dma_addr;
    uint32_t src_stride_luma;
    uint32_t src_stride_chroma;

    uint32_t dst_width;
    uint32_t dst_height;
    uint32_t dst_format;
    uint64_t dst_dma_addr;
    uint32_t dst_stride;

    uint8_t  scale_mode;                /* msr_scale_mode_t */
    uint8_t  csc_matrix_index;          /* 0=Rec.601, 1=Rec.709, 2=BT.2020 */
    uint8_t  dither_enable;
    uint8_t  flags;
} msr_pa_pipeline_cfg_t;

/* APIODMA Generic Packet Header */
typedef struct __attribute__((packed)) {
    uint16_t packet_id;
    uint16_t transfer_length_bytes;
    uint32_t direction;                 /* 0=Read, 1=Write */
    uint64_t bus_address;
    uint32_t burst_size;
    uint32_t flags;
} apiodma_generic_packet_t;

/* Control Plane Dashboard Entry */
typedef struct __attribute__((packed)) {
    uint32_t entry_index;
    uint32_t bank_id;
    uint32_t client_id;
    uint32_t status_code;
    uint64_t completion_timestamp_ticks;
} msr_dashboard_entry_t;

static inline bool msr_validate_dimensions(uint32_t w, uint32_t h) {
    return (w > 0 && w <= 8192) && (h > 0 && h <= 8192);
}

#ifdef __cplusplus
}
#endif

#endif /* MSR_SURFACE_ACCELERATOR_H */
