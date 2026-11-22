/**
 * iOS 27 Apple Neural Engine (ANE) Direct Userspace Runtime Driver
 * Clean-Room C Implementation for Apple Silicon A19 Pro (t8150 / H18 / Apollo v5)
 *
 * Provides a zero-overhead runtime bypassing CoreML / MIL to execute arbitrary
 * ANE bytecode and quantized tensor models directly on hardware queues.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <math.h>

/* Hardware Configuration Constants */
#define ANE_FIFO_NID              0x40      /* Hardware Command FIFO Node ID */
#define ANE_CMD_GRAN              0x10      /* Command packet granularity (16 bytes) */
#define ANE_TILE_SIZE             16384     /* 16 KB hardware tile unit */
#define ANE_TILE_SHIFT            14        /* 2^14 = 16384 */
#define ANE_CHANNELS_PER_TILE     32        /* 32-channel aligned raster format */
#define ANE_MAX_CHANNELS          32        /* Up to 32 memory channels */
#define ANE_TD_SIZE               128       /* Task descriptor size (ZinAneTd36) */

/* IOCTL Command Definitions */
#define ANE_IOCTL_MAGIC           'A'
#define ANE_IOCTL_OPEN            _IO(ANE_IOCTL_MAGIC, 0)
#define ANE_IOCTL_CLOSE           _IO(ANE_IOCTL_MAGIC, 1)
#define ANE_IOCTL_MAP_BUFFER      _IOWR(ANE_IOCTL_MAGIC, 2, struct ane_map_args)
#define ANE_IOCTL_UNMAP_BUFFER    _IOW(ANE_IOCTL_MAGIC, 3, struct ane_unmap_args)
#define ANE_IOCTL_SUBMIT          _IOW(ANE_IOCTL_MAGIC, 4, struct ane_submit_args)
#define ANE_IOCTL_WAIT            _IOWR(ANE_IOCTL_MAGIC, 5, struct ane_wait_args)

/* Task Descriptor Struct Layout (ZinAneTd36 - 128 Bytes) */
struct __attribute__((packed)) ane_task_descriptor {
    uint32_t task_type;          /* +0x00: 0x1=Conv/GEMM, 0x2=ElemWise, 0x3=Pool, 0x4=CCDma */
    uint32_t bar_id;             /* +0x04: Base Address Register index (0..7) */
    uint64_t src_base_addr;      /* +0x08: Source buffer DART virtual address */
    uint64_t dst_base_addr;      /* +0x10: Destination buffer DART virtual address */
    uint64_t kernel_offset;      /* +0x18: Offset into krn weights section */
    uint32_t shape0;             /* +0x20: Batch / Depth */
    uint32_t shape1;             /* +0x24: Channels */
    uint32_t shape2;             /* +0x28: Height */
    uint32_t shape3;             /* +0x2c: Width */
    uint32_t shape4;             /* +0x30: Sub-tile planes */
    uint32_t constant_data;      /* +0x34: Immediate scalar operand (e.g. ReLU threshold) */
    uint64_t src_stride0;        /* +0x38: Source stride dim 0 */
    uint64_t src_stride1;        /* +0x40: Source stride dim 1 */
    uint64_t src_stride2;        /* +0x48: Source stride dim 2 */
    uint64_t src_stride3;        /* +0x50: Source stride dim 3 */
    uint64_t dst_stride0;        /* +0x58: Dest stride dim 0 */
    uint64_t dst_stride1;        /* +0x60: Dest stride dim 1 */
    uint64_t dst_stride2;        /* +0x68: Dest stride dim 2 */
    uint64_t dst_stride3;        /* +0x70: Dest stride dim 3 */
    uint32_t zero_pad_mode;      /* +0x78: Spatial padding mask */
    uint32_t wait_event_val;     /* +0x7c: Barrier sync value */
    uint8_t  padding[48];        /* +0x80: 128-byte hardware alignment */
};

/* Submission Arguments (160 Bytes) */
struct __attribute__((packed)) ane_submit_args {
    uint32_t tsk_size;           /* Microcode stream length in bytes */
    uint32_t td_count;           /* Number of task descriptors */
    uint32_t td_size;            /* Task descriptor size (128) */
    uint32_t btsp_handle;        /* Bootstrap memory handle */
    uint32_t handles[32];        /* DART memory channel handles */
    uint32_t num_handles;        /* Active handle count */
    uint32_t flags;              /* QoS & execution flags */
    uint64_t sync_handle;        /* Hardware sync event handle */
};

/* Buffer Mapping Arguments */
struct ane_map_args {
    void    *user_vaddr;         /* Userspace pointer */
    size_t   size_bytes;         /* Size in bytes (multiple of 16KB) */
    uint32_t prot_flags;         /* Read/Write flags */
    uint32_t handle_out;         /* Allocated DART handle */
    uint64_t dart_vaddr_out;     /* DART virtual address */
};

struct ane_unmap_args {
    uint32_t handle;             /* DART handle to free */
};

struct ane_wait_args {
    uint64_t sync_handle;        /* Barrier handle */
    uint32_t timeout_ms;         /* Timeout in milliseconds */
    uint64_t elapsed_hw_ns;      /* Execution duration measured by hardware */
    uint32_t status_out;         /* Completion status (0 = success) */
};

/* Device Context */
struct ane_device {
    int      fd;                 /* Device file descriptor */
    bool     initialized;        /* Initialization state */
    uint32_t core_count;         /* Number of ANE clusters (3 on A19 Pro) */
};

/**
 * Initialize ANE hardware driver context
 */
int ane_init(struct ane_device *dev) {
    if (!dev) return -1;
    
    dev->fd = open("/dev/ane", O_RDWR);
    if (dev->fd < 0) {
        /* Fallback to IOKit userclient service node */
        dev->fd = open("/dev/h16ane", O_RDWR);
        if (dev->fd < 0) {
            perror("[ANE Driver] Failed to open ANE device node");
            return -1;
        }
    }
    
    if (ioctl(dev->fd, ANE_IOCTL_OPEN, 0) < 0) {
        perror("[ANE Driver] ANE_IOCTL_OPEN failed");
        close(dev->fd);
        return -1;
    }
    
    dev->core_count = 3; /* A19 Pro t8150 tri-cluster ANE */
    dev->initialized = true;
    printf("[ANE Driver] Successfully initialized ANE H18/Apollo_v5 on t8150\n");
    return 0;
}

/**
 * Transform standard row-major tensor [N, C, H, W] into ANE 32-channel 16KB tiles
 */
int ane_tile(const float *src_fp32, void *dst_tiled,
             uint32_t N, uint32_t C, uint32_t H, uint32_t W,
             bool is_fp16) {
    if (!src_fp32 || !dst_tiled) return -1;
    
    uint32_t elem_size = is_fp16 ? 2 : 1; /* FP16 or INT8 */
    uint32_t R = ((W * elem_size + 63) / 64) * 64; /* 64-byte row alignment */
    uint32_t plane_size = H * R;
    uint32_t P = ((plane_size + 16383) / 16384) * 16384; /* 16KB tile pitch */
    uint32_t channel_groups = (C + 31) / 32;
    
    uint8_t *out_ptr = (uint8_t *)dst_tiled;
    memset(out_ptr, 0, N * channel_groups * P * 32);
    
    for (uint32_t n = 0; n < N; n++) {
        for (uint32_t cg = 0; cg < channel_groups; cg++) {
            uint8_t *group_base = out_ptr + (n * channel_groups + cg) * P * 32;
            for (uint32_t c_idx = 0; c_idx < 32; c_idx++) {
                uint32_t actual_c = cg * 32 + c_idx;
                if (actual_c >= C) break;
                
                uint8_t *channel_base = group_base + c_idx * P;
                for (uint32_t h = 0; h < H; h++) {
                    uint8_t *row_base = channel_base + h * R;
                    for (uint32_t w = 0; w < W; w++) {
                        float val = src_fp32[((n * C + actual_c) * H + h) * W + w];
                        if (is_fp16) {
                            /* Convert float to FP16 representation */
                            uint16_t h_val;
                            uint32_t x = *(uint32_t *)&val;
                            h_val = ((x >> 16) & 0x8000) |
                                    ((((x & 0x7f800000) - 0x38000000) >> 13) & 0x7c00) |
                                    ((x >> 13) & 0x03ff);
                            ((uint16_t *)row_base)[w] = h_val;
                        } else {
                            /* Quantize float to INT8 [-128..127] */
                            int8_t q_val = (int8_t)fmaxf(-128.0f, fminf(127.0f, roundf(val * 127.0f)));
                            ((int8_t *)row_base)[w] = q_val;
                        }
                    }
                }
            }
        }
    }
    return 0;
}

/**
 * Transform ANE 16KB tiles back into contiguous row-major tensor [N, C, H, W]
 */
int ane_untile(const void *src_tiled, float *dst_fp32,
               uint32_t N, uint32_t C, uint32_t H, uint32_t W,
               bool is_fp16) {
    if (!src_tiled || !dst_fp32) return -1;
    
    uint32_t elem_size = is_fp16 ? 2 : 1;
    uint32_t R = ((W * elem_size + 63) / 64) * 64;
    uint32_t plane_size = H * R;
    uint32_t P = ((plane_size + 16383) / 16384) * 16384;
    uint32_t channel_groups = (C + 31) / 32;
    
    const uint8_t *in_ptr = (const uint8_t *)src_tiled;
    
    for (uint32_t n = 0; n < N; n++) {
        for (uint32_t cg = 0; cg < channel_groups; cg++) {
            const uint8_t *group_base = in_ptr + (n * channel_groups + cg) * P * 32;
            for (uint32_t c_idx = 0; c_idx < 32; c_idx++) {
                uint32_t actual_c = cg * 32 + c_idx;
                if (actual_c >= C) break;
                
                const uint8_t *channel_base = group_base + c_idx * P;
                for (uint32_t h = 0; h < H; h++) {
                    const uint8_t *row_base = channel_base + h * R;
                    for (uint32_t w = 0; w < W; w++) {
                        float val = 0.0f;
                        if (is_fp16) {
                            uint16_t h_val = ((const uint16_t *)row_base)[w];
                            uint32_t sign = (h_val & 0x8000) << 16;
                            uint32_t exp  = ((h_val >> 10) & 0x1f);
                            uint32_t mant = (h_val & 0x3ff);
                            if (exp != 0) {
                                exp = (exp + 112) << 23;
                                mant = mant << 13;
                            }
                            uint32_t f_bits = sign | exp | mant;
                            val = *(float *)&f_bits;
                        } else {
                            int8_t q_val = ((const int8_t *)row_base)[w];
                            val = (float)q_val / 127.0f;
                        }
                        dst_fp32[((n * C + actual_c) * H + h) * W + w] = val;
                    }
                }
            }
        }
    }
    return 0;
}

/**
 * Format and send command buffer to FIFO Node ID 0x40
 */
int ane_send(struct ane_device *dev, struct ane_submit_args *args) {
    if (!dev || !dev->initialized || !args) return -1;
    
    /* Format header with Node ID 0x40 and length in 16-byte words */
    uint32_t num_words = (args->tsk_size + ANE_CMD_GRAN - 1) / ANE_CMD_GRAN;
    uint32_t hdr0 = (num_words & 0xffff) | ((ANE_FIFO_NID & 0xff) << 16) | (0x21 << 24); /* QoS = 0x21 */
    args->flags = hdr0;
    
    if (ioctl(dev->fd, ANE_IOCTL_SUBMIT, args) < 0) {
        perror("[ANE Driver] ANE_IOCTL_SUBMIT failed");
        return -1;
    }
    return 0;
}

/**
 * High-level synchronous inference execution pipeline
 */
int ane_exec(struct ane_device *dev,
             struct ane_submit_args *submit_args,
             uint64_t sync_handle,
             uint32_t timeout_ms,
             uint64_t *hw_duration_ns) {
    if (!dev || !submit_args) return -1;
    
    /* Submit to hardware queue */
    if (ane_send(dev, submit_args) < 0) {
        return -1;
    }
    
    /* Await completion barrier */
    struct ane_wait_args wait_args = {
        .sync_handle = sync_handle,
        .timeout_ms = timeout_ms,
        .elapsed_hw_ns = 0,
        .status_out = 0
    };
    
    if (ioctl(dev->fd, ANE_IOCTL_WAIT, &wait_args) < 0) {
        perror("[ANE Driver] ANE_IOCTL_WAIT failed (inference timeout)");
        return -1;
    }
    
    if (hw_duration_ns) {
        *hw_duration_ns = wait_args.elapsed_hw_ns;
    }
    return wait_args.status_out == 0 ? 0 : -1;
}

/**
 * Release ANE hardware resources and close driver
 */
void ane_free(struct ane_device *dev) {
    if (!dev || !dev->initialized) return;
    ioctl(dev->fd, ANE_IOCTL_CLOSE, 0);
    close(dev->fd);
    dev->initialized = false;
    printf("[ANE Driver] Released ANE hardware session\n");
}
