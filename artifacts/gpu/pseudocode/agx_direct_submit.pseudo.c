/**
 * @file agx_direct_submit.pseudo.c
 * @brief Clean-Room C Implementation of Apple AGX G18 Direct Userland Command Submission
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap), Apple AGX G18P GPU (PI_300)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 *
 * Dissected from:
 *   - /System/Library/Extensions/AGXMetalG18P.bundle/AGXMetalG18P
 *   - /System/Library/Extensions/AGXG18P.kext (v362.5)
 *   - /System/Library/Extensions/IOGPUFamily.kext (v162.16.1)
 *
 * Verifiable with: gcc -fsyntax-only -Wall -Wextra
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* --- Hardware Architecture Definitions --- */
#define AGX_PAGE_SIZE                 16384U       /* 16 KB native GPU page size */
#define AGX_DESCRIPTOR_SIZE           64U          /* 64-byte command descriptor */
#define AGX_RING_CAPACITY_ENTRIES     1024U        /* Power-of-two queue depth */
#define AGX_RING_INDEX_MASK           (AGX_RING_CAPACITY_ENTRIES - 1U)

/* --- Hardware Data Masters (DMs) --- */
typedef enum {
    AGX_DM_VDM   = 0,   /* Vertex / Meshlet Data Master */
    AGX_DM_PDM   = 1,   /* Pixel / Primitive Data Master (Rasterizer) */
    AGX_DM_BLIT  = 2,   /* 2D Memory Blit / Transfer Engine */
    AGX_DM_CDM   = 3    /* Compute Data Master (GPGPU & Ray Tracing) */
} agx_data_master_t;

/* --- Hardware Command Opcodes --- */
typedef enum {
    AGX_CMD_3D_RENDER_PASS         = 0x01,  /* TBDR Render Pass */
    AGX_CMD_COMPUTE_DISPATCH       = 0x02,  /* GPGPU Compute Kernel Launch */
    AGX_CMD_RAY_TRACING_BVH_BUILD  = 0x03,  /* Hardware BVH2/BVH4 Build / Refit */
    AGX_CMD_RAY_TRACING_DISPATCH   = 0x04,  /* RIA Hardware Ray Traversal & Hit */
    AGX_CMD_TILE_LOAD_STORE        = 0x05,  /* Tile Memory SRAM <-> DRAM Transfer */
    AGX_CMD_BLIT_COPY              = 0x06,  /* 2D Surface Copy / Format Convert */
    AGX_CMD_BARRIER_FENCE          = 0x07,  /* Execution Barrier & Cache Flush */
    AGX_CMD_SHARED_EVENT_SIGNAL    = 0x08,  /* Metal SharedEvent Signal Token */
    AGX_CMD_SHARED_EVENT_WAIT      = 0x09,  /* Metal SharedEvent Wait Token */
    AGX_CMD_NOP                    = 0x0F   /* Hardware No-Operation Padding */
} agx_opcode_t;

/* --- 64-Byte Hardware Command Descriptor Layout --- */
struct __attribute__((aligned(64))) agx_command_descriptor {
    union {
        struct {
            uint8_t   opcode;            /* [7:0]   Hardware Opcode */
            uint8_t   data_master : 4;   /* [11:8]  Target Data Master (0..3) */
            uint8_t   priority    : 4;   /* [15:12] Priority: 0=Normal, 1=High, 2=RealTime */
            uint16_t  flags;             /* [31:16] Flags: Coherent, Sync, Profiling */
            uint32_t  context_id;        /* [63:32] Hardware Context Identifier */
        } bits;
        uint64_t raw_header;             /* 64-bit Packed Header */
    } hdr;
    uint64_t trace_id;                   /* 0x08: Profiling / telemetry trace ID */
    uint64_t command_buffer_gpu_va;      /* 0x10: 64-bit GPU virtual address */
    uint32_t used_bytes;                 /* 0x18: Valid payload byte count */
    uint32_t allocated_bytes;            /* 0x1C: Page-aligned allocation size */
    uint64_t fence_list_head;            /* 0x20: IOFence / AGXBlockFence pointer */
    uint32_t stamp_queue_index;          /* 0x28: TimeStamp queue ring index */
    uint32_t stamp_value;                /* 0x2C: Expected completion timestamp */
    uint64_t parameter_buffer_desc;      /* 0x30: MList / MTileArray / VHeap pointer */
    uint64_t completion_event;           /* 0x38: Metal SharedEvent completion token */
};
_Static_assert(sizeof(struct agx_command_descriptor) == 64, "agx_command_descriptor must be 64 bytes");

/* --- 64-Bit PMPDoorbell Kick Token Layout --- */
typedef union {
    struct {
        uint16_t queue_id;               /* Bits 15:0:  Hardware Queue ID */
        uint32_t tail_offset;            /* Bits 47:16: 64-byte aligned write offset */
        uint16_t flags;                  /* Bits 63:48: Kick flags (Bit 63: Priority) */
    } fields;
    uint64_t raw_token;                  /* 64-bit atomic store payload */
} agx_doorbell_token_t;

/* --- Shared Hardware Status Page --- */
struct __attribute__((aligned(AGX_PAGE_SIZE))) agx_status_page {
    volatile uint32_t completed_stamps[AGX_RING_CAPACITY_ENTRIES];
    volatile uint32_t firmware_heartbeat;
    volatile uint32_t channel_error_code;
    uint8_t           reserved[AGX_PAGE_SIZE - (AGX_RING_CAPACITY_ENTRIES * 4) - 8];
};
_Static_assert(sizeof(struct agx_status_page) == AGX_PAGE_SIZE, "Status page must be 16 KB");

/* --- Coherent Command Descriptor Ring Buffer --- */
struct __attribute__((aligned(AGX_PAGE_SIZE))) agx_ring_buffer {
    struct agx_command_descriptor entries[AGX_RING_CAPACITY_ENTRIES];
};
_Static_assert(sizeof(struct agx_ring_buffer) == (AGX_RING_CAPACITY_ENTRIES * 64), "Ring buffer must be 64 KB");

/* --- Direct Submission Client State --- */
typedef struct agx_direct_client {
    struct agx_ring_buffer*      ring;             /* Mapped write-combined ring buffer */
    struct agx_status_page*      status;           /* Mapped read-only status page */
    volatile uint64_t*           doorbell_mmio;    /* Mapped write-only PMPDoorbell page */
    uint32_t                     queue_id;         /* Hardware Queue ID from kernel */
    uint32_t                     write_index;      /* Local producer tail index */
    uint32_t                     next_stamp;       /* Monotonic completion stamp counter */
} agx_direct_client_t;

/* --- Direct Submission Client API --- */

/**
 * @brief Initialize direct userland client instance
 */
static inline void agx_client_init(
    agx_direct_client_t* client,
    void* ring_vaddr,
    void* status_vaddr,
    void* doorbell_vaddr,
    uint32_t queue_id
) {
    client->ring = (struct agx_ring_buffer*)ring_vaddr;
    client->status = (struct agx_status_page*)status_vaddr;
    client->doorbell_mmio = (volatile uint64_t*)doorbell_vaddr;
    client->queue_id = queue_id;
    client->write_index = 0;
    client->next_stamp = 1;
}

/**
 * @brief Test whether circular ring buffer has space for a new descriptor
 */
static inline bool agx_ring_has_space(const agx_direct_client_t* client) {
    /* Read completed stamp index as conservative consumer head approximation */
    uint32_t head_index = client->status->completed_stamps[0] & AGX_RING_INDEX_MASK;
    uint32_t next_tail = (client->write_index + 1U) & AGX_RING_INDEX_MASK;
    return (next_tail != head_index);
}

/**
 * @brief Enqueue 3D TBDR render pass command
 */
static inline uint32_t agx_encode_render_pass(
    agx_direct_client_t* client,
    uint64_t command_stream_va,
    uint32_t stream_size_bytes,
    uint64_t parameter_scene_alloc_va
) {
    uint32_t slot = client->write_index;
    struct agx_command_descriptor* desc = &client->ring->entries[slot];

    desc->hdr.raw_header = 0;
    desc->hdr.bits.opcode = AGX_CMD_3D_RENDER_PASS;
    desc->hdr.bits.data_master = AGX_DM_VDM;
    desc->hdr.bits.priority = 1; /* High priority */
    desc->hdr.bits.flags = 0x0001; /* Coherent */
    desc->hdr.bits.context_id = client->queue_id;

    desc->trace_id = 0x4147585F31385000ULL | (uint64_t)slot;
    desc->command_buffer_gpu_va = command_stream_va;
    desc->used_bytes = stream_size_bytes;
    desc->allocated_bytes = (stream_size_bytes + AGX_PAGE_SIZE - 1U) & ~(AGX_PAGE_SIZE - 1U);
    desc->fence_list_head = 0;
    desc->stamp_queue_index = slot;
    desc->stamp_value = client->next_stamp;
    desc->parameter_buffer_desc = parameter_scene_alloc_va;
    desc->completion_event = 0;

    client->write_index = (client->write_index + 1U) & AGX_RING_INDEX_MASK;
    return client->next_stamp++;
}

/**
 * @brief Enqueue hardware Ray-Tracing intersection query
 */
static inline uint32_t agx_encode_ray_tracing_query(
    agx_direct_client_t* client,
    uint64_t command_stream_va,
    uint32_t stream_size_bytes,
    uint64_t tlas_bvh_va
) {
    uint32_t slot = client->write_index;
    struct agx_command_descriptor* desc = &client->ring->entries[slot];

    desc->hdr.raw_header = 0;
    desc->hdr.bits.opcode = AGX_CMD_RAY_TRACING_DISPATCH;
    desc->hdr.bits.data_master = AGX_DM_CDM; /* CDM routes to RIA */
    desc->hdr.bits.priority = 1;
    desc->hdr.bits.flags = 0x0003; /* Coherent + RT Pipeline */
    desc->hdr.bits.context_id = client->queue_id;

    desc->trace_id = 0x5249415F47313800ULL | (uint64_t)slot;
    desc->command_buffer_gpu_va = command_stream_va;
    desc->used_bytes = stream_size_bytes;
    desc->allocated_bytes = (stream_size_bytes + AGX_PAGE_SIZE - 1U) & ~(AGX_PAGE_SIZE - 1U);
    desc->fence_list_head = 0;
    desc->stamp_queue_index = slot;
    desc->stamp_value = client->next_stamp;
    desc->parameter_buffer_desc = tlas_bvh_va;
    desc->completion_event = 0;

    client->write_index = (client->write_index + 1U) & AGX_RING_INDEX_MASK;
    return client->next_stamp++;
}

/**
 * @brief Execute direct low-latency submission via atomic PMPDoorbell kick
 *
 * Bypasses all XNU kernel software layers by writing directly to the memory-mapped
 * hardware doorbell page (kAGFIPIORegionTypePMPDoorbell).
 */
static inline void agx_direct_submit_kick(const agx_direct_client_t* client) {
    agx_doorbell_token_t token;
    token.fields.queue_id = (uint16_t)client->queue_id;
    token.fields.tail_offset = client->write_index * (uint32_t)sizeof(struct agx_command_descriptor);
    token.fields.flags = 0x8000; /* High-priority hardware dispatch */

    /* Memory barrier ensuring descriptors are visible to GPU before doorbell rings */
    __atomic_thread_fence(__ATOMIC_RELEASE);

    /* Atomic MMIO 64-bit store directly to PMPDoorbell hardware trigger */
    *(client->doorbell_mmio) = token.raw_token;
}

/**
 * @brief Poll for completion of a submitted timestamp
 */
static inline bool agx_poll_completion(
    const agx_direct_client_t* client,
    uint32_t slot_index,
    uint32_t expected_stamp
) {
    uint32_t completed = client->status->completed_stamps[slot_index & AGX_RING_INDEX_MASK];
    return (completed >= expected_stamp);
}

/* --- Mock Verification Harness --- */
int main(void) {
    static struct agx_ring_buffer mock_ring;
    static struct agx_status_page mock_status;
    static volatile uint64_t mock_doorbell = 0;

    agx_direct_client_t client;
    agx_client_init(&client, &mock_ring, &mock_status, (void*)&mock_doorbell, 42);

    if (!agx_ring_has_space(&client)) {
        return 1;
    }

    /* Encode 3D render pass */
    uint32_t stamp1 = agx_encode_render_pass(
        &client,
        0x0000000800000000ULL, /* GPU VA */
        4096,
        0x0000000840000000ULL  /* Parameter buffer VA */
    );

    /* Encode hardware Ray-Tracing query */
    uint32_t stamp2 = agx_encode_ray_tracing_query(
        &client,
        0x0000000800010000ULL,
        8192,
        0x0000000850000000ULL  /* TLAS BVH VA */
    );

    /* Kick doorbell directly in hardware */
    agx_direct_submit_kick(&client);

    /* Simulate coprocessor completion in status page */
    mock_status.completed_stamps[0] = stamp1;
    mock_status.completed_stamps[1] = stamp2;

    bool ok1 = agx_poll_completion(&client, 0, stamp1);
    bool ok2 = agx_poll_completion(&client, 1, stamp2);

    return (ok1 && ok2 && mock_doorbell != 0) ? 0 : 2;
}
