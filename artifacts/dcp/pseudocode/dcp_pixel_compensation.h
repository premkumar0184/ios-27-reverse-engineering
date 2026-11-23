/*
 * Apple Display Co-Processor (DCP) — Sub-Pixel Panel Compensation Pipeline
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Silicon A19 Pro (t8150) — iPhone 18,3 (v57ap)
 * Subsystems: UPBlock_BICS_v19, UPBlock_PTUC_v4, UPBlock_PDC_v11, UPBlock_ACSS_v11
 */

#ifndef DCP_PIXEL_COMPENSATION_H
#define DCP_PIXEL_COMPENSATION_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. Burn-In Compensation System (UPBlock_BICS_v19)
 * ========================================================================= */

#define BICS_HISTORY_BUFFER_SIZE      8388608U    /* 8 MB compressed aging history table (0x800000) */
#define BICS_AGING_GAMMA              1.45f       /* Subpixel degradation exponent */
#define BICS_ACTIVATION_ENERGY_EV     0.62f       /* Arrhenius activation energy */
#define BICS_BOLTZMANN_EV_K           8.617333262145e-5f /* k_B in eV/K */

typedef struct {
    uint8_t  history_buffer[BICS_HISTORY_BUFFER_SIZE];
    uint32_t active_history_size;
    float    gain_red;
    float    gain_green;
    float    gain_blue;
    bool     compressed_export_supported;
} bics_engine_t;

static inline float bics_compute_stress_increment(float luminance_nits, float temp_celsius, float delta_t_hours) {
    float temp_kelvin = temp_celsius + 273.15f;
    float thermal_acceleration = expf(-BICS_ACTIVATION_ENERGY_EV / (BICS_BOLTZMANN_EV_K * temp_kelvin));
    return powf(luminance_nits, BICS_AGING_GAMMA) * delta_t_hours * thermal_acceleration;
}

static inline float bics_compute_subpixel_gain(float cumulative_stress) {
    /* Voltage boost model: linear-exponential gain restoration */
    return 1.0f + (0.045f * cumulative_stress / (1.0f + 0.02f * cumulative_stress));
}

/* =========================================================================
 * 2. Panel Temperature Uniformity Compensation (UPBlock_PTUC_v4)
 * ========================================================================= */

#define PTUC_GRID_X_COUNT             64U         /* 64 horizontal zones across 1320 pixels */
#define PTUC_GRID_Y_COUNT             32U         /* 32 vertical zones across 2868 lines */
#define PTUC_TOTAL_ZONES              (PTUC_GRID_X_COUNT * PTUC_GRID_Y_COUNT) /* 2048 zones */

#define PTUC_ZONE_WIDTH_PIXELS        20.625f     /* 1320 / 64 */
#define PTUC_ZONE_HEIGHT_PIXELS       89.625f     /* 2868 / 32 */

typedef struct {
    float soc_ttr[4];                 /* A19 Pro die temperature sensors (T8150_TTR0..3) */
    float battery_temp_c;             /* Battery PMU thermistor */
    float ddic_temp_c;                /* Display Driver IC telemetry */
    float fallback_initial_guess_c;   /* Fallback guess if SMC telemetry is missing */
    bool  smc_valid;
} ptuc_thermal_inputs_t;

typedef struct {
    float zone_temp_c[PTUC_GRID_Y_COUNT][PTUC_GRID_X_COUNT];
    uint16_t compensation_lut_2dtc[PTUC_TOTAL_ZONES];
    uint32_t current_dbv;             /* Display Brightness Value (0 - 4095) */
    uint32_t current_rr_mode;         /* Refresh rate mode */
} ptuc_engine_t;

static inline void ptuc_interpolate_thermal_grid(ptuc_engine_t *engine, const ptuc_thermal_inputs_t *inputs) {
    if (!engine || !inputs) return;
    float core_hotspot = (inputs->soc_ttr[0] + inputs->soc_ttr[1] + inputs->soc_ttr[2] + inputs->soc_ttr[3]) * 0.25f;
    float ambient_ref = inputs->smc_valid ? inputs->battery_temp_c : inputs->fallback_initial_guess_c;

    for (uint32_t y = 0; y < PTUC_GRID_Y_COUNT; y++) {
        for (uint32_t x = 0; x < PTUC_GRID_X_COUNT; x++) {
            /* Gaussian thermal spread model centered over SoC position (x=20, y=10) */
            float dx = (float)x - 20.0f;
            float dy = (float)y - 10.0f;
            float dist_sq = dx * dx + dy * dy;
            float heat_factor = expf(-dist_sq / 128.0f);
            engine->zone_temp_c[y][x] = ambient_ref + (core_hotspot - ambient_ref) * heat_factor;
        }
    }
}

/* =========================================================================
 * 3. Pixel Distortion & Density Compensation (UPBlock_PDC_v11)
 * ========================================================================= */

typedef struct {
    uint32_t version;
    uint32_t num_bins;
    float    bin_weights[8];
    bool     dynamic_island_cutout_active;
    bool     corner_curvature_active;
} pdcc_config_block_t;

typedef struct {
    uint32_t version;
    float    channel_gains[3];        /* R, G, B channels */
    uint16_t spuc_calibration_map[1320]; /* Subpixel Uniformity Compensation factory map */
} pdcp_param_block_t;

static inline float pdc_mix_bins(float bin_a, float bin_b, float weight) {
    if (weight < 0.0f) weight = 0.0f;
    if (weight > 1.0f) weight = 1.0f;
    return bin_a * (1.0f - weight) + bin_b * weight;
}

/* =========================================================================
 * 4. Active / Angle Color Shift (UPBlock_ACSS_v11)
 * ========================================================================= */

typedef struct {
    float emmp_matrix[3][3];          /* 3x3 Electro-Magnetic Microcavity Parameter table */
    float viewing_angle_theta_deg;    /* Viewing angle off normal */
    float als_lux;                    /* Ambient light illuminance */
    float als_cct_kelvin;             /* Ambient light correlated color temperature */
} acss_engine_t;

static inline void acss_apply_als_rescale(acss_engine_t *acss, float ambient_lux, float ambient_cct) {
    if (!acss) return;
    acss->als_lux = ambient_lux;
    acss->als_cct_kelvin = ambient_cct;

    /* Rescale off-axis blue correction when ambient illumination increases */
    float lux_factor = 1.0f + (ambient_lux / 50000.0f) * 0.12f;
    acss->emmp_matrix[2][2] = 1.0f * lux_factor; /* Modulate Blue microcavity gain */
}

#ifdef __cplusplus
}
#endif

#endif /* DCP_PIXEL_COMPENSATION_H */
