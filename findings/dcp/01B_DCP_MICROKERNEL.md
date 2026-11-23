# Phase D1B: Display Coprocessor (DCP) — RTKit Microkernel, Task Topology & Hardware Pipe Architecture

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Research Classification**: RTKit Execution Model, Task Prioritization, and GenPipe_v33 Hardware Topology  
**Date**: November 2026  

---

## 1. RTKitOS Microkernel Executive in the Display Domain

The Apple Display Coprocessor runs an optimized build of Apple's proprietary real-time operating system:  
`RTKit_armv8_cl4_Oz_flto_pac-3514.40.18.release`.

Unlike general-purpose application cores, the DCP's ARM64e execution engine operates under strict deterministic timing constraints: a missed deadline in the display pipeline directly causes visual artifacts, display tearing, or dropped frames.

```
+----------------------------------------------------------------------------------------------------+
|                                      HOST AP (Darwin / XNU)                                        |
|  [WindowServer] ------> [IOMobileFramebuffer] ------> [AppleCLCD2.kext]                          |
+----------------------------------------------------------------------------------------------------+
                                                  |
                  [ASCwrap-v6 Mailbox MMIO: 0x100600000 | 64-Word FIFOs | AIC 411/403]
                                                  |
+----------------------------------------------------------------------------------------------------+
|                                DISPLAY COPROCESSOR (DCP) ARM64e CORE                               |
|                                                                                                    |
|  =============================== RTKitOS MICROKERNEL SCHEDULER ==================================  |
|  - Priority 62 (Hard Real-Time): VFTG_Subframe_ISR (VSYNC generation & Tearing Effect alignment)   |
|  - Priority 56 (High Real-Time): PIODMA_Tagging_Worker (LUT & calibration hardware pushes)         |
|  - Priority 48 (Firm Real-Time): SWMPR_Refresh_Governor (ProMotion dynamic rate arbitrator)       |
|  - Priority 40 (Normal RT):      AOP_Flipbook_Consumer (1Hz AOD frames via CBAOPEndpoint)          |
|  - Priority 24 (Low RT):         BICS_Aging_Accumulator (OLED burn-in mitigation math)             |
|                                                                                                    |
|  ================================== GenPipe_v33 PIPELINE ========================================  |
|  [Stage 1: DMA Ingestion]   --> [Stage 2: Blending/Comp]    --> [Stage 3: Color/Tone Mapping]      |
|  UPBlock_GenPipe_v33            UPBlock_Blend_v18               UPBlock_ColorManager_v19           |
|  UPBlock_CDI_v1                 UPBlock_DPE_v1                  UPBlock_PCC2DLTM_v12               |
|                                                                                                    |
|  [Stage 4: True Tone/Env]   --> [Stage 5: Panel Uniformity] --> [Stage 6: ProMotion Timing]       |
|  UPBlock_ALSS                   UPBlock_BICS_v19                UPBlock_VFTG_v38                   |
|  UPBlock_ACSS_v11               UPBlock_PDC_v11                 UPBlock_SWMPR_v1                   |
|  UPBlock_ABG_v4                 UPBlock_PTUC_v4                 (Flexible Vertical Timing)         |
|                                                                                                    |
|  [Stage 7: Output Dither & MIPI DSI Serialization]                                                 |
|  UPBlock_Dither_v24 --> UPBlock_Regamma_v5 --> AppleDCPSynopsysMIPIDSIController                  |
+----------------------------------------------------------------------------------------------------+
                                                  |
                   [Dedicated DART Display IOMMUs: 0x1fa340000 / 0x1fa300000]
                                                  |
+----------------------------------------------------------------------------------------------------+
|                                        SYSTEM LPDDR5X DRAM                                         |
|  - dcp_runtime_window (48 MB): RTKit heap pools & task descriptors (0x810000000)                   |
|  - disp0_isoc_dram_pool (80 MB): Triple framebuffers (2868x1320 @ 4B/px) (0x813000000)             |
|  - dcp_lut_staging_window (16 MB): 2D PCC, SPUC maps & BICS history (0x818000000)                  |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Multi-Enclave IPC Endpoints (AFK & Tightbeam)

The DCP establishes four standardized communication endpoints across the system fabric:

1. **`AFKBuiltinAPMailboxEndpoint` (Endpoint 1)**:  
   Carries command descriptors from the Darwin kernel (`AppleCLCD2.kext` / `IOMobileFramebuffer`). When WindowServer completes a composited surface, it issues a swap token containing buffer Device Virtual Addresses (DVAs) mapped through `dart-disp0`.
2. **`CBAOPEndpoint` (Endpoint 2)**:  
   Direct link to the Always-On Processor (AOP). In Always-On Display (AOD) mode, Darwin puts the AP cores to sleep. The AOP computes ambient clock movements, battery states, and widgets, assembling them into lightweight Context Buffer (CB) flipbook frames delivered straight to the DCP at 1Hz.
3. **`RTKExclaveTBEndpoint` (Endpoint 3)**:  
   A capability-isolated Tightbeam RPC endpoint connecting the DCP to ExclaveOS Conclaves. This endpoint handles direct presentation of the hardware Secure Indicator Light (`EXSurface` / SIL), guaranteeing that camera and microphone dots are rendered by hardware regardless of Darwin host compromise.
4. **`RTKTrustedTBEndpoint` (Endpoint 4)**:  
   Secure link to the Secure Enclave Processor (SEP) for HDCP 2.3 key exchange and hardware-protected content decryption.

---

## 3. Unified Pipe Blocks (`UPBlock`) Architecture

The A19 Pro features the 33rd revision of Apple's display processing hardware: **GenPipe_v33**. In the DCP firmware, 38 discrete `UPBlock` C++ drivers are instantiated to program the hardware execution stages:

### Key Hardware Blocks
- **`UPBlock_VFTG_v38` (Vertical Flexible Timing Generator)**:  
  Enables variable frame intervals by dynamically adjusting vertical back porch blanking lines without resynchronizing the MIPI DSI physical link.
- **`UPBlock_SWMPR_v1` (Software-Managed Pixel Refresh)**:  
  Tracks touch event timestamps and velocity vectors, transitioning the display between 120Hz (high motion) and lower refresh rates (e.g. 10Hz/24Hz/30Hz/60Hz).
- **`UPBlock_PCC2DLTM_v12` (Pixel Color Calibration & 2D Local Tone Mapping)**:  
  Divides the 2868x1320 display into a 2D grid, applying spatial tone-mapping curves in real time for HDR/EDR highlights up to 2000 nits.
- **`UPBlock_BICS_v19` (Burn-In Compensation System)**:  
  Maintains an accumulated aging matrix for every OLED subpixel, compensating for differential degradation across static UI elements (such as the status bar and Home Indicator).

This completes Phase D1B.
