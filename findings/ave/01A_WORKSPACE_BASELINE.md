# Apple Video Encoder 2 (AVE2) Hardware Codec Accelerator: Workspace Baseline & Container Spec

**Document Identifier**: `findings/ave/01A_WORKSPACE_BASELINE.md`  
**SoC Architecture**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Firmware Version**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Subsystem**: Apple Video Encoder 2 (AVE2) Multi-Stream Video Codec Accelerator  
**Extraction Methodology**: Clean-Room Image4 Extraction via `tools/parse_im4p.py`  

---

## 1. Executive Summary

The Apple Video Encoder 2 (AVE2) subsystem on the A19 Pro (`t8150`) SoC represents Apple's latest generation heterogeneous hardware media acceleration engine. Unlike earlier homogeneous DSP blocks, the H18 AVE2 engine couples an **ARM64e 64-bit Chinook Master Microprocessor** running an RTKit preemptive microkernel with an array of **9 independent 32-bit RISC-V (`riscv32i`) satellite micro-CPUs** dedicated to specialized pixel-pipeline stages.

The AVE2 accelerator is managed from the Darwin (XNU) kernel by `AppleAVE2.kext` and isolated behind the `dart-ave` Gen3 IOMMU (MMIO base `0x77020000`, aperture `128 KB`).

All 10 firmware images packaged in `Firmware/ave/` were extracted from the IPSW restore bundle, structurally parsed, and cataloged with complete cryptographic hashes.

---

## 2. Container Dissection & Cryptographic Ledger

Apple packages the AVE2 firmware assets using the ASN.1 Distinguished Encoding Rules (DER) Image4 container format (`IM4P`). The primary firmware payload (`AppleAVE2FW_H18.im4p`) carries the FourCC tag `avef` and encapsulates an uncompressed 64-bit Mach-O bare-metal preload image. The 9 auxiliary microcode images (`AppleAVE2FW_H18_AVE0.im4p` through `AppleAVE2FW_H18_AVE8.im4p`) carry tags `ave0` through `ave8` and encapsulate bare-metal RISC-V binary code.

```
+------------------------------------------------------------------------------------------------------------------------------------+
|                                                AVE2 FIRMWARE ASSET LEDGER                                                          |
+------------------------------------------------------------------------------------------------------------------------------------+
| Asset Filename               | FourCC | Container Size | Raw Payload Size | Target Core Architecture   | SHA-256 Digest (Container)     |
+------------------------------+--------+----------------+------------------+----------------------------+--------------------------------+
| AppleAVE2FW_H18.im4p         | avef   | 2,687,585 B    | 2,687,560 B      | ARM64E (Chinook Master)    | faf92ec00ef4a7d47f8d533594003bc4ef1af3f96d2432166b6643816e9379c2 |
| AppleAVE2FW_H18_AVE0.im4p    | ave0   | 9,543 B        | 9,520 B          | RISC-V 32-bit (Dispatcher) | 6bcbba7146a30a9b131001319104e1d5cae9d70a44f300b85c1605f5de460c22 |
| AppleAVE2FW_H18_AVE1.im4p    | ave1   | 16,463 B       | 16,440 B         | RISC-V 32-bit (HEIF Tuning)| bc734399d26e3f7387757cc0c56acfb791297d68933eb98d26b7eaf93401ca74 |
| AppleAVE2FW_H18_AVE2.im4p    | ave2   | 10,763 B       | 10,740 B         | RISC-V 32-bit (HW Results) | 1e15af0dd6a3d7459ec829610d11da8acc597f501114d1a6377214d139b4c7f2 |
| AppleAVE2FW_H18_AVE3.im4p    | ave3   | 9,067 B        | 9,044 B          | RISC-V 32-bit (Motion Pel) | 6d87cf8a3ded795f375eb969c9e9913f92654f5093b82d2e03bbfe2b9d3fe0cc |
| AppleAVE2FW_H18_AVE4.im4p    | ave4   | 11,327 B       | 11,304 B         | RISC-V 32-bit (MV Sifting) | 83c47583305d5dea9bb2bd5aa5178d0da0cebe4f2d5153fc01af1f55316596f8 |
| AppleAVE2FW_H18_AVE5.im4p    | ave5   | 11,003 B       | 10,980 B         | RISC-V 32-bit (RDO / Skip) | b2db8f82c393be83142cd54b24b5ac376e54c61b2c0ddd3e8d948be6250ece38 |
| AppleAVE2FW_H18_AVE6.im4p    | ave6   | 8,783 B        | 8,760 B          | RISC-V 32-bit (Deblocking) | cabdfe08031d95e9097ddd58cc0f079601739bb8b172a4ec60d55ffcc106ace1 |
| AppleAVE2FW_H18_AVE7.im4p    | ave7   | 11,943 B       | 11,920 B         | RISC-V 32-bit (VLC Coder)  | 9d5155e24adb746d3accf9af3119eca2c916237da0865298438f0d488b47868c |
| AppleAVE2FW_H18_AVE8.im4p    | ave8   | 26,303 B       | 26,280 B         | RISC-V 32-bit (Arbitrator) | 431412d31b1cd1b350e5267a386a60ae6f015802d99e3e848a8afa20a6b80189 |
+------------------------------+--------+----------------+------------------+----------------------------+--------------------------------+
```

---

## 3. Master Firmware Mach-O Structure (`AppleAVE2FW_H18.raw`)

The decompressed master firmware image `AppleAVE2FW_H18.raw` is an intact 64-bit Mach-O bare-metal execution container:

### 3.1 Header Attributes
- **Mach-O Magic**: `0xfeedfacf` (`MH_MAGIC_64`)
- **CPU Architecture**: `0x0100000c` (`CPU_TYPE_ARM64`)
- **CPU Subtype**: `0x80000002` (`CPU_SUBTYPE_ARM64E_PTRAUTH`) — Enforces Pointer Authentication Code (PAC00) signatures on function pointers and return registers.
- **File Type**: `0x00000005` (`MH_PRELOAD`) — Indicates a bare-metal coprocessor firmware image loaded at physical base addresses by the bootloader/kernel rather than standard dynamic Mach-O userland binaries.
- **Total Load Commands**: 7 commands spanning `2,552` bytes.
- **Mach-O Flags**: `0x00200001` (`MH_NOUNDEFS | MH_PIE`).
- **Binary UUID**: `11ae5742-2a71-37f9-ac2f-e78ce47ab324`.

### 3.2 Memory Segment Layout

The master firmware maps two primary operational segments:

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                    AppleAVE2FW_H18 MEMORY SEGMENT TABLE                                               |
+-----------------------------------------------------------------------------------------------------------------------+
| Segment Name   | VM Base Address    | VM Size     | File Offset | File Size   | Permissions & Role                    |
+----------------+--------------------+-------------+-------------+-------------+---------------------------------------+
| __TEXT         | 0x0000000000000000 | 0x00148000  | 0x00004000  | 0x00148000  | r-x (Executable Code & Read-Only Data)|
|   __text       | 0x0000000000000000 | 0x001175bc  | 0x00004000  | 0x001175bc  | r-x (Chinook Core ARM64E Instructions)|
|   __const      | 0x00000000001175c0 | 0x00017094  | 0x0011b5c0  | 0x00017094  | r-- (Codec Parameter Tables & Consts) |
|   __cstring    | 0x000000000012e654 | 0x000198ce  | 0x00132654  | 0x000198ce  | r-- (Debug Logs & Telemetry Strings)  |
| __DATA         | 0x0000000000148000 | 0x0012c000  | 0x0014c000  | 0x0012c000  | rw- (Mutable State, Queues & Stacks)  |
|   _rtk_patchbay| 0x0000000000148000 | 0x00000211  | 0x0014c000  | -           | rw- (RTKit Dynamic Patch Table)       |
|   _rtk_init_stk| 0x000000000014ec20 | 0x00010000  | 0x00152c20  | -           | rw- (Bootstrap Kernel Stack, 64 KB)   |
|   _rtk_irq_stk | 0x000000000015ec20 | 0x00001000  | 0x00162c20  | -           | rw- (Interrupt Servicing Stack, 4 KB) |
|   _rtk_exc_stk | 0x000000000015fc20 | 0x00001000  | 0x00163c20  | -           | rw- (Exception Handler Stack, 4 KB)   |
|   _rtk_boot    | 0x0000000000164000 | 0x00008000  | 0x00168000  | -           | rw- (Early Boot Reclaimable Memory)   |
|   _rtk_pgtables| 0x000000000016c000 | 0x00040000  | 0x00170000  | -           | rw- (Coprocessor MMU Translation Tbl) |
|   __zerofill   | 0x00000000001ac000 | 0x000c6860  | 0x001b0000  | -           | rw- (Dynamic BSS Heap & Buffers)      |
+----------------+--------------------+-------------+-------------+-------------+---------------------------------------+
```

---

## 4. Satellite RISC-V Micro-CPU Array Analysis

The 9 satellite firmware modules contain RISC-V 32-bit integer instructions (`riscv32i`). The micro-CPUs operate as dedicated hardware pipeline controllers tightly integrated with the AVE2 motion estimation, DCT transform, entropy encoding, and quantization datapaths:

```
+----------------------------------------------------------------------------------------------------+
|                                SATELLITE RISC-V MICRO-CPU DIRECTORY                                |
+----------------------------------------------------------------------------------------------------+
| Core ID | Target Engine           | Binary Size | Primary Exported Entrypoints & Handlers          |
+---------+-------------------------+-------------+--------------------------------------------------+
| AVE0    | Task Dispatcher         | 9,520 B     | _AVE_RV_Main, _AVE_RV_CtxExecute, _AVE_MCPUInit  |
| AVE1    | HEIF & Still Picture    | 16,440 B    | _AVE_HEIF_Process, _AVE_HEIF_QPModByVar          |
| AVE2    | HW Results Collector    | 10,740 B    | _AVE_ISR_HWResults, _UpdateFwData                |
| AVE3    | Sub-Pel Motion Search   | 9,044 B     | _AVE_RV_CtxExecute, _AVE_ISR_WakeUp              |
| AVE4    | MV Candidate Sifter     | 11,304 B    | _AVE_RV_ProcessHwResults, _AVE_RV_CtxExecute     |
| AVE5    | Rate Distortion (RDO)   | 10,980 B    | _gv_sSavedSkipMode, _AVE_RV_CtxExecute           |
| AVE6    | Deblocking & In-Loop    | 8,760 B     | _AVE_RV_Main, _AVE_RV_CtxExecute                 |
| AVE7    | VLC & Slice Headers     | 11,920 B    | _AVE_VLC_InsertHevcSliceHeader, _BitReverseTable |
| AVE8    | Pipeline Arbitrator     | 26,280 B    | __rtk_riscv_switch, _RTK_riscv32i_start          |
+---------+-------------------------+-------------+--------------------------------------------------+
```

---

## 5. Hardware Interconnect & IOMMU Topology

The AVE2 subsystem communicates with system DRAM via Apple's Gen3 Device Address Resolution Table (DART) IOMMU:
- **DeviceTree Node**: `dart-ave` (Node offset `0x3de91`).
- **MMIO Peripheral Base**: `0x77020000` (128 KB aperture, `0x20000` bytes).
- **Page Granularity**: 16 KB hardware translation granules.
- **Hardware Mapper**: `mapper-ave` providing isolated virtual address translation buffers for source YUV frames, compressed NAL units, and reference frame Decoded Picture Buffers (DPB).

---

## 6. Verification Status

All Phase 1A extraction artifacts were validated:
- `artifacts/ave/phase_1a_workspace_baseline.json`: Valid JSON schema, complete device context.
- `artifacts/ave/ave_firmware_container_spec.json`: Valid JSON schema, all 10 firmware targets cataloged.
- `findings/ave/01A_WORKSPACE_BASELINE.md`: Formatted technical report with complete empirical verification.
