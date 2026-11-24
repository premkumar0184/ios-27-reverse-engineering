/**
 * @file springboard_compositor_interface.h
 * @brief Clean-room C99 interface for Apple SpringBoard UI Compositor, System Aperture, and Fluid Switcher
 *
 * Architecture: Apple Silicon A19 Pro (t8150 / v57ap / iPhone 18,3)
 * Target OS: iOS 27.2 (Darwin Kernel Version 24.2.0, xnu-11215.61.5~2, Build 24B119)
 * Clean-Room Specification: SpringBoard.framework, SystemAperture.framework, FrontBoard.framework
 * Standard: ISO C99, freestanding-compatible, zero external dependencies except <stdint.h>, <stdbool.h>, <math.h>
 */

#ifndef SPRINGBOARD_COMPOSITOR_INTERFACE_H
#define SPRINGBOARD_COMPOSITOR_INTERFACE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * Display & Hardware Constraints (v57ap Platform)
 * ========================================================================= */

#define SB_DISPLAY_POINTS_WIDE              440.0
#define SB_DISPLAY_POINTS_HIGH             956.0
#define SB_DISPLAY_SCALE_FACTOR               3.0
#define SB_DISPLAY_PIXELS_WIDE             1320.0
#define SB_DISPLAY_PIXELS_HIGH             2868.0

#define SB_HARDWARE_CUTOUT_X               196.50
#define SB_HARDWARE_CUTOUT_Y                11.00
#define SB_HARDWARE_CUTOUT_WIDTH           120.00
#define SB_HARDWARE_CUTOUT_HEIGHT           35.00
#define SB_HARDWARE_CUTOUT_RADIUS           17.50

#define SB_ISLAND_SPLIT_LEADING_WIDTH       37.00
#define SB_ISLAND_SPLIT_LEADING_HEIGHT      35.00
#define SB_ISLAND_SPLIT_TRAILING_WIDTH      37.00
#define SB_ISLAND_SPLIT_TRAILING_HEIGHT     35.00
#define SB_ISLAND_SPLIT_GAP                  8.33
#define SB_ISLAND_SPLIT_LEADING_X          151.17  /* 196.50 - 37.00 - 8.33 */
#define SB_ISLAND_SPLIT_TRAILING_X         324.83  /* 196.50 + 120.00 + 8.33 */

#define SB_ISLAND_MINIMAL_WIDTH             35.00
#define SB_ISLAND_MINIMAL_HEIGHT            35.00
#define SB_ISLAND_MINIMAL_RADIUS            17.50

#define SB_ISLAND_EXPANDED_WIDTH           368.00
#define SB_ISLAND_EXPANDED_DEFAULT_HEIGHT  160.00
#define SB_ISLAND_EXPANDED_MAX_HEIGHT      214.00
#define SB_ISLAND_EXPANDED_CORNER_RADIUS    42.00
#define SB_ISLAND_EXPANDED_X                36.00  /* (440.0 - 368.0) / 2 */
#define SB_ISLAND_EXPANDED_Y                11.00

#define SB_FLUID_SWITCHER_SCALE_DECAY        0.082
#define SB_FLUID_SWITCHER_MIN_SCALE          0.650
#define SB_FLUID_SWITCHER_DEPTH_STEP        40.00
#define SB_FLUID_SWITCHER_Y_DISMISS_THRESH 180.00
#define SB_FLUID_SWITCHER_VELOCITY_DISMISS -1200.00

#define SB_SPRING_DEFAULT_MASS               1.00
#define SB_SPRING_DEFAULT_STIFFNESS        380.00  /* N/m */
#define SB_SPRING_DEFAULT_DAMPING_RATIO      0.88  /* zeta */

#define SB_WATCHDOG_LAUNCH_TIMEOUT_SEC      20.00
#define SB_WATCHDOG_TRANSITION_TIMEOUT_SEC  10.00
#define SB_WATCHDOG_TERMINATION_TIMEOUT_SEC  5.00

/* =========================================================================
 * Basic Geometry Types
 * ========================================================================= */

typedef struct sb_point {
    double x;
    double y;
} sb_point_t;

typedef struct sb_size {
    double width;
    double height;
} sb_size_t;

typedef struct sb_rect {
    sb_point_t origin;
    sb_size_t size;
} sb_rect_t;

typedef struct sb_inset {
    double top;
    double left;
    double bottom;
    double right;
} sb_inset_t;

/* =========================================================================
 * Dynamic Island (System Aperture) Enumerations & Structures
 * ========================================================================= */

typedef enum sb_island_layout_mode {
    SB_ISLAND_MODE_COMPACT_SINGLE = 0,
    SB_ISLAND_MODE_COMPACT_SPLIT  = 1,
    SB_ISLAND_MODE_MINIMAL        = 2,
    SB_ISLAND_MODE_EXPANDED       = 3,
    SB_ISLAND_MODE_STAGED_ALERT   = 4,
    SB_ISLAND_MODE_COUNT          = 5
} sb_island_layout_mode_t;

typedef enum sb_island_element_priority {
    SB_ISLAND_PRIORITY_BACKGROUND_TIMER   = 20,
    SB_ISLAND_PRIORITY_MEDIA_PLAYBACK     = 40,
    SB_ISLAND_PRIORITY_TURN_BY_TURN_NAV   = 60,
    SB_ISLAND_PRIORITY_INCOMING_CALL      = 80,
    SB_ISLAND_PRIORITY_SYSTEM_ALERT       = 100
} sb_island_element_priority_t;

typedef struct sb_island_element {
    uint32_t element_id;
    uint32_t client_pid;
    char client_bundle_id[64];
    sb_island_element_priority_t priority;
    sb_island_layout_mode_t preferred_layout_mode;
    bool has_leading_view;
    bool has_trailing_view;
    bool has_minimal_view;
    bool has_expanded_view;
    uint64_t submission_timestamp_mach_abs;
} sb_island_element_t;

typedef struct sb_island_layout_result {
    sb_island_layout_mode_t layout_mode;
    sb_rect_t container_frame;
    sb_rect_t leading_pill_frame;
    sb_rect_t trailing_pill_frame;
    sb_rect_t minimal_bubble_frame;
    sb_rect_t expanded_hud_frame;
    double corner_radius;
    bool pill_split_active;
    uint32_t primary_element_id;
    uint32_t secondary_element_id;
} sb_island_layout_result_t;

/* =========================================================================
 * Fluid Switcher Multitasking Enumerations & Structures
 * ========================================================================= */

typedef enum sb_switcher_card_state {
    SB_SWITCHER_CARD_STATE_INACTIVE     = 0,
    SB_SWITCHER_CARD_STATE_VISIBLE      = 1,
    SB_SWITCHER_CARD_STATE_FOCUSED      = 2,
    SB_SWITCHER_CARD_STATE_DISMISSING   = 3,
    SB_SWITCHER_CARD_STATE_KILLED       = 4
} sb_switcher_card_state_t;

typedef struct sb_switcher_card_frame {
    uint32_t app_index;
    char bundle_identifier[64];
    uint32_t process_id;
    sb_rect_t frame;
    double scale;
    double z_depth;
    double alpha;
    double corner_radius;
    sb_switcher_card_state_t state;
} sb_switcher_card_frame_t;

/* =========================================================================
 * Velocity-Preserving Spring Physics State & Integrator
 * ========================================================================= */

typedef struct sb_spring_parameters {
    double mass;             /**< Mass (kg), default 1.0 */
    double stiffness;        /**< Spring constant k (N/m), default 380.0 */
    double damping_ratio;    /**< Damping ratio zeta, default 0.88 */
    double initial_position; /**< Displacement x0 from equilibrium (pt) */
    double initial_velocity; /**< Release velocity v0 (pt/s) */
} sb_spring_parameters_t;

typedef struct sb_spring_state {
    double mass;
    double stiffness;
    double damping_ratio;
    double undamped_frequency; /**< omega_n = sqrt(k/m) */
    double damped_frequency;   /**< omega_d = omega_n * sqrt(1 - zeta^2) */
    double damping_coeff;      /**< c = 2 * zeta * sqrt(k*m) */
    double initial_position;   /**< Equilibrium offset x0 (pt) */
    double initial_velocity;   /**< Release velocity v0 (pt/s) */
    double position;           /**< Current x(t) */
    double velocity;           /**< Current v(t) */
    double elapsed_time;       /**< Accumulated time t (seconds) */
    bool is_settled;           /**< True when displacement and velocity are below threshold */
} sb_spring_state_t;

/* =========================================================================
 * FrontBoard Scene Lifecycle Enumerations & Structures
 * ========================================================================= */

typedef enum sb_scene_lifecycle_state {
    SB_SCENE_STATE_UNPREPARED          = 0,
    SB_SCENE_STATE_PREPARED            = 1,
    SB_SCENE_STATE_FOREGROUND_ACTIVE   = 2,
    SB_SCENE_STATE_FOREGROUND_INACTIVE = 3,
    SB_SCENE_STATE_BACKGROUND          = 4,
    SB_SCENE_STATE_DESTROYED           = 5,
    SB_SCENE_STATE_COUNT               = 6
} sb_scene_lifecycle_state_t;

typedef struct sb_scene_specification {
    char scene_identifier[64];
    char client_bundle_id[64];
    uint32_t workspace_id;
    sb_scene_lifecycle_state_t current_state;
    sb_rect_t scene_frame;
    uint32_t ca_context_id;
    double state_transition_timestamp_sec;
    double watchdog_deadline_sec;
    bool watchdog_expired;
} sb_scene_specification_t;

/* =========================================================================
 * Window Level Hierarchy (UIWindowLevel) & Hit-Testing
 * ========================================================================= */

typedef enum sb_window_level {
    SB_WINDOW_LEVEL_WALLPAPER             = -1000,
    SB_WINDOW_LEVEL_DESKTOP               = -500,
    SB_WINDOW_LEVEL_NORMAL                = 0,
    SB_WINDOW_LEVEL_DOCK                  = 100,
    SB_WINDOW_LEVEL_STATUS_BAR            = 1000,
    SB_WINDOW_LEVEL_NOTIFICATION_CENTER   = 1500,
    SB_WINDOW_LEVEL_CONTROL_CENTER        = 1800,
    SB_WINDOW_LEVEL_ALERT                 = 2000,
    SB_WINDOW_LEVEL_SYSTEM_APERTURE       = 2500,
    SB_WINDOW_LEVEL_PICTURE_IN_PICTURE    = 2800,
    SB_WINDOW_LEVEL_COVER_SHEET           = 3000,
    SB_WINDOW_LEVEL_CALL_SCREEN           = 3200,
    SB_WINDOW_LEVEL_SECURE_PINPAD         = 3500,
    SB_WINDOW_LEVEL_EMERGENCY_OVERLAY     = 4000
} sb_window_level_t;

typedef struct sb_compositor_window {
    uint32_t window_id;
    char window_title[48];
    double window_level;
    sb_rect_t frame;
    double alpha;
    bool hidden;
    bool user_interaction_enabled;
    uint32_t ca_context_id;
} sb_compositor_window_t;

typedef struct sb_hit_test_result {
    bool hit_detected;
    uint32_t hit_window_id;
    uint32_t hit_ca_context_id;
    double hit_window_level;
    sb_point_t local_point;
} sb_hit_test_result_t;

/* =========================================================================
 * Clean-Room Function Prototypes
 * ========================================================================= */

/**
 * @brief Initialize a 2D bounding rectangle with origin and size.
 */
sb_rect_t sb_rect_make(double x, double y, double width, double height);

/**
 * @brief Determine if a 2D point lies inside a rectangle.
 */
bool sb_rect_contains_point(sb_rect_t rect, sb_point_t point);

/**
 * @brief Compute Dynamic Island split and container coordinates for the given layout mode.
 *
 * @param mode Target layout mode (Mode 0 through Mode 4).
 * @param primary_id Identifier of primary element (e.g. Phone call).
 * @param secondary_id Identifier of secondary element (e.g. Timer) if split.
 * @param out_layout Pointer to output layout result structure.
 * @return true if computation succeeded, false on invalid parameter.
 */
bool sb_solve_island_layout(
    sb_island_layout_mode_t mode,
    uint32_t primary_id,
    uint32_t secondary_id,
    sb_island_layout_result_t *out_layout
);

/**
 * @brief Calculate card scale and z-depth for an app in the Fluid Switcher deck.
 *
 * Formula:
 *   scale(i) = clamp(1.0 - i * 0.082, 0.65, 1.0)
 *   z(i) = -i * 40.0 pt
 *
 * @param app_index Index in the switcher stack (0 is active foreground, 1 is previous).
 * @param out_scale Pointer to receive calculated scale factor.
 * @param out_z_depth Pointer to receive calculated z-depth in points.
 * @return true if calculated successfully.
 */
bool sb_solve_switcher_card_geometry(
    uint32_t app_index,
    double *out_scale,
    double *out_z_depth
);

/**
 * @brief Initialize a velocity-preserving damped harmonic oscillator spring.
 *
 * Parameters:
 *   mass = 1.0 kg
 *   stiffness = 380.0 N/m
 *   damping_ratio = 0.88
 *
 * @param params Pointer to initial spring parameters (initial displacement and velocity).
 * @param out_state Pointer to receive initialized spring state structure.
 * @return true on success, false on invalid parameters (e.g. non-positive mass/stiffness).
 */
bool sb_spring_init(
    const sb_spring_parameters_t *params,
    sb_spring_state_t *out_state
);

/**
 * @brief Evaluate exact analytical position and velocity of the damped spring at time t.
 *
 * x(t) = exp(-zeta * omega_n * t) * [x0 * cos(omega_d * t) + ((v0 + zeta * omega_n * x0) / omega_d) * sin(omega_d * t)]
 *
 * @param state Pointer to initialized spring state.
 * @param time_sec Elapsed time in seconds.
 * @param out_position Pointer to receive position x(t).
 * @param out_velocity Pointer to receive velocity v(t).
 * @return true on success.
 */
bool sb_spring_evaluate_analytical(
    const sb_spring_state_t *state,
    double time_sec,
    double *out_position,
    double *out_velocity
);

/**
 * @brief Advance spring state numerically by timestep dt using Runge-Kutta 4th Order (RK4).
 *
 * Preserves release velocity v0 and dampens towards target equilibrium position 0.0.
 *
 * @param state Pointer to spring state to be integrated in-place.
 * @param dt Timestep in seconds (e.g. 1.0 / 120.0 for 120 Hz ProMotion display).
 * @return true on success.
 */
bool sb_spring_integrate_rk4(
    sb_spring_state_t *state,
    double dt
);

/**
 * @brief Sort window list in-place by window level in ascending order (back to front).
 *
 * @param windows Array of compositor windows.
 * @param count Number of windows in array.
 */
void sb_sort_windows_by_level(
    sb_compositor_window_t *windows,
    size_t count
);

/**
 * @brief Perform hit-testing against a stack of compositor windows.
 *
 * Iterates front-to-back (highest window level first). Tests bounding box,
 * visibility (hidden == false), alpha threshold (> 0.01), and user interaction enabled.
 *
 * @param windows Array of compositor windows.
 * @param count Number of windows in array.
 * @param screen_point Point in screen coordinate space (pt).
 * @param out_result Pointer to receive hit-test outcome.
 * @return true if a window was hit, false if point fell through to desktop background.
 */
bool sb_hit_test_arbitrate(
    const sb_compositor_window_t *windows,
    size_t count,
    sb_point_t screen_point,
    sb_hit_test_result_t *out_result
);

/**
 * @brief Execute clean-room verification test suite asserting all invariants.
 *
 * @return 0 on success (all assertions passed), non-zero on failure.
 */
int sb_compositor_run_all_tests(void);

#ifdef __cplusplus
}
#endif

#endif /* SPRINGBOARD_COMPOSITOR_INTERFACE_H */
