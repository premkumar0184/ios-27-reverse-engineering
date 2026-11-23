/**
 * ave_direct_submit.pseudo.c — Clean-Room C Client for Apple Video Encoder 2 (AVE2)
 *
 * Target: Apple Silicon A19 Pro (t8150) / iOS 27.2 (24B119)
 * Driver Interface: com.apple.driver.AppleAVE2 / AppleAVE2UserClient
 * Hardware Engine: Multi-Stream Video Codec Accelerator (AV1, HEVC, AVC, ProRes)
 *
 * Verified with: gcc -fsyntax-only -Wall -Wextra -Werror
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define AVE_PAGE_SIZE                0x4000ULL       /* 16 KB Granule */
#define AVE_MMIO_BASE_DART           0x77020000ULL   /* dart-ave IOMMU */
#define AVE_MMIO_BASE_CORE           0x77000000ULL   /* AVE2 Core MMIO */
#define AVE_CMD_DESCRIPTOR_SIZE      128             /* sCmdInformation size */
#define AVE_DMA_DESCRIPTOR_SIZE      64              /* DMA descriptor size */

/* Hardware Command Opcodes */
typedef enum {
    AVE_CMD_NONE            = 0,
    AVE_CMD_OPEN            = 1,
    AVE_CMD_CLOSE           = 2,
    AVE_CMD_START           = 3,
    AVE_CMD_START_AVC       = 4,
    AVE_CMD_START_HEVC      = 5,
    AVE_CMD_PROCESS_AVC     = 6,
    AVE_CMD_PROCESS_HEVC    = 7,
    AVE_CMD_PROCESS_LRME    = 8,
    AVE_CMD_PROCESS_MCTF    = 9,
    AVE_CMD_PROCESS_DMV     = 10,
    AVE_CMD_PROCESS_GGM     = 11,
    AVE_CMD_CONFIG          = 12,
    AVE_CMD_FLUSH           = 13,
    AVE_CMD_RESET           = 14,
    AVE_CMD_PRIORITY        = 15,
    AVE_CMD_COMPLETE        = 16,
    AVE_CMD_MAX             = 17
} ave_cmd_opcode_t;

/* Codec Type Identifiers */
typedef enum {
    AVE_CODEC_AVC           = 0,
    AVE_CODEC_HEVC          = 1,
    AVE_CODEC_AV1           = 2,
    AVE_CODEC_PRORES        = 3,
    AVE_CODEC_HEIF          = 4,
    AVE_CODEC_MAX           = 5
} ave_codec_type_t;

/* UserClient External Method Selectors */
typedef enum {
    AVE_UCCmd_None          = 0,
    AVE_UCCmd_Open          = 1,
    AVE_UCCmd_Close         = 2,
    AVE_UCCmd_Config        = 3,
    AVE_UCCmd_Prepare       = 4,
    AVE_UCCmd_Start         = 5,
    AVE_UCCmd_Stop          = 6,
    AVE_UCCmd_Process       = 7,
    AVE_UCCmd_Complete      = 8,
    AVE_UCCmd_Flush         = 9,
    AVE_UCCmd_Reset         = 10,
    AVE_UCCmd_Print         = 11,
    AVE_UCCmd_Max           = 12
} ave_uc_selector_t;

/* Status Codes */
typedef enum {
    AVE_STATUS_SUCCESS              = 0x00000000,
    AVE_STATUS_INVALID_ARGUMENT     = 0x00000001,
    AVE_STATUS_NO_MEMORY            = 0x00000002,
    AVE_STATUS_BUSY                 = 0x00000003,
    AVE_STATUS_TIMEOUT              = 0x00000004,
    AVE_STATUS_HARDWARE_FAULT       = 0x00000005,
    AVE_STATUS_BUFFER_OVERFLOW      = 0x00000006,
    AVE_STATUS_UNSUPPORTED_PROFILE  = 0x00000007
} ave_status_t;

/* Source Input DMA Descriptor */
typedef struct __attribute__((aligned(64))) {
    uint64_t luma_plane_pa;
    uint64_t chroma_plane_pa;
    uint64_t alpha_plane_pa;
    uint32_t luma_stride_bytes;
    uint32_t chroma_stride_bytes;
    uint32_t frame_width_pixels;
    uint32_t frame_height_pixels;
    uint32_t pixel_format;
    uint32_t flags;
    uint8_t  padding[16];
} ave_source_dma_desc_t;

/* Bitstream Output DMA Descriptor */
typedef struct __attribute__((aligned(64))) {
    uint64_t bitstream_buffer_pa;
    uint32_t buffer_capacity_bytes;
    uint32_t written_bytes_counter;
    uint64_t slice_offset_table_pa;
    uint32_t flags;
    uint8_t  padding[36];
} ave_bitstream_dma_desc_t;

/* Reconstructed Frame DPB Descriptor */
typedef struct __attribute__((aligned(64))) {
    uint64_t ref_l0_frame_pa;
    uint64_t ref_l1_frame_pa;
    uint64_t reconstructed_frame_pa;
    uint64_t motion_vector_storage_pa;
    uint32_t dpb_slot_id;
    uint32_t picture_order_count;
    uint8_t  padding[88];
} ave_reconstructed_dpb_desc_t;

/* Hardware Command Descriptor (sCmdInformation) */
typedef struct __attribute__((aligned(64))) {
    uint32_t session_id;
    uint32_t command_opcode;
    uint64_t timestamp_us;
    uint64_t source_input_desc_pa;
    uint64_t bitstream_output_desc_pa;
    uint64_t reconstructed_dpb_desc_pa;
    uint64_t slice_params_pa;
    uint64_t client_cookie;
    uint32_t status_flags;
    uint8_t  reserved[68];
} ave_cmd_information_t;

/* UserClient Open In/Out Parameters */
typedef struct {
    uint32_t client_version;
    uint32_t codec_type;
    uint32_t frame_width;
    uint32_t frame_height;
    uint32_t profile_level;
    uint32_t reserved;
} S_AVE_UCInParam_Open;

typedef struct {
    uint32_t session_id;
    uint32_t max_dpb_slots;
    uint64_t shared_queue_pa;
    uint32_t shared_queue_entries;
    uint32_t result_status;
} S_AVE_UCOutParam_Open;

/* UserClient Process In/Out Parameters */
typedef struct {
    uint32_t session_id;
    uint32_t slice_type;
    uint64_t input_surface_id;
    uint64_t output_buffer_id;
    uint32_t target_qp;
    uint32_t flags;
} S_AVE_UCInParam_Process;

typedef struct {
    uint32_t session_id;
    uint32_t encoded_bytes;
    uint32_t average_qp;
    uint32_t status_code;
} S_AVE_UCOutParam_Process;

/* UserClient Close In/Out Parameters */
typedef struct {
    uint32_t session_id;
    uint32_t flags;
} S_AVE_UCInParam_Close;

typedef struct {
    uint32_t result_status;
} S_AVE_UCOutParam_Close;

/* Device Context State Structure */
typedef struct {
    uint32_t session_id;
    ave_codec_type_t codec_type;
    uint32_t width;
    uint32_t height;
    uint64_t command_ring_pa;
    uint32_t command_ring_entries;
    uint32_t head_index;
    uint32_t tail_index;
    volatile uint32_t *mmio_ctrl;
    volatile uint32_t *mmio_doorbell;
    bool is_active;
} ave_context_t;

/* Memory barrier primitive */
static inline void ave_memory_barrier(void) {
    __asm__ volatile("dmb ish" ::: "memory");
}

/* MMIO write primitive */
static inline void ave_mmio_write32(volatile uint32_t *addr, uint32_t val) {
    *addr = val;
    ave_memory_barrier();
}

/* MMIO read primitive */
static inline uint32_t ave_mmio_read32(volatile const uint32_t *addr) {
    uint32_t val = *addr;
    ave_memory_barrier();
    return val;
}

/* Session Initialization */
ave_status_t ave_client_open_session(
    ave_context_t *ctx,
    ave_codec_type_t codec,
    uint32_t width,
    uint32_t height)
{
    if (!ctx || width == 0 || height == 0 || codec >= AVE_CODEC_MAX) {
        return AVE_STATUS_INVALID_ARGUMENT;
    }

    ctx->codec_type = codec;
    ctx->width = width;
    ctx->height = height;
    ctx->session_id = 0x1001; /* Simulated allocated session ID */
    ctx->command_ring_pa = 0x88000000ULL;
    ctx->command_ring_entries = 64;
    ctx->head_index = 0;
    ctx->tail_index = 0;
    ctx->mmio_ctrl = (volatile uint32_t *)(uintptr_t)AVE_MMIO_BASE_CORE;
    ctx->mmio_doorbell = (volatile uint32_t *)(uintptr_t)(AVE_MMIO_BASE_CORE + 0x10);
    ctx->is_active = true;

    return AVE_STATUS_SUCCESS;
}

/* Submits a Frame Encode Command into the Hardware Ring */
ave_status_t ave_client_submit_frame(
    ave_context_t *ctx,
    uint64_t luma_pa,
    uint64_t chroma_pa,
    uint64_t bitstream_pa,
    uint32_t buffer_capacity,
    uint32_t slice_type,
    uint32_t target_qp,
    uint64_t cookie)
{
    if (!ctx || !ctx->is_active) {
        return AVE_STATUS_INVALID_ARGUMENT;
    }
    if ((luma_pa & (AVE_PAGE_SIZE - 1)) != 0 || (bitstream_pa & (AVE_PAGE_SIZE - 1)) != 0) {
        return AVE_STATUS_INVALID_ARGUMENT;
    }

    /* Compute next tail slot */
    uint32_t next_tail = (ctx->tail_index + 1) % ctx->command_ring_entries;
    if (next_tail == ctx->head_index) {
        return AVE_STATUS_BUSY; /* Ring buffer full */
    }

    /* Format DMA Source Input Descriptor */
    ave_source_dma_desc_t src_desc;
    src_desc.luma_plane_pa = luma_pa;
    src_desc.chroma_plane_pa = chroma_pa;
    src_desc.alpha_plane_pa = 0;
    src_desc.luma_stride_bytes = ctx->width;
    src_desc.chroma_stride_bytes = ctx->width;
    src_desc.frame_width_pixels = ctx->width;
    src_desc.frame_height_pixels = ctx->height;
    src_desc.pixel_format = 0x34323076; /* NV12 FourCC ('420v') */
    src_desc.flags = 0x1;               /* Cache flush */

    /* Format Bitstream Output Descriptor */
    ave_bitstream_dma_desc_t bs_desc;
    bs_desc.bitstream_buffer_pa = bitstream_pa;
    bs_desc.buffer_capacity_bytes = buffer_capacity;
    bs_desc.written_bytes_counter = 0;
    bs_desc.slice_offset_table_pa = 0;
    bs_desc.flags = 0;

    /* Format Command Information Packet */
    ave_cmd_information_t cmd;
    cmd.session_id = ctx->session_id;
    cmd.command_opcode = (ctx->codec_type == AVE_CODEC_HEVC) ? AVE_CMD_PROCESS_HEVC : AVE_CMD_PROCESS_AVC;
    cmd.timestamp_us = 1000000ULL;
    cmd.source_input_desc_pa = (uint64_t)(uintptr_t)&src_desc;
    cmd.bitstream_output_desc_pa = (uint64_t)(uintptr_t)&bs_desc;
    cmd.reconstructed_dpb_desc_pa = 0;
    cmd.slice_params_pa = (uint64_t)target_qp;
    cmd.client_cookie = cookie;
    cmd.status_flags = slice_type;

    /* Write command descriptor into shared command ring slot */
    ave_cmd_information_t *ring_base = (ave_cmd_information_t *)(uintptr_t)ctx->command_ring_pa;
    ring_base[ctx->tail_index] = cmd;

    /* Advance ring pointer and ring hardware doorbell */
    ctx->tail_index = next_tail;
    ave_memory_barrier();
    ave_mmio_write32(ctx->mmio_doorbell, ctx->session_id);

    return AVE_STATUS_SUCCESS;
}

/* Session Termination */
ave_status_t ave_client_close_session(ave_context_t *ctx) {
    if (!ctx || !ctx->is_active) {
        return AVE_STATUS_INVALID_ARGUMENT;
    }

    /* Issue flush before closing */
    ave_mmio_write32(ctx->mmio_doorbell, 0xFFFFFFFFU);
    ctx->is_active = false;

    return AVE_STATUS_SUCCESS;
}
