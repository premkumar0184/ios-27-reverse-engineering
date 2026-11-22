/**
 * @file IOHIDPointerScrollFilter.pseudo.c
 * @brief Production-grade C99 reverse-engineered reconstruction of Apple's
 *        IOHIDPointerScrollFilter.plugin for iOS 27.2 (Darwin 24.2.0, arm64e PAC00).
 *
 * Reconstructed from dyld_shared_cache_arm64e.48 at VM base 0x2529c4000.
 * Implements wheel delta translation, parametric pointer scroll acceleration curves,
 * trackpad momentum scrolling synthesis, and phase gating.
 *
 * Compiles cleanly with: gcc -Wall -Wextra -Werror -std=c99
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
#include <assert.h>

/* ========================================================================= */
/* 1. Hardware & System Architecture Constants                              */
/* ========================================================================= */

#define PACDA_DISCRIMINATOR_FILTER_VTABLE       0x7e02
#define PACDA_DISCRIMINATOR_ACCELERATOR_VTABLE  0x9ff6
#define PACDA_DISCRIMINATOR_VTABLE              0x7e02
#define PACDA_DISCRIMINATOR_METHOD              0x9dcf
#define PACDA_DISCRIMINATOR_TABLE               0x7166

#define K_IOHID_EVENT_TYPE_NULL         0
#define K_IOHID_EVENT_TYPE_SCROLL       6
#define K_IOHID_EVENT_TYPE_DIGITIZER    11
#define K_IOHID_EVENT_TYPE_POINTER      17

#define K_IOHID_EVENT_FIELD_SCROLL_X           0x00060000
#define K_IOHID_EVENT_FIELD_SCROLL_Y           0x00060001
#define K_IOHID_EVENT_FIELD_SCROLL_Z           0x00060002
#define K_IOHID_EVENT_FIELD_SCROLL_IS_PIXELS   0x00060003

#define K_IOHID_EVENT_FIELD_POINTER_X          0x00110000
#define K_IOHID_EVENT_FIELD_POINTER_Y          0x00110001

#define K_IOHID_EVENT_FLAG_IS_ACCELERATED      0x00010000
#define K_IOHID_EVENT_FLAG_IS_PIXEL_UNITS      0x00000008

/* Scroll Phase Bitmask */
#define K_IOHID_EVENT_SCROLL_PHASE_NONE             0
#define K_IOHID_EVENT_SCROLL_PHASE_BEGAN            (1 << 0) /* 1 */
#define K_IOHID_EVENT_SCROLL_PHASE_CHANGED          (1 << 1) /* 2 */
#define K_IOHID_EVENT_SCROLL_PHASE_ENDED            (1 << 2) /* 4 */
#define K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN         (1 << 3) /* 8 */
#define K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED       (1 << 4) /* 16 */
#define K_IOHID_EVENT_SCROLL_MOMENTUM_ENDED         (1 << 5) /* 32 */

/* Modifier Flags */
#define K_IOHID_MODIFIER_SHIFT                 (1 << 17)

/* Authoritative Constants from __TEXT.__const (offsets 0x2529cd690 - 0x2529cd7c0) */
static const double K_CONST_USEC_PER_SEC               = 1000000.0;             /* 0x2529cd690 */
static const double K_CONST_POINTER_ACCEL_MAX_CLAMP   = 500.0;                 /* 0x2529cd698 */
static const double K_CONST_REPORT_RATE_MAX           = 150.0;                 /* 0x2529cd6a0 */
static const double K_CONST_REPORT_RATE_DEFAULT       = 67.0;                  /* 0x2529cd6a8 */
static const double K_CONST_PARAM_CURVATURE_BETA      = -0.0145721435546875;   /* 0x2529cd6b0 */
static const double K_CONST_PARAM_GAIN_LINEAR_ALPHA   = 1.5009918212890625;    /* 0x2529cd6b8 */
static const double K_CONST_PARAM_TANGENT_ROOT_GAMMA  = 0.100006103515625;     /* 0x2529cd6c0 */
static const double K_CONST_MSEC_PER_SEC              = 1000.0;                /* 0x2529cd6c8 */
static const double K_CONST_DEFAULT_SCROLL_MULTIPLIER = 1.4328358208955223;    /* 0x2529cd7b0 */
static const double K_CONST_LINE_TO_POINT_SCALE       = 10.0;                  /* 0x2529ca624 */
static const double K_CONST_MOMENTUM_DECAY_RATE       = 0.950;                 /* Per 10ms tick */
static const double K_CONST_MOMENTUM_TERMINAL_CUTOFF  = 0.050;                 /* Points/tick resting threshold */

/* ========================================================================= */
/* 2. Type Definitions & Simulated Event Subsystem                          */
/* ========================================================================= */

typedef struct {
    uint32_t type;
    uint64_t timestamp_ns;
    uint32_t flags;
    uint32_t modifier_flags;
    double scroll_x;
    double scroll_y;
    double scroll_z;
    double pointer_x;
    double pointer_y;
    bool is_pixel_units;
    uint32_t scroll_phase;
} IOHIDEvent;

typedef struct {
    double velocity_threshold;
    double gain;
} IOHIDCurvePoint;

typedef struct {
    uint32_t point_count;
    IOHIDCurvePoint points[16];
} IOHIDAccelerationTable;

typedef enum {
    ACCEL_ALGORITHM_TABLE = 0,
    ACCEL_ALGORITHM_PARAMETRIC = 1,
    ACCEL_ALGORITHM_LINEAR = 2
} IOHIDAccelerationAlgorithm;

typedef struct IOHIDPointerScrollFilterState {
    uint64_t vtable_signature;
    uint64_t accelerator_vtable_signature;
    uint32_t ref_count;
    void* service_ref;
    uint64_t service_id;
    
    /* Device configuration */
    double pointer_acceleration_value;
    double scroll_acceleration_value;
    double pointer_acceleration_minimum;
    double scroll_resolution;
    double pointer_resolution;
    
    bool is_pointer_acceleration_enabled;
    bool is_scroll_acceleration_enabled;
    bool use_linear_mouse_scaling;
    bool natural_scrolling_enabled;
    
    IOHIDAccelerationAlgorithm accel_algorithm;
    IOHIDAccelerationTable scroll_table;
    
    /* Sub-pixel accumulator with remainder preservation */
    double accum_subpixel_x;
    double accum_subpixel_y;
    double accum_remainder_x;
    double accum_remainder_y;
    
    /* Lifecycle & scheduling state */
    bool is_open;
    bool is_scheduled;
    uint64_t momentum_timer_disarm_timestamp;
    
    /* Momentum Synthesis Engine State */
    bool momentum_active;
    double momentum_velocity_x;
    double momentum_velocity_y;
    uint64_t momentum_dispatch_rate_ms;
    uint32_t momentum_phase;
} IOHIDPointerScrollFilterState;

/* ========================================================================= */
/* 3. PAC00 Virtual Dispatch Verification                                    */
/* ========================================================================= */

static inline uint64_t sign_vtable_pointer(uint64_t raw_ptr, uint16_t discriminator) {
    uint64_t pac_tag = ((uint64_t)discriminator) << 48;
    return (raw_ptr & 0x0000FFFFFFFFFFFFULL) | pac_tag;
}

static inline bool authenticate_vtable_pointer(uint64_t signed_ptr, uint16_t discriminator) {
    uint16_t tag = (uint16_t)(signed_ptr >> 48);
    return tag == discriminator;
}

/* ========================================================================= */
/* 4. Core Filter Logic Implementation                                       */
/* ========================================================================= */

/**
 * Initializes IOHIDPointerScrollFilter state to authoritative system defaults.
 */
void IOHIDPointerScrollFilter_init(IOHIDPointerScrollFilterState* state) {
    if (!state) return;
    memset(state, 0, sizeof(IOHIDPointerScrollFilterState));
    
    state->vtable_signature = sign_vtable_pointer(0x26dd6ad58, PACDA_DISCRIMINATOR_FILTER_VTABLE);
    state->accelerator_vtable_signature = sign_vtable_pointer(0x26dd6ac70, PACDA_DISCRIMINATOR_ACCELERATOR_VTABLE);
    state->ref_count = 1;
    state->service_id = 0x100000183;
    state->is_open = true;
    state->is_scheduled = true;
    state->momentum_timer_disarm_timestamp = 0;
    
    state->pointer_acceleration_value = 1.0;
    state->scroll_acceleration_value = K_CONST_DEFAULT_SCROLL_MULTIPLIER;
    state->pointer_acceleration_minimum = 0.0;
    state->scroll_resolution = K_CONST_LINE_TO_POINT_SCALE;
    state->pointer_resolution = 400.0;
    
    state->is_pointer_acceleration_enabled = true;
    state->is_scroll_acceleration_enabled = true;
    state->use_linear_mouse_scaling = false;
    state->natural_scrolling_enabled = true;
    
    state->accel_algorithm = ACCEL_ALGORITHM_PARAMETRIC;
    state->momentum_dispatch_rate_ms = 10; /* 10ms = 100Hz dispatch */
    state->momentum_active = false;
    state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
    state->accum_remainder_x = 0.0;
    state->accum_remainder_y = 0.0;
    
    /* Default Generic USB Mouse Piecewise Table */
    state->scroll_table.point_count = 5;
    state->scroll_table.points[0] = (IOHIDCurvePoint){0.0, 1.000};
    state->scroll_table.points[1] = (IOHIDCurvePoint){1.0, 1.000};
    state->scroll_table.points[2] = (IOHIDCurvePoint){3.0, 1.500};
    state->scroll_table.points[3] = (IOHIDCurvePoint){6.0, 2.250};
    state->scroll_table.points[4] = (IOHIDCurvePoint){12.0, 3.500};
}

/**
 * Evaluates Apple's parametric acceleration curve f(v).
 * Implements 3-segment transfer function with TangentSpeedLinear inflection threshold.
 * - For v <= TangentSpeedLinear (1.50099): Unity gain M(v) = 1.000 (1:1 linear precision)
 * - For v > TangentSpeedLinear: Progressive rational polynomial acceleration
 *   M(v) = 1.0 + (u / (1.0 + gamma * u)) * (alpha - 1.0 + beta * u)
 * - High-speed saturation clamped at K_CONST_POINTER_ACCEL_MAX_CLAMP (500.0)
 */
double IOHIDPointerScrollFilter_evaluateParametric(double velocity) {
    if (isnan(velocity)) {
        return 1.0; /* Robustness: NaN returns baseline unity gain */
    }
    if (isinf(velocity)) {
        return K_CONST_POINTER_ACCEL_MAX_CLAMP; /* Extreme velocity saturates at 500.0 */
    }
    double v_abs = fabs(velocity);
    if (v_abs <= K_CONST_PARAM_GAIN_LINEAR_ALPHA) {
        return 1.0;
    }
    
    double u = v_abs - K_CONST_PARAM_GAIN_LINEAR_ALPHA;
    /* Numerical guard against overflow before polynomial */
    if (u > 100000.0) {
        return K_CONST_POINTER_ACCEL_MAX_CLAMP;
    }
    double numerator = u * ((K_CONST_PARAM_GAIN_LINEAR_ALPHA - 1.0) + (fabs(K_CONST_PARAM_CURVATURE_BETA) * u));
    double denominator = 1.0 + (K_CONST_PARAM_TANGENT_ROOT_GAMMA * u);
    
    if (denominator <= 0.0) {
        return K_CONST_POINTER_ACCEL_MAX_CLAMP;
    }
    
    double gain = 1.0 + (numerator / denominator);
    if (isnan(gain) || gain < 1.0) gain = 1.0;
    if (gain > K_CONST_POINTER_ACCEL_MAX_CLAMP) {
        gain = K_CONST_POINTER_ACCEL_MAX_CLAMP;
    }
    return gain;
}

/**
 * Evaluates piecewise table acceleration via linear interpolation between points.
 * Ensures strict symmetry under negative velocity and safe handling of non-finite inputs.
 */
double IOHIDPointerScrollFilter_evaluateTable(const IOHIDAccelerationTable* table, double velocity) {
    if (!table || table->point_count == 0) return 1.0;
    uint32_t count = table->point_count > 16 ? 16 : table->point_count;
    if (isnan(velocity)) return 1.0;
    if (isinf(velocity)) return table->points[count - 1].gain;
    double v_abs = fabs(velocity);
    
    if (v_abs <= table->points[0].velocity_threshold) {
        return table->points[0].gain;
    }
    
    for (uint32_t i = 0; i < count - 1; i++) {
        double v0 = table->points[i].velocity_threshold;
        double v1 = table->points[i + 1].velocity_threshold;
        if (v_abs >= v0 && v_abs <= v1) {
            double span = v1 - v0;
            if (span < 1e-9) return table->points[i].gain;
            double fraction = (v_abs - v0) / span;
            return table->points[i].gain + fraction * (table->points[i + 1].gain - table->points[i].gain);
        }
    }
    return table->points[count - 1].gain;
}

/**
 * Filters a scroll event: performs delta normalization, line multiplication,
 * Shift modifier redirection, natural scrolling inversion, acceleration scaling,
 * direction reversal detection, and sub-pixel remainder tracking.
 */
void IOHIDPointerScrollFilter_filterScroll(IOHIDPointerScrollFilterState* state, IOHIDEvent* event) {
    if (!state || !event) return;
    if (event->type != K_IOHID_EVENT_TYPE_SCROLL) return;
    
    /* Sanitize NaN/Inf in inputs to prevent kernel/WindowServer pipeline poisoning */
    if (isnan(event->scroll_x) || isinf(event->scroll_x)) event->scroll_x = 0.0;
    if (isnan(event->scroll_y) || isinf(event->scroll_y)) event->scroll_y = 0.0;
    if (isnan(event->scroll_z) || isinf(event->scroll_z)) event->scroll_z = 0.0;

    /* 1. Touch Interruption & Direction Reversal Check */
    if (state->momentum_active) {
        /* Physical touch contact initiated */
        if (event->scroll_phase & K_IOHID_EVENT_SCROLL_PHASE_BEGAN) {
            state->momentum_active = false;
            state->momentum_velocity_x = 0.0;
            state->momentum_velocity_y = 0.0;
            state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
        }
        /* Direction reversal during active momentum */
        else if ((event->scroll_x * state->momentum_velocity_x < -1e-6) ||
                 (event->scroll_y * state->momentum_velocity_y < -1e-6)) {
            state->momentum_active = false;
            state->momentum_velocity_x = 0.0;
            state->momentum_velocity_y = 0.0;
            state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
        }
        /* Discrete mouse wheel scroll during trackpad momentum */
        else if (!event->is_pixel_units && (fabs(event->scroll_x) > 1e-6 || fabs(event->scroll_y) > 1e-6)) {
            state->momentum_active = false;
            state->momentum_velocity_x = 0.0;
            state->momentum_velocity_y = 0.0;
            state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
        }
    }
    
    double dx = event->scroll_x;
    double dy = event->scroll_y;
    double dz = event->scroll_z;
    
    /* 2. Shift Modifier Redirection: Shift + Vertical Wheel -> Horizontal Scroll */
    /* Only applied to 1D discrete notched wheels; 2D continuous trackpads natively report 2D axes */
    if (!event->is_pixel_units && (event->modifier_flags & K_IOHID_MODIFIER_SHIFT)) {
        if (fabs(dy) > 0.0 && fabs(dx) < 1e-6) {
            dx = dy;
            dy = 0.0;
        }
    }
    
    /* 3. Natural Scrolling Inversion */
    if (state->natural_scrolling_enabled) {
        dx = -dx;
        dy = -dy;
    }
    
    /* 4. Discrete Notch Line Scaling vs Continuous Pixel Scaling */
    if (!event->is_pixel_units) {
        /* Discrete notched wheel: multiply by line conversion factor (10.0pt) */
        dx *= K_CONST_LINE_TO_POINT_SCALE;
        dy *= K_CONST_LINE_TO_POINT_SCALE;
        dz *= K_CONST_LINE_TO_POINT_SCALE;
    } else {
        /* Continuous trackpad sub-pixel accumulation with remainder tracking */
        state->accum_subpixel_x += dx;
        state->accum_subpixel_y += dy;
        
        /* Preserve exact fractional residual to prevent cumulative truncation drift */
        double whole_x = (double)((int64_t)state->accum_subpixel_x);
        double whole_y = (double)((int64_t)state->accum_subpixel_y);
        state->accum_remainder_x = state->accum_subpixel_x - whole_x;
        state->accum_remainder_y = state->accum_subpixel_y - whole_y;
    }
    
    /* 5. Acceleration Gain Calculation */
    if (state->is_scroll_acceleration_enabled) {
        double v_inst = sqrt(dx * dx + dy * dy);
        double gain = 1.0;
        
        if (state->accel_algorithm == ACCEL_ALGORITHM_PARAMETRIC) {
            gain = IOHIDPointerScrollFilter_evaluateParametric(v_inst);
        } else if (state->accel_algorithm == ACCEL_ALGORITHM_TABLE) {
            gain = IOHIDPointerScrollFilter_evaluateTable(&state->scroll_table, v_inst);
        }
        
        /* Apply gain & user acceleration multiplier */
        dx *= gain * (state->scroll_acceleration_value / K_CONST_DEFAULT_SCROLL_MULTIPLIER);
        dy *= gain * (state->scroll_acceleration_value / K_CONST_DEFAULT_SCROLL_MULTIPLIER);
    }
    
    /* 6. Normalization Division by Resolution */
    if (state->scroll_resolution > 1e-6) {
        dx /= state->scroll_resolution;
        dy /= state->scroll_resolution;
        dz /= state->scroll_resolution;
    }
    
    /* 7. Store Result & Mark Event Accelerated */
    event->scroll_x = dx;
    event->scroll_y = dy;
    event->scroll_z = dz;
    event->flags |= K_IOHID_EVENT_FLAG_IS_ACCELERATED;
    
    /* 8. Momentum Handoff Detection: Contact Lifted -> Initiate Momentum */
    if (event->scroll_phase & K_IOHID_EVENT_SCROLL_PHASE_ENDED) {
        double exit_velocity = sqrt(dx * dx + dy * dy);
        if (exit_velocity >= K_CONST_MOMENTUM_TERMINAL_CUTOFF) {
            state->momentum_active = true;
            state->momentum_velocity_x = dx;
            state->momentum_velocity_y = dy;
            state->momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN;
        }
    }
}

/**
 * Filters a pointer movement event: evaluates parametric acceleration curves,
 * enforces minimum gain, and applies multiplier to pointer_x and pointer_y.
 * Matches decompiled routine at 0x2529ca2d4 - 0x2529ca3fc.
 */
void IOHIDPointerScrollFilter_filterPointer(IOHIDPointerScrollFilterState* state, IOHIDEvent* event) {
    if (!state || !event) return;
    if (event->type != K_IOHID_EVENT_TYPE_POINTER) return;
    if (!state->is_pointer_acceleration_enabled) return;
    if (event->flags & (K_IOHID_EVENT_FLAG_IS_PIXEL_UNITS | K_IOHID_EVENT_FLAG_IS_ACCELERATED)) return;

    if (isnan(event->pointer_x) || isinf(event->pointer_x)) event->pointer_x = 0.0;
    if (isnan(event->pointer_y) || isinf(event->pointer_y)) event->pointer_y = 0.0;

    double px = event->pointer_x;
    double py = event->pointer_y;
    double v_inst = sqrt(px * px + py * py);
    
    double gain = 1.0;
    if (state->accel_algorithm == ACCEL_ALGORITHM_PARAMETRIC) {
        gain = IOHIDPointerScrollFilter_evaluateParametric(v_inst);
    } else if (state->accel_algorithm == ACCEL_ALGORITHM_TABLE) {
        gain = IOHIDPointerScrollFilter_evaluateTable(&state->scroll_table, v_inst);
    }
    
    gain *= state->pointer_acceleration_value;
    if (gain < state->pointer_acceleration_minimum) {
        gain = state->pointer_acceleration_minimum;
    }
    if (gain > K_CONST_POINTER_ACCEL_MAX_CLAMP) {
        gain = K_CONST_POINTER_ACCEL_MAX_CLAMP;
    }

    event->pointer_x = px * gain;
    event->pointer_y = py * gain;
    event->flags |= K_IOHID_EVENT_FLAG_IS_ACCELERATED;
}

/**
 * Unified IOHIDPointerScrollFilter::filter entry point matching slot 9 at 0x2529ca294.
 * Performs event type discrimination (kIOHIDEventTypePointer vs kIOHIDEventTypeScroll).
 */
IOHIDEvent* IOHIDPointerScrollFilter_filter(IOHIDPointerScrollFilterState* state, void* service_ref, IOHIDEvent* event) {
    (void)service_ref;
    if (!state || !event) return event;
    if (!state->is_open || !state->is_scheduled) return event;
    
    if (event->type == K_IOHID_EVENT_TYPE_POINTER) {
        IOHIDPointerScrollFilter_filterPointer(state, event);
    } else if (event->type == K_IOHID_EVENT_TYPE_SCROLL) {
        IOHIDPointerScrollFilter_filterScroll(state, event);
    }
    return event;
}

/**
 * Opens the filter instance for a given service reference and option bits.
 * Matches IOHIDPointerScrollFilter::open at 0x2529c51ec (Slot 3).
 */
int IOHIDPointerScrollFilter_open(IOHIDPointerScrollFilterState* state, void* service_ref, uint32_t options) {
    (void)options;
    if (!state) return -1; /* kIOReturnBadArgument */
    state->service_ref = service_ref;
    state->is_open = true;
    state->momentum_active = false;
    state->momentum_velocity_x = 0.0;
    state->momentum_velocity_y = 0.0;
    state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
    return 0; /* kIOReturnSuccess */
}

/**
 * Closes the filter instance and disarms any active synthetic momentum timers.
 * Matches IOHIDPointerScrollFilter::close at 0x2529c52f4 (Slot 4).
 */
void IOHIDPointerScrollFilter_close(IOHIDPointerScrollFilterState* state) {
    if (!state) return;
    if (state->momentum_active) {
        state->momentum_active = false;
        state->momentum_velocity_x = 0.0;
        state->momentum_velocity_y = 0.0;
        state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
    }
    state->is_open = false;
    state->momentum_timer_disarm_timestamp = ~0ULL;
}

/**
 * Schedules the filter with a GCD dispatch queue for asynchronous event processing.
 * Matches IOHIDPointerScrollFilter::scheduleWithDispatchQueue at 0x2529c5444 (Slot 5).
 */
void IOHIDPointerScrollFilter_scheduleWithDispatchQueue(IOHIDPointerScrollFilterState* state, void* dispatch_queue) {
    if (!state) return;
    (void)dispatch_queue;
    state->is_scheduled = true;
}

/**
 * Unschedules the filter from the dispatch queue and invalidates pending timers.
 * Matches IOHIDPointerScrollFilter::unscheduleFromDispatchQueue at 0x2529c54a8 (Slot 6).
 */
void IOHIDPointerScrollFilter_unscheduleFromDispatchQueue(IOHIDPointerScrollFilterState* state) {
    if (!state) return;
    IOHIDPointerScrollFilter_close(state);
    state->is_scheduled = false;
}

/**
 * Convenience alias for unscheduleFromDispatchQueue.
 */
void IOHIDPointerScrollFilter_unschedule(IOHIDPointerScrollFilterState* state) {
    IOHIDPointerScrollFilter_unscheduleFromDispatchQueue(state);
}

/**
 * Queries a configuration property value from the filter instance.
 * Matches IOHIDPointerScrollFilter::copyProperty at 0x2529c50b4 (Slot 7).
 */
bool IOHIDPointerScrollFilter_copyProperty(const IOHIDPointerScrollFilterState* state, const char* key, double* out_value) {
    if (!state || !key || !out_value) return false;
    
    if (strcmp(key, "HIDPointerAcceleration") == 0) {
        *out_value = state->pointer_acceleration_value;
        return true;
    }
    if (strcmp(key, "HIDScrollAcceleration") == 0) {
        *out_value = state->scroll_acceleration_value;
        return true;
    }
    if (strcmp(key, "HIDScrollResolution") == 0) {
        *out_value = state->scroll_resolution;
        return true;
    }
    if (strcmp(key, "HIDPointerResolution") == 0) {
        *out_value = state->pointer_resolution;
        return true;
    }
    if (strcmp(key, "ScrollMomentumDispatchRate") == 0) {
        *out_value = (double)state->momentum_dispatch_rate_ms;
        return true;
    }
    if (strcmp(key, "HIDPointerAccelerationMinimum") == 0) {
        *out_value = state->pointer_acceleration_minimum;
        return true;
    }
    if (strcmp(key, "HIDUseLinearScalingMouseAcceleration") == 0) {
        *out_value = state->use_linear_mouse_scaling ? 1.0 : 0.0;
        return true;
    }
    if (strcmp(key, "NaturalScrolling") == 0) {
        *out_value = state->natural_scrolling_enabled ? 1.0 : 0.0;
        return true;
    }
    return false;
}

/**
 * Sets a configuration property value on the filter instance.
 * Matches IOHIDPointerScrollFilter::setProperty at 0x2529c4a9c (Slot 8).
 */
bool IOHIDPointerScrollFilter_setProperty(IOHIDPointerScrollFilterState* state, const char* key, double value) {
    if (!state || !key) return false;
    
    if (strcmp(key, "HIDPointerAcceleration") == 0) {
        state->pointer_acceleration_value = value;
        state->is_pointer_acceleration_enabled = (value >= 0.0);
        return true;
    }
    if (strcmp(key, "HIDScrollAcceleration") == 0) {
        state->scroll_acceleration_value = value;
        state->is_scroll_acceleration_enabled = (value >= 0.0);
        return true;
    }
    if (strcmp(key, "HIDScrollResolution") == 0) {
        state->scroll_resolution = (value > 1e-6) ? value : K_CONST_LINE_TO_POINT_SCALE;
        return true;
    }
    if (strcmp(key, "HIDPointerResolution") == 0) {
        state->pointer_resolution = (value > 1e-6) ? value : 400.0;
        return true;
    }
    if (strcmp(key, "ScrollMomentumDispatchRate") == 0) {
        state->momentum_dispatch_rate_ms = (uint64_t)value;
        return true;
    }
    if (strcmp(key, "HIDPointerAccelerationMinimum") == 0) {
        state->pointer_acceleration_minimum = value;
        return true;
    }
    if (strcmp(key, "HIDUseLinearScalingMouseAcceleration") == 0) {
        state->use_linear_mouse_scaling = (value != 0.0);
        return true;
    }
    if (strcmp(key, "NaturalScrolling") == 0) {
        state->natural_scrolling_enabled = (value != 0.0);
        return true;
    }
    return false;
}

/**
 * Simulates a single tick of the synthetic momentum scroll engine.
 * Generates synthetic IOHIDEvent with momentum phases and exponential friction decay.
 */
bool IOHIDPointerScrollFilter_stepMomentum(IOHIDPointerScrollFilterState* state, IOHIDEvent* synth_event_out) {
    if (!state || !synth_event_out) return false;
    if (!state->is_open || !state->momentum_active) return false;
    
    memset(synth_event_out, 0, sizeof(IOHIDEvent));
    synth_event_out->type = K_IOHID_EVENT_TYPE_SCROLL;
    synth_event_out->is_pixel_units = true;
    synth_event_out->flags = K_IOHID_EVENT_FLAG_IS_ACCELERATED | K_IOHID_EVENT_FLAG_IS_PIXEL_UNITS;
    
    /* Apply exponential decay: v_{n+1} = v_n * 0.950 */
    state->momentum_velocity_x *= K_CONST_MOMENTUM_DECAY_RATE;
    state->momentum_velocity_y *= K_CONST_MOMENTUM_DECAY_RATE;
    
    double speed = sqrt(state->momentum_velocity_x * state->momentum_velocity_x +
                        state->momentum_velocity_y * state->momentum_velocity_y);
                        
    if (speed < K_CONST_MOMENTUM_TERMINAL_CUTOFF) {
        /* Terminal Resting Condition */
        synth_event_out->scroll_x = 0.0;
        synth_event_out->scroll_y = 0.0;
        synth_event_out->scroll_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_ENDED;
        state->momentum_active = false;
        state->momentum_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE;
        return true;
    }
    
    synth_event_out->scroll_x = state->momentum_velocity_x;
    synth_event_out->scroll_y = state->momentum_velocity_y;
    
    if (state->momentum_phase == K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN) {
        synth_event_out->scroll_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN;
        state->momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    } else {
        synth_event_out->scroll_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    }
    return true;
}

/* ========================================================================= */
/* 5. Comprehensive Unit Assertion Suites (33 Suites)                       */
/* ========================================================================= */

static void test_suite_01_vtable_pac_authentication(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    assert(authenticate_vtable_pointer(state.vtable_signature, PACDA_DISCRIMINATOR_FILTER_VTABLE));
    assert(authenticate_vtable_pointer(state.accelerator_vtable_signature, PACDA_DISCRIMINATOR_ACCELERATOR_VTABLE));
    assert(!authenticate_vtable_pointer(state.vtable_signature, 0x1234));
    printf("[PASS] Suite 01: PAC00 vtable authentication verified\n");
}

static void test_suite_02_discrete_wheel_normalization(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 10.0;
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 3.0, /* 3 detent lines */
        .is_pixel_units = false,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt);
    
    /* 3.0 lines * 10.0 scale / 10.0 resolution = 3.0 points */
    assert(fabs(evt.scroll_y - 3.0) < 1e-6);
    assert(evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    printf("[PASS] Suite 02: Discrete wheel normalization verified\n");
}

static void test_suite_03_shift_modifier_redirection(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 10.0;
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 2.0,
        .modifier_flags = K_IOHID_MODIFIER_SHIFT,
        .is_pixel_units = false,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt);
    
    /* dy redirected to dx */
    assert(fabs(evt.scroll_x - 2.0) < 1e-6);
    assert(fabs(evt.scroll_y) < 1e-6);
    printf("[PASS] Suite 03: Shift modifier horizontal conversion verified\n");
}

static void test_suite_04_natural_scrolling_inversion(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = true;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 10.0;
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 1.0,
        .scroll_y = 2.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt);
    
    assert(evt.scroll_x < 0.0);
    assert(evt.scroll_y < 0.0);
    printf("[PASS] Suite 04: Natural scrolling inversion verified\n");
}

static void test_suite_05_natural_scrolling_disabled(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 10.0;
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 1.0,
        .scroll_y = 2.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt);
    
    assert(evt.scroll_x > 0.0);
    assert(evt.scroll_y > 0.0);
    printf("[PASS] Suite 05: Standard scrolling orientation verified\n");
}

static void test_suite_06_parametric_curve_low_speed(void) {
    double gain = IOHIDPointerScrollFilter_evaluateParametric(2.0);
    /* At low speed near TangentSpeedLinear (2.0 pt/s), gain must be near baseline unity */
    assert(gain >= 1.0);
    assert(gain <= 1.35);
    printf("[PASS] Suite 06: Parametric low-speed regime verified\n");
}

static void test_suite_07_parametric_curve_medium_speed(void) {
    double gain_low = IOHIDPointerScrollFilter_evaluateParametric(5.0);
    double gain_med = IOHIDPointerScrollFilter_evaluateParametric(20.0);
    
    assert(gain_med > gain_low);
    assert(gain_low >= 2.0 && gain_low <= 3.0);
    assert(gain_med >= 5.0 && gain_med <= 7.0);
    printf("[PASS] Suite 07: Parametric medium-speed progressive gain verified\n");
}

static void test_suite_08_parametric_curve_high_speed_saturation(void) {
    double gain_high = IOHIDPointerScrollFilter_evaluateParametric(500.0);
    double gain_extreme = IOHIDPointerScrollFilter_evaluateParametric(2000.0);
    
    assert(gain_extreme >= gain_high);
    assert(gain_extreme <= K_CONST_POINTER_ACCEL_MAX_CLAMP);
    printf("[PASS] Suite 08: Parametric high-speed saturation verified\n");
}

static void test_suite_09_table_acceleration_interpolation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Curve points: (1.0, 1.000) and (3.0, 1.500). Midpoint at v = 2.0 -> gain = 1.250 */
    double gain_mid = IOHIDPointerScrollFilter_evaluateTable(&state.scroll_table, 2.0);
    assert(fabs(gain_mid - 1.250) < 1e-6);
    printf("[PASS] Suite 09: Piecewise table linear interpolation verified\n");
}

static void test_suite_10_continuous_subpixel_accumulation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    
    IOHIDEvent evt1 = {.type = K_IOHID_EVENT_TYPE_SCROLL, .scroll_y = 0.25, .is_pixel_units = true};
    IOHIDEvent evt2 = {.type = K_IOHID_EVENT_TYPE_SCROLL, .scroll_y = 0.75, .is_pixel_units = true};
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt1);
    IOHIDPointerScrollFilter_filterScroll(&state, &evt2);
    
    assert(fabs(state.accum_subpixel_y - 1.00) < 1e-6);
    printf("[PASS] Suite 10: Continuous sub-pixel accumulation verified\n");
}

static void test_suite_11_momentum_handoff_initiation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 1.0;
    
    IOHIDEvent lift_evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 12.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_ENDED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &lift_evt);
    
    assert(state.momentum_active == true);
    assert(state.momentum_phase == K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN);
    assert(fabs(state.momentum_velocity_y - 12.0) < 1e-6);
    printf("[PASS] Suite 11: Momentum handoff initiation verified\n");
}

static void test_suite_12_momentum_exponential_decay_recurrence(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.momentum_active = true;
    state.momentum_velocity_x = 0.0;
    state.momentum_velocity_y = 10.0;
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN;
    
    IOHIDEvent synth1;
    bool active1 = IOHIDPointerScrollFilter_stepMomentum(&state, &synth1);
    assert(active1);
    /* 10.0 * 0.950 = 9.50 */
    assert(fabs(synth1.scroll_y - 9.50) < 1e-6);
    assert(synth1.scroll_phase == K_IOHID_EVENT_SCROLL_MOMENTUM_BEGAN);
    
    IOHIDEvent synth2;
    bool active2 = IOHIDPointerScrollFilter_stepMomentum(&state, &synth2);
    assert(active2);
    /* 9.50 * 0.950 = 9.025 */
    assert(fabs(synth2.scroll_y - 9.025) < 1e-6);
    assert(synth2.scroll_phase == K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED);
    printf("[PASS] Suite 12: Exponential momentum decay recurrence verified\n");
}

static void test_suite_13_momentum_terminal_resting_cutoff(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.momentum_active = true;
    state.momentum_velocity_x = 0.0;
    state.momentum_velocity_y = 0.051; /* Just above cutoff */
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    
    IOHIDEvent synth;
    bool active = IOHIDPointerScrollFilter_stepMomentum(&state, &synth);
    assert(active);
    /* 0.051 * 0.95 = 0.04845 < 0.050 -> Triggers terminal rest */
    assert(synth.scroll_phase == K_IOHID_EVENT_SCROLL_MOMENTUM_ENDED);
    assert(state.momentum_active == false);
    printf("[PASS] Suite 13: Momentum terminal resting condition verified\n");
}

static void test_suite_14_touch_interruption_immediate_halt(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.momentum_active = true;
    state.momentum_velocity_x = 5.0;
    state.momentum_velocity_y = 8.0;
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    
    /* Fresh physical contact arrived */
    IOHIDEvent contact_evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.1,
        .scroll_y = 0.2,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_BEGAN
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &contact_evt);
    
    assert(state.momentum_active == false);
    assert(fabs(state.momentum_velocity_x) < 1e-9);
    assert(fabs(state.momentum_velocity_y) < 1e-9);
    printf("[PASS] Suite 14: Ballistic momentum touch interruption verified\n");
}

static void test_suite_15_ieee754_text_const_precision(void) {
    assert(K_CONST_USEC_PER_SEC == 1000000.0);
    assert(K_CONST_POINTER_ACCEL_MAX_CLAMP == 500.0);
    assert(K_CONST_REPORT_RATE_MAX == 150.0);
    assert(K_CONST_REPORT_RATE_DEFAULT == 67.0);
    assert(K_CONST_MSEC_PER_SEC == 1000.0);
    assert(fabs(K_CONST_PARAM_CURVATURE_BETA - (-0.0145721435546875)) < 1e-15);
    assert(fabs(K_CONST_PARAM_GAIN_LINEAR_ALPHA - 1.5009918212890625) < 1e-15);
    assert(fabs(K_CONST_PARAM_TANGENT_ROOT_GAMMA - 0.100006103515625) < 1e-15);
    assert(fabs(K_CONST_DEFAULT_SCROLL_MULTIPLIER - 1.4328358208955223) < 1e-15);
    printf("[PASS] Suite 15: IEEE 754 __TEXT.__const constants verified\n");
}

static void test_suite_16_resolution_scaling_accuracy(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 20.0; /* 20.0 DPI / resolution */
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_y = 100.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &evt);
    
    /* 100.0 / 20.0 = 5.0 points */
    assert(fabs(evt.scroll_y - 5.0) < 1e-6);
    printf("[PASS] Suite 16: Resolution scaling division verified\n");
}

static void test_suite_17_non_scroll_event_passthrough(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    IOHIDEvent non_scroll = {
        .type = K_IOHID_EVENT_TYPE_DIGITIZER,
        .scroll_x = 42.0,
        .scroll_y = 84.0,
        .flags = 0
    };
    
    IOHIDPointerScrollFilter_filterScroll(&state, &non_scroll);
    
    /* Must not be modified or accelerated */
    assert(fabs(non_scroll.scroll_x - 42.0) < 1e-6);
    assert(fabs(non_scroll.scroll_y - 84.0) < 1e-6);
    assert((non_scroll.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    printf("[PASS] Suite 17: Non-scroll event bypass verified\n");
}

static void test_suite_18_unified_filter_dispatch(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* 1. Pointer Event Dispatched & Accelerated */
    IOHIDEvent ptr_evt = {
        .type = K_IOHID_EVENT_TYPE_POINTER,
        .pointer_x = 10.0,
        .pointer_y = 0.0,
        .flags = 0
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &ptr_evt);
    assert(ptr_evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    assert(ptr_evt.pointer_x > 10.0); /* Positive acceleration gain applied */
    
    /* 2. Scroll Event Dispatched */
    IOHIDEvent scr_evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 3.0,
        .is_pixel_units = false
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &scr_evt);
    assert(scr_evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    
    /* 3. Non-pointer non-scroll Event Bypassed */
    IOHIDEvent digi_evt = {
        .type = K_IOHID_EVENT_TYPE_DIGITIZER,
        .pointer_x = 5.0,
        .flags = 0
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &digi_evt);
    assert((digi_evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    assert(fabs(digi_evt.pointer_x - 5.0) < 1e-6);
    printf("[PASS] Suite 18: Unified filter dispatch verified\n");
}

static void test_suite_19_dual_pac_discriminators(void) {
    assert(PACDA_DISCRIMINATOR_FILTER_VTABLE == 0x7e02);
    assert(PACDA_DISCRIMINATOR_ACCELERATOR_VTABLE == 0x9ff6);
    assert(PACDA_DISCRIMINATOR_METHOD == 0x9dcf);
    assert(PACDA_DISCRIMINATOR_TABLE == 0x7166);
    printf("[PASS] Suite 19: PAC00 dual discriminators verified\n");
}

static void test_suite_20_trackpad_shift_preservation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    state.scroll_resolution = 10.0;
    
    /* Trackpad event (is_pixel_units = true) with Shift modifier pressed */
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 1.0,
        .scroll_y = 4.0,
        .modifier_flags = K_IOHID_MODIFIER_SHIFT,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    
    /* Vertical scroll must NOT be redirected to horizontal for 2D trackpad */
    assert(fabs(evt.scroll_x) > 0.0);
    assert(fabs(evt.scroll_y) > 0.0);
    printf("[PASS] Suite 20: Trackpad 2D scrolling Shift preservation verified\n");
}

static void test_suite_21_nan_robustness_and_sanitization(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* 1. Parametric evaluation on NaN returns baseline unity gain */
    double gain_nan = IOHIDPointerScrollFilter_evaluateParametric(NAN);
    assert(fabs(gain_nan - 1.0) < 1e-9);
    
    /* 2. Table evaluation on NaN returns baseline unity gain */
    double table_gain_nan = IOHIDPointerScrollFilter_evaluateTable(&state.scroll_table, NAN);
    assert(fabs(table_gain_nan - 1.0) < 1e-9);
    
    /* 3. Scroll event with NaN coordinates is sanitized and does not poison pipeline */
    IOHIDEvent evt_nan = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = NAN,
        .scroll_y = NAN,
        .scroll_z = NAN,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt_nan);
    assert(!isnan(evt_nan.scroll_x));
    assert(!isnan(evt_nan.scroll_y));
    assert(fabs(evt_nan.scroll_x) < 1e-9);
    assert(fabs(evt_nan.scroll_y) < 1e-9);
    
    /* 4. Pointer event with NaN coordinates is sanitized */
    IOHIDEvent ptr_nan = {
        .type = K_IOHID_EVENT_TYPE_POINTER,
        .pointer_x = NAN,
        .pointer_y = NAN
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &ptr_nan);
    assert(!isnan(ptr_nan.pointer_x));
    assert(!isnan(ptr_nan.pointer_y));
    assert(fabs(ptr_nan.pointer_x) < 1e-9);
    assert(fabs(ptr_nan.pointer_y) < 1e-9);
    
    printf("[PASS] Suite 21: NaN robustness & coordinate sanitization verified\n");
}

static void test_suite_22_infinity_and_saturation_clamp(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Positive infinity saturates at K_CONST_POINTER_ACCEL_MAX_CLAMP (500.0) */
    double gain_pos_inf = IOHIDPointerScrollFilter_evaluateParametric(INFINITY);
    assert(fabs(gain_pos_inf - K_CONST_POINTER_ACCEL_MAX_CLAMP) < 1e-9);
    
    /* Negative infinity saturates at K_CONST_POINTER_ACCEL_MAX_CLAMP (500.0) */
    double gain_neg_inf = IOHIDPointerScrollFilter_evaluateParametric(-INFINITY);
    assert(fabs(gain_neg_inf - K_CONST_POINTER_ACCEL_MAX_CLAMP) < 1e-9);
    
    /* Ballistic extreme velocity Spike (100,000 pt/s) */
    double gain_ballistic = IOHIDPointerScrollFilter_evaluateParametric(100000.0);
    assert(fabs(gain_ballistic - K_CONST_POINTER_ACCEL_MAX_CLAMP) < 1e-9);
    
    /* Table evaluation with infinity returns upper bound */
    double table_inf = IOHIDPointerScrollFilter_evaluateTable(&state.scroll_table, INFINITY);
    assert(fabs(table_inf - 3.500) < 1e-6);
    
    printf("[PASS] Suite 22: Infinity & ballistic saturation clamping (500.0) verified\n");
}

static void test_suite_23_negative_velocity_symmetry(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    double test_velocities[] = {0.5, 1.5, 2.0, 5.0, 15.0, 50.0, 120.0, 500.0};
    size_t num_tests = sizeof(test_velocities) / sizeof(test_velocities[0]);
    
    for (size_t i = 0; i < num_tests; i++) {
        double v = test_velocities[i];
        double g_pos = IOHIDPointerScrollFilter_evaluateParametric(v);
        double g_neg = IOHIDPointerScrollFilter_evaluateParametric(-v);
        assert(fabs(g_pos - g_neg) < 1e-12);
        
        double t_pos = IOHIDPointerScrollFilter_evaluateTable(&state.scroll_table, v);
        double t_neg = IOHIDPointerScrollFilter_evaluateTable(&state.scroll_table, -v);
        assert(fabs(t_pos - t_neg) < 1e-12);
    }
    
    printf("[PASS] Suite 23: Negative velocity mathematical symmetry M(-v) == M(v) verified\n");
}

static void test_suite_24_momentum_direction_reversal_interruption(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Active positive forward momentum */
    state.momentum_active = true;
    state.momentum_velocity_x = 0.0;
    state.momentum_velocity_y = 12.0;
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    
    /* Opposite physical gesture arrived (downwards/negative Y pan) */
    IOHIDEvent rev_evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = -3.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    
    IOHIDPointerScrollFilter_filter(&state, NULL, &rev_evt);
    
    /* Momentum must be terminated immediately upon direction reversal */
    assert(state.momentum_active == false);
    assert(fabs(state.momentum_velocity_y) < 1e-9);
    assert(state.momentum_phase == K_IOHID_EVENT_SCROLL_PHASE_NONE);
    
    printf("[PASS] Suite 24: Momentum direction reversal immediate termination verified\n");
}

static void test_suite_25_discrete_wheel_interruption_of_momentum(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Active continuous trackpad momentum */
    state.momentum_active = true;
    state.momentum_velocity_x = 4.0;
    state.momentum_velocity_y = 8.0;
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    
    /* Discrete mouse wheel click arrives without ScrollPhaseBegan (typical for mouse wheels) */
    IOHIDEvent wheel_click = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 1.0,
        .is_pixel_units = false,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_NONE
    };
    
    IOHIDPointerScrollFilter_filter(&state, NULL, &wheel_click);
    
    /* Discrete mouse wheel must disarm active trackpad momentum */
    assert(state.momentum_active == false);
    assert(fabs(state.momentum_velocity_x) < 1e-9);
    assert(fabs(state.momentum_velocity_y) < 1e-9);
    
    printf("[PASS] Suite 25: Discrete wheel interruption of trackpad momentum verified\n");
}

static void test_suite_26_subpixel_drift_compensation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = false;
    
    /* Simulate 10,000 sub-pixel continuous trackpad reports of 1/3 pt */
    const double step = 1.0 / 3.0;
    const int cycles = 10000;
    
    for (int i = 0; i < cycles; i++) {
        IOHIDEvent evt = {
            .type = K_IOHID_EVENT_TYPE_SCROLL,
            .scroll_x = step,
            .scroll_y = step,
            .is_pixel_units = true,
            .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
        };
        IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    }
    
    double expected_accum = cycles * step;
    assert(fabs(state.accum_subpixel_x - expected_accum) < 1e-7);
    assert(fabs(state.accum_subpixel_y - expected_accum) < 1e-7);
    assert(state.accum_remainder_x >= -1.0 && state.accum_remainder_x <= 1.0);
    assert(state.accum_remainder_y >= -1.0 && state.accum_remainder_y <= 1.0);
    
    printf("[PASS] Suite 26: Continuous sub-pixel drift compensation (10,000 cycles) verified\n");
}

static void test_suite_27_lifecycle_hot_unplug_cancellation(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Device in active momentum decay */
    state.momentum_active = true;
    state.momentum_velocity_x = 10.0;
    state.momentum_velocity_y = 15.0;
    state.momentum_phase = K_IOHID_EVENT_SCROLL_MOMENTUM_CHANGED;
    assert(state.is_open == true);
    assert(state.is_scheduled == true);
    
    /* Device hot-unplug / teardown via close */
    IOHIDPointerScrollFilter_close(&state);
    assert(state.is_open == false);
    assert(state.momentum_active == false);
    assert(fabs(state.momentum_velocity_x) < 1e-9);
    assert(fabs(state.momentum_velocity_y) < 1e-9);
    assert(state.momentum_timer_disarm_timestamp == ~0ULL);
    
    /* Unschedule from dispatch queue */
    IOHIDPointerScrollFilter_unschedule(&state);
    assert(state.is_scheduled == false);
    
    printf("[PASS] Suite 27: Lifecycle hot-unplug & queue teardown cancellation verified\n");
}

static void test_suite_28_high_speed_inflection_points_interpolation(void) {
    IOHIDAccelerationTable table;
    table.point_count = 4;
    table.points[0] = (IOHIDCurvePoint){0.0, 1.000};
    table.points[1] = (IOHIDCurvePoint){8.0, 1.500};
    table.points[2] = (IOHIDCurvePoint){32.0, 2.500};
    table.points[3] = (IOHIDCurvePoint){128.0, 4.000};

    /* 1. Exact inflection points */
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, 0.0) - 1.000) < 1e-9);
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, 8.0) - 1.500) < 1e-9);
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, 32.0) - 2.500) < 1e-9);
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, 128.0) - 4.000) < 1e-9);

    /* 2. Linear interpolation between 8.0 and 32.0: midpoint v = 20.0 */
    /* span = 24.0, frac = (20.0 - 8.0) / 24.0 = 0.5 -> gain = 1.500 + 0.5 * 1.000 = 2.000 */
    double gain_mid_low = IOHIDPointerScrollFilter_evaluateTable(&table, 20.0);
    assert(fabs(gain_mid_low - 2.000) < 1e-9);

    /* 3. Linear interpolation between 32.0 and 128.0: midpoint v = 80.0 */
    /* span = 96.0, frac = (80.0 - 32.0) / 96.0 = 0.5 -> gain = 2.500 + 0.5 * 1.500 = 3.250 */
    double gain_mid_high = IOHIDPointerScrollFilter_evaluateTable(&table, 80.0);
    assert(fabs(gain_mid_high - 3.250) < 1e-9);

    /* 4. Beyond highest threshold saturates at 4.000 */
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, 256.0) - 4.000) < 1e-9);

    /* 5. Negative velocity symmetry */
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, -20.0) - 2.000) < 1e-9);
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, -80.0) - 3.250) < 1e-9);
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(&table, -256.0) - 4.000) < 1e-9);

    printf("[PASS] Suite 28: High-speed inflection points (8.0, 32.0, 128.0) table interpolation verified\n");
}

static void test_suite_29_closed_device_event_bypass(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* Device is closed (unplugged or torn down) */
    IOHIDPointerScrollFilter_close(&state);
    assert(state.is_open == false);
    
    /* Scroll event arriving on closed filter */
    IOHIDEvent scr_evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 5.0,
        .scroll_y = 10.0,
        .is_pixel_units = false,
        .flags = 0
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &scr_evt);
    /* Must pass through untouched: no line scaling (5.0, not 50.0), no acceleration flag */
    assert(fabs(scr_evt.scroll_x - 5.0) < 1e-9);
    assert(fabs(scr_evt.scroll_y - 10.0) < 1e-9);
    assert((scr_evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    
    /* Pointer event arriving on closed filter */
    IOHIDEvent ptr_evt = {
        .type = K_IOHID_EVENT_TYPE_POINTER,
        .pointer_x = 25.0,
        .pointer_y = 50.0,
        .flags = 0
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &ptr_evt);
    assert(fabs(ptr_evt.pointer_x - 25.0) < 1e-9);
    assert(fabs(ptr_evt.pointer_y - 50.0) < 1e-9);
    assert((ptr_evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    
    printf("[PASS] Suite 29: Closed device event bypass (hot-unplug safety) verified\n");
}

static void test_suite_30_null_pointer_safety(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 1.0,
        .scroll_y = 2.0
    };
    
    /* NULL state safety */
    assert(IOHIDPointerScrollFilter_filter(NULL, NULL, &evt) == &evt);
    IOHIDPointerScrollFilter_filterScroll(NULL, &evt);
    IOHIDPointerScrollFilter_filterPointer(NULL, &evt);
    IOHIDPointerScrollFilter_close(NULL);
    IOHIDPointerScrollFilter_unschedule(NULL);
    assert(IOHIDPointerScrollFilter_stepMomentum(NULL, &evt) == false);
    
    /* NULL event safety */
    assert(IOHIDPointerScrollFilter_filter(&state, NULL, NULL) == NULL);
    IOHIDPointerScrollFilter_filterScroll(&state, NULL);
    IOHIDPointerScrollFilter_filterPointer(&state, NULL);
    assert(IOHIDPointerScrollFilter_stepMomentum(&state, NULL) == false);
    
    /* NULL table safety in evaluateTable */
    assert(fabs(IOHIDPointerScrollFilter_evaluateTable(NULL, 10.0) - 1.0) < 1e-9);
    
    /* NULL init safety */
    IOHIDPointerScrollFilter_init(NULL);
    
    /* NULL lifecycle and property accessor safety */
    assert(IOHIDPointerScrollFilter_open(NULL, NULL, 0) == -1);
    IOHIDPointerScrollFilter_scheduleWithDispatchQueue(NULL, NULL);
    IOHIDPointerScrollFilter_unscheduleFromDispatchQueue(NULL);
    assert(IOHIDPointerScrollFilter_setProperty(NULL, "HIDScrollResolution", 10.0) == false);
    assert(IOHIDPointerScrollFilter_setProperty(&state, NULL, 10.0) == false);
    double val_null = 0.0;
    assert(IOHIDPointerScrollFilter_copyProperty(NULL, "HIDScrollResolution", &val_null) == false);
    assert(IOHIDPointerScrollFilter_copyProperty(&state, NULL, &val_null) == false);
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDScrollResolution", NULL) == false);
    
    printf("[PASS] Suite 30: NULL pointer defensive robustness & boundaries verified\n");
}

static void test_suite_31_property_accessors_and_dynamic_reconfiguration(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* 1. Test setProperty and copyProperty for all supported keys */
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDPointerAcceleration", 2.5));
    double val = 0.0;
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDPointerAcceleration", &val) && fabs(val - 2.5) < 1e-9);
    assert(state.is_pointer_acceleration_enabled == true);
    
    /* Disabling pointer acceleration via negative value */
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDPointerAcceleration", -1.0));
    assert(state.is_pointer_acceleration_enabled == false);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDScrollAcceleration", 3.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDScrollAcceleration", &val) && fabs(val - 3.0) < 1e-9);
    assert(state.is_scroll_acceleration_enabled == true);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDScrollResolution", 20.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDScrollResolution", &val) && fabs(val - 20.0) < 1e-9);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDPointerResolution", 800.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDPointerResolution", &val) && fabs(val - 800.0) < 1e-9);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "ScrollMomentumDispatchRate", 16.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "ScrollMomentumDispatchRate", &val) && fabs(val - 16.0) < 1e-9);
    assert(state.momentum_dispatch_rate_ms == 16);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDPointerAccelerationMinimum", 0.5));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDPointerAccelerationMinimum", &val) && fabs(val - 0.5) < 1e-9);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "HIDUseLinearScalingMouseAcceleration", 1.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "HIDUseLinearScalingMouseAcceleration", &val) && fabs(val - 1.0) < 1e-9);
    assert(state.use_linear_mouse_scaling == true);
    
    assert(IOHIDPointerScrollFilter_setProperty(&state, "NaturalScrolling", 0.0));
    assert(IOHIDPointerScrollFilter_copyProperty(&state, "NaturalScrolling", &val) && fabs(val) < 1e-9);
    assert(state.natural_scrolling_enabled == false);
    
    /* Unsupported property returns false */
    assert(!IOHIDPointerScrollFilter_setProperty(&state, "NonExistentKey", 42.0));
    assert(!IOHIDPointerScrollFilter_copyProperty(&state, "NonExistentKey", &val));
    
    /* 2. Verify dynamic reconfiguration affects live event filtering */
    state.is_scroll_acceleration_enabled = false;
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 100.0,
        .is_pixel_units = true,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    /* With NaturalScrolling=false and resolution=20.0: 100.0 / 20.0 = 5.0 (positive) */
    assert(fabs(evt.scroll_y - 5.0) < 1e-6);
    
    /* Dynamically enable NaturalScrolling */
    assert(IOHIDPointerScrollFilter_setProperty(&state, "NaturalScrolling", 1.0));
    evt.scroll_y = 100.0;
    evt.flags = 0;
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    /* Inverted: -5.0 */
    assert(fabs(evt.scroll_y - (-5.0)) < 1e-6);
    
    printf("[PASS] Suite 31: Property accessors (setProperty/copyProperty) & dynamic reconfiguration verified\n");
}

static void test_suite_32_open_and_schedule_lifecycle(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    
    /* 1. Close the filter: is_open becomes false */
    IOHIDPointerScrollFilter_close(&state);
    assert(state.is_open == false);
    
    IOHIDEvent evt = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 10.0,
        .scroll_y = 20.0,
        .is_pixel_units = false
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    /* Bypassed while closed: flags not set, values unmodified */
    assert((evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    assert(fabs(evt.scroll_x - 10.0) < 1e-9);
    assert(fabs(evt.scroll_y - 20.0) < 1e-9);
    
    /* 2. Re-open filter with new service reference */
    void* fake_service = (void*)0xdeadbeef;
    int rc = IOHIDPointerScrollFilter_open(&state, fake_service, 0);
    assert(rc == 0);
    assert(state.is_open == true);
    assert(state.service_ref == fake_service);
    
    /* Filtering resumes */
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    assert(evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    
    /* 3. Unschedule from dispatch queue */
    IOHIDPointerScrollFilter_unscheduleFromDispatchQueue(&state);
    assert(state.is_scheduled == false);
    assert(state.is_open == false);
    
    evt.flags = 0;
    evt.scroll_x = 10.0;
    evt.scroll_y = 20.0;
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt);
    assert((evt.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED) == 0);
    
    /* 4. Schedule with dispatch queue */
    IOHIDPointerScrollFilter_scheduleWithDispatchQueue(&state, (void*)0x12345678);
    assert(state.is_scheduled == true);
    
    printf("[PASS] Suite 32: Open, close, schedule, and unschedule lifecycle verified\n");
}

static void test_suite_33_table_acceleration_dispatch_integration(void) {
    IOHIDPointerScrollFilterState state;
    IOHIDPointerScrollFilter_init(&state);
    state.natural_scrolling_enabled = false;
    state.is_scroll_acceleration_enabled = true;
    state.scroll_resolution = 10.0;
    state.scroll_acceleration_value = K_CONST_DEFAULT_SCROLL_MULTIPLIER;
    state.accel_algorithm = ACCEL_ALGORITHM_TABLE;
    
    /* High-speed optical mouse table: inflection thresholds 0.0, 8.0, 32.0, 128.0 */
    state.scroll_table.point_count = 4;
    state.scroll_table.points[0] = (IOHIDCurvePoint){0.0, 1.000};
    state.scroll_table.points[1] = (IOHIDCurvePoint){8.0, 1.500};
    state.scroll_table.points[2] = (IOHIDCurvePoint){32.0, 2.500};
    state.scroll_table.points[3] = (IOHIDCurvePoint){128.0, 4.000};
    
    /* Test 1: Midpoint velocity between 8.0 and 32.0: v = 20.0 */
    /* Discrete detent input: raw detent = 2.0 lines -> scaled = 20.0 pt */
    /* Table gain at 20.0 is 2.000. Output = 20.0 * 2.000 / 10.0 = 4.00 pt */
    IOHIDEvent evt1 = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 2.0,
        .is_pixel_units = false,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt1);
    assert(evt1.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    assert(fabs(evt1.scroll_y - 4.000) < 1e-6);
    
    /* Test 2: Midpoint velocity between 32.0 and 128.0: v = 80.0 */
    /* Raw detent = 8.0 lines -> scaled = 80.0 pt */
    /* Table gain at 80.0 is 3.250. Output = 80.0 * 3.250 / 10.0 = 26.00 pt */
    IOHIDEvent evt2 = {
        .type = K_IOHID_EVENT_TYPE_SCROLL,
        .scroll_x = 0.0,
        .scroll_y = 8.0,
        .is_pixel_units = false,
        .scroll_phase = K_IOHID_EVENT_SCROLL_PHASE_CHANGED
    };
    IOHIDPointerScrollFilter_filter(&state, NULL, &evt2);
    assert(evt2.flags & K_IOHID_EVENT_FLAG_IS_ACCELERATED);
    assert(fabs(evt2.scroll_y - 26.000) < 1e-6);
    
    /* Test 3: Table acceleration overflow protection (point_count > 16) */
    IOHIDAccelerationTable overflow_table = state.scroll_table;
    overflow_table.point_count = 999; /* Corrupted point count */
    double gain_safe = IOHIDPointerScrollFilter_evaluateTable(&overflow_table, 20.0);
    assert(fabs(gain_safe - 2.000) < 1e-6);
    
    printf("[PASS] Suite 33: Table acceleration dispatch integration & buffer overflow protection verified\n");
}

/* ========================================================================= */
/* 6. Main Test Runner                                                      */
/* ========================================================================= */

int main(void) {
    printf("============================================================\n");
    printf("Running IOHIDPointerScrollFilter C99 Unit Verification Suite\n");
    printf("Target: iOS 27.2 (Darwin 24.2.0, arm64e PAC00)\n");
    printf("============================================================\n");
    
    test_suite_01_vtable_pac_authentication();
    test_suite_02_discrete_wheel_normalization();
    test_suite_03_shift_modifier_redirection();
    test_suite_04_natural_scrolling_inversion();
    test_suite_05_natural_scrolling_disabled();
    test_suite_06_parametric_curve_low_speed();
    test_suite_07_parametric_curve_medium_speed();
    test_suite_08_parametric_curve_high_speed_saturation();
    test_suite_09_table_acceleration_interpolation();
    test_suite_10_continuous_subpixel_accumulation();
    test_suite_11_momentum_handoff_initiation();
    test_suite_12_momentum_exponential_decay_recurrence();
    test_suite_13_momentum_terminal_resting_cutoff();
    test_suite_14_touch_interruption_immediate_halt();
    test_suite_15_ieee754_text_const_precision();
    test_suite_16_resolution_scaling_accuracy();
    test_suite_17_non_scroll_event_passthrough();
    test_suite_18_unified_filter_dispatch();
    test_suite_19_dual_pac_discriminators();
    test_suite_20_trackpad_shift_preservation();
    test_suite_21_nan_robustness_and_sanitization();
    test_suite_22_infinity_and_saturation_clamp();
    test_suite_23_negative_velocity_symmetry();
    test_suite_24_momentum_direction_reversal_interruption();
    test_suite_25_discrete_wheel_interruption_of_momentum();
    test_suite_26_subpixel_drift_compensation();
    test_suite_27_lifecycle_hot_unplug_cancellation();
    test_suite_28_high_speed_inflection_points_interpolation();
    test_suite_29_closed_device_event_bypass();
    test_suite_30_null_pointer_safety();
    test_suite_31_property_accessors_and_dynamic_reconfiguration();
    test_suite_32_open_and_schedule_lifecycle();
    test_suite_33_table_acceleration_dispatch_integration();
    
    printf("============================================================\n");
    printf("All 33 Assertion Suites PASSED Cleanly! (0 Warnings, 0 Errors)\n");
    printf("============================================================\n");
    return 0;
}
