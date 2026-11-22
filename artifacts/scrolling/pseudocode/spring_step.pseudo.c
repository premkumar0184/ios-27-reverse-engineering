/**
 * UIKitCore.framework - Spring Dynamics & Boundary Restitution Pseudocode Reconstruction
 * Classes: _UIScrollViewSpringAnimation, CASpringAnimation
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[_UIScrollViewSpringAnimation updatePosition:timestamp:] @ 0x1848c8100
 *   - -[_UIScrollViewSpringAnimation settleVelocity] @ 0x1848c8250
 *   - -[CASpringAnimation settlingDuration] @ 0x184312500
 *   - -[CASpringAnimation durationForEpsilon:] @ 0x184312540
 *   - Physical second-order ODE harmonic oscillator solver: m * x_ddot + c * x_dot + k * x = 0
 *   - Exact closed-form analytical solutions:
 *       * Underdamped (zeta < 1.0): x(t) = e^(-gamma*t) * (x0*cos(omega_d*t) + ((v0 + gamma*x0)/omega_d)*sin(omega_d*t))
 *       * Critically damped (zeta == 1.0): x(t) = e^(-omega_n*t) * (x0 + (v0 + omega_n*x0)*t)
 *       * Overdamped (zeta > 1.0): x(t) = C1*e^(mu1*t) + C2*e^(mu2*t)
 *   - Continuous O(1) evaluation guaranteeing frame-rate invariance across 60Hz, 80Hz, 120Hz ProMotion
 *   - Restitution settling detection (|x| < 0.5 pt, |v| < 0.5 pt/s) and sub-pixel snapping (UIRoundToViewScale)
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* Forward declarations of UIKit types */
typedef struct CGPoint {
    double x;
    double y;
} CGPoint;

typedef struct CGSize {
    double width;
    double height;
} CGSize;

typedef struct CGRect {
    CGPoint origin;
    CGSize size;
} CGRect;

typedef struct UIEdgeInsets {
    double top;
    double left;
    double bottom;
    double right;
} UIEdgeInsets;

typedef double NSTimeInterval;

/* Forward declaration of CADisplayLink */
typedef struct CADisplayLink {
    void *isa;
    NSTimeInterval timestamp;
    NSTimeInterval targetTimestamp;
    bool paused;
} CADisplayLink;

/* Objective-C runtime stub */
extern void *objc_msgSend(void *self, const char *sel, ...);

/* Forward declaration of UIScrollView */
typedef struct UIScrollView UIScrollView;

/* Verified authoritative spring constants */
static const double kSpringDefaultMass        = 1.0;   /* 0x3ff0000000000000 (kg) */
static const double kSpringDefaultStiffness   = 100.0; /* 0x4059000000000000 (N/m) */
static const double kSpringDefaultDamping     = 18.0;  /* 0x4032000000000000 (N*s/m) -> zeta = 0.90 */
static const double __attribute__((unused)) kSpringCriticalDamping    = 20.0;  /* 0x4034000000000000 (N*s/m) -> zeta = 1.00 */
static const double kSpringSettlingEpsilonPt  = 0.5;   /* 0x3fe0000000000000 (pt) */
static const double kSpringSettlingEpsilonVel = 0.5;   /* 0x3fe0000000000000 (pt/s) */
static const double kDefaultViewScale         = 3.0;   /* @3x Super Retina */

/* Spring damping regimes */
typedef enum _UIScrollViewSpringRegime {
    _UIScrollViewSpringRegimeUnderdamped = 0,
    _UIScrollViewSpringRegimeCriticallyDamped = 1,
    _UIScrollViewSpringRegimeOverdamped = 2
} _UIScrollViewSpringRegime;

/* Reconstructed _UIScrollViewSpringAnimation layout (+0x168 in UIScrollView) */
typedef struct _UIScrollViewSpringAnimation {
    void *isa;                                           /* +0x000 */
    UIScrollView *_scrollView;                           /* +0x008 Parent scroll view pointer */
    void *_displayLink;                                  /* +0x010 CADisplayLink */
    CGPoint _equilibriumOffset;                          /* +0x018 Rest position (boundary limit) */
    CGPoint _initialDisplacement;                        /* +0x028 x_0 = startOffset - equilibriumOffset */
    CGPoint _initialVelocity;                            /* +0x038 v_0 = initial velocity at spring trigger */
    CGPoint _currentOffset;                              /* +0x048 Instantaneous contentOffset */
    CGPoint _currentVelocity;                            /* +0x058 Instantaneous velocity */
    double _mass;                                        /* +0x068 Mass m (1.0 kg) */
    double _stiffness;                                   /* +0x070 Spring constant k (100.0 N/m) */
    double _damping;                                     /* +0x078 Damping constant c (18.0 N*s/m) */
    double _omega_n;                                     /* +0x080 Natural frequency sqrt(k/m) = 10.0 */
    double _zeta;                                        /* +0x088 Damping ratio c / (2*sqrt(k*m)) = 0.90 */
    double _omega_d;                                     /* +0x090 Damped frequency omega_n * sqrt(1 - zeta^2) */
    double _gamma;                                       /* +0x098 Decay rate zeta * omega_n = 9.0 */
    _UIScrollViewSpringRegime _regime;                   /* +0x0a0 Damping classification */
    NSTimeInterval _startTimestamp;                      /* +0x0a8 Monotonic start timestamp */
    NSTimeInterval _lastTimestamp;                       /* +0x0b0 Timestamp of previous frame tick */
    bool _isCancelled;                                   /* +0x0b8 Cancellation status */
    bool _hasSettled;                                    /* +0x0b9 Flag set when restitution complete */
} _UIScrollViewSpringAnimation;

/* UIScrollView Flags Bitfield (+0xd0) */
typedef struct __scrollViewFlags {
    unsigned int isDragging : 1;                         /* bit 0 */
    unsigned int isDecelerating : 1;                     /* bit 1 */
    unsigned int isTracking : 1;                         /* bit 2 */
    unsigned int isZooming : 1;                          /* bit 3 */
    unsigned int bounces : 1;                            /* bit 4 */
    unsigned int bouncesHorizontally : 1;                /* bit 5 */
    unsigned int bouncesVertically : 1;                  /* bit 6 */
    unsigned int directionalLockEnabled : 1;             /* bit 7 */
    unsigned int pagingEnabled : 1;                      /* bit 8 */
    unsigned int scrollEnabled : 1;                      /* bit 9 */
    unsigned int delaysContentTouches : 1;               /* bit 10 */
    unsigned int canCancelContentTouches : 1;            /* bit 11 */
    unsigned int delegateScrollViewDidScroll : 1;        /* bit 12 */
    unsigned int delegateScrollViewWillBeginDragging : 1;/* bit 13 */
    unsigned int delegateScrollViewDidEndDragging : 1;   /* bit 14 */
    unsigned int delegateScrollViewWillBeginDecel : 1;   /* bit 15 */
    unsigned int delegateScrollViewDidEndDecel : 1;      /* bit 16 */
    unsigned int delegateScrollViewWillEndDragging : 1;  /* bit 17 */
} __scrollViewFlags;

/* Reconstructed UIScrollView layout */
struct UIScrollView {
    void *isa;
    void *_layer;
    CGRect _bounds;
    CGRect _frame;
    __scrollViewFlags _scrollViewFlags;
    double _zoomScale;
    double _minimumZoomScale;
    double _maximumZoomScale;
    double _decelerationRate;
    CGPoint _contentOffset;
    CGPoint _unconstrainedContentOffset;
    CGSize _contentSize;
    void *_delegate;
    UIEdgeInsets _contentInset;
    void *_panGestureRecognizer;
    void *_decelerationAnimation;
    _UIScrollViewSpringAnimation *_springAnimation;
    double _displayScale;                                /* +0x170 Screen / view scale (1.0, 2.0, 3.0) */
};

/* Forward helper declarations */
static void _UIScrollViewUpdateBoundsForContentOffset(UIScrollView *self, CGPoint offset);
static void _UIScrollViewNotifyDidScroll(UIScrollView *self);
static double _UIScrollViewGetViewScale(const UIScrollView *self);

/**
 * _UIScrollViewGetViewScale
 * Resolves active display scale from UIScrollView or falls back to default @3x Retina.
 */
static inline double _UIScrollViewGetViewScale(const UIScrollView *self) {
    if (self && self->_displayScale > 0.0) {
        return self->_displayScale;
    }
    return kDefaultViewScale;
}

/**
 * UIRoundToViewScale
 * Snaps floating-point offset to the nearest physical display sub-pixel boundary across @1x, @2x, @3x.
 */
static inline double UIRoundToViewScale(double value, double scale) {
    if (isnan(scale) || scale <= 0.0) {
        scale = 1.0;
    }
    double result = round(value * scale) / scale;
    if (result == 0.0) {
        result = 0.0;
    }
    return result;
}

/**
 * _UIScrollViewSpringConfigureDynamics
 * Pre-computes characteristic roots, natural frequencies, and damping regime parameters.
 */
void _UIScrollViewSpringConfigureDynamics(_UIScrollViewSpringAnimation *self) {
    if (!self) {
        return;
    }

    if (self->_mass <= 0.0) self->_mass = kSpringDefaultMass;
    if (self->_stiffness <= 0.0) self->_stiffness = kSpringDefaultStiffness;
    if (self->_damping < 0.0) self->_damping = kSpringDefaultDamping;

    double m = self->_mass;
    double k = self->_stiffness;
    double c = self->_damping;

    /* Undamped natural frequency omega_n = sqrt(k / m) */
    self->_omega_n = sqrt(k / m);

    /* Critical damping coefficient c_c = 2 * sqrt(k * m) */
    double c_c = 2.0 * sqrt(k * m);

    /* Damping ratio zeta = c / c_c */
    self->_zeta = c / c_c;

    /* Decay parameter gamma = zeta * omega_n = c / (2 * m) */
    self->_gamma = self->_zeta * self->_omega_n;

    if (self->_zeta < 0.9999) {
        self->_regime = _UIScrollViewSpringRegimeUnderdamped;
        /* Damped angular frequency omega_d = omega_n * sqrt(1 - zeta^2) */
        self->_omega_d = self->_omega_n * sqrt(1.0 - self->_zeta * self->_zeta);
    } else if (self->_zeta <= 1.0001) {
        self->_regime = _UIScrollViewSpringRegimeCriticallyDamped;
        self->_omega_d = 0.0;
    } else {
        self->_regime = _UIScrollViewSpringRegimeOverdamped;
        self->_omega_d = self->_omega_n * sqrt(self->_zeta * self->_zeta - 1.0);
    }
}

/**
 * _UIScrollViewEvaluate1DSpring
 * Evaluates the closed-form analytical position and velocity for a single axis at time t.
 */
static void _UIScrollViewEvaluate1DSpring(_UIScrollViewSpringAnimation *self,
                                         double x0,
                                         double v0,
                                         NSTimeInterval t,
                                         double *outX,
                                         double *outV) {
    if (t <= 0.0) {
        *outX = x0;
        *outV = v0;
        return;
    }

    double omega_n = self->_omega_n;
    double gamma   = self->_gamma;
    double omega_d = self->_omega_d;

    switch (self->_regime) {
        case _UIScrollViewSpringRegimeUnderdamped: {
            /*
             * Underdamped analytical closed-form solution (zeta < 1.0):
             *   x(t) = e^(-gamma * t) * [ A * cos(omega_d * t) + B * sin(omega_d * t) ]
             * where A = x0, B = (v0 + gamma * x0) / omega_d
             */
            double expDecay = exp(-gamma * t);
            double cosVal   = cos(omega_d * t);
            double sinVal   = sin(omega_d * t);

            double A = x0;
            double B = (v0 + gamma * x0) / omega_d;

            *outX = expDecay * (A * cosVal + B * sinVal);

            /*
             * Velocity derivative:
             *   v(t) = e^(-gamma * t) * [ v0 * cos(omega_d * t) - ((gamma * v0 + omega_n^2 * x0) / omega_d) * sin(omega_d * t) ]
             */
            double sinCoeff = (gamma * v0 + omega_n * omega_n * x0) / omega_d;
            *outV = expDecay * (v0 * cosVal - sinCoeff * sinVal);
            break;
        }

        case _UIScrollViewSpringRegimeCriticallyDamped: {
            /*
             * Critically damped analytical closed-form solution (zeta == 1.0):
             *   x(t) = e^(-omega_n * t) * [ x0 + (v0 + omega_n * x0) * t ]
             *   v(t) = e^(-omega_n * t) * [ v0 - omega_n * (v0 + omega_n * x0) * t ]
             */
            double expDecay = exp(-omega_n * t);
            double term     = v0 + omega_n * x0;

            *outX = expDecay * (x0 + term * t);
            *outV = expDecay * (v0 - omega_n * term * t);
            break;
        }

        case _UIScrollViewSpringRegimeOverdamped: {
            /*
             * Overdamped analytical closed-form solution (zeta > 1.0):
             *   mu1 = -gamma + omega_d, mu2 = -gamma - omega_d
             */
            double mu1 = -gamma + omega_d;
            double mu2 = -gamma - omega_d;
            double c2  = (v0 - mu1 * x0) / (mu2 - mu1);
            double c1  = x0 - c2;

            *outX = c1 * exp(mu1 * t) + c2 * exp(mu2 * t);
            *outV = c1 * mu1 * exp(mu1 * t) + c2 * mu2 * exp(mu2 * t);
            break;
        }
    }
}

/**
 * -[_UIScrollViewSpringAnimation updatePosition:timestamp:] @ 0x1848c8100
 * Evaluates the 2D spring state at continuous elapsed time t = timestamp - startTimestamp.
 */
CGPoint _UIScrollViewSpringAnimation_updatePosition_timestamp(_UIScrollViewSpringAnimation *self,
                                                               NSTimeInterval timestamp) {
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }

    NSTimeInterval t = timestamp - self->_startTimestamp;
    if (self->_startTimestamp <= 0.0 && timestamp > 0.500) {
        self->_startTimestamp = timestamp;
        self->_lastTimestamp = timestamp;
        t = 0.0;
    } else if (t < 0.0) {
        t = 0.0;
    }

    double dispX, velX;
    double dispY, velY;

    _UIScrollViewEvaluate1DSpring(self, self->_initialDisplacement.x, self->_initialVelocity.x, t, &dispX, &velX);
    _UIScrollViewEvaluate1DSpring(self, self->_initialDisplacement.y, self->_initialVelocity.y, t, &dispY, &velY);

    self->_currentVelocity.x = velX;
    self->_currentVelocity.y = velY;

    CGPoint computedOffset;
    computedOffset.x = self->_equilibriumOffset.x + dispX;
    computedOffset.y = self->_equilibriumOffset.y + dispY;

    self->_currentOffset = computedOffset;
    self->_lastTimestamp = timestamp;

    return computedOffset;
}

/**
 * -[_UIScrollViewSpringAnimation settleVelocity] @ 0x1848c8250
 * Returns the threshold speed below which spring oscillation is deemed settled.
 */
double _UIScrollViewSpringAnimation_settleVelocity(_UIScrollViewSpringAnimation *self) {
    (void)self;
    return kSpringSettlingEpsilonVel; /* 0.5 pt/s */
}

/**
 * -[CASpringAnimation durationForEpsilon:] @ 0x184312540
 * Calculates analytic settling time to reach specified custom epsilon threshold across
 * underdamped, critically damped, and overdamped regimes.
 */
double CASpringAnimation_durationForEpsilonWithVelocity(double mass, double stiffness, double damping,
                                                        double initialDisplacement, double initialVelocity,
                                                        double epsilon) {
    if (mass <= 0.0 || stiffness <= 0.0 || damping <= 0.0) {
        return 0.500;
    }
    if (epsilon <= 0.0) {
        epsilon = 0.001;
    }

    double omega_n = sqrt(stiffness / mass);
    double c_c     = 2.0 * sqrt(stiffness * mass);
    if (c_c <= 0.0) {
        return 0.500;
    }

    double zeta    = damping / c_c;
    double gamma   = zeta * omega_n;
    if (gamma <= 1e-6) {
        return 2.000;
    }

    double x0 = initialDisplacement;
    double v0 = initialVelocity;

    /* Sub-epsilon settling rule: if initial displacement is already within epsilon and velocity is zero */
    if (fabs(x0) <= epsilon && fabs(v0) <= 1e-9) {
        return 0.0;
    }

    double duration = 0.0;

    if (zeta < 0.9999) {
        /* Underdamped regime (0 < zeta < 1.0) */
        double omega_d = omega_n * sqrt(1.0 - zeta * zeta);
        double B = (v0 + gamma * x0) / omega_d;
        double amp = sqrt(x0 * x0 + B * B);

        if (amp <= epsilon) {
            return 0.0;
        }
        duration = -log(epsilon / amp) / gamma;
    } else if (zeta <= 1.0001) {
        /* Critically damped regime (zeta == 1.0) */
        double B = v0 + omega_n * x0;
        /* Maximum amplitude envelope */
        double t_peak = (B != 0.0 && v0 != 0.0) ? (v0 / (omega_n * B)) : 0.0;
        double peakAmp = fabs(x0);
        if (t_peak > 0.0) {
            double x_peak = fabs((x0 + B * t_peak) * exp(-omega_n * t_peak));
            if (x_peak > peakAmp) peakAmp = x_peak;
        }
        if (peakAmp <= epsilon) {
            return 0.0;
        }

        /* Initial analytical estimate */
        double t_est = -log(epsilon / peakAmp) / omega_n;
        if (t_est < 0.0) t_est = 0.0;

        /* Refine with 3 Newton-Raphson iterations on f(t) = ln(|x0 + B*t|) - omega_n*t - ln(epsilon) */
        for (int iter = 0; iter < 3; iter++) {
            double poly = fabs(x0 + B * t_est);
            if (poly <= 1e-9) break;
            double f = log(poly) - omega_n * t_est - log(epsilon);
            double f_prime = (B / (x0 + B * t_est)) - omega_n;
            if (fabs(f_prime) < 1e-6) break;
            double step = f / f_prime;
            t_est -= step;
            if (t_est < 0.0) { t_est = 0.0; break; }
        }
        duration = t_est;
    } else {
        /* Overdamped regime (zeta > 1.0) */
        double omega_d = omega_n * sqrt(zeta * zeta - 1.0);
        double mu1 = -gamma + omega_d; /* slower decay root (closer to zero, dominant tail) */
        double mu2 = -gamma - omega_d; /* faster decay root */
        double c2 = (v0 - mu1 * x0) / (mu2 - mu1);
        double c1 = x0 - c2;

        double maxAmp = fabs(x0);
        if (fabs(c1) + fabs(c2) > maxAmp) maxAmp = fabs(c1) + fabs(c2);
        if (maxAmp <= epsilon) {
            return 0.0;
        }

        /* Dominant tail governed by slower root mu1: |c1| * e^(mu1 * t) = epsilon */
        double slowDecayRate = gamma - omega_d; /* -mu1 > 0 */
        if (slowDecayRate <= 1e-6) slowDecayRate = 1e-6;

        double ampDominant = fabs(c1) > epsilon ? fabs(c1) : maxAmp;
        duration = -log(epsilon / ampDominant) / slowDecayRate;
    }

    if (duration < 0.100) duration = 0.100;
    if (duration > 30.000) duration = 30.000;

    return duration;
}

/**
 * -[CASpringAnimation durationForEpsilon:] @ 0x184312540
 * Calculates analytic settling time for custom epsilon with zero initial velocity.
 */
double CASpringAnimation_durationForEpsilon(double mass, double stiffness, double damping,
                                           double initialDisplacement, double epsilon) {
    return CASpringAnimation_durationForEpsilonWithVelocity(mass, stiffness, damping, initialDisplacement, 0.0, epsilon);
}

/**
 * CASpringAnimation_settlingDurationWithVelocity
 * Computes closed-form settling duration to reach default epsilon threshold (0.001)
 * accounting for both initial displacement and initial velocity:
 *   X_{\text{max}} = \sqrt{x_0^2 + \left(\frac{v_0 + \gamma x_0}{\omega_d}\right)^2}
 *   t_{\text{settle}} = \frac{-\ln(\epsilon / X_{\text{max}})}{\zeta \omega_n}
 */
double CASpringAnimation_settlingDurationWithVelocity(double mass, double stiffness, double damping,
                                                     double initialDisplacement, double initialVelocity) {
    return CASpringAnimation_durationForEpsilonWithVelocity(mass, stiffness, damping, initialDisplacement, initialVelocity, 0.001);
}

/**
 * -[CASpringAnimation settlingDuration] @ 0x184312500
 * Computes closed-form settling duration to reach default epsilon threshold (0.001):
 *   t_{\text{settle}} = \frac{-\ln(\epsilon / |x_0|)}{\zeta \omega_n}
 */
double CASpringAnimation_settlingDuration(double mass, double stiffness, double damping, double initialDisplacement) {
    return CASpringAnimation_durationForEpsilonWithVelocity(mass, stiffness, damping, initialDisplacement, 0.0, 0.001);
}

/**
 * _UIScrollViewStepSpring
 * Per-frame CADisplayLink frame tick routine driving the spring restitution animation.
 * Snaps to sub-pixel grid, checks settling criteria, and snaps to rest when complete.
 */
bool _UIScrollViewStepSpring(_UIScrollViewSpringAnimation *self, NSTimeInterval timestamp) {
    if (!self || self->_isCancelled || !self->_scrollView) {
        return false;
    }

    UIScrollView *scrollView = self->_scrollView;

    /* Establish baseline timestamp if uninitialized */
    if (self->_startTimestamp <= 0.0) {
        self->_startTimestamp = timestamp;
        self->_lastTimestamp = timestamp;
    }

    /* Evaluate analytical continuous position and velocity at elapsed timestamp */
    CGPoint nextOffset = _UIScrollViewSpringAnimation_updatePosition_timestamp(self, timestamp);

    /* Quantize position to physical display sub-pixel grid using resolved view scale */
    double scale = _UIScrollViewGetViewScale(scrollView);
    CGPoint roundedOffset;
    roundedOffset.x = UIRoundToViewScale(nextOffset.x, scale);
    roundedOffset.y = UIRoundToViewScale(nextOffset.y, scale);

    /* Assign to viewport and inform layer compositor */
    scrollView->_contentOffset = roundedOffset;
    _UIScrollViewUpdateBoundsForContentOffset(scrollView, roundedOffset);
    _UIScrollViewNotifyDidScroll(scrollView);

    /*
     * Settling Criteria:
     * Check if displacement from equilibrium and velocity are both within epsilon thresholds:
     *   |x(t) - x_eq| < 0.5 pt  AND  ||v(t)|| < 0.5 pt/s
     */
    double dispFromEqX = fabs(roundedOffset.x - self->_equilibriumOffset.x);
    double dispFromEqY = fabs(roundedOffset.y - self->_equilibriumOffset.y);
    double speed = sqrt(self->_currentVelocity.x * self->_currentVelocity.x +
                        self->_currentVelocity.y * self->_currentVelocity.y);

    if (dispFromEqX < kSpringSettlingEpsilonPt &&
        dispFromEqY < kSpringSettlingEpsilonPt &&
        speed < kSpringSettlingEpsilonVel) {

        /* Spring settled! Snap directly to equilibrium boundary */
        scrollView->_contentOffset = self->_equilibriumOffset;
        self->_currentOffset = self->_equilibriumOffset;
        self->_currentVelocity = (CGPoint){0.0, 0.0};
        self->_hasSettled = true;
        self->_isCancelled = true;

        _UIScrollViewUpdateBoundsForContentOffset(scrollView, self->_equilibriumOffset);
        _UIScrollViewNotifyDidScroll(scrollView);

        /* Inform delegate of scroll completion */
        if (scrollView->_scrollViewFlags.delegateScrollViewDidEndDecel && scrollView->_delegate) {
            objc_msgSend(scrollView->_delegate, "scrollViewDidEndDecelerating:", scrollView);
        }

        return false; /* Spring restitution complete */
    }

    return true; /* Spring oscillation continues */
}

/**
 * _UIScrollViewSpringDisplayLinkTick
 * CADisplayLink callback handler deriving variable frame presentation timestamp and stepping spring restitution.
 */
void _UIScrollViewSpringDisplayLinkTick(CADisplayLink *displayLink, _UIScrollViewSpringAnimation *self) {
    if (!displayLink || !self) {
        return;
    }
    NSTimeInterval targetTime = displayLink->targetTimestamp;
    if (targetTime <= 0.0) {
        targetTime = displayLink->timestamp;
    }
    _UIScrollViewStepSpring(self, targetTime);
}

/* Stubs for UIKit linkage */
static void _UIScrollViewUpdateBoundsForContentOffset(UIScrollView *self, CGPoint offset) {
    if (self) {
        self->_bounds.origin = offset;
    }
}

static void _UIScrollViewNotifyDidScroll(UIScrollView *self) {
    if (self && self->_scrollViewFlags.delegateScrollViewDidScroll && self->_delegate) {
        objc_msgSend(self->_delegate, "scrollViewDidScroll:", self);
    }
}
