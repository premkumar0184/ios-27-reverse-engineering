#!/usr/bin/env python3
"""
tools/insert_ave_mtp_parts.py
Inserts:
  - Part XXVII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines
  - Part XXVIII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence
  - Renumbers Glossary to Part XXIX
"""

from pathlib import Path

BOOK_PATH = Path("APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md")

part_xxvii = r"""## Part XXVII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines

### 27.1 Subsystem Overview & Heterogeneous Codec Topology
The Apple Silicon A19 Pro (`t8150`) integrates a dedicated, multi-block hardware video acceleration cluster decoupled into three specialized silicon engines:
1. **Apple Video Decoder (AVD)**: Memory-mapped at `0x77040000`, protected by `dart-avd` (Stream ID `0x02`, 16 Stream IDs). Capable of multi-stream decoding of AV1, HEVC (Main 10 / Main 12), H.264 (Level 5.2), and VP9 up to 28,096 samples/second. Features the **Apple Decryption Service (ADS)** hardware keystore v3 (`avd-ads-keytype-version: 3`) for direct hardware-protected FairPlay DRM streaming directly into secure DART-backed framebuffers without host CPU exposure.
2. **Apple Video Encoder 2 (AVE2)**: Memory-mapped at `0x77020000`, protected by `dart-ave` (Stream ID `0x01`). Houses the **AV1 Boreas**, **HEVC Erebus**, and **AVC Erebus** inter-frame encoding pipelines, coupled to an autonomous 9-core 32-bit RISC-V satellite coprocessor array (`AVE0` through `AVE8`) and dedicated hardware motion estimation coprocessors (**HMESC**, **LRME**, **DMV**, **MCTF**).
3. **Apple ProRes Hardware Accelerator (AppleProResHW)**: Memory-mapped at `0x77080000`, protected by `dart-apr` (Stream ID `0x18`). Comprises a master arbiter (`apr,m0`) and two parallel slice processing engines (`apr,a1` and `apr,a2`), executing real-time 8K 60fps **ProRes 422 HQ** (16-slice parallelization) and direct uncompressed 14-bit Bayer **ProRes RAW** encoding (4-plane CFA ingestion bypassing the ISP demosaicing engine).

```
+=======================================================================================================================+
|                                    A19 PRO HETEROGENEOUS VIDEO CODEC CLUSTER TOPOLOGY                                 |
+=======================================================================================================================+
|                                          SYSTEM MEMORY (LPDDR5X-8533 / ACF7 CROSSBAR)                                  |
|                                       Input Frames / Reference Buffers / Output Bitstreams                            |
+-----------------------------------+-----------------------------------+-----------------------------------------------+
                 |                                                   |                                                   |
      DART-AVD (SID 0x02)                                 DART-AVE (SID 0x01)                                 DART-APR (SID 0x18)
                 |                                                   |                                                   |
+----------------v------------------+               +----------------v------------------+               +----------------v------------------+
|    Apple Video Decoder (AVD)      |               |     Apple Video Encoder 2 (AVE2)  |               |     AppleProResHW Accelerator     |
|    Base: 0x77040000               |               |     Base: 0x77020000              |               |     Base: 0x77080000              |
|  - AV1 / HEVC / H.264 Decode      |               |  - AV1 Boreas / HEVC Erebus Pipe  |               |  - Master Arbiter (apr,m0)        |
|  - ADS Keystore v3 (FairPlay DRM) |               |  - 9x RISC-V Satellites (AVE0..8) |               |  - Slice Engine 1 (apr,a1: 0..7)  |
|  - Botanical Queues (Borage..Kops)|               |  - HMESC / LRME / DMV / MCTF ME   |               |  - Slice Engine 2 (apr,a2: 8..15) |
|  - Multi-Stream Flight Control    |               |  - Rate Control & Lagrangian RDO  |               |  - 8K ProRes RAW 4-Plane CFA Ingest|
+-----------------------------------+               +-----------------------------------+               +-----------------------------------+
```

### 27.2 Apple Video Decoder (AVD) Multi-Stream Architecture
The AVD engine is driven by the XNU driver `com.apple.driver.AppleAVD` (1.64 MB in kernelcache). It partitions concurrent decoding sessions across multi-level hardware priority queues designated by botanical codenames (`CPriorityQueueBorage`, `Catnip`, `Clary`, `Clover`, `Dahlia`, `Daisy`, `Hibiscus`, `Ixora`, `Kopsia`).
- **Hardware Command Patcher (`AppleAVDCommandPatcher`)**: Inspects incoming bitstream slice headers in kernel space, validating slice parameter boundaries (`saHEVC_PPS`, `saHEVC_SPS`, `sHEVC_VPS`, `sHEVC_RPS`) before programming hardware doorbells.
- **Flight Control (`AppleAVDCoreFlightControl`)**: Regulates macroblock pipeline scheduling and clock gating (`AVDWRAPCTRL_AVDCTRL_CLOCKGATEENABLE`), ensuring deterministic real-time decoding latency for simultaneous 4K/8K picture-in-picture playback.
- **FairPlay DRM Hardware Isolation**: Protected content is decrypted directly within the AVD core using key slots loaded from the Secure Enclave via `AppleAVDADSInfo`. Decrypted YUV pixels are written directly into protected DART translation apertures inaccessible to user-space applications or unsigned kernel code.

### 27.3 Apple Video Encoder 2 (AVE2) & RISC-V Motion Estimation Network
AVE2 utilizes a primary 64-bit ARM64e RTKit microkernel container (`AppleAVE2FW_H18.raw`, 2,687,560 bytes) assisted by 9 satellite 32-bit RISC-V microcode engines (`AVE0.raw` through `AVE8.raw`):
- `AVE0` (9,520 B): Frame Dispatcher & DMA queue ingress.
- `AVE1` (16,440 B) & `AVE2` (10,740 B): In-loop Deblocking Filter (DBF) & Constrained Directional Enhancement Filter (CDEF) accelerators for AV1.
- `AVE3` (9,044 B): Sub-pixel interpolation & fractional-pel search engine.
- `AVE4` (11,304 B): Motion candidate sifter & spatial predictor engine.
- `AVE5` (10,980 B): Rate-Distortion Optimization (RDO) solver & skip mode decision.
- `AVE6` (8,760 B) & `AVE7` (11,920 B): Entropy coder bitstream serializes (CABAC / AV1 CDF engine).
- `AVE8` (26,280 B): Multi-stream master arbitrator & hardware synchronization manager.

The motion estimation coprocessor cluster executes a 4-tier hierarchical search:
1. **HMESC**: 4-level quadtree hierarchical motion estimation candidate generator evaluating directional spatial variance metrics (Horizontal, Vertical, D45, D135).
2. **LRME**: Low-Resolution Motion Estimation operating over 16:1 downsampled luma pyramids across a $[-128, +127] \times [-64, +63]$ window.
3. **DMV**: Dense Motion Vector calculation producing quarter-pel accurate vectors for every $4 \times 4$ sub-block.
4. **MCTF**: Motion-Compensated Temporal Filtering filtering spatial noise across 3 past reference buffers (`MCTF LFSRef buffers num %d`).

### 27.4 AppleProResHW 8K ProRes 422 HQ & ProRes RAW Real-Time Pipelines
The `AppleProResHW` IP block (`0x77080000`, `dart-apr`) implements dedicated intra-frame transform engines:
- **8K ProRes 422 HQ Parallelization**: An $8192 \times 4320$ raster is split into 16 horizontal macroblock slices (`log2DesiredSliceSizeInMb = 13`). The master dispatcher `apr,m0` partitions Slices 0..7 to `apr,a1` and Slices 8..15 to `apr,a2`. Controlled via `ProRes_EncodeFrame_UserKernel_In_Info` (`EncodeYCbCr`), utilizing 6 complexity thresholds (`mbCategoryThr0..5`) and Lagrangian multipliers (`alpha`, `alpha0`, `gamma0`, `beta[4]`).
- **8K ProRes RAW Direct Sensor Ingestion**: Uncompressed 14-bit CFA Bayer sensor frames ($R, G_r, G_b, B$) are ingested across 4 discrete spatial planes, bypassing the ISP demosaicing engine entirely. Controlled via a 128-byte `sAppleProResRawFrameHeader_t` prepended to the bitstream containing active crop geometries, CFA patterns, analog gains, $3 \times 3$ color matrix (`cm[0..8]`), and transfer curve coefficients (`tf[0..7]`).

---
"""

part_xxviii = r"""## Part XXVIII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence

### 28.1 Multi-Touch Processor (MTP) RTKit Architecture
The touch sensing plane on the A19 Pro is driven by an autonomous **Multi-Touch Processor (MTP)** coprocessor image packaged in `Firmware/V57_MtpFirmware.im4p` (FourCC `mtpf`, 9,981,367 bytes). The binary encapsulates an RTKit OS flash table (`rkosftab`) containing 5 partitions:
- `A5PH` (2,433,024 bytes): Primary Touch Sensor Controller firmware for active scan modes.
- `P5S1` (2,433,024 bytes): Low-power sleep scan and wake-on-tap gesture engine.
- `P5L1` (2,433,024 bytes): Large-area touch rejection and palm filtering DSP pipeline.
- `P5B1` (2,433,024 bytes): Stylus / Apple Pencil active electro-magnetic digitizer firmware.
- `iokt` (249,118 bytes): IOKit driver shim, calibration parameters, and surface configuration.

Driven by `com.apple.driver.AppleMultitouchDriver` (170 KB in kernelcache), MTP processes 120 Hz / 240 Hz mutual-capacitance raw frame matrices (`reportBuffer16P16`), executing spatial baseline calibration, water-droplet suppression, and multi-finger contact centroid tracking (`_handleTouchFrame`).

### 28.2 Leap Haptics & Actuator Synchronization
Haptic feedback is coordinated by the **Leap Haptics** subsystem (`Firmware/V57_LeapHapticsFirmware.im4p`, FourCC `lphp`, 312,552 bytes XML property dictionary) and kernel driver `com.apple.driver.AppleHapticsSupportLEAP`. It interfaces directly to a custom voice-coil Linear Resonant Actuator (LRA), synthesizing complex tactile textures, click stops, and button emulation waveforms with sub-millisecond phase alignment to touch down events.

### 28.3 MagSafe Wireless Power (Qi2 / WPC) & Tri-Subsystem Coexistence
The A19 Pro incorporates an autonomous **Wireless Power Coprocessor** image (`Firmware/WirelessPower/WirelessPower.d23_v5z.im4p`, FourCC `wchf`, 239,988 bytes raw binary) driven by `com.apple.driver.AppleSMCWirelessCharger`. 

Because inductive wireless charging transmits at $110\text{ kHz} - 360\text{ kHz}$ with harmonics extending into megahertz bands, the SoC enforces a dynamic, tripartite hardware coexistence arbitration matrix:
1. **Touch Coexistence Throttling (`touchCoexThrottleStateMachineSetState`)**: The MTP sensor scan window is frequency-locked to the switching frequency of the MagSafe inverter bridge. Capacitive ADC integrations occur strictly during zero-crossing switching deadtimes, completely eliminating touch jitter and phantom taps during 15W/25W wireless fast charging.
2. **Display Frame Scanout Interleaving (`noiseAvoidanceChangeNotification`)**: Switching pulses are phased outside the OLED gate driver scan intervals to prevent display line noise and flicker.
3. **RF Wireless Coexistence Limiting (`_coexLimitPower`)**: When cellular or Wi-Fi 7 radios operate on sensitive low-band frequencies, SMC power limits the inductive bridge duty cycle to suppress harmonic interference into antennas.

---
"""

def update_book():
    content = BOOK_PATH.read_text(encoding="utf-8")
    
    # 1. Update Table of Contents
    toc_old = "- [Part XXVII: Architectural Glossary & Mathematical Notation Index](#part-xxvii-architectural-glossary--mathematical-notation-index)"
    toc_new = """- [Part XXVII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines](#part-xxvii-apple-video-decoder-avd-video-encoder-2-ave2--appleproreshw-codec-engines)
- [Part XXVIII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence](#part-xxviii-multi-touch-processor-mtp-leap-haptics--magsafe-wireless-charging-coexistence)
- [Part XXIX: Complete Full-Stack Architectural Glossary & Mathematical Notation Index](#part-xxix-complete-full-stack-architectural-glossary--mathematical-notation-index)"""
    
    if toc_old in content:
        content = content.replace(toc_old, toc_new)
        print("[+] Updated Table of Contents with Parts XXVII, XXVIII, XXIX")
    
    # 2. Insert Parts XXVII and XXVIII before Part XXVII Glossary
    glossary_anchor = "## Part XXVII: Architectural Glossary & Mathematical Notation Index"
    if glossary_anchor in content:
        replacement = part_xxvii + "\n" + part_xxviii + "\n## Part XXIX: Complete Full-Stack Architectural Glossary & Mathematical Notation Index"
        content = content.replace(glossary_anchor, replacement)
        # Also renumber internal section numbers in glossary
        content = content.replace("### 27.1 Architectural Glossary", "### 29.1 Architectural Glossary")
        content = content.replace("### 27.2 Mathematical Formulation", "### 29.2 Mathematical Formulation")
        print("[+] Inserted Parts XXVII and XXVIII, renumbered Glossary to XXIX")

    BOOK_PATH.write_text(content, encoding="utf-8")
    print(f"[+] Book updated: {len(content):,} characters")

if __name__ == "__main__":
    update_book()
