/*
 * Apple Display Co-Processor (DCP) — VFTG & SWMPR Architecture
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Silicon A19 Pro (t8150) — iPhone 18,3 (v57ap)
 * Subsystems: UPBlock_VFTG_v38 & UPBlock_SWMPR_v1
 */

#ifndef DCP_VFTG_SWMPR_H
#define DCP_VFTG_SWMPR_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. Physical Panel & Line Geometry Invariants
 * ========================================================================= */

#define VFTG_PIXEL_CLOCK_HZ          504000000ULL  /* 504.0 MHz constant scanout clock */
#define VFTG_HORIZONTAL_ACTIVE       1320U         /* Active pixels per scanline */
#define VFTG_HORIZONTAL_FRONT_PORCH  24U           /* HFP pixels */
#define VFTG_HORIZONTAL_SYNC_WIDTH   16U           /* HSYNC pixels */
#define VFTG_HORIZONTAL_BACK_PORCH   40U           /* HBP pixels */
#define VFTG_HORIZONTAL_TOTAL        1400U         /* Total pixels per line (fixed) */

/* Line duration in picoseconds: (1400 / 504,000,000) * 1e12 = 2,777,777 ps (~2.778 us) */
#define VFTG_LINE_TIME_PS            2777778ULL
#define VFTG_LINE_TIME_NS            2777.777778

#define VFTG_VERTICAL_ACTIVE         2868U         /* Active lines (Tandem OLED) */
#define VFTG_VERTICAL_FRONT_PORCH    12U           /* VFP lines */
#define VFTG_VERTICAL_SYNC_WIDTH     4U            /* VSYNC lines */
#define VFTG_VERTICAL_OVERHEAD_LINES (VFTG_VERTICAL_ACTIVE + VFTG_VERTICAL_FRONT_PORCH + VFTG_VERTICAL_SYNC_WIDTH) /* 2884 lines */

/* Active scanout time: 2868 lines * 2.777778 us = 7,966.667 us (~7.967 ms) */
#define VFTG_ACTIVE_SCAN_TIME_US     7966.666667

/* Hardware Fast_TE Panel Synchronization Constants */
#define VFTG_FAST_TE_CLOCK_HZ        24000000U     /* 24.0 MHz sample clock */
#define VFTG_MAX_TE_JITTER_TICKS     48U           /* 48 ticks @ 24MHz = 2.0 us */

/* =========================================================================
 * 2. ProMotion Discrete Timing Modes
 * ========================================================================= */

typedef struct {
    uint32_t refresh_rate_hz;
    uint32_t frame_duration_us;
    uint32_t vbp_lines;
    uint32_t total_lines;
    uint32_t vblank_lines;
    uint32_t vblank_duration_us;
    float active_duty_cycle_pct;
} vftg_timing_mode_t;

static const vftg_timing_mode_t kPromotionTimingTable[11] = {
    { 120,    8333,     116,   3000,     132,     366,  95.60f },
    {  80,   12500,    1616,   4500,    1632,    4533,  63.73f },
    {  60,   16666,    3116,   6000,    3132,    8700,  47.80f },
    {  48,   20833,    4616,   7500,    4632,   12866,  38.24f },
    {  40,   25000,    6116,   9000,    6132,   17033,  31.87f },
    {  30,   33333,    9116,  12000,    9132,   25366,  23.90f },
    {  24,   41666,   12116,  15000,   12132,   33700,  19.12f },
    {  20,   50000,   15116,  18000,   15132,   42033,  15.93f },
    {  15,   66666,   21116,  24000,   21132,   58700,  11.95f },
    {  10,  100000,   33116,  36000,   33132,   92033,   7.97f },
    {   1, 1000000,  357116, 360000,  357132,  992033,   0.80f }
};

/* =========================================================================
 * 3. Software-Managed Pixel Refresh (SWMPR) State Machine
 * ========================================================================= */

typedef enum {
    SWMPR_STATE_IDLE_10HZ               = 0,
    SWMPR_STATE_INTERACTIVE_RAMP_UP     = 1,
    SWMPR_STATE_ACTIVE_120HZ            = 2,
    SWMPR_STATE_DECEL_RAMP_DOWN         = 3,
    SWMPR_STATE_MEDIA_LOCK_24_48_60HZ   = 4,
    SWMPR_STATE_AOD_1HZ                 = 5
} swmpr_state_t;

typedef struct {
    uint32_t step;
    uint32_t target_hz;
    uint32_t hold_time_ms;
} swmpr_decel_step_t;

static const swmpr_decel_step_t kDecelSequence[5] = {
    { 1, 80, 25 },
    { 2, 60, 25 },
    { 3, 40, 25 },
    { 4, 30, 15 },
    { 5, 10, 10 }
};

#define SWMPR_HYSTERESIS_TOTAL_MS       100U
#define SWMPR_TOUCH_BOOST_MAX_LATENCY_US 8333U

typedef struct {
    swmpr_state_t current_state;
    uint32_t current_rate_hz;
    uint32_t requested_rate_hz;
    uint64_t last_touch_timestamp_us;
    uint64_t state_entry_timestamp_us;
    uint32_t decel_step_index;
    bool fast_te_locked;
    uint32_t te_jitter_accumulator;
} swmpr_context_t;

/* =========================================================================
 * 4. Helper & Arbitration Functions
 * ========================================================================= */

static inline uint32_t vftg_calculate_total_lines(uint32_t vbp_lines) {
    return VFTG_VERTICAL_OVERHEAD_LINES + vbp_lines;
}

static inline uint64_t vftg_calculate_frame_duration_us(uint32_t total_lines) {
    /* (total_lines * 1400) / 504 = total_lines * 2.777778 us */
    return ((uint64_t)total_lines * VFTG_HORIZONTAL_TOTAL) / (VFTG_PIXEL_CLOCK_HZ / 1000000ULL);
}

static inline const vftg_timing_mode_t* vftg_lookup_mode(uint32_t target_hz) {
    for (size_t i = 0; i < 11; i++) {
        if (kPromotionTimingTable[i].refresh_rate_hz == target_hz) {
            return &kPromotionTimingTable[i];
        }
    }
    return &kPromotionTimingTable[2]; /* Default to 60Hz if not found */
}

static inline void swmpr_handle_touch_begin(swmpr_context_t *ctx, uint64_t now_us) {
    if (!ctx) return;
    ctx->last_touch_timestamp_us = now_us;
    ctx->state_entry_timestamp_us = now_us;
    ctx->current_state = SWMPR_STATE_ACTIVE_120HZ;
    ctx->current_rate_hz = 120;
    ctx->decel_step_index = 0;
}

static inline void swmpr_step_arbitration(swmpr_context_t *ctx, uint64_t now_us) {
    if (!ctx) return;
    uint64_t elapsed_since_touch_ms = (now_us - ctx->last_touch_timestamp_us) / 1000ULL;

    switch (ctx->current_state) {
        case SWMPR_STATE_ACTIVE_120HZ:
            if (elapsed_since_touch_ms > 16) { /* User finger lifted */
                ctx->current_state = SWMPR_STATE_DECEL_RAMP_DOWN;
                ctx->state_entry_timestamp_us = now_us;
                ctx->decel_step_index = 0;
                ctx->current_rate_hz = kDecelSequence[0].target_hz;
            }
            break;

        case SWMPR_STATE_DECEL_RAMP_DOWN: {
            uint64_t step_elapsed_ms = (now_us - ctx->state_entry_timestamp_us) / 1000ULL;
            if (step_elapsed_ms >= kDecelSequence[ctx->decel_step_index].hold_time_ms) {
                ctx->decel_step_index++;
                ctx->state_entry_timestamp_us = now_us;
                if (ctx->decel_step_index >= 5) {
                    ctx->current_state = SWMPR_STATE_IDLE_10HZ;
                    ctx->current_rate_hz = 10;
                } else {
                    ctx->current_rate_hz = kDecelSequence[ctx->decel_step_index].target_hz;
                }
            }
            break;
        }

        case SWMPR_STATE_IDLE_10HZ:
        case SWMPR_STATE_MEDIA_LOCK_24_48_60HZ:
        case SWMPR_STATE_AOD_1HZ:
        default:
            break;
    }
}

#ifdef __cplusplus
}
#endif

#endif /* DCP_VFTG_SWMPR_H */
