/**
 * @file sb_fluid_switcher.c
 * @brief Clean-Room C99 Implementation of SpringBoard Fluid Gestures & Switcher Pipeline
 *
 * Target: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 * Architecture: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 */

#include "sb_fluid_switcher.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>

/* ========================================================================= */
/* Spring Dynamics Analytical Solver                                         */
/* ========================================================================= */

void sb_spring_params_init(sb_spring_params_t *params, double mass, double stiffness, double damping_ratio)
{
    if (!params || mass <= 0.0 || stiffness <= 0.0 || damping_ratio < 0.0) return;
    params->mass = mass;
    params->stiffness = stiffness;
    params->damping_ratio = damping_ratio;

    params->omega_n = sqrt(stiffness / mass);
    params->gamma = damping_ratio * params->omega_n;
    params->damping_coefficient = 2.0 * damping_ratio * sqrt(stiffness * mass);

    if (damping_ratio < 1.0) {
        /* Underdamped regime */
        params->omega_d = params->omega_n * sqrt(1.0 - (damping_ratio * damping_ratio));
    } else {
        /* Critically damped or overdamped */
        params->omega_d = 0.0;
    }
}

double sb_spring_solve_position(const sb_spring_params_t *params, double x0, double v0, double t)
{
    if (!params) return 0.0;
    if (t <= 0.0) return x0;

    double decay = exp(-params->gamma * t);

    if (params->damping_ratio < 1.0) {
        /* Underdamped */
        double cos_val = cos(params->omega_d * t);
        double sin_val = sin(params->omega_d * t);
        double coeff = (v0 + params->gamma * x0) / params->omega_d;
        return decay * (x0 * cos_val + coeff * sin_val);
    } else if (fabs(params->damping_ratio - 1.0) < 1e-6) {
        /* Critically damped */
        return decay * (x0 + (v0 + params->gamma * x0) * t);
    } else {
        /* Overdamped */
        double alpha = params->omega_n * sqrt(params->damping_ratio * params->damping_ratio - 1.0);
        double r1 = -params->gamma + alpha;
        double r2 = -params->gamma - alpha;
        double c1 = (v0 - r2 * x0) / (r1 - r2);
        double c2 = x0 - c1;
        return c1 * exp(r1 * t) + c2 * exp(r2 * t);
    }
}

double sb_spring_solve_velocity(const sb_spring_params_t *params, double x0, double v0, double t)
{
    if (!params) return 0.0;
    if (t <= 0.0) return v0;

    double decay = exp(-params->gamma * t);

    if (params->damping_ratio < 1.0) {
        /* Underdamped analytical derivative */
        double cos_val = cos(params->omega_d * t);
        double sin_val = sin(params->omega_d * t);
        double coeff = (params->gamma * v0 + params->omega_n * params->omega_n * x0) / params->omega_d;
        return decay * (v0 * cos_val - coeff * sin_val);
    } else if (fabs(params->damping_ratio - 1.0) < 1e-6) {
        /* Critically damped analytical derivative: v(t) = exp(-gamma*t) * (v0 - gamma*(v0 + gamma*x0)*t) */
        double b = v0 + params->gamma * x0;
        return decay * (v0 - params->gamma * b * t);
    } else {
        /* Overdamped analytical derivative: v(t) = c1*r1*exp(r1*t) + c2*r2*exp(r2*t) */
        double alpha = params->omega_n * sqrt(params->damping_ratio * params->damping_ratio - 1.0);
        double r1 = -params->gamma + alpha;
        double r2 = -params->gamma - alpha;
        double c1 = (v0 - r2 * x0) / (r1 - r2);
        double c2 = x0 - c1;
        return c1 * r1 * exp(r1 * t) + c2 * r2 * exp(r2 * t);
    }
}

/* ========================================================================= */
/* Home Gesture Recognizer State Machine                                     */
/* ========================================================================= */

void sb_home_gesture_recognizer_init(sb_home_gesture_pan_recognizer_t *recognizer)
{
    if (!recognizer) return;
    memset(recognizer, 0, sizeof(*recognizer));
    recognizer->state = SB_HOME_GESTURE_STATE_POSSIBLE;
    recognizer->resolved_destination = SB_DESTINATION_UNKNOWN;
    recognizer->stationary_dwell_duration_ms = 0.0;
    recognizer->edge_protect_active = false;
    recognizer->edge_protect_last_swipe_timestamp = -1.0;
    recognizer->edge_protect_affordance_revealed = false;
}

void sb_home_gesture_set_edge_protect(sb_home_gesture_pan_recognizer_t *rec, bool active)
{
    if (!rec) return;
    rec->edge_protect_active = active;
    if (!active) {
        rec->edge_protect_affordance_revealed = false;
        rec->edge_protect_last_swipe_timestamp = -1.0;
    }
}

bool sb_home_gesture_touches_began(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp)
{
    if (!rec) return false;

    /* Bottom edge exclusion zone: touch must start in the bottom 16pt */
    if (y < SB_HOME_GESTURE_EDGE_MIN_Y_PT || y > SB_DISPLAY_HEIGHT_PT) {
        rec->state = SB_HOME_GESTURE_STATE_POSSIBLE;
        rec->exclusion_trapezoid_violation = true;
        return false;
    }

    /* Edge Protect Double-Swipe Arbitration */
    if (rec->edge_protect_active) {
        if (rec->edge_protect_affordance_revealed &&
            (timestamp - rec->edge_protect_last_swipe_timestamp) <= SB_EDGE_PROTECT_TIMEOUT_S) {
            /* Second swipe within 1.2s: unlock and claim gesture */
            rec->edge_protect_affordance_revealed = false;
        } else {
            /* First swipe or expired timeout: reveal affordance only, defer gesture */
            rec->edge_protect_affordance_revealed = true;
            rec->edge_protect_last_swipe_timestamp = timestamp;
            rec->state = SB_HOME_GESTURE_STATE_POSSIBLE;
            return false;
        }
    }

    rec->state = SB_HOME_GESTURE_STATE_POSSIBLE;
    rec->touch_start.x = x;
    rec->touch_start.y = y;
    rec->touch_current.x = x;
    rec->touch_current.y = y;
    rec->translation.x = 0.0;
    rec->translation.y = 0.0;
    rec->velocity.x = 0.0;
    rec->velocity.y = 0.0;
    rec->touch_start_timestamp = timestamp;
    rec->current_timestamp = timestamp;
    rec->dwell_duration_ms = 0.0;
    rec->stationary_dwell_duration_ms = 0.0;
    rec->ever_translated_upward = false;
    rec->hold_timer_fired = false;
    rec->exclusion_trapezoid_violation = false;
    rec->resolved_destination = SB_DESTINATION_UNKNOWN;

    return true;
}

bool sb_home_gesture_touches_moved(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp)
{
    if (!rec) return false;
    if (rec->exclusion_trapezoid_violation) return false;

    double dt = timestamp - rec->current_timestamp;
    if (dt > 1e-5) {
        rec->velocity.x = (x - rec->touch_current.x) / dt;
        rec->velocity.y = (y - rec->touch_current.y) / dt;
    }

    rec->touch_current.x = x;
    rec->touch_current.y = y;
    rec->current_timestamp = timestamp;
    rec->translation.x = x - rec->touch_start.x;
    rec->translation.y = rec->touch_start.y - y; /* Positive upward */

    if (rec->translation.y > 0.0) {
        rec->ever_translated_upward = true;
    }

    rec->dwell_duration_ms = (timestamp - rec->touch_start_timestamp) * 1000.0;

    /* 2D kinematic speed evaluation for stationary dwell detection */
    double speed = sqrt(rec->velocity.x * rec->velocity.x + rec->velocity.y * rec->velocity.y);
    if (speed < SB_HOME_GESTURE_HOLD_VELOCITY_MAX_PT_S) {
        if (dt > 0.0) {
            rec->stationary_dwell_duration_ms += (dt * 1000.0);
        }
    } else {
        rec->stationary_dwell_duration_ms = 0.0;
        if (rec->state == SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER) {
            rec->state = SB_HOME_GESTURE_STATE_TRACKING_SWITCHER;
        }
    }

    /* State transition gating */
    if (rec->state == SB_HOME_GESTURE_STATE_POSSIBLE) {
        /* Minimum vertical displacement slop: 8.0 pt */
        if (rec->translation.y >= SB_HOME_GESTURE_SLOP_PT) {
            rec->state = SB_HOME_GESTURE_STATE_BEGAN;
            return true;
        }
        return false;
    }

    if (rec->state == SB_HOME_GESTURE_STATE_BEGAN || rec->state == SB_HOME_GESTURE_STATE_TRACKING_HOME) {
        rec->state = SB_HOME_GESTURE_STATE_TRACKING_HOME;

        /* Check for horizontal arc swipe */
        if (fabs(rec->velocity.x) >= 600.0 && fabs(rec->velocity.x) >= 2.0 * fabs(rec->velocity.y)) {
            rec->state = SB_HOME_GESTURE_STATE_ARC_SWIPE;
            return true;
        }

        /* Check for dwell threshold: stationary hold >= 180 ms with speed < 50 pt/s */
        if (rec->stationary_dwell_duration_ms >= SB_HOME_GESTURE_HOLD_TIME_MS) {
            sb_home_gesture_dwell_timer_fired(rec);
            return true;
        }
    } else if (rec->state == SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER) {
        /* Finger resumed dragging after pause */
        if (speed > 20.0) {
            rec->state = SB_HOME_GESTURE_STATE_TRACKING_SWITCHER;
        }
    }

    return true;
}

void sb_home_gesture_dwell_timer_fired(sb_home_gesture_pan_recognizer_t *rec)
{
    if (!rec) return;
    if (rec->state == SB_HOME_GESTURE_STATE_TRACKING_HOME || rec->state == SB_HOME_GESTURE_STATE_BEGAN) {
        rec->state = SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER;
        rec->hold_timer_fired = true;
    }
}

sb_home_gesture_destination_t sb_home_gesture_touches_ended(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp)
{
    if (!rec) return SB_DESTINATION_UNKNOWN;

    sb_home_gesture_touches_moved(rec, x, y, timestamp);

    /* If slop was never satisfied */
    if (rec->state == SB_HOME_GESTURE_STATE_POSSIBLE) {
        rec->state = SB_HOME_GESTURE_STATE_CANCELLED_RETURN;
        rec->resolved_destination = SB_DESTINATION_RETURN_TO_APPLICATION;
        return rec->resolved_destination;
    }

    /* Arc swipe resolution */
    if (rec->state == SB_HOME_GESTURE_STATE_ARC_SWIPE) {
        rec->state = SB_HOME_GESTURE_STATE_COMMITTED_HOME;
        rec->resolved_destination = (rec->velocity.x > 0.0) ?
            SB_DESTINATION_ARC_NEXT_APP : SB_DESTINATION_ARC_PREVIOUS_APP;
        return rec->resolved_destination;
    }

    /* Velocity & displacement decision engine */
    sb_point_t release_pos = rec->touch_current;
    sb_point_t release_vel = rec->velocity;

    rec->resolved_destination = sb_determine_final_destination(
        release_pos, release_vel, rec->stationary_dwell_duration_ms, rec->hold_timer_fired
    );

    if (rec->resolved_destination == SB_DESTINATION_HOME_SCREEN) {
        rec->state = SB_HOME_GESTURE_STATE_COMMITTED_HOME;
    } else if (rec->resolved_destination == SB_DESTINATION_APP_SWITCHER) {
        rec->state = SB_HOME_GESTURE_STATE_COMMITTED_SWITCHER;
    } else {
        rec->state = SB_HOME_GESTURE_STATE_CANCELLED_RETURN;
    }

    return rec->resolved_destination;
}

/* ========================================================================= */
/* Participant Priority Arbitration                                          */
/* ========================================================================= */

void sb_participant_registry_init(sb_participant_registry_t *reg)
{
    if (!reg) return;
    memset(reg, 0, sizeof(*reg));
    reg->current_owner_id = -1;
}

bool sb_participant_register(sb_participant_registry_t *reg, int id, const char *ident, sb_participant_priority_t prio, bool double_swipe)
{
    if (!reg) return false;

    /* Check if already registered - can update priority even if at max capacity */
    for (size_t i = 0; i < reg->count; ++i) {
        if (reg->participants[i].participant_id == id) {
            reg->participants[i].identifier = ident;
            reg->participants[i].priority = prio;
            reg->participants[i].wants_home_gesture = true;
            reg->participants[i].requires_double_swipe = double_swipe;
            sb_participant_arbitrate(reg);
            return true;
        }
    }

    if (reg->count >= SB_MAX_PARTICIPANTS) return false;

    sb_home_gesture_participant_t *p = &reg->participants[reg->count++];
    p->participant_id = id;
    p->identifier = ident;
    p->priority = prio;
    p->wants_home_gesture = true;
    p->owns_home_gesture = false;
    p->requires_double_swipe = double_swipe;

    sb_participant_arbitrate(reg);
    return true;
}

bool sb_participant_unregister(sb_participant_registry_t *reg, int id)
{
    if (!reg || reg->count == 0) return false;

    for (size_t i = 0; i < reg->count; ++i) {
        if (reg->participants[i].participant_id == id) {
            for (size_t j = i; j < reg->count - 1; ++j) {
                reg->participants[j] = reg->participants[j + 1];
            }
            reg->count--;
            sb_participant_arbitrate(reg);
            return true;
        }
    }
    return false;
}

bool sb_participant_set_wants_gesture(sb_participant_registry_t *reg, int id, bool wants)
{
    if (!reg || reg->count == 0) return false;
    for (size_t i = 0; i < reg->count; ++i) {
        if (reg->participants[i].participant_id == id) {
            reg->participants[i].wants_home_gesture = wants;
            sb_participant_arbitrate(reg);
            return true;
        }
    }
    return false;
}

int sb_participant_arbitrate(sb_participant_registry_t *reg)
{
    if (!reg || reg->count == 0) {
        if (reg) reg->current_owner_id = -1;
        return -1;
    }

    int highest_prio = -1;
    int winner_idx = -1;

    for (size_t i = 0; i < reg->count; ++i) {
        reg->participants[i].owns_home_gesture = false;
        if (reg->participants[i].wants_home_gesture) {
            if ((int)reg->participants[i].priority > highest_prio) {
                highest_prio = (int)reg->participants[i].priority;
                winner_idx = (int)i;
            }
        }
    }

    if (winner_idx >= 0) {
        reg->participants[winner_idx].owns_home_gesture = true;
        reg->current_owner_id = reg->participants[winner_idx].participant_id;
        return reg->current_owner_id;
    }

    reg->current_owner_id = -1;
    return -1;
}

/* ========================================================================= */
/* Deck Switcher Geometry Math                                               */
/* ========================================================================= */

double sb_deck_card_scale(size_t index)
{
    double s = 1.0 - (double)index * SB_DECK_SCALE_DECAY_PER_CARD;
    if (s < SB_DECK_SCALE_MIN_CLAMP) {
        s = SB_DECK_SCALE_MIN_CLAMP;
    }
    return s;
}

double sb_interactive_card_scale(double delta_y)
{
    if (delta_y <= 0.0) return 1.0;
    double progress = delta_y / SB_INTERACTIVE_CARD_SCALE_MAX_TRAVEL_PT;
    if (progress > 1.0) progress = 1.0;
    return 1.0 - (1.0 - SB_INTERACTIVE_CARD_SCALE_SWITCHER) * progress;
}

double sb_deck_card_depth(size_t index)
{
    return -(double)index * SB_DECK_DELTA_Z_PT;
}

double sb_deck_card_offset(size_t index)
{
    return SB_DECK_Y_BASE_PT - (double)index * SB_DECK_DELTA_Y_PT;
}

double sb_deck_offset_curve(double t, double y0, double v0, const sb_spring_params_t *params)
{
    return sb_spring_solve_position(params, y0, v0, t);
}

double sb_deck_rubberband(double x, double dimension, double coefficient)
{
    if (dimension <= 0.0 || coefficient <= 0.0) return x;
    double abs_x = fabs(x);
    double numer = x * coefficient * dimension;
    double denom = dimension + coefficient * abs_x;
    if (denom <= 0.0) return 0.0;
    return numer / denom;
}

double sb_deck_rubberband_inverse(double fx, double dimension, double coefficient)
{
    if (dimension <= 0.0 || coefficient <= 0.0) return fx;
    double abs_fx = fabs(fx);
    /* Asymptotic limit is exactly dimension (874.0pt), where denominator -> 0 */
    if (abs_fx >= dimension) {
        return (fx >= 0.0) ? 1e6 : -1e6;
    }
    double sign = (fx >= 0.0) ? 1.0 : -1.0;
    return sign * (abs_fx * dimension) / (coefficient * (dimension - abs_fx));
}

double sb_continuous_corner_radius(double delta_y, double r_start, double r_end, double morph_threshold)
{
    if (morph_threshold <= 0.0) return r_end;
    double progress = delta_y / morph_threshold;
    if (progress < 0.0) progress = 0.0;
    if (progress > 1.0) progress = 1.0;
    return r_start + progress * (r_end - r_start);
}

void sb_deck_layout_compute_card(size_t index, sb_deck_card_layout_t *out_layout)
{
    if (!out_layout) return;
    out_layout->card_index = index;
    out_layout->scale = sb_deck_card_scale(index);
    out_layout->z_depth = sb_deck_card_depth(index);
    out_layout->y_offset = sb_deck_card_offset(index);
    out_layout->alpha = (index == 0) ? 1.0 : (1.0 - 0.05 * (double)index);
    if (out_layout->alpha < 0.4) out_layout->alpha = 0.4;
    out_layout->corner_radius = SB_CARD_RESTING_CORNER_RADIUS_PT;
}

/* ========================================================================= */
/* Velocity Projection & Destination Gating                                  */
/* ========================================================================= */

void sb_velocity_project_landing(sb_point_t release_pos, sb_point_t release_vel, double delta, sb_point_t *out_projected_pos)
{
    if (!out_projected_pos) return;
    if (delta <= 0.0) delta = SB_VELOCITY_PROJECTION_DELTA;

    out_projected_pos->x = release_pos.x + (release_vel.x / delta);
    out_projected_pos->y = release_pos.y + (release_vel.y / delta);
}

sb_home_gesture_destination_t sb_determine_final_destination(
    sb_point_t release_pos,
    sb_point_t release_vel,
    double dwell_ms,
    bool hold_fired)
{
    /* 1. Check horizontal arc swipe quick switch */
    if (fabs(release_vel.x) >= 600.0 && fabs(release_vel.x) >= 2.0 * fabs(release_vel.y)) {
        return (release_vel.x > 0.0) ? SB_DESTINATION_ARC_NEXT_APP : SB_DESTINATION_ARC_PREVIOUS_APP;
    }

    /* 2. Downward throw / flick (vy >= 500 pt/s): abort back to application */
    if (release_vel.y >= 500.0) {
        return SB_DESTINATION_RETURN_TO_APPLICATION;
    }

    /* 3. Fast flick upward: unconditional Home commit */
    if (release_vel.y <= SB_HOME_GESTURE_COMMIT_HOME_VELOCITY_PT_S) {
        return SB_DESTINATION_HOME_SCREEN;
    }

    /* 4. Stationary dwell hold: commits to Switcher */
    if (hold_fired || (dwell_ms >= SB_HOME_GESTURE_HOLD_TIME_MS &&
                       fabs(release_vel.y) < SB_HOME_GESTURE_HOLD_VELOCITY_MAX_PT_S &&
                       fabs(release_vel.x) < SB_HOME_GESTURE_HOLD_VELOCITY_MAX_PT_S)) {
        return SB_DESTINATION_APP_SWITCHER;
    }

    /* 5. Trajectory projection calculation */
    sb_point_t projected_target;
    sb_velocity_project_landing(release_pos, release_vel, SB_VELOCITY_PROJECTION_DELTA, &projected_target);

    double commit_y_threshold = SB_DISPLAY_HEIGHT_PT - SB_HOME_GESTURE_COMMIT_HOME_DISTANCE_PT; /* 568.1 pt */

    /* If finger is moving downward, check if projected trajectory lands below commit horizon */
    if (release_vel.y > 0.0) {
        if (projected_target.y > commit_y_threshold) {
            return SB_DESTINATION_RETURN_TO_APPLICATION;
        }
    }

    /* Upward travel exceeded commit distance (305.9pt = 35% height) while moving upward */
    double upward_travel = SB_DISPLAY_HEIGHT_PT - release_pos.y;
    if (upward_travel >= SB_HOME_GESTURE_COMMIT_HOME_DISTANCE_PT && release_vel.y <= 0.0) {
        return SB_DESTINATION_HOME_SCREEN;
    }

    /* Projected target landed sufficiently high up display */
    if (projected_target.y <= commit_y_threshold) {
        return SB_DESTINATION_HOME_SCREEN;
    }

    /* Subthreshold release: returns back into active app */
    return SB_DESTINATION_RETURN_TO_APPLICATION;
}

/* ========================================================================= */
/* Match-Move Affine Transformation                                          */
/* ========================================================================= */

sb_affine_transform_t sb_affine_transform_identity(void)
{
    sb_affine_transform_t t;
    t.a = 1.0; t.b = 0.0;
    t.c = 0.0; t.d = 1.0;
    t.tx = 0.0; t.ty = 0.0;
    return t;
}

sb_point_t sb_affine_transform_point(sb_affine_transform_t t, sb_point_t p)
{
    sb_point_t res;
    res.x = t.a * p.x + t.c * p.y + t.tx;
    res.y = t.b * p.x + t.d * p.y + t.ty;
    return res;
}

void sb_match_move_compute(sb_rect_t source_card, sb_rect_t target_icon, sb_match_move_transform_t *out_transform)
{
    if (!out_transform) return;
    if (source_card.size.width <= 0.0 || source_card.size.height <= 0.0 ||
        target_icon.size.width <= 0.0 || target_icon.size.height <= 0.0) {
        memset(out_transform, 0, sizeof(*out_transform));
        out_transform->final_transform = sb_affine_transform_identity();
        out_transform->current_transform = sb_affine_transform_identity();
        return;
    }
    out_transform->source_card_bounds = source_card;
    out_transform->target_icon_bounds = target_icon;

    double card_center_x = source_card.origin.x + source_card.size.width / 2.0;
    double card_center_y = source_card.origin.y + source_card.size.height / 2.0;

    double icon_center_x = target_icon.origin.x + target_icon.size.width / 2.0;
    double icon_center_y = target_icon.origin.y + target_icon.size.height / 2.0;

    out_transform->final_transform.a = target_icon.size.width / source_card.size.width;
    out_transform->final_transform.b = 0.0;
    out_transform->final_transform.c = 0.0;
    out_transform->final_transform.d = target_icon.size.height / source_card.size.height;
    out_transform->final_transform.tx = icon_center_x - out_transform->final_transform.a * card_center_x;
    out_transform->final_transform.ty = icon_center_y - out_transform->final_transform.d * card_center_y;

    out_transform->start_corner_radius = SB_DISPLAY_CORNER_RADIUS_PT;
    out_transform->target_corner_radius = SB_ICON_CORNER_RADIUS_PT;

    sb_match_move_interpolate(out_transform, 0.0);
}

void sb_match_move_interpolate(sb_match_move_transform_t *transform, double progress)
{
    if (!transform) return;
    if (progress < 0.0) progress = 0.0;
    if (progress > 1.0) progress = 1.0;

    transform->progress = progress;

    double card_center_x = transform->source_card_bounds.origin.x + transform->source_card_bounds.size.width / 2.0;
    double card_center_y = transform->source_card_bounds.origin.y + transform->source_card_bounds.size.height / 2.0;

    double icon_center_x = transform->target_icon_bounds.origin.x + transform->target_icon_bounds.size.width / 2.0;
    double icon_center_y = transform->target_icon_bounds.origin.y + transform->target_icon_bounds.size.height / 2.0;

    double cur_center_x = card_center_x + progress * (icon_center_x - card_center_x);
    double cur_center_y = card_center_y + progress * (icon_center_y - card_center_y);

    transform->current_transform.a = 1.0 + progress * (transform->final_transform.a - 1.0);
    transform->current_transform.b = 0.0;
    transform->current_transform.c = 0.0;
    transform->current_transform.d = 1.0 + progress * (transform->final_transform.d - 1.0);
    transform->current_transform.tx = cur_center_x - transform->current_transform.a * card_center_x;
    transform->current_transform.ty = cur_center_y - transform->current_transform.d * card_center_y;

    transform->current_corner_radius = (1.0 - progress) * transform->start_corner_radius +
                                       progress * transform->target_corner_radius;
}

/* ========================================================================= */
/* Switcher Modifier Pipeline                                                */
/* ========================================================================= */

void sb_modifier_stack_init(sb_switcher_modifier_stack_t *stack)
{
    if (!stack) return;
    memset(stack, 0, sizeof(*stack));
}

bool sb_modifier_stack_push(sb_switcher_modifier_stack_t *stack, sb_modifier_t *modifier)
{
    if (!stack || !modifier || stack->count >= SB_MAX_MODIFIERS) return false;
    stack->stack[stack->count++] = modifier;
    modifier->is_active = true;
    return true;
}

bool sb_modifier_stack_pop(sb_switcher_modifier_stack_t *stack, sb_modifier_t **out_modifier)
{
    if (!stack || stack->count == 0) return false;
    sb_modifier_t *m = stack->stack[--stack->count];
    m->is_active = false;
    if (out_modifier) *out_modifier = m;
    return true;
}

sb_switcher_modifier_event_response_t sb_modifier_stack_handle_event(
    sb_switcher_modifier_stack_t *stack,
    const sb_switcher_modifier_event_t *event)
{
    sb_switcher_modifier_event_response_t accumulated_response;
    memset(&accumulated_response, 0, sizeof(accumulated_response));

    if (!stack || !event) return accumulated_response;

    /* Iterate from top of stack downward */
    for (size_t i = stack->count; i > 0; --i) {
        sb_modifier_t *mod = stack->stack[i - 1];
        if (mod && mod->is_active && mod->handle_event) {
            sb_switcher_modifier_event_response_t r = mod->handle_event(mod, event);
            accumulated_response.response_flags |= r.response_flags;
            if (r.response_flags & SB_RESPONSE_INJECT_VELOCITY) {
                accumulated_response.injected_velocity = r.injected_velocity;
            }
            if (r.target_modifier_id != 0) {
                accumulated_response.target_modifier_id = r.target_modifier_id;
            }
        }
    }
    return accumulated_response;
}

/* ========================================================================= */
/* Standalone Verification Test Suite (compiles with -DSB_STANDALONE_TEST)   */
/* ========================================================================= */

#ifdef SB_STANDALONE_TEST

static sb_switcher_modifier_event_response_t mock_modifier_handler(
    sb_modifier_t *self,
    const sb_switcher_modifier_event_t *event)
{
    sb_switcher_modifier_event_response_t res;
    memset(&res, 0, sizeof(res));
    if (!self || !event) return res;

    if (event->gesture_state == SB_HOME_GESTURE_STATE_COMMITTED_HOME) {
        res.response_flags |= SB_RESPONSE_REQUEST_MATCH_MOVE_TO_ICON;
        res.response_flags |= SB_RESPONSE_NOTIFY_ICON_WILL_ZOOM_DOWN;
        res.response_flags |= SB_RESPONSE_INJECT_VELOCITY;
        res.injected_velocity = event->velocity;
    }
    return res;
}

int main(void)
{
    printf("[*] Running SpringBoard Fluid Switcher Clean-Room Verification Suite...\n");

    /* 1. Spring Parameters & Analytical Equations */
    {
        sb_spring_params_t spring;
        sb_spring_params_init(&spring, SB_SPRING_MASS_KG, SB_SPRING_STIFFNESS_NPM, SB_SPRING_DAMPING_RATIO);
        assert(fabs(spring.omega_n - 19.493588676) < 1e-4);
        assert(fabs(spring.omega_d - 9.258941624) < 1e-4);
        assert(fabs(spring.gamma - 17.154358035) < 1e-4);

        double x0 = 100.0;
        double v0 = -600.0;
        double x_0 = sb_spring_solve_position(&spring, x0, v0, 0.0);
        assert(fabs(x_0 - 100.0) < 1e-6);

        double x_settle = sb_spring_solve_position(&spring, x0, v0, 0.320);
        assert(fabs(x_settle) < 0.5); /* Settling within 0.5pt tolerance */

        /* Verify exact analytical velocity for underdamped spring */
        double v_analytical = sb_spring_solve_velocity(&spring, x0, v0, 0.0);
        assert(fabs(v_analytical - v0) < 1e-6);

        /* Verify exact analytical velocity for critically damped spring */
        sb_spring_params_t crit_spring;
        sb_spring_params_init(&crit_spring, 1.0, 100.0, 1.0);
        double v_crit_exact = sb_spring_solve_velocity(&crit_spring, 10.0, -50.0, 1e-6);
        double b_crit = -50.0 + 10.0 * 10.0;
        double v_crit_expected = exp(-10.0 * 1e-6) * (-50.0 - 10.0 * b_crit * 1e-6);
        assert(fabs(v_crit_exact - v_crit_expected) < 1e-6);

        /* Verify exact analytical velocity for overdamped spring */
        sb_spring_params_t over_spring;
        sb_spring_params_init(&over_spring, 1.0, 100.0, 1.25);
        double v_over = sb_spring_solve_velocity(&over_spring, 10.0, -50.0, 0.0);
        assert(fabs(v_over - (-50.0)) < 1e-6);

        printf("    -> [PASS] Spring dynamics analytical solver verified (underdamped, critical, overdamped).\n");
    }

    /* 2. Home Gesture Edge Exclusion, Touch Slop & Edge Protect Double-Swipe */
    {
        sb_home_gesture_pan_recognizer_t rec;
        sb_home_gesture_recognizer_init(&rec);

        /* Touch above exclusion zone (y = 800.0 < 858.0) must fail */
        bool accepted = sb_home_gesture_touches_began(&rec, 201.0, 800.0, 0.0);
        assert(!accepted);
        assert(rec.exclusion_trapezoid_violation);

        /* Touch in exclusion zone (y = 865.0 >= 858.0) must succeed */
        accepted = sb_home_gesture_touches_began(&rec, 201.0, 865.0, 0.0);
        assert(accepted);
        assert(rec.state == SB_HOME_GESTURE_STATE_POSSIBLE);

        /* Travel < 8pt slop must remain POSSIBLE */
        sb_home_gesture_touches_moved(&rec, 201.0, 860.0, 0.010); /* delta_y = 5.0 pt */
        assert(rec.state == SB_HOME_GESTURE_STATE_POSSIBLE);

        /* Travel >= 8pt slop must transition to BEGAN / TRACKING */
        sb_home_gesture_touches_moved(&rec, 201.0, 855.0, 0.020); /* delta_y = 10.0 pt */
        assert(rec.state == SB_HOME_GESTURE_STATE_BEGAN || rec.state == SB_HOME_GESTURE_STATE_TRACKING_HOME);

        /* Test Edge Protect Double-Swipe Timing Window (1.2s) */
        sb_home_gesture_pan_recognizer_t ep_rec;
        sb_home_gesture_recognizer_init(&ep_rec);
        sb_home_gesture_set_edge_protect(&ep_rec, true);

        /* Swipe 1: Reveals affordance, does not begin gesture */
        bool ep1 = sb_home_gesture_touches_began(&ep_rec, 201.0, 865.0, 1.000);
        assert(!ep1);
        assert(ep_rec.edge_protect_affordance_revealed);

        /* Swipe 2 at 1.500s (dt = 0.500s <= 1.2s): Successfully claims gesture */
        bool ep2 = sb_home_gesture_touches_began(&ep_rec, 201.0, 865.0, 1.500);
        assert(ep2);
        assert(!ep_rec.edge_protect_affordance_revealed);

        /* Test Edge Protect Timeout Expiration (> 1.2s) */
        sb_home_gesture_pan_recognizer_t ep_timeout_rec;
        sb_home_gesture_recognizer_init(&ep_timeout_rec);
        sb_home_gesture_set_edge_protect(&ep_timeout_rec, true);
        sb_home_gesture_touches_began(&ep_timeout_rec, 201.0, 865.0, 1.000); /* Swipe 1 */
        bool ep_late = sb_home_gesture_touches_began(&ep_timeout_rec, 201.0, 865.0, 2.300); /* dt = 1.3s > 1.2s */
        assert(!ep_late); /* Timed out, acts as new first swipe */
        assert(ep_timeout_rec.edge_protect_affordance_revealed);

        printf("    -> [PASS] Edge exclusion zone (16pt), touch slop (8pt) & edge protect double-swipe (1.2s) verified.\n");
    }

    /* 3. Dwell Hold for Switcher (180ms & 2D speed < 50pt/s) */
    {
        sb_home_gesture_pan_recognizer_t rec;
        sb_home_gesture_recognizer_init(&rec);
        sb_home_gesture_touches_began(&rec, 201.0, 865.0, 0.0);
        sb_home_gesture_touches_moved(&rec, 201.0, 850.0, 0.020); /* delta_y = 15pt */

        /* Stationary dwell simulation (speed < 50pt/s for 180ms) */
        sb_home_gesture_touches_moved(&rec, 201.0, 850.0, 0.200); /* dt = 180ms stationary */
        assert(rec.state == SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER);
        assert(rec.hold_timer_fired);

        sb_home_gesture_destination_t dest = sb_home_gesture_touches_ended(&rec, 201.0, 850.0, 0.210);
        assert(dest == SB_DESTINATION_APP_SWITCHER);
        assert(rec.state == SB_HOME_GESTURE_STATE_COMMITTED_SWITCHER);

        /* Horizontal moving swipe must NOT fire dwell timer */
        sb_home_gesture_pan_recognizer_t horiz_rec;
        sb_home_gesture_recognizer_init(&horiz_rec);
        sb_home_gesture_touches_began(&horiz_rec, 100.0, 865.0, 0.0);
        sb_home_gesture_touches_moved(&horiz_rec, 100.0, 850.0, 0.020);
        /* User moves horizontally across screen at 400 pt/s (vx = 400, vy = 0) */
        sb_home_gesture_touches_moved(&horiz_rec, 172.0, 850.0, 0.200);
        assert(!horiz_rec.hold_timer_fired);
        assert(horiz_rec.state != SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER);

        printf("    -> [PASS] Hold-for-switcher time gate (180ms) & 2D speed gating verified.\n");
    }

    /* 4. Priority Arbitration & Dynamic State Toggling */
    {
        sb_participant_registry_t reg;
        sb_participant_registry_init(&reg);

        sb_participant_register(&reg, 1, "SBApplication", SB_PARTICIPANT_PRIORITY_APPLICATION, false);
        assert(reg.current_owner_id == 1);

        sb_participant_register(&reg, 2, "SBAssistantIsland", SB_PARTICIPANT_PRIORITY_DYNAMIC_ISLAND, false);
        assert(reg.current_owner_id == 2); /* Dynamic island preempts application */

        sb_participant_register(&reg, 3, "CSCoverSheet", SB_PARTICIPANT_PRIORITY_COVERSHEET, false);
        assert(reg.current_owner_id == 3); /* CoverSheet preempts dynamic island */

        /* Test dynamic toggling of wants_home_gesture */
        sb_participant_set_wants_gesture(&reg, 3, false);
        assert(reg.current_owner_id == 2); /* Drops back to dynamic island */

        sb_participant_set_wants_gesture(&reg, 3, true);
        assert(reg.current_owner_id == 3); /* Re-claims ownership */

        sb_participant_unregister(&reg, 3);
        assert(reg.current_owner_id == 2); /* Reverts back to dynamic island */

        /* Test registry capacity & update at full capacity */
        sb_participant_registry_t full_reg;
        sb_participant_registry_init(&full_reg);
        for (int i = 0; i < SB_MAX_PARTICIPANTS; i++) {
            bool ok = sb_participant_register(&full_reg, i + 1, "P", SB_PARTICIPANT_PRIORITY_APPLICATION, false);
            assert(ok);
        }
        /* New participant fails at capacity */
        bool new_ok = sb_participant_register(&full_reg, 999, "Overflow", SB_PARTICIPANT_PRIORITY_COVERSHEET, false);
        assert(!new_ok);
        /* Updating existing participant succeeds even at capacity */
        bool update_ok = sb_participant_register(&full_reg, 5, "Updated", SB_PARTICIPANT_PRIORITY_COVERSHEET, false);
        assert(update_ok);
        assert(full_reg.current_owner_id == 5);

        printf("    -> [PASS] Participant priority arbitration, capacity update & dynamic toggling verified.\n");
    }

    /* 5. Deck Switcher 3D Geometry, Interactive s(y), Offset Curve y(t) & Rubberband Horizon */
    {
        assert(fabs(sb_deck_card_scale(0) - 1.000) < 1e-6);
        assert(fabs(sb_deck_card_scale(1) - 0.918) < 1e-6);
        assert(fabs(sb_deck_card_scale(2) - 0.836) < 1e-6);
        assert(fabs(sb_deck_card_scale(5) - 0.650) < 1e-6); /* Minimum clamp */
        assert(fabs(sb_deck_card_scale(10) - 0.650) < 1e-6);

        /* Interactive card scaling function s(y) */
        assert(fabs(sb_interactive_card_scale(0.0) - 1.000) < 1e-6);
        assert(fabs(sb_interactive_card_scale(200.0) - 0.900) < 1e-6);
        assert(fabs(sb_interactive_card_scale(400.0) - 0.800) < 1e-6);
        assert(fabs(sb_interactive_card_scale(600.0) - 0.800) < 1e-6); /* Clamped at 400pt */

        assert(fabs(sb_deck_card_depth(0) - 0.0) < 1e-6);
        assert(fabs(sb_deck_card_depth(2) - (-80.0)) < 1e-6);

        /* Offset curve y(t) */
        sb_spring_params_t sp;
        sb_spring_params_init(&sp, SB_SPRING_MASS_KG, SB_SPRING_STIFFNESS_NPM, SB_SPRING_DAMPING_RATIO);
        double y_t0 = sb_deck_offset_curve(0.0, 100.0, -600.0, &sp);
        assert(fabs(y_t0 - 100.0) < 1e-6);

        /* Rubberband roundtrip */
        double x_drag = 120.0;
        double fx = sb_deck_rubberband(x_drag, SB_DISPLAY_HEIGHT_PT, SB_RUBBERBAND_COEFF);
        double x_inv = sb_deck_rubberband_inverse(fx, SB_DISPLAY_HEIGHT_PT, SB_RUBBERBAND_COEFF);
        assert(fabs(x_drag - x_inv) < 1e-4);

        /* Asymptotic limit verification: fx >= d saturates safely to 1e6 */
        double x_asymp = sb_deck_rubberband_inverse(SB_DISPLAY_HEIGHT_PT, SB_DISPLAY_HEIGHT_PT, SB_RUBBERBAND_COEFF);
        assert(x_asymp == 1e6);
        double x_beyond = sb_deck_rubberband_inverse(900.0, SB_DISPLAY_HEIGHT_PT, SB_RUBBERBAND_COEFF);
        assert(x_beyond == 1e6);
        double x_neg_asymp = sb_deck_rubberband_inverse(-SB_DISPLAY_HEIGHT_PT, SB_DISPLAY_HEIGHT_PT, SB_RUBBERBAND_COEFF);
        assert(x_neg_asymp == -1e6);

        /* Continuous corner radius interpolation (0pt to 55pt over 100pt drag) */
        double r_0 = sb_continuous_corner_radius(0.0, 0.0, 55.0, 100.0);
        double r_50 = sb_continuous_corner_radius(50.0, 0.0, 55.0, 100.0);
        double r_100 = sb_continuous_corner_radius(100.0, 0.0, 55.0, 100.0);
        assert(fabs(r_0 - 0.0) < 1e-6);
        assert(fabs(r_50 - 27.5) < 1e-6);
        assert(fabs(r_100 - 55.0) < 1e-6);
        printf("    -> [PASS] Card deck geometry, scaling s(y), offset curve y(t) & rubberband horizon verified.\n");
    }

    /* 6. Velocity Projection, Downward Throws & Match-Move Affine Transformation */
    {
        sb_point_t rel_pos = {201.0, 700.0};
        sb_point_t rel_vel = {0.0, -1400.0};
        sb_point_t proj_pos;
        sb_velocity_project_landing(rel_pos, rel_vel, SB_VELOCITY_PROJECTION_DELTA, &proj_pos);
        assert(fabs(proj_pos.x - 201.0) < 1e-6);
        assert(fabs(proj_pos.y - 600.0) < 1e-6);

        /* Downward throw cancellation test: vy = +1500 pt/s must return to app */
        sb_point_t throw_pos = {201.0, 500.0};
        sb_point_t throw_vel = {0.0, 1500.0};
        sb_home_gesture_destination_t throw_dest = sb_determine_final_destination(throw_pos, throw_vel, 100.0, false);
        assert(throw_dest == SB_DESTINATION_RETURN_TO_APPLICATION);

        /* Downward slow throw whose trajectory lands below commit horizon */
        sb_point_t slow_down_pos = {201.0, 550.0};
        sb_point_t slow_down_vel = {0.0, 300.0};
        sb_home_gesture_destination_t slow_down_dest = sb_determine_final_destination(slow_down_pos, slow_down_vel, 100.0, false);
        assert(slow_down_dest == SB_DESTINATION_RETURN_TO_APPLICATION);

        /* Zero bounds safety in match move */
        sb_rect_t zero_card = {{0.0, 0.0}, {0.0, 0.0}};
        sb_rect_t normal_icon = {{28.0, 180.0}, {60.0, 60.0}};
        sb_match_move_transform_t zero_mm;
        sb_match_move_compute(zero_card, normal_icon, &zero_mm);
        assert(zero_mm.final_transform.a == 1.0);

        sb_rect_t card_rect = {{0.0, 0.0}, {402.0, 874.0}};
        sb_rect_t icon_rect = {{28.0, 180.0}, {60.0, 60.0}};
        sb_match_move_transform_t mm;
        sb_match_move_compute(card_rect, icon_rect, &mm);

        assert(fabs(mm.final_transform.a - (60.0 / 402.0)) < 1e-6);
        assert(fabs(mm.final_transform.d - (60.0 / 874.0)) < 1e-6);
        assert(fabs(mm.final_transform.tx - 28.0) < 1e-6);
        assert(fabs(mm.final_transform.ty - 180.0) < 1e-6);

        /* At progress 1.0, transformed center must map to icon center */
        sb_match_move_interpolate(&mm, 1.0);
        sb_point_t card_center = {201.0, 437.0};
        sb_point_t mapped_center = sb_affine_transform_point(mm.current_transform, card_center);
        assert(fabs(mapped_center.x - 58.0) < 1e-6);
        assert(fabs(mapped_center.y - 210.0) < 1e-6);
        assert(fabs(mm.current_corner_radius - 13.5) < 1e-6);
        printf("    -> [PASS] Velocity vector projection, downward throw abort & match-move affine morphing verified.\n");
    }

    /* 7. Modifier Stack Event Propagation */
    {
        sb_switcher_modifier_stack_t stack;
        sb_modifier_stack_init(&stack);

        sb_modifier_t test_mod;
        memset(&test_mod, 0, sizeof(test_mod));
        test_mod.modifier_id = 42;
        test_mod.name = "TestHomeToZoomDownModifier";
        test_mod.handle_event = mock_modifier_handler;

        sb_modifier_stack_push(&stack, &test_mod);
        assert(stack.count == 1);

        sb_switcher_modifier_event_t evt;
        memset(&evt, 0, sizeof(evt));
        evt.type = SB_MODIFIER_EVENT_GESTURE;
        evt.gesture_state = SB_HOME_GESTURE_STATE_COMMITTED_HOME;
        evt.velocity.y = -1200.0;

        sb_switcher_modifier_event_response_t resp = sb_modifier_stack_handle_event(&stack, &evt);
        assert(resp.response_flags & SB_RESPONSE_REQUEST_MATCH_MOVE_TO_ICON);
        assert(resp.response_flags & SB_RESPONSE_NOTIFY_ICON_WILL_ZOOM_DOWN);
        assert(resp.response_flags & SB_RESPONSE_INJECT_VELOCITY);
        assert(fabs(resp.injected_velocity.y - (-1200.0)) < 1e-6);
        printf("    -> [PASS] Modifier stack declarative event propagation verified.\n");
    }

    printf("[+] All SpringBoard Fluid Switcher runtime tests PASSED with 100%% integrity.\n");
    return 0;
}

#endif /* SB_STANDALONE_TEST */
