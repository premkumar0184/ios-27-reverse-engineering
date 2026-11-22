// Clean-Room Pseudocode: CASpringAnimation settlingDuration
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
 * Computes the duration after which oscillation amplitude has decayed below threshold.
 * In iOS 27, CoreAnimation sets epsilon = 0.001 (0.1% of initial displacement).
 *
 * @param self The CASpringAnimation instance
 * @return Estimated settling duration in seconds
 */
double CASpringAnimation_settlingDuration(const CASpringAnimationState *self) {
    if (!self) {
        return 0.0;
    }

    double m = self->mass;
    double k = self->stiffness;
    double c = self->damping;

    // Safety checks against degenerate zero or negative physical values
    if (m <= 0.0 || k <= 0.0) {
        return 0.0;
    }

    // Natural frequency: omega_n = sqrt(k / m)
    double omega_n = sqrt(k / m);
    if (omega_n <= 0.0) {
        return 0.0;
    }

    // Damping ratio: zeta = c / (2 * sqrt(k * m))
    double zeta = c / (2.0 * sqrt(k * m));

    // Empirical completion threshold epsilon = 0.001 (1e-3)
    // -ln(0.001) = 6.907755278982137
    const double neg_log_epsilon = 6.907755278982137;

    if (zeta <= 0.0) {
        // Undamped system technically oscillates indefinitely
        return 100.0;
    }

    if (zeta < 1.0) {
        // Underdamped regime: Decay envelope is governed by exp(-zeta * omega_n * t)
        // t_settle = -ln(epsilon) / (zeta * omega_n)
        double settling_time = neg_log_epsilon / (zeta * omega_n);
        return settling_time;
    } else if (fabs(zeta - 1.0) < 1e-6) {
        // Critically damped regime: (1 + omega_n * t) * exp(-omega_n * t) <= epsilon
        // Approx: t_settle ≈ (neg_log_epsilon + 1.0) / omega_n
        double settling_time = (neg_log_epsilon + 1.0) / omega_n;
        return settling_time;
    } else {
        // Overdamped regime: Two real roots lambda_1, lambda_2 = -omega_n * (zeta +- sqrt(zeta^2 - 1))
        // Dominant decay root is the slower exponential decay rate:
        double sqrt_term = sqrt(zeta * zeta - 1.0);
        double dominant_rate = omega_n * (zeta - sqrt_term);
        if (dominant_rate <= 0.0) {
            dominant_rate = omega_n * 0.1;
        }
        double settling_time = neg_log_epsilon / dominant_rate;
        return settling_time;
    }
}
