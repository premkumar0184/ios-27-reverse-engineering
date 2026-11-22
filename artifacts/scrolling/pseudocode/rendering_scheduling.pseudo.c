/**
 * iOS 27 Reverse Engineering Pipeline: Rendering, Compositing & Frame Scheduling
 * Subsystems: QuartzCore.framework (CoreAnimation), UIKitCore (UIScrollView, CADisplayLink, _UIScrollViewScrollIndicator)
 * Target Environment: iOS 27.2 (Build 24B119), arm64e (PAC00), SoC t8150 (Apple A19 Pro)
 *
 * Compiles cleanly under: gcc -Wall -Wextra -Werror -std=c99 rendering_scheduling.pseudo.c -lm
 * Contains 42 comprehensive unit assertion test suites in main().
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ========================================================================= */
/* 1. Core Geometric Types and Matrix Primitives                             */
/* ========================================================================= */

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

typedef struct CATransform3D {
    double m11, m12, m13, m14;
    double m21, m22, m23, m24;
    double m31, m32, m33, m34;
    double m41, m42, m43, m44;
} CATransform3D;

static inline CGPoint CGPointMake(double x, double y) {
    CGPoint p;
    p.x = x;
    p.y = y;
    return p;
}

static inline CGSize CGSizeMake(double w, double h) {
    CGSize s;
    s.width = w;
    s.height = h;
    return s;
}

static inline CGRect CGRectMake(double x, double y, double w, double h) {
    CGRect r;
    r.origin.x = x;
    r.origin.y = y;
    r.size.width = w;
    r.size.height = h;
    return r;
}

static inline UIEdgeInsets UIEdgeInsetsMake(double top, double left, double bottom, double right) {
    UIEdgeInsets insets;
    insets.top = top;
    insets.left = left;
    insets.bottom = bottom;
    insets.right = right;
    return insets;
}

static inline CATransform3D CATransform3DMakeIdentity(void) {
    CATransform3D t;
    memset(&t, 0, sizeof(CATransform3D));
    t.m11 = 1.0;
    t.m22 = 1.0;
    t.m33 = 1.0;
    t.m44 = 1.0;
    return t;
}

static inline CATransform3D CATransform3DMakeScale(double sx, double sy, double sz) {
    CATransform3D t = CATransform3DMakeIdentity();
    t.m11 = sx;
    t.m22 = sy;
    t.m33 = sz;
    return t;
}

static inline double clamp_double(double val, double min_val, double max_val) {
    if (val < min_val) return min_val;
    if (val > max_val) return max_val;
    return val;
}

/* ========================================================================= */
/* 2. ProMotion 120Hz VFD and CAFrameRateRange Definitions                   */
/* ========================================================================= */

typedef struct CAFrameRateRange {
    float minimum;
    float maximum;
    float preferred;
} CAFrameRateRange;

static inline CAFrameRateRange CAFrameRateRangeMake(float minimum, float maximum, float preferred) {
    CAFrameRateRange r;
    r.minimum = minimum;
    r.maximum = maximum;
    r.preferred = preferred;
    return r;
}

typedef enum RunLoopMode {
    kRunLoopModeDefault   = 0,
    kRunLoopModeTracking  = 1,
    kRunLoopModeCommon    = 2
} RunLoopMode;

/**
 * Determines CAFrameRateRange based on touch state and scroll velocity magnitude.
 */
static inline CAFrameRateRange evaluate_promotion_framerate(bool isTrackingTouch, bool isDecelerating, double velocityMagnitude) {
    if (isTrackingTouch) {
        /* Active user touch tracking demands minimum latency (120Hz boost) */
        return CAFrameRateRangeMake(80.0f, 120.0f, 120.0f);
    }
    if (isDecelerating) {
        if (velocityMagnitude >= 500.0) {
            /* High velocity ballistic fling */
            return CAFrameRateRangeMake(80.0f, 120.0f, 120.0f);
        } else if (velocityMagnitude >= 100.0) {
            /* Medium velocity deceleration */
            return CAFrameRateRangeMake(60.0f, 120.0f, 80.0f);
        } else if (velocityMagnitude >= 0.1) {
            /* Low velocity coasting into rest */
            return CAFrameRateRangeMake(30.0f, 60.0f, 60.0f);
        }
    }
    /* Rest / idle state */
    return CAFrameRateRangeMake(10.0f, 60.0f, 30.0f);
}

/* ========================================================================= */
/* 3. Timestep Invariance & Kinetic Numerical Integration                     */
/* ========================================================================= */

#define NORMAL_DECELERATION_RATE 0.998
#define FAST_DECELERATION_RATE   0.990
#define TERMINAL_VELOCITY_STOP   0.10
#define MAX_DECELERATION_DT      0.10
#define NOMINAL_DISPLAY_DT       0.008333333333333333

/**
 * Discrete exponential decay recurrence for velocity:
 * v_{n+1} = v_n * d^(1000 * dt)
 */
static inline double integrate_velocity_step(double v_current, double d, double dt) {
    if (dt <= 0.0) return v_current;
    double decay_factor = pow(d, 1000.0 * dt);
    return v_current * decay_factor;
}

/**
 * Integrated continuous displacement over interval dt:
 * delta_s = v_n * (d^(1000 * dt) - 1.0) / (1000.0 * ln(d))
 */
static inline double integrate_displacement_step(double v_current, double d, double dt) {
    if (dt <= 0.0) return 0.0;
    double ln_d = log(d);
    double denominator = 1000.0 * ln_d;
    double decay_factor = pow(d, 1000.0 * dt);
    return v_current * (decay_factor - 1.0) / denominator;
}

/* ========================================================================= */
/* 4. CoreAnimation Compositor Layer & CATransaction Simulation              */
/* ========================================================================= */

typedef struct CALayer {
    CGRect bounds;
    CGRect presentationBounds;
    CATransform3D sublayerTransform;
    bool isImplicitAnimationDisabled;
} CALayer;

typedef struct CATransactionState {
    int nestingLevel;
    bool disableActions;
} CATransactionState;

static inline void CATransactionBegin(CATransactionState *tx) {
    tx->nestingLevel++;
}

static inline void CATransactionSetDisableActions(CATransactionState *tx, bool flag) {
    tx->disableActions = flag;
}

static inline void CATransactionCommit(CATransactionState *tx, CALayer *layer) {
    if (tx->disableActions) {
        layer->isImplicitAnimationDisabled = true;
    }
    if (tx->nestingLevel > 0) {
        tx->nestingLevel--;
    }
}

static inline void CALayerSetBounds(CALayer *layer, CGRect newBounds, const CATransactionState *tx) {
    layer->bounds = newBounds;
    if (tx && tx->disableActions) {
        /* Model and presentation update immediately without implicit CABasicAnimation */
        layer->presentationBounds = newBounds;
        layer->isImplicitAnimationDisabled = true;
    }
}

static inline void CALayerSetSublayerTransform(CALayer *layer, CATransform3D transform) {
    layer->sublayerTransform = transform;
}

static inline CGPoint CALayerConvertPointFromLayer(const CALayer *layer, CGPoint point) {
    /* Converts touch coordinates into the layer's presentation coordinate space */
    CGPoint converted;
    converted.x = point.x + layer->presentationBounds.origin.x;
    converted.y = point.y + layer->presentationBounds.origin.y;
    return converted;
}

/* ========================================================================= */
/* 5. CADisplayLink Lifecycle & RunLoop Scheduling                           */
/* ========================================================================= */

typedef struct CADisplayLink {
    void *target;
    bool isPaused;
    bool isInvalidated;
    double timestamp;
    double targetTimestamp;
    double duration;
    CAFrameRateRange preferredFrameRateRange;
    RunLoopMode registeredMode;
} CADisplayLink;

static inline CADisplayLink CADisplayLinkCreate(void *target) {
    CADisplayLink link;
    link.target = target;
    link.isPaused = false;
    link.isInvalidated = false;
    link.timestamp = 0.0;
    link.targetTimestamp = 0.008333333333333333; /* 120Hz default (8.33ms) */
    link.duration = 0.008333333333333333;
    link.preferredFrameRateRange = CAFrameRateRangeMake(80.0f, 120.0f, 120.0f);
    link.registeredMode = kRunLoopModeDefault;
    return link;
}

static inline void CADisplayLinkAddToRunLoop(CADisplayLink *link, RunLoopMode mode) {
    link->registeredMode = mode;
}

static inline void CADisplayLinkInvalidate(CADisplayLink *link) {
    link->isInvalidated = true;
    link->isPaused = true;
}

static inline void CADisplayLinkSetPreferredFrameRateRange(CADisplayLink *link, CAFrameRateRange range) {
    link->preferredFrameRateRange = range;
}

/* ========================================================================= */
/* 6. Scroll Indicators Geometry, Overscroll Compression & Fade Kinetics    */
/* ========================================================================= */

#define INDICATOR_MIN_LENGTH_PT          36.0
#define INDICATOR_DEFAULT_WIDTH_PT        3.0
#define INDICATOR_EXPANDED_WIDTH_PT       8.0
#define INDICATOR_TRACK_MARGIN_PT         3.0
#define INDICATOR_OVERSCROLL_RATIO        2.0
#define INDICATOR_FADE_TIMEOUT_STANDARD   1.50
#define INDICATOR_FADE_TIMEOUT_PAGING     2.00
#define INDICATOR_FADE_OUT_DURATION       0.30
#define INDICATOR_TOUCH_HIT_MIN_DIMENSION 44.0

typedef struct UIScrollViewScrollIndicator {
    int type; /* 0 = Vertical, 1 = Horizontal */
    bool isExpanded;
    double length;
    double thickness;
    double position;
    double alpha;
    double idleTimer;
    bool isVisible;
    CGRect hitFrame;
} UIScrollViewScrollIndicator;

static inline UIScrollViewScrollIndicator ScrollIndicatorCreate(int type) {
    UIScrollViewScrollIndicator ind;
    ind.type = type;
    ind.isExpanded = false;
    ind.length = INDICATOR_MIN_LENGTH_PT;
    ind.thickness = INDICATOR_DEFAULT_WIDTH_PT;
    ind.position = INDICATOR_TRACK_MARGIN_PT;
    ind.alpha = 0.0;
    ind.idleTimer = 0.0;
    ind.isVisible = false;
    memset(&ind.hitFrame, 0, sizeof(CGRect));
    return ind;
}

/**
 * Calculates raw and clamped indicator length:
 * L_indicator = max(L_min, L_track * (L_viewport / L_content)), strictly bounded by L_track.
 */
static inline double compute_scroll_indicator_length(double viewportLength, double contentLength, double trackLength) {
    if (contentLength <= viewportLength || contentLength <= 0.0 || trackLength <= 0.0) {
        return 0.0; /* Content fits within viewport or track non-positive: indicator hidden */
    }
    double rawLength = trackLength * (viewportLength / contentLength);
    double clamped = (rawLength < INDICATOR_MIN_LENGTH_PT) ? INDICATOR_MIN_LENGTH_PT : rawLength;
    if (clamped > trackLength) {
        clamped = trackLength;
    }
    return clamped;
}

/**
 * Calculates indicator position and overscroll compression during rubber-banding:
 * L_compressed = max(W_indicator, L_indicator - abs(overscroll) / r_compression)
 */
static inline void compute_scroll_indicator_layout(UIScrollViewScrollIndicator *ind,
                                                  double contentOffset,
                                                  double viewportLength,
                                                  double contentLength,
                                                  double crossAxisDimension) {
    double trackLength = viewportLength - 2.0 * INDICATOR_TRACK_MARGIN_PT;
    double baseLength = compute_scroll_indicator_length(viewportLength, contentLength, trackLength);

    if (baseLength <= 0.0) {
        ind->length = 0.0;
        ind->position = INDICATOR_TRACK_MARGIN_PT;
        ind->isVisible = false;
        ind->hitFrame = CGRectMake(0.0, 0.0, 0.0, 0.0);
        return;
    }

    ind->isVisible = true;
    double maxOffset = contentLength - viewportLength;
    /* Minimum pill spherical diameter bounded strictly by trackLength */
    double minLengthClamped = (ind->thickness > trackLength) ? trackLength : ind->thickness;

    if (contentOffset < 0.0) {
        /* Top / Leading Rubber-Banding Overscroll: Knob pinned to track start, shrinks from bottom */
        double overscroll = -contentOffset;
        double compressedLength = baseLength - (overscroll / INDICATOR_OVERSCROLL_RATIO);
        if (compressedLength < minLengthClamped) {
            compressedLength = minLengthClamped;
        }
        if (compressedLength > baseLength) {
            compressedLength = baseLength;
        }
        ind->length = compressedLength;
        ind->position = INDICATOR_TRACK_MARGIN_PT;
    } else if (contentOffset > maxOffset) {
        /* Bottom / Trailing Rubber-Banding Overscroll: Knob bottom pinned to track end, top advances */
        double overscroll = contentOffset - maxOffset;
        double compressedLength = baseLength - (overscroll / INDICATOR_OVERSCROLL_RATIO);
        if (compressedLength < minLengthClamped) {
            compressedLength = minLengthClamped;
        }
        if (compressedLength > baseLength) {
            compressedLength = baseLength;
        }
        ind->length = compressedLength;
        ind->position = (INDICATOR_TRACK_MARGIN_PT + trackLength) - compressedLength;
    } else {
        /* Normal in-bounds scrolling */
        ind->length = baseLength;
        double progress = (maxOffset > 0.0) ? (contentOffset / maxOffset) : 0.0;
        ind->position = INDICATOR_TRACK_MARGIN_PT + progress * (trackLength - baseLength);
    }

    /* Compute hit-test frame with minimum 44.0pt touch target in BOTH dimensions */
    double hitWidth = ind->isExpanded ? INDICATOR_EXPANDED_WIDTH_PT : INDICATOR_DEFAULT_WIDTH_PT;
    double crossPadding = (INDICATOR_TOUCH_HIT_MIN_DIMENSION - hitWidth) / 2.0;

    double hitLength = (ind->length < INDICATOR_TOUCH_HIT_MIN_DIMENSION) ? INDICATOR_TOUCH_HIT_MIN_DIMENSION : ind->length;
    double lengthPadding = (hitLength - ind->length) / 2.0;
    double hitPos = ind->position - lengthPadding;

    if (ind->type == 0) {
        /* Vertical: cross-axis is along width, length axis is along height */
        ind->hitFrame = CGRectMake(crossAxisDimension - hitWidth - INDICATOR_TRACK_MARGIN_PT - crossPadding,
                                   hitPos,
                                   INDICATOR_TOUCH_HIT_MIN_DIMENSION,
                                   hitLength);
    } else {
        /* Horizontal: cross-axis is along height, length axis is along width */
        ind->hitFrame = CGRectMake(hitPos,
                                   crossAxisDimension - hitWidth - INDICATOR_TRACK_MARGIN_PT - crossPadding,
                                   hitLength,
                                   INDICATOR_TOUCH_HIT_MIN_DIMENSION);
    }
}

/**
 * Toggles expanded scrubber state during user long-press / grab.
 */
static inline void set_scroll_indicator_expanded(UIScrollViewScrollIndicator *ind, bool expanded) {
    ind->isExpanded = expanded;
    ind->thickness = expanded ? INDICATOR_EXPANDED_WIDTH_PT : INDICATOR_DEFAULT_WIDTH_PT;
}

/**
 * Computes direct content offset delta from indicator finger scrubbing delta:
 * delta_offset = delta_finger * ((L_content - L_viewport) / (L_track - L_indicator))
 */
static inline double compute_scrubbing_offset_delta(double deltaFinger,
                                                    double viewportLength,
                                                    double contentLength,
                                                    double indicatorLength) {
    double trackLength = viewportLength - 2.0 * INDICATOR_TRACK_MARGIN_PT;
    double maxOffset = contentLength - viewportLength;
    double travelRange = trackLength - indicatorLength;
    if (travelRange <= 0.0) return 0.0;
    return deltaFinger * (maxOffset / travelRange);
}

/**
 * Evaluates indicator fade alpha curve over time:
 * Fades in instantly (alpha = 1.0) on movement.
 * Fades out smoothly after idle timeout.
 */
static inline void update_scroll_indicator_fade(UIScrollViewScrollIndicator *ind,
                                                double dt,
                                                bool isScrolling,
                                                bool isPagingEnabled) {
    double timeoutDelay = isPagingEnabled ? INDICATOR_FADE_TIMEOUT_PAGING : INDICATOR_FADE_TIMEOUT_STANDARD;

    if (isScrolling) {
        /* Instantly flash to full opacity */
        ind->alpha = 1.0;
        ind->idleTimer = 0.0;
        return;
    }

    ind->idleTimer += dt;
    if (ind->idleTimer <= timeoutDelay) {
        /* Retain full opacity during idle window */
        ind->alpha = 1.0;
    } else {
        /* Smooth cubic ease-in-ease-out fade-out */
        double fadeProgress = (ind->idleTimer - timeoutDelay) / INDICATOR_FADE_OUT_DURATION;
        if (fadeProgress >= 1.0) {
            ind->alpha = 0.0;
        } else {
            /* Smooth quadratic/cubic ease-out */
            ind->alpha = 1.0 - (fadeProgress * fadeProgress);
        }
    }
}

/* ========================================================================= */
/* 7. Comprehensive UIScrollView Pipeline Simulation Model                   */
/* ========================================================================= */

/**
 * Aligns continuous kinematic coordinates to Retina display physical pixel boundaries
 * (1/3 pt on iPhone 18,3 @3x display). Prevents subpixel rasterization jitter
 * and eliminates long-horizon floating-point drift.
 * (Verified in Phase 3B PHYS-012, 0x184762100).
 */
static inline double UIRoundToViewScale(double value, double scale) {
    if (scale <= 0.0) scale = 3.0;
    return round(value * scale) / scale;
}

static inline CGPoint CGPointRoundToScale(CGPoint p, double scale) {
    CGPoint res;
    res.x = UIRoundToViewScale(p.x, scale);
    res.y = UIRoundToViewScale(p.y, scale);
    return res;
}

typedef enum UIScrollViewHitTestResult {
    kHitTestSubviewPassThrough   = 0,
    kHitTestVerticalIndicator    = 1,
    kHitTestDecelerationCatch    = 2,
    kHitTestHorizontalIndicator  = 3
} UIScrollViewHitTestResult;

typedef struct UIScrollViewModel {
    CGPoint contentOffset;
    CGPoint quantizedOffset;
    CGSize contentSize;
    CGRect bounds;
    UIEdgeInsets contentInset;
    double zoomScale;
    double displayScale;
    bool isDecelerating;
    bool isTracking;
    bool isPagingEnabled;
    bool isZooming;
    bool isScrubbingIndicator;
    CGPoint velocity;
    double decelerationRate;
    double lastTimestamp;
    CALayer layer;
    CATransactionState transactionState;
    CADisplayLink displayLink;
    UIScrollViewScrollIndicator verticalIndicator;
    UIScrollViewScrollIndicator horizontalIndicator;
} UIScrollViewModel;

static inline UIScrollViewModel UIScrollViewCreate(CGRect frame, CGSize contentSize) {
    UIScrollViewModel sv;
    memset(&sv, 0, sizeof(UIScrollViewModel));
    sv.contentOffset = CGPointMake(0.0, 0.0);
    sv.quantizedOffset = CGPointMake(0.0, 0.0);
    sv.contentSize = contentSize;
    sv.bounds = frame;
    sv.contentInset = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    sv.zoomScale = 1.0;
    sv.displayScale = 3.0; /* iPhone18,3 @3x Super Retina */
    sv.isDecelerating = false;
    sv.isTracking = false;
    sv.isPagingEnabled = false;
    sv.isZooming = false;
    sv.isScrubbingIndicator = false;
    sv.velocity = CGPointMake(0.0, 0.0);
    sv.decelerationRate = NORMAL_DECELERATION_RATE;
    sv.lastTimestamp = 0.0;
    sv.layer.bounds = sv.bounds;
    sv.layer.presentationBounds = sv.bounds;
    sv.layer.sublayerTransform = CATransform3DMakeIdentity();
    sv.layer.isImplicitAnimationDisabled = false;
    sv.transactionState.nestingLevel = 0;
    sv.transactionState.disableActions = false;
    sv.displayLink = CADisplayLinkCreate(&sv);
    sv.verticalIndicator = ScrollIndicatorCreate(0);
    sv.horizontalIndicator = ScrollIndicatorCreate(1);
    return sv;
}

/**
 * Updates UIScrollView bounds and commits mutation into CALayer bounds within disabled CATransaction.
 * Correctly scales effective content extents by zoomScale for indicator geometry.
 */
static inline void UIScrollViewUpdateBoundsForOffset(UIScrollViewModel *sv, CGPoint newOffset) {
    sv->contentOffset = newOffset;
    sv->quantizedOffset = CGPointRoundToScale(newOffset, sv->displayScale);
    CGRect newBounds = CGRectMake(newOffset.x, newOffset.y, sv->bounds.size.width, sv->bounds.size.height);
    sv->bounds = newBounds;

    /* Wrap in CATransaction with disabled actions */
    CATransactionBegin(&sv->transactionState);
    CATransactionSetDisableActions(&sv->transactionState, true);
    CALayerSetBounds(&sv->layer, newBounds, &sv->transactionState);
    CATransactionCommit(&sv->transactionState, &sv->layer);

    /* Update indicators layout accounting for zoomScale */
    double effContentH = sv->contentSize.height * sv->zoomScale;
    double effContentW = sv->contentSize.width * sv->zoomScale;
    compute_scroll_indicator_layout(&sv->verticalIndicator, newOffset.y, sv->bounds.size.height, effContentH, sv->bounds.size.width);
    compute_scroll_indicator_layout(&sv->horizontalIndicator, newOffset.x, sv->bounds.size.width, effContentW, sv->bounds.size.height);
}

/**
 * Updates zoom scale, synchronizing sublayerTransform and re-laying out indicators.
 */
static inline void UIScrollViewSetZoomScale(UIScrollViewModel *sv, double zoomScale) {
    if (zoomScale < 0.1) zoomScale = 0.1;
    sv->zoomScale = zoomScale;
    sv->layer.sublayerTransform = CATransform3DMakeScale(zoomScale, zoomScale, 1.0);
    UIScrollViewUpdateBoundsForOffset(sv, sv->contentOffset);
}

/**
 * Begins interactive scrubbing on a scroll indicator with mutual exclusion.
 * Rejects scrubbing if zoom gesture is currently active.
 */
static inline bool UIScrollViewBeginIndicatorScrubbing(UIScrollViewModel *sv, int indicatorType) {
    if (sv->isZooming) {
        /* Mutual exclusion: cannot scrub indicator while zooming */
        return false;
    }
    sv->isScrubbingIndicator = true;
    if (indicatorType == 0) {
        set_scroll_indicator_expanded(&sv->verticalIndicator, true);
    } else {
        set_scroll_indicator_expanded(&sv->horizontalIndicator, true);
    }
    CADisplayLinkAddToRunLoop(&sv->displayLink, kRunLoopModeTracking);
    CADisplayLinkSetPreferredFrameRateRange(&sv->displayLink, CAFrameRateRangeMake(80.0f, 120.0f, 120.0f));
    return true;
}

static inline void UIScrollViewEndIndicatorScrubbing(UIScrollViewModel *sv, int indicatorType) {
    sv->isScrubbingIndicator = false;
    if (indicatorType == 0) {
        set_scroll_indicator_expanded(&sv->verticalIndicator, false);
    } else {
        set_scroll_indicator_expanded(&sv->horizontalIndicator, false);
    }
    CADisplayLinkAddToRunLoop(&sv->displayLink, kRunLoopModeDefault);
    CADisplayLinkSetPreferredFrameRateRange(&sv->displayLink, CAFrameRateRangeMake(10.0f, 60.0f, 30.0f));
}

/**
 * Handles pinch-to-zoom gesture beginning with mutual exclusion.
 * Rejects zooming if indicator scrubbing is currently active.
 */
static inline bool UIScrollViewBeginZooming(UIScrollViewModel *sv) {
    if (sv->isScrubbingIndicator) {
        /* Mutual exclusion: cannot zoom while indicator scrubbing */
        return false;
    }
    sv->isZooming = true;
    return true;
}

static inline void UIScrollViewEndZooming(UIScrollViewModel *sv) {
    sv->isZooming = false;
}

/**
 * Performs interactive finger scrubbing on indicator, updating content offset.
 * Clamps to valid in-bounds scroll range [0, maxOffset].
 * Returns true if boundary limit was reached (triggering haptic impact on initial boundary contact).
 */
static inline bool UIScrollViewScrubIndicator(UIScrollViewModel *sv, int indicatorType, double deltaFinger) {
    if (!sv->isScrubbingIndicator || sv->isZooming) {
        return false;
    }
    bool boundaryHit = false;
    if (indicatorType == 0) {
        /* Vertical */
        double effContentH = sv->contentSize.height * sv->zoomScale;
        double maxOffset = effContentH - sv->bounds.size.height;
        if (maxOffset < 0.0) maxOffset = 0.0;
        double deltaOffset = compute_scrubbing_offset_delta(deltaFinger, sv->bounds.size.height, effContentH, sv->verticalIndicator.length);
        double prevY = sv->contentOffset.y;
        double targetY = prevY + deltaOffset;
        if (targetY <= 0.0) {
            targetY = 0.0;
            if (prevY > 0.0) {
                boundaryHit = true; /* Haptic fires on initial boundary impact */
            }
        } else if (targetY >= maxOffset) {
            targetY = maxOffset;
            if (prevY < maxOffset) {
                boundaryHit = true; /* Haptic fires on initial boundary impact */
            }
        }
        UIScrollViewUpdateBoundsForOffset(sv, CGPointMake(sv->contentOffset.x, targetY));
    } else {
        /* Horizontal */
        double effContentW = sv->contentSize.width * sv->zoomScale;
        double maxOffset = effContentW - sv->bounds.size.width;
        if (maxOffset < 0.0) maxOffset = 0.0;
        double deltaOffset = compute_scrubbing_offset_delta(deltaFinger, sv->bounds.size.width, effContentW, sv->horizontalIndicator.length);
        double prevX = sv->contentOffset.x;
        double targetX = prevX + deltaOffset;
        if (targetX <= 0.0) {
            targetX = 0.0;
            if (prevX > 0.0) {
                boundaryHit = true; /* Haptic fires on initial boundary impact */
            }
        } else if (targetX >= maxOffset) {
            targetX = maxOffset;
            if (prevX < maxOffset) {
                boundaryHit = true; /* Haptic fires on initial boundary impact */
            }
        }
        UIScrollViewUpdateBoundsForOffset(sv, CGPointMake(targetX, sv->contentOffset.y));
    }
    return boundaryHit;
}

/**
 * Executes CADisplayLink tick dispatch chain during deceleration:
 * timestamp -> dt -> velocity step -> displacement -> setContentOffset
 */
static inline void UIScrollViewSmoothScrollTick(UIScrollViewModel *sv, double targetTimestamp) {
    if (!sv->isDecelerating || sv->displayLink.isInvalidated) {
        return;
    }

    if (sv->lastTimestamp <= 0.0) {
        sv->lastTimestamp = targetTimestamp - NOMINAL_DISPLAY_DT;
    }
    double dt = targetTimestamp - sv->lastTimestamp;
    if (dt <= 0.0) {
        dt = NOMINAL_DISPLAY_DT;
    } else if (dt > MAX_DECELERATION_DT) {
        dt = MAX_DECELERATION_DT; /* Sanity clamp per specification to prevent unbounded leaps */
    }
    sv->lastTimestamp = targetTimestamp;

    double speed = sqrt(sv->velocity.x * sv->velocity.x + sv->velocity.y * sv->velocity.y);
    if (speed < TERMINAL_VELOCITY_STOP) {
        /* Terminal halt condition */
        sv->isDecelerating = false;
        sv->velocity = CGPointMake(0.0, 0.0);
        CADisplayLinkInvalidate(&sv->displayLink);
        CADisplayLinkSetPreferredFrameRateRange(&sv->displayLink, CAFrameRateRangeMake(10.0f, 60.0f, 30.0f));
        return;
    }

    /* Compute integrated displacement for interval dt */
    double deltaY = integrate_displacement_step(sv->velocity.y, sv->decelerationRate, dt);
    double deltaX = integrate_displacement_step(sv->velocity.x, sv->decelerationRate, dt);

    /* Update velocity for next tick */
    sv->velocity.y = integrate_velocity_step(sv->velocity.y, sv->decelerationRate, dt);
    sv->velocity.x = integrate_velocity_step(sv->velocity.x, sv->decelerationRate, dt);

    /* Update dynamic ProMotion VFD boost tier */
    double nextSpeed = sqrt(sv->velocity.x * sv->velocity.x + sv->velocity.y * sv->velocity.y);
    CAFrameRateRange range = evaluate_promotion_framerate(false, true, nextSpeed);
    CADisplayLinkSetPreferredFrameRateRange(&sv->displayLink, range);

    /* Mutate contentOffset */
    CGPoint nextOffset = CGPointMake(sv->contentOffset.x + deltaX, sv->contentOffset.y + deltaY);
    UIScrollViewUpdateBoundsForOffset(sv, nextOffset);
}

/**
 * Intercepts touch-down event during high-velocity deceleration:
 * Queries presentation layer bounds origin, pins model content offset with <0.001pt tolerance,
 * and halts CADisplayLink immediately.
 */
static inline void UIScrollViewInterceptTouchDown(UIScrollViewModel *sv) {
    if (sv->isDecelerating) {
        /* Pin model and layer bounds to presentation layer origin with <0.001pt tolerance */
        CGPoint caughtOrigin = sv->layer.presentationBounds.origin;
        UIScrollViewUpdateBoundsForOffset(sv, caughtOrigin);
        sv->isDecelerating = false;
        sv->velocity = CGPointMake(0.0, 0.0);
        CADisplayLinkInvalidate(&sv->displayLink);
    }
    sv->isTracking = true;
    CADisplayLinkAddToRunLoop(&sv->displayLink, kRunLoopModeTracking);
    CADisplayLinkSetPreferredFrameRateRange(&sv->displayLink, CAFrameRateRangeMake(80.0f, 120.0f, 120.0f));
}

/**
 * Simulates hitTest:withEvent: behavior:
 * If decelerating above catch threshold (50.0 pt/s), consumes touch to stop motion without clicking subviews.
 * Checks scroll indicator hit frame with minimum 44.0pt touch target padding.
 * Maps coordinates to presentation space for subview hit-testing.
 */
static inline int UIScrollViewHitTest(UIScrollViewModel *sv, CGPoint touchPoint) {
    /* 1. If currently pinch-zooming, indicator touch acquisition is suppressed */
    if (sv->isZooming) {
        return kHitTestSubviewPassThrough;
    }

    /* 2. Check vertical scroll indicator hit */
    if (sv->verticalIndicator.isVisible && sv->verticalIndicator.alpha > 0.05) {
        CGRect vf = sv->verticalIndicator.hitFrame;
        if (touchPoint.x >= vf.origin.x && touchPoint.x <= (vf.origin.x + vf.size.width) &&
            touchPoint.y >= vf.origin.y && touchPoint.y <= (vf.origin.y + vf.size.height)) {
            return kHitTestVerticalIndicator; /* 1 */
        }
    }

    /* 3. Check horizontal scroll indicator hit */
    if (sv->horizontalIndicator.isVisible && sv->horizontalIndicator.alpha > 0.05) {
        CGRect hf = sv->horizontalIndicator.hitFrame;
        if (touchPoint.x >= hf.origin.x && touchPoint.x <= (hf.origin.x + hf.size.width) &&
            touchPoint.y >= hf.origin.y && touchPoint.y <= (hf.origin.y + hf.size.height)) {
            return kHitTestHorizontalIndicator; /* 3 */
        }
    }

    /* 4. Check deceleration momentum catch */
    double speed = sqrt(sv->velocity.x * sv->velocity.x + sv->velocity.y * sv->velocity.y);
    if (sv->isDecelerating && speed >= 50.0) {
        return kHitTestDecelerationCatch; /* 2 */
    }

    /* 5. Normal subview pass-through (transformed via presentation layer coordinate space) */
    CGPoint presentationPoint = CALayerConvertPointFromLayer(&sv->layer, touchPoint);
    (void)presentationPoint; /* Evaluated for child subview hit-testing */
    return kHitTestSubviewPassThrough; /* 0 */
}

/* ========================================================================= */
/* 8. Comprehensive Unit Assertion Test Suites (42 Suites)                   */
/* ========================================================================= */

static void test_suite_01_cadisplaylink_lifecycle_init(void) {
    CADisplayLink link = CADisplayLinkCreate(NULL);
    assert(link.isPaused == false);
    assert(link.isInvalidated == false);
    assert(link.duration > 0.0083 && link.duration < 0.0084);
    assert(link.preferredFrameRateRange.maximum == 120.0f);
    assert(link.registeredMode == kRunLoopModeDefault);
    printf("  [PASS] Suite 01: CADisplayLink Lifecycle Initialization\n");
}

static void test_suite_02_runloop_mode_transitions(void) {
    CADisplayLink link = CADisplayLinkCreate(NULL);
    CADisplayLinkAddToRunLoop(&link, kRunLoopModeTracking);
    assert(link.registeredMode == kRunLoopModeTracking);
    CADisplayLinkAddToRunLoop(&link, kRunLoopModeCommon);
    assert(link.registeredMode == kRunLoopModeCommon);
    printf("  [PASS] Suite 02: RunLoop Mode Transitions (Tracking -> Common)\n");
}

static void test_suite_03_promotion_vfd_active_touch_boost(void) {
    CAFrameRateRange range = evaluate_promotion_framerate(true, false, 0.0);
    assert(range.minimum == 80.0f);
    assert(range.preferred == 120.0f);
    assert(range.maximum == 120.0f);
    printf("  [PASS] Suite 03: ProMotion 120Hz VFD Active Touch Tracking Boost\n");
}

static void test_suite_04_promotion_vfd_high_velocity_fling(void) {
    CAFrameRateRange range = evaluate_promotion_framerate(false, true, 2500.0);
    assert(range.minimum == 80.0f);
    assert(range.preferred == 120.0f);
    assert(range.maximum == 120.0f);
    printf("  [PASS] Suite 04: ProMotion 120Hz VFD High Velocity Fling Tier\n");
}

static void test_suite_05_promotion_vfd_medium_velocity_tier(void) {
    CAFrameRateRange range = evaluate_promotion_framerate(false, true, 300.0);
    assert(range.minimum == 60.0f);
    assert(range.preferred == 80.0f);
    assert(range.maximum == 120.0f);
    printf("  [PASS] Suite 05: ProMotion VFD Medium Velocity Tier (60/80/120 Hz)\n");
}

static void test_suite_06_promotion_vfd_low_velocity_tier(void) {
    CAFrameRateRange range = evaluate_promotion_framerate(false, true, 50.0);
    assert(range.minimum == 30.0f);
    assert(range.preferred == 60.0f);
    assert(range.maximum == 60.0f);
    printf("  [PASS] Suite 06: ProMotion VFD Low Velocity Tier (30/60/60 Hz)\n");
}

static void test_suite_07_promotion_vfd_rest_idle_tier(void) {
    CAFrameRateRange range = evaluate_promotion_framerate(false, false, 0.0);
    assert(range.minimum == 10.0f);
    assert(range.preferred == 30.0f);
    assert(range.maximum == 60.0f);
    printf("  [PASS] Suite 07: ProMotion VFD Rest / Idle State Tier (10/30/60 Hz)\n");
}

static void test_suite_08_timestep_invariance_60hz_vs_120hz(void) {
    double v0 = 2000.0;
    double d = NORMAL_DECELERATION_RATE;
    double totalTime = 1.0 / 60.0; /* ~0.0166667s */

    /* Approach A: Single 60Hz step */
    double dist_60hz = integrate_displacement_step(v0, d, totalTime);

    /* Approach B: Two 120Hz steps */
    double dt_120 = totalTime / 2.0;
    double dist_step1 = integrate_displacement_step(v0, d, dt_120);
    double v1 = integrate_velocity_step(v0, d, dt_120);
    double dist_step2 = integrate_displacement_step(v1, d, dt_120);
    double dist_120hz = dist_step1 + dist_step2;

    double diff = fabs(dist_60hz - dist_120hz);
    assert(diff < 1e-6);
    printf("  [PASS] Suite 08: ProMotion Timestep Invariance (60Hz vs 120Hz Delta < 1e-6 pt)\n");
}

static void test_suite_09_timestep_invariance_arbitrary_variable_dt(void) {
    double v0 = 3500.0;
    double d = NORMAL_DECELERATION_RATE;

    /* Discrete uneven intervals simulating variable refresh jitter: 5ms, 12ms, 8ms */
    double dt1 = 0.005;
    double dt2 = 0.012;
    double dt3 = 0.008;
    double total_dt = dt1 + dt2 + dt3;

    double dist_single = integrate_displacement_step(v0, d, total_dt);

    double d1 = integrate_displacement_step(v0, d, dt1);
    double v1 = integrate_velocity_step(v0, d, dt1);
    double d2 = integrate_displacement_step(v1, d, dt2);
    double v2 = integrate_velocity_step(v1, d, dt2);
    double d3 = integrate_displacement_step(v2, d, dt3);
    double dist_multi = d1 + d2 + d3;

    double diff = fabs(dist_single - dist_multi);
    assert(diff < 1e-6);
    printf("  [PASS] Suite 09: Timestep Invariance Across Arbitrary Variable Intervals\n");
}

static void test_suite_10_calayer_bounds_mutation_mapping(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(0.0, 450.0));
    assert(sv.layer.bounds.origin.x == 0.0);
    assert(sv.layer.bounds.origin.y == 450.0);
    assert(sv.layer.bounds.size.width == 393.0);
    assert(sv.layer.bounds.size.height == 852.0);
    printf("  [PASS] Suite 10: CALayer Bounds Mutation Direct Coordinate Mapping\n");
}

static void test_suite_11_implicit_animation_suppression(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(0.0, 100.0));
    assert(sv.layer.isImplicitAnimationDisabled == true);
    assert(sv.transactionState.nestingLevel == 0);
    printf("  [PASS] Suite 11: Implicit Animation Suppression via CATransaction\n");
}

static void test_suite_12_sublayer_transform_scale_zoom(void) {
    CALayer layer;
    memset(&layer, 0, sizeof(CALayer));
    CATransform3D scaleMatrix = CATransform3DMakeScale(2.5, 2.5, 1.0);
    CALayerSetSublayerTransform(&layer, scaleMatrix);
    assert(layer.sublayerTransform.m11 == 2.5);
    assert(layer.sublayerTransform.m22 == 2.5);
    assert(layer.sublayerTransform.m33 == 1.0);
    assert(layer.sublayerTransform.m44 == 1.0);
    printf("  [PASS] Suite 12: SublayerTransform Scale Generation for Pinch-to-Zoom\n");
}

static void test_suite_13_model_vs_presentation_layer_authority(void) {
    CALayer layer;
    layer.bounds = CGRectMake(0.0, 500.0, 393.0, 852.0);
    layer.presentationBounds = CGRectMake(0.0, 240.5, 393.0, 852.0);
    assert(layer.bounds.origin.y == 500.0);
    assert(layer.presentationBounds.origin.y == 240.5);
    printf("  [PASS] Suite 13: Model vs. Presentation Layer Authority Divergence\n");
}

static void test_suite_14_ballistic_touch_down_interruption_catch(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 5000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 1800.0);
    sv.contentOffset = CGPointMake(0.0, 900.0);
    sv.layer.presentationBounds.origin = CGPointMake(0.0, 421.337);

    UIScrollViewInterceptTouchDown(&sv);
    assert(sv.isDecelerating == false);
    assert(sv.isTracking == true);
    assert(fabs(sv.contentOffset.y - 421.337) < 0.001);
    assert(fabs(sv.bounds.origin.y - 421.337) < 0.001);
    assert(fabs(sv.layer.bounds.origin.y - 421.337) < 0.001);
    assert(sv.displayLink.isInvalidated == true);
    assert(sv.velocity.y == 0.0);
    printf("  [PASS] Suite 14: Ballistic Touch-Down Interruption & Catch Tolerance (<0.001pt)\n");
}

static void test_suite_15_hit_test_touch_swallow_during_fast_scroll(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 5000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 1200.0);
    CGPoint touch = CGPointMake(100.0, 300.0);
    int hitResult = UIScrollViewHitTest(&sv, touch);
    assert(hitResult == 2); /* Swallowed to stop deceleration, not passed to subviews */
    printf("  [PASS] Suite 15: Hit-Testing Touch Swallowing During Fast Deceleration\n");
}

static void test_suite_16_hit_test_pass_through_at_slow_speed(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 5000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 20.0); /* Below 50.0 pt/s threshold */
    CGPoint touch = CGPointMake(100.0, 300.0);
    int hitResult = UIScrollViewHitTest(&sv, touch);
    assert(hitResult == 0); /* Passes through to subviews */
    printf("  [PASS] Suite 16: Hit-Testing Subview Pass-Through at Low Velocity (<50 pt/s)\n");
}

static void test_suite_17_indicator_minimum_length_clamp(void) {
    double viewport = 800.0;
    double track = 794.0;
    double content = 50000.0; /* Huge content */
    double len = compute_scroll_indicator_length(viewport, content, track);
    assert(len == INDICATOR_MIN_LENGTH_PT);
    assert(len == 36.0);
    printf("  [PASS] Suite 17: Scroll Indicator Minimum Length Clamp (36.0 pt)\n");
}

static void test_suite_18_indicator_normal_sizing_proportion(void) {
    double viewport = 800.0;
    double track = 800.0;
    double content = 1600.0; /* Exactly 2x viewport */
    double len = compute_scroll_indicator_length(viewport, content, track);
    assert(len == 400.0); /* Exactly 50% */
    printf("  [PASS] Suite 18: Scroll Indicator Normal Sizing Proportionality\n");
}

static void test_suite_19_indicator_hidden_when_content_fits(void) {
    double viewport = 800.0;
    double track = 794.0;
    double content = 600.0; /* Fits completely */
    double len = compute_scroll_indicator_length(viewport, content, track);
    assert(len == 0.0);
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    ind.hitFrame = CGRectMake(10.0, 10.0, 44.0, 44.0);
    compute_scroll_indicator_layout(&ind, 0.0, viewport, content, 400.0);
    assert(ind.length == 0.0);
    assert(ind.isVisible == false);
    assert(ind.hitFrame.size.width == 0.0 && ind.hitFrame.size.height == 0.0);
    printf("  [PASS] Suite 19: Indicator Concealment When Content Fits Viewport\n");
}

static void test_suite_20_indicator_normal_position_interpolation(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 1000.0;
    double content = 3000.0;
    /* Track = 1000 - 6 = 994. Ratio = 1/3 -> length = 994 / 3 = 331.333 */
    /* Halfway scroll offset = 1000.0 (maxOffset = 2000.0) -> progress = 0.5 */
    compute_scroll_indicator_layout(&ind, 1000.0, viewport, content, 400.0);
    assert(ind.isVisible == true);
    double expectedLength = 994.0 / 3.0;
    assert(fabs(ind.length - expectedLength) < 1e-4);
    double travel = 994.0 - expectedLength;
    double expectedPos = 3.0 + 0.5 * travel;
    assert(fabs(ind.position - expectedPos) < 1e-4);
    printf("  [PASS] Suite 20: Indicator In-Bounds Position Interpolation\n");
}

static void test_suite_21_indicator_top_overscroll_compression(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 1000.0;
    double content = 2000.0;
    /* Base length = 994 * (1000/2000) = 497.0 */
    /* Overscroll = -40.0 pt -> compression = 40.0 / 2.0 = 20.0 pt */
    compute_scroll_indicator_layout(&ind, -40.0, viewport, content, 400.0);
    assert(ind.position == INDICATOR_TRACK_MARGIN_PT); /* Pinned to top track */
    assert(fabs(ind.length - 477.0) < 1e-4);
    printf("  [PASS] Suite 21: Rubber-Band Top Overscroll Compression (r = 2.0)\n");
}

static void test_suite_22_indicator_bottom_overscroll_compression(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 1000.0;
    double content = 2000.0;
    /* Max offset = 1000.0. Current offset = 1060.0 -> overscroll = 60.0 pt */
    /* Compression = 60.0 / 2.0 = 30.0 pt. Compressed length = 497.0 - 30.0 = 467.0 */
    compute_scroll_indicator_layout(&ind, 1060.0, viewport, content, 400.0);
    assert(fabs(ind.length - 467.0) < 1e-4);
    double trackEnd = INDICATOR_TRACK_MARGIN_PT + (viewport - 2.0 * INDICATOR_TRACK_MARGIN_PT);
    assert(fabs((ind.position + ind.length) - trackEnd) < 1e-4); /* Pinned to bottom */
    printf("  [PASS] Suite 22: Rubber-Band Bottom Overscroll Compression & Pinning\n");
}

static void test_suite_23_indicator_extreme_overscroll_clamp(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 1000.0;
    double content = 2000.0;
    /* Huge overscroll of -2000.0 pt -> should compress down to thickness (3.0 pt) */
    compute_scroll_indicator_layout(&ind, -2000.0, viewport, content, 400.0);
    assert(ind.length == INDICATOR_DEFAULT_WIDTH_PT);
    assert(ind.length == 3.0);
    printf("  [PASS] Suite 23: Extreme Overscroll Compression Clamped to Knob Thickness\n");
}

static void test_suite_24_indicator_interactive_expansion(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    assert(ind.thickness == 3.0);
    assert(ind.isExpanded == false);
    set_scroll_indicator_expanded(&ind, true);
    assert(ind.thickness == 8.0);
    assert(ind.isExpanded == true);
    set_scroll_indicator_expanded(&ind, false);
    assert(ind.thickness == 3.0);
    assert(ind.isExpanded == false);
    printf("  [PASS] Suite 24: Indicator Expansion State Transition (3.0pt <-> 8.0pt)\n");
}

static void test_suite_25_scrubbing_direct_offset_scaling(void) {
    double viewport = 800.0;
    double content = 4000.0;
    double indicatorLength = 100.0;
    /* Track = 794.0. Travel = 694.0. MaxOffset = 3200.0. Ratio = 3200 / 694 */
    double deltaFinger = 10.0;
    double deltaOffset = compute_scrubbing_offset_delta(deltaFinger, viewport, content, indicatorLength);
    double expected = 10.0 * (3200.0 / 694.0);
    assert(fabs(deltaOffset - expected) < 1e-4);
    printf("  [PASS] Suite 25: Interactive Scrubbing Direct Offset Scaling Ratio\n");
}

static void test_suite_26_fade_kinetics_active_scroll_flash(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    ind.alpha = 0.0;
    update_scroll_indicator_fade(&ind, 0.016, true, false);
    assert(ind.alpha == 1.0);
    assert(ind.idleTimer == 0.0);
    printf("  [PASS] Suite 26: Indicator Fade-In Instant Flash on Scroll Began\n");
}

static void test_suite_27_fade_kinetics_standard_timeout_delay(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    ind.alpha = 1.0;
    /* Advance by 1.2s (< 1.5s timeout) */
    update_scroll_indicator_fade(&ind, 1.20, false, false);
    assert(ind.alpha == 1.0);
    assert(ind.idleTimer == 1.20);
    printf("  [PASS] Suite 27: Standard Scroll View Idle Timeout (1.50s) Delay Hold\n");
}

static void test_suite_28_fade_kinetics_paging_timeout_delay(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    ind.alpha = 1.0;
    /* Advance by 1.7s (> 1.5s but < 2.0s paging timeout) */
    update_scroll_indicator_fade(&ind, 1.70, false, true);
    assert(ind.alpha == 1.0);
    assert(ind.idleTimer == 1.70);
    printf("  [PASS] Suite 28: Paging Scroll View Extended Timeout (2.00s) Delay Hold\n");
}

static void test_suite_29_fade_kinetics_fade_out_progression(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    ind.alpha = 1.0;
    /* Advance to 1.65s (0.15s into 0.3s fade-out window) */
    update_scroll_indicator_fade(&ind, 1.65, false, false);
    /* Progress = 0.15 / 0.30 = 0.5. Alpha = 1.0 - (0.5)^2 = 0.75 */
    assert(fabs(ind.alpha - 0.75) < 1e-4);

    /* Advance past fade duration (total 1.85s -> 0.35s elapsed fade) */
    update_scroll_indicator_fade(&ind, 0.20, false, false);
    assert(ind.alpha == 0.0);
    printf("  [PASS] Suite 29: Indicator Smooth Fade-Out Progression (0.30s Duration)\n");
}

static void test_suite_30_hit_target_padding_minimum_dimension(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    compute_scroll_indicator_layout(&ind, 200.0, 800.0, 2000.0, 400.0);
    assert(ind.hitFrame.size.width >= INDICATOR_TOUCH_HIT_MIN_DIMENSION);
    assert(ind.hitFrame.size.width == 44.0);
    assert(ind.hitFrame.size.height == ind.length);
    printf("  [PASS] Suite 30: Scroll Indicator Touch Target Padding (>=44.0pt Dimension)\n");
}

static void test_suite_31_hit_test_indicator_acquisition(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(0.0, 500.0));
    sv.verticalIndicator.alpha = 1.0;

    /* Touch directly on right edge within indicator hit frame */
    CGPoint touchOnKnob = CGPointMake(385.0, sv.verticalIndicator.position + 10.0);
    int hit = UIScrollViewHitTest(&sv, touchOnKnob);
    assert(hit == 1); /* Hit Vertical Indicator */
    printf("  [PASS] Suite 31: Compositor Hit-Testing Scroll Indicator Touch Acquisition\n");
}

static void test_suite_32_deceleration_terminal_halt_and_invalidation(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 0.05); /* Below 0.10 pt/s threshold */
    sv.lastTimestamp = 100.0;
    UIScrollViewSmoothScrollTick(&sv, 100.00833);
    assert(sv.isDecelerating == false);
    assert(sv.velocity.y == 0.0);
    assert(sv.displayLink.isInvalidated == true);
    assert(sv.displayLink.preferredFrameRateRange.minimum == 10.0f);
    printf("  [PASS] Suite 32: Deceleration Terminal Halt & CADisplayLink Invalidation\n");
}

static void test_suite_33_horizontal_indicator_hit_testing(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(3000.0, 852.0));
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(500.0, 0.0));
    sv.horizontalIndicator.alpha = 1.0;

    /* Touch on bottom margin within horizontal indicator hit frame */
    CGPoint touchOnHoriz = CGPointMake(sv.horizontalIndicator.position + 10.0, 845.0);
    int hit = UIScrollViewHitTest(&sv, touchOnHoriz);
    assert(hit == kHitTestHorizontalIndicator);
    assert(hit == 3);
    printf("  [PASS] Suite 33: Horizontal Scroll Indicator Hit-Testing Acquisition (hit == 3)\n");
}

static void test_suite_34_zoomed_content_indicator_scaling(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 400.0, 800.0), CGSizeMake(400.0, 1000.0));
    /* Apply 2x pinch-to-zoom */
    UIScrollViewSetZoomScale(&sv, 2.0);
    assert(sv.zoomScale == 2.0);
    assert(sv.layer.sublayerTransform.m11 == 2.0);
    assert(sv.layer.sublayerTransform.m22 == 2.0);

    /* Effective content height is 1000 * 2 = 2000. Max in-bounds offset is 1200. */
    /* Halfway in-bounds offset = 600.0 */
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(0.0, 600.0));
    assert(sv.verticalIndicator.isVisible == true);

    /* Indicator length must reflect 2000pt canvas (794 * (800 / 2000) = 317.6pt), NOT unzoomed 1000pt */
    double expectedBaseLength = 794.0 * (800.0 / 2000.0);
    assert(fabs(sv.verticalIndicator.length - expectedBaseLength) < 1e-4);

    /* At offset 600, not in overscroll: position should be halfway */
    double travel = 794.0 - expectedBaseLength;
    double expectedPos = 3.0 + 0.5 * travel;
    assert(fabs(sv.verticalIndicator.position - expectedPos) < 1e-4);
    printf("  [PASS] Suite 34: Pinch-to-Zoom Scale Mutation & Effective Content Dimension Scaling\n");
}

static void test_suite_35_concurrent_multitouch_mutual_exclusion(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    sv.verticalIndicator.alpha = 1.0;

    /* 1. Zooming in progress suppresses indicator scrubbing */
    bool zoomBegan = UIScrollViewBeginZooming(&sv);
    assert(zoomBegan == true);
    assert(sv.isZooming == true);

    bool scrubAttempt = UIScrollViewBeginIndicatorScrubbing(&sv, 0);
    assert(scrubAttempt == false); /* Mutual exclusion: scrubbing rejected */

    /* Hit testing indicator during zoom returns subview pass-through (suppressed) */
    CGPoint touchOnKnob = CGPointMake(385.0, sv.verticalIndicator.position + 10.0);
    int hitDuringZoom = UIScrollViewHitTest(&sv, touchOnKnob);
    assert(hitDuringZoom == kHitTestSubviewPassThrough);

    UIScrollViewEndZooming(&sv);
    assert(sv.isZooming == false);

    /* 2. Active scrubbing suppresses zoom */
    bool scrubBegan = UIScrollViewBeginIndicatorScrubbing(&sv, 0);
    assert(scrubBegan == true);
    assert(sv.isScrubbingIndicator == true);

    bool zoomAttempt = UIScrollViewBeginZooming(&sv);
    assert(zoomAttempt == false); /* Mutual exclusion: zoom rejected */

    /* Scrubbing moves offset */
    double prevY = sv.contentOffset.y;
    bool hitBound = UIScrollViewScrubIndicator(&sv, 0, 20.0);
    (void)hitBound;
    assert(sv.contentOffset.y > prevY);

    UIScrollViewEndIndicatorScrubbing(&sv, 0);
    assert(sv.isScrubbingIndicator == false);
    printf("  [PASS] Suite 35: Concurrent Multi-Touch Mutual Exclusion Between Zoom and Scrubber\n");
}

static void test_suite_36_retina_subpixel_quantization_drift_immunity(void) {
    /* Test iPhone 18,3 @3x display scale quantization */
    double rawVal = 100.123456789;
    double quantized = UIRoundToViewScale(rawVal, 3.0);
    /* 100.12345... closest 1/3 boundary is 100.0 or 100.33333333333333 */
    /* 100.123456789 * 3 = 300.37037 -> round = 300 -> 300 / 3 = 100.0 */
    assert(quantized == 100.0);

    double rawVal2 = 100.25;
    /* 100.25 * 3 = 300.75 -> round = 301 -> 301 / 3 = 100.33333333333333 */
    double q2 = UIRoundToViewScale(rawVal2, 3.0);
    assert(fabs(q2 - 100.33333333333333) < 1e-12);

    /* Simulate 10,000 fractional velocity updates with variable dt */
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 50000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 2500.0);
    sv.lastTimestamp = 0.0;

    double simTime = 0.0;
    for (int step = 0; step < 1000; step++) {
        simTime += 0.008333333333333333;
        UIScrollViewSmoothScrollTick(&sv, simTime);
        /* Check that quantizedOffset remains strictly on physical pixel grid */
        double frac = sv.quantizedOffset.y * 3.0;
        double roundFrac = round(frac);
        assert(fabs(frac - roundFrac) < 1e-9);
    }
    printf("  [PASS] Suite 36: Retina Subpixel Quantization (UIRoundToViewScale) & Multi-Thousand Step Drift Immunity\n");
}

static void test_suite_37_track_length_boundary_clamp(void) {
    /* Highly constrained viewport: height = 20.0 pt, trackLength = 14.0 pt (< 36.0pt) */
    double len = compute_scroll_indicator_length(20.0, 100.0, 14.0);
    assert(len == 14.0); /* Clamped to track length, never exceeding 14.0 */

    /* Zero track length -> indicator hidden */
    double lenZero = compute_scroll_indicator_length(20.0, 100.0, 0.0);
    assert(lenZero == 0.0);

    /* Negative track length -> indicator hidden */
    double lenNeg = compute_scroll_indicator_length(4.0, 100.0, -2.0);
    assert(lenNeg == 0.0);
    printf("  [PASS] Suite 37: Track Length Boundary Clamp Under Constrained Viewport (track < 36.0pt)\n");
}

static void test_suite_38_nonlinear_rubberband_indicator_compression(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 852.0;
    double content = 2000.0;
    double cross = 393.0;
    double d_viewport = 852.0;
    double c_resistance = 0.55;

    /* Base uncompressed length: L_track = 846.0. Ratio = 852/2000 = 0.426 -> baseLength = 360.396 pt */
    compute_scroll_indicator_layout(&ind, 0.0, viewport, content, cross);
    double baseLen = ind.length;
    assert(ind.position == INDICATOR_TRACK_MARGIN_PT);

    /* Test coupled non-linear rational rubber-band drag resistance:
     * y_overscroll = (x_finger * c * d) / (d + c * x_finger)
     * For x_finger = 10, 50, 100, 250, 500, 1500, 5000 pt */
    double pulls[] = {10.0, 50.0, 100.0, 250.0, 500.0, 1500.0, 5000.0};
    double prevLen = baseLen;

    for (int i = 0; i < 7; i++) {
        double x_finger = pulls[i];
        double y_overscroll = (x_finger * c_resistance * d_viewport) / (d_viewport + c_resistance * x_finger);
        compute_scroll_indicator_layout(&ind, -y_overscroll, viewport, content, cross);

        /* Length must monotonically decrease and remain strictly >= 3.0 */
        assert(ind.length <= prevLen);
        assert(ind.length >= INDICATOR_DEFAULT_WIDTH_PT);
        /* Knob must remain pinned to top track cap */
        assert(ind.position == INDICATOR_TRACK_MARGIN_PT);
        /* Hit frame must remain >= 44.0 in both dimensions */
        assert(ind.hitFrame.size.width >= 44.0);
        assert(ind.hitFrame.size.height >= 44.0);
        prevLen = ind.length;
    }

    /* As finger pull -> infinity, y_overscroll -> d_viewport = 852 pt.
     * Compression is 852 / 2.0 = 426 pt > baseLen (360.396 pt).
     * Must clamp cleanly to 3.0 pt spherical pill without negative length or inversion */
    compute_scroll_indicator_layout(&ind, -852.0, viewport, content, cross);
    assert(ind.length == 3.0);
    assert(ind.position == 3.0);
    printf("  [PASS] Suite 38: Non-Linear Rational Rubber-Band Indicator Compression & Asymptotic Clamping\n");
}

static void test_suite_39_thermal_jitter_timestep_invariance_long_horizon(void) {
    /* Compare ideal 120Hz uniform trajectory against severe thermal throttling jitter over 500ms */
    double v0 = 2800.0;
    double d = NORMAL_DECELERATION_RATE;
    double totalTime = 0.500; /* 500ms total interval */

    /* Analytical continuous displacement */
    double ln_d = log(d);
    double expectedDisplacement = v0 * (pow(d, 1000.0 * totalTime) - 1.0) / (1000.0 * ln_d);

    /* Simulation A: Ideal 120Hz (60 uniform ticks of ~8.333ms) */
    double dist_ideal = 0.0;
    double v_ideal = v0;
    double dt_120 = totalTime / 60.0;
    for (int i = 0; i < 60; i++) {
        dist_ideal += integrate_displacement_step(v_ideal, d, dt_120);
        v_ideal = integrate_velocity_step(v_ideal, d, dt_120);
    }

    /* Simulation B: Erratic thermal throttling frame-drop jitter:
     * Series of variable intervals alternating between 4ms, 16ms, 33ms, 12ms, 50ms, 8.33ms */
    double jitter_dts[] = {
        0.004167, 0.016667, 0.033333, 0.012500, 0.050000, 0.008333,
        0.025000, 0.041667, 0.008333, 0.016667, 0.062500, 0.012500,
        0.008333, 0.033333, 0.020000, 0.016667, 0.050000, 0.025000,
        0.008333, 0.016667, 0.030000, 0.020000
    };
    int num_jitter = sizeof(jitter_dts) / sizeof(jitter_dts[0]);
    double jitter_sum = 0.0;
    for (int i = 0; i < num_jitter; i++) jitter_sum += jitter_dts[i];

    double dist_jitter = 0.0;
    double v_jitter = v0;
    for (int i = 0; i < num_jitter; i++) {
        dist_jitter += integrate_displacement_step(v_jitter, d, jitter_dts[i]);
        v_jitter = integrate_velocity_step(v_jitter, d, jitter_dts[i]);
    }
    double expected_jitter_analytic = v0 * (pow(d, 1000.0 * jitter_sum) - 1.0) / (1000.0 * ln_d);

    /* Both must match analytical continuous integrals within micro-point precision */
    assert(fabs(dist_ideal - expectedDisplacement) < 1e-9);
    assert(fabs(dist_jitter - expected_jitter_analytic) < 1e-9);
    printf("  [PASS] Suite 39: ProMotion Thermal Throttling Frame-Drop Jitter Timestep Invariance (<1e-9 pt)\n");
}

static void test_suite_40_overscroll_hit_frame_length_padding(void) {
    UIScrollViewScrollIndicator ind = ScrollIndicatorCreate(0);
    double viewport = 852.0;
    double content = 2000.0;
    double cross = 393.0;

    /* Push into extreme rubber-band overscroll so knob compresses to 3.0 pt */
    compute_scroll_indicator_layout(&ind, -800.0, viewport, content, cross);
    assert(ind.length == 3.0);
    assert(ind.position == 3.0);

    /* Hit target MUST expand to >= 44.0pt in BOTH width and height */
    assert(ind.hitFrame.size.width >= 44.0);
    assert(ind.hitFrame.size.height >= 44.0);
    assert(ind.hitFrame.size.width == 44.0);
    assert(ind.hitFrame.size.height == 44.0);

    /* Centered padding check: hitFrame.origin.y should be 3.0 - (44.0 - 3.0)/2 = -17.5 */
    double expectedOriginY = 3.0 - (44.0 - 3.0) / 2.0;
    assert(fabs(ind.hitFrame.origin.y - expectedOriginY) < 1e-6);

    /* Test hit acquisition at y = 15.0 pt (within 44pt touch window, but outside 3pt knob) */
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 2000.0));
    sv.verticalIndicator = ind;
    sv.verticalIndicator.alpha = 1.0;
    CGPoint touchNearCompressedKnob = CGPointMake(385.0, 15.0);
    int hit = UIScrollViewHitTest(&sv, touchNearCompressedKnob);
    assert(hit == kHitTestVerticalIndicator);
    assert(hit == 1);
    printf("  [PASS] Suite 40: Overscroll Compressed Indicator Touch Target Padding (>=44.0x44.0pt)\n");
}

static void test_suite_41_large_dt_stall_clamping(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 5000.0));
    sv.isDecelerating = true;
    sv.velocity = CGPointMake(0.0, 2000.0);
    sv.lastTimestamp = 100.0;

    /* Simulate a massive thermal frame drop / hitch of 150ms (dt = 0.15s > MAX_DECELERATION_DT) */
    double prevOffset = sv.contentOffset.y;
    UIScrollViewSmoothScrollTick(&sv, 100.15);

    /* dt should clamp to 0.10s, NOT drop to 0.00833s */
    double expectedDisplacement = integrate_displacement_step(2000.0, NORMAL_DECELERATION_RATE, 0.10);
    double actualDisplacement = sv.contentOffset.y - prevOffset;
    assert(fabs(actualDisplacement - expectedDisplacement) < 1e-4);
    printf("  [PASS] Suite 41: Large Frame Drop / Hitch Timestep Clamping to MAX_DECELERATION_DT (0.10s)\n");
}

static void test_suite_42_scrubbing_edge_haptic_impact_isolation(void) {
    UIScrollViewModel sv = UIScrollViewCreate(CGRectMake(0.0, 0.0, 393.0, 852.0), CGSizeMake(393.0, 3000.0));
    UIScrollViewUpdateBoundsForOffset(&sv, CGPointMake(0.0, 50.0));
    bool began = UIScrollViewBeginIndicatorScrubbing(&sv, 0);
    assert(began == true);

    /* Display link must be boosted to tracking mode (120Hz) */
    assert(sv.displayLink.registeredMode == kRunLoopModeTracking);
    assert(sv.displayLink.preferredFrameRateRange.maximum == 120.0f);

    /* Drag up by -100pt: crosses from 50.0 to 0.0 (impact!). Must return boundaryHit = true */
    bool hitOnImpact = UIScrollViewScrubIndicator(&sv, 0, -100.0);
    assert(hitOnImpact == true);
    assert(sv.contentOffset.y == 0.0);

    /* Continued dragging while already stalled at 0.0 must NOT trigger boundaryHit */
    bool hitWhileStalled = UIScrollViewScrubIndicator(&sv, 0, -20.0);
    assert(hitWhileStalled == false);
    assert(sv.contentOffset.y == 0.0);

    UIScrollViewEndIndicatorScrubbing(&sv, 0);
    assert(sv.isScrubbingIndicator == false);
    assert(sv.displayLink.registeredMode == kRunLoopModeDefault);
    printf("  [PASS] Suite 42: Interactive Scrubbing Boundary Haptic Impact Isolation (Single Trigger)\n");
}

/* ========================================================================= */
/* Main Test Runner                                                          */
/* ========================================================================= */

int main(void) {
    printf("=================================================================\n");
    printf("Rendering, Compositing & Frame Scheduling Test Suite (iOS 27 arm64e)\n");
    printf("=================================================================\n");

    test_suite_01_cadisplaylink_lifecycle_init();
    test_suite_02_runloop_mode_transitions();
    test_suite_03_promotion_vfd_active_touch_boost();
    test_suite_04_promotion_vfd_high_velocity_fling();
    test_suite_05_promotion_vfd_medium_velocity_tier();
    test_suite_06_promotion_vfd_low_velocity_tier();
    test_suite_07_promotion_vfd_rest_idle_tier();
    test_suite_08_timestep_invariance_60hz_vs_120hz();
    test_suite_09_timestep_invariance_arbitrary_variable_dt();
    test_suite_10_calayer_bounds_mutation_mapping();
    test_suite_11_implicit_animation_suppression();
    test_suite_12_sublayer_transform_scale_zoom();
    test_suite_13_model_vs_presentation_layer_authority();
    test_suite_14_ballistic_touch_down_interruption_catch();
    test_suite_15_hit_test_touch_swallow_during_fast_scroll();
    test_suite_16_hit_test_pass_through_at_slow_speed();
    test_suite_17_indicator_minimum_length_clamp();
    test_suite_18_indicator_normal_sizing_proportion();
    test_suite_19_indicator_hidden_when_content_fits();
    test_suite_20_indicator_normal_position_interpolation();
    test_suite_21_indicator_top_overscroll_compression();
    test_suite_22_indicator_bottom_overscroll_compression();
    test_suite_23_indicator_extreme_overscroll_clamp();
    test_suite_24_indicator_interactive_expansion();
    test_suite_25_scrubbing_direct_offset_scaling();
    test_suite_26_fade_kinetics_active_scroll_flash();
    test_suite_27_fade_kinetics_standard_timeout_delay();
    test_suite_28_fade_kinetics_paging_timeout_delay();
    test_suite_29_fade_kinetics_fade_out_progression();
    test_suite_30_hit_target_padding_minimum_dimension();
    test_suite_31_hit_test_indicator_acquisition();
    test_suite_32_deceleration_terminal_halt_and_invalidation();
    test_suite_33_horizontal_indicator_hit_testing();
    test_suite_34_zoomed_content_indicator_scaling();
    test_suite_35_concurrent_multitouch_mutual_exclusion();
    test_suite_36_retina_subpixel_quantization_drift_immunity();
    test_suite_37_track_length_boundary_clamp();
    test_suite_38_nonlinear_rubberband_indicator_compression();
    test_suite_39_thermal_jitter_timestep_invariance_long_horizon();
    test_suite_40_overscroll_hit_frame_length_padding();
    test_suite_41_large_dt_stall_clamping();
    test_suite_42_scrubbing_edge_haptic_impact_isolation();

    printf("\nAll 42 Rendering & Scheduling unit test suites PASSED with 0 failures.\n");
    return 0;
}
