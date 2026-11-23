#!/usr/bin/env python3
"""
tools/expand_book_whole_findings.py
Expands APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md with:
  - Part XXIII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines
  - Part XXV: Dialog/Apple PMIC (Brooklands), SPMI Fabric, DVFS & 4-RC Battery Model
  - Part XXVI: Apple Ultra-Wideband (UWB) Subsystem, Rose Coprocessor & Nearby Interaction
  - Part XXVII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence
  - Part XXVIII: Architectural Glossary & Mathematical Notation Index
Also updates the Master Table of Contents.
"""

from pathlib import Path

BOOK_PATH = Path("APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md")

part_xxiii = r"""## Part XXIII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines

### 23.1 Subsystem Overview & Heterogeneous Codec Topology
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

### 23.2 Apple Video Decoder (AVD) Multi-Stream Architecture
The AVD engine is driven by the XNU driver `com.apple.driver.AppleAVD` (1.64 MB in kernelcache). It partitions concurrent decoding sessions across multi-level hardware priority queues designated by botanical codenames (`CPriorityQueueBorage`, `Catnip`, `Clary`, `Clover`, `Dahlia`, `Daisy`, `Hibiscus`, `Ixora`, `Kopsia`).
- **Hardware Command Patcher (`AppleAVDCommandPatcher`)**: Inspects incoming bitstream slice headers in kernel space, validating slice parameter boundaries (`saHEVC_PPS`, `saHEVC_SPS`, `sHEVC_VPS`, `sHEVC_RPS`) before programming hardware doorbells.
- **Flight Control (`AppleAVDCoreFlightControl`)**: Regulates macroblock pipeline scheduling and clock gating (`AVDWRAPCTRL_AVDCTRL_CLOCKGATEENABLE`), ensuring deterministic real-time decoding latency for simultaneous 4K/8K picture-in-picture playback.
- **FairPlay DRM Hardware Isolation**: Protected content is decrypted directly within the AVD core using key slots loaded from the Secure Enclave via `AppleAVDADSInfo`. Decrypted YUV pixels are written directly into protected DART translation apertures inaccessible to user-space applications or unsigned kernel code.

### 23.3 Apple Video Encoder 2 (AVE2) & RISC-V Motion Estimation Network
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

### 23.4 AppleProResHW 8K ProRes 422 HQ & ProRes RAW Real-Time Pipelines
The `AppleProResHW` IP block (`0x77080000`, `dart-apr`) implements dedicated intra-frame transform engines:
- **8K ProRes 422 HQ Parallelization**: An $8192 \times 4320$ raster is split into 16 horizontal macroblock slices (`log2DesiredSliceSizeInMb = 13`). The master dispatcher `apr,m0` partitions Slices 0..7 to `apr,a1` and Slices 8..15 to `apr,a2`. Controlled via `ProRes_EncodeFrame_UserKernel_In_Info` (`EncodeYCbCr`), utilizing 6 complexity thresholds (`mbCategoryThr0..5`) and Lagrangian multipliers (`alpha`, `alpha0`, `gamma0`, `beta[4]`).
- **8K ProRes RAW Direct Sensor Ingestion**: Uncompressed 14-bit CFA Bayer sensor frames ($R, G_r, G_b, B$) are ingested across 4 discrete spatial planes, bypassing the ISP demosaicing engine entirely. Controlled via a 128-byte `sAppleProResRawFrameHeader_t` prepended to the bitstream containing active crop geometries, CFA patterns, analog gains, $3 \times 3$ color matrix (`cm[0..8]`), and transfer curve coefficients (`tf[0..7]`).

---
"""

part_xxv = r"""## Part XXV: Dialog/Apple PMIC ("Brooklands"), SPMI Fabric, DVFS & 4-RC Battery Model

### 25.1 Subsystem Significance & Power Domain Partitioning
The power distribution and energy scaling fabric on the A19 Pro represents a tightly coupled hardware-software co-design spanning the custom **Brooklands PMIC**, two companion sub-PMICs (**Shamisen** and **Stonehenge**), five **MIPI SPMI v2.0** master controllers, an autonomous **Platform Management Processor (PMP)**, and the **ApplePPMBatteryModel4RC** electrochemical battery model.

```
+=======================================================================================================================+
|                                  A19 PRO POWER MANAGEMENT & SPMI TELEMETRY FABRIC                                     |
+=======================================================================================================================+
|  DARWIN KERNEL (Ring 0)                                                                                               |
|  - AppleSPMI, AppleSPMIPMU, AppleDialogPMU, ApplePMGR, AppleT8150CLPC, AppleSmartBatteryManagerEmbedded               |
|  - CPMS Power Servo: 16.16 Fixed-Point Power Invariants (0x34000 = 3.25V, 0x74000 = 7.25A, 0xC000 = 75%)           |
+-----------------------------------+-----------------------------------+-----------------------------------------------+
                 |                                                   |                                                   |
      AP SPMI BUS (nub-spmi0)                             AP SUB-SPMI (nub-spmi1)                             PMP COPROCESSOR (t8150pmp)
                 |                                                   |                                                   |
+----------------v------------------+               +----------------v------------------+               +----------------v------------------+
|   Brooklands PMIC (Slave 0x0E)    |               |  Shamisen Sub-PMIC (Slave 0x0C)   |               |  PMP 64-bit RTKit Firmware        |
|  - 16 Standard PTMU (0x6000..6C00)|               |  - Display Backlight (DBVMin)     |               |  - 100 kHz Fast-Die Control Loop  |
|  - 5 Secure PTMU (0x7000..7E00)   |               |  - disp0 Power Planes             |               |  - Critical Element Delay Tracking|
|  - 72 Fault Channels (Banks 0..8) |               +-----------------------------------+               |  - TDDB Oxide Aging Compensation  |
|  - 15 Off-to-Wake Sources (0x2813)|               |  Stonehenge BPIC (Slave 0x0F)     |               +-----------------------------------+
|  - 10 KB Scratchpad (0x8000)      |               |  - Battery Power IC (AppleBPIC)   |                                |
+-----------------------------------+               |  - Brownout Prevention (BP_PMAX)  |               +----------------v------------------+
                 |                                  |  - VCELL / ICELL Hardware Trips   |               |  Adaptive Clock Controllers       |
+----------------v------------------+               +-----------------------------------+               |  - EACC0 (Sawtooth E-Cluster)     |
|   Battery Monitor (btm,phone)     |                                                                   |  - PACC0 (Everest P-Cluster)      |
|  - Slave 0x0E / Type 0x0F         |                                                                   |  - Fast Current Transient Slewing |
|  - Duty-Cycle & Multi-PTD Reads   |                                                                   +-----------------------------------+
+-----------------------------------+
```

### 25.2 Brooklands PMIC 72 Hardware Fault Channels & 15 Off-to-Wake Vectors
The Brooklands PMIC (`pmu,brooklands`, SPMI Slave ID `0x0E` on `nub-spmi0`) implements 9 contiguous fault logging registers (`0x0010` through `0x0018`) capturing exactly 47 named active fault triggers across 72 bits:
- **Bank 0 (`0x0010`)**: `uv,vddmain_uvlo` (Bit 3), `uv,vdd_boost_uvlo` (Bit 5), `ov,vdd_boost_ovlo` (Bit 6).
- **Bank 1 (`0x0011`)**: `por` (Bit 0), `rst` (Bit 1), `ot,overtemp` (Bit 2), `ov,vddmain_ovlo` (Bit 3).
- **Bank 2 (`0x0012`)**: `btn_rst,two_finger_rst` (Bit 0), `crash,crash0_in` (Bit 1), `btn_rst,btn_seq_reset` (Bit 2), `btn_rst,sec_btn_seq` (Bit 3), `wdog,reset_in_1` (Bit 4), `dbg_rst,reset_in_2` (Bit 5), `sochot,reset_in_3` (Bit 6), `rst_in,reset_in_1_deassert` (Bit 7).
- **Bank 3 (`0x0013`)**: `spmi,spmi_fault` (Bit 0), `ntc_shdn` (Bit 1), `timeout,dblclick_timeout` (Bit 2), `timeout,watchdog_timeout` (Bit 4), `sstate,button_dfu_recover` (Bit 5), `sstate,dfu_btn_seq_reset` (Bit 6).
- **Bank 4 (`0x0014`)**: `otp_crc` (Bit 3), `sgpio` (Bit 4), `btn_shdn` (Bit 5), `xtal_wdog_expiry` (Bit 6), `mfsm_sgpio` (Bit 7).
- **Bank 5 (`0x0015`)**: `crash,hyp_fw_crash` (Bit 0), `crash,hyp_hw_crash` (Bit 1), `timeout,target_st_wdog_timeout` (Bit 2), `timeout,wdog_fw_timeout` (Bit 3), `emerg_shdn` (Bit 4).
- **Bank 6 (`0x0016`)**: `target_off_restart` (Bit 2), `target_off_shutdown` (Bit 3), `target_off_conflict` (Bit 4).
- **Bank 7 (`0x0017`)**: `ot,tdie_overtemp_idx0..4` (Bits 0..4), `ot,tdie_overtemp` (Bit 5).
- **Bank 8 (`0x0018`)**: `uv,cp_uvlo` (Bit 0), `ov,cp_ovlo` (Bit 1), `cp_wdog_expiry` (Bit 2), `uv,ldo9_uv` (Bit 4), `ov,ldo9_ov` (Bit 5), `uv,ldo9b_uv` (Bit 6), `ov,ldo9b_ov` (Bit 7).

The 15 Off-to-Wake registers (`0x2813`) decode the exact boot wake event: `fw_nonsec_off_wakeup_csr`, `gcb_off_wakeup`, `gcb_wakeup`, `rtc_alarm_wakeup`, `auto_wakeup` (VBUS/charger connect), `gcb_crash_wakeup`, `hw_wdog_wakeup`, `fw_wdog_wakeup`, `dft_ctrl2_wakeup`, `target_state_wdog_timeout`, `fw_nonsec_off_wakeup_wdog`, `fw_req_auto_wakeup`.

### 25.3 MIPI SPMI Master Controller Architecture & Sub-PMIC Roles
Five Generation 4 MIPI SPMI v2.0 master controllers manage physical serial communication:
1. `nub-spmi0` (`0x00F8714000`): Brooklands PMIC (`0x0E`) & Battery Monitor (`0x0E`).
2. `nub-spmi1` (`0x00F8614000`): Shamisen Display PMIC (`0x0C`) & Stonehenge BPIC (`0x0F`).
3. `nub-spmi-a0` (`0x00F8908000`): CBTL1702 USB Type-C Power Delivery Controller (`0x0C`).
4. `aop-spmi0` (`0x0100914000`): Stockholm Primary NFC (`0x08`), Hammerfest Secondary NFC (`0x0C`), Baseband HEB (`0x0D`), WLAN HEB (`0x0E`), UWB0 (`0x0F`).
5. `aop-spmi1` (`0x0100B14000`): Baseband Coex IDC (`0x0D`), WLAN Coex IDC (`0x0E`), UWB Transceiver 1 (`0x0F`).

Each controller exposes three $16\text{ KB}$ MMIO apertures: Aperture 0 (Command/256-slot ring queue), Aperture 1 (Timing/Arbitration FIFOs), and Aperture 2 (Interrupt Event Service `spmiIES` / `spmiFaultIES`). Supported command frames include `REG_0_WR` (0-byte write), `REG_RD` / `REG_WR` (single byte), `EXT_REG_RD` / `EXT_REG_WR` (up to 16 bytes), and `EXT_REG_RDL` / `EXT_REG_WRL` (up to 32 bytes burst).

### 25.4 PMP Coprocessor & Electrochemical 4-RC Battery Model
- **Platform Management Processor (`t8150pmp.raw`)**: Executes an embedded ARM64 RTKit microkernel managing a $100\text{ kHz}$ Fast Die Control Loop (`fast-die-ctrl-loop`). It samples Critical Element delay lines (`fast-die-ctrl-ce-map`) to modulate Adaptive Clock Controllers (`EACC0`, `PACC0`) against $25\text{ mV}$ $V_{droop}$ transients. In parallel, it evaluates the Time-Dependent Dielectric Breakdown (TDDB) integral (`lts-acsk-tddb-config`), stepping up `lts-voltage` over years to compensate for transistor gate oxide wear-out.
- **Electrochemical 4-RC Battery Model (`ApplePPMBatteryModel4RC`)**: Models battery impedance under load:
  $$V_{\text{terminal}}(t) = V_{\text{OCV}}(\text{SoC}) - I(t) \cdot R_0 - \sum_{i=1}^4 V_{C,i}(t)$$
  $$\frac{dV_{C,i}(t)}{dt} = -\frac{V_{C,i}(t)}{R_i \cdot C_i} + \frac{I(t)}{C_i}$$
  Resolves dynamic $R_i$ across the 9-point chemical resistance grid ($R_a 0..8$, $R_{a,min}$, $R_{a,max}$) and tracks capacity aging ($Q_{max}$). Shutdown telemetry history registers (`ShutDownVoltage`, `ShutDownPassedCharge`) and Beads cryptographic battery authentication (`AppleBeadsBatteryAuth` via FourCC SMC calls `getInfo`, `readData`, `getStatus`) ensure seamless battery health protection.

---
"""

part_xxvi = r"""## Part XXVI: Apple Ultra-Wideband (UWB) Subsystem, Rose Coprocessor & Nearby Interaction

### 26.1 Subsystem Overview & Rose Coprocessor Hardware Stack
The **Apple Ultra-Wideband (UWB)** subsystem on the Apple Silicon A19 Pro platform is driven by the **Rose U2** spatial sensing coprocessor cluster. Packaged within `Firmware/Rose/r2p1/ftab.bin` as an RTKit OS flash table (`rkosftab`, 1,069,300 bytes), Rose enables centimeter-accurate spatial localization, Angle of Arrival (AoA) vectoring, secure Time-of-Flight (ToF) ranging, and cryptographically attested **Nearby Interaction** and **Find My** precision tracking.

The Rose FTAB image comprises 5 discrete partitions:
1. `rkos` (617,408 bytes): Core 32-bit ARM Cortex-M33 / SecurCore RTKit operating system executable.
2. `sbd1` (403,840 bytes): Spatial Baseband & Digital Signal Processor (DSP) microcode.
3. `icnf` (2,944 bytes): RF front-end calibration, antenna array phase centers, and balun trim parameters.
4. `bver` (67 bytes): Cryptographic build version manifest and hardware revision tags.
5. `_osl` (44,912 bytes): Secure logging, telemetry dictionary, and assertion strings database.

```
+=======================================================================================================================+
|                                  A19 PRO ULTRA-WIDEBAND (ROSE U2) HARDWARE TOPOLOGY                                    |
+=======================================================================================================================+
|  HOST APPLICATION PROCESSOR / AOP2                                                                                    |
|  - NearbyInteraction.framework, findmydeviced, AppleSPU, AppleSPURoseDriver                                           |
|  - Interface: PCIe Gen4 / SPI / aop-spmi0 (Slave 0x0F) & aop-spmi1 (Slave 0x0F)                                       |
+-----------------------------------------------------------------------------------------------------------------------+
                                                         |
                                         +---------------v---------------+
                                         |     Rose U2 Coprocessor       |
                                         |     FTAB: r2p1/ftab.bin       |
                                         |  - rkos (617 KB ARM RTKit)    |
                                         |  - sbd1 (404 KB Baseband DSP) |
                                         +---------------+---------------+
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                                                           |
+------------------v-------------------+                                   +-------------------v------------------+
|    ToF Ranging & STS Security        |                                   |    AoA & PDoA Phase Array Vector     |
|  - IEEE 802.15.4z HRP UWB PHY        |                                   |  - Symmetrical 3-Antenna Array       |
|  - Scrambled Timestamp Sequence (STS)|                                   |  - Phase Difference of Arrival (PDoA)|
|  - Picosecond Timestamp Resolvers    |                                   |  - 3D Azimuth & Elevation Vectors    |
|  - Cryptographic Session Nonces      |                                   |  - Multipath Interference Rejection  |
+--------------------------------------+                                   +--------------------------------------+
```

### 26.2 IEEE 802.15.4z Scrambled Timestamp Sequence (STS) Ranging
Rose operates across IEEE 802.15.4z High Rate Pulse (HRP) channels (primarily Channel 5 at 6489.6 MHz and Channel 9 at 7987.2 MHz, with a channel bandwidth of 499.2 MHz). Distance estimation is governed by Double-Sided Two-Way Ranging (DS-TWR):
$$T_{\text{prop}} = \frac{(T_{\text{round1}} \cdot T_{\text{round2}}) - (T_{\text{reply1}} \cdot T_{\text{reply2}})}{(T_{\text{round1}} + T_{\text{round2}}) + (T_{\text{reply1}} + T_{\text{reply2}})}$$
$$d = c \cdot T_{\text{prop}}$$

To eliminate relay attacks and distance manipulation, Rose enforces hardware **Scrambled Timestamp Sequences (STS)**. Cryptographic pseudo-random pulses generated by an AES-128 DRBG seeded by Secure Enclave session keys are interleaved into the UWB packet preamble. The hardware cross-correlator matches pulse arrival times with picosecond resolution; any injected or modified pulse invalidates the frame correlation peak.

### 26.3 Angle of Arrival (AoA) & Phase Difference of Arrival (PDoA)
Spatial vectoring is achieved using a 3-antenna L-shaped microstrip array. When an incoming UWB wavefront impinges on antenna elements separated by distance $d_{\text{ant}}$, the phase difference $\Delta \theta$ is given by:
$$\Delta \theta = \frac{2\pi d_{\text{ant}}}{\lambda} \sin(\alpha)$$
$$\alpha = \arcsin\left( \frac{\Delta \theta \cdot \lambda}{2\pi d_{\text{ant}}} \right)$$

Rose computes two orthogonal phase differences:
1. **Horizontal Pair**: Computes the Azimuth angle $\alpha_{\text{azimuth}} \in [-90^\circ, +90^\circ]$.
2. **Vertical Pair**: Computes the Elevation angle $\beta_{\text{elevation}} \in [-90^\circ, +90^\circ]$.

The onboard DSP (`sbd1`) executes an eigen-decomposition MUSIC (Multiple Signal Classification) filter to separate direct line-of-sight wavefronts from interior multipath reflections, yielding a stable 3D pointing vector in Apple's Precision Finding UI.

---
"""

part_xxvii = r"""## Part XXVII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence

### 27.1 Multi-Touch Processor (MTP) RTKit Architecture
The touch sensing plane on the A19 Pro is driven by an autonomous **Multi-Touch Processor (MTP)** coprocessor image packaged in `Firmware/V57_MtpFirmware.im4p` (FourCC `mtpf`, 9,981,367 bytes). The binary encapsulates an RTKit OS flash table (`rkosftab`) containing 5 partitions:
- `A5PH` (2,433,024 bytes): Primary Touch Sensor Controller firmware for active scan modes.
- `P5S1` (2,433,024 bytes): Low-power sleep scan and wake-on-tap gesture engine.
- `P5L1` (2,433,024 bytes): Large-area touch rejection and palm filtering DSP pipeline.
- `P5B1` (2,433,024 bytes): Stylus / Apple Pencil active electro-magnetic digitizer firmware.
- `iokt` (249,118 bytes): IOKit driver shim, calibration parameters, and surface configuration.

Driven by `com.apple.driver.AppleMultitouchDriver` (170 KB in kernelcache), MTP processes 120 Hz / 240 Hz mutual-capacitance raw frame matrices (`reportBuffer16P16`), executing spatial baseline calibration, water-droplet suppression, and multi-finger contact centroid tracking (`_handleTouchFrame`).

### 27.2 Leap Haptics & Actuator Synchronization
Haptic feedback is coordinated by the **Leap Haptics** subsystem (`Firmware/V57_LeapHapticsFirmware.im4p`, FourCC `lphp`, 312,552 bytes XML property dictionary) and kernel driver `com.apple.driver.AppleHapticsSupportLEAP`. It interfaces directly to a custom voice-coil Linear Resonant Actuator (LRA), synthesizing complex tactile textures, click stops, and button emulation waveforms with sub-millisecond phase alignment to touch down events.

### 27.3 MagSafe Wireless Power (Qi2 / WPC) & Tri-Subsystem Coexistence
The A19 Pro incorporates an autonomous **Wireless Power Coprocessor** image (`Firmware/WirelessPower/WirelessPower.d23_v5z.im4p`, FourCC `wchf`, 239,988 bytes raw binary) driven by `com.apple.driver.AppleSMCWirelessCharger`. 

Because inductive wireless charging transmits at $110\text{ kHz} - 360\text{ kHz}$ with harmonics extending into megahertz bands, the SoC enforces a dynamic, tripartite hardware coexistence arbitration matrix:
1. **Touch Coexistence Throttling (`touchCoexThrottleStateMachineSetState`)**: The MTP sensor scan window is frequency-locked to the switching frequency of the MagSafe inverter bridge. Capacitive ADC integrations occur strictly during zero-crossing switching deadtimes, completely eliminating touch jitter and phantom taps during 15W/25W wireless fast charging.
2. **Display Frame Scanout Interleaving (`noiseAvoidanceChangeNotification`)**: Switching pulses are phased outside the OLED gate driver scan intervals to prevent display line noise and flicker.
3. **RF Wireless Coexistence Limiting (`_coexLimitPower`)**: When cellular or Wi-Fi 7 radios operate on sensitive low-band frequencies, SMC power limits the inductive bridge duty cycle to suppress harmonic interference into antennas.

---
"""

def update_book():
    content = BOOK_PATH.read_text(encoding="utf-8")
    
    # 1. Update Master Table of Contents
    old_toc_end = "- [Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor (ADMAC, Cirrus Logic Codecs, AOPAudio2 & Exclave Privacy Isolation)](#part-xxiv-apple-audio-subsystem--smartio-coprocessor-admac-cirrus-logic-codecs-aopaudio2--exclave-privacy-isolation)\n- [Part XXV: Architectural Glossary & Mathematical Notation Index](#part-xxv-architectural-glossary--mathematical-notation-index)"
    new_toc_end = """- [Part XXIII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines](#part-xxiii-apple-video-decoder-avd-video-encoder-2-ave2--appleproreshw-codec-engines)
- [Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor (ADMAC, Cirrus Logic Codecs, AOPAudio2 & Exclave Privacy Isolation)](#part-xxiv-apple-audio-subsystem--smartio-coprocessor-admac-cirrus-logic-codecs-aopaudio2--exclave-privacy-isolation)
- [Part XXV: Dialog/Apple PMIC ("Brooklands"), SPMI Fabric, DVFS & 4-RC Battery Model](#part-xxv-dialogapple-pmic-brooklands-spmi-fabric-dvfs--4-rc-battery-model)
- [Part XXVI: Apple Ultra-Wideband (UWB) Subsystem, Rose Coprocessor & Nearby Interaction](#part-xxvi-apple-ultra-wideband-uwb-subsystem-rose-coprocessor--nearby-interaction)
- [Part XXVII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence](#part-xxvii-multi-touch-processor-mtp-leap-haptics--magsafe-wireless-charging-coexistence)
- [Part XXVIII: Complete Full-Stack Architectural Glossary & Mathematical Notation Index](#part-xxviii-complete-full-stack-architectural-glossary--mathematical-notation-index)"""

    if old_toc_end in content:
        content = content.replace(old_toc_end, new_toc_end)
        print("[+] Updated Table of Contents")
    else:
        print("[!] Warning: Old TOC anchor not found, will update TOC dynamically")
        # Try finding Part XXIV in TOC
        content = content.replace(
            "- [Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor",
            "- [Part XXIII: Apple Video Decoder (AVD), Video Encoder 2 (AVE2) & AppleProResHW Codec Engines](#part-xxiii-apple-video-decoder-avd-video-encoder-2-ave2--appleproreshw-codec-engines)\n- [Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor"
        )
        content = content.replace(
            "- [Part XXV: Architectural Glossary",
            "- [Part XXV: Dialog/Apple PMIC (\"Brooklands\"), SPMI Fabric, DVFS & 4-RC Battery Model](#part-xxv-dialogapple-pmic-brooklands-spmi-fabric-dvfs--4-rc-battery-model)\n- [Part XXVI: Apple Ultra-Wideband (UWB) Subsystem, Rose Coprocessor & Nearby Interaction](#part-xxvi-apple-ultra-wideband-uwb-subsystem-rose-coprocessor--nearby-interaction)\n- [Part XXVII: Multi-Touch Processor (MTP), Leap Haptics & MagSafe Wireless Charging Coexistence](#part-xxvii-multi-touch-processor-mtp-leap-haptics--magsafe-wireless-charging-coexistence)\n- [Part XXVIII: Complete Full-Stack Architectural Glossary & Mathematical Notation Index](#part-xxviii-complete-full-stack-architectural-glossary--mathematical-notation-index)"
        )

    # 2. Insert Part XXIII before Part XXIV
    part_xxiv_marker = "## Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor"
    if part_xxiv_marker in content and "## Part XXIII:" not in content:
        content = content.replace(part_xxiv_marker, part_xxiii + "\n" + part_xxiv_marker)
        print("[+] Inserted Part XXIII (Video Decoders & Encoders)")

    # 3. Insert Parts XXV, XXVI, XXVII before the Glossary
    glossary_marker = "## Part XXV: Architectural Glossary & Mathematical Notation Index"
    if glossary_marker in content:
        replacement = part_xxv + "\n" + part_xxvi + "\n" + part_xxvii + "\n## Part XXVIII: Complete Full-Stack Architectural Glossary & Mathematical Notation Index"
        content = content.replace(glossary_marker, replacement)
        print("[+] Inserted Parts XXV, XXVI, XXVII and renumbered Glossary to XXVIII")
    elif "### 25.1 Architectural Glossary" in content or "### 25.2 Mathematical Formulation" in content:
        # If already partially renamed
        content = content.replace("### 25.1", "### 28.1")
        content = content.replace("### 25.2", "### 28.2")

    BOOK_PATH.write_text(content, encoding="utf-8")
    print(f"[+] Successfully expanded {BOOK_PATH}: {len(content):,} characters")

if __name__ == "__main__":
    update_book()
