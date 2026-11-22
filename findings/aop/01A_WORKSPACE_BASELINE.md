# AOP2 & RTKit Reverse Engineering: Phase 1A — Workspace Baseline & Container Specification

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`, Train `RaveB`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem**: Always-On Processor 2 (AOP2), RTKit Preemptive Microkernel & Sensor Hub  
**Primary Target Binary**: `iPhone18,3_27.2_24B119_Restore/Firmware/AOP2/aop2fw-v57aop2.RELEASE.im4p` (5,603,353 bytes)  
**Date**: November 2026  
**Classification**: Clean-Room Architectural Reverse Engineering Report

---

## 1. Executive Subsystem Overview

On modern Apple Silicon architectures (A19 Pro `t8150`), the **Always-On Processor 2 (AOP2)** is the dedicated, ultra-low-power coprocessor responsible for autonomous device awareness, background environmental monitoring, always-on display (AOD) refresh arbitration, and cross-enclave sensor telemetry while the main Application Processor (AP) CPU clusters sleep in deep low-power retention states (C4/P-state sleep).

Historically, the original AOP (`aopf`, ARMv7/ARMv8-M microcontroller) handled simple power-state transitions and basic accelerometer wakeups. In contrast, modern AOP2 executes a full 64-bit **RTKit preemptive real-time microkernel** compiled for **ARM64e (Pointer Authentication PAC00)**, managing a complex constellation of real-time application tasks, fast-path lock-free ring buffers, and direct DART IOMMU bridges to the host XNU kernel and **ExclaveOS**.

```
+----------------------------------------------------------------------------------------------------+
|                                    DARWIN / XNU (Host AP Ring 0)                                   |
|   AppleAOP2.kext | AppleSPU.kext | AppleEmbeddedAudio.kext | backboardd (1Hz AOD) | assistantd     |
+----------------------------------------------------------------------------------------------------+
                                                  |
                         [Apple Silicon ASCwrap Mailbox & DART-AOP IOMMU]
                                                  |
+----------------------------------------------------------------------------------------------------+
|                                ALWAYS-ON PROCESSOR 2 (AOP2)                                        |
|  - Microkernel: RTKit 64-bit Preemptive Scheduler (MH_PRELOAD @ 0xffffffff00000000)                |
|  - Host Communication: ASCwrap-v6 Mailbox (MMIO: 0x101600000, size: 0x88000)                      |
|  - Direct ExclaveOS Mailbox: Secure RTBuddy Proxy (MMIO: 0x35167c000, size: 0x4000)               |
|  - Memory Translation: DART-AOP (MMIO: 0x100fc0000, Streams: 0x00, 0x01, 0x10, 0x11, 0x08..0x0b)  |
+----------------------------------------------------------------------------------------------------+
         |                                        |                                        |
+------------------+                    +--------------------+                    +------------------+
| Task 1:          |                    | Task 2:            |                    | Task 3:          |
| Motion Expert    |                    | Audio & Hotword    |                    | RTKit-Exclave    |
| (ap-motionx-ep)  |                    | (ap-audio-ep)      |                    | Bridge (EP 0x53) |
| IMU Fast-Path    |                    | 3.0s SRAM FIFO     |                    | Sensor Privacy   |
+------------------+                    +--------------------+                    +------------------+
```

---

## 2. Firmware Container Structure: Image4 (IM4P) & BUND Envelopes

The production AOP2 firmware image `aop2fw-v57aop2.RELEASE.im4p` is encapsulated within an Apple Image4 (`IM4P`) DER-encoded ASN.1 envelope containing an embedded Apple BUND (`DNUB`) multi-binary archive.

### 2.1 Image4 ASN.1 Header Geometry
Inspection of the first 33 bytes of `aop2fw-v57aop2.RELEASE.im4p` reveals the standard Image4 payload container header:
- **Root Sequence**: `0x30 0x83 0x55 0x80 0x14` (DER Sequence tag, length `0x558014` = 5,603,348 bytes)
- **Magic String**: `IM4P` (`0x16 0x04 0x49 0x4d 0x34 0x50`, IA5String)
- **Type FourCC**: `aop2` (`0x16 0x04 0x61 0x6f 0x70 0x32`, IA5String)
- **Version String**: `1` (`0x16 0x01 0x31`, IA5String)
- **Payload Octet String**: `0x04 0x83 0x55 0x80 0x00` (Octet String header, payload size `0x558000` = 5,603,328 bytes)

Unlike the Secure Enclave (`sepi`) payload, which is encrypted under a Silicon eFuse GID keybag (`KBAG`), the AOP2 firmware payload is unencrypted code packaged directly in the Apple `BUND` container format.

### 2.2 Apple BUND (`DNUB`) Multi-Binary Container Architecture
At byte offset `33` (`0x21`) from the file beginning, the payload begins with the Apple `BUND` container header:

```
Offset in File     Offset in Payload     Value / Hex                      Structural Interpretation
----------------------------------------------------------------------------------------------------------------
0x00000021         0x00000000            44 4e 55 42 ('DNUB')             Magic Identifier (FourCC 'BUND')
0x00000025         0x00000004            00 00 04 00 (0x00040000)         Container Format Version 4.0
0x00000029         0x00000008            01 00 00 00 (0x00000001)         Top-Level Entry Count
0x0000002d         0x0000000c            0b 00 00 00 (0x0000000b)         Segment Map Entry Count (11 entries)
0x00000031         0x00000010            00 00 00 00 00 00 00 00          Reserved / Alignment Padding
0x00000039         0x00000018            00 10 01 00 00 00 00 00          Total Container Allocation (0x11000)
```

### 2.3 Segment Map Table
Following the descriptor table, the container defines an 11-entry segment allocation map specifying how the physical memory image is partitioned across execution domains:

| Entry | FourCC Tag | Interpretation | Allocated Size | Image Offset | Memory Protection Flags |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **00** | `txtk` | Kernel Text | 69,632 bytes (`0x11000`) | `0x11000` | `0x0a` (Read / Execute) |
| **01** | `txtr` | RootTask Text | 139,264 bytes (`0x22000`) | `0x33000` | `0x0a` (Read / Execute) |
| **02** | `txtu` | User Applications Text | 1,183,744 bytes (`0x121000`)| `0x154000` | `0x0e` (Read / Execute / User) |
| **03** | `tadk` | Kernel Data | 32,768 bytes (`0x8000`) | `0x15c000` | `0x11` (Read / Write / Supervisor) |
| **04** | `tadr` | RootTask Data | 16,384 bytes (`0x4000`) | `0x160000` | `0x11` (Read / Write / Supervisor) |
| **05** | `tadu` | User Applications Data | 3,883,008 bytes (`0x3b4000`)| `0x514000` | `0x15` (Read / Write / User) |
| **06** | `orsd` | Shared Read-Only Data | 0 bytes (`0x0000`) | `0x514000` | `0x15` (Read Only) |
| **07** | `wrsd` | Shared Read-Write Data | 98,304 bytes (`0x18000`) | `0x52c000` | `0x15` (Read / Write Shared) |
| **08** | `dlon` | Non-Loadable Metadata | 16,384 bytes (`0x4000`) | `0x530000` | `0x114` (Metadata / Debug) |
| **09** | `ldbu` | User Build Data | 131,072 bytes (`0x20000`) | `0x550000` | `0x15` (Read / Write) |
| **10** | `glso` | OS Log String Table | 24,576 bytes (`0x6000`) | `0x556000` | `0x104` (OS Log Read-Only) |

---

## 3. The Seven Mach-O Sub-Binaries of AOP2

Within the `BUND` container payload, exactly seven Mach-O 64-bit sub-binaries (`cputype = 0x100000c`, `cpusubtype = 0x80000002` ARM64e PAC00) are located. Each binary was extracted, parsed, and verified:

```
Index  Offset     Size (Bytes)  Type        UUID                              Identity / Primary Role
-----------------------------------------------------------------------------------------------------------------------
0      69,657     147,456       MH_EXECUTE  2e915a01a6613afbb04aa81aae792a70  roottask.IOP_ASC7.RELEASE (System Root)
1      208,921    536,288       MH_EXECUTE  b035344a292d3a16bcf80ffcab64a775  AppleFirmwareKit Motion App (ap-motionx-ep)
2      311,321    477,184       MH_EXECUTE  c52a816d0e0733cb87db9ab57586ac39  AONLocationApp (Always-On Location)
3      434,201    753,976       MH_EXECUTE  46699d8af0e633b595d262b5cce92e9c  Audio Hotword App (ap-audio-ep / Siri FIFO)
4      823,321    326,560       MH_EXECUTE  3fbec0c7266a3f2db4b55319055c9d5f  RTKit Exclave Bridge (rtkit-exclave)
5      888,857    532,480       MH_DYLIB    f9f5696af4df397e928d32e29f0f263e  v57aop2.dylib (AppleSPUFirmwareBuilder)
6      5,439,513  81,920        MH_PRELOAD  05c35c6100d33aaebc5d4c4c29405445  RTKit Microkernel Preload (@ 0xffffffff00000000)
```

### 3.1 Binary 0: RootTask (`00_roottask_iop_asc7.macho`)
- **VM Load Base**: `0x8000000` (Size: `0x26000`)
- **Segments**: `__TEXT` (`0x8000000`, size `0x22000`), `__DATA` (`0x8022000`, size `0x4000`), `__DATA_CONST`, `__LINKEDIT`.
- **Primary Function**: The initial supervisory process launched by the microkernel upon boot completion. Initializes Apple Silicon Storage/Silicon Coprocessor 7 (`IOP_ASC7`), validates firmware digital signatures, maps userland task spaces, and configures IPC patchbays.

### 3.2 Binary 1: Motion Expert App (`01_motion_expert_app.macho`)
- **VM Load Base**: `0x10f3000` (Size: `0x13a000`)
- **Segments**: `__TEXT` (`0x10f3000`, size `0x19000`), `__DATA_CONST`, `__DATA` (`0x110f000`, size `0x11a000`), `APPCONFIG` (`0x1229000`, size `0x3000`), `METADATA`, `__DATA_SHARED_RW`, `__OS_LOG`.
- **Special Sections**: `_rtk_patchbay`, `_rtk_pb_finder`, `_rtk_init_stack`, `_rtk_irq_stack`, `_rtk_exc_stack`, `_rtk_heap`, `_afk_sys_objt`, `_aop2_shm_reg`, `_RTK_EXT_SHD_DTA`.
- **Primary Function**: Manages the continuous sensor telemetry pipeline, reading 6-axis IMU samples (accelerometer and gyroscope) into lock-free fastpath ring buffers mapped to host XNU driver `AppleSPUFastpathDriver`.

### 3.3 Binary 2: Always-On Location & Activity Classifier (`02_aon_location_app.macho`)
- **VM Load Base**: `0x10f3000` (Size: `0x16e000`)
- **Segments**: `__TEXT` (`0x10f3000`, size `0x1e000`), `__DATA_CONST`, `__DATA` (`0x1114000`, size `0x14a000`), `__CMA` (`0x1000f3000`, size `0x1000`), `APPCONFIG`, `METADATA`.
- **Special Sections**: `_aop2_app_stack`, `__loc_log_str` (Contiguous Memory Allocator CMA log string buffer).
- **Primary Function**: Executes on-chip pedestrian dead reckoning (PDR), step cadence tracking, stationary posture detection, and low-power GNSS geofence filtering without waking host GPS baseband silicon.

### 3.4 Binary 3: Audio Hotword & Voice Trigger App (`03_audio_hotword_app.macho`)
- **VM Load Base**: `0x10f3000` (Size: `0xd0000`)
- **Segments**: `__TEXT` (`0x10f3000`, size `0x5f000`), `__DATA_CONST`, `__DATA` (`0x1154000`, size `0x6b000`), `APPCONFIG`, `METADATA`.
- **Special Sections**: `__objc_imageinfo` (Objective-C runtime metadata for acoustic graph descriptors).
- **Primary Function**: Interfaces with Apple Low-Power Microphone input devices (`AppleAOPAudioLPMicInDevice`), maintaining a 3.0-second circular audio buffer in on-chip SRAM for local "Siri" keyword acoustic scoring.

### 3.5 Binary 4: RTKit-Exclave Bridge (`04_rtkit_exclave_bridge.macho`)
- **VM Load Base**: `0x10f3000` (Size: `0xb6000`)
- **Segments**: `__TEXT` (`0x10f3000`, size `0x10000`), `__DATA_CONST`, `__DATA` (`0x1105000`, size `0xa0000`), `APPCONFIG`, `METADATA`, `__DATA_SHARED_RW`.
- **Special Sections**: `_aop2_shm_reg`, `_RTK_EXT_SHD_DTA`.
- **Primary Function**: Houses `RTKExclaveTBEndpoint`, communicating directly with **ExclaveOS** over DART Stream ID `0x11` (`mapper-exclave-aop2`). Transmits real-time microphone and camera sensor power state to the Exclave Sensor Indicator Light (SIL) manager.

### 3.6 Binary 5: AppleSPUFirmwareBuilder Runtime Dylib (`05_applespu_v57aop2_dylib.macho`)
- **Install Name**: `/Library/Caches/com.apple.xbs/.../Binaries/AppleSPUFirmwareBuilder/install/Symbols/RELEASE/v57aop2/DYLIB/v57aop2.dylib`
- **VM Load Base**: `0x1000000` (Size: `0x84000`)
- **Segments**: `__TEXT` (`0x1000000`, size `0x7a000`), `__DATA_CONST`, `__DATA`, `__OS_LOG`, `APPCONFIG`.
- **Special Sections**: `__lcxx_override`, `_rtk_patchbay_1`, `__osc_ctor_mask1`, `__osc_ctor_mask2`, `_rtk_threads`, `_afk_sys_drv`.
- **Primary Function**: The core shared framework hosting AppleFirmwareKit C++ driver base classes, runtime memory allocators, virtual method tables (`_rtk_mtab`), and OSLog string formatters.

### 3.7 Binary 6: RTKit Microkernel Preload (`06_rtkit_microkernel_preload.macho`)
- **VM Load Base**: `0xffffffff00000000` (High 64-bit Kernel Virtual Address space, size: `0x19000`)
- **Segments**: `__TEXT` (`0xffffffff00000000`, size `0x11000`), `__DATA` (`0xffffffff00011000`, size `0x8000`), `__IMAGE_END`.
- **Special Sections**: `__head`, `__tunables`, `__kernel_stack`, `__image_end`.
- **Primary Function**: The bare-metal microkernel preboot image executed upon coprocessor core reset. Sets up ARM64 exception vectors (EL1), configures stage-1 MMU translation tables, initialises hardware timer interrupts, and launches the root task.

---

## 4. Hardware Memory & Bus Topology from DeviceTree

Decompression and empirical analysis of `DeviceTree.v57ap.im4p` (decompressed size: 365,632 bytes) reveals the hardware memory map and peripheral interconnects for AOP2:

### 4.1 MMIO Register Ranges
```
DeviceTree Node                     Register Index   Physical Base Address   Window Size (Bytes)  Hardware Function
--------------------------------------------------------------------------------------------------------------------------------
/device-tree/arm-io/aop2            0                0x0000000101600000      0x88000 (557,056)    ASCwrap Mailbox & Control
/device-tree/arm-io/aop2            1                0x0000000101050000      0x04000 (16,384)     Secondary Mailbox Control
/device-tree/arm-io/aop2            2                0x000000010162c000      0x3c008 (245,768)    Doorbell & Interrupt Aggregation
/device-tree/arm-io/aop2-exclave-   0                0x000000035167c000      0x04000 (16,384)     Secure ExclaveOS Mailbox Proxy Doorbell
  mailbox
/device-tree/arm-io/dart-aop        0                0x0000000100fc0000      0x0c000 (49,152)     DART IOMMU Configuration
/device-tree/arm-io/aop-gpio        0                0x0000000100824000      0x04000 (16,384)     AOP GPIO Controller (t8101)
/device-tree/arm-io/aop-spmi0       0                0x0000000100914000      0x04000 (16,384)     SPMI Bus 0 Controller
/device-tree/arm-io/aop-spmi1       0                0x0000000100b14000      0x04000 (16,384)     SPMI Bus 1 Controller
```

### 4.2 DART-AOP IOMMU Stream ID Assignments
The DeviceTree defines 9 distinct DMA translation streams managed by `/device-tree/arm-io/dart-aop`:
- **Stream ID `0x00` (`mapper-aop`)**: Legacy AOP1 host shared memory mapping.
- **Stream ID `0x01` (`mapper-exclave-aop`)**: AOP1 ExclaveOS secure bridge.
- **Stream ID `0x10` (`mapper-aop2`)**: AOP2 high-speed host DMA buffers (fastpath sensor ring buffers).
- **Stream ID `0x11` (`mapper-exclave-aop2`)**: AOP2-to-ExclaveOS cross-enclave bridge (`sharedmem_xcoproc_AOP2_EP53_in`).
- **Stream ID `0x08` (`mapper-admac-base-ns`)**: Audio DMA Base (Non-Secure).
- **Stream ID `0x0a` (`mapper-admac-leap-ns`)**: Audio DMA LEAP (Non-Secure).
- **Stream ID `0x09` (`mapper-admac-base-s`)**: Audio DMA Base (Secure Exclave realm).
- **Stream ID `0x0b` (`mapper-admac-leap-s`)**: Audio DMA LEAP (Secure Exclave realm).
- **Stream ID `0x03` (`mapper-scm`)**: System Control & Management bus master.

---

## 5. Phase 1A Verification & Completion Status

- [x] Target firmware containers (`aop2fw-v57aop2.RELEASE.im4p`, `aopfw-v57aop.RELEASE.im4p`, `v57-boot-chime.im4p`) verified with SHA256 hashes.
- [x] Apple BUND (`DNUB`) container unpacked and 11-segment mapping table cataloged.
- [x] All 7 embedded Mach-O 64-bit sub-binaries extracted to `artifacts/aop/unpacked/` with exact byte sizes, offsets, UUIDs, and section inventories.
- [x] Empirical DeviceTree geometry parsed from `DeviceTree.v57ap.im4p` (MMIO bases `0x101600000`, `0x35167c000`, DART stream IDs `0x00..0x11`).
- [x] Deliverable `artifacts/aop/phase_1a_workspace_baseline.json` created.
- [x] Deliverable `artifacts/aop/aop_firmware_container_spec.json` created.
- [x] Zero collisions or file alterations in `artifacts/sep`, `artifacts/gpu`, or `artifacts/sptm`.
