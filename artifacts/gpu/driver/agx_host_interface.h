/**
 * @file agx_host_interface.h
 * @brief Clean-Room C99 Host Interface & AppleMetalDirect Wire Definitions
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap), Apple AGX G18P GPU (PI_300)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 * Driver Bundles:
 *   - com.apple.AGXG18P (v362.5)
 *   - com.apple.iokit.IOGPUFamily (v162.16.1)
 *   - com.apple.AGXFirmwareKextG18PRTBuddy (v1.0.0d1)
 *
 * GCC syntax verification: gcc -fsyntax-only -Wall -Wextra -std=c99
 */

#ifndef AGX_HOST_INTERFACE_H
#define AGX_HOST_INTERFACE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Hardware Architecture Constants                                        */
/* ========================================================================= */

#define AGX_PAGE_SIZE                 16384U       /* 16 KB native GPU page size */
#define AGX_PAGE_MASK                 16383U       /* 0x3FFF */
#define AGX_PAGE_SHIFT                14U          /* 14-bit page offset */

#define AGX_DESCRIPTOR_SIZE           64U          /* 64-byte command descriptor */
#define AGX_RING_CAPACITY_ENTRIES     1024U        /* Power-of-two queue depth */
#define AGX_RING_SIZE_BYTES           (AGX_RING_CAPACITY_ENTRIES * AGX_DESCRIPTOR_SIZE) /* 64 KB */
#define AGX_RING_INDEX_MASK           (AGX_RING_CAPACITY_ENTRIES - 1U)                  /* 0x3FF */

#define AGX_STATUS_PAGE_SIZE          16384U       /* 16 KB status page */
#define AGX_DOORBELL_PAGE_SIZE        16384U       /* 16 KB doorbell page */

#define AGX_GPU_VA_BITS               48U          /* 48-bit Virtual Addressing */
#define AGX_MAX_CONTEXTS              256U         /* Maximum active hardware contexts */
#define AGX_MAX_COMMAND_QUEUES        64U          /* Maximum queues per client */

/* ========================================================================= */
/* 2. Hardware Data Masters (DMs)                                            */
/* ========================================================================= */

typedef enum {
    AGX_DM_VDM   = 0,   /* Vertex / Meshlet Data Master (Geometry Phase) */
    AGX_DM_PDM   = 1,   /* Pixel / Primitive Data Master (Raster Phase) */
    AGX_DM_BLIT  = 2,   /* 2D Memory Blit / DMA Transfer Engine */
    AGX_DM_CDM   = 3    /* Compute Data Master (GPGPU & Ray Tracing RIA) */
} agx_data_master_t;

/* ========================================================================= */
/* 3. Hardware Command Opcodes                                               */
/* ========================================================================= */

typedef enum {
    AGX_CMD_3D_RENDER_PASS         = 0x01,  /* TBDR Render Pass (Vertex/Fragment) */
    AGX_CMD_COMPUTE_DISPATCH       = 0x02,  /* GPGPU Compute Kernel Execution */
    AGX_CMD_BLIT_2D                = 0x03,  /* 2D DMA Blit / Texture Sub-resource Copy */
    AGX_CMD_RAY_TRACING_DISPATCH   = 0x04,  /* RIA Hardware Ray Traversal & Shading */
    AGX_CMD_TILE_LOAD_STORE        = 0x05,  /* Tile Memory SRAM <-> DRAM Transfer */
    AGX_CMD_BLIT_COPY              = 0x06,  /* Extended Format Conversion Blit */
    AGX_CMD_BARRIER_FENCE          = 0x07,  /* Execution Barrier & USC Cache Flush */
    AGX_CMD_SHARED_EVENT_SIGNAL    = 0x08,  /* Metal SharedEvent Signal Token */
    AGX_CMD_SHARED_EVENT_WAIT      = 0x09,  /* Metal SharedEvent Wait Token */
    AGX_CMD_NOP                    = 0x0F   /* Hardware No-Operation Padding */
} agx_opcode_t;

/* ========================================================================= */
/* 4. Priority & Execution Flags                                             */
/* ========================================================================= */

typedef enum {
    AGX_PRIORITY_NORMAL    = 0,   /* Standard background / interactive render */
    AGX_PRIORITY_HIGH      = 1,   /* Foreground presentation queue */
    AGX_PRIORITY_REALTIME  = 2    /* VRR ProMotion display pacing deadline */
} agx_priority_t;

#define AGX_CMD_FLAG_COHERENT      (1U << 0)  /* Require system-level memory coherency */
#define AGX_CMD_FLAG_SYNC          (1U << 1)  /* Synchronous pipeline stall on entry */
#define AGX_CMD_FLAG_PROFILING     (1U << 2)  /* Emit detailed hardware timestamp trace */
#define AGX_CMD_FLAG_SECURE        (1U << 3)  /* Execute within SPTM/TXM protected domain */
#define AGX_CMD_FLAG_LATE_EVAL     (1U << 4)  /* Late evaluation event evaluation */

/* ========================================================================= */
/* 5. 64-Byte Command Descriptor Wire Format                                 */
/* ========================================================================= */

struct __attribute__((aligned(64))) agx_command_descriptor {
    union {
        struct {
            uint8_t   opcode;            /* [7:0]   Hardware Opcode (agx_opcode_t) */
            uint8_t   data_master : 4;   /* [11:8]  Target Data Master (0..3) */
            uint8_t   priority    : 4;   /* [15:12] Priority (0=Norm, 1=High, 2=RealTime) */
            uint16_t  flags;             /* [31:16] Execution Flags */
            uint32_t  context_id;        /* [63:32] Hardware Context Identifier */
        } bits;
        uint64_t raw_header;             /* 64-bit Packed Header */
    } hdr;                               /* 0x00 - 0x07 */

    uint64_t trace_id;                   /* 0x08 - 0x0F: Telemetry / profiling trace ID */
    uint64_t command_buffer_gpu_va;      /* 0x10 - 0x17: 64-bit GPU VA to command stream */

    union {
        struct {
            uint32_t  used_bytes;        /* [31:0]  Actual valid payload byte count */
            uint32_t  allocated_bytes;   /* [63:32] Page-aligned allocation size */
        } lengths;
        uint64_t raw_lengths;
    } buf_size;                          /* 0x18 - 0x1F */

    uint64_t fence_list_head;            /* 0x20 - 0x27: IOGPUIOFenceListHead pointer */

    union {
        struct {
            uint32_t  queue_index;       /* [31:0]  TimeStamp queue ring index */
            uint32_t  stamp_value;       /* [63:32] Expected completion timestamp */
        } stamp;
        uint64_t raw_stamp;
    } stamp_token;                       /* 0x28 - 0x2F */

    uint64_t parameter_buffer_desc;      /* 0x30 - 0x37: MList / MTileArray / VHeap / surface */
    uint64_t completion_event;           /* 0x38 - 0x3F: Metal SharedEvent completion token */
};

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_command_descriptor) == 64, "agx_command_descriptor must be 64 bytes");
#endif

/* ========================================================================= */
/* 6. 64-Bit PMPDoorbell Kick Token Layout                                   */
/* ========================================================================= */

typedef union {
    struct __attribute__((packed)) {
        uint16_t queue_id;               /* Bits 15:0:  Hardware Queue ID */
        uint32_t tail_offset;            /* Bits 47:16: 64-byte aligned ring byte offset */
        uint16_t flags;                  /* Bits 63:48: Kick flags (Bit 63: Priority Kick) */
    } fields;
    uint64_t raw_token;                  /* 64-bit atomic store payload */
} agx_doorbell_token_t;

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(agx_doorbell_token_t) == 8, "agx_doorbell_token_t must be 8 bytes");
#endif

/* ========================================================================= */
/* 7. Shared Circular Ring Buffer & Status Page                              */
/* ========================================================================= */

struct __attribute__((aligned(AGX_PAGE_SIZE))) agx_ring_buffer {
    struct agx_command_descriptor entries[AGX_RING_CAPACITY_ENTRIES];
};

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_ring_buffer) == 65536, "agx_ring_buffer must be exactly 64 KB");
#endif

struct __attribute__((aligned(AGX_PAGE_SIZE))) agx_status_page {
    volatile uint32_t completed_stamps[AGX_RING_CAPACITY_ENTRIES]; /* 4096 bytes: 0x0000 - 0x0FFF */
    volatile uint32_t firmware_heartbeat;                         /* 0x1000: RTBuddy Core 0 heartbeat counter */
    volatile uint32_t channel_error_code;                         /* 0x1004: Channel fault / SAPT error code */
    volatile uint32_t active_context_id;                          /* 0x1008: Currently executing context ID */
    volatile uint32_t recovery_counter;                           /* 0x100C: Hardware restart / recovery counter */
    volatile uint32_t firmware_read_index;                        /* 0x1010: Consumer ring read index (getReadIndex()) */
    volatile uint32_t firmware_cfi_index;                         /* 0x1014: Control Flow Integrity index (getCFIIndex()) */
    uint8_t           reserved[AGX_PAGE_SIZE - (AGX_RING_CAPACITY_ENTRIES * 4) - 24];
};

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_status_page) == 16384, "agx_status_page must be exactly 16 KB");
#endif

/* ========================================================================= */
/* 8. GPU Virtual Memory & Page Table Translation Hierarchy                  */
/* ========================================================================= */

/*
 * Radix 4-Level GPU Page Table Addressing (48-bit Virtual Address):
 *   [47:45] L0 Index (3 bits,  8 entries)
 *   [44:36] L1 Index (9 bits,  512 entries)
 *   [35:25] L2 Index (11 bits, 2048 entries)
 *   [24:14] L3 Index (11 bits, 2048 entries)
 *   [13:0]  Page Offset (14 bits, 16384 bytes)
 */

#define AGX_GPU_L0_SHIFT              45U
#define AGX_GPU_L0_MASK               0x07U
#define AGX_GPU_L1_SHIFT              36U
#define AGX_GPU_L1_MASK               0x1FFU
#define AGX_GPU_L2_SHIFT              25U
#define AGX_GPU_L2_MASK               0x7FFU
#define AGX_GPU_L3_SHIFT              14U
#define AGX_GPU_L3_MASK               0x7FFU
#define AGX_GPU_PAGE_OFFSET_MASK      0x3FFFU

static inline uint32_t agx_va_to_l0(uint64_t va) {
    return (uint32_t)((va >> AGX_GPU_L0_SHIFT) & AGX_GPU_L0_MASK);
}

static inline uint32_t agx_va_to_l1(uint64_t va) {
    return (uint32_t)((va >> AGX_GPU_L1_SHIFT) & AGX_GPU_L1_MASK);
}

static inline uint32_t agx_va_to_l2(uint64_t va) {
    return (uint32_t)((va >> AGX_GPU_L2_SHIFT) & AGX_GPU_L2_MASK);
}

static inline uint32_t agx_va_to_l3(uint64_t va) {
    return (uint32_t)((va >> AGX_GPU_L3_SHIFT) & AGX_GPU_L3_MASK);
}

static inline uint32_t agx_va_to_offset(uint64_t va) {
    return (uint32_t)(va & AGX_GPU_PAGE_OFFSET_MASK);
}

/* PTE Cacheability Attributes */
#define AGX_PTE_CACHE_COHERENT        0x00U  /* System Coherent (CPU/GPU unified) */
#define AGX_PTE_CACHE_WRITE_COMBINED  0x01U  /* Write-Combined (Ring buffers) */
#define AGX_PTE_CACHE_DEVICE_MMIO     0x02U  /* Non-cached Guarded Device IO */
#define AGX_PTE_CACHE_INNER_CACHED    0x03U  /* Inner Cacheable Private VRAM */

/* PTE Access Permissions */
#define AGX_PTE_AP_READ_WRITE         0x00U  /* Full Read / Write */
#define AGX_PTE_AP_READ_ONLY          0x01U  /* Read-Only */
#define AGX_PTE_AP_NO_ACCESS          0x02U  /* Guard Page / Unmapped */
#define AGX_PTE_AP_KERNEL_ONLY        0x03U  /* Supervisor / Firmware only */

typedef union {
    struct {
        uint64_t valid         : 1;   /* [0]    Page is present */
        uint64_t table         : 1;   /* [1]    1=Table descriptor, 0=Block descriptor */
        uint64_t cache_attr    : 2;   /* [3:2]  Cacheability attribute */
        uint64_t reserved_0    : 2;   /* [5:4]  Reserved */
        uint64_t ap            : 2;   /* [7:6]  Access permission */
        uint64_t shareability  : 2;   /* [9:8]  Shareability: 2=Outer, 3=Inner */
        uint64_t access_flag   : 1;   /* [10]   Accessed flag */
        uint64_t non_global    : 1;   /* [11]   Non-global (ASID/DSID tagged) */
        uint64_t reserved_1    : 2;   /* [13:12] Reserved */
        uint64_t pfn           : 34;  /* [47:14] Physical Frame Number (16 KB aligned) */
        uint64_t reserved_2    : 6;   /* [53:48] Reserved */
        uint64_t execute_never : 1;   /* [54]   XN - Execute Never */
        uint64_t dart_stream_id: 9;   /* [63:55] DART Stage-2 Domain / Stream Tag */
    } bits;
    uint64_t raw_pte;
} agx_gpu_pte_t;

#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(agx_gpu_pte_t) == 8, "agx_gpu_pte_t must be 8 bytes");
#endif

/* ========================================================================= */
/* 9. Host XNU IOKit UserClient Boundary & Selectors                         */
/* ========================================================================= */

typedef enum {
    AGX_UC_NEW_COMMAND_QUEUE               = 0,
    AGX_UC_DELETE_COMMAND_QUEUE            = 1,
    AGX_UC_NEW_RESOURCE                    = 2,
    AGX_UC_SUBMIT_COMMAND_BUFFERS          = 3,
    AGX_UC_ASYNC_SIGNAL_MTL_LATE_EVAL_EVENT= 4,
    AGX_UC_QUERY_MTL_LATE_EVAL_EVENT       = 5,
    AGX_UC_SIGNAL_SHARED_EVENT             = 6,
    AGX_UC_WAIT_SHARED_EVENT               = 7,
    AGX_UC_CREATE_IO_COMMAND_QUEUE         = 8,
    AGX_UC_SUBMIT_IO_COMMANDS              = 9,
    AGX_UC_METHOD_COUNT                    = 10
} agx_user_client_selector_t;

/* IOGPU Memory Mapping Types */
typedef enum {
    IOGPU_CLIENT_MEMORY_COMMAND_RING       = 0,  /* Type 0: 64 KB Write-Combined Ring */
    IOGPU_CLIENT_MEMORY_STATUS_PAGE        = 1,  /* Type 1: 16 KB Read-Only Status Page */
    IOGPU_CLIENT_MEMORY_DOORBELL           = 2   /* Type 2: 16 KB Write-Only MMIO Doorbell */
} iogpu_client_memory_type_t;

/* Userclient Method Structs */
struct __attribute__((aligned(8))) agx_uc_new_queue_args {
    uint32_t ring_capacity;      /* Requested entries (1024) */
    uint32_t priority;           /* Queue priority (0=Norm, 1=High, 2=RealTime) */
    uint32_t flags;              /* Initial flags */
    uint32_t context_id;         /* Desired context identifier */
    uint64_t client_token;       /* Userland callback token */
    uint8_t  reserved[40];       /* Reserved for future extensions */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_new_queue_args) == 64, "agx_uc_new_queue_args must be 64 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_new_queue_output {
    uint32_t queue_id;           /* Allocated Hardware Queue ID */
    uint32_t ring_size;          /* Size of mapped ring buffer (65536) */
    uint64_t ring_user_addr;     /* User virtual address of Ring Buffer */
    uint64_t status_user_addr;   /* User virtual address of Status Page */
    uint64_t doorbell_user_addr; /* User virtual address of PMPDoorbell */
    uint8_t  reserved[96];       /* Capability tokens and firmware handles */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_new_queue_output) == 128, "agx_uc_new_queue_output must be 128 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_new_resource_args {
    uint64_t gpu_virtual_address;/* Requested or bound GPU VA */
    uint64_t allocation_size;    /* Byte size (16 KB aligned) */
    uint32_t memory_type;        /* Buffer, Texture, Parameter, Private */
    uint32_t cache_mode;         /* Cacheability flags */
    uint32_t protection;         /* VM Protection flags */
    uint32_t flags;              /* Allocation flags */
    uint64_t iosurface_id;       /* Shared IOSurface ID (0 if private) */
    uint8_t  reserved[56];       /* Subsystem parameters */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_new_resource_args) == 96, "agx_uc_new_resource_args must be 96 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_new_resource_output {
    uint64_t mapped_gpu_va;      /* Actual mapped GPU Virtual Address */
    uint64_t resident_size;      /* Physical resident bytes */
    uint32_t dart_token;         /* DART Stage-2 registration token */
    uint32_t status;             /* Result status */
    uint8_t  reserved[40];       /* Alignment pad */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_new_resource_output) == 64, "agx_uc_new_resource_output must be 64 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_submit_args {
    uint32_t queue_id;               /* Target queue ID */
    uint32_t num_command_buffers;    /* Number of descriptors in payload */
    uint64_t command_descriptors_ptr;/* Userland pointer to descriptor batch */
    uint64_t fence_head;             /* Head of wait fence list */
    uint8_t  payload[232];           /* Inlined command descriptors for fast IPC */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_submit_args) == 256, "agx_uc_submit_args must be 256 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_io_queue_args {
    uint32_t queue_type;         /* Direct storage read/write stream */
    uint32_t priority;           /* IO priority */
    uint64_t max_commands;       /* Maximum concurrent IO commands */
    uint64_t storage_fd;         /* Target file descriptor */
    uint8_t  reserved[24];
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_io_queue_args) == 48, "agx_uc_io_queue_args must be 48 bytes");
#endif

struct __attribute__((aligned(8))) agx_uc_io_queue_output {
    uint32_t io_queue_id;        /* Hardware IO Queue ID */
    uint32_t ring_capacity;      /* Capacity */
    uint64_t queue_desc_va;      /* GPU VA of IO Queue ring */
    uint8_t  reserved[16];
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_io_queue_output) == 32, "agx_uc_io_queue_output must be 32 bytes");
#endif

/* Selector 4: s_async_signal_mtlLateEvalevent (In: 32 bytes) */
struct __attribute__((aligned(8))) agx_uc_late_eval_signal_args {
    uint64_t shared_event_id;    /* Target Metal SharedEvent ID */
    uint64_t signal_value;       /* Monotonic value to signal */
    uint32_t context_id;         /* Calling context ID */
    uint32_t flags;              /* Late eval flags */
    uint8_t  reserved[8];
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_late_eval_signal_args) == 32, "agx_uc_late_eval_signal_args must be 32 bytes");
#endif

/* Selector 5: s_query_mtlLateEvalevent (Out: 16 bytes) */
struct __attribute__((aligned(8))) agx_uc_late_eval_query_output {
    uint64_t current_value;      /* Current signaled value */
    uint32_t status;             /* 0=Pending, 1=Resolved, 2=TimedOut */
    uint32_t reserved;
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_late_eval_query_output) == 16, "agx_uc_late_eval_query_output must be 16 bytes");
#endif

/* Selector 9: s_submit_io_commands (In: 128 bytes) */
struct __attribute__((aligned(8))) agx_uc_submit_io_args {
    uint32_t io_queue_id;        /* Target IO Queue ID */
    uint32_t num_commands;       /* Number of streaming IO commands */
    uint64_t io_commands_ptr;    /* Pointer to MTLIOCommandBuffer payload */
    uint64_t destination_gpu_va; /* Target GPU virtual address buffer */
    uint64_t file_offset;        /* Source byte offset in storage */
    uint64_t read_byte_count;    /* Total bytes to stream */
    uint8_t  reserved[88];       /* Decompression parameters & completion tokens */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_uc_submit_io_args) == 128, "agx_uc_submit_io_args must be 128 bytes");
#endif

/* Kernel IOSharedLock Structure */
struct __attribute__((aligned(8))) agx_io_shared_lock {
    volatile uint32_t owner_thread_id; /* Thread ID holding lock */
    volatile uint32_t ticket_now;      /* Current served ticket */
    volatile uint32_t ticket_next;     /* Next issued ticket */
    volatile uint32_t flags;           /* Contention / recursion flags */
};
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(struct agx_io_shared_lock) == 16, "agx_io_shared_lock must be 16 bytes");
#endif

/* ========================================================================= */
/* 10. Direct Submission Client Context                                      */
/* ========================================================================= */

typedef struct agx_direct_client {
    struct agx_ring_buffer*      ring;             /* Mapped write-combined ring buffer */
    struct agx_status_page*      status;           /* Mapped read-only status page */
    volatile uint64_t*           doorbell_mmio;    /* Mapped write-only PMPDoorbell page */
    uint32_t                     queue_id;         /* Hardware Queue ID from kernel */
    uint32_t                     write_index;      /* Local producer tail index */
    uint32_t                     next_stamp;       /* Monotonic completion stamp counter */
    uint32_t                     context_id;       /* Bound hardware context identifier */
} agx_direct_client_t;

/* ========================================================================= */
/* 11. Helper Inline Functions & Hardware Accessors                          */
/* ========================================================================= */

static inline void agx_client_init(
    agx_direct_client_t* client,
    void* ring_vaddr,
    void* status_vaddr,
    void* doorbell_vaddr,
    uint32_t queue_id,
    uint32_t context_id
) {
    client->ring = (struct agx_ring_buffer*)ring_vaddr;
    client->status = (struct agx_status_page*)status_vaddr;
    client->doorbell_mmio = (volatile uint64_t*)doorbell_vaddr;
    client->queue_id = queue_id;
    client->write_index = 0;
    client->next_stamp = 1;
    client->context_id = context_id;
}

/**
 * @brief Check whether direct submission ring buffer has capacity for next descriptor
 *
 * Evaluates the RTBuddy firmware consumer read index against producer write index.
 * Aborts if channel error code indicates a hardware/DART Stage-2 fault.
 */
static inline bool agx_ring_has_space(const agx_direct_client_t* client) {
    if (client->status->channel_error_code != 0) {
        return false; /* Channel is halted / faulted */
    }
    uint32_t head = client->status->firmware_read_index & AGX_RING_INDEX_MASK;
    uint32_t next_tail = (client->write_index + 1U) & AGX_RING_INDEX_MASK;
    return (next_tail != head);
}

static inline uint32_t agx_ring_entries_used(const agx_direct_client_t* client) {
    uint32_t head = client->status->firmware_read_index & AGX_RING_INDEX_MASK;
    uint32_t tail = client->write_index & AGX_RING_INDEX_MASK;
    return (tail >= head) ? (tail - head) : (AGX_RING_CAPACITY_ENTRIES - (head - tail));
}

static inline uint32_t agx_ring_entries_available(const agx_direct_client_t* client) {
    return (AGX_RING_CAPACITY_ENTRIES - 1U) - agx_ring_entries_used(client);
}

static inline bool agx_client_has_error(const agx_direct_client_t* client) {
    return client->status->channel_error_code != 0;
}

static inline uint64_t agx_make_doorbell_token(uint16_t queue_id, uint32_t tail_offset, uint16_t flags) {
    agx_doorbell_token_t tok = { .raw_token = 0 };
    tok.fields.queue_id = queue_id;
    tok.fields.tail_offset = tail_offset;
    tok.fields.flags = flags;
    return tok.raw_token;
}

/* ========================================================================= */
/* 12. Client Function Declarations                                          */
/* ========================================================================= */

uint32_t agx_encode_render_pass(
    agx_direct_client_t* client,
    uint64_t command_stream_va,
    uint32_t stream_size_bytes,
    uint64_t parameter_scene_alloc_va,
    uint64_t fence_list_head,
    uint64_t completion_event,
    uint16_t flags,
    agx_priority_t priority
);

uint32_t agx_encode_compute_dispatch(
    agx_direct_client_t* client,
    uint64_t kernel_stream_va,
    uint32_t stream_size_bytes,
    uint64_t threadgroup_desc_va,
    uint64_t fence_list_head,
    uint64_t completion_event,
    uint16_t flags,
    agx_priority_t priority
);

uint32_t agx_encode_blit_2d(
    agx_direct_client_t* client,
    uint64_t blit_cmd_stream_va,
    uint32_t stream_size_bytes,
    uint64_t surface_bindings_va,
    uint64_t fence_list_head,
    uint64_t completion_event
);

uint32_t agx_encode_ray_tracing_dispatch(
    agx_direct_client_t* client,
    uint64_t shader_binding_table_va,
    uint32_t sbt_size_bytes,
    uint64_t bvh_acceleration_structure_va,
    uint64_t fence_list_head,
    uint64_t completion_event,
    agx_priority_t priority
);

uint32_t agx_direct_submit_kick(agx_direct_client_t* client, uint16_t kick_flags);

bool agx_client_poll_completion(const agx_direct_client_t* client, uint32_t slot, uint32_t expected_stamp);

#ifdef __cplusplus
}
#endif

#endif /* AGX_HOST_INTERFACE_H */
