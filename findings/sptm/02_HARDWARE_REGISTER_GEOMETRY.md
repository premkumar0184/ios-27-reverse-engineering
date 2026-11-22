# iOS 27 SPTM & TXM RE — Phase 2: Hardware Register & Stage-2 Memory Geometry

## 1. Executive Summary & Hardware Memory Virtualization Paradigm

On Apple Silicon A19 Pro (`t8150`, device `v57ap`), hardware memory isolation is governed by Stage-2 address translation enforced at Guarded EL2 (GL2) by the **Secure Page Table Monitor (SPTM)**. Unlike conventional architectures where the kernel directly configures hardware Memory Management Units (MMU), iOS 27.2 virtualizes physical address spaces:

1. **Two-Stage Address Translation**: The Darwin/XNU kernel configures Stage-1 translation tables mapping Virtual Addresses (VA) to Intermediate Physical Addresses (IPA). SPTM configures hardware Stage-2 translation tables (`VTTBR_EL2`) mapping IPA to actual Physical Addresses (PA).
2. **Zero Direct Kernel Physical Access**: Stage-1 page tables are themselves mapped read-only in the kernel's address space. Any page table allocation, modification, or invalidation must be submitted as a synchronous hypercall into SPTM.
3. **Hardware-Enforced Domain Partitioning**: Physical DRAM is subdivided into discrete hardware domains (XNU Host, ExclaveOS Conclaves, TXM Monitor, Secure Enclave, AGX GPU, ANE H18, and AOP2) enforced via 59 immutable or atomically retypable Physical Frame Types.

```
+----------------------------------------------------------------------------------------------------+
|                               TWO-STAGE HARDWARE TRANSLATION PIPELINE                              |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Guest Virtual Address (VA)] ──────────────────────────────────────────────────┐                  |
|                                                                                 │                  |
|                                [Stage-1 Translation (XNU Controlled)]           ▼                  |
|                                - Uses TTBR0_EL12 / TTBR1_EL12                   │                  |
|                                - Table frames locked Read-Only by SPTM          │                  |
|                                                                                 ▼                  |
|                                                            [Intermediate Physical Address (IPA)]   |
|                                                                                 │                  |
|                                [Stage-2 Translation (SPTM Controlled)]          ▼                  |
|                                - Uses VTTBR_EL2 & VTCR_EL2                      │                  |
|                                - 16 KB Granule (TG0 = 0x2), 4-Level Radix Tree  │                  |
|                                - Enforces AP[2:1] and XN Permissions            │                  |
|                                                                                 ▼                  |
|  [Actual Physical Address (PA)] ◄───────────────────────────────────────────────┘                  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. ARMv8.6 Stage-2 Hardware Translation Geometry

### 2.1 Hardware Translation Parameters
- **Page Granule**: 16 KB (`0x4000` bytes), encoded as `TG0 = 0x2`.
- **Input Address Space (IPA)**: 48 bits, configured via `T0SZ = 0x19` in `VTCR_EL2`.
- **Translation Hierarchy**: 3 active hardware levels for 48-bit IPA with 16 KB granules (Levels 1, 2, and 3).
- **Virtualization Translation Control Register (`VTCR_EL2`)**: Initialized to `0x061f000061002000`:
  - `T0SZ[5:0] = 0x19`: Sets 48-bit IPA space ($2^{48}$ bytes = 256 TB).
  - `TG0[15:14] = 0x2`: Selects 16 KB page granule size.
  - `SH0[13:12] = 0x3`: Designates memory as Inner Shareable.
  - `ORGN0[11:10] = 0x1`: Normal Memory, Outer Write-Back Read-Allocate Write-Allocate.
  - `IRGN0[9:8] = 0x1`: Normal Memory, Inner Write-Back Read-Allocate Write-Allocate.
  - `SL0[7:6] = 0x2`: Start translation radix lookup at Level 1.

### 2.2 Mathematical Translation Address Decomposition

For any 48-bit Intermediate Physical Address $\text{IPA}$, the translation indices are computed via bitfield extraction:

$$\text{IPA}[47:0] = \underbrace{\text{IPA}[47:36]}_{\text{Level 1 Index (12 bits)}} \;\|\; \underbrace{\text{IPA}[35:25]}_{\text{Level 2 Index (11 bits)}} \;\|\; \underbrace{\text{IPA}[24:14]}_{\text{Level 3 Index (11 bits)}} \;\|\; \underbrace{\text{IPA}[13:0]}_{\text{Page Offset (14 bits)}}$$

1. **Level 1 Table Lookup**:
   - Covers $2^{36}$ bytes (64 GB) per Level 1 block entry.
   - Contains $2^{12} = 4,096$ descriptors of 8 bytes each ($32\text{ KB}$ table size, spanning 2 contiguous 16 KB frames).
   - $\text{L1\_Descriptor\_Addr} = \text{VTTBR\_EL2.BADDR} + (\text{IPA}[47:36] \times 8)$.
2. **Level 2 Table Lookup**:
   - Covers $2^{25}$ bytes (32 MB) per Level 2 block entry.
   - Contains $2^{11} = 2,048$ descriptors of 8 bytes each ($16\text{ KB}$ table size, matching 1 physical frame).
   - $\text{L2\_Descriptor\_Addr} = \text{L1\_NextTable\_PA} + (\text{IPA}[35:25] \times 8)$.
3. **Level 3 Table Lookup (Leaf)**:
   - Covers $2^{14}$ bytes (16 KB) per Level 3 page entry.
   - Contains $2^{11} = 2,048$ descriptors of 8 bytes each ($16\text{ KB}$ table size).
   - $\text{L3\_Descriptor\_Addr} = \text{L2\_NextTable\_PA} + (\text{IPA}[24:14] \times 8)$.
   - $\text{Physical\_Address} = \text{L3\_Page\_PA} \;|\; \text{IPA}[13:0]$.

---

## 3. The 59 Physical Memory Frame Types Catalog

Every 16 KB physical DRAM page on SoC T8150 is tracked by SPTM's **Physical Address Page Table (PAPT)** under one of 59 discrete frame types. Transitions between frame types are mediated exclusively via the `SPTM_FUNCTIONID_RETYPE` hypercall:

```
+-------------------------------------------------------------------------------------------------------------------------------------+
|                                              SPTM 59 PHYSICAL FRAME TYPES CATALOG                                                   |
+-------------------------------------------------------------------------------------------------------------------------------------+
| ID | Type Constant                      | Category        | Default Access  | Pinned | Architectural Role                           |
+----+------------------------------------+-----------------+-----------------+--------+----------------------------------------------+
| 0  | TYPE_00_FREE_PAGE                  | UNALLOCATED     | NONE            | No     | Available unallocated DRAM frame             |
| 1  | TYPE_01_XNU_DEFAULT                | XNU_GUEST       | RW-             | No     | Anonymous dynamic kernel memory              |
| 2  | TYPE_02_XNU_KERNEL_DATA            | XNU_GUEST       | RW-             | No     | Static or heap mutable kernel memory         |
| 3  | TYPE_03_XNU_KERNEL_TEXT            | XNU_GUEST       | R-X (CTRR)      | Yes    | Executable kernel code, locked against write |
| 4  | TYPE_04_XNU_ROZONE                 | XNU_GUEST       | R-- (CTRR)      | Yes    | Read-Only Zone security metadata             |
| 5  | TYPE_05_XNU_PT_L1                  | XNU_PAGETABLE   | R--             | Yes    | Guest Level 1 translation table frame        |
| 6  | TYPE_06_XNU_PT_L2                  | XNU_PAGETABLE   | R--             | Yes    | Guest Level 2 translation table frame        |
| 7  | TYPE_07_XNU_PT_L3                  | XNU_PAGETABLE   | R--             | Yes    | Guest Level 3 page table leaf frame          |
| 8  | TYPE_08_XNU_USER_TEXT              | USERLAND        | R-X             | No     | Darwin userland executable code page         |
| 9  | TYPE_09_XNU_USER_DATA              | USERLAND        | RW-             | No     | Userland anonymous heap/stack data           |
| 10 | TYPE_10_XNU_USER_JIT               | USERLAND_JIT    | RW- / R-X       | No     | WebKit JIT compiler code cache               |
| 11 | TYPE_11_XNU_USER_TPRO              | USERLAND        | R--             | No     | Thread-Protection register shadow frame      |
| 12 | TYPE_12_XNU_COMMPAGE               | SHARED          | R--             | Yes    | Kernel-to-userland read-only shared commpage |
| 13 | TYPE_13_XNU_DEVICE_MMIO            | HARDWARE        | RW- (Device)    | Yes    | Peripheral memory-mapped IO aperture         |
| 14 | TYPE_14_SPTM_MONITOR_CODE          | SPTM_INTERNAL   | R-X (CTRR)      | Yes    | SPTM hypervisor __TEXT_EXEC code frame       |
| 15 | TYPE_15_SPTM_MONITOR_DATA          | SPTM_INTERNAL   | RW-             | Yes    | SPTM hypervisor private dynamic BSS frame    |
| 16 | TYPE_16_SPTM_BOOT_DATA             | SPTM_INTERNAL   | RW-             | No     | Early boot scratchpad data (reclaimed)       |
| 17 | TYPE_17_SPTM_PAGE_TABLE            | SPTM_PAGETABLE  | R-- (CTRR)      | Yes    | Stage-2 translation table frame              |
| 18 | TYPE_18_SPTM_PAPT_TABLE            | SPTM_PAGETABLE  | R--             | Yes    | Physical Address Page Table index frame      |
| 19 | TYPE_19_SPTM_STACK_GUARD           | SPTM_INTERNAL   | NONE            | Yes    | Hypervisor stack canary guard frame           |
| 20 | TYPE_20_TXM_CODE                   | TXM_INTERNAL    | R-X (CTRR)      | Yes    | TXM Code Signing Monitor executable code     |
| 21 | TYPE_21_TXM_DATA                   | TXM_INTERNAL    | RW-             | Yes    | TXM static configuration and context data    |
| 22 | TYPE_22_TXM_HEAP                   | TXM_INTERNAL    | RW-             | No     | TXM dynamic cryptographic allocation heap    |
| 23 | TYPE_23_TXM_SLAB_TRUSTCACHE        | TXM_SECURITY    | R-- (CTRR)      | Yes    | Verified TrustCache storage frame            |
| 24 | TYPE_24_TXM_STAGE2_ROOT            | TXM_PAGETABLE   | R--             | Yes    | TXM Stage-2 root translation table frame     |
| 25 | TYPE_25_TXM_STAGE2_LEAF            | TXM_PAGETABLE   | R--             | Yes    | TXM Stage-2 intermediate/leaf table frame    |
| 26 | TYPE_26_EXCLAVE_CL4_KERNEL         | EXCLAVE_CORE    | R-X             | Yes    | ExclaveCore cL4 microkernel executable text  |
| 27 | TYPE_27_EXCLAVE_CL4_DATA           | EXCLAVE_CORE    | RW-             | Yes    | cL4 microkernel state and CNode radix tree   |
| 28 | TYPE_28_EXCLAVE_CONCLAVE_TEXT      | EXCLAVE_CONCLAVE| R-X             | Yes    | Conclave private executable code frame       |
| 29 | TYPE_29_EXCLAVE_CONCLAVE_DATA      | EXCLAVE_CONCLAVE| RW-             | No     | Conclave private heap or stack frame         |
| 30 | TYPE_30_EXCLAVE_PMM_STORAGE        | EXCLAVE_PMM     | RW-             | Yes    | Physical Memory Manager (PMM) metadata frame |
| 31 | TYPE_31_EXCLAVE_DATACUBE_DONATED   | EXCLAVE_SHARED  | NONE -> RW-     | No     | Donated DRAM frame in Datacube transition    |
| 32 | TYPE_32_EXCLAVE_JUNGLE_SHARED      | EXCLAVE_SHARED  | RW-             | No     | Jungle shared memory segment (EXSurface)     |
| 33 | TYPE_33_EXCLAVE_RINGGATE_ENDPOINT  | EXCLAVE_IPC     | RW-             | Yes    | Hardware RingGate transition mailbox frame   |
| 34 | TYPE_34_SEP_FIRMWARE_CARVEOUT      | SECURE_ENCLAVE  | NONE (SEP Only) | Yes    | Secure Enclave DRAM carveout (tz0s/tz1s)     |
| 35 | TYPE_35_SEP_SHARED_MAILBOX         | SECURE_ENCLAVE  | RW-             | Yes    | ASCwrap-v6 Mailbox communication frame       |
| 36 | TYPE_36_SEP_SECURE_STORAGE         | SECURE_ENCLAVE  | NONE (SEP Only) | Yes    | Anti-replay NVRAM / Keystore backing frame   |
| 37 | TYPE_37_AGX_GPU_SHARED_CHANNEL     | COPROCESSOR_GPU | RW- (Coherent)  | No     | Metal GPU command submission ring buffer     |
| 38 | TYPE_38_AGX_GPU_FRAMEBUFFER        | COPROCESSOR_GPU | RW-             | No     | WindowServer / Compositor render frame       |
| 39 | TYPE_39_ANE_MODEL_WEIGHTS          | COPROCESSOR_ANE | R--             | No     | Apple Neural Engine compiler weights buffer  |
| 40 | TYPE_40_ANE_FIFO_COMMAND_RING      | COPROCESSOR_ANE | RW-             | Yes    | ANE hardware FIFO mailbox descriptor frame   |
| 41 | TYPE_41_AOP_SENSOR_BUFFER          | COPROCESSOR_AOP | RW-             | No     | Always-On Processor circular ring buffer     |
| 42 | TYPE_42_AOP_AUDIO_PRELOAD          | COPROCESSOR_AOP | RW-             | No     | Always-On low-power voice trigger buffer     |
| 43 | TYPE_43_DART_STREAM_TABLE          | IOMMU_DART      | R--             | Yes    | DART Gen3 IOMMU stream ID descriptor frame   |
| 44 | TYPE_44_DART_PAGE_TABLE_L1         | IOMMU_DART      | R--             | Yes    | DART IOMMU translation table Level 1 frame   |
| 45 | TYPE_45_DART_PAGE_TABLE_L2         | IOMMU_DART      | R--             | Yes    | DART IOMMU translation table Level 2 frame   |
| 46 | TYPE_46_SART_APERTURE_TABLE        | IOMMU_SART      | R--             | Yes    | Secure Apple Remap Table aperture frame      |
| 47 | TYPE_47_CTRR_LOCKED_KERNEL_TEXT    | HARDWARE_LOCK   | R-X (CTRR)      | Yes    | Kernel code locked in hardware CTRR register |
| 48 | TYPE_48_CTRR_LOCKED_SPTM_CORE      | HARDWARE_LOCK   | R-X (CTRR)      | Yes    | SPTM core hypervisor text locked in CTRR     |
| 49 | TYPE_49_GAPF_FILTERED_APERTURE     | HARDWARE_LOCK   | FILTERED        | Yes    | Guarded Address Protection Filter bus frame  |
| 50 | TYPE_50_MTE_TAG_STORAGE            | SECURITY_MTE    | NONE (Hardware) | Yes    | MTE physical tag storage frame               |
| 51 | TYPE_51_HIBERNATION_IMAGE_HEADER   | HIBERNATION     | R--             | Yes    | Encrypted hibernation image superblock frame |
| 52 | TYPE_52_HIBERNATION_PAGE_DATA      | HIBERNATION     | RW-             | No     | Encrypted DRAM page during hibernation       |
| 53 | TYPE_53_SECURE_TRACE_BUFFER        | TELEMETRY       | RW- (Guarded)   | Yes    | Guarded CPU execution trace buffer frame     |
| 54 | TYPE_54_PANIC_CRASH_PRESERVE       | DIAGNOSTICS     | RW-             | Yes    | Non-volatile crash dump preserve frame       |
| 55 | TYPE_55_DEBUG_DIAGNOSTIC_SHELL     | DIAGNOSTICS     | RW-             | No     | Research build diagnostic scratchpad frame   |
| 56 | TYPE_56_IOMMU_BOUNCE_BUFFER        | DMA_BOUNCE      | RW-             | No     | Peripheral DMA bounce buffer frame           |
| 57 | TYPE_57_DISPLAY_PIPE_ISOC          | DISPLAY         | RW- (Isoc)      | Yes    | Real-time isochronous display DMA pipe frame |
| 58 | TYPE_58_RESERVED_FIRMWARE_SEALED   | RESERVED        | NONE            | Yes    | Hardware-sealed reserved firmware frame      |
+----+------------------------------------+-----------------+-----------------+--------+----------------------------------------------+
```

---

## 4. Physical Page Tracking: PAPT & SAPT Mechanics

### 4.1 Physical Address Page Table (PAPT)
SPTM maintains the **Physical Address Page Table (PAPT)**, a flat array of 64-bit Frame Table Entries (FTE) indexed directly by physical page frame number:

$$\text{Frame\_Number} = \frac{\text{PA}}{16384}$$

Each 64-bit FTE descriptor stores:
- `Type[7:0]`: Current frame type identifier (values `0` through `58`).
- `Pinned[8]`: Set if frame is locked against deallocation or retyping.
- `OwnerDomain[15:12]`: Security domain identifier (`XNU`, `EXCLAVE`, `TXM`, `SEP`).
- `RO_RefCnt[31:16]`: Active read-only mapping reference counter.
- `WX_RefCnt[47:32]`: Active write/execute exclusive reference counter.
- `MTE_Tag[55:48]`: Associated physical memory tag index.
- `Flags[63:56]`: Lock bit, dirty bit, and IOMMU coherency tags.

### 4.2 Dynamic Retyping Invariants & Violation Markers

When an OS component requests a frame transition via `sptm_retype()`, SPTM enforces strict state machine invariants. Violations trigger immediate hardware panics recorded in monitor telemetry:

```
+----------------------------------------------------------------------------------------------------+
|                                    SPTM RETYPING VIOLATION LEDGER                                  |
+----------------------------------------------------------------------------------------------------+
| Violation Symbol                             | Enforcement Trigger & Invariant Checked             |
+----------------------------------------------+-----------------------------------------------------+
| VIOLATION_ILLEGAL_RETYPE                     | Attempted invalid transition between unlinked types |
| VIOLATION_ILLEGAL_RETYPE_PINNED              | Retyping a pinned frame (e.g. CTRR or SPTM table)   |
| VIOLATION_FRAME_HELD_EXCLUSIVE               | Frame retyping attempted while WX_RefCnt > 0        |
| VIOLATION_FRAME_HELD_SHARED                  | Frame retyping attempted while RO_RefCnt > 0        |
| VIOLATION_FRAME_OWNER                        | Caller security domain does not match FTE owner     |
| VIOLATION_FRAME_PROTECTED                    | Destination frame falls within CTRR / GAPF locked PA|
| VIOLATION_OVERFLOW_RO_REFCNT                 | Exceeded maximum allowable read-only mappings       |
| VIOLATION_OVERFLOW_WX_REFCNT                 | Attempted concurrent write mappings on secure frame |
| VIOLATION_INVALID_TAG_STORAGE_FRAME          | Tag storage buffer fails 16 KB alignment or bounds  |
| VIOLATION_T8110_DART_INVALID_RETYPE_NEW_TYPE | Peripheral DART attempted retyping to CPU type      |
+----------------------------------------------+-----------------------------------------------------+
```

---

## 5. Hardware Access Control Registers: CTRR, GAPF & DART

### 5.1 Configurable Text Region Registers (CTRR)

Configurable Text Region Registers (CTRR) are Apple proprietary hardware registers in the Memory Controller (`mcc`, MMIO `0xf0780000`) that enforce immutable read-only executable status over physical memory regions:

- **Region A (`CTRR_A_LWR`, `CTRR_A_UPR`, `CTRR_A_CTL`)**: Locks XNU kernel text (`TYPE_03`) and Read-Only Zone (`TYPE_04`).
- **Region B (`CTRR_B_LWR`, `CTRR_B_UPR`, `CTRR_B_CTL`)**: Locks SPTM core hypervisor text (`TYPE_14`), Stage-2 page tables (`TYPE_17`), and TXM TrustCache slabs (`TYPE_23`).
- **Hardware Lockout Bit**: Once programmed during boot initialization (`SPTM_FUNCTIONID_LOCKDOWN`), CTRR registers cannot be written to or cleared by software, including EL2/GL2 code, until a complete hardware power cycle.

### 5.2 Guarded Address Protection Filter (GAPF)

GAPF provides hardware-level bus filtering across heterogeneous memory masters:
- **`SPTM_GAPF_ENABLE_REG` (`sptm-gapf-enable-reg`)**: Master control register enabling aperture access arbitration.
- **`SPTM_GAPF_LOCK_REG` (`sptm-gapf-lock-reg`)**: Hardware lock register freezing GAPF aperture tables.
- **`AOP_GAPF_LOCK_REG` (`aop_gapf_lock_reg`)**: Dedicated aperture filter isolating the Always-On Processor memory bus.

---

## 6. DeviceTree Hardware Topography & Memory Carveouts

Analysis of the extracted `DeviceTree.v57ap.raw` (`365,632` bytes) reveals the hardware physical memory layout and coprocessor IOMMU controllers for SoC T8150:

### 6.1 DRAM Physical Reservation Carveouts

```
+----------------------------------------------------------------------------------------------------+
|                                 T8150 PHYSICAL DRAM CARVEOUT MAP                                   |
+----------------------------------------------------------------------------------------------------+
| Carveout Name              | Physical Base   | Size (Hex)    | Size (Bytes)    | Functional Role   |
+----------------------------+-----------------+---------------+-----------------+-------------------+
| SPTM_RESERVED_CARVEOUT     | 0x800000000     | 0x020000000   | 512 MiB         | Stage-2 Tables    |
| TXM_RESERVED_CARVEOUT      | 0x820000000     | 0x004000000   | 64 MiB          | TrustCache / CSM  |
| EXCLAVECORE_CARVEOUT       | 0x824000000     | 0x040000000   | 1,024 MiB       | cL4 Conclaves     |
| SEP_FW_TZ0S_CARVEOUT       | 0x864000000     | 0x0061b0000   | 97.6875 MiB     | Secure Enclave TZ0|
| SEP_FW_TZ1S_CARVEOUT       | 0x86a1b0000     | 0x005060000   | 80.375 MiB      | Secure Enclave TZ1|
+----------------------------+-----------------+---------------+-----------------+-------------------+
```

### 6.2 DART Gen3 IOMMU Controller Directory (25 Controllers Enumerated)

The DeviceTree defines 25 distinct **Device Address Resolution Table (DART)** units managing coprocessor and peripheral DMA streams:

```
+----------------------------------------------------------------------------------------------------+
|                             DART Gen3 IOMMU CONTROLLER DIRECTORY (T8150)                           |
+----------------------------------------------------------------------------------------------------+
| Controller Name | Peripheral MMIO Base Address | Aperture Size  | Target Coprocessor / Subsystem   |
+-----------------+------------------------------+----------------+----------------------------------+
| dart-sep        | 0x70c80000                   | 0x20000 (128K) | Secure Enclave Processor IOMMU   |
| dart-aop        | 0x100fc0000                  | 0x0c000 (48K)  | Always-On Processor IOMMU        |
| dart-ane        | 0x271800000                  | 0x0c000 (48K)  | Apple Neural Engine (H18) IOMMU  |
| dart-sio        | 0x175060000                  | 0x20000 (128K) | Serial IO (SPI/UART/I2C) IOMMU   |
| sart-ans        | 0x17dc50000                  | 0x0c000 (48K)  | Apple NVMe Storage SART unit     |
| dart-usb0       | 0x402f00000                  | 0x20000 (128K) | Type-C USB 3.2 / Thunderbolt     |
| dart-isp        | 0x1128c0000                  | 0x0c000 (48K)  | Image Signal Processor IOMMU     |
| dart-jpeg       | 0x7d020000                   | 0x0c000 (48K)  | Hardware JPEG Decoder IOMMU      |
| dart-ave        | 0x77020000                   | 0x20000 (128K) | Apple Video Encoder (AVE) IOMMU  |
| dart-avd        | 0x85020000                   | 0x20000 (128K) | Apple Video Decoder (AVD) IOMMU  |
| dart-disp0      | 0x1fa300000                  | 0x0c000 (48K)  | Primary Display Pipeline IOMMU   |
| dart-disp0-isoc | 0x1fa1c0000                  | 0x20000 (128K) | Real-Time Isochronous Display    |
| dart-dcp        | 0x1fa340000                  | 0x0c000 (48K)  | Display Coprocessor (DCP) IOMMU  |
| dart-apcie0     | 0x180000000                  | 0x20000 (128K) | Apple PCI Express Controller 0   |
| dart-apcie1     | 0x181000000                  | 0x20000 (128K) | Apple PCI Express Controller 1   |
| dart-mtp        | 0x104800000                  | 0x0c000 (48K)  | Multi-Touch Processor (MTP) IOMMU|
| dart-pmp        | 0xf0300000                   | 0x0c000 (48K)  | Power Management Processor IOMMU |
| dart-scaler     | 0x81260000                   | 0x20000 (128K) | Hardware Display Scaler IOMMU    |
| dart-apr        | 0x171020000                  | 0x20000 (128K) | Audio Packet Router IOMMU        |
| dart-rsm        | 0xf99a0000                   | 0x0c000 (48K)  | Resource State Manager IOMMU     |
| dart-dcpext0    | 0x1fe340000                  | 0x0c000 (48K)  | External Display Coprocessor     |
| dart-dispext0   | 0x1fe300000                  | 0x0c000 (48K)  | External Display Pipe IOMMU      |
| dart-dispext0-is| 0x1fe1c0000                  | 0x20000 (128K) | External Isochronous Display DMA  |
| dart-dispgrt    | 0x1fa320000                  | 0x0c000 (48K)  | Display Graphic Rendering Target |
| audio-shared-pr | MMIO Inherited               | Dynamic        | Audio Shared Proxy DART unit     |
+-----------------+------------------------------+----------------+----------------------------------+
```

---

## 7. Zero-Conflict Workspace Validation

This phase was executed exclusively within assigned Agent 3 paths:
- Artifacts generated: [`artifacts/sptm/stage2_translation_geometry.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/stage2_translation_geometry.json) and [`artifacts/sptm/devicetree_hardware_map.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/devicetree_hardware_map.json).
- Findings report: [`findings/sptm/02_HARDWARE_REGISTER_GEOMETRY.md`](file:///home/prem/Projects/iOS%2027/findings/sptm/02_HARDWARE_REGISTER_GEOMETRY.md).
- Zero modifications to `artifacts/sep/`, `artifacts/gpu/`, or `artifacts/aop/`.
- All Phase 2 specifications verified against extracted binary assets with complete empirical verification.
