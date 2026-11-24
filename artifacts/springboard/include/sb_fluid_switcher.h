/**
 * @file sb_fluid_switcher.h
 * @brief SpringBoard Fluid Gestures & Fluid Switcher Subsystem Architecture
 *
 * Target: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 * Architecture: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 * Specification: Clean-Room C99 Implementation
 */

#ifndef SB_FLUID_SWITCHER_H
#define SB_FLUID_SWITCHER_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* Physical Display Geometry & Threshold Constants                           */
/* ========================================================================= */

#define SB_DISPLAY_WIDTH_PT                      402.0
#define SB_DISPLAY_HEIGHT_PT                     874.0
#define SB_DISPLAY_CORNER_RADIUS_PT               55.0

#define SB_HOME_GESTURE_EDGE_EXCLUSION_DEPTH_PT   16.0
#define SB_HOME_GESTURE_EDGE_MIN_Y_PT            (SB_DISPLAY_HEIGHT_PT - SB_HOME_GESTURE_EDGE_EXCLUSION_DEPTH_PT) /* 858.0 */

#define SB_HOME_GESTURE_SLOP_PT                    8.0
#define SB_HOME_GESTURE_HOLD_TIME_MS             180.0
#define SB_HOME_GESTURE_HOLD_VELOCITY_MAX_PT_S    50.0

#define SB_HOME_GESTURE_COMMIT_HOME_VELOCITY_PT_S -500.0
#define SB_HOME_GESTURE_COMMIT_HOME_DISTANCE_PT   305.9 /* 0.35 * 874.0 */

#define SB_VELOCITY_PROJECTION_DELTA              14.0  /* Deceleration rate s^-1 */
#define SB_RUBBERBAND_COEFF                        0.55
#define SB_RUBBERBAND_ASYMPTOTE_PT                 SB_DISPLAY_HEIGHT_PT /* 874.0: lim_{x->inf} (x*c*d)/(d+c*x) = d */
#define SB_INTERACTIVE_CARD_SCALE_SWITCHER         0.80
#define SB_INTERACTIVE_CARD_SCALE_MAX_TRAVEL_PT    400.0
#define SB_EDGE_PROTECT_TIMEOUT_S                  1.2
#define SB_SPRING_MASS_KG                          1.0
#define SB_SPRING_STIFFNESS_NPM                  380.0
#define SB_SPRING_DAMPING_RATIO                    0.88

#define SB_DECK_Y_BASE_PT                        454.48
#define SB_DECK_DELTA_Y_PT                        64.0
#define SB_DECK_DELTA_Z_PT                        40.0
#define SB_DECK_SCALE_DECAY_PER_CARD               0.082
#define SB_DECK_SCALE_MIN_CLAMP                    0.65
#define SB_CARD_RESTING_CORNER_RADIUS_PT          44.0
#define SB_ICON_CORNER_RADIUS_PT                  13.5
#define SB_ICON_WIDTH_PT                          60.0
#define SB_ICON_HEIGHT_PT                         60.0

#define SB_MAX_PARTICIPANTS                       16
#define SB_MAX_MODIFIERS                          32

/* ========================================================================= */
/* Core Data Types & Geometry                                                */
/* ========================================================================= */

typedef struct {
    double x;
    double y;
} sb_point_t;

typedef struct {
    double width;
    double height;
} sb_size_t;

typedef struct {
    sb_point_t origin;
    sb_size_t size;
} sb_rect_t;

/**
 * @brief Homogeneous 2D Affine Transformation (CGAffineTransform representation)
 * [x', y', 1] = [x, y, 1] * [[a, b, 0], [c, d, 0], [tx, ty, 1]]
 */
typedef struct {
    double a;
    double b;
    double c;
    double d;
    double tx;
    double ty;
} sb_affine_transform_t;

/* ========================================================================= */
/* Harmonic Oscillator Parameters                                            */
/* ========================================================================= */

typedef struct {
    double mass;
    double stiffness;
    double damping_ratio;
    double damping_coefficient;
    double omega_n;
    double omega_d;
    double gamma;
} sb_spring_params_t;

/* ========================================================================= */
/* Gesture State & Final Destination Enumerations                            */
/* ========================================================================= */

typedef enum {
    SB_HOME_GESTURE_STATE_POSSIBLE = 0,
    SB_HOME_GESTURE_STATE_BEGAN,
    SB_HOME_GESTURE_STATE_TRACKING_HOME,
    SB_HOME_GESTURE_STATE_PAUSED_IN_SWITCHER,
    SB_HOME_GESTURE_STATE_TRACKING_SWITCHER,
    SB_HOME_GESTURE_STATE_ARC_SWIPE,
    SB_HOME_GESTURE_STATE_COMMITTED_HOME,
    SB_HOME_GESTURE_STATE_COMMITTED_SWITCHER,
    SB_HOME_GESTURE_STATE_CANCELLED_RETURN,
    SB_HOME_GESTURE_STATE_ENDED
} sb_home_gesture_state_t;

typedef enum {
    SB_DESTINATION_UNKNOWN = 0,
    SB_DESTINATION_HOME_SCREEN,
    SB_DESTINATION_APP_SWITCHER,
    SB_DESTINATION_RETURN_TO_APPLICATION,
    SB_DESTINATION_ARC_PREVIOUS_APP,
    SB_DESTINATION_ARC_NEXT_APP
} sb_home_gesture_destination_t;

/* ========================================================================= */
/* Participant Priority Arbitration                                          */
/* ========================================================================= */

typedef enum {
    SB_PARTICIPANT_PRIORITY_HOME_SCREEN       = 0,
    SB_PARTICIPANT_PRIORITY_APPLICATION       = 10,
    SB_PARTICIPANT_PRIORITY_FLOATING_DOCK     = 20,
    SB_PARTICIPANT_PRIORITY_SYSTEM_MODAL      = 50,
    SB_PARTICIPANT_PRIORITY_DYNAMIC_ISLAND    = 80,
    SB_PARTICIPANT_PRIORITY_COVERSHEET        = 100
} sb_participant_priority_t;

typedef struct {
    int participant_id;
    const char *identifier;
    sb_participant_priority_t priority;
    bool wants_home_gesture;
    bool owns_home_gesture;
    bool requires_double_swipe;
} sb_home_gesture_participant_t;

typedef struct {
    sb_home_gesture_participant_t participants[SB_MAX_PARTICIPANTS];
    size_t count;
    int current_owner_id;
} sb_participant_registry_t;

/* ========================================================================= */
/* Gesture Recognizer State                                                  */
/* ========================================================================= */

typedef struct {
    sb_home_gesture_state_t state;
    sb_point_t touch_start;
    sb_point_t touch_current;
    sb_point_t translation;
    sb_point_t velocity;
    double touch_start_timestamp;
    double current_timestamp;
    double dwell_duration_ms;
    double stationary_dwell_duration_ms;
    bool ever_translated_upward;
    bool hold_timer_fired;
    bool exclusion_trapezoid_violation;
    bool edge_protect_active;
    double edge_protect_last_swipe_timestamp;
    bool edge_protect_affordance_revealed;
    sb_home_gesture_destination_t resolved_destination;
} sb_home_gesture_pan_recognizer_t;

/* ========================================================================= */
/* Card Deck Geometry Layout                                                 */
/* ========================================================================= */

typedef struct {
    size_t card_index;
    double scale;
    double z_depth;
    double y_offset;
    double alpha;
    double corner_radius;
} sb_deck_card_layout_t;

/* ========================================================================= */
/* Match-Move Transform Morphing                                             */
/* ========================================================================= */

typedef struct {
    sb_rect_t source_card_bounds;
    sb_rect_t target_icon_bounds;
    sb_affine_transform_t final_transform;
    sb_affine_transform_t current_transform;
    double start_corner_radius;
    double target_corner_radius;
    double current_corner_radius;
    double progress;
} sb_match_move_transform_t;

/* ========================================================================= */
/* Switcher Modifier Architecture                                            */
/* ========================================================================= */

typedef enum {
    SB_MODIFIER_EVENT_GESTURE = 1,
    SB_MODIFIER_EVENT_TRANSITION,
    SB_MODIFIER_EVENT_TIMER
} sb_modifier_event_type_t;

typedef struct {
    sb_modifier_event_type_t type;
    sb_home_gesture_state_t gesture_state;
    sb_point_t touch_location;
    sb_point_t translation;
    sb_point_t velocity;
    double timestamp;
} sb_switcher_modifier_event_t;

typedef enum {
    SB_RESPONSE_NONE = 0,
    SB_RESPONSE_ADD_MODIFIER = (1 << 0),
    SB_RESPONSE_REMOVE_MODIFIER = (1 << 1),
    SB_RESPONSE_REQUEST_MATCH_MOVE_TO_ICON = (1 << 2),
    SB_RESPONSE_NOTIFY_ICON_WILL_ZOOM_DOWN = (1 << 3),
    SB_RESPONSE_INJECT_VELOCITY = (1 << 4),
    SB_RESPONSE_REMOVE_FROM_DESKTOP = (1 << 5)
} sb_modifier_event_response_flags_t;

typedef struct {
    sb_modifier_event_response_flags_t response_flags;
    sb_point_t injected_velocity;
    int target_modifier_id;
} sb_switcher_modifier_event_response_t;

typedef struct sb_modifier {
    int modifier_id;
    const char *name;
    bool is_active;
    sb_switcher_modifier_event_response_t (*handle_event)(struct sb_modifier *self, const sb_switcher_modifier_event_t *event);
} sb_modifier_t;

typedef struct {
    sb_modifier_t *stack[SB_MAX_MODIFIERS];
    size_t count;
} sb_switcher_modifier_stack_t;

/* ========================================================================= */
/* Function Declarations: Spring Physics                                     */
/* ========================================================================= */

void sb_spring_params_init(sb_spring_params_t *params, double mass, double stiffness, double damping_ratio);
double sb_spring_solve_position(const sb_spring_params_t *params, double x0, double v0, double t);
double sb_spring_solve_velocity(const sb_spring_params_t *params, double x0, double v0, double t);

/* ========================================================================= */
/* Function Declarations: Home Gesture Recognizer                            */
/* ========================================================================= */

void sb_home_gesture_recognizer_init(sb_home_gesture_pan_recognizer_t *recognizer);
bool sb_home_gesture_touches_began(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp);
bool sb_home_gesture_touches_moved(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp);
sb_home_gesture_destination_t sb_home_gesture_touches_ended(sb_home_gesture_pan_recognizer_t *rec, double x, double y, double timestamp);
void sb_home_gesture_dwell_timer_fired(sb_home_gesture_pan_recognizer_t *rec);
void sb_home_gesture_set_edge_protect(sb_home_gesture_pan_recognizer_t *rec, bool active);

/* ========================================================================= */
/* Function Declarations: Participant Priority Arbitration                   */
/* ========================================================================= */

void sb_participant_registry_init(sb_participant_registry_t *reg);
bool sb_participant_register(sb_participant_registry_t *reg, int id, const char *ident, sb_participant_priority_t prio, bool double_swipe);
bool sb_participant_unregister(sb_participant_registry_t *reg, int id);
bool sb_participant_set_wants_gesture(sb_participant_registry_t *reg, int id, bool wants);
int sb_participant_arbitrate(sb_participant_registry_t *reg);

/* ========================================================================= */
/* Function Declarations: Deck Switcher Geometry Math                        */
/* ========================================================================= */

double sb_deck_card_scale(size_t index);
double sb_interactive_card_scale(double delta_y);
double sb_deck_card_depth(size_t index);
double sb_deck_card_offset(size_t index);
double sb_deck_offset_curve(double t, double y0, double v0, const sb_spring_params_t *params);
double sb_deck_rubberband(double x, double dimension, double coefficient);
double sb_deck_rubberband_inverse(double fx, double dimension, double coefficient);
double sb_continuous_corner_radius(double delta_y, double r_start, double r_end, double morph_threshold);
void sb_deck_layout_compute_card(size_t index, sb_deck_card_layout_t *out_layout);

/* ========================================================================= */
/* Function Declarations: Velocity Projection & Destination Gating           */
/* ========================================================================= */

void sb_velocity_project_landing(sb_point_t release_pos, sb_point_t release_vel, double delta, sb_point_t *out_projected_pos);
sb_home_gesture_destination_t sb_determine_final_destination(sb_point_t release_pos, sb_point_t release_vel, double dwell_ms, bool hold_fired);

/* ========================================================================= */
/* Function Declarations: Match-Move Affine Transformation                   */
/* ========================================================================= */

sb_affine_transform_t sb_affine_transform_identity(void);
sb_point_t sb_affine_transform_point(sb_affine_transform_t t, sb_point_t p);
void sb_match_move_compute(sb_rect_t source_card, sb_rect_t target_icon, sb_match_move_transform_t *out_transform);
void sb_match_move_interpolate(sb_match_move_transform_t *transform, double progress);

/* ========================================================================= */
/* Function Declarations: Switcher Modifier Pipeline                         */
/* ========================================================================= */

void sb_modifier_stack_init(sb_switcher_modifier_stack_t *stack);
bool sb_modifier_stack_push(sb_switcher_modifier_stack_t *stack, sb_modifier_t *modifier);
bool sb_modifier_stack_pop(sb_switcher_modifier_stack_t *stack, sb_modifier_t **out_modifier);
sb_switcher_modifier_event_response_t sb_modifier_stack_handle_event(sb_switcher_modifier_stack_t *stack, const sb_switcher_modifier_event_t *event);

#ifdef __cplusplus
}
#endif

#endif /* SB_FLUID_SWITCHER_H */
