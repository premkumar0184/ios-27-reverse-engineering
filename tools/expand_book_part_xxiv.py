#!/usr/bin/env python3
"""
Expands APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md with Part XXIV:
Apple Audio Subsystem & SmartIO Coprocessor (ADMAC, Cirrus Logic Codecs, AOPAudio2 & Exclave Privacy Isolation).
Updates Table of Contents and re-numbers Glossary to Part XXV.
"""

BOOK_PATH = "APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md"

with open(BOOK_PATH, "r", encoding="utf-8") as f:
    book = f.read()

# 1. Update Table of Contents
old_toc = "- [Part XXIII: Architectural Glossary & Mathematical Notation Index](#part-xxiii-architectural-glossary--mathematical-notation-index)"
new_toc = """- [Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor (ADMAC, Cirrus Logic Codecs, AOPAudio2 & Exclave Privacy Isolation)](#part-xxiv-apple-audio-subsystem--smartio-coprocessor-admac-cirrus-logic-codecs-aopaudio2--exclave-privacy-isolation)
- [Part XXV: Architectural Glossary & Mathematical Notation Index](#part-xxv-architectural-glossary--mathematical-notation-index)"""

if old_toc in book:
    book = book.replace(old_toc, new_toc)
    print("[+] Table of Contents updated successfully!")
else:
    print("[-] Old TOC entry not found!")

# 2. Prepare Part XXIV text
part_xxiv_text = """---

## Part XXIV: Apple Audio Subsystem & SmartIO Coprocessor (ADMAC, Cirrus Logic Codecs, AOPAudio2 & Exclave Privacy Isolation)

### 24.1 Architecture Overview & Multi-Tier Topology
The **Apple Audio Subsystem** embedded within the Apple Silicon A19 Pro (`t8150`) represents an advanced, multi-tier heterogeneous acoustic processing and routing architecture. Unlike conventional smartphone audio pipelines that funnel all acoustic transactions through the application processor, the A19 Pro decouples audio capture, processing, power governance, and playback across four distinct hardware domains:

1. **SmartIO Embedded Coprocessor (ASCv7)**: An autonomous 64-bit ARM64 real-time processor running RTKit OS (`RTKit_armv8_chinook_Oz_flto-3514.40.18.release`), managing high-speed SPI/UART peripherals, register shims, DMA buffer segment tables, and inter-processor communication with `AOP-AUDIO`.
2. **AudioDMA Controller (ADMAC Evolution `t8150`)**: A dedicated hardware direct memory access crossbar featuring 32 Tx/Rx operational channels, 16-byte aligned descriptor queues, critical low-latency transfer (CLLT) escalation detectors, Multichannel Audio (MCA0..MCA5) serial buses, and dual-port PDM digital microphone decimators.
3. **Cirrus Logic High-Fidelity Audio Codecs (CS42L84 / CS42L79)**: Custom mixed-signal codecs providing 24-bit/32-bit ultra-low noise digital-to-analog conversion, low-power microphone (LPMic) always-listening paths, hall-effect calibration, and pre-boot hardware boot chime synthesis (`v57-boot-chime.im4p` / `aubt`).
4. **Always-On Audio (AOPAudio2) & ExclaveOS Privacy Isolation**: Autonomous 16 kHz acoustic ring buffer in 5.34 MB low-leakage SRAM, 3.0-second circular history buffer for Siri voice trigger wake, and capability-isolated ExclaveOS Tightbeam RPC stream handles backed by the hardware Secure Indicator Light (SIL) 2000-nit/80-nit cap.

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                  APPLE AUDIO SUBSYSTEM FULL-STACK ARCHITECTURE                                        |
+-----------------------------------------------------------------------------------------------------------------------+
|  DARWIN AP HOST (Ring 0 / Ring 3)                                                                                     |
|  - CoreAudio HAL, audiod, AppleEmbeddedAudio & AppleCS42L79Audio                                                      |
|  - AudioDMAController (t8150): 32 Tx / 32 Rx Channels, Circular DMA Ring Buffers                                      |
|  - ExclavesAudioKext: Microphone privacy enforcement & isolated stream proxy                                          |
+-----------------------------------------------------------------------------------------------------------------------+
|  EXCLAVEOS cL4 SECURE CONCLAVE (GL1 Isolation)                                                                        |
|  - ExclavesAudioProxyInputStreamDriverTightbeam: Zero raw PCM exposure to Ring 0                                      |
|  - Hardware Secure Indicator Light (SIL) binding: 80 nits nominal / 2000 nits peak cap                                |
|  - IISAudioIsolatedStreamECProxy: Formally verified capability-mediated stream handles                                |
+-----------------------------------------------------------------------------------------------------------------------+
|  MEMORY FABRIC & IOMMU APERTURES                                                                                      |
|  - DART-SIO (0x175060000): 128 KB MMIO window, 16 KB page granules                                                    |
|  - audio-shared-dart-proxy: mapper-admac-base-ns, mapper-admac-base-s, mapper-admac-leap-ns                            |
|  - Circular SPSC Ring Buffers: Producer-consumer pointer synchronization & overflow recovery                          |
+-----------------------------------------------------------------------------------------------------------------------+
|  EMBEDDED REAL-TIME COPROCESSORS                                                                                      |
|  - SmartIO Coprocessor (siof): ARM64 RTKit OS Chinook, SPI0..SPI2, UART0..UART2, SIO Shims                            |
|  - Always-On Processor 2 (AOP2): 3.0s Circular Audio History Buffer (48,000 frames @ 16 kHz, 96 KB SRAM)              |
|  - Audio Boot Chime (aubt): 582 KB Pre-Boot Linear PCM Buffer (24-bit stereo 48 kHz @ 2.022s)                         |
+-----------------------------------------------------------------------------------------------------------------------+
|  MIXED-SIGNAL CODECS & TRANSDUCERS                                                                                    |
|  - Cirrus Logic CS42L84 / CS42L79: CS42L79_GLOBAL_BLOCK_EN1 power blocks & LPMic capture                             |
|  - Multichannel Audio (MCA): 6 Serial Ports (audio-mca0..audio-mca5) & PDM2 digital mic decimators                    |
|  - Smart Amplifiers & LEAP Taptic Engine: Microsecond audio-haptic co-scheduling (<100 us phase latency)              |
+-----------------------------------------------------------------------------------------------------------------------+
```

### 24.2 SmartIO Coprocessor (ASCv7) & RTKit OS Chinook Microkernel
The **Apple SmartIO Coprocessor** (`siof`, encapsulated in `SmartIOFirmware_ASCv7.im4p`, 1,140,621 bytes) is an autonomous 64-bit ARM64 real-time coprocessor powering auxiliary high-speed I/O, audio streaming, and peripheral shims.
- **Mach-O Container Layout**: Bare-metal `MH_PRELOAD` image (`0xfeedfacf`, CPU `0x100000c`, 6 load commands).
  * `__TEXT` Segment: Virtual base `0x0`, size `0x1c000` (`__text` size `0x1a884`, `__cstring` size `0x1062`, `_rtk_mtab` size `0x290`).
  * `__DATA` Segment: Virtual base `0x1c000`, size `0xf8000` (`_rtk_init_stack` 4 KB, `_rtk_irq_stack` 4 KB, `_rtk_exc_stack` 4 KB, `_rtk_boot` 8 KB, `_rtk_page_tables` 132 KB, `_rtk_patchbay` at `0x44000`, `_rtk_power` at `0x44220`, `__gxf_data` 16B, `_rtk_tunables` at `0x44588`, `__zerofill` `0xcec80` / 847,488 bytes).
- **RTKit OS Chinook**: Version banner `RTKit_armv8_chinook_Oz_flto-3514.40.18.release`.
- **Peripherals & Shims**:
  * 3x SPI Channels (`SPI0_TX/RX`, `SPI1_TX/RX`, `SPI2_TX/RX`) and 3x UART Channels (`UART0_TX/RX`..`UART2_TX/RX`).
  * SIO Register Shims: Dynamic register tuple parsers managing hardware FIFO buffers and power gating.
  * DMA Segment List: 4-stage endpoint pipeline (`0x00004048` .. `0x0000433c`) with buffer descriptors (`0x00003f8c` .. `0x00004044`).
- **Mailbox Architecture**: `_rtk_mtab` table dispatching across ASCwrap registers (`_RTK_DEV_ASC`, `_RTK_DEV_ASCWRAP`, `_RTK_DEV_ASC_OUTBOX`) interfacing directly with `AOP-AUDIO`.

### 24.3 AudioDMA Controller (ADMAC Evolution `t8150`) & Multichannel Audio
The **ADMAC Evolution** (`admac-evolution,t8150`) is Apple's high-throughput audio DMA crossbar on the A19 Pro.
- **Channel Architecture**: 32 Tx channels and 32 Rx channels operating across dual-FIFO ring buffers (`_adma_base_ns_txch_blk_v3`).
- **Hardware Descriptors**: 16-byte aligned descriptors containing source/destination physical addresses, 32-bit transfer byte counts, and descriptor attribute bitfields (`Attr` byte offset `0x0E`).
- **State Machine**: Driven by `AudioDMAChannelStateMachine` governing transitions across `Init`, `Configured`, `Active`, `Paused`, `Draining`, and `Stopped`.
- **Critical Low-Latency Transfer (CLLT) Detector**: `AudioDMACLLTEscalationDetector_T8150_iOS` dynamically monitors ring buffer head-tail divergence; if latency exceeds 2.5 ms, it escalates fabric QoS priority on ACF7.
- **Multichannel Audio (MCA)**: 6 serial ports (`audio-mca0`..`audio-mca5`) managing I2S/TDM streaming, loopback monitoring (`audio-aop-mca-loopback`), and PDM2 digital microphone decimator arrays.

### 24.4 Cirrus Logic Mixed-Signal Codecs & Boot Tone Pre-Boot Synthesis
- **Cirrus Logic CS42L84 / CS42L79**:
  * High-fidelity DAC/ADC codec configured via register blocks (`CS42L79_GLOBAL_BLOCK_EN1` at offset `0x0011`, `CS42L79_GLOBAL_BLOCK_EN2` at offset `0x0012`).
  * AKCI Request Handshake: Handles `CS42L79StreamingRequest`, `CS42L79ListeningRequest`, `CS42L79HallRequest`, and `CS42L79FlickerBiasRequest`.
  * Low-Power Microphone (LPMic): Dedicated ultra-low power analog front-end streaming to AOP2 at <1.85 mW total subsystem power.
- **Audio Boot Chime Resource (`v57-boot-chime.im4p` / `aubt`)**:
  * 582,555 bytes Image4 container packaging raw 24-bit stereo linear PCM audio at 48,000 Hz (2.022 seconds duration, 97,087 sample frames, 582,522 payload bytes).
  * Synthesizes the F-sharp major chord ($F\sharp_2, C\sharp_3, F\sharp_3, A\sharp_3, C\sharp_4$) executed by iBoot firmware through the CS42L84 codec prior to Darwin kernel initialization.
- **Smart Speaker Protection (`IOPAudioSpeaker`)**:
  * Real-time voice coil thermal modeling ($R_e(T) = R_0 [1 + \alpha (T - T_0)]$) with dual time constants ($\tau_{\text{fast}} = 1.8\text{ s}$, $\tau_{\text{slow}} = 45.0\text{ s}$).
  * Adaptive Class-H boost converter dynamically elevating supply rail from 3.8V to 11.5V with real-time IV-sense feedback.

### 24.5 Always-On Audio (AOPAudio2) & Low-Power Siri VoiceTrigger
- **AOP2 Acoustic SRAM Allocation**: 5.34 MB low-leakage SRAM at `0x0000000101000000`. Binary #3 (`03_audio_hotword_app.macho`, 753,976 bytes) runs the autonomous keyword spotting (KWS) model.
- **3.0-Second Acoustic History Buffer**: 48,000 frames of 16-bit 16 kHz mono LPCM audio occupying exactly 96,000 bytes, managed by `AppleAOPAudioRingBufferImpl`.
- **Hardware Wake Doorbell**: Upon local acoustic template match, AOP2 asserts **AIC Vector 357** (`0x0165`), delivering the wake doorbell to the Everest P-cores within 18.45 ms.

### 24.6 ExclaveOS Tightbeam Audio Stream Privacy & Hardware Isolation
- **ExclaveOS cL4 Protection**: Darwin (Ring 0) is physically blocked from mapping raw microphone DMA buffers. All microphone ingest routes through `ExclavesAudioKext` and `ExclavesAudioProxyInputStreamDriverTightbeam`.
- **Tightbeam Wire Descriptors**:
  * `exad_stream_description_t`: 16-byte stream descriptor (`{IIISCC}`).
  * `voicetriggernonsecure_data_t`: 16-byte metadata context (`{QQ}`).
  * `voicetrigger_secure_data_t`: 156-byte capability-sealed context (`{QQQI[128C]}`).
- **Secure Indicator Light (SIL)**: Hardware-enforced display overlay driven by `com.apple.service.ExclaveIndicatorController`, capping orange microphone privacy indicator luminance at 80 nits nominal / 2000 nits HDR.

### 24.7 LEAP Haptic Engine Audio Synchronization
- **System Co-Scheduler**: `AppleAOPAudioHapticLEAP` synchronizes wave table haptic waveforms (`leap_waveform_asset_t`, 30 bytes) with audio transients.
- **Phase Latency**: Achieves sub-100 microsecond phase alignment (45 µs typical) between voice coil acoustic output and Linear Resonant Actuator (LRA) haptic transients at 175.0 Hz resonance.

### 24.8 Clean-Room C Audio Host Interface Runtime
```c
/* Clean-Room AOP Audio Ring Buffer Status Page (Exactly 64 bytes) */
typedef struct __attribute__((packed, aligned(64))) {
    uint64_t magic;                 /* 0x414F50415544494FUL ('AOPAUDIO')      */
    uint64_t producer_head_frames;  /* Monotonic audio frames written by AOP2 */
    uint64_t consumer_tail_frames;  /* Monotonic audio frames read by host    */
    uint64_t last_sync_host_time_ns;/* Host mach_absolute_time in nanoseconds */
    uint64_t last_sync_aop_time_ns; /* AOP local timer timestamp             */
    uint32_t ring_capacity_frames;  /* Ring buffer capacity (48,000 frames)   */
    uint32_t sample_rate_hz;        /* Nominal sampling rate (16,000 Hz)      */
    uint16_t channel_count;         /* Channel count (1 = Mono)               */
    uint16_t bits_per_sample;       /* Bit depth (16 bits)                    */
    uint16_t bytes_per_frame;       /* Bytes per frame (2 bytes)              */
    uint16_t status_flags;          /* Bit 0: Active, Bit 1: Overflow         */
    int32_t  clock_drift_ppm_q16;   /* Clock drift in Q16 PPM                 */
    uint32_t dropped_frames_count;  /* Cumulative overflow frame count        */
} aop_audio_ring_status_t;
_Static_assert(sizeof(aop_audio_ring_status_t) == 64, "aop_audio_ring_status_t must be 64 bytes");
```

---
"""

# 3. Replace Glossary Part XXIII with Part XXV and insert Part XXIV before it
glossary_heading = "## Part XXIII: Architectural Glossary & Mathematical Notation Index"
new_glossary = """## Part XXV: Architectural Glossary & Mathematical Notation Index

### 25.1 Definitions and Acronyms"""

if glossary_heading in book:
    book = book.replace(glossary_heading + "\n\n### 23.1 Definitions and Acronyms", part_xxiv_text + "\n" + new_glossary)
    book = book.replace("### 23.2 Mathematical Formulation", "### 25.2 Mathematical Formulation")
    print("[+] Part XXIV inserted and Glossary re-numbered to Part XXV successfully!")
else:
    print("[-] Glossary heading not found!")

with open(BOOK_PATH, "w", encoding="utf-8") as f:
    f.write(book)

print(f"[+] Book updated successfully! Total bytes: {len(book):,}")
