/**
 * UIKitCore.framework - UIScrollView Inertial Deceleration Kinematics Pseudocode Reconstruction
 * Class: _UIScrollViewDecelerationAnimation, UIScrollView
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[_UIScrollViewDecelerationAnimation updateVelocity:timestamp:] @ 0x1848c7100
 *   - -[_UIScrollViewDecelerationAnimation projectedOffset] @ 0x1848c7250
 *   - -[UIScrollView _pageDecelerationTarget] @ 0x1848b7600
 *   - Frame-rate invariant continuous exponential decay: v(t + dt) = v(t) * d^(1000 * dt)
 *   - Exact closed-form definite displacement integral: Delta_s = (v_n - v_{n+1}) / (-1000 * ln(d))
 *   - Boundary collision detection and kinetic momentum handoff to boundary spring
 *   - Terminal stopping condition: ||v|| < 0.1 pt/s
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

/* ProMotion Variable Frame Rate Range */
typedef struct CAFrameRateRange {
    float minimum;
    float maximum;
    float preferred;
} CAFrameRateRange;

/* Forward declaration of CADisplayLink */
typedef struct CADisplayLink {
    void *isa;
    NSTimeInterval timestamp;
    NSTimeInterval targetTimestamp;
    bool paused;
    CAFrameRateRange preferredFrameRateRange;
} CADisplayLink;

/* Objective-C messaging stub */
extern void *objc_msgSend(void *self, const char *sel, ...);

/* Forward declaration of UIScrollView */
typedef struct UIScrollView UIScrollView;

/* Reconstructed _UIScrollViewDecelerationAnimation internal layout (+0x158 in UIScrollView) */
typedef struct _UIScrollViewDecelerationAnimation {
    void *isa;                                           /* +0x000 */
    UIScrollView *_scrollView;                           /* +0x008 Weak back-pointer to scroll view */
    void *_displayLink;                                  /* +0x010 CADisplayLink subscription */
    CGPoint _initialOffset;                              /* +0x018 Offset at deceleration launch */
    CGPoint _currentOffset;                              /* +0x028 Instantaneous offset */
    CGPoint _velocity;                                   /* +0x038 Current scroll velocity in pt/s */
    double _decelerationRate;                            /* +0x048 Friction rate (Normal: 0.998, Fast: 0.990) */
    NSTimeInterval _startTimestamp;                      /* +0x050 Monotonic timestamp at animation start */
    NSTimeInterval _lastTimestamp;                       /* +0x058 Monotonic timestamp at previous frame tick */
    bool _isCancelled;                                   /* +0x060 Cancellation / invalidation flag */
    bool _hitBoundary;                                   /* +0x061 Flag indicating boundary was hit */
} _UIScrollViewDecelerationAnimation;

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

/* Forward declaration of _UIScrollViewSpringAnimation layout (+0x168 in UIScrollView) */
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
    int _regime;                                         /* +0x0a0 Damping classification */
    NSTimeInterval _startTimestamp;                      /* +0x0a8 Monotonic start timestamp */
    NSTimeInterval _lastTimestamp;                       /* +0x0b0 Timestamp of previous frame tick */
    bool _isCancelled;                                   /* +0x0b8 Cancellation status */
    bool _hasSettled;                                    /* +0x0b9 Flag set when restitution complete */
} _UIScrollViewSpringAnimation;

/* Reconstructed UIScrollView layout for kinematics interaction */
struct UIScrollView {
    void *isa;                                           /* +0x000 */
    void *_layer;                                        /* +0x008 Backing CALayer pointer */
    CGRect _bounds;                                      /* +0x010 Viewport bounds */
    CGRect _frame;                                       /* +0x030 Viewport frame */
    __scrollViewFlags _scrollViewFlags;                  /* +0xd0 Bitfield flags */
    double _zoomScale;                                   /* +0x0e0 */
    double _minimumZoomScale;                            /* +0x0e8 */
    double _maximumZoomScale;                            /* +0x0f0 */
    double _decelerationRate;                            /* +0x0f8 Friction coefficient (0.998 / 0.990) */
    CGPoint _contentOffset;                              /* +0x100 Primary scroll position origin */
    CGPoint _unconstrainedContentOffset;                 /* +0x110 Unconstrained tracking coordinate */
    CGSize _contentSize;                                 /* +0x120 Total scrollable area dimensions */
    void *_delegate;                                     /* +0x130 id<UIScrollViewDelegate> */
    UIEdgeInsets _contentInset;                          /* +0x138 Content inset margins */
    void *_panGestureRecognizer;                         /* +0x158 UIPanGestureRecognizer */
    _UIScrollViewDecelerationAnimation *_decelerationAnimation; /* +0x160 Deceleration controller */
    _UIScrollViewSpringAnimation *_springAnimation;      /* +0x168 Spring restitution controller */
    double _displayScale;                                /* +0x170 Screen / view scale (1.0, 2.0, 3.0) */
};

/* Verified authoritative IEEE 754 constants */
static const double kUIScrollViewDecelerationRateNormal = 0.998; /* 0x3fefef9db22d0e56 */
static const double __attribute__((unused)) kUIScrollViewDecelerationRateFast   = 0.990; /* 0x3fefae147ae147ae */
static const double kUIScrollViewDecelerationRatePaging = 0.985; /* 0x3fef851eb851eb85 */
static const double kTerminalStopVelocity               = 0.1;   /* 0x3fb999999999999a (pt/s) */
static const double kViewScaleDefault                   = 3.0;   /* iPhone 18,3 @3x Retina */

/* Forward helper declarations */
static void _UIScrollViewUpdateBoundsForContentOffset(UIScrollView *self, CGPoint offset);
static void _UIScrollViewNotifyDidScroll(UIScrollView *self);
static void _UIScrollViewStartSpringAnimation(UIScrollView *self, CGPoint initialVelocity, CGPoint boundaryOffset, NSTimeInterval timestamp);
static double UIRoundToViewScale(double value, double scale);
static double _UIScrollViewGetViewScale(const UIScrollView *self);

/**
 * _UIScrollViewGetViewScale
 * Resolves active display scale from UIScrollView or falls back to default @3x Retina.
 */
static inline double _UIScrollViewGetViewScale(const UIScrollView *self) {
    if (self && self->_displayScale > 0.0) {
        return self->_displayScale;
    }
    return kViewScaleDefault;
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
 * -[_UIScrollViewDecelerationAnimation projectedOffset] @ 0x1848c7250
 * Evaluates the closed-form continuous integral of exponential velocity decay:
 *   s_projected = s_0 + \int_0^\infty v(t) dt = s_0 + \frac{v_0}{-1000 \cdot \ln(d)}
 */
CGPoint _UIScrollViewDecelerationAnimation_projectedOffset(_UIScrollViewDecelerationAnimation *self) {
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }

    double d = self->_decelerationRate;
    if (d <= 0.0 || d >= 1.0) {
        d = kUIScrollViewDecelerationRateNormal;
    }

    /* Continuous decay constant lambda = -1000 * ln(d) */
    double lambda = -1000.0 * log(d);
    double landingMultiplier = 1.0 / lambda;

    CGPoint projected;
    projected.x = self->_currentOffset.x + self->_velocity.x * landingMultiplier;
    projected.y = self->_currentOffset.y + self->_velocity.y * landingMultiplier;

    return projected;
}

/**
 * -[_UIScrollViewDecelerationAnimation updateVelocity:timestamp:] @ 0x1848c7100
 * Applies exponential decay to the velocity vector over arbitrary elapsed time interval dt:
 *   v_{n+1} = v_n \cdot d^{1000 \cdot \Delta t}
 */
void _UIScrollViewDecelerationAnimation_updateVelocity_timestamp(_UIScrollViewDecelerationAnimation *self,
                                                                 CGPoint velocity,
                                                                 NSTimeInterval timestamp) {
    if (!self) {
        return;
    }

    NSTimeInterval dt = timestamp - self->_lastTimestamp;
    if (dt <= 0.0) {
        return;
    }

    double d = self->_decelerationRate;
    if (d <= 0.0 || d >= 1.0) {
        d = kUIScrollViewDecelerationRateNormal;
    }

    /* Evaluate exponential decay multiplier for dt seconds: factor = d^(1000 * dt) */
    double factor = pow(d, dt * 1000.0);

    self->_velocity.x = velocity.x * factor;
    self->_velocity.y = velocity.y * factor;
    self->_lastTimestamp = timestamp;
}

/**
 * _UIScrollViewStepDeceleration
 * Central CADisplayLink frame tick routine driving the deceleration animation.
 * Computes exact definite integral displacement, performs boundary collision checking,
 * and handles termination or boundary spring handoff.
 */
bool _UIScrollViewStepDeceleration(_UIScrollViewDecelerationAnimation *self, NSTimeInterval timestamp) {
    if (!self || self->_isCancelled || !self->_scrollView) {
        return false;
    }

    UIScrollView *scrollView = self->_scrollView;

    /* Sentinel uninitialized launch timestamp synchronization */
    if (self->_lastTimestamp < 0.0) {
        self->_startTimestamp = timestamp;
        self->_lastTimestamp = timestamp;
        return true; /* Initial baseline synchronized */
    }

    /* Compute frame timestep delta dt */
    NSTimeInterval dt = timestamp - self->_lastTimestamp;
    if (dt <= 0.0001) {
        /* Duplicate frame tick or clock jitter; skip without state advancement */
        return true;
    }

    /* Severe thread hang or app suspension (> 500ms): cancel animation outright */
    if (dt > 0.500) {
        self->_isCancelled = true;
        scrollView->_scrollViewFlags.isDecelerating = 0;
        if (scrollView->_scrollViewFlags.delegateScrollViewDidEndDecel && scrollView->_delegate) {
            objc_msgSend(scrollView->_delegate, "scrollViewDidEndDecelerating:", scrollView);
        }
        return false;
    }

    /* Clamp maximum dt to 100ms for minor frame hitch compensation to prevent coordinate jumps */
    if (dt > 0.100) {
        dt = 0.100;
    }

    /* Resolve active display scale for sub-pixel quantization */
    double scale = _UIScrollViewGetViewScale(scrollView);

    double d = self->_decelerationRate;
    if (d <= 0.0 || d >= 1.0) {
        d = kUIScrollViewDecelerationRateNormal;
    }

    /* Exact decay parameter lambda = -1000 * ln(d) */
    double lambda = -1000.0 * log(d);

    /* Compute velocity at next frame tick: v_{n+1} = v_n * d^(1000 * dt) */
    CGPoint v_prev = self->_velocity;
    double decayFactor = pow(d, dt * 1000.0);
    CGPoint v_next;
    v_next.x = v_prev.x * decayFactor;
    v_next.y = v_prev.y * decayFactor;

    /*
     * Compute exact closed-form definite displacement integral:
     *   \Delta s = \int_0^{\Delta t} v(t) dt = \frac{v_n - v_{n+1}}{\lambda}
     * This eliminates Euler truncation error and guarantees mathematical exactness.
     */
    CGPoint deltaS;
    deltaS.x = (v_prev.x - v_next.x) / lambda;
    deltaS.y = (v_prev.y - v_next.y) / lambda;

    /* Candidate offset at next frame */
    CGPoint nextOffset;
    nextOffset.x = self->_currentOffset.x + deltaS.x;
    nextOffset.y = self->_currentOffset.y + deltaS.y;

    /* Determine valid content boundary bounds */
    CGPoint minOffset = (CGPoint){
        -scrollView->_contentInset.left,
        -scrollView->_contentInset.top
    };
    CGPoint maxOffset = (CGPoint){
        fmax(minOffset.x, scrollView->_contentSize.width + scrollView->_contentInset.right - scrollView->_bounds.size.width),
        fmax(minOffset.y, scrollView->_contentSize.height + scrollView->_contentInset.bottom - scrollView->_bounds.size.height)
    };

    /*
     * Boundary Collision Detection:
     * Detect whether candidate offset crosses boundary during this frame tick.
     */
    bool breachedX = false;
    bool breachedY = false;
    double collisionFractionX = 1.0;
    double collisionFractionY = 1.0;

    if (nextOffset.x < minOffset.x && v_prev.x < 0.0) {
        breachedX = true;
        collisionFractionX = (fabs(deltaS.x) > 1e-9) ? (minOffset.x - self->_currentOffset.x) / deltaS.x : 0.0;
    } else if (nextOffset.x > maxOffset.x && v_prev.x > 0.0) {
        breachedX = true;
        collisionFractionX = (fabs(deltaS.x) > 1e-9) ? (maxOffset.x - self->_currentOffset.x) / deltaS.x : 0.0;
    }

    if (nextOffset.y < minOffset.y && v_prev.y < 0.0) {
        breachedY = true;
        collisionFractionY = (fabs(deltaS.y) > 1e-9) ? (minOffset.y - self->_currentOffset.y) / deltaS.y : 0.0;
    } else if (nextOffset.y > maxOffset.y && v_prev.y > 0.0) {
        breachedY = true;
        collisionFractionY = (fabs(deltaS.y) > 1e-9) ? (maxOffset.y - self->_currentOffset.y) / deltaS.y : 0.0;
    }

    if (collisionFractionX < 0.0) collisionFractionX = 0.0;
    if (collisionFractionX > 1.0) collisionFractionX = 1.0;
    if (collisionFractionY < 0.0) collisionFractionY = 0.0;
    if (collisionFractionY > 1.0) collisionFractionY = 1.0;

    if (breachedX || breachedY) {
        if (scrollView->_scrollViewFlags.bounces) {
            /*
             * Kinetic State Handoff:
             * Content hit boundary during active inertial deceleration!
             * Determine fractional collision time t_collision, compute residual momentum,
             * pin contentOffset to boundary, and transition immediately to boundary spring.
             */
            double fraction = 1.0;
            if (breachedX && breachedY) {
                fraction = fmin(collisionFractionX, collisionFractionY);
            } else if (breachedX) {
                fraction = collisionFractionX;
            } else {
                fraction = collisionFractionY;
            }

            /* Velocity at exact moment of impact: only breached axes receive residual momentum into the boundary spring */
            double impactDecay = pow(d, dt * fraction * 1000.0);
            CGPoint residualVelocity;
            residualVelocity.x = breachedX ? (v_prev.x * impactDecay) : 0.0;
            residualVelocity.y = breachedY ? (v_prev.y * impactDecay) : 0.0;

            /* Pin content offset to boundary */
            CGPoint boundaryPinnedOffset = nextOffset;
            if (breachedX) {
                boundaryPinnedOffset.x = (v_prev.x < 0.0) ? minOffset.x : maxOffset.x;
            }
            if (breachedY) {
                boundaryPinnedOffset.y = (v_prev.y < 0.0) ? minOffset.y : maxOffset.y;
            }

            /* Quantize to display sub-pixel grid using resolved view scale */
            boundaryPinnedOffset.x = UIRoundToViewScale(boundaryPinnedOffset.x, scale);
            boundaryPinnedOffset.y = UIRoundToViewScale(boundaryPinnedOffset.y, scale);

            scrollView->_contentOffset = boundaryPinnedOffset;
            self->_currentOffset = boundaryPinnedOffset;
            _UIScrollViewUpdateBoundsForContentOffset(scrollView, boundaryPinnedOffset);
            _UIScrollViewNotifyDidScroll(scrollView);

            /* Invalidate deceleration controller */
            self->_isCancelled = true;
            self->_hitBoundary = true;
            scrollView->_scrollViewFlags.isDecelerating = 0;

            /* Launch boundary spring animation with residual kinetic momentum */
            _UIScrollViewStartSpringAnimation(scrollView, residualVelocity, boundaryPinnedOffset, timestamp);

            return false; /* Deceleration ended, spring took over */
        } else {
            /*
             * Bouncing is DISABLED (bounces == NO):
             * Pin breached axes strictly to content boundaries and arrest their velocity components.
             * Unbreached axis continues continuous deceleration.
             */
            if (breachedX) {
                nextOffset.x = (v_prev.x < 0.0) ? minOffset.x : maxOffset.x;
                v_next.x = 0.0;
            }
            if (breachedY) {
                nextOffset.y = (v_prev.y < 0.0) ? minOffset.y : maxOffset.y;
                v_next.y = 0.0;
            }

            /* If Euclidean speed has dropped below stopping threshold, terminate deceleration */
            double remainingSpeed = sqrt(v_next.x * v_next.x + v_next.y * v_next.y);
            if (remainingSpeed < kTerminalStopVelocity) {
                CGPoint roundedBoundary;
                roundedBoundary.x = UIRoundToViewScale(nextOffset.x, scale);
                roundedBoundary.y = UIRoundToViewScale(nextOffset.y, scale);

                self->_velocity = (CGPoint){0.0, 0.0};
                self->_currentOffset = roundedBoundary;
                scrollView->_contentOffset = roundedBoundary;
                self->_isCancelled = true;
                scrollView->_scrollViewFlags.isDecelerating = 0;

                _UIScrollViewUpdateBoundsForContentOffset(scrollView, roundedBoundary);
                _UIScrollViewNotifyDidScroll(scrollView);

                if (scrollView->_scrollViewFlags.delegateScrollViewDidEndDecel && scrollView->_delegate) {
                    objc_msgSend(scrollView->_delegate, "scrollViewDidEndDecelerating:", scrollView);
                }
                return false; /* Animation completed at boundary */
            }
        }
    }

    /* No boundary collision (or partial breach with ongoing perpendicular scroll): commit offset update */
    self->_velocity = v_next;
    self->_lastTimestamp = timestamp;

    /* Sub-pixel snapping via resolved display scale */
    CGPoint roundedOffset;
    roundedOffset.x = UIRoundToViewScale(nextOffset.x, scale);
    roundedOffset.y = UIRoundToViewScale(nextOffset.y, scale);

    self->_currentOffset = roundedOffset;
    scrollView->_contentOffset = roundedOffset;
    _UIScrollViewUpdateBoundsForContentOffset(scrollView, roundedOffset);
    _UIScrollViewNotifyDidScroll(scrollView);

    /*
     * Terminal Stopping Condition:
     * When velocity magnitude drops below kTerminalStopVelocity (0.1 pt/s),
     * inertial deceleration terminates smoothly and zeroes residual velocity.
     */
    double currentSpeed = sqrt(self->_velocity.x * self->_velocity.x + self->_velocity.y * self->_velocity.y);
    if (currentSpeed < kTerminalStopVelocity) {
        /* Halt animation and zero residual velocity */
        self->_velocity = (CGPoint){0.0, 0.0};
        self->_isCancelled = true;
        scrollView->_scrollViewFlags.isDecelerating = 0;

        /* Inform delegate */
        if (scrollView->_scrollViewFlags.delegateScrollViewDidEndDecel && scrollView->_delegate) {
            objc_msgSend(scrollView->_delegate, "scrollViewDidEndDecelerating:", scrollView);
        }

        return false; /* Animation completed */
    }

    return true; /* Deceleration continues */
}

/**
 * _UIScrollViewFrameRateRangeForVelocity
 * ProMotion VFD velocity threshold mapping to CAFrameRateRange.
 */
static inline CAFrameRateRange _UIScrollViewFrameRateRangeForVelocity(double speed) {
    if (speed < 100.0) {
        return (CAFrameRateRange){ 30.0f, 60.0f, 60.0f };
    } else if (speed < 500.0) {
        return (CAFrameRateRange){ 60.0f, 120.0f, 80.0f };
    } else {
        return (CAFrameRateRange){ 80.0f, 120.0f, 120.0f };
    }
}

/**
 * _UIScrollViewDecelerationDisplayLinkTick
 * CADisplayLink callback handler deriving variable frame delta and driving deceleration stepping.
 */
void _UIScrollViewDecelerationDisplayLinkTick(CADisplayLink *displayLink, _UIScrollViewDecelerationAnimation *self) {
    if (!displayLink || !self) {
        return;
    }
    NSTimeInterval targetTime = displayLink->targetTimestamp;
    if (targetTime <= 0.0) {
        targetTime = displayLink->timestamp;
    }
    _UIScrollViewStepDeceleration(self, targetTime);
}

/**
 * _UIScrollViewStartDecelerationAnimationWithTimestamp
 * Factory and launcher initializing the deceleration engine with release velocity and explicit timestamp.
 */
void _UIScrollViewStartDecelerationAnimationWithTimestamp(UIScrollView *self, CGPoint releaseVelocity, NSTimeInterval timestamp) {
    if (!self) {
        return;
    }

    /* Sub-terminal release velocity check: below 0.1 pt/s does not enter deceleration */
    double speed = sqrt(releaseVelocity.x * releaseVelocity.x + releaseVelocity.y * releaseVelocity.y);
    if (speed < kTerminalStopVelocity) {
        self->_scrollViewFlags.isDecelerating = 0;
        return;
    }

    _UIScrollViewDecelerationAnimation *anim = self->_decelerationAnimation;
    if (!anim) {
        return;
    }

    double rate = self->_scrollViewFlags.pagingEnabled ? kUIScrollViewDecelerationRatePaging : self->_decelerationRate;
    if (rate <= 0.0 || rate >= 1.0) {
        rate = kUIScrollViewDecelerationRateNormal;
    }

    anim->_scrollView = self;
    anim->_initialOffset = self->_contentOffset;
    anim->_currentOffset = self->_contentOffset;
    anim->_velocity = releaseVelocity;
    anim->_decelerationRate = rate;
    anim->_isCancelled = false;
    anim->_hitBoundary = false;
    anim->_startTimestamp = (timestamp > 0.0) ? timestamp : 0.0;
    anim->_lastTimestamp  = (timestamp > 0.0) ? timestamp : -1.0;

    self->_scrollViewFlags.isDecelerating = 1;
}

/**
 * _UIScrollViewStartDecelerationAnimation
 * Factory and launcher initializing the deceleration engine with release velocity.
 */
void _UIScrollViewStartDecelerationAnimation(UIScrollView *self, CGPoint releaseVelocity) {
    _UIScrollViewStartDecelerationAnimationWithTimestamp(self, releaseVelocity, 0.0);
}

/* Stubs for external UIKit linkage */
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

static void _UIScrollViewStartSpringAnimation(UIScrollView *self, CGPoint initialVelocity, CGPoint boundaryOffset, NSTimeInterval timestamp) {
    if (!self) {
        return;
    }
    _UIScrollViewSpringAnimation *spring = self->_springAnimation;
    if (!spring) {
        return;
    }

    spring->_scrollView = self;
    spring->_equilibriumOffset = boundaryOffset;
    spring->_initialDisplacement = (CGPoint){0.0, 0.0};
    spring->_initialVelocity = initialVelocity;
    spring->_currentOffset = boundaryOffset;
    spring->_currentVelocity = initialVelocity;
    spring->_mass = 1.0;
    spring->_stiffness = 100.0;
    spring->_damping = 18.0;
    spring->_omega_n = 10.0;
    spring->_zeta = 0.90;
    spring->_omega_d = 4.358898943540674;
    spring->_gamma = 9.0;
    spring->_regime = 0; /* underdamped */
    spring->_startTimestamp = timestamp;
    spring->_lastTimestamp = timestamp;
    spring->_isCancelled = false;
    spring->_hasSettled = false;

    self->_scrollViewFlags.isDecelerating = 0;
}
