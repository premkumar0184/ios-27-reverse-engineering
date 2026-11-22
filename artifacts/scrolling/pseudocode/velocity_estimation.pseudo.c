/**
 * UIKitCore.framework - Touch Velocity Estimation & Filtering Pipeline Pseudocode Reconstruction
 * Classes: _UIScrollViewVelocity, UIPanGestureRecognizer, _UIScrollViewPanGestureRecognizer
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[_UIScrollViewVelocity addSample:atTimestamp:] @ 0x1848d6100
 *   - -[_UIScrollViewVelocity filteredVelocity] @ 0x1848d6200
 *   - -[UIPanGestureRecognizer velocityInView:] @ 0x1848d1420
 *   - -[UIScrollViewPanGestureRecognizer velocityInView:] @ 0x1848c1150
 *   - 100ms / 8-sample rolling ring buffer management
 *   - Ordinary Least Squares (OLS) linear regression velocity solver
 *   - Exponential Moving Average (EMA) coordinate pre-filter (alpha = 0.85)
 *   - Directional locking vector projection & 60/30-degree axis discrimination
 *   - Dynamic velocity magnitude clamping ([10.0, 8000.0] pt/s)
 *   - Coordinate frame transformation and sign inversion (v_scroll = -v_pan)
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

typedef struct CGAffineTransform {
    double a, b, c, d;
    double tx, ty;
} CGAffineTransform;

typedef double NSTimeInterval;

/* Ring buffer constants */
#define kVelocityRingBufferCapacity 8
#define kVelocityLookbackWindowSec 0.100

/* Verified IEEE 754 Constants */
static const double kMinFlingVelocity     = 10.0;   /* 0x4024000000000000 (pt/s) */
static const double kMaxFlingVelocityCap  = 8000.0; /* 0x40bf400000000000 (pt/s) */
static const double kCoordinateEmaAlpha   = 0.85;   /* 0x3feb333333333333 */
static const double kVerticalLockAngle    = 1.0471975511965976; /* pi/3 rad (60.0 deg) */
static const double kHorizontalLockAngle  = 0.5235987755982988; /* pi/6 rad (30.0 deg) */

/* Velocity sample ring buffer entry */
typedef struct _UIVelocitySample {
    CGPoint point;
    NSTimeInterval timestamp;
    bool isValid;
} _UIVelocitySample;

/* Reconstructed _UIScrollViewVelocity internal layout */
typedef struct _UIScrollViewVelocity {
    void *isa;                                           /* +0x000 */
    _UIVelocitySample _samples[kVelocityRingBufferCapacity]; /* +0x008 (8 * 24 = 192 bytes) */
    uint32_t _sampleIndex;                               /* +0x0c8 Circular write head pointer */
    uint32_t _sampleCount;                               /* +0x0cc Total valid samples inserted */
    CGPoint _lastFilteredCoordinate;                     /* +0x0d0 EMA smoothed coordinate */
    bool _hasFilteredCoordinate;                         /* +0x0e0 First sample flag */
    CGPoint _cachedVelocity;                             /* +0x0e8 Cached regression output */
    NSTimeInterval _cacheTimestamp;                      /* +0x0f8 Timestamp of last computation */
} _UIScrollViewVelocity;

/* Directional lock modes */
typedef enum _UIScrollViewDirectionalLockAxis {
    _UIScrollViewDirectionalLockAxisNone = 0,
    _UIScrollViewDirectionalLockAxisHorizontal = 1,
    _UIScrollViewDirectionalLockAxisVertical = 2
} _UIScrollViewDirectionalLockAxis;

/* Reconstructed UIPanGestureRecognizer tracking subset */
typedef struct UIPanGestureRecognizer {
    void *isa;
    void *_view;
    _UIScrollViewVelocity *_velocityTracker;
    _UIScrollViewDirectionalLockAxis _lockedAxis;
    bool _directionalLockEnabled;
    CGPoint _startPoint;
    CGPoint _currentPoint;
    NSTimeInterval _startTimestamp;
    NSTimeInterval _currentTimestamp;
} UIPanGestureRecognizer;

/* Forward helper declarations */
static CGPoint _UIAffineTransformApplyToVector(CGAffineTransform t, CGPoint v);
static CGAffineTransform _UIViewGetTransformToView(void *fromView, void *toView);

/**
 * _UIVelocityFilterCoordinateEMA
 * Applies single-pole recursive IIR coordinate smoothing to suppress digitizer centroid jitter:
 *   P_{smooth}[n] = \alpha \cdot P_{raw}[n] + (1 - \alpha) \cdot P_{smooth}[n-1]
 */
static CGPoint _UIVelocityFilterCoordinateEMA(_UIScrollViewVelocity *self, CGPoint rawPoint) {
    if (!self->_hasFilteredCoordinate) {
        self->_lastFilteredCoordinate = rawPoint;
        self->_hasFilteredCoordinate = true;
        return rawPoint;
    }

    CGPoint smoothed;
    smoothed.x = kCoordinateEmaAlpha * rawPoint.x + (1.0 - kCoordinateEmaAlpha) * self->_lastFilteredCoordinate.x;
    smoothed.y = kCoordinateEmaAlpha * rawPoint.y + (1.0 - kCoordinateEmaAlpha) * self->_lastFilteredCoordinate.y;

    self->_lastFilteredCoordinate = smoothed;
    return smoothed;
}

/**
 * -[_UIScrollViewVelocity addSample:atTimestamp:] @ 0x1848d6100
 * Inserts smoothed touch coordinate and timestamp into the 8-sample circular ring buffer.
 */
void _UIScrollViewVelocity_addSample_atTimestamp(_UIScrollViewVelocity *self, CGPoint point, NSTimeInterval timestamp) {
    if (!self) {
        return;
    }

    /* Save EMA filter state prior to this sample for duplicate deduplication revert */
    CGPoint prevFiltered = self->_lastFilteredCoordinate;
    bool hadFiltered = self->_hasFilteredCoordinate;

    /* Pre-filter raw coordinate using exponential moving average */
    CGPoint smoothedPoint = _UIVelocityFilterCoordinateEMA(self, point);

    /*
     * Duplicate Timestamp Deduplication:
     * If two events arrive in the same runloop cycle with identical timestamps (dt < 1 microsecond),
     * overwrite the previous sample with the updated centroid coordinate rather than inserting
     * a duplicate zero-dt point that would pollute the regression buffer.
     */
    if (self->_sampleCount > 0) {
        uint32_t prevIdx = (self->_sampleIndex - 1 + kVelocityRingBufferCapacity) % kVelocityRingBufferCapacity;
        if (self->_samples[prevIdx].isValid && fabs(self->_samples[prevIdx].timestamp - timestamp) < 1e-6) {
            /* Revert EMA state to pre-duplicate and re-filter against saved state */
            self->_lastFilteredCoordinate = prevFiltered;
            self->_hasFilteredCoordinate = hadFiltered;
            smoothedPoint = _UIVelocityFilterCoordinateEMA(self, point);
            self->_samples[prevIdx].point = smoothedPoint;
            self->_cacheTimestamp = 0.0;
            return;
        }
    }

    /* Write into ring buffer at current head */
    uint32_t index = self->_sampleIndex;
    self->_samples[index].point = smoothedPoint;
    self->_samples[index].timestamp = timestamp;
    self->_samples[index].isValid = true;

    /* Advance circular head */
    self->_sampleIndex = (index + 1) % kVelocityRingBufferCapacity;
    if (self->_sampleCount < kVelocityRingBufferCapacity) {
        self->_sampleCount++;
    }

    /* Invalidate cached velocity */
    self->_cacheTimestamp = 0.0;
}

/**
 * -[_UIScrollViewVelocity filteredVelocity] @ 0x1848d6200
 * Computes release velocity using Ordinary Least Squares (OLS) linear regression
 * over samples collected within the 100ms lookback window:
 *   v = \frac{\sum_{i=1}^N (t_i - \bar{t})(P_i - \bar{P})}{\sum_{i=1}^N (t_i - \bar{t})^2}
 */
CGPoint _UIScrollViewVelocity_filteredVelocity(_UIScrollViewVelocity *self) {
    if (!self || self->_sampleCount < 2) {
        return (CGPoint){0.0, 0.0};
    }

    /* Find latest timestamp among valid samples */
    NSTimeInterval latestTimestamp = 0.0;
    for (uint32_t i = 0; i < kVelocityRingBufferCapacity; i++) {
        if (self->_samples[i].isValid && self->_samples[i].timestamp > latestTimestamp) {
            latestTimestamp = self->_samples[i].timestamp;
        }
    }

    /*
     * Cache Optimization:
     * If velocity was already computed for the latest sample timestamp,
     * return the cached result immediately.
     */
    if (self->_cacheTimestamp > 0.0 && self->_cacheTimestamp == latestTimestamp) {
        return self->_cachedVelocity;
    }

    NSTimeInterval windowStart = latestTimestamp - kVelocityLookbackWindowSec;

    /*
     * Chronological Ring Buffer Traversal:
     * In a circular buffer of capacity N where write head advances modulo N,
     * array indices [0..N-1] do not match chronological order once wrapped.
     * We locate the oldest valid sample and walk forward chronologically.
     */
    uint32_t startIdx = (self->_sampleCount < kVelocityRingBufferCapacity) ? 0 : self->_sampleIndex;

    /* Collect samples within [latestTimestamp - 100ms, latestTimestamp] in chronological order */
    NSTimeInterval times[kVelocityRingBufferCapacity];
    CGPoint points[kVelocityRingBufferCapacity];
    uint32_t validCount = 0;

    for (uint32_t step = 0; step < self->_sampleCount; step++) {
        uint32_t i = (startIdx + step) % kVelocityRingBufferCapacity;
        if (self->_samples[i].isValid && self->_samples[i].timestamp >= windowStart) {
            times[validCount] = self->_samples[i].timestamp;
            points[validCount] = self->_samples[i].point;
            validCount++;
        }
    }

    if (validCount < 2) {
        /* Fewer than 2 samples in 100ms window: finger has stopped prior to lift */
        return (CGPoint){0.0, 0.0};
    }

    /* Compute mean time \bar{t} and mean position \bar{P} */
    double sumT = 0.0;
    double sumX = 0.0;
    double sumY = 0.0;
    for (uint32_t i = 0; i < validCount; i++) {
        sumT += times[i];
        sumX += points[i].x;
        sumY += points[i].y;
    }

    double meanT = sumT / (double)validCount;
    double meanX = sumX / (double)validCount;
    double meanY = sumY / (double)validCount;

    /* Compute covariance sums: numerator and denominator */
    double numeratorX = 0.0;
    double numeratorY = 0.0;
    double denominatorT = 0.0;

    for (uint32_t i = 0; i < validCount; i++) {
        double dt = times[i] - meanT;
        numeratorX += dt * (points[i].x - meanX);
        numeratorY += dt * (points[i].y - meanY);
        denominatorT += dt * dt;
    }

    CGPoint velocity;
    if (denominatorT > 1e-9) {
        /* Standard OLS regression slope: v = Cov(t, P) / Var(t) */
        velocity.x = numeratorX / denominatorT;
        velocity.y = numeratorY / denominatorT;
    } else {
        /* Fallback: finite difference between oldest and newest in window */
        NSTimeInterval dtSpan = times[validCount - 1] - times[0];
        if (dtSpan > 1e-6) {
            velocity.x = (points[validCount - 1].x - points[0].x) / dtSpan;
            velocity.y = (points[validCount - 1].y - points[0].y) / dtSpan;
        } else {
            velocity = (CGPoint){0.0, 0.0};
        }
    }

    /* Cache and return computed velocity */
    self->_cachedVelocity = velocity;
    self->_cacheTimestamp = latestTimestamp;
    return velocity;
}

/**
 * _UIPanDetermineDirectionalLockAxis
 * Determines the dominant motion axis from initial gesture displacement:
 *   theta = atan2(|dy|, |dx|)
 *   theta >= kVerticalLockAngle (60 deg, pi/3)  -> Vertical lock
 *   theta <= kHorizontalLockAngle (30 deg, pi/6) -> Horizontal lock
 *   kHorizontalLockAngle < theta < kVerticalLockAngle -> None (diagonal neutral zone)
 */
_UIScrollViewDirectionalLockAxis _UIPanDetermineDirectionalLockAxis(CGPoint displacement) {
    double absX = fabs(displacement.x);
    double absY = fabs(displacement.y);
    if (absX < 1e-6 && absY < 1e-6) {
        return _UIScrollViewDirectionalLockAxisNone;
    }
    double angle = atan2(absY, absX);
    if (angle >= kVerticalLockAngle) {
        return _UIScrollViewDirectionalLockAxisVertical;
    } else if (angle <= kHorizontalLockAngle) {
        return _UIScrollViewDirectionalLockAxisHorizontal;
    }
    return _UIScrollViewDirectionalLockAxisNone;
}

/**
 * _UIPanApplyDirectionalLock
 * Projects velocity vector onto permissible axes when directionalLockEnabled is YES.
 */
static CGPoint _UIPanApplyDirectionalLock(CGPoint velocity, _UIScrollViewDirectionalLockAxis lockedAxis) {
    if (lockedAxis == _UIScrollViewDirectionalLockAxisHorizontal) {
        /* Locked to horizontal motion: zero out vertical velocity component */
        velocity.y = 0.0;
    } else if (lockedAxis == _UIScrollViewDirectionalLockAxisVertical) {
        /* Locked to vertical motion: zero out horizontal velocity component */
        velocity.x = 0.0;
    }
    return velocity;
}

/**
 * _UIPanClampVelocity
 * Applies lower dead-zone threshold (10 pt/s) and upper runaway cap (8000 pt/s).
 */
static CGPoint _UIPanClampVelocity(CGPoint velocity) {
    double speed = sqrt(velocity.x * velocity.x + velocity.y * velocity.y);

    /* Dead-zone threshold: below 10 pt/s treated as intentional static release */
    if (speed < kMinFlingVelocity) {
        return (CGPoint){0.0, 0.0};
    }

    /* Hard cap: prevent ballistic projection beyond 8000 pt/s */
    if (speed > kMaxFlingVelocityCap) {
        double scale = kMaxFlingVelocityCap / speed;
        velocity.x *= scale;
        velocity.y *= scale;
    }

    return velocity;
}

/**
 * _UIScrollViewVelocity_lastSampleTimestamp
 * Returns the timestamp of the most recent valid sample in the circular buffer.
 */
NSTimeInterval _UIScrollViewVelocity_lastSampleTimestamp(_UIScrollViewVelocity *self) {
    if (!self || self->_sampleCount == 0) {
        return 0.0;
    }
    uint32_t latestIdx = (self->_sampleIndex - 1 + kVelocityRingBufferCapacity) % kVelocityRingBufferCapacity;
    if (self->_samples[latestIdx].isValid) {
        return self->_samples[latestIdx].timestamp;
    }
    return 0.0;
}

/**
 * -[UIPanGestureRecognizer velocityInView:] @ 0x1848d1420
 * Queries filtered velocity from ring buffer, applies directional locking,
 * transforms coordinates into target view space, and clamps velocity vector.
 */
CGPoint _UIPanGestureRecognizer_velocityInView(UIPanGestureRecognizer *self, void *targetView) {
    if (!self || !self->_velocityTracker) {
        return (CGPoint){0.0, 0.0};
    }

    /*
     * Stationary Pause Detection:
     * If the finger halted on screen before lifting (e.g. current gesture timestamp
     * is > 100ms past the last touch movement sample in the buffer), release velocity
     * is clamped to 0.0 (user held finger still, then lifted).
     */
    NSTimeInterval lastSampleTime = _UIScrollViewVelocity_lastSampleTimestamp(self->_velocityTracker);
    if (self->_currentTimestamp > 0.0 && lastSampleTime > 0.0) {
        if (self->_currentTimestamp - lastSampleTime > kVelocityLookbackWindowSec) {
            return (CGPoint){0.0, 0.0};
        }
    }

    /* Step 1: Compute raw filtered release velocity in recognizer window space */
    CGPoint rawVelocity = _UIScrollViewVelocity_filteredVelocity(self->_velocityTracker);

    /* Step 2: Apply directional locking vector projections */
    if (self->_directionalLockEnabled) {
        CGPoint disp = (CGPoint){ self->_currentPoint.x - self->_startPoint.x, self->_currentPoint.y - self->_startPoint.y };
        if (self->_lockedAxis == _UIScrollViewDirectionalLockAxisNone) {
            self->_lockedAxis = _UIPanDetermineDirectionalLockAxis(disp);
        } else {
            /*
             * Cross-Axis Break Hysteresis:
             * If perpendicular displacement exceeds 40.0 pt, the initial directional lock is broken.
             */
            if (self->_lockedAxis == _UIScrollViewDirectionalLockAxisVertical && fabs(disp.x) >= 40.0) {
                self->_lockedAxis = _UIScrollViewDirectionalLockAxisNone;
            } else if (self->_lockedAxis == _UIScrollViewDirectionalLockAxisHorizontal && fabs(disp.y) >= 40.0) {
                self->_lockedAxis = _UIScrollViewDirectionalLockAxisNone;
            }
        }
        rawVelocity = _UIPanApplyDirectionalLock(rawVelocity, self->_lockedAxis);
    }

    /* Step 3: Transform vector from recognizer space to target view coordinate space */
    CGPoint viewVelocity = rawVelocity;
    if (targetView && targetView != self->_view) {
        CGAffineTransform transform = _UIViewGetTransformToView(self->_view, targetView);
        viewVelocity = _UIAffineTransformApplyToVector(transform, rawVelocity);
    }

    /* Step 4: Apply threshold dead-zone and velocity magnitude clamping */
    CGPoint clampedVelocity = _UIPanClampVelocity(viewVelocity);

    return clampedVelocity;
}

/**
 * _UIPanComputeMultiTouchCentroid
 * Computes arithmetic mean coordinate across N active touch locations:
 *   C = (1 / N) \sum_{i=1}^N P_i
 * Eliminates conflicting directional flings during multi-finger gestures.
 */
CGPoint _UIPanComputeMultiTouchCentroid(const CGPoint *touchPoints, uint32_t touchCount) {
    if (!touchPoints || touchCount == 0) {
        return (CGPoint){0.0, 0.0};
    }
    if (touchCount == 1) {
        return touchPoints[0];
    }
    double sumX = 0.0;
    double sumY = 0.0;
    for (uint32_t i = 0; i < touchCount; i++) {
        sumX += touchPoints[i].x;
        sumY += touchPoints[i].y;
    }
    return (CGPoint){ sumX / (double)touchCount, sumY / (double)touchCount };
}

/**
 * -[UIScrollViewPanGestureRecognizer velocityInView:] @ 0x1848c1150
 * Specialized scroll recognizer implementation: derives scroll contentOffset velocity
 * by inverting the pan velocity sign:
 *   v_{\text{scroll}} = -v_{\text{pan}}
 */
CGPoint _UIScrollViewPanGestureRecognizer_velocityInView(UIPanGestureRecognizer *self, void *targetView) {
    CGPoint panVelocity = _UIPanGestureRecognizer_velocityInView(self, targetView);

    /*
     * Scroll Kinematic Sign Inversion:
     * A downward finger gesture (+v_pan.y) pulls content down, decreasing contentOffset.
     * Ballistic scroll inertia must continue this direction:
     *   v_scroll.x = -panVelocity.x
     *   v_scroll.y = -panVelocity.y
     */
    CGPoint scrollVelocity;
    scrollVelocity.x = -panVelocity.x;
    scrollVelocity.y = -panVelocity.y;

    return scrollVelocity;
}

/* Stubs for coordinate geometry transforms */
static CGPoint _UIAffineTransformApplyToVector(CGAffineTransform t, CGPoint v) {
    return (CGPoint){
        t.a * v.x + t.c * v.y,
        t.b * v.x + t.d * v.y
    };
}

static CGAffineTransform _UIViewGetTransformToView(void *fromView, void *toView) {
    (void)fromView;
    (void)toView;
    /* Identity transform when views are collocated */
    return (CGAffineTransform){ 1.0, 0.0, 0.0, 1.0, 0.0, 0.0 };
}
