/*
 * Apple U2 / U3 Ultra-Wideband (UWB) — Angle-of-Arrival (AoA) & PDoA Localization
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Rose 2 (r2p1 / hammerfest) — iPhone 18,3 (v57ap)
 * Subsystems: ALGO _run_toa_aoa_algo_r2, 3D Antenna Array PDoA Interferometer
 */

#ifndef ROSE_AOA_PDOA_H
#define ROSE_AOA_PDOA_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. Physical Antenna Array Geometries (iPhone 18,3)
 * ========================================================================= */

#define ROSE_NUM_RX_ANTENNAS           3U
#define ROSE_BASELINE_DH_MM            15.5f       /* Rx0 - Rx1 horizontal baseline */
#define ROSE_BASELINE_DV_MM            14.8f       /* Rx1 - Rx2 vertical baseline */
#define ROSE_CHANNEL9_WAVELENGTH_MM    37.534f     /* c / 7987.2 MHz */
#define ROSE_PI                        3.14159265358979323846f

#define Q16_TO_FLOAT(x)                ((float)(x) / 65536.0f)
#define FLOAT_TO_Q16(x)                ((int32_t)((x) * 65536.0f))

/* =========================================================================
 * 2. DeviceTree Spherical Calibration Boundaries
 * ========================================================================= */

typedef struct {
    int32_t theta_attach_high_q16;     /* 194641 -> 2.970 rad (170.2 deg) */
    int32_t theta_attach_low_q16;      /* 0 -> 0.0 rad (0 deg) */
    int32_t theta_detach_high_q16;     /* 205783 -> 3.140 rad (180.0 deg) */
    int32_t theta_detach_low_q16;      /* 11141 -> 0.170 rad (9.7 deg) */

    int32_t phi_attach_high_q16;       /* -156631 -> -2.390 rad (-136.9 deg) */
    int32_t phi_attach_low_q16;        /* 99614 -> 1.520 rad (87.1 deg) */
    int32_t phi_detach_high_q16;       /* 49152 -> 0.750 rad (43.0 deg) */
    int32_t phi_detach_low_q16;        /* -106168 -> -1.620 rad (-92.8 deg) */
    int32_t phi_ignore_high_q16;       /* 177602 -> 2.710 rad (155.3 deg) */
    int32_t phi_ignore_low_q16;        /* 28835 -> 0.440 rad (25.2 deg) */

    float   std_dev_x;                 /* 67.0 */
    float   std_dev_y;                 /* 65.0 */
    float   std_dev_z;                 /* 30.0 */
    uint32_t magnitude_cal;            /* 50790400 */
} rose_spherical_calibration_t;

static const rose_spherical_calibration_t kDefaultRoseCalibration = {
    .theta_attach_high_q16 = 194641,
    .theta_attach_low_q16  = 0,
    .theta_detach_high_q16 = 205783,
    .theta_detach_low_q16  = 11141,
    .phi_attach_high_q16   = -156631,
    .phi_attach_low_q16    = 99614,
    .phi_detach_high_q16   = 49152,
    .phi_detach_low_q16    = -106168,
    .phi_ignore_high_q16   = 177602,
    .phi_ignore_low_q16    = 28835,
    .std_dev_x             = 67.0f,
    .std_dev_y             = 65.0f,
    .std_dev_z             = 30.0f,
    .magnitude_cal         = 50790400U
};

/* =========================================================================
 * 3. PDoA Phase Difference to Angle Computation
 * ========================================================================= */

typedef struct {
    float phase_rx0_rad;
    float phase_rx1_rad;
    float phase_rx2_rad;
    float snr_rx0_db;
    float snr_rx1_db;
    float snr_rx2_db;
} rose_pdoa_inputs_t;

typedef struct {
    float   azimuth_deg;               /* -90.0 to +90.0 degrees */
    float   elevation_deg;             /* -90.0 to +90.0 degrees */
    int16_t raw_azi_centideg;          /* Firmware integer output */
    int16_t raw_ele_centideg;          /* Firmware integer output */
    int16_t raw_pdoa_h;                /* Horizontal PDoA count */
    int16_t raw_pdoa_v;                /* Vertical PDoA count */
    uint16_t aoa_uncertainty;          /* Covariance metric */
    bool    within_attachment_cone;
} rose_aoa_result_t;

static inline float rose_wrap_phase_rad(float phase) {
    if (!isfinite(phase)) return 0.0f;
    while (phase > ROSE_PI)  phase -= 2.0f * ROSE_PI;
    while (phase < -ROSE_PI) phase += 2.0f * ROSE_PI;
    return phase;
}

static inline void rose_compute_aoa(
    const rose_pdoa_inputs_t *inputs,
    const rose_spherical_calibration_t *cal,
    rose_aoa_result_t *out)
{
    if (!inputs || !out) return;
    if (!cal) cal = &kDefaultRoseCalibration;

    /* Phase differences: Rx0-Rx1 (horizontal) and Rx1-Rx2 (vertical, Delta_psi_12) */
    float delta_psi_h = rose_wrap_phase_rad(inputs->phase_rx0_rad - inputs->phase_rx1_rad);
    float delta_psi_v = rose_wrap_phase_rad(inputs->phase_rx1_rad - inputs->phase_rx2_rad);

    /* Spatial PDoA interferometer sin(theta) inversion */
    float sin_theta = (ROSE_CHANNEL9_WAVELENGTH_MM * delta_psi_h) / (2.0f * ROSE_PI * ROSE_BASELINE_DH_MM);
    float sin_phi   = (ROSE_CHANNEL9_WAVELENGTH_MM * delta_psi_v) / (2.0f * ROSE_PI * ROSE_BASELINE_DV_MM);

    /* Clamp numerical domain to [-1.0, 1.0] to prevent NaN on extreme angles or noise */
    sin_theta = fmaxf(-1.0f, fminf(1.0f, sin_theta));
    sin_phi   = fmaxf(-1.0f, fminf(1.0f, sin_phi));

    float theta_rad = asinf(sin_theta);
    float phi_rad   = asinf(sin_phi);

    out->azimuth_deg   = theta_rad * (180.0f / ROSE_PI);
    out->elevation_deg = phi_rad   * (180.0f / ROSE_PI);

    out->raw_azi_centideg = (int16_t)(out->azimuth_deg * 100.0f);
    out->raw_ele_centideg = (int16_t)(out->elevation_deg * 100.0f);
    out->raw_pdoa_h = (int16_t)(delta_psi_h * 1000.0f);
    out->raw_pdoa_v = (int16_t)(delta_psi_v * 1000.0f);

    /* Validate against attachment cone calibration limits */
    int32_t theta_q16 = FLOAT_TO_Q16(fabsf(theta_rad));
    int32_t phi_q16   = FLOAT_TO_Q16(phi_rad);

    bool theta_valid = (theta_q16 >= cal->theta_attach_low_q16 && theta_q16 <= cal->theta_attach_high_q16);
    bool phi_valid   = (phi_q16 >= cal->phi_attach_high_q16 && phi_q16 <= cal->phi_attach_low_q16);
    out->within_attachment_cone = (theta_valid && phi_valid);

    /* Calculate uncertainty based on minimum antenna SNR */
    float min_snr = fminf(inputs->snr_rx0_db, fminf(inputs->snr_rx1_db, inputs->snr_rx2_db));
    if (min_snr < 6.0f) {
        out->aoa_uncertainty = 0xFFFF; /* High uncertainty / untrusted */
    } else {
        out->aoa_uncertainty = (uint16_t)(1000.0f / fmaxf(1.0f, min_snr));
    }
}

#ifdef __cplusplus
}
#endif

#endif /* ROSE_AOA_PDOA_H */
