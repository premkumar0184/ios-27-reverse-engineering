# Phase 2 Findings: Apple Silicon A19 Pro (t8150) Unified DART Gen3 IOMMU & Coprocessor DMA Ledger

**Target Platform**: Apple Silicon A19 Pro (`t8150`) / iPhone18,3 / Device Class `v57ap`  
**IOMMU Architecture**: DART Gen3 (Device Address Resolution Table Version 3)  
**Translation Granule**: 16 KB Physical Page Granularity  
**Artifact Dependencies**:
- [`artifacts/synthesis/unified_dart_iommu_ledger.json`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/unified_dart_iommu_ledger.json)
- [`artifacts/sptm/devicetree_hardware_map.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/devicetree_hardware_map.json)
- [`artifacts/aop/aop_hardware_registers.json`](file:///home/prem/Projects/iOS%2027/artifacts/aop/aop_hardware_registers.json)

---

## 1. DART Gen3 Translation & Protection Architecture

On the Apple Silicon A19 Pro (`t8150`), peripheral DMA masters are strictly prohibited from issuing untranslated physical memory operations directly to system DRAM. All coprocessor memory transactions are mediated by dedicated **DART Gen3 (Device Address Resolution Table Version 3)** hardware IOMMU controllers.

```
+----------------------------------------------------------------------------------------------------+
| DART GEN3 TRANSLATION & HARDWARE PROTECTION PIPELINE                                               |
+----------------------------------------------------------------------------------------------------+
| Coprocessor Master (SEP, AOP2, ANE, GPU, DCP, ISP)                                                 |
|    |                                                                                               |
|    v  Issues 36-bit Device Virtual Address (DVA) + 8-bit Stream ID (SID)                           |
| [ DART Gen3 Controller ]                                                                           |
|    |                                                                                               |
|    +---> Check 1: Stream ID Enabled & Bypass Flag? (If bypassed: FAULT)                            |
|    +---> Check 2: TLB Hit? (High-speed hardware translation cache)                                 |
|    +---> Check 3: Page Table Walk (2-Level Radix Tree, 16 KB Granule)                              |
|    |         - Level 1: Page Directory Pointer Table (PDPT)                                        |
|    |         - Level 2: Page Table Entries (PTE: Physical Frame | R/W | Enclave-Tag)                |
|    v                                                                                               |
| [ Fabric Protection Filter (GAPF) ]                                                                |
|    | Checks physical destination address against CTRR and carveout ranges                          |
|    v                                                                                               |
| Apple Coherent Fabric 7 (ACF7) ===> Target DRAM / SRAM Physical Memory                             |
+----------------------------------------------------------------------------------------------------+
```

### 1.1 DART Hardware Register Model
Every DART Gen3 controller exposes an identical standard register layout within its 48 KB (`0xc000`) or 128 KB (`0x20000`) MMIO window:
- `+0x0000` (`DART_CONFIG`, 32-bit): Global translation enable, bypass disable, bus error reporting.
- `+0x0004` (`DART_TLB_FLUSH`, 32-bit): Write-1-to-flush TLB by Device Virtual Address (DVA).
- `+0x0010` (`DART_TLB_FLUSH_ALL`, 32-bit): Invalidate all active translation entries across all SIDs.
- `+0x0040` (`DART_ERROR_ADDR`, 64-bit): Captured faulting 36-bit DVA upon page translation failure.
- `+0x0048` (`DART_ERROR_STATUS`, 32-bit): Fault type code (permission fault, unmapped page, stream mismatch).
- `+0x0100 + (SID * 0x20)` (`DART_STREAM_CONFIG[SID]`): Per-stream translation table root physical address.

---

## 2. Complete Inventory of All 25 DART Controllers

Empirical extraction from `DeviceTree.v57ap.im4p` confirmed exactly **25 DART Gen3 IOMMU controllers** active on the A19 Pro:

| Index | Controller Name | MMIO Base Address | Window Size | AIC IRQ Vector | Managed Coprocessor Subsystem |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **00**| `dart-aop` | `0x0000000100fc0000` | 48 KB (`0xc000`) | `0x0183 (387)` | Always-On Processor 2 (AOP2) & SPU |
| **01**| `dart-pmp` | `0x00000000f0300000` | 48 KB (`0xc000`) | `0x030c (780)` | AGX G18 Power Management & RTBuddy |
| **02**| `dart-sep` | `0x0000000070c80000` | 128 KB (`0x20000`)| `0x013a (314)` | Secure Enclave Processor (SEP A19) |
| **03**| `dart-sio` | `0x0000000175060000` | 128 KB (`0x20000`)| `0x041e (1054)`| High-Speed Serial I/O (SPI/UART/I2S) |
| **04**| `sart-ans` | `0x000000017dc50000` | 48 KB (`0xc000`) | `0x03cd (973)` | Apple NAND Storage Controller (ANS) |
| **05**| `dart-rsm` | `0x00000000f99a0000` | 48 KB (`0xc000`) | `0x0109 (265)` | Remote Security Monitor |
| **06**| `dart-mtp` | `0x0000000104800000` | 48 KB (`0xc000`) | `0x042d (1069)`| Multi-Touch Processor (MTP) |
| **07**| `dart-usb0` | `0x0000000402f00000` | 128 KB (`0x20000`)| `0x0495 (1173)`| USB 3.2 / USB4 SuperSpeed DMA |
| **08**| `dart-dcp` | `0x00000001fa340000` | 48 KB (`0xc000`) | `0x028b (651)` | Display Co-Processor (DCP) Control |
| **09**| `dart-disp0` | `0x00000001fa300000` | 48 KB (`0xc000`) | `0x028b (651)` | Internal Panel Primary Scanout |
| **10**| `dart-dispgrt`| `0x00000001fa320000` | 48 KB (`0xc000`) | `0x028b (651)` | Display Real-Time Graphics Pipe |
| **11**| `dart-disp0-isoc`| `0x00000001fa1c0000`| 128 KB (`0x20000`)| `0x02a2 (674)` | Display Isochronous Memory Pipe |
| **12**| `dart-dcpext0`| `0x00000001fe340000` | 48 KB (`0xc000`) | `0x02d3 (723)` | External Display DCP Controller |
| **13**| `dart-dispext0`| `0x00000001fe300000`| 48 KB (`0xc000`) | `0x02d3 (723)` | External Display Frame Buffer |
| **14**| `dart-dispext0-isoc`| `0x00000001fe1c0000`| 128 KB (`0x20000`)| `0x02ea (746)`| External Display Isochronous DMA |
| **15**| `dart-scaler`| `0x0000000081260000` | 128 KB (`0x20000`)| `0x03eb (1003)`| Hardware Image Scaler Pipe |
| **16**| `dart-jpeg` | `0x000000007d020000` | 48 KB (`0xc000`) | `0x03d6 (982)` | Hardware JPEG Codec DMA |
| **17**| `dart-isp` | `0x00000001128c0000` | 48 KB (`0xc000`) | `0x012e (302)` | Image Signal Processor (Bayer/YUV) |
| **18**| `dart-ave` | `0x0000000077020000` | 128 KB (`0x20000`)| `0x0395 (917)` | Apple Video Encoder (AVE / ProRes) |
| **19**| `dart-avd` | `0x0000000085020000` | 128 KB (`0x20000`)| `0x0389 (905)` | Apple Video Decoder (AVD / HEVC) |
| **20**| `dart-apr` | `0x0000000171020000` | 128 KB (`0x20000`)| `0x049e (1182)`| Apple Pixel Realizer (APR) |
| **21**| `dart-ane` | `0x0000000271800000` | 48 KB (`0xc000`) | `0x0260 (608)` | Apple Neural Engine H18 Tensors |
| **22**| `audio-shared-dart-proxy`| Virtual Interface | Proxy Window | `0x0000 (0)` | Shared Low-Power Audio DMA Bridge |
| **23**| `dart-apcie0`| `0x0000000180000000` | 128 KB (`0x20000`)| `0x0476 (1142)`| PCIe Port 0 (Baseband Modem DMA) |
| **24**| `dart-apcie1`| `0x0000000181000000` | 128 KB (`0x20000`)| `0x047e (1150)`| PCIe Port 1 (WLAN / Bluetooth / UWB)|

---

## 3. Cross-Enclave Stream ID (SID) Routing Matrix

The core security innovation of the A19 Pro is the use of dedicated **Stream IDs** to establish hardware-enforced private tunnels between coprocessors without exposing intermediate buffers to the Darwin host kernel:

```
+----------------------------------------------------------------------------------------------------+
| CROSS-ENCLAVE DIRECT DART STREAM MAPPINGS                                                          |
+----------------------------------------------------------------------------------------------------+
| Source Subsystem   | DART Instance | Stream ID | Destination Target        | Physical Carveout     |
| Camera ISP         | dart-isp      | SID 0x02  | SEP Pearl NIR Buffer      | SEP TZ1S (0x86a1b0000)|
| Apple Neural Engine| dart-ane      | SID 0x02  | SEP Biometric Tensor Pool | SEP TZ1S (0x86d1b0000)|
| Secure Enclave     | dart-sep      | SID 0x02  | ExclaveOS Biometric Engine| SEP TZ1S (0x86e1b0000)|
| Always-On Processor| dart-aop      | SID 0x11  | ExclaveOS Privacy Monitor | ExclaveCore (0x824000)|
| Display Co-Proc    | dart-dcp      | SID 0x02  | ExclaveOS SIL Overlay Pipe| ExclaveCore (0x824000)|
| AOP2 Motion Hub    | dart-aop      | SID 0x10  | Darwin FastPath Ring Buffer| Host DRAM (0x87000000)|
+----------------------------------------------------------------------------------------------------+
```

### 3.1 Face ID Private Ingest Pipeline
1. Camera sensor streams Near-Infrared frames into `dart-isp` using **Stream ID `0x02`**.
2. `dart-isp` translates DVAs directly into physical addresses inside **SEP TZ1S** (`0x86a1b0000`).
3. Neither the host Darwin kernel nor the GPU can read or modify these NIR buffers.
4. SEP triggers ANE via `ane_map_iobmd` using **Stream ID `0x02`** on `dart-ane` to execute embedding inference directly within the secure perimeter.

### 3.2 Sensor Indicator Light (SIL) Hardware Path
1. AOP2 monitors camera/microphone power rails and physical action button states.
2. When active, AOP2 sends a Tightbeam frame via **DART-AOP Stream ID `0x11`** to ExclaveOS.
3. ExclaveOS constructs the green/orange indicator glyph within a protected surface.
4. ExclaveOS instructs the Display Co-Processor via **DART-DCP Stream ID `0x02`** to blend the indicator dot directly into the scanout compositor out-of-band from SpringBoard.
