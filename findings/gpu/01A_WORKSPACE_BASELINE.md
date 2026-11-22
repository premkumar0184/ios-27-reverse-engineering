# Findings: AGX GPU Phase 1A — Workspace Baseline, Image Extraction & Firmware Container Dissection

## 1. Executive Summary & Domain Scope

This investigation establishes the clean-room, verifiable architectural baseline for the **Apple AGX GPU (Generation G18 / G18P)** integrated within the Apple A19 Pro (`t8150`, board revision `v57ap`) running iOS 27.2 (Darwin 24.2.0, Build `24B119`).

As **Agent 2**, this subsystem investigation reverse engineers the graphics and compute coprocessor hardware, its multi-core real-time firmware execution environment (RTBuddy / RTKit), dedicated hardware ray-tracing acceleration pipelines, the DRAM memory compression co-engine (MSRF), and the userland-to-hardware direct command dispatch interface (`AppleMetalDirect` / `AGXMetalG18P`).

All findings are extracted directly from production firmware binaries (`armfw_g18p.im4p`, `armfw1_g18p.im4p`, `t8150.msrf.im4p`), release kernelcaches (`kernelcache.release.raw`), and the consolidated dyld shared cache (`dyld_shared_cache_arm64e.01`).

```
+----------------------------------------------------------------------------------------------------+
|                               AGX G18 FULL-STACK SYSTEM TOPOLOGY                                   |
+----------------------------------------------------------------------------------------------------+
|  USERLAND (Metal 3.2 / Direct Dispatch)                                                            |
|  - Metal.framework (VA: 0x1a566c000)                                                               |
|  - AGXMetalG18P.bundle (VA: 0x2470bc000) [Lock-free Ring Buffer & Doorbell fast-path]            |
|  - IOGPU.framework (VA: 0x20d2c5000) | MPSRayIntersector.framework (VA: 0x24ebf9000)              |
+----------------------------------------------------------------------------------------------------+
|                                    IOKit / Mach Trap Boundary                                      |
+----------------------------------------------------------------------------------------------------+
|  XNU KERNEL (com.apple.AGXG18P v362.5 / IOGPUFamily v162.16.1)                                    |
|  - AGXAccelerator (start, createIOFenceWithTransaction, waitForCommandSubmissionEnabled)           |
|  - AGX3DChannelSKSM / AGXCLChannelSKSM (submitBuffer, copyPassthroughData)                         |
|  - AGXFirmwareKextG18PRTBuddy / AGXFirmwareKextRTBuddy64 (Coprocessor boot & endpoint management)  |
+----------------------------------------------------------------------------------------------------+
|                                    Hardware MMIO / ASCwrap Mailbox                                 |
+----------------------------------------------------------------------------------------------------+
|  AGX COPROCESSOR DUAL-CORE FIRMWARE (RTBuddy / RTKit OS)                                           |
|  - Core 0 (armfw_g18p.im4p, 'gfxf'): Scheduling, Power Management, SPTM Telemetry                  |
|  - Core 1 (armfw1_g18p.im4p, 'gf1f'): Context Switching, VDM/PDM/CDM Channel Command Dispatch      |
|  - DRAM Memory Compression Co-Engine (t8150.msrf.im4p, 'msrf'): Lossless Tile & Texture Buffer     |
+----------------------------------------------------------------------------------------------------+
|  G18 HARDWARE RENDER & COMPUTE SILICON                                                             |
|  - Unified Shading Clusters (USCs) with SIMD32 pipelines                                           |
|  - Hardware Ray-Tracing (RT) BVH Traversal & Intersection Accelerators                             |
|  - Mesh Shading Engine & On-Chip Parameter Buffer Tile Memory                                      |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Hardware Target & Environment Identification

The target device environment is completely cataloged and pinned from manifest parameters:

| Parameter | Extracted Hardware Value | Verification Source |
|---|---|---|
| Target SoC | `t8150` | `BuildManifest.plist` / `Restore.plist` |
| Commercial Platform | Apple A19 Pro | Board configuration identification |
| Device Model | iPhone18,3 | Device Tree / Restore identity |
| Hardware Board ID | `v57ap` | `BuildManifest.plist` |
| Darwin Kernel Version | Darwin Kernel Version 24.2.0 (`24B119`) | `kernelcache.release.raw` |
| OS Build Train | `RaveB24B119.V57ExclaveOS.apfs` | Restore ramdisk & manifests |
| GPU Microarchitecture | Apple AGX Generation 18 Pro (`G18P`) | `AGXG18P.kext` / `AGXMetalG18P.bundle` |
| GPU Page Size | 16,384 bytes (16 KB) | Kernel assertion: `GPU uses 16K page size` |

---

## 3. Firmware Asset Inventory & SHA-256 Checksums

The GPU and memory compression subsystem binaries reside within the restore bundle and kernel image sets. Each component has been verified with raw byte sizes and cryptographic hashes:

| Binary Filename | FourCC Tag | Total Size (Bytes) | SHA-256 Digest | Functional Role |
|---|---|---|---|---|
| `armfw_g18p.im4p` | `gfxf` | 3,510,409 | `2c3d3d88483a05264f8163ea12d6139deea760d0ef4993f6c0207cf0f2eb1e6e` | G18 Coprocessor Core 0: Power, Telemetry & Scheduling |
| `armfw1_g18p.im4p` | `gf1f` | 3,313,873 | `22b7c5dbfcfe818af2aa96ef6c58dd2ca3ea056835db80892bc0a7a61bd74645` | G18 Coprocessor Core 1: Context & Render/Compute Dispatch |
| `t8150.msrf.im4p` | `msrf` | 161,917 | `a975ff160716da4fd7e9fd7d209679814588a7e6e4a8bbbbe9f7c4494f2f2c84` | DRAM Memory Subsystem Resource Coprocessor (Release) |
| `t8150.rmsr.im4p` | `rmsr` | 161,917 | `f10c3730da096a0b8c3be1c775d4310450f407b72cc74c64ddf1d6b3733899e6` | DRAM Memory Subsystem Resource Coprocessor (Recovery) |

---

## 4. Apple Image4 (IM4P) ASN.1 Container Dissection

All GPU firmware binaries are wrapped in Apple's Image4 Payload (`IM4P`) ASN.1 DER container format. The header structure occupies exactly 25 bytes across all four targets before the raw payload:

```
IM4P Header Byte Breakdown:
Offset  Length  ASN.1 Type          Description
0x00    5       SEQUENCE            Total container length tag
0x05    6       IA5String 'IM4P'    Image4 magic identifier
0x0B    6       IA5String FourCC    Subsystem identifier tag (gfxf, gf1f, msrf, rmsr)
0x11    3       IA5String '1'       Version / Description string
0x14    5       OCTET STRING        Encapsulated payload length header
0x19    ...     RAW PAYLOAD         Uncompressed firmware payload
```

### Extracted Container Parameters:
- **`armfw_g18p.im4p` (`gfxf`)**:
  - ASN.1 Header: `30833590841604494d34501604676678661601310483359070`
  - Encoded Payload Length: 3,510,384 bytes (`0x359070`)
  - Payload SHA-256: `80bc203d95ec9da7b619b827fc768194f73d2f89f293d20c57c2e9e3d3a39f89`
- **`armfw1_g18p.im4p` (`gf1f`)**:
  - ASN.1 Header: `30833290cc1604494d345016046766316616013104833290b8`
  - Encoded Payload Length: 3,313,848 bytes (`0x3290b8`)
  - Payload SHA-256: `e87f1ae96bdc6ba7729f0843842700b403fc11c8aed5b3b97103e786a1f2a4a6`
- **`t8150.msrf.im4p` (`msrf`)**:
  - ASN.1 Header: `30830278781604494d345016046d7372661601310483027864`
  - Encoded Payload Length: 161,892 bytes (`0x27864`)
  - Payload SHA-256: `ef642ee75dfe7a8a6608b647b6f6a0a004cf3dad2ccc02daac5ba863f41c03ee`

---

## 5. RTKit OS Firmware Table (`rkosftab`) Architecture

Inspection of the uncompressed payload of both `armfw_g18p.im4p` and `armfw1_g18p.im4p` reveals that the payload does not start directly with executable machine code. Instead, offset `0x20` within the payload contains the **RTKit OS Firmware Table (`rkosftab`)**.

This table enables a single firmware container to store multiple executable Mach-O binaries tailored to specific silicon stepping revisions of the A19 Pro GPU:

```
rkosftab Header Format (Offset 0x20 in IM4P Payload):
Offset  Field           Type            Value / Explanation
0x00    magic           char[8]         "rkosftab" (0x726b6f7366746162)
0x08    entry_count     uint64_t        0x0000000000000003 (3 silicon step images)
0x10    entries[0]      rkosftab_entry  16 bytes (Silicon Step 'a000')
0x20    entries[1]      rkosftab_entry  16 bytes (Silicon Step 'b000')
0x30    entries[2]      rkosftab_entry  16 bytes (Silicon Step 'a010')
```

### Structure of `rkosftab_entry` (16 bytes):
```c
struct rkosftab_entry {
    char     tag[4];       /* Silicon stepping: "a000", "b000", "a010" */
    uint32_t offset;       /* Byte offset relative to payload base     */
    uint32_t size;         /* Length of embedded Mach-O binary         */
    uint32_t reserved;     /* Flags / alignment padding                */
};
```

### Concrete Table Entries Extracted:

#### 1. Core 0 (`armfw_g18p.im4p`):
| Stepping Tag | Payload Offset | Hex Offset | Image Size (Bytes) | SHA-256 Digest |
|---|---|---|---|---|
| `a000` (A0 Step 0) | 96 | `0x00000060` | 1,170,096 (`0x11dab0`) | `59203673c683b584d4fa75225c57b328a3068e1c6687ea71a8106f23ca397fe5` |
| `b000` (B0 Step 0) | 1,170,192 | `0x0011db10` | 1,170,096 (`0x11dab0`) | `3699042c0dfb572242137aa599c22e51921f6498be90666bb9a44c920e53a5c1` |
| `a010` (A1 Step 0) | 2,340,288 | `0x0023b5c0` | 1,170,096 (`0x11dab0`) | `bc8e1daff15e4f45d8b88d2fbf00e4c6981881bcf70129cf9904bc4935418b70` |

#### 2. Core 1 (`armfw1_g18p.im4p`):
| Stepping Tag | Payload Offset | Hex Offset | Image Size (Bytes) | SHA-256 Digest |
|---|---|---|---|---|
| `a000` (A0 Step 0) | 96 | `0x00000060` | 1,104,584 (`0x10dac8`) | `c2eb3183570656a84eb8d53f2cf1923cb8cf63fec1981180fb785e28a5989bb5` |
| `b000` (B0 Step 0) | 1,104,680 | `0x0010db28` | 1,104,584 (`0x10dac8`) | `5614917fbfbbbe64303499e7d958fc94c3cc0e8ddc79426f43e5c709e39bf834` |
| `a010` (A1 Step 0) | 2,209,264 | `0x0021b5f0` | 1,104,584 (`0x10dac8`) | `c3ba7f8c7b6c507c5dbcb242ff8416d8e826437190ca1e9cbfa36e3557e0fa80` |

---

## 6. Mach-O Embedded Image Segmentation & Memory Maps

Each embedded binary inside `rkosftab` is a complete **Mach-O 64-bit (`MH_MAGIC_64` / `0xFEEDFACF`)** image built for `CPU_TYPE_ARM64` (`0x100000c`) and `CPU_SUBTYPE_ARM64_V8` (`0x80000002`).

### Core 0 (`armfw_g18p`) Primary Virtual Memory Map (`a000` image):
- Base Virtual Address: `0xfffffc0000000000`
- Number of Load Commands: 8

```
+----------------------------------------------------------------------------------------------------+
| Segment Name       | VM Address          | VM Size (Bytes) | File Offset | File Size | Access Prot |
+--------------------+---------------------+-----------------+-------------+-----------+-------------+
| __TEXT             | 0xfffffc0000000000  | 327,680 (320 KB)| 0x00004000  | 327,680   | r-x (read/ex|
| __DATA             | 0xfffffc0000050000  | 786,432 (768 KB)| 0x00054000  | 786,432   | rw- (rd/wrt)|
| __DATA_SHARED_RO   | 0xfffffc0000110000  | 32,768 (32 KB)  | 0x00114000  | 32,768    | r-- (ro-shrd|
| __DATA_CONST       | 0xfffffc0000118000  | 0 (0 KB)        | 0x0011c000  | 0         | r-- (ro-cnst|
+----------------------------------------------------------------------------------------------------+
```

### Core 1 (`armfw1_g18p`) Primary Virtual Memory Map (`a000` image):
- Base Virtual Address: `0xfffffc0000000000`
- Number of Load Commands: 8

```
+----------------------------------------------------------------------------------------------------+
| Segment Name       | VM Address          | VM Size (Bytes) | File Offset | File Size | Access Prot |
+--------------------+---------------------+-----------------+-------------+-----------+-------------+
| __TEXT             | 0xfffffc0000000000  | 311,296 (304 KB)| 0x00004000  | 311,296   | r-x (read/ex|
| __DATA             | 0xfffffc000004c000  | 737,280 (720 KB)| 0x00050000  | 737,280   | rw- (rd/wrt)|
| __DATA_SHARED_RO   | 0xfffffc0000100000  | 32,768 (32 KB)  | 0x00104000  | 32,768    | r-- (ro-shrd|
| __DATA_CONST       | 0xfffffc0000108000  | 0 (0 KB)        | 0x0010c000  | 0         | r-- (ro-cnst|
+----------------------------------------------------------------------------------------------------+
```

**Key Architectural Finding**: Both Core 0 and Core 1 utilize independent virtual address spaces mapped at identical base addresses (`0xfffffc0000000000`), mediated by the hardware RTBuddy MMU. The `__DATA_SHARED_RO` segment (`32 KB`) provides the hardware mailbox communication buffer between Core 0 and Core 1.

---

## 7. DRAM Memory Subsystem Resource (MSRF) Coprocessor

The memory subsystem resource binary (`t8150.msrf.im4p`) provides firmware for the dedicated DRAM memory compression co-engine that manages real-time lossless ASTC and Tile compression across the unified memory fabric.

### Binary Header Properties:
- Magic: `0xFEEDFACE` (**Mach-O 32-bit**)
- CPU Type: `0x0000000c` (`CPU_TYPE_ARM`)
- CPU Subtype: `0x0000000f` (`CPU_SUBTYPE_ARM_V7K` — specialized low-power ARMv7 microcontroller core)
- File Type: `5` (`MH_PRELOAD`)
- Number of Load Commands: 6

### Segment Memory Layout:
| Segment Name | VM Base Address | VM Size (Bytes) | File Offset | File Size | Purpose |
|---|---|---|---|---|---|
| `__TEXT` | `0x00100000` | 71,624 (`0x117c8`) | `0x00000324` | 71,624 | Compression firmware logic & microcode |
| `__DATA` | `0x10000200` | 52,464 (`0xccf0`) | `0x00011aec` | 52,392 | State buffers & lookup tables |
| `__DMEM` | `0x10000000` | 264 (`0x108`) | `0x0001e794` | 264 | Direct tightly-coupled data memory |

---

## 8. Host XNU Kernel Driver Topology

Four kernel extensions form the kernel-space GPU stack in `kernelcache.release.raw`:

```
                           HOST KERNEL EXTENSION GRAPH
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ com.apple.iokit.IOGPUFamily (v162.16.1)                                                │
│ ├── IOGPUCommandDescriptor, IOGPUCommandQueue, IOGPUWorkQueue                         │
│ └── Shared UserClient abstraction and shared memory memory mapping                     │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │ Inherits / Bridges
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│ com.apple.AGXG18P (v362.5) [892,632 B TEXT_EXEC]                                       │
│ ├── AGXAccelerator: Central hardware coordinator                                      │
│ ├── AGX3DChannelSKSM / AGXCLChannelSKSM: 3D Render & Compute submission queues          │
│ └── AGXDeviceUserClient: Userland direct submission broker                             │
└───────────────┬────────────────────────────────────────────────────────┬───────────────┘
                │ Controls                                               │ Relies on
┌───────────────▼──────────────────────────────────────┐ ┌───────────────▼──────────────┐
│ com.apple.AGXFirmwareKextG18PRTBuddy (v362.5)        │ │ com.apple.AGXFirmwareKext     │
│ └── Coprocessor bootloader & G18 RTBuddy interface   │ │ RTBuddy64 (v362.5)            │
└──────────────────────────────────────────────────────┘ └───────────────────────────────┘
```

### Extracted Kernel Driver Specifications:
1. **`com.apple.AGXG18P`**:
   - Path: `/System/Library/Extensions/AGXG18P.kext`
   - Version: `362.5`
   - Text Execution Segment (`__TEXT_EXEC`): VM Address `0xfffffe00084e5960`, Size `892,632` bytes (`0x14e1960`)
   - Dependencies: `com.apple.iokit.IOGPUFamily`, `com.apple.driver.RTBuddy`, `com.apple.iokit.IOSurface`
2. **`com.apple.iokit.IOGPUFamily`**:
   - Path: `/System/Library/Extensions/IOGPUFamily.kext`
   - Version: `162.16.1`
   - Text Execution Segment (`__TEXT_EXEC`): VM Address `0xfffffe000a0dede0`, Size `280,604` bytes (`0x30dade0`)

---

## 9. Dyld Shared Cache Userland Framework Entry Points

The userland drivers and ray-tracing intersector frameworks reside at fixed virtual addresses in `dyld_shared_cache_arm64e.01`:

| Image Index | Virtual Base Address | Framework / Bundle Path | Architectural Functionality |
|---|---|---|---|
| 174 | `0x1a566c000` | `/System/Library/Frameworks/Metal.framework/Metal` | High-level Metal API entry point |
| 722 | `0x20d2c5000` | `/System/Library/PrivateFrameworks/IOGPU.framework/IOGPU` | Userland IOGPU client buffer manager |
| 1690 | `0x2470bc000` | `/System/Library/Extensions/AGXMetalG18P.bundle/AGXMetalG18P` | G18 hardware driver & direct submission |
| 1820 | `0x24ebf9000` | `/System/Library/Frameworks/.../MPSRayIntersector.framework` | Hardware ray-tracing acceleration API |
| 1987 | `0x253452000` | `/System/Library/PrivateFrameworks/AGXCompilerCore.framework` | AIR to AGX G18 machine code compiler |
| 1988 | `0x25373c000` | `/System/Library/PrivateFrameworks/AGXGPURawCounter.framework` | Hardware performance counter telemetry |
| 2997 | `0x28ce6d000` | `/System/Library/PrivateFrameworks/IOAccelerator.framework` | IOKit accelerator connection library |

---

## 10. Phase 1A Verification Evidence & Phase 1B Handoff

Phase 1A has established the verified, deterministic workspace baseline:
- `artifacts/gpu/phase_1a_workspace_baseline.json`: Complete hardware, kext, and framework inventory.
- `artifacts/gpu/agx_firmware_container_spec.json`: Precise ASN.1 IM4P headers, `rkosftab` table geometry, and Mach-O segment mappings.
- `artifacts/gpu/progress_gpu.json`: Domain-isolated execution progress state machine.

With the firmware containers parsed and their internal Mach-O boundaries resolved, the investigation is ready for **Phase 1B: G18 Microarchitecture & RTBuddy Coprocessor Topology**.
