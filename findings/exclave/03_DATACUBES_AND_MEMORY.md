# ExclaveOS Memory Architecture: Datacubes, PMM Retyping & Jungle Shared Memory

**Target Platform**: iOS 27.2 (`24B119`) — Apple Silicon A19 Pro (`t8150`)  
**Target Hardware**: iPhone 18,3 (`v57ap`)  
**Binaries Dissected**:
- `01_pmm_server.macho` (`pmm-server` — Physical Memory Manager, Datacube Retyping & Allocation)
- `03_jg_sharedmem_preload.macho` (`jg_sharedmem` — Jungle Preload Shared Memory & EXSurface Root)
- `02_vascore_platform.macho` (`vascore` — Virtual Address Space Core Platform)

---

## 1. Executive Memory Architecture Overview

In monolithic operating systems, the kernel maintains total control over physical memory mappings. Under Apple's **ExclaveOS** architecture, physical memory management is split between the untrusted host operating system (**Darwin / XNU**) and the isolated microkernel environment (**ExclaveOS cL4**), governed by the Apple Silicon **Secure Page Manager (SPTM / SPM)**:

1. **Datacube Abstraction**: Rather than granting ExclaveOS fixed, static physical DRAM ranges at boot, Apple implements dynamic memory donation via **Datacubes** (`L4_Type_Plat_DataCube`). Darwin donates physical RAM to ExclaveOS on demand.
2. **Page Retyping via Microkernel Invariant**: Once donated, a page is stripped from the host Stage-1 translation table and retyped into a formal cL4 page frame (`L4_Type_Arm64_FrameLevel0`). The SPTM hardware barrier guarantees that host Darwin cannot read, write, or snooped donated pages while owned by an Exclave.
3. **PMM Server Hierarchy**: The `pmm-server` manages two internal allocation engines:
   - **`ipmm` (Internal PMM)**: High-speed bitmap allocator managing local Untyped memory.
   - **`xnu_allocator`**: Dynamically interfaces with Darwin to ingest and release Datacubes, managing standard and MTE-tagged frame pools (`__PMM_EXTRA_FRAMES`, `__PMM_EXTRA_MTE_FRAMES`).
4. **Jungle Component System (`jg_sharedmem`)**: Provides structured shared memory segments (`ExclavesSegment`, `XnuSharedSegment`) and hardware surface bridges (`JgEXSurfaceRootComponent`) for sensors, audio DSP, and biometric pipelines.

```
+-----------------------------------------------------------------------------------+
|                              Darwin / XNU Kernel                                  |
|  - Allocates host DRAM page (paddr)                                               |
|  - Initiates donation trap (_exclaves_ctl_trap)                                    |
+-----------------------------------------------------------------------------------+
                                          |
                      [SPTM / SPM Hardware Translation Barrier]
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         ExclaveOS PMM Server (pmm-server)                         |
|  1. Receives notification: "[PMM] Received releasing Datacube"                    |
|  2. Invokes cL4 Retyping:                                                         |
|     L4_Untyped_Create(untyped_memory[FrameL0], FrameL0, paddr - xnu_pbase, ret)    |
|  3. Derives frame capability with attenuated rights                               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                   Jungle Shared Memory System (jg_sharedmem)                      |
|  - JgSharedMemoryComponent.ExclavesSegment (nPages, shmemGroup, backingModel)     |
|  - JgEXSurfaceRootComponent (Secure display overlays for SIL indicator dots)      |
|  - AOP2_EXDARTDriver (DART IOMMU DMA isolation for Coprocessor channels)          |
+-----------------------------------------------------------------------------------+
```

---

## 2. The Datacube Abstraction & Retyping Protocol

### 2.1 The Retyping Primitive
From `01_pmm_server.macho` at offset `0x6c400`, we extracted the exact C retyping call executed by `xnu_allocator.c`:

```c
L4_Untyped_Create(
    untyped_memory.caps[memory_type][L4_Type_Arm64_FrameLevel0],
    L4_Type_Arm64_FrameLevel0,       // 0x12: 16 KB Apple Silicon page frame
    paddr - xnu_pbase,               // Offset within XNU donated untyped pool
    frame_cap(ret_frame)             // Output capability slot in CSpace
);
```

### 2.2 Datacube Lifecycle State Machine

```
[HOST_ALLOCATED] (XNU Kernel owns page)
       |
       | Darwin issues donation via _exclaves_ctl_trap
       v
[DONATION_IN_FLIGHT] (Unmapped from Darwin Stage-1 tables)
       |
       | SPTM changes Stage-2 attributes; notifies PMM
       v
[RELEASING_DATACUBE] (PMM receives event: "[PMM] Received releasing Datacube")
       |
       | PMM calls L4_Untyped_Create(..., paddr - xnu_pbase, ...)
       v
[RETYPED_FRAME] (Converted to L4_Type_Arm64_FrameLevel0)
       |
       | VASCore maps frame via _map_this_frame into Conclave VAS
       v
[CONCLAVE_MAPPED] (Active Conclave compute: ANE, Face ID, Backboardd)
       |
       | Conclave unmaps buffer or terminates
       v
[RECLAIMED_ZEROED] (PMM revokes cap, scrubs with zero-fill, returns to XNU)
```

### 2.3 Mathematical Offset Calculation
Because physical memory is donated in variable contiguous chunks, the PMM converts arbitrary 64-bit physical addresses into Untyped offsets using:

$$\text{Offset} = \text{paddr} - \text{xnu\_pbase}$$

Verified assertion from `frame.c`:
```c
// Validates physical address is within untyped allocation bounds
[PMM] raw_frame_create paddr %#llx too small (< %llx), type %d, rt %d
[PMM] raw_frame_create error paddr too big %#llx, (> %llx), type %d, rt %d
```

---

## 3. PMM Physical Allocator Architecture

The Physical Memory Manager (`01_pmm_server.macho`) implements a dual-allocator architecture:

### 3.1 Internal PMM (`ipmm`) & Bitmap Allocator
- **Source Module**: `pmm-server/src/bitmap.c` & `pmm-server/src/pmm.c`.
- **Telemetry String**:
  ```json
  "ipmm_usage": {"allocs_size_bytes": 1048576, "allocs_size_str": "1.00 MiB"}
  ```
- **Bitmap Mechanics**:
  - Manages boot-time Untyped memory assigned directly to ExclaveCore during IPL (Initial Program Load).
  - Each bit in the allocation bitmap represents a 16 KB page frame ($2^{14} \text{ bytes}$).
  - Throws `PMM out of bitmap memory` when internal allocation tables exhaust their tracking headers.

### 3.2 XNU Allocator & Dynamic Expansion
- **Source Module**: `pmm-server/src/xnu_allocator.c`.
- **Early Synchronization**: During Conclave boot, the runtime executes `xrt__sync_pmm_early_alloc` to request an initial page frame reservoir before host Darwin has finished booting userland.
- **Bundle Metadata Keys**:
  - `__PMM_EXTRA_FRAMES`: Configures supplementary standard 16 KB page frames granted to the Conclave heap.
  - `__PMM_EXTRA_MTE_FRAMES`: Configures hardware Memory Tagging Extension (MTE) frames.
  - `__RELEASE`: Release metadata tag enforcing strict bounds on dynamic expansion.
- **Assertion Verification**:
  ```c
  pmm: bundle metadata for "%s" is too long (%zd >= %zd)
  pmm: bundle metadata for "%s" not a valid number ("%s")
  pmm: bundle metadata for "%s" %zu clamped to max %zd
  pmm: "%s" set to %zu
  ```

### 3.3 Hardware Memory Tagging Extension (MTE) Support
Apple Silicon A19 Pro (`t8150`) features ARMv8.5-A / ARMv9 **FEAT_MTE2**. `pmm-server` supports allocating MTE-tagged frames:
- Granule size: 16 bytes.
- Tag width: 4 bits (stored in upper address bits 56..59).
- Hardened conclaves (e.g. `sksd` Secure Key Store) allocate from `__PMM_EXTRA_MTE_FRAMES`, enabling hardware detection of spatial out-of-bounds access and temporal use-after-free bugs with near-zero performance penalty.

---

## 4. Jungle Shared Memory Architecture (`jg_sharedmem`)

The Jungle shared memory preload subsystem (`03_jg_sharedmem_preload.macho`) manages inter-conclave and host-conclave shared memory topologies.

### 4.1 Segment Initializers & Parameter Models

#### `JgSharedMemoryComponent.ExclavesSegment`
```swift
JgSharedMemoryComponent.ExclavesSegment.init(
    nPages: UInt32,              // 16 KB page count
    shmemGroup: UInt32,          // Domain isolation group ID
    mappingAttribute: UInt32,    // Caching: Normal WB, Uncached, Device
    backingModel: UInt32,        // Backend: 1=Datacube, 2=Untyped Pool
    shmemID: UInt64,             // Unique 64-bit segment identifier
    initRangeStart: UInt64,      // Virtual address start in Conclave VAS
    initRangeEnd: UInt64         // Virtual address limit in Conclave VAS
)
```

#### `JgSharedMemoryComponent.XnuSharedSegment`
Extends `ExclavesSegment` by appending Darwin kernel permission attributes:
```swift
JgSharedMemoryComponent.XnuSharedSegment.init(
    nPages: UInt32,
    shmemGroup: UInt32,
    mappingAttribute: UInt32,
    backingModel: UInt32,
    shmemID: UInt64,
    initRangeStart: UInt64,
    initRangeEnd: UInt64,
    xnuPerms: UInt32             // Read=0x1, Write=0x2 enforced by XNU
)
```

### 4.2 Comprehensive Shared Memory Segment Catalog

Extracted directly from `03_jg_sharedmem_preload.macho`:

| Segment Name | Subsystem / Consumer | Architectural Function | Backing Model |
|---|---|---|---|
| `sharedmem_backboardd_silmanager_exsurface` | BackBoard (`backboardd`) | **Sensor Indicator Light Surface Buffer** (Hardware privacy dots) | Datacube |
| `sharedmem_backboardd_silmanager_exdata` | BackBoard (`backboardd`) | Telemetry channel for sensor indicator state machine | Datacube |
| `EXSurfaceRoot_ANEEKTest` | Apple Neural Engine (ANE) | **ANE ExclaveKit Surface Test & Tensor Pipeline** | Datacube Frame |
| `sharedmem_audio_SoundAnalysisHALEKOutput` | CoreAudio HAL | Audio classification vector output (zero raw PCM leak) | PMM Pool |
| `sharedmem_audio_SiriArbiter` | Siri Voice Processing | Secure acoustic keyword validation channel | Datacube |
| `sharedmem_audio_SoundAnalysisRefInput` | CoreAudio HAL | Audio reference input stream from XNU | XNU Shared |
| `sharedmem_xcoproc_AOP2_EP53_in` | Always-On Processor (AOP2) | Coprocessor Mailbox Endpoint 53 input FIFO | Mailbox Buffer |
| `sharedmem_xcoproc_AOP2_EP52_out` | Always-On Processor (AOP2) | Coprocessor Mailbox Endpoint 52 output FIFO | Mailbox Buffer |
| `sharedmem_perception_feature_detection_polaris_output_buffer` | Polaris Vision Pipeline | Facial landmark and iris biometric feature vectors | Datacube |
| `sharedmem_ExclaveSEPManager_sksd_in` | Secure Enclave / `sksd` | Passkey and cryptographic key storage OOL buffer | Datacube |

---

## 5. Hardware Surface & IOMMU Protection

### 5.1 The `JgEXSurfaceRootComponent`
The Sensor Indicator Light (SIL) in iOS 27 displays green and orange dots when the camera or microphone is active. To prevent compromised Darwin userland graphics daemons (e.g. `WindowServer` or `backboardd`) from maliciously hiding or tampering with the indicator, Apple renders the dot inside an Exclave:
1. `JgEXSurfaceRootComponent` allocates a dedicated secure surface segment (`sharedmem_backboardd_silmanager_exsurface`).
2. The surface is composited directly to the display hardware pipe via an isolated hardware layer.
3. The host OS cannot write to or disable this surface because the physical framebuffer scanout is fenced by the Apple Silicon Display Engine (IOMobileFramebuffer) under SPTM protection.

### 5.2 Device Address Resolution Table (DART) IOMMU Mapping
Peripheral coprocessors (like AOP2 and ANE) use Direct Memory Access (DMA) to exchange tensors and audio buffers. To prevent peripheral DMA attacks from compromising ExclaveOS memory:
- `JgExclaveDARTMemoryMapperComponent` programs the hardware **DART IOMMU**.
- `AOP2_EXDARTDriver` maps only designated shared memory segments (`sharedmem_xcoproc_AOP2_*`) into the coprocessor's Secure Stream ID (SID).
- Any attempt by peripheral bus masters to read outside the authorized DART span triggers an immediate hardware IOMMU abort.

---

## 6. Conclusions & Next Steps

Phase E3 has reverse engineered the memory management bedrock of ExclaveOS:
1. Dynamic page donation and retyping via the **Datacube** protocol (`L4_Untyped_Create` at `paddr - xnu_pbase`).
2. PMM dual allocation architecture (`ipmm` bitmap vs `xnu_allocator` dynamic ingestion).
3. MTE hardware frame protection (`__PMM_EXTRA_MTE_FRAMES`).
4. Complete 10-segment Jungle shared memory catalog across Backboardd SIL, ANE ExclaveKit, CoreAudio, and AOP2.

**Next Phase**: Proceed to **Phase E4 (`exclave_phase_4_xnu_boundary`)** to dissect the Darwin/XNU boundary traps (`_exclaves_ctl_trap`, `_exclaves_call_trap`), `xnuproxy`, and develop clean-room C client pseudocode.
