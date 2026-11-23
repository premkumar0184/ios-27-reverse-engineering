# Phase D1A: Display Coprocessor (DCP) & ProMotion Pipeline — Workspace Baseline & Container Dissection

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Target Firmware**: `Firmware/dcp/t8150dcp.im4p` (2,466,452 bytes compressed)  
**Research Classification**: Display Pipeline, Dynamic Refresh Rate (ProMotion), and RTKit Coprocessor Architecture  
**Date**: November 2026  

---

## 1. Executive Summary

On modern Apple Silicon (A19 Pro / `t8150`), display scanout, pixel composition, panel timing, and variable refresh rate arbitration are completely decoupled from the Application Processors (AP) and the primary GPU. Instead, Apple utilizes an autonomous, high-performance display coprocessor known as the **Display Coprocessor (DCP)** or **Timing Controller (TCON) Executive**.

The DCP executes a dedicated instance of Apple's **RTKitOS** microkernel (`RTKit_armv8_cl4_Oz_flto_pac-3514.40.18.release`) running on a dedicated 64-bit ARM64e core equipped with Pointer Authentication (PAC00) and Branch Target Identification (BTI). The firmware coordinates:
1. **Vertical Flexible Timing Generator (VFTG)**: Generating dynamic pixel clocks and front/back porch timings to drive variable refresh rates from 1Hz (Always-On Display) up to 120Hz (ProMotion).
2. **Software-Managed Pixel Refresh (SWMPR)**: State machine arbitrating instantaneous refresh rate switches (10Hz, 24Hz, 30Hz, 48Hz, 60Hz, 80Hz, 120Hz) based on user interaction, touch velocity, and media playback metadata.
3. **Hardware Unified Pipe Blocks (UPBlocks)**: A 38-stage hardware processing pipeline performing real-time subpixel rendering, Burn-In Compensation (BICS), Ambient Light Shift (ALSS / True Tone), and Pixel Color Calibration (PCC).
4. **Always-On Display Flipbook Architecture**: In low-power sleep mode, the Always-On Processor (AOP) sends frame flipbooks directly to the DCP over an Apple Firmware Kit (AFK) IPC endpoint without waking Darwin/XNU or the GPU.

---

## 2. Firmware Container Architecture: Image4 & LZFSE

The DCP firmware container is packaged as an Apple Image4 payload (`t8150dcp.im4p`) within the restore bundle.

### 2.1 ASN.1 DER Header Breakdown
The file begins with a standard Image4 Payload wrapper:
```
30 83 25 a1 50          ; SEQUENCE (Length 0x25a150 = 2,466,128 bytes)
  06 09 2a 86 48 86 f7  ; OID: 1.4.840.113635.100.4.1 (Apple Image4 Payload)
        0d 01 0c 01
  16 04 64 63 70 66     ; IA5String: "dcpf" (FourCC: Display Coprocessor Firmware)
  16 01 31              ; IA5String: "1" (Payload Version)
  04 83 25 a1 30        ; OCTET STRING (Length 0x25a130 = 2,466,096 bytes)
    62 76 78 32 ...     ; Magic: "bvx2" (LZFSE Compressed Stream)
```

### 2.2 LZFSE Decompression & BUND Analysis
Decompressing the 2.46 MB `bvx2` payload produces a 16,990,208 byte (16.20 MB) binary. Inspecting the decompressed stream reveals an Apple **BUNDLE** (`DNUB`) container:
- Magic: `0x42554e44` (`DNUB` at offset `0x08`)
- Version: `0x00040000` (4.0)
- Number of TOC Entries: `11`
- Embedded Mach-O Slices:
  - Slice 0 (`0x00011000`): Mach-O 64-bit `MH_EXECUTE` (`__TEXT` at `0x08000000`, 136 KB). Contains the primary display runtime, pipe control algorithms, and pixel compensation LUT handlers.
  - Slice 1 (`0x00fe4000`): Mach-O 64-bit `MH_PRELOAD` (`__TEXT` at `0xffffffff00000000`, 68 KB). Contains the low-level RTKit microkernel boot executive and trap vectors.

---

## 3. Hardware Interconnect & Memory Map

The DCP interfaces with the host AP and memory subsystems via dedicated MMIO controllers mapped in the A19 Pro DeviceTree:

### 3.1 ASCwrap-v6 Mailbox Geometry
- **DeviceTree Node**: `/arm-io/dcp`
- **Compatible**: `iop,ascwrap-v6`, `iop-nub,rtbuddy-v2`
- **MMIO Base Address**: `0x0000000100600000`
- **MMIO Window Size**: `557,056 bytes` (544 KB)
- **FIFO Depth**: 64 bidirectional words with hardware threshold interrupts.

### 3.2 DART IOMMU Display Stream Allocation
DMA access from the DCP into system DRAM is fenced by multiple dedicated DART IOMMU controllers:
- `dart-dcp`: Base `0x1fa340000`, size 48 KB (DCP control DMA)
- `dart-disp0`: Base `0x1fa300000`, size 48 KB (Primary display scanout pipe)
- `dart-dispgrt`: Base `0x1fa320000`, size 48 KB (Graphics real-time stream)
- `dart-disp0-isoc`: Base `0x1fa1c0000`, size 128 KB (Isochronous memory channel)
- `dart-scaler`: Base `0x81260000`, size 128 KB (Hardware display scaling engine)

### 3.3 Interrupt Controller (AIC) Vectors
The DCP registers four critical interrupt lines with the Apple Interrupt Controller:
- `DISP_INT_DCP`: Vector 411 (`0x019b`) — Primary DCP interrupt
- `DISP_EXT0_DCP`: Vector 412 (`0x019c`) — External display coprocessor interrupt
- `DCP0-V`: Vector 403 (`0x0193`) — VSYNC and vertical timing interrupt
- `DCPEXT0-V`: Vector 405 (`0x0195`) — External VSYNC interrupt

This concludes the empirical baseline for Phase D1A.
