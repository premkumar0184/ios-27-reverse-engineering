/*
 * Apple U2 / U3 Ultra-Wideband (UWB) — Time-of-Flight (ToF) & Ranging Mechanics
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Rose 2 (r2p1 / hammerfest) — iPhone 18,3 (v57ap)
 * Subsystems: FxTA, clib_mms32 CIR processor, firacrypto STS engine
 */

#ifndef ROSE_TOF_ALGORITHM_H
#define ROSE_TOF_ALGORITHM_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. Physical Constants & Timing Parameters
 * ========================================================================= */

#define ROSE_SPEED_OF_LIGHT_MM_PER_PS  0.000299792458  /* Speed of light in mm/ps */
#define ROSE_CHIP_RATE_HZ              499200000ULL    /* 499.2 MHz chip clock */
#define ROSE_CHIP_PERIOD_PS            2003.205128     /* (1 / 499.2e6) * 1e12 ps */
#define ROSE_SUBCHIP_INTERP_BITS       8U              /* 256 fractional sub-chip steps */
#define ROSE_SUBCHIP_STEP_PS           (ROSE_CHIP_PERIOD_PS / 256.0) /* ~7.825 ps */

#define ROSE_CIR_BUFFER_ADDR           0x20010000U     /* Hardware CIR memory base */
#define ROSE_CIR_NUM_TAPS              4096U           /* Total CIR complex taps */

/* =========================================================================
 * 2. Fixed Time of Arrival (FxTA) Computation
 * ========================================================================= */

typedef struct {
    uint32_t integer_delay_id;      /* Chip count (id) */
    uint32_t fractional_delay_fd;   /* Sub-chip interpolator count (fd) */
    int64_t  calibration_offset_ps; /* Loopback group delay offset */
} rose_fxta_descriptor_t;

static inline uint64_t rose_compute_fxta_timestamp_ps(const rose_fxta_descriptor_t *fxta) {
    if (!fxta) return 0;
    double raw_ps = ((double)fxta->integer_delay_id * ROSE_CHIP_PERIOD_PS) +
                    ((double)fxta->fractional_delay_fd * ROSE_SUBCHIP_STEP_PS);
    int64_t adjusted_ps = (int64_t)raw_ps - fxta->calibration_offset_ps;
    return (adjusted_ps > 0) ? (uint64_t)adjusted_ps : 0;
}

/* =========================================================================
 * 3. Double-Sided Two-Way Ranging (DS-TWR) Distance Calculation
 * ========================================================================= */

typedef struct {
    uint64_t t1_poll_tx_ps;         /* Initiator TX timestamp */
    uint64_t t2_poll_rx_ps;         /* Responder RX timestamp */
    uint64_t t3_resp_tx_ps;         /* Responder TX timestamp */
    uint64_t t4_resp_rx_ps;         /* Initiator RX timestamp */
    uint64_t t5_final_tx_ps;        /* Initiator Final TX timestamp */
    uint64_t t6_final_rx_ps;        /* Responder Final RX timestamp */
} rose_twr_timestamps_t;

static inline int64_t rose_compute_ds_twr_tof_ps(const rose_twr_timestamps_t *ts) {
    if (!ts) return 0;
    int64_t t_round1 = (int64_t)(ts->t4_resp_rx_ps - ts->t1_poll_tx_ps);
    int64_t t_reply1 = (int64_t)(ts->t3_resp_tx_ps - ts->t2_poll_rx_ps);
    int64_t t_round2 = (int64_t)(ts->t6_final_rx_ps - ts->t3_resp_tx_ps);
    int64_t t_reply2 = (int64_t)(ts->t5_final_tx_ps - ts->t4_resp_rx_ps);

    /* DS-TWR Formula: cancels clock drift between initiator and responder oscillators.
     * Use 128-bit integer / double precision to guard against 64-bit signed overflow on multi-ms transactions. */
#if defined(__SIZEOF_INT128__)
    __int128 num = ((__int128)t_round1 * (__int128)t_round2) - ((__int128)t_reply1 * (__int128)t_reply2);
    __int128 den = (__int128)t_round1 + (__int128)t_round2 + (__int128)t_reply1 + (__int128)t_reply2;
    if (den <= 0) return 0;
    return (int64_t)(num / den);
#else
    double num = ((double)t_round1 * (double)t_round2) - ((double)t_reply1 * (double)t_reply2);
    double den = (double)t_round1 + (double)t_round2 + (double)t_reply1 + (double)t_reply2;
    if (den <= 0.0) return 0;
    return (int64_t)(num / den);
#endif
}

static inline float rose_tof_to_distance_meters(int64_t tof_ps) {
    if (tof_ps <= 0) return 0.0f;
    return (float)((double)tof_ps * ROSE_SPEED_OF_LIGHT_MM_PER_PS / 1000.0);
}

/* =========================================================================
 * 4. Channel Impulse Response (CIR) First-Path Detection
 * ========================================================================= */

typedef struct {
    int16_t i;
    int16_t q;
} rose_cir_tap_t;

typedef struct {
    uint32_t first_path_idx;        /* LE_1stpathidx */
    uint32_t peak_path_idx;         /* Maximum amplitude tap */
    float    first_path_snr_db;
    float    peak_path_snr_db;
    uint8_t  figure_of_merit;       /* tof_fom (0 - 255) */
    bool     line_of_sight_detected;
} rose_cir_analysis_t;

static inline void rose_analyze_cir(const rose_cir_tap_t *cir, uint32_t num_taps, rose_cir_analysis_t *out) {
    if (!cir || !out || num_taps == 0) return;

    float peak_mag_sq = 0.0f;
    uint32_t peak_idx = 0;
    float noise_accum = 0.0f;
    uint32_t noise_samples = (num_taps > 256) ? 256 : num_taps / 4;

    /* Measure baseline noise floor from early taps prior to signal arrival */
    for (uint32_t k = 0; k < noise_samples; k++) {
        float mag_sq = (float)cir[k].i * (float)cir[k].i + (float)cir[k].q * (float)cir[k].q;
        noise_accum += mag_sq;
    }
    float noise_floor_sq = (noise_samples > 0) ? (noise_accum / (float)noise_samples) : 1.0f;
    if (noise_floor_sq < 1.0f) noise_floor_sq = 1.0f;

    /* Search for peak amplitude tap */
    for (uint32_t k = 0; k < num_taps; k++) {
        float mag_sq = (float)cir[k].i * (float)cir[k].i + (float)cir[k].q * (float)cir[k].q;
        if (mag_sq > peak_mag_sq) {
            peak_mag_sq = mag_sq;
            peak_idx = k;
        }
    }

    /* Leading Edge (LE) thresholding: 6 dB above noise floor or 20% of peak */
    float le_thresh_sq = fmaxf(noise_floor_sq * 4.0f, peak_mag_sq * 0.04f);
    uint32_t fp_idx = peak_idx;
    for (uint32_t k = (peak_idx > 64) ? (peak_idx - 64) : 0; k < peak_idx; k++) {
        float mag_sq = (float)cir[k].i * (float)cir[k].i + (float)cir[k].q * (float)cir[k].q;
        if (mag_sq >= le_thresh_sq) {
            fp_idx = k;
            break;
        }
    }

    float fp_mag_sq = (float)cir[fp_idx].i * (float)cir[fp_idx].i + (float)cir[fp_idx].q * (float)cir[fp_idx].q;
    out->first_path_idx = fp_idx;
    out->peak_path_idx = peak_idx;
    out->first_path_snr_db = 10.0f * log10f(fmaxf(1.0f, fp_mag_sq / noise_floor_sq));
    out->peak_path_snr_db = 10.0f * log10f(fmaxf(1.0f, peak_mag_sq / noise_floor_sq));

    /* LOS detection: First path within 12 taps of peak and high relative power */
    out->line_of_sight_detected = ((peak_idx - fp_idx) <= 12);
    float fp_to_peak_ratio = fp_mag_sq / fmaxf(1.0f, peak_mag_sq);
    out->figure_of_merit = (uint8_t)fminf(255.0f, fp_to_peak_ratio * 200.0f + (out->line_of_sight_detected ? 55.0f : 0.0f));
}

/* =========================================================================
 * 5. Scrambled Timestamp Sequence (STS) Cryptographic State
 * ========================================================================= */

typedef struct {
    uint8_t  session_key[16];       /* 128-bit AES Session Key */
    uint8_t  session_config[32];    /* FiRa session configuration */
    uint8_t  session_config_digest[32]; /* SHA-256 digest */
    uint8_t  auth_key[16];          /* STS pulse generation key */
    uint8_t  auth_iv[8];            /* STS initialization vector */
    uint32_t sts_block_index;       /* Current ranging block index */
    uint32_t sts_round_index;       /* Current ranging round index */
    bool     sts_valid;             /* Hardware correlation verification flag */
} rose_firacrypto_state_t;

#ifdef __cplusplus
}
#endif

#endif /* ROSE_TOF_ALGORITHM_H */
