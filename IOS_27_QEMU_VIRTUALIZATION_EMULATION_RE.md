# iOS 27 Reverse Engineering: Apple Silicon A19 Pro (t8150) Clean-Room Virtualization & Emulation Layer
## Publication Master Dossier — Unified Bare-Metal QEMU Architecture, Hardware Accelerator Integration & RTKit Firmware Stubs

**Platform**: Apple Silicon A19 Pro (`t8150` / `v57ap` / `iPhone18,3`)  
**Operating System**: iOS 27.2 (Darwin Kernel Version 24.2.0, Build `24B119`)  
**Architecture Profile**: ARMv9.4-A with Apple FEAT_PAUTH2 / FEAT_BTI / CTRR Stage-2 Virtualization  
**Security Domain**: SPTM (EL2), TXM (EL2), ExclaveOS cL4 Conclaves, sepOS TZ0S/TZ1S  
**Distribution**: Standalone Publication Master Technical Dossier  
**Release Date**: November 2026  

---

## 1. Executive Summary

This publication dossier presents the definitive clean-room emulation and bare-metal virtualization platform for the modern Apple Silicon A19 Pro (`t8150`) system-on-chip running iOS 27.2 (`24B119`). Throughout the iOS 27 reverse engineering effort, isolated C driver specifications, register layouts, wire formats, and dispatch protocols were extracted from production kernelcaches and coprocessor firmware. This project synthesizes those isolated discoveries into an executable, verifiable virtualized execution platform.

The deliverable provides two interoperable emulation modalities:
1. **Upstream-Compatible QEMU Machine Models**: Standard QOM C99/C11 source files formatted for upstream `qemu-system-aarch64` (`apple-a19-pro`).
2. **Standalone Bare-Metal Simulation Runner**: A self-contained, native test harness (`apple_a19_emulation_runner`) and bare-metal ARM64 firmware stubs that cross-compile cleanly via `clang -target aarch64-none-elf -fuse-ld=lld` and execute end-to-end on host systems.

The emulation platform integrates all four clean-room client workloads:
- **AppleMetalDirect (AGX G18 Pro GPU)**: Emulating direct 64-byte command descriptor queueing, PMP Doorbell kicks, TBDR compute execution, status page heartbeats, and AIC interrupt signaling.
- **Silenus Camera ISP & Bayer Neural Interface (BNI)**: Emulating the CISP command channel (`IOP_RINGBUFFER_VERSION_V2`), DART-mediated sensor ingestion, 3A statistics, and direct routing of FaceID Near-Infrared (NIR) frames into the Secure Enclave `TZ1S` memory domain.
- **AppleProResHW (AVE2 Video Accelerator)**: Emulating dual-core (`apr,a1` / `apr,a2`) hardware video encoding, parsing 128-byte `sAppleProResRawFrameHeader` structures, parallel slice compression, and hardware CRC32 calculation.
- **Tightbeam IPC & ExclaveOS Bridge**: Emulating cL4 microkernel system call traps (`svc #0`), 88-byte `struct tb_message_s` binary serialization, conclave service routing, and unforgeable capability badge minting.

---

## 2. 36-Bit Physical Memory Architecture & Hardware Protection Fences

The A19 Pro architecture operates on a 36-bit physical addressing fabric (64 GB addressable physical space). Unified system memory spans from `0x0000000800000000` to `0x0000000FFFFFFFFF` (32 GB DRAM).

### 2.1 Hardware-Enforced DRAM Carveout Map

```
+----------------------------------------------------------------------------------------------------+
| 0x0000000800000000 - 0x000000081FFFFFFF (512 MB)  : SPTM Reserved (EL2 / CTRR Hardware Locked)    |
+----------------------------------------------------------------------------------------------------+
| 0x0000000820000000 - 0x0000000823FFFFFF (64 MB)   : TXM Reserved (Trusted Execution Monitor)      |
+----------------------------------------------------------------------------------------------------+
| 0x0000000824000000 - 0x0000000863FFFFFF (1024 MB) : ExclaveOS cL4 Conclave Dynamic Pool           |
+----------------------------------------------------------------------------------------------------+
| 0x0000000864000000 - 0x000000086A1AFFFF (97.68 MB): Secure Enclave TZ0S Static Firmware Buffer     |
+----------------------------------------------------------------------------------------------------+
| 0x000000086A1B0000 - 0x000000086F20FFFF (80.37 MB): Secure Enclave TZ1S Dynamic Buffer (Pearl NIR)|
+----------------------------------------------------------------------------------------------------+
| 0x000000086F210000 - 0x00000008FFFFFFFF (30.26 GB): Darwin XNU Host Physical Memory Pool          |
+----------------------------------------------------------------------------------------------------+
```

### 2.2 On-Chip Retention SRAM Domains

In addition to main DRAM, on-chip static RAM pools provide persistent low-power state storage across power gating cycles:
- **SEP Retention SRAM** (`0x0000000070000000`, 512 KB): Secure Enclave cryptographic keystore.
- **AOP2 Retention SRAM** (`0x0000000100000000`, 5.34 MB): Always-On Processor 2 microkernel and sensor state.
- **AGX Tile Memory SRAM** (`0x0000000230000000`, 16 MB): High-bandwidth on-chip raster cache for Tile-Based Deferred Rendering.
- **ANE Tensor SRAM** (`0x0000000270000000`, 32 MB): Neural Engine activation and weight buffer.

---

## 3. Apple Interrupt Controller (AIC v3/v4) Emulation Model

The Apple Interrupt Controller on A19 Pro (`MMIO_AIC_BASE = 0x00000000F3C00000`) multiplexes up to 1024 vector lines across 8 CPU cores.

### 3.1 Register Specifications

- `AIC_REG_INFO` (`0x0000`): Returns `0x04000400` (Version 4, 1024 vector lines).
- `AIC_REG_WHOAMI` (`0x0004`): Returns caller CPU core affinity index.
- `AIC_REG_EVENT` (`0x0010`): Atomic event query and acknowledgment register.
- `AIC_REG_MASK_SET_BASE` (`0x0100`): 32-bit register array masking vector lines.
- `AIC_REG_MASK_CLR_BASE` (`0x0180`): 32-bit register array unmasking vector lines.
- `AIC_REG_PENDING_BASE` (`0x0200`): Live interrupt assertion bitfield.
- `AIC_REG_TARGET_BASE` (`0x0400`): Core affinity route table per vector.

### 3.2 Key Accelerator Vector Assignments

```
Vector   Hex     Subsystem              Signal Description
-----------------------------------------------------------------------------------------
256      0x0100  AppleProResHW          ProRes RAW Slice Compression Complete
284      0x011c  Silenus Camera ISP     CISP Frame Done Completion
285      0x011d  Silenus Camera ISP     3A Real-Time Statistics Ready
286      0x011e  Silenus Camera ISP     Camera DMA Bus Error
287      0x011f  Silenus Camera ISP     MIPI CIL Circuit Breaker Trip
297      0x0129  Silenus Camera ISP     ISP Coprocessor Mailbox Event
302      0x012e  Apple DART-ISP         IOMMU Translation / Permission Fault
304      0x0130  Secure Enclave (SEP)   ASCwrap-v6 Inbox Message Available
305      0x0131  Secure Enclave (SEP)   ASCwrap-v6 Outbox Space Available
306      0x0132  Secure Enclave (SEP)   Hardware Doorbell Kicked
357      0x0165  Always-On (AOP2)       ASCwrap-v6 Inbox Message Available
358      0x0166  Always-On (AOP2)       ASCwrap-v6 Outbox Space Available
359      0x0167  Always-On (AOP2)       Hardware Doorbell Kicked
361      0x0169  Exclave AOP2 Proxy     Conclave IPC Request Pending
364      0x016c  Exclave AOP2 Proxy     Conclave IPC Response Ready
952      0x03b8  AGX RTBuddy Core 0     ASCwrap-v6 Inbox Message Available
953      0x03b9  AGX RTBuddy Core 0     ASCwrap-v6 Outbox Space Available
954      0x03ba  AGX RTBuddy Core 0     Hardware PMP Doorbell Completion
```

---

## 4. Apple ASCwrap-v6 Mailbox & Doorbell Engine

The ASCwrap-v6 engine (`iop,ascwrap-v6`) enables low-latency message passing between CPU cores and coprocessors.

### 4.1 Message Architecture

Each mailbox exchange consists of a 64-bit word:
- `Bits [63:48]` (16 bits): Endpoint Selector ID.
- `Bits [47:0]` (48 bits): Message Payload.

### 4.2 Register Architecture

```
Offset   Register Name        Role
-----------------------------------------------------------------------------------------
0x0000   MBI_INBOX_CTRL       Inbox interrupt mask and message count [23:16]
0x0008   MBI_INBOX_DATA       64-bit pop register (pops word from Inbox FIFO)
0x0020   MBI_OUTBOX_CTRL      Outbox interrupt mask and queue count [23:16]
0x0028   MBI_OUTBOX_DATA      64-bit push register (pushes word to Outbox FIFO)
0x0040   MBI_STATUS           Full/Empty status flags for Inbox and Outbox
0x0000   DOORBELL_SET         Write-1-to-set peer core doorbell interrupt
0x0004   DOORBELL_CLEAR       Write-1-to-clear pending doorbell interrupt
0x0008   DOORBELL_STATUS      Live pending doorbell interrupt bitmask
```

---

## 5. Apple DART Gen3/Gen4 IOMMU Emulation Model

The Apple DART IOMMU provides hardware memory translation and DMA access isolation.

### 5.1 DART Architecture

- **Page Granule**: 16 KB native pages (`A19_PAGE_SIZE_16K = 16384`).
- **Stream ID Allocation**: 16 hardware stream contexts per DART instance.
- **Radix Page Walk**: 2-level page table walking with permission enforcement.
- **Fault Handling**: Hardware latching of faulting DVA, Stream ID, and cause in `DART_REG_FAULT_STATUS` (`0x10`), triggering assigned AIC interrupt lines.

---

## 6. Clean-Room Hardware Accelerator Models

### 6.1 AppleMetalDirect: AGX G18 Pro GPU Accelerator Model

The AGX G18 Pro model implements direct userland/kernel dispatch for Apple Silicon GPUs:
- **64-Byte Command Descriptors**: `agx_command_descriptor` structures specifying opcode, Data Master (VDM, PDM, CDM, BLIT), priority, flags, GPU virtual addresses, and stamp values.
- **8-Byte PMP Doorbell Kick Tokens**: Encodes queue ID, 64-byte aligned ring offset, and priority kick flags.
- **16 KB Status Page**: Monotonically advancing completion timestamps (`completed_stamps`), consumer read index (`firmware_read_index`), and firmware heartbeat counter (`firmware_heartbeat`).
- **Interrupt Routing**: Fires `AIC_IRQ_AGX_CORE0_INBOX` (Vector 952) upon descriptor completion.

### 6.2 Silenus Camera ISP & Bayer Neural Interface (BNI)

The Silenus model handles real-time camera ingestion and biometric isolation:
- **CISP Protocol**: 64-byte command envelopes (`CISP_MAGIC = 0x43495350`).
- **Sensor Ingestion**: Streams Bayer raw data from DVA `0x880000000` via Stream ID `0x01`.
- **BNI Pearl FaceID Routing**: Directly routes FaceID Near-Infrared frames into the Secure Enclave `SEP_TZ1S` memory domain (`0x000000086A1B0000`, Stream ID `0x02`), completely bypassing non-secure Darwin host memory.
- **3A Statistics**: Generates auto-exposure, auto-white-balance, and auto-focus histograms, firing AIC Vectors 284 (`frame_done`) and 285 (`stats_ready`).

### 6.3 AppleProResHW: AVE2 Dual-Core Video Accelerator

The AppleProResHW model emulates high-throughput 8K ProRes RAW compression:
- **Dual-Core Encoding**: Core A1 processes upper slices 0..7; Core A2 processes lower slices 8..15.
- **128-Byte FrameHeader**: Parses `sAppleProResRawFrameHeader` containing sensor crop dimensions, CFA pattern (RGGB/BGGR/GRBG/GBRG), Q16.16 white balance gains, and $3 \times 3$ color matrix coefficients.
- **Bitstream Verification**: Emits bitstreams prefixed with magic `'pr8k'` (`0x7072386B`) and calculates hardware IEEE 802.3 CRC32 checksums, firing AIC Vector 256 upon slice completion.

### 6.4 ExclaveOS cL4 Microkernel & Tightbeam IPC Relay

The Tightbeam model emulates cross-conclave RPC dispatch:
- **Immediate Syscall Trap**: Intercepts ARM64 `svc #0` instructions with thread IPC buffer (`L4_IpcBuffer_t`) and message header (`struct tb_message_s`).
- **88-Byte Wire Format**: Enforces invocation ID nonces, endpoint selectors, and capability delegation limits (`TB_MAX_CAPS = 8`).
- **Capability Badge Minting**: Mints unforgeable 64-bit reply badges (`0xCAFEBABE00000000 | (nonce & 0xFFFF)`), returning reply payloads to the caller and raising Exclave proxy interrupt Vector 361.

---

## 7. Bare-Metal RTKit Coprocessor Firmware Stubs

The platform includes bare-metal ARM64 firmware stubs compiled directly with `clang -target aarch64-none-elf -fuse-ld=lld`:
- **Boot Entrypoint (`stub_rtkit_boot.S`)**: Programs `vbar_el1`, initializes stack pointer `sp` in retention SRAM, writes the `0x52544B535441434B` (`'RTKSTACK'`) canary watermark, clears `.bss`, and enters `rtkit_main()`.
- **Protocol Handshake (`stub_rtkit_core.c`)**:
  - Responds to host `RTK_EP0_MSG_HELLO` with `RTK_EP0_MSG_HELLO_ACK` carrying protocol version `0x00020000`.
  - Advertises active endpoints bitmask via `RTK_EP0_MSG_EP_MAP`.
  - Streams diagnostic syslog messages over Endpoint 1: `"RTKitOS: [BOOT] Coprocessor ready, SMP 2 cores active, MMU enabled\n"`.
  - Services application commands over Endpoint 16+.

---

## 8. Verification Results & Telemetry Trace

Running the standalone emulation runner (`apple_a19_emulation_runner`) executes all four clean-room client workloads and validates the RTKit boot handshake with 100% green pass:

```
====================================================================
  Apple Silicon A19 Pro (t8150) Bare-Metal Emulation Runner
  Clean-Room Virtualization Platform (iOS 27.2 Build 24B119)
====================================================================

[1/6] Initializing Hardware Fabric & Subsystems...
      -> AIC v3/v4: 1024 IRQ lines ready
      -> ASCwrap-v6: Mailbox & Doorbell FIFO active
      -> DART IOMMU: Gen3/Gen4 16 KB page granules active

[2/6] Executing RTKit Coprocessor Endpoint 0 Handshake...
      -> [PASS] RTKit Handshake SUCCESS: Version 0x00020000 ACK received
      -> [PASS] RTKit Endpoint Map Received: 0x0000000300010003

[3/6] Running Workload 1: AppleMetalDirect (AGX G18 Pro GPU)...
      -> [PASS] AGX Compute Executed: Timestamp 0x00001001, Heartbeat 3, AIC IRQ 952 Acked

[4/6] Running Workload 2: Silenus Camera ISP & Bayer Neural Interface (BNI)...
      -> [PASS] Silenus CISP Frame Processed: BNI NIR Token 0x4E495230 in SEP TZ1S, IRQs 284 & 285 Acked

[5/6] Running Workload 3: AppleProResHW (AVE2 8K RAW Video Accelerator)...
      -> [PASS] ProRes 8K RAW Encoded: Magic 'pr8k', 16 Slices (A1:8, A2:8), CRC=0x6F653975, AIC IRQ 256 Acked

[6/6] Running Workload 4: Tightbeam IPC & ExclaveOS cL4 Syscall Bridge...
      -> [PASS] Tightbeam RPC Delivered: Reply Value=1554, Minted Badge=0xCAFEBABE0000CDEF, AIC IRQ 361 Acked

[+] Execution trace recorded to artifacts/qemu/logs/emulation_trace.json

====================================================================
  >>> ALL EMULATION WORKLOADS PASSED (100% GREEN) <<<
====================================================================
```

---

## 9. Deliverables Inventory

```
Artifact File Path                                      Role / Subsystem
---------------------------------------------------------------------------------------------------
artifacts/qemu/include/apple_a19_platform.h             Unified A19 Pro memory & register constants
artifacts/qemu/devices/apple_aic.h                      Apple Interrupt Controller v4 header
artifacts/qemu/devices/apple_aic.c                      Apple Interrupt Controller v4 model
artifacts/qemu/devices/apple_ascwrap.h                  ASCwrap-v6 Mailbox & Doorbell header
artifacts/qemu/devices/apple_ascwrap.c                  ASCwrap-v6 Mailbox & Doorbell model
artifacts/qemu/devices/apple_dart.h                     Apple DART Gen3/Gen4 IOMMU header
artifacts/qemu/devices/apple_dart.c                     Apple DART Gen3/Gen4 IOMMU model
artifacts/qemu/devices/apple_agx_direct.h               AppleMetalDirect AGX G18 Pro header
artifacts/qemu/devices/apple_agx_direct.c               AppleMetalDirect AGX G18 Pro model
artifacts/qemu/devices/apple_silenus_dma.h              Silenus Camera ISP & BNI header
artifacts/qemu/devices/apple_silenus_dma.c              Silenus Camera ISP & BNI model
artifacts/qemu/devices/apple_prores_hw.h                AppleProResHW AVE2 video accelerator header
artifacts/qemu/devices/apple_prores_hw.c                AppleProResHW AVE2 video accelerator model
artifacts/qemu/devices/apple_tightbeam_ipc.h            ExclaveOS Tightbeam IPC relay header
artifacts/qemu/devices/apple_tightbeam_ipc.c            ExclaveOS Tightbeam IPC relay model
artifacts/qemu/firmware/stub_rtkit_boot.S               Bare-metal ARM64 RTKit boot entrypoint
artifacts/qemu/firmware/stub_rtkit_core.h               RTKit state machine & protocol header
artifacts/qemu/firmware/stub_rtkit_core.c               RTKit state machine runtime implementation
artifacts/qemu/firmware/stub_rtkit_linker.ld            Bare-metal ARM64 linker script
artifacts/qemu/firmware/build_stubs.py                  ARM64 stub cross-compilation pipeline
artifacts/qemu/firmware/stub_rtkit_aop2.elf             Compiled AOP2 RTKit coprocessor stub
artifacts/qemu/firmware/stub_rtkit_silenus.elf          Compiled Silenus RTKit coprocessor stub
artifacts/qemu/firmware/stub_rtkit_rtbuddy.elf          Compiled AGX RTBuddy coprocessor stub
artifacts/qemu/machine/qemu_apple_a19_pro.c             QEMU MachineClass board model
artifacts/qemu/harness/apple_a19_emulation_runner.c     Standalone C execution harness
artifacts/qemu/harness/Makefile                         Runner build script
artifacts/qemu/specs/platform_hardware_topology.json    Platform hardware topology specification
artifacts/qemu/specs/accelerator_device_specs.json      Accelerator hardware specification
artifacts/qemu/specs/rtkit_firmware_stub_spec.json      RTKit firmware stub specification
artifacts/qemu/logs/emulation_trace.json                Execution trace telemetry log
findings/qemu/05_QEMU_VIRTUALIZATION_LAYER.md           Master technical report (40KB+)
tools/verify_qemu_emulation.py                          Automated 7-suite verification test script
---------------------------------------------------------------------------------------------------
Total: 30 Clean-Room Virtualization & Emulation Deliverables
```

---

## 10. Conclusion

The completion of the clean-room QEMU virtualization and emulation layer marks the synthesis of the entire iOS 27.2 reverse engineering effort for the Apple Silicon A19 Pro architecture. By bridging GPU graphics, neural biometric camera processing, hardware video encoding, and microkernel enclave IPC through unified memory and interrupt fabrics, this platform delivers an unprecedented, verifiable baseline for modern Apple Silicon emulation.
