/**
 * @file springboard_layout_solver.c
 * @brief Clean-room C99 layout solver and numerical integrator for SpringBoard Compositor
 *
 * Implementations:
 * 1. Dynamic Island pill split coordinate calculator (Hardware cutout x=196.5, y=11.0, W=120.0, H=35.0;
 *    Mode 1 Leading x=151.17, Trailing x=324.83; Expanded HUD Mode 3; Minimal Mode 2).
 * 2. Fluid Switcher card scale calculator (Scale(i) = 1.0 - i * 0.082 clamped to >= 0.65, depth z(i) = -i * 40.0 pt).
 * 3. Velocity-preserving spring curve numerical integrator (zeta=0.88, k=380.0 N/m, preserving release v0).
 * 4. Window level sorting and hit-test arbitration function.
 * 5. Main test execution routine with comprehensive assert() validation.
 *
 * Standard: ISO C99 (-Wall -Wextra -Werror -std=c99 -pedantic -lm)
 */

#include "springboard_compositor_interface.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>

/* Helper macro for floating-point comparison */
#define SB_FEQUAL(a, b, eps) (fabs((a) - (b)) <= (eps))

/* =========================================================================
 * Geometry Helpers
 * ========================================================================= */

sb_rect_t sb_rect_make(double x, double y, double width, double height) {
    sb_rect_t r;
    r.origin.x = x;
    r.origin.y = y;
    r.size.width = width;
    r.size.height = height;
    return r;
}

bool sb_rect_contains_point(sb_rect_t rect, sb_point_t point) {
    return (point.x >= rect.origin.x &&
            point.x <= (rect.origin.x + rect.size.width) &&
            point.y >= rect.origin.y &&
            point.y <= (rect.origin.y + rect.size.height));
}

/* =========================================================================
 * 1. Dynamic Island Layout Solver
 * ========================================================================= */

bool sb_solve_island_layout(
    sb_island_layout_mode_t mode,
    uint32_t primary_id,
    uint32_t secondary_id,
    sb_island_layout_result_t *out_layout
) {
    if (!out_layout) {
        return false;
    }

    memset(out_layout, 0, sizeof(*out_layout));
    out_layout->layout_mode = mode;
    out_layout->primary_element_id = primary_id;
    out_layout->secondary_element_id = secondary_id;

    switch (mode) {
        case SB_ISLAND_MODE_COMPACT_SINGLE: {
            /* Mode 0: Continuous pill seamlessly enclosing physical sensor cutout */
            out_layout->container_frame = sb_rect_make(
                SB_HARDWARE_CUTOUT_X,
                SB_HARDWARE_CUTOUT_Y,
                SB_HARDWARE_CUTOUT_WIDTH,
                SB_HARDWARE_CUTOUT_HEIGHT
            );
            out_layout->leading_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->trailing_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->minimal_bubble_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->expanded_hud_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->corner_radius = SB_HARDWARE_CUTOUT_RADIUS;
            out_layout->pill_split_active = false;
            return true;
        }

        case SB_ISLAND_MODE_COMPACT_SPLIT: {
            /* Mode 1: Split pill with Leading sub-pill and Trailing sub-pill separated by sensor void */
            double lead_x = SB_ISLAND_SPLIT_LEADING_X;   /* 151.17 pt */
            double trail_x = SB_ISLAND_SPLIT_TRAILING_X; /* 324.83 pt */
            double y = SB_HARDWARE_CUTOUT_Y;             /* 11.00 pt */
            double w_lead = SB_ISLAND_SPLIT_LEADING_WIDTH;   /* 37.00 pt */
            double h_lead = SB_ISLAND_SPLIT_LEADING_HEIGHT;  /* 35.00 pt */
            double w_trail = SB_ISLAND_SPLIT_TRAILING_WIDTH; /* 37.00 pt */
            double h_trail = SB_ISLAND_SPLIT_TRAILING_HEIGHT;/* 35.00 pt */

            out_layout->leading_pill_frame = sb_rect_make(lead_x, y, w_lead, h_lead);
            out_layout->trailing_pill_frame = sb_rect_make(trail_x, y, w_trail, h_trail);
            out_layout->minimal_bubble_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->expanded_hud_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);

            /* Container bounds enclosing both sub-pills */
            double total_w = (trail_x + w_trail) - lead_x;
            out_layout->container_frame = sb_rect_make(lead_x, y, total_w, h_lead);
            out_layout->corner_radius = SB_HARDWARE_CUTOUT_RADIUS;
            out_layout->pill_split_active = true;
            return true;
        }

        case SB_ISLAND_MODE_MINIMAL: {
            /* Mode 2: Minimal secondary bubble attached to trailing side of sensor cutout */
            double lead_x = SB_HARDWARE_CUTOUT_X;
            double y = SB_HARDWARE_CUTOUT_Y;
            double w_lead = SB_HARDWARE_CUTOUT_WIDTH;
            double h_lead = SB_HARDWARE_CUTOUT_HEIGHT;

            double bubble_x = SB_ISLAND_SPLIT_TRAILING_X;
            double bubble_w = SB_ISLAND_MINIMAL_WIDTH;
            double bubble_h = SB_ISLAND_MINIMAL_HEIGHT;

            out_layout->leading_pill_frame = sb_rect_make(lead_x, y, w_lead, h_lead);
            out_layout->trailing_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->minimal_bubble_frame = sb_rect_make(bubble_x, y, bubble_w, bubble_h);
            out_layout->expanded_hud_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);

            double total_w = (bubble_x + bubble_w) - lead_x;
            out_layout->container_frame = sb_rect_make(lead_x, y, total_w, h_lead);
            out_layout->corner_radius = SB_ISLAND_MINIMAL_RADIUS;
            out_layout->pill_split_active = true;
            return true;
        }

        case SB_ISLAND_MODE_EXPANDED: {
            /* Mode 3: Expanded HUD card centered horizontally */
            double x = SB_ISLAND_EXPANDED_X; /* 36.00 pt */
            double y = SB_ISLAND_EXPANDED_Y; /* 11.00 pt */
            double w = SB_ISLAND_EXPANDED_WIDTH;          /* 368.00 pt */
            double h = SB_ISLAND_EXPANDED_DEFAULT_HEIGHT; /* 160.00 pt */

            out_layout->expanded_hud_frame = sb_rect_make(x, y, w, h);
            out_layout->container_frame = out_layout->expanded_hud_frame;
            out_layout->leading_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->trailing_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->minimal_bubble_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->corner_radius = SB_ISLAND_EXPANDED_CORNER_RADIUS;
            out_layout->pill_split_active = false;
            return true;
        }

        case SB_ISLAND_MODE_STAGED_ALERT: {
            /* Mode 4: High-priority system alert (Face ID, Apple Pay) */
            double x = SB_ISLAND_EXPANDED_X;
            double y = SB_ISLAND_EXPANDED_Y;
            double w = SB_ISLAND_EXPANDED_WIDTH;
            double h = SB_ISLAND_EXPANDED_MAX_HEIGHT; /* 214.00 pt */

            out_layout->expanded_hud_frame = sb_rect_make(x, y, w, h);
            out_layout->container_frame = out_layout->expanded_hud_frame;
            out_layout->leading_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->trailing_pill_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->minimal_bubble_frame = sb_rect_make(0.0, 0.0, 0.0, 0.0);
            out_layout->corner_radius = SB_ISLAND_EXPANDED_CORNER_RADIUS;
            out_layout->pill_split_active = false;
            return true;
        }

        default:
            return false;
    }
}

/* =========================================================================
 * 2. Fluid Switcher Card Scale & Depth Calculator
 * ========================================================================= */

bool sb_solve_switcher_card_geometry(
    uint32_t app_index,
    double *out_scale,
    double *out_z_depth
) {
    if (!out_scale || !out_z_depth) {
        return false;
    }

    double scale = 1.0 - ((double)app_index * SB_FLUID_SWITCHER_SCALE_DECAY);
    if (scale < SB_FLUID_SWITCHER_MIN_SCALE) {
        scale = SB_FLUID_SWITCHER_MIN_SCALE;
    }

    double z_depth = -((double)app_index * SB_FLUID_SWITCHER_DEPTH_STEP);

    *out_scale = scale;
    *out_z_depth = z_depth;
    return true;
}

/* =========================================================================
 * 3. Velocity-Preserving Spring Physics Solver & RK4 Integrator
 * ========================================================================= */

bool sb_spring_init(
    const sb_spring_parameters_t *params,
    sb_spring_state_t *out_state
) {
    if (!params || !out_state) {
        return false;
    }

    if (params->mass <= 0.0 || params->stiffness <= 0.0 || params->damping_ratio < 0.0) {
        return false;
    }

    memset(out_state, 0, sizeof(*out_state));
    out_state->mass = params->mass;
    out_state->stiffness = params->stiffness;
    out_state->damping_ratio = params->damping_ratio;

    /* Natural angular frequency omega_n = sqrt(k / m) */
    out_state->undamped_frequency = sqrt(out_state->stiffness / out_state->mass);

    /* Damping coefficient c = 2 * zeta * sqrt(k * m) */
    out_state->damping_coeff = 2.0 * out_state->damping_ratio * sqrt(out_state->stiffness * out_state->mass);

    /* Damped angular frequency omega_d = omega_n * sqrt(1 - zeta^2) for underdamped (zeta < 1.0) */
    if (out_state->damping_ratio < 1.0) {
        double underdamped_radicand = 1.0 - (out_state->damping_ratio * out_state->damping_ratio);
        out_state->damped_frequency = out_state->undamped_frequency * sqrt(underdamped_radicand);
    } else {
        out_state->damped_frequency = 0.0;
    }

    out_state->initial_position = params->initial_position;
    out_state->initial_velocity = params->initial_velocity;
    out_state->position = params->initial_position;
    out_state->velocity = params->initial_velocity;
    out_state->elapsed_time = 0.0;
    out_state->is_settled = false;

    return true;
}

bool sb_spring_evaluate_analytical(
    const sb_spring_state_t *state,
    double time_sec,
    double *out_position,
    double *out_velocity
) {
    if (!state || !out_position || !out_velocity || time_sec < 0.0) {
        return false;
    }

    double zeta = state->damping_ratio;
    double wn = state->undamped_frequency;
    double wd = state->damped_frequency;
    double x0 = state->initial_position;
    double v0 = state->initial_velocity;

    if (zeta < 1.0 && wd > 0.0) {
        /* Underdamped analytical closed-form solution */
        double decay = exp(-zeta * wn * time_sec);
        double cos_val = cos(wd * time_sec);
        double sin_val = sin(wd * time_sec);
        double c2 = (v0 + (zeta * wn * x0)) / wd;

        double pos = decay * ((x0 * cos_val) + (c2 * sin_val));

        /* Derivative: v(t) = d/dt [ x(t) ] */
        double term_bracket = (x0 * cos_val) + (c2 * sin_val);
        double term_deriv = (-x0 * wd * sin_val) + (c2 * wd * cos_val);
        double vel = (-zeta * wn * decay * term_bracket) + (decay * term_deriv);

        *out_position = pos;
        *out_velocity = vel;
        return true;
    }

    /* Fallback for critically damped or overdamped */
    double decay = exp(-wn * time_sec);
    *out_position = decay * (x0 + ((v0 + wn * x0) * time_sec));
    *out_velocity = decay * (v0 - (wn * (v0 + wn * x0) * time_sec));
    return true;
}

/* Helper for state derivative: dx/dt = v, dv/dt = -(c*v + k*x)/m */
static void sb_spring_derivatives(
    double mass,
    double stiffness,
    double damping_coeff,
    double x,
    double v,
    double *dx_dt,
    double *dv_dt
) {
    *dx_dt = v;
    *dv_dt = -(damping_coeff * v + stiffness * x) / mass;
}

bool sb_spring_integrate_rk4(
    sb_spring_state_t *state,
    double dt
) {
    if (!state || dt <= 0.0) {
        return false;
    }

    double m = state->mass;
    double k = state->stiffness;
    double c = state->damping_coeff;

    double x = state->position;
    double v = state->velocity;

    /* RK4 Step 1: at start of interval */
    double k1_x, k1_v;
    sb_spring_derivatives(m, k, c, x, v, &k1_x, &k1_v);

    /* RK4 Step 2: at midpoint using k1 */
    double x_k2 = x + 0.5 * dt * k1_x;
    double v_k2 = v + 0.5 * dt * k1_v;
    double k2_x, k2_v;
    sb_spring_derivatives(m, k, c, x_k2, v_k2, &k2_x, &k2_v);

    /* RK4 Step 3: at midpoint using k2 */
    double x_k3 = x + 0.5 * dt * k2_x;
    double v_k3 = v + 0.5 * dt * k2_v;
    double k3_x, k3_v;
    sb_spring_derivatives(m, k, c, x_k3, v_k3, &k3_x, &k3_v);

    /* RK4 Step 4: at end of interval using k3 */
    double x_k4 = x + dt * k3_x;
    double v_k4 = v + dt * k3_v;
    double k4_x, k4_v;
    sb_spring_derivatives(m, k, c, x_k4, v_k4, &k4_x, &k4_v);

    /* Weighted combination */
    state->position = x + (dt / 6.0) * (k1_x + (2.0 * k2_x) + (2.0 * k3_x) + k4_x);
    state->velocity = v + (dt / 6.0) * (k1_v + (2.0 * k2_v) + (2.0 * k3_v) + k4_v);
    state->elapsed_time += dt;

    /* Settling detection criteria: position < 0.1 pt and velocity < 5.0 pt/s */
    if (fabs(state->position) < 0.1 && fabs(state->velocity) < 5.0) {
        state->is_settled = true;
    } else {
        state->is_settled = false;
    }

    return true;
}

/* =========================================================================
 * 4. Window Level Sorting & Hit-Test Arbitration
 * ========================================================================= */

void sb_sort_windows_by_level(
    sb_compositor_window_t *windows,
    size_t count
) {
    if (!windows || count <= 1) {
        return;
    }

    /* Insertion sort for stable ascending order (back-to-front compositing) */
    for (size_t i = 1; i < count; ++i) {
        sb_compositor_window_t key = windows[i];
        size_t j = i;
        while (j > 0 && windows[j - 1].window_level > key.window_level) {
            windows[j] = windows[j - 1];
            --j;
        }
        windows[j] = key;
    }
}

bool sb_hit_test_arbitrate(
    const sb_compositor_window_t *windows,
    size_t count,
    sb_point_t screen_point,
    sb_hit_test_result_t *out_result
) {
    if (!windows || !out_result) {
        return false;
    }

    memset(out_result, 0, sizeof(*out_result));

    /* Hit-testing traverses front-to-back (highest window level first) */
    for (size_t i = count; i > 0; --i) {
        const sb_compositor_window_t *win = &windows[i - 1];

        /* Exclude non-interactive, hidden, or transparent layers */
        if (win->hidden) {
            continue;
        }
        if (!win->user_interaction_enabled) {
            continue;
        }
        if (win->alpha <= 0.01) {
            continue;
        }

        if (sb_rect_contains_point(win->frame, screen_point)) {
            out_result->hit_detected = true;
            out_result->hit_window_id = win->window_id;
            out_result->hit_ca_context_id = win->ca_context_id;
            out_result->hit_window_level = win->window_level;
            out_result->local_point.x = screen_point.x - win->frame.origin.x;
            out_result->local_point.y = screen_point.y - win->frame.origin.y;
            return true;
        }
    }

    out_result->hit_detected = false;
    return false;
}

/* =========================================================================
 * 5. Comprehensive Clean-Room Verification Suite
 * ========================================================================= */

int sb_compositor_run_all_tests(void) {
    printf("[+] ====================================================================\n");
    printf("[+] SpringBoard UI Compositor Clean-Room Verification Suite (A19 Pro)\n");
    printf("[+] ====================================================================\n");

    /* ---------------------------------------------------------------------
     * Test 1: Dynamic Island Geometry & Pill Split Coordinates
     * --------------------------------------------------------------------- */
    printf("[*] Running Test 1: Dynamic Island Geometry Verification...\n");
    sb_island_layout_result_t layout;

    /* Mode 0: Compact Single */
    assert(sb_solve_island_layout(SB_ISLAND_MODE_COMPACT_SINGLE, 101, 0, &layout));
    assert(!layout.pill_split_active);
    assert(SB_FEQUAL(layout.container_frame.origin.x, 196.50, 0.001));
    assert(SB_FEQUAL(layout.container_frame.origin.y, 11.00, 0.001));
    assert(SB_FEQUAL(layout.container_frame.size.width, 120.00, 0.001));
    assert(SB_FEQUAL(layout.container_frame.size.height, 35.00, 0.001));
    assert(SB_FEQUAL(layout.corner_radius, 17.50, 0.001));

    /* Mode 1: Compact Split (Leading + Trailing separated by hardware sensor) */
    assert(sb_solve_island_layout(SB_ISLAND_MODE_COMPACT_SPLIT, 101, 102, &layout));
    assert(layout.pill_split_active);
    assert(SB_FEQUAL(layout.leading_pill_frame.origin.x, 151.17, 0.01));
    assert(SB_FEQUAL(layout.leading_pill_frame.origin.y, 11.00, 0.01));
    assert(SB_FEQUAL(layout.leading_pill_frame.size.width, 37.00, 0.01));
    assert(SB_FEQUAL(layout.leading_pill_frame.size.height, 35.00, 0.01));

    assert(SB_FEQUAL(layout.trailing_pill_frame.origin.x, 324.83, 0.01));
    assert(SB_FEQUAL(layout.trailing_pill_frame.origin.y, 11.00, 0.01));
    assert(SB_FEQUAL(layout.trailing_pill_frame.size.width, 37.00, 0.01));
    assert(SB_FEQUAL(layout.trailing_pill_frame.size.height, 35.00, 0.01));
    printf("    -> Mode 1 Pill Split Verified: Leading X=%.2f, Trailing X=%.2f\n",
           layout.leading_pill_frame.origin.x, layout.trailing_pill_frame.origin.x);

    /* Mode 2: Minimal Bubble */
    assert(sb_solve_island_layout(SB_ISLAND_MODE_MINIMAL, 101, 102, &layout));
    assert(layout.pill_split_active);
    assert(SB_FEQUAL(layout.minimal_bubble_frame.origin.x, 324.83, 0.01));
    assert(SB_FEQUAL(layout.minimal_bubble_frame.size.width, 35.00, 0.01));
    assert(SB_FEQUAL(layout.minimal_bubble_frame.size.height, 35.00, 0.01));

    /* Mode 3: Expanded HUD */
    assert(sb_solve_island_layout(SB_ISLAND_MODE_EXPANDED, 101, 0, &layout));
    assert(!layout.pill_split_active);
    assert(SB_FEQUAL(layout.expanded_hud_frame.origin.x, 36.00, 0.01));
    assert(SB_FEQUAL(layout.expanded_hud_frame.origin.y, 11.00, 0.01));
    assert(SB_FEQUAL(layout.expanded_hud_frame.size.width, 368.00, 0.01));
    assert(SB_FEQUAL(layout.expanded_hud_frame.size.height, 160.00, 0.01));
    assert(SB_FEQUAL(layout.corner_radius, 42.00, 0.01));

    /* Mode 4: Staged Alert */
    assert(sb_solve_island_layout(SB_ISLAND_MODE_STAGED_ALERT, 101, 0, &layout));
    assert(SB_FEQUAL(layout.expanded_hud_frame.size.height, 214.00, 0.01));
    printf("[+] Test 1 Passed: Dynamic Island layout modes 0-4 confirmed.\n\n");

    /* ---------------------------------------------------------------------
     * Test 2: Fluid Switcher Scale & Depth Mechanics
     * --------------------------------------------------------------------- */
    printf("[*] Running Test 2: Fluid Switcher Deck Scale & Depth...\n");
    double scale, z_depth;

    /* Index 0: Active Foreground App */
    assert(sb_solve_switcher_card_geometry(0, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 1.000, 0.001));
    assert(SB_FEQUAL(z_depth, 0.000, 0.001));

    /* Index 1: Previous App (scale decay = 0.082, z-depth = -40.0 pt) */
    assert(sb_solve_switcher_card_geometry(1, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 0.918, 0.001));
    assert(SB_FEQUAL(z_depth, -40.000, 0.001));

    /* Index 2: Second Background App */
    assert(sb_solve_switcher_card_geometry(2, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 0.836, 0.001));
    assert(SB_FEQUAL(z_depth, -80.000, 0.001));

    /* Index 4: Fourth Background App */
    assert(sb_solve_switcher_card_geometry(4, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 0.672, 0.001));
    assert(SB_FEQUAL(z_depth, -160.000, 0.001));

    /* Index 5: Clamped Scale (1.0 - 5 * 0.082 = 0.590 < 0.650) */
    assert(sb_solve_switcher_card_geometry(5, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 0.650, 0.001));
    assert(SB_FEQUAL(z_depth, -200.000, 0.001));

    /* Index 10: Deep Stack Clamped */
    assert(sb_solve_switcher_card_geometry(10, &scale, &z_depth));
    assert(SB_FEQUAL(scale, 0.650, 0.001));
    assert(SB_FEQUAL(z_depth, -400.000, 0.001));
    printf("    -> Switcher Deck Clamping Verified: index=5 -> scale=%.3f, depth=%.1f pt\n", scale, z_depth);
    printf("[+] Test 2 Passed: Fluid Switcher deck math confirmed.\n\n");

    /* ---------------------------------------------------------------------
     * Test 3: Velocity-Preserving Spring Curve Numerical Integration (RK4)
     * --------------------------------------------------------------------- */
    printf("[*] Running Test 3: Spring Curve RK4 Numerical Integration...\n");
    sb_spring_parameters_t spring_params;
    spring_params.mass = SB_SPRING_DEFAULT_MASS;          /* 1.0 kg */
    spring_params.stiffness = SB_SPRING_DEFAULT_STIFFNESS;/* 380.0 N/m */
    spring_params.damping_ratio = SB_SPRING_DEFAULT_DAMPING_RATIO; /* 0.88 */
    spring_params.initial_position = 100.0; /* 100 pt drag displacement */
    spring_params.initial_velocity = -800.0; /* -800 pt/s flick-to-home velocity */

    sb_spring_state_t spring_state;
    assert(sb_spring_init(&spring_params, &spring_state));
    assert(SB_FEQUAL(spring_state.undamped_frequency, 19.4935, 0.001));
    assert(SB_FEQUAL(spring_state.damped_frequency, 9.2589, 0.001));

    /* Compare RK4 integration against analytical solution over 350 ms */
    double dt = 1.0 / 120.0; /* 120 Hz ProMotion display frame interval (8.333 ms) */
    double max_rk4_error = 0.0;

    for (int step = 1; step <= 42; ++step) { /* 42 steps * 8.333 ms ~ 350 ms */
        assert(sb_spring_integrate_rk4(&spring_state, dt));

        double analytical_pos = 0.0, analytical_vel = 0.0;
        assert(sb_spring_evaluate_analytical(&spring_state, spring_state.elapsed_time,
                                             &analytical_pos, &analytical_vel));

        double err = fabs(spring_state.position - analytical_pos);
        if (err > max_rk4_error) {
            max_rk4_error = err;
        }
    }

    printf("    -> RK4 Integrator Error vs Analytical at 350 ms: %.6f pt (tolerance: < 0.05 pt)\n", max_rk4_error);
    assert(max_rk4_error < 0.05);

    /* Verify spring settling: after 350 ms with zeta=0.88, displacement must be critically damped to < 0.5 pt */
    printf("    -> Final Spring Position: %.4f pt, Velocity: %.4f pt/s, Settled: %s\n",
           spring_state.position, spring_state.velocity, spring_state.is_settled ? "TRUE" : "FALSE");
    assert(fabs(spring_state.position) < 0.5);
    printf("[+] Test 3 Passed: Spring physics RK4 numerical integration confirmed.\n\n");

    /* ---------------------------------------------------------------------
     * Test 4: Window Level Hierarchy & Hit-Test Arbitration
     * --------------------------------------------------------------------- */
    printf("[*] Running Test 4: Window Level Hierarchy & Hit-Test Arbitration...\n");
    sb_compositor_window_t window_stack[6];

    /* Window 0: Wallpaper */
    window_stack[0].window_id = 1;
    strncpy(window_stack[0].window_title, "SBWallpaperWindow", 48);
    window_stack[0].window_level = SB_WINDOW_LEVEL_WALLPAPER;
    window_stack[0].frame = sb_rect_make(0, 0, 440, 956);
    window_stack[0].alpha = 1.0;
    window_stack[0].hidden = false;
    window_stack[0].user_interaction_enabled = false;
    window_stack[0].ca_context_id = 0x100;

    /* Window 1: CoverSheet (LockScreen) - currently hidden */
    window_stack[1].window_id = 2;
    strncpy(window_stack[1].window_title, "SBCoverSheetWindow", 48);
    window_stack[1].window_level = SB_WINDOW_LEVEL_COVER_SHEET;
    window_stack[1].frame = sb_rect_make(0, 0, 440, 956);
    window_stack[1].alpha = 1.0;
    window_stack[1].hidden = true; /* Hidden during normal app usage */
    window_stack[1].user_interaction_enabled = true;
    window_stack[1].ca_context_id = 0x200;

    /* Window 2: Foreground Application Scene */
    window_stack[2].window_id = 3;
    strncpy(window_stack[2].window_title, "SBAppSceneWindow", 48);
    window_stack[2].window_level = SB_WINDOW_LEVEL_NORMAL;
    window_stack[2].frame = sb_rect_make(0, 0, 440, 956);
    window_stack[2].alpha = 1.0;
    window_stack[2].hidden = false;
    window_stack[2].user_interaction_enabled = true;
    window_stack[2].ca_context_id = 0x300;

    /* Window 3: Status Bar */
    window_stack[3].window_id = 4;
    strncpy(window_stack[3].window_title, "UIStatusBarWindow", 48);
    window_stack[3].window_level = SB_WINDOW_LEVEL_STATUS_BAR;
    window_stack[3].frame = sb_rect_make(0, 0, 440, 54);
    window_stack[3].alpha = 1.0;
    window_stack[3].hidden = false;
    window_stack[3].user_interaction_enabled = true;
    window_stack[3].ca_context_id = 0x400;

    /* Window 4: Dynamic Island (System Aperture) */
    window_stack[4].window_id = 5;
    strncpy(window_stack[4].window_title, "SBSystemApertureWindow", 48);
    window_stack[4].window_level = SB_WINDOW_LEVEL_SYSTEM_APERTURE;
    window_stack[4].frame = sb_rect_make(196.5, 11.0, 120.0, 35.0);
    window_stack[4].alpha = 1.0;
    window_stack[4].hidden = false;
    window_stack[4].user_interaction_enabled = true;
    window_stack[4].ca_context_id = 0x500;

    /* Window 5: Control Center Overlay - hidden */
    window_stack[5].window_id = 6;
    strncpy(window_stack[5].window_title, "SBControlCenterWindow", 48);
    window_stack[5].window_level = SB_WINDOW_LEVEL_CONTROL_CENTER;
    window_stack[5].frame = sb_rect_make(0, 0, 440, 956);
    window_stack[5].alpha = 0.0; /* Fully transparent */
    window_stack[5].hidden = false;
    window_stack[5].user_interaction_enabled = false;
    window_stack[5].ca_context_id = 0x600;

    /* Sort ascending for rendering compositing order */
    sb_sort_windows_by_level(window_stack, 6);

    assert(window_stack[0].window_level == SB_WINDOW_LEVEL_WALLPAPER);
    assert(window_stack[1].window_level == SB_WINDOW_LEVEL_NORMAL);
    assert(window_stack[2].window_level == SB_WINDOW_LEVEL_STATUS_BAR);
    assert(window_stack[3].window_level == SB_WINDOW_LEVEL_CONTROL_CENTER);
    assert(window_stack[4].window_level == SB_WINDOW_LEVEL_SYSTEM_APERTURE);
    assert(window_stack[5].window_level == SB_WINDOW_LEVEL_COVER_SHEET);
    printf("    -> Window Stack Sorted: Ascending levels from %.1f to %.1f verified.\n",
           window_stack[0].window_level, window_stack[5].window_level);

    /* Test Hit-Test Arbitration */
    sb_hit_test_result_t hit;

    /* Hit at (200.0, 20.0): Within Dynamic Island bounds (Level 2500) */
    sb_point_t pt_island = {200.0, 20.0};
    assert(sb_hit_test_arbitrate(window_stack, 6, pt_island, &hit));
    assert(hit.hit_detected);
    assert(hit.hit_window_id == 5);
    assert(hit.hit_ca_context_id == 0x500);
    assert(SB_FEQUAL(hit.hit_window_level, SB_WINDOW_LEVEL_SYSTEM_APERTURE, 0.1));
    printf("    -> Hit Test at (200, 20) -> Dynamic Island (Level %.1f, Context 0x%X) - CONFIRMED\n",
           hit.hit_window_level, hit.hit_ca_context_id);

    /* Hit at (20.0, 20.0): Outside Dynamic Island, inside Status Bar (Level 1000) */
    sb_point_t pt_statusbar = {20.0, 20.0};
    assert(sb_hit_test_arbitrate(window_stack, 6, pt_statusbar, &hit));
    assert(hit.hit_detected);
    assert(hit.hit_window_id == 4);
    assert(hit.hit_ca_context_id == 0x400);
    assert(SB_FEQUAL(hit.hit_window_level, SB_WINDOW_LEVEL_STATUS_BAR, 0.1));
    printf("    -> Hit Test at (20, 20) -> Status Bar (Level %.1f, Context 0x%X) - CONFIRMED\n",
           hit.hit_window_level, hit.hit_ca_context_id);

    /* Hit at (220.0, 500.0): In main view area -> Foreground App (Level 0) */
    sb_point_t pt_app = {220.0, 500.0};
    assert(sb_hit_test_arbitrate(window_stack, 6, pt_app, &hit));
    assert(hit.hit_detected);
    assert(hit.hit_window_id == 3);
    assert(hit.hit_ca_context_id == 0x300);
    assert(SB_FEQUAL(hit.hit_window_level, SB_WINDOW_LEVEL_NORMAL, 0.1));
    printf("    -> Hit Test at (220, 500) -> Foreground App (Level %.1f, Context 0x%X) - CONFIRMED\n",
           hit.hit_window_level, hit.hit_ca_context_id);

    /* Activate CoverSheet (unhide) */
    window_stack[5].hidden = false;
    assert(sb_hit_test_arbitrate(window_stack, 6, pt_app, &hit));
    assert(hit.hit_detected);
    assert(hit.hit_window_id == 2); /* CoverSheet intercepts whole screen */
    assert(SB_FEQUAL(hit.hit_window_level, SB_WINDOW_LEVEL_COVER_SHEET, 0.1));
    printf("    -> CoverSheet Active: Hit Test at (220, 500) -> CoverSheet (Level %.1f) - CONFIRMED\n",
           hit.hit_window_level);

    printf("[+] Test 4 Passed: Window level sorting and hit-test arbitration confirmed.\n\n");

    printf("[+] ====================================================================\n");
    printf("[+] ALL SPRINGBOARD COMPOSITOR VERIFICATION TESTS PASSED (100%% GREEN)\n");
    printf("[+] ====================================================================\n");
    return 0;
}

int main(void) {
    return sb_compositor_run_all_tests();
}
