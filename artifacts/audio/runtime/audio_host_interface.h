/**
 * @file audio_host_interface.h
 * @brief Clean-Room C99 Interface Specification for Apple Silicon A19 Pro (t8150)
 *        Always-On Audio (AOPAudio2), VoiceTrigger & ExclaveOS Tightbeam Privacy Isolation
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 *
 * Verified with: gcc -Wall -Wextra -std=c99 -pedantic
 */

#ifndef AUDIO_HOST_INTERFACE_H
#define AUDIO_HOST_INTERFACE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Hardware Memory Maps, Apertures & AIC Interrupt Vectors                */
/* ========================================================================= */

/** @brief AOP2 Low-Leakage Retention SRAM Physical Base (5.34 MB aperture) */
#define AOP2_RETENTION_SRAM_BASE            0x0000000101000000ULL
#define AOP2_RETENTION_SRAM_SIZE            0x0000000000557000ULL /* 5.34 MB (5,599,232 bytes) */

/** @brief AOP2 ASCwrap Mailbox MMIO Base Aperture */
#define AOP2_ASCWRAP_MAILBOX_BASE           0x0000000101600000ULL
#define AOP2_ASCWRAP_MAILBOX_SIZE           0x0000000000088000ULL /* 544 KB aperture */

/** @brief AOP2 Doorbell Aggregator MMIO Base */
#define AOP2_DOORBELL_AGGREGATOR_BASE       0x000000010162c000ULL
#define AOP2_DOORBELL_AGGREGATOR_SIZE       0x0000000000004000ULL /* 16 KB aperture */

/** @brief Exclave Mailbox Proxy MMIO Base (Direct CL4/Tightbeam Cross-Enclave) */
#define AOP2_EXCLAVE_MAILBOX_PROXY_BASE     0x000000035167c000ULL
#define AOP2_EXCLAVE_MAILBOX_PROXY_SIZE     0x0000000000004000ULL /* 16 KB aperture */

/** @brief DART-AOP IOMMU Controller Base */
#define DART_AOP_IOMMU_BASE                 0x0000000100fc0000ULL
#define DART_AOP_IOMMU_SIZE                 0x0000000000010000ULL /* 64 KB aperture */

/** @brief DART-AOP Stream Identifiers (SIDs) */
#define DART_AOP_SID_MAPPER_AOP2            0x10    /* Host XNU / SPU Kernel DMA mapper */
#define DART_AOP_SID_MAPPER_EXCLAVE_AOP2    0x11    /* ExclaveOS Secure Audio DMA mapper */

/** @brief Apple Interrupt Controller (AIC) Interrupt Vectors */
#define AIC_IRQ_AOP2_INBOX_PENDING          357     /* 0x0165: AOP2 Primary Mailbox Inbox (VoiceTrigger Wake) */
#define AIC_IRQ_AOP2_OUTBOX_ACK             358     /* 0x0166: AOP2 Primary Mailbox Outbox Consumed Ack */
#define AIC_IRQ_AOP2_DOORBELL_TRIGGER       359     /* 0x0167: AOP2 Doorbell Aggregator Trigger */
#define AIC_IRQ_AOP2_PANIC_TELEMETRY        360     /* 0x0168: AOP2 Hardware Error / RTKit Panic */
#define AIC_IRQ_AOP2_EXCLAVE_INBOX          361     /* 0x0169: AOP2 Exclave Mailbox Proxy Inbox */
#define AIC_IRQ_AOP2_EXCLAVE_OUTBOX         364     /* 0x016c: AOP2 Exclave Mailbox Proxy Outbox */
#define AIC_IRQ_DART_AOP_FAULT              387     /* 0x0183: DART-AOP IOMMU Translation Fault */

/* ========================================================================= */
/* 2. Always-On Audio Acoustic Parameters & SRAM Buffer Geometry             */
/* ========================================================================= */

/** @brief Always-On Audio Sampling Frequency (16.0 kHz) */
#define AOP_AUDIO_SAMPLE_RATE_HZ            16000U

/** @brief Always-On Audio Bit Depth & Channels */
#define AOP_AUDIO_BITS_PER_SAMPLE           16U
#define AOP_AUDIO_BYTES_PER_SAMPLE          2U
#define AOP_AUDIO_CHANNEL_COUNT             1U      /* Mono acoustic input */
#define AOP_AUDIO_BYTES_PER_FRAME           (AOP_AUDIO_BYTES_PER_SAMPLE * AOP_AUDIO_CHANNEL_COUNT)

/** @brief Continuous Acoustic History Buffer Duration & Size */
#define AOP_AUDIO_HISTORY_DURATION_SEC      3.0f
#define AOP_AUDIO_HISTORY_DURATION_MS       3000U
#define AOP_AUDIO_HISTORY_FRAME_COUNT       48000U  /* 16000 frames/sec * 3.0 sec */
#define AOP_AUDIO_HISTORY_BUFFER_SIZE       96000U  /* 48000 frames * 2 bytes/frame */

/** @brief Low-Power Front-End Power Consumption Limit */
#define AOP_AUDIO_POWER_ENVELOPE_MW         1.85f   /* Operating power consumption <= 1.85 mW */

/** @brief SRAM Memory Offsets inside AOP2 Retention Carveout */
#define AOP2_SRAM_AUDIO_RING_OFFSET         0x00080000U  /* Offset 512 KB: Circular Acoustic FIFO */
#define AOP2_SRAM_AUDIO_RING_STATUS_OFFSET  0x0007F000U  /* Offset 508 KB: Ring Buffer Status Header */
#define AOP2_SRAM_AUDIO_KWS_STATE_OFFSET    0x00098000U  /* Offset 608 KB: Hotword Neural State */

/** @brief Channel Control Bitmasks (kAppleAOPLPMic Properties) */
#define AOP_LPMIC_CH0_MIC0                  (1U << 0)   /* Primary Low-Power PDM Microphone */
#define AOP_LPMIC_CH1_MIC1                  (1U << 1)   /* Secondary Noise Reference Microphone */
#define AOP_LPMIC_CH2_MIC2                  (1U << 2)   /* Tertiary Beamforming Microphone */
#define AOP_LPMIC_CH3_LOOPBACK              (1U << 3)   /* Acoustic Echo Cancellation (AEC) Ref */

#define AOP_LPMIC_DEFAULT_CHANNELS          AOP_LPMIC_CH0_MIC0

/* ========================================================================= */
/* 3. AOP2 Lock-Free Circular Ring Buffer Structures                         */
/* ========================================================================= */

/**
 * @brief Lock-free Single-Producer Single-Consumer (SPSC) Ring Buffer Status Descriptor
 * Reflects struct layout used by AppleAOPAudioRingBufferImpl.
 */
typedef struct __attribute__((aligned(64))) aop_audio_ring_status {
    volatile uint64_t head_frame_index;     /**< Producer write pointer (monotonically increasing) */
    volatile uint64_t tail_frame_index;     /**< Consumer read pointer (monotonically increasing)  */
    volatile uint64_t zero_timestamp_aop;   /**< AOP2 continuous timebase origin (mach_absolute)   */
    volatile uint64_t host_timestamp_ap;    /**< AP Everest host continuous timebase origin        */
    volatile int64_t  clock_drift_ns;       /**< Measured AP/AOP clock drift in nanoseconds        */
    volatile uint32_t zero_ts_wrap_frames;  /**< Frame modulus before timestamp phase rollover     */
    volatile uint32_t buffer_size_bytes;    /**< Ring buffer capacity in bytes (96,000 bytes)      */
    volatile uint16_t frame_size_bytes;     /**< Size per audio frame (2 bytes for 16-bit mono)    */
    volatile uint16_t channels_per_frame;   /**< Active channel count (1)                          */
    volatile uint16_t frames_per_packet;    /**< Hardware DMA transfer chunk size (160 frames)     */
    volatile uint16_t safety_offset_frames; /**< Driver safety margin offset (64 frames)           */
    volatile uint32_t input_latency_frames; /**< PDM decimation hardware pipeline latency          */
    volatile uint32_t status_flags;         /**< Status bitmask (running, overflow, wake_pending)  */
} aop_audio_ring_status_t;

/** @brief Ring Buffer Status Flags */
#define AOP_RING_FLAG_RUNNING               (1U << 0)
#define AOP_RING_FLAG_PREWARMED             (1U << 1)
#define AOP_RING_FLAG_OVERFLOW              (1U << 2)
#define AOP_RING_FLAG_HISTORIC_VALID        (1U << 3)
#define AOP_RING_FLAG_WAKE_PENDING          (1U << 4)
#define AOP_RING_FLAG_EXCLAVE_ISOLATED      (1U << 5)

/**
 * @brief Complete Circular DMA Audio Ring Buffer in SRAM
 */
typedef struct __attribute__((aligned(64))) aop_audio_acoustic_buffer {
    aop_audio_ring_status_t status;
    uint8_t data[AOP_AUDIO_HISTORY_BUFFER_SIZE];
} aop_audio_acoustic_buffer_t;

/* ========================================================================= */
/* 4. VoiceTrigger Structures & Wake Event Descriptors                       */
/* ========================================================================= */

/** @brief UserClient Entitlement for VoiceTrigger Access */
#define kIOPAudioVoiceTriggerUserClientEntitlement  "com.apple.private.aop-voicetrigger.user-access"

/** @brief UserClient Entitlement for Button Haptics Service Access */
#define kAppleAOPButtonHapticsUserClientEntitlement "com.apple.private.aea.haptics.user-access"

/** @brief Maximum Secure VoiceTrigger State Vector Payload Length */
#define VT_MAX_TRIGGER_STATE_SIZE           128U

/**
 * @brief Non-secure VoiceTrigger Event Data (Tightbeam Wire Format)
 * Wire equivalent of voicetriggernonsecure_voicetriggernonsecuredatatb_s (size: 16 bytes).
 */
typedef struct __attribute__((packed)) voicetrigger_nonsecure_data {
    uint64_t timestamp;                     /**< Continuous time of trigger event (mach_absolute) */
    uint64_t sample_frame_time;             /**< Absolute sample frame index of hotword detection */
} voicetrigger_nonsecure_data_t;

/**
 * @brief Secure VoiceTrigger Event Data (Tightbeam Wire Format)
 * Wire equivalent of voicetriggercommon_voicetriggersecuredatatb_s (size: 156 bytes).
 */
typedef struct __attribute__((packed)) voicetrigger_secure_data {
    uint64_t timestamp;                     /**< Continuous time of trigger event                  */
    uint64_t sample_frame_time;             /**< Absolute sample frame index of hotword detection  */
    uint64_t trigger_length_frames;         /**< Utterance duration in audio frames (e.g. 16000)   */
    uint32_t secure_payload_length;         /**< Length of encrypted/isolated acoustic state vector*/
    uint8_t  secure_trigger_payload[VT_MAX_TRIGGER_STATE_SIZE]; /**< Acoustic model embedding */
} voicetrigger_secure_data_t;

/**
 * @brief VoiceTrigger Comprehensive Wake Event Package
 */
typedef struct voicetrigger_wake_event {
    uint64_t host_time_ns;                  /**< Host AP wallclock timestamp in nanoseconds        */
    int64_t  delta_ns;                      /**< Timestamp delta between AOP detection and AP wake */
    int64_t  aop_trigger_time;              /**< AOP timebase timestamp                            */
    int64_t  sample_time;                   /**< Global sample counter at trigger assertion        */
    uint64_t trigger_length_frames;         /**< Utterance frame span                              */
    bool     woke_ap;                       /**< True if Everest P-core was awakened from deep idle*/
    uint32_t trigger_state_size;            /**< Embedded acoustic state size in bytes             */
    uint8_t  trigger_state[VT_MAX_TRIGGER_STATE_SIZE]; /**< Feature correlation vector             */
} voicetrigger_wake_event_t;

/* ========================================================================= */
/* 5. ExclaveOS Tightbeam Audio Stream Isolation & Wire Definitions          */
/* ========================================================================= */

/** @brief Tightbeam Protocol Error Codes */
typedef enum tb_error {
    TB_ERROR_SUCCESS                        = 0x00000000U,
    TB_ERROR_USER_FAILURE                   = 0x00000001U,
    TB_ERROR_INVALID_ARGUMENT               = 0x00000002U,
    TB_ERROR_BUFFER_TOO_SMALL               = 0x00000003U,
    TB_ERROR_PERMISSION_DENIED              = 0x00000004U,
    TB_ERROR_ENDPOINT_CLOSED                = 0x00000005U,
    TB_ERROR_OVERFLOW                       = 0x00000006U,
    TB_ERROR_NOT_INITIALIZED                = 0x00000007U
} tb_error_t;

/** @brief Tightbeam Endpoint Identifiers for Audio */
#define TB_ENDPOINT_AOP2_EXCLAVE_BRIDGE     0x0053U /**< EP 0x53: AOP2 to ExclaveOS Audio Route  */
#define TB_ENDPOINT_IIS_ISOLATED_INPUT      0x0061U /**< Isolated Input Stream EC Proxy           */
#define TB_ENDPOINT_IIS_ISOLATED_OUTPUT     0x0062U /**< Isolated Output Stream EC Proxy          */

/** @brief Tightbeam Audio Driver Method Selectors */
typedef enum tb_audio_selector {
    TB_SEL_AUDIO_INIT                       = 0x0001U,
    TB_SEL_AUDIO_SETUP_IO                   = 0x0002U,
    TB_SEL_AUDIO_TEARDOWN_IO                = 0x0003U,
    TB_SEL_AUDIO_SETUP_CLIENT_IO            = 0x0004U,
    TB_SEL_AUDIO_TEARDOWN_CLIENT_IO         = 0x0005U,
    TB_SEL_AUDIO_READ_INPUT                 = 0x0006U,
    TB_SEL_AUDIO_WRITE_MIX_OUTPUT           = 0x0007U,
    TB_SEL_AUDIO_SELECT_PHYSICAL_STREAM     = 0x0008U,
    TB_SEL_AUDIO_GET_STREAM_DESCRIPTION     = 0x0009U,
    TB_SEL_AUDIO_MAP_DMA_BUFFER             = 0x000AU,
    TB_SEL_AUDIO_ENABLE_ALT_SOURCE          = 0x000BU,
    TB_SEL_AUDIO_ENABLE_INJECTION           = 0x000CU,
    TB_SEL_AUDIO_SLEEP                      = 0x000DU,
    TB_SEL_AUDIO_WAKE                       = 0x000EU,
    TB_SEL_VT_GET_NONSECURE_DATA            = 0x0020U,
    TB_SEL_VT_CONFIGURE_NOTIFICATION        = 0x0021U,
    TB_SEL_VT_DEBUG_GET_SECURE_DATA         = 0x0022U,
    TB_SEL_VT_DEBUG_SIRI_LANGUAGE_MODEL     = 0x0023U
} tb_audio_selector_t;

/**
 * @brief Exclave Audio Driver Status / Result Return Code
 * Wire signature: {exclavesaudiodrivers_exadresult_s=Q} (size: 8 bytes).
 */
typedef struct __attribute__((packed)) exclavesaudiodrivers_exadresult {
    uint64_t status;                        /**< 0 = success, non-zero = IOReturn / Exclave error */
} exclavesaudiodrivers_exadresult_t;

/**
 * @brief Exclave Audio DMA Buffer Specification
 * Wire signature: {exclavesaudiodrivers_audiodmabufferspectb_s=QQ} (size: 16 bytes).
 * Used by exclavesaudiodrivers_audiodriver_mapdmabuffer.
 */
typedef struct __attribute__((packed)) exclavesaudiodrivers_audiodmabufferspec {
    uint64_t dma_base_iova;                 /**< DART IOMMU mapped bus address (SID 0x11)         */
    uint64_t buffer_size_bytes;             /**< Total contiguous buffer capacity in bytes        */
} exclavesaudiodrivers_audiodmabufferspec_t;

/**
 * @brief Tightbeam Message Envelope Header
 * Wire signature: ^{tb_message_s=ICQQQQ[4Q]Q^{tb_transport_s}QQ}
 */
typedef struct __attribute__((packed)) tb_message_header {
    uint32_t message_flags;                 /**< Protocol version and options                     */
    uint8_t  disposition;                   /**< Message type / RPC disposition tag               */
    uint64_t client_identifier;             /**< Client session handle                            */
    uint64_t selector;                      /**< RPC method selector ID                           */
    uint64_t sequence_num;                  /**< Monotonic request/response counter               */
    uint64_t payload_size;                  /**< Trailing variable payload size                   */
} tb_message_header_t;

/**
 * @brief Exclave Physical Stream Description
 * Wire equivalent of exclavesaudiodrivers_exadstreamdescription_s.
 * Format: {IIISCC} (uint32, uint32, uint32, uint16, uint8, uint8) -> 16 bytes packed.
 */
typedef struct __attribute__((packed)) exad_stream_description {
    uint32_t sample_rate;                   /**< Sampling rate in Hz (e.g. 16000, 48000)          */
    uint32_t channels;                      /**< Number of channels (1=mono, 2=stereo)            */
    uint32_t bytes_per_frame;               /**< Total byte stride per frame                      */
    uint16_t format_flags;                  /**< LPCM format flags (linear, signed, float)        */
    uint8_t  bit_depth;                     /**< Bits per channel (16, 24, 32)                    */
    uint8_t  endianness;                    /**< 0=Little-Endian, 1=Big-Endian                    */
} exad_stream_description_t;

/**
 * @brief Secure Indicator Light (SIL) Hardware Enforcement State
 * Managed exclusively by com.apple.service.ExclaveIndicatorController.
 */
typedef enum sil_hardware_state {
    SIL_STATE_INACTIVE                      = 0,    /**< Microphone powered down, SIL off         */
    SIL_STATE_ACTIVE_TRUSTED                = 1,    /**< Microphone active, HW SIL illuminated    */
    SIL_STATE_UNTRUSTED_ATTEMPT             = 2,    /**< Untrusted host access attempt (blocked)  */
    SIL_STATE_TAMPER_FAULT                  = 3     /**< Hardware PWM or display driver failure   */
} sil_hardware_state_t;

/**
 * @brief Exclave Indicator Controller Metrics & State
 */
typedef struct exclave_indicator_state {
    sil_hardware_state_t state;             /**< Current hardware SIL state                       */
    uint32_t brightness_nits;               /**< Secure indicator luminance in nits (IOMFB cap)   */
    uint64_t activation_timestamp;          /**< Timestamp when microphone capture commenced      */
    uint64_t duration_ms;                   /**< Total active capture time                        */
    uint32_t sensor_copy_requests;          /**< Counter of isolated sensor copy operations       */
    bool     pwm_line_asserted;             /**< Physical amber LED PWM line verification         */
} exclave_indicator_state_t;

/* ========================================================================= */
/* 6. LEAP Haptic Engine Audio Transient Synchronization                     */
/* ========================================================================= */

/** @brief LEAP Waveform Asset Identification Constants */
#define LEAP_ASSET_SSHB_CLICK_DOWN          0x0001U /**< Button press mechanical click impulse    */
#define LEAP_ASSET_SSHB_CLICK_UP            0x0002U /**< Button release tactile click impulse     */
#define LEAP_ASSET_SHUTTER_AUDIO_SYNC       0x0005U /**< Camera shutter audio transient sync      */
#define LEAP_ASSET_CROWN_DETENT             0x0008U /**< Rotational virtual detent transient      */

/** @brief Maximum Assets Supported by AppleAOPAudioButtonHapticDevice */
#define LEAP_MAX_WAVEFORM_ASSETS            16U

/**
 * @brief LEAP Waveform Asset Internal Descriptor
 * Wire equivalent of AppleAOPButtonHapticsAssetInternalProp.
 */
typedef struct __attribute__((packed)) leap_waveform_asset {
    uint16_t asset_id;                      /**< Identifier of haptic waveform asset              */
    uint16_t duration_samples;              /**< Waveform length in 48 kHz haptic DAC samples     */
    uint16_t frequency_hz;                  /**< Resonant frequency of LRA motor (e.g. 175 Hz)    */
    uint16_t amplitude_q15;                 /**< Fixed-point Q15 peak amplitude scalar            */
    uint32_t audio_sync_delay_us;           /**< Relative delay from audio transient in microsecs */
    uint16_t coefficient_count;             /**< Number of polynomial FIR shaping coefficients    */
    int16_t  coefficients[8];               /**< PDM2 shaping coefficients for High-Force Driver  */
} leap_waveform_asset_t;

/**
 * @brief LEAP Motor Parking & Resonance Properties
 * Wire equivalent of LEAPParkingProperties::kParkingInfo.
 */
typedef struct __attribute__((packed)) leap_parking_info {
    uint32_t resonant_freq_measured_hz;     /**< Dynamic calibration resonant frequency           */
    uint32_t back_emf_voltage_mv;           /**< Back-EMF sensory voltage feedback                */
    uint16_t damping_factor_q8;             /**< Critical damping coefficient                     */
    uint16_t state_error_count;             /**< Accumulator of missed or anomalous pulses        */
    uint32_t parking_time_us;               /**< Active brake settling duration in microseconds   */
} leap_parking_info_t;

/**
 * @brief Synchronized Audio-Haptic Event Package
 */
typedef struct leap_haptic_audio_sync_event {
    uint64_t audio_sample_index;            /**< Sample index of triggering audio transient       */
    uint16_t haptic_asset_id;               /**< Waveform asset to render                         */
    uint16_t latency_offset_us;             /**< Measured audio-to-haptic phase delta (< 100 us)  */
    bool     coherent;                      /**< True if haptic impulse perfectly aligned         */
} leap_haptic_audio_sync_event_t;

/* ========================================================================= */
/* 7. Clean-Room Ring Buffer Helper Inlines                                  */
/* ========================================================================= */

/**
 * @brief Calculate available unread frames in acoustic ring buffer
 */
static inline uint64_t aop_ring_available_frames(const aop_audio_ring_status_t* status) {
    if (!status) return 0;
    uint64_t head = status->head_frame_index;
    uint64_t tail = status->tail_frame_index;
    return (head >= tail) ? (head - tail) : 0;
}

/**
 * @brief Convert audio frames to bytes
 */
static inline uint32_t aop_frames_to_bytes(uint32_t frames) {
    return frames * AOP_AUDIO_BYTES_PER_FRAME;
}

/**
 * @brief Convert bytes to audio frames
 */
static inline uint32_t aop_bytes_to_frames(uint32_t bytes) {
    return bytes / AOP_AUDIO_BYTES_PER_FRAME;
}

/**
 * @brief Convert audio frames to milliseconds at 16 kHz
 */
static inline uint32_t aop_frames_to_ms(uint32_t frames) {
    return (frames * 1000U) / AOP_AUDIO_SAMPLE_RATE_HZ;
}

/**
 * @brief Convert milliseconds to audio frames at 16 kHz
 */
static inline uint32_t aop_ms_to_frames(uint32_t ms) {
    return (ms * AOP_AUDIO_SAMPLE_RATE_HZ) / 1000U;
}

/**
 * @brief Check if acoustic ring buffer is in an overflow state
 */
static inline bool aop_ring_is_overflow(const aop_audio_ring_status_t* status) {
    if (!status) return false;
    return (status->status_flags & AOP_RING_FLAG_OVERFLOW) != 0;
}

/**
 * @brief Safely calculate trigger time in nanoseconds preventing underflow
 */
static inline uint64_t aop_safe_trigger_time_ns(uint64_t host_time_ns, int64_t delta_ns) {
    if (delta_ns >= 0 && (uint64_t)delta_ns <= host_time_ns) {
        return host_time_ns - (uint64_t)delta_ns;
    }
    return host_time_ns;
}

/* ========================================================================= */
/* 8. Compile-Time Architecture Struct Geometry Invariant Asserts            */
/* ========================================================================= */

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(aop_audio_ring_status_t) == 64, "aop_audio_ring_status_t must be exactly 64 bytes");
_Static_assert(sizeof(aop_audio_acoustic_buffer_t) == 96064, "aop_audio_acoustic_buffer_t must be exactly 96064 bytes");
_Static_assert(sizeof(exclavesaudiodrivers_exadresult_t) == 8, "exadresult must be exactly 8 bytes");
_Static_assert(sizeof(exclavesaudiodrivers_audiodmabufferspec_t) == 16, "audiodmabufferspec must be exactly 16 bytes");
_Static_assert(sizeof(exad_stream_description_t) == 16, "exad_stream_description must be exactly 16 bytes");
_Static_assert(sizeof(voicetrigger_nonsecure_data_t) == 16, "voicetriggernonsecure must be exactly 16 bytes");
_Static_assert(sizeof(voicetrigger_secure_data_t) == 156, "voicetrigger_secure_data must be exactly 156 bytes");
_Static_assert(sizeof(leap_waveform_asset_t) == 30, "leap_waveform_asset must be exactly 30 bytes");
_Static_assert(sizeof(leap_parking_info_t) == 16, "leap_parking_info must be exactly 16 bytes");
#else
typedef char _assert_aop_ring_status_sz[(sizeof(aop_audio_ring_status_t) == 64) ? 1 : -1];
typedef char _assert_aop_acoustic_buf_sz[(sizeof(aop_audio_acoustic_buffer_t) == 96064) ? 1 : -1];
typedef char _assert_exadresult_sz[(sizeof(exclavesaudiodrivers_exadresult_t) == 8) ? 1 : -1];
typedef char _assert_audiodmabuffer_sz[(sizeof(exclavesaudiodrivers_audiodmabufferspec_t) == 16) ? 1 : -1];
typedef char _assert_exadstream_sz[(sizeof(exad_stream_description_t) == 16) ? 1 : -1];
typedef char _assert_vt_nonsec_sz[(sizeof(voicetrigger_nonsecure_data_t) == 16) ? 1 : -1];
typedef char _assert_vt_sec_sz[(sizeof(voicetrigger_secure_data_t) == 156) ? 1 : -1];
typedef char _assert_leap_asset_sz[(sizeof(leap_waveform_asset_t) == 30) ? 1 : -1];
typedef char _assert_leap_parking_sz[(sizeof(leap_parking_info_t) == 16) ? 1 : -1];
#endif

#ifdef __cplusplus
}
#endif

#endif /* AUDIO_HOST_INTERFACE_H */
