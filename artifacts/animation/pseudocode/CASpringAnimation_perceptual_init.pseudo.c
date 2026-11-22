// Clean-Room Pseudocode: CASpringAnimation initWithPerceptualDuration:bounce:
// Target Platform: iOS 27.2 (Darwin 24.2.0, Build 24B119, arm64e PAC00)
// Binary Source: QuartzCore.framework / CASpringAnimation.m

#include <math.h>
#include <stdbool.h>

typedef struct {
    double mass;
    double stiffness;
    double damping;
    double initialVelocity;
    double perceptualDuration;
    double bounce;
    bool allowsOverdamping;
} CASpringAnimationState;

/**
 * Designated Initializer for modern Apple spring animations.
 * Converts perceptual duration (d) and bounce (b) into physical ODE constants (m, k, c).
 *
 * @param self The CASpringAnimation instance
 * @param perceptualDuration The pace/period of primary oscillation in seconds (must be > 0.0)
 * @param bounce The elasticity coefficient in the range [-1.0, 1.0]
 * @return Initialized animation instance
 */
CASpringAnimationState* CASpringAnimation_initWithPerceptualDuration_bounce(
    CASpringAnimationState *self,
    double perceptualDuration,
    double bounce
) {
    if (!self) {
        return 0;
    }

    // 1. Guard against non-positive perceptual duration (enforce minimum clamp threshold)
    if (perceptualDuration <= 0.0001) {
        perceptualDuration = 0.0001;
    }

    // 2. Clamp bounce parameter to physical domain [-1.0, 1.0]
    if (bounce < -1.0) {
        bounce = -1.0;
    } else if (bounce > 1.0) {
        bounce = 1.0;
    }

    // Store high-level properties
    self->perceptualDuration = perceptualDuration;
    self->bounce = bounce;
    self->allowsOverdamping = true;
    self->initialVelocity = 0.0;

    // 3. Normalized unit mass invariant
    const double m = 1.0000000000000000; // 0x3ff0000000000000
    self->mass = m;

    // 4. Derive undamped natural angular frequency and stiffness
    // Formula: omega_n = 2 * PI / perceptualDuration
    // Stiffness: k = m * (omega_n)^2
    const double two_pi = 6.28318530717958647692;
    double omega_n = two_pi / perceptualDuration;
    double k = m * (omega_n * omega_n);
    self->stiffness = k;

    // 5. Derive dimensionless damping ratio (zeta) based on bounce polarity
    double zeta;
    if (bounce >= 0.0) {
        // Underdamped / critically damped regime (0.0 <= zeta <= 1.0)
        zeta = 1.0 - bounce;
    } else {
        // Overdamped regime (zeta > 1.0)
        zeta = 1.0 / (1.0 + bounce);
    }

    // 6. Calculate viscous damping coefficient (c)
    // Formula: c = 2 * m * omega_n * zeta
    double c = 2.0 * m * omega_n * zeta;
    self->damping = c;

    return self;
}
