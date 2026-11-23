/*
 * silenus_host_interface.h — Clean-Room C99 Interface Specification
 * Apple Silicon A19 Pro (t8150) Camera ISP (Silenus) Host Driver Boundary
 *
 * Targets: AppleH16CameraInterface.kext, AppleH16CamIn, DART-ISP & Volchok X3357
 * Platform: Apple Silicon A19 Pro (t8150 / iPhone18,3 v57ap) — iOS 27.2 (24B119)
 */

#ifndef SILENUS_HOST_INTERFACE_H
#define SILENUS_HOST_INTERFACE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Hardware MMIO Bases, Apertures & AIC Interrupt Vectors                 */
/* ========================================================================= */

#define DART_ISP_BASE_ADDR              0x00000001128c0000ULL
#define DART_ISP_APERTURE_SIZE          0x00010000ULL   /* 64 KB aperture    */
#define DART_ISP_PAGE_SIZE              16384ULL        /* 16 KB page granule*/
#define DART_ISP_SID_CAPACITY           16

/* AIC Interrupt Vectors */
#define AIC_IRQ_DART_ISP_FAULT          302             /* 0x012e: DART fault*/
#define AIC_IRQ_ISP_FRAME_DONE          284             /* 0x011c: Frame done*/
#define AIC_IRQ_ISP_STATS_READY         285             /* 0x011d: 3A stats  */
#define AIC_IRQ_ISP_DMA_ERROR           286             /* 0x011e: Bus error */
#define AIC_IRQ_ISP_CIL_BREAKER         287             /* 0x011f: CIL trip  */
#define AIC_IRQ_ISP_MAILBOX_EVENT       297             /* 0x0129: Mailbox   */

/* Core ISP Memory Apertures */
#define ISP_CORE_SRAM_REG_BASE          0x0000000101000000ULL
#define ISP_CORE_SRAM_REG_SIZE          0x0000000003ffc000ULL /* 63.98 MB   */
#define ISP_CONTROL_REGS_BASE           0x00000000f0700000ULL
#define ISP_CONTROL_REGS_SIZE           0x0000000000018000ULL /* 96 KB      */
#define ISP_SIF_SENSOR_IF_BASE          0x00000000f0724000ULL
#define ISP_SIF_SENSOR_IF_SIZE          0x0000000000004000ULL /* 16 KB      */

/* ========================================================================= */
/* 2. DART-ISP IOMMU Stream Identifiers (SIDs)                               */
/* ========================================================================= */

#define DART_ISP_SID_CONTROL            0x00    /* Host control & descriptors */
#define DART_ISP_SID_RAW_STREAM         0x01    /* Raw Bayer sensor ingest    */
#define DART_ISP_SID_BNI_PEARL          0x02    /* BNI FaceID NIR (to SEP)    */
#define DART_ISP_SID_YUV_PREVIEW        0x03    /* YUV preview & display plane*/
#define DART_ISP_SID_EXCLAVE_EPIPE0     0x04    /* Exclave secure engine pipe0*/
#define DART_ISP_SID_EXCLAVE_EPIPE1     0x05    /* Exclave secure engine pipe1*/
#define DART_ISP_SID_EXCLAVE_PIODMA1    0x09    /* Exclave PIO DMA 1          */
#define DART_ISP_SID_MPM                0x0c    /* Multi-Plane Memory surface */

/* ========================================================================= */
/* 3. DART-ISP Hardware Register Layout                                      */
/* ========================================================================= */

struct dart_isp_bank0_regs {
    volatile uint32_t config;           /* 0x00: DART configuration register  */
    volatile uint32_t tlb_inval;        /* 0x04: TLB invalidation trigger     */
    volatile uint32_t tlb_inval_addr;   /* 0x08: Invalidation target DVA      */
    volatile uint32_t reserved0;        /* 0x0C: Reserved                     */
    volatile uint32_t fault_status;     /* 0x10: Fault interrupt status       */
    volatile uint32_t fault_addr_lo;    /* 0x14: Faulting DVA low 32 bits     */
    volatile uint32_t fault_addr_hi;    /* 0x18: Faulting DVA high 32 bits    */
    volatile uint32_t fault_sid;        /* 0x1C: Faulting Stream ID           */
    volatile uint32_t ttbr_base[16];    /* 0x20..0x5C: Translation table base */
} __attribute__((packed));

/* ========================================================================= */
/* 4. CISP Command Channel Opcodes & Message Envelope                         */
/* ========================================================================= */

#define CISP_MAGIC                      0x43495350      /* 'CISP' ASCII       */
#define IOP_RINGBUFFER_VERSION_V2       0x0002

/* Core Control Opcodes */
#define CISP_CMD_PING                   0x0001
#define CISP_CMD_START                  0x0002
#define CISP_CMD_STOP                   0x0003
#define CISP_CMD_SUSPEND                0x0004
#define CISP_CMD_POWER_DOWN             0x0005
#define CISP_CMD_RESET                  0x0006

/* Channel Streaming Opcodes */
#define CISP_CMD_CH_START               0x0010
#define CISP_CMD_CH_STOP                0x0011
#define CISP_CMD_CH_CONFIG              0x0012
#define CISP_CMD_CH_PROCESS_BUFFERS     0x0020
#define CISP_CMD_CH_RETURN_BUFFERS      0x0021

/* Biometric & FaceID (Pearl) Opcodes */
#define CISP_CMD_FID_ENTER              0x0030
#define CISP_CMD_FID_EXIT               0x0031

/* Lens Actuator & Stabilization (Volchok) Opcodes */
#define CISP_CMD_CH_VA_ACTUATOR_SET     0x0040
#define CISP_CMD_CH_VA_ACTUATOR_GET     0x0041
#define CISP_CMD_CH_VA_DIAMETER_SET     0x0042
#define CISP_CMD_CH_VA_RUN_MODE_SET     0x0043

/* Cross-Coprocessor IPC Opcodes */
#define CISP_CMD_IPC_ENDPOINT_SET2      0x0050
#define CISP_CMD_IPC_ENDPOINT_UNSET2    0x0051

/* Command Header (16 bytes) */
struct cisp_command_header {
    uint32_t magic;             /* 'CISP' (0x43495350)                        */
    uint16_t opcode;            /* CISP_CMD_* opcode                          */
    uint16_t sequence_id;       /* Monotonically increasing command sequence  */
    uint8_t  channel_id;        /* Streaming channel index (0..3)             */
    uint8_t  flags;             /* Command flags (bit 0: async response req)  */
    uint16_t payload_len;       /* Length of following payload in bytes       */
    uint32_t status;            /* Return status code (0 = success)           */
} __attribute__((packed));

/* Command Packet (64 bytes fixed envelope) */
struct cisp_command_packet {
    struct cisp_command_header header;  /* 16 bytes                           */
    union {
        uint8_t  raw[48];
        struct {
            uint32_t surface_id;
            uint64_t dva_luma;
            uint64_t dva_chroma;
            uint32_t width;
            uint32_t height;
            uint32_t stride;
            uint32_t frame_index;
            uint32_t timestamp_lo;
            uint32_t timestamp_hi;
        } buffer_process;
        struct {
            int32_t  af_position;
            int32_t  ois_shift_x;
            int32_t  ois_shift_y;
            uint32_t gyro_timestamp;
            uint16_t coil_current_ma[4];
        } actuator_ctrl;
    } payload;
} __attribute__((packed));

/* ========================================================================= */
/* 5. RTKit Ring Buffer Layout (IOP_RINGBUFFER_VERSION_V2)                   */
/* ========================================================================= */

struct isp_ring_buffer_header_v2 {
    uint32_t version;           /* High 16 bits = IOP_RINGBUFFER_VERSION_V2   */
    volatile uint32_t wrptr;    /* Write offset in buffer (atomic)            */
    volatile uint32_t rdptr;    /* Read offset in buffer (atomic)             */
    uint32_t buffer_size;       /* Capacity in bytes                          */
    uint32_t entry_size;        /* Fixed descriptor size in bytes             */
    uint32_t flags;             /* Ring control flags                         */
    uint64_t dart_dva;          /* DART Virtual Address of ring backing memory*/
    uint8_t  reserved[32];      /* Cache line alignment padding (64 bytes)    */
} __attribute__((packed));

/* ========================================================================= */
/* 6. IOSharedDataQueue Memory Structure                                      */
/* ========================================================================= */

struct IODataQueueEntry {
    uint32_t size;              /* Size of payload following this header      */
    uint8_t  data[1];           /* Variable-length event payload              */
} __attribute__((packed));

struct IODataQueueMemory {
    uint32_t queue_size;        /* Total allocated capacity of queue          */
    volatile uint32_t head;     /* Queue read pointer offset                  */
    volatile uint32_t tail;     /* Queue write pointer offset                 */
    struct IODataQueueEntry entries[1]; /* Base of contiguous entry memory    */
} __attribute__((packed));

/* UserClient Process Buffer Arguments (48 bytes) */
struct h16_isp_process_buffer_args {
    uint32_t surface_id;        /* IOSurface identifier                       */
    uint32_t channel_index;     /* Active camera channel                      */
    uint64_t luma_dva;          /* DART Virtual Address of Y plane            */
    uint64_t chroma_dva;        /* DART Virtual Address of CbCr plane         */
    uint32_t width;             /* Surface width in pixels                    */
    uint32_t height;            /* Surface height in pixels                   */
    uint32_t bytes_per_row;     /* Row stride in bytes                        */
    uint32_t frame_flags;       /* Bit 0: AE bracketed, Bit 1: FaceID         */
    uint32_t client_cookie;     /* User-space context reference               */
    uint32_t reserved;          /* Alignment padding                          */
} __attribute__((packed));

/* ========================================================================= */
/* 7. ARM Platform Function Interface Prototypes                             */
/* ========================================================================= */

typedef void* IOService_t;
typedef void* IOMemoryDescriptor_t;

/* Function pointer types matching kernel exports */
typedef uint64_t (*isp_map_iobmd_fn)(IOService_t provider,
                                     IOMemoryDescriptor_t desc,
                                     uint32_t stream_id,
                                     uint32_t flags);

typedef void (*isp_unmap_iobmd_fn)(IOService_t provider,
                                   uint64_t dva,
                                   uint32_t stream_id);

typedef int (*isp_ref_clk_fn)(IOService_t provider,
                              uint32_t clk_idx,
                              uint64_t target_hz);

#ifdef __cplusplus
}
#endif

#endif /* SILENUS_HOST_INTERFACE_H */
