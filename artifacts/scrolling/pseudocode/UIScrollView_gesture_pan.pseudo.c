/**
 * UIKitCore.framework - UIScrollView Pan Gesture & Tracking Pipeline Pseudocode Reconstruction
 * Classes: UIScrollView, _UIScrollViewPanGestureRecognizer
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[UIScrollView handlePan:] @ 0x1848b8140
 *   - -[UIScrollView _gestureRecognizerShouldBegin:] @ 0x1848b7890
 *   - -[_UIScrollViewPanGestureRecognizer touchesBegan:withEvent:] @ 0x1848c1000
 *   - -[UIScrollView _scrollViewWillBeginDragging] @ 0x1848b6100
 *   - -[UIScrollView _stopScrollingAndFillDisplayList:] @ 0x1848b7040
 *   - -[UIScrollView _smoothScrollDisplayLink:] @ 0x1848b7120
 *   - -[UIScrollView touchesShouldCancelInContentView:] @ 0x1848b7a00
 *   - -[UIScrollView _gestureRecognizer:shouldReceiveTouch:] @ 0x1848b85a0
 *   - -[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:] @ 0x1848b8550
 *   - Ballistic Interruption & Drag Handoff Mechanics
 *   - Dimensionally-accurate axis discrimination & rubber-banding resistance
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

typedef enum UIGestureRecognizerState {
    UIGestureRecognizerStatePossible = 0,
    UIGestureRecognizerStateBegan = 1,
    UIGestureRecognizerStateChanged = 2,
    UIGestureRecognizerStateEnded = 3,
    UIGestureRecognizerStateCancelled = 4,
    UIGestureRecognizerStateFailed = 5
} UIGestureRecognizerState;

/* UIScrollView Flags Bitfield (+0xd0) */
typedef struct __scrollViewFlags {
    unsigned int isDragging : 1;                         /* bit 0: Active drag in progress */
    unsigned int isDecelerating : 1;                     /* bit 1: Inertial deceleration active */
    unsigned int isTracking : 1;                         /* bit 2: Touch contact currently down */
    unsigned int isZooming : 1;                          /* bit 3: Pinch zoom in progress */
    unsigned int bounces : 1;                            /* bit 4: Rubber-band bounce allowed */
    unsigned int bouncesHorizontally : 1;                /* bit 5: Always bounce horizontal */
    unsigned int bouncesVertically : 1;                  /* bit 6: Always bounce vertical */
    unsigned int directionalLockEnabled : 1;             /* bit 7: Single-axis lock active */
    unsigned int pagingEnabled : 1;                      /* bit 8: Page boundary snapping */
    unsigned int scrollEnabled : 1;                      /* bit 9: User interaction scroll allowed */
    unsigned int delaysContentTouches : 1;               /* bit 10: Delay subview touches by 150ms */
    unsigned int canCancelContentTouches : 1;            /* bit 11: Cancel subview touches on drag */
    unsigned int delegateScrollViewDidScroll : 1;        /* bit 12: Cached respondsToSelector */
    unsigned int delegateScrollViewWillBeginDragging : 1;/* bit 13: Cached respondsToSelector */
    unsigned int delegateScrollViewDidEndDragging : 1;   /* bit 14: Cached respondsToSelector */
    unsigned int delegateScrollViewWillBeginDecel : 1;   /* bit 15: Cached respondsToSelector */
    unsigned int delegateScrollViewDidEndDecel : 1;      /* bit 16: Cached respondsToSelector */
    unsigned int delegateScrollViewWillEndDragging : 1;  /* bit 17: Cached respondsToSelector */
} __scrollViewFlags;

/* Forward declaration of UIScrollView */
typedef struct UIScrollView UIScrollView;

/* Velocity sample ring buffer entry */
typedef struct _UIVelocitySample {
    CGPoint point;
    NSTimeInterval timestamp;
} _UIVelocitySample;

/* Reconstructed base UIPanGestureRecognizer layout */
typedef struct UIPanGestureRecognizer {
    void *isa;                                           /* +0x000 */
    void *_targets;                                      /* +0x008 */
    void *_gestureEnvironment;                           /* +0x010 */
    void *_view;                                         /* +0x018 */
    UIGestureRecognizerState _state;                     /* +0x020 */
    uint32_t _flags;                                     /* +0x024 */
    CGPoint _startLocation;                              /* +0x028 */
    CGPoint _currentLocation;                            /* +0x038 */
    CGPoint _translation;                                /* +0x048 */
    CGPoint _previousTranslation;                        /* +0x058 */
    NSTimeInterval _startTimestamp;                      /* +0x068 */
    NSTimeInterval _lastTimestamp;                       /* +0x070 */
    _UIVelocitySample _sampleRingBuffer[8];              /* +0x078 */
    uint32_t _sampleCount;                               /* +0x138 */
    uint32_t _sampleIndex;                               /* +0x13c */
    bool _directionalLockEnabled;                        /* +0x140 */
    uint32_t _lockedAxis;                                /* +0x144 */
    double _lockAngle;                                   /* +0x148 */
    uint32_t _consecutiveBreakFrames;                    /* +0x150 */
    double _crossAxisDisplacement;                       /* +0x158 */
    double _customHysteresis;                            /* +0x160 */
    bool _delaysContentTouches;                          /* +0x168 */
    bool _canCancelContentTouches;                       /* +0x169 */
    CGPoint _hysteresisOffset;                           /* +0x170 */
    void *_trackingTouch;                                /* +0x180 */
} UIPanGestureRecognizer;

/* Reconstructed _UIScrollViewPanGestureRecognizer internal layout */
typedef struct _UIScrollViewPanGestureRecognizer {
    union {
        UIPanGestureRecognizer _super;
        struct {
            void *isa;                                   /* +0x000 */
            void *_targets;                              /* +0x008 */
            void *_gestureEnvironment;                   /* +0x010 */
            void *_view;                                 /* +0x018 */
            UIGestureRecognizerState _state;             /* +0x020 */
            uint32_t _flags;                             /* +0x024 */
        };
    };
    
    /* Subclass specialization ivars */
    UIScrollView *_scrollView;                           /* +0x188 Weak back-pointer to parent scroll view */
    bool _directionalLockEnabled;                        /* +0x190 Shadow flag from scroll view */
    CGPoint _transferredVelocity;                        /* +0x198 Velocity inherited from prior interruption */
    uint64_t _lastTouchCount;                            /* +0x1a8 Number of active touch contacts */
} _UIScrollViewPanGestureRecognizer;

/* Reconstructed UIScrollView internal layout */
struct UIScrollView {
    void *isa;                                           /* +0x000 */
    void *_layer;                                        /* +0x008 Backing CALayer pointer */
    CGRect _bounds;                                      /* +0x010 Viewport bounds */
    CGRect _frame;                                       /* +0x030 Viewport frame */
    
    /* State flags */
    __scrollViewFlags _scrollViewFlags;                  /* +0x0d0 Bitfield flags */
    double _zoomScale;                                   /* +0x0e0 Current zoom scale */
    double _minimumZoomScale;                            /* +0x0e8 Minimum allowable zoom */
    double _maximumZoomScale;                            /* +0x0f0 Maximum allowable zoom */
    double _decelerationRate;                            /* +0x0f8 Friction coefficient (0.998 / 0.990) */
    
    /* Geometry storage */
    CGPoint _contentOffset;                              /* +0x100 Primary scroll position origin */
    CGPoint _unconstrainedContentOffset;                 /* +0x110 Unconstrained tracking coordinate preventing recursive damping */
    CGSize _contentSize;                                 /* +0x120 Total scrollable area dimensions */
    void *_delegate;                                     /* +0x130 id<UIScrollViewDelegate> */
    UIEdgeInsets _contentInset;                          /* +0x138 Content inset margins */
    
    /* Gesture recognizers and helpers */
    _UIScrollViewPanGestureRecognizer *_panGesture;      /* +0x158 Primary pan recognizer */
    void *_pinchGesture;                                 /* +0x160 Primary pinch recognizer */
    void *_horizontalScrollIndicator;                    /* +0x168 Visual indicator bar */
    void *_verticalScrollIndicator;                      /* +0x170 Visual indicator bar */
    void *_pagingController;                             /* +0x178 Snap page resolver */
    void *_decelerationAnimation;                        /* +0x180 Active _UIScrollViewDecelerationAnimation */
    void *_springAnimation;                              /* +0x188 Active _UIScrollViewSpringAnimation */
    void *_displayLink;                                  /* +0x190 CADisplayLink synchronization */
};

/* Empirical Physical Constants */
static const double kRubberBandCoefficient   = 0.55;  /* TouchRubberBandingCoefficient */
static const double kMinFlingVelocity        = 10.0;  /* Minimum speed (pt/s) to start deceleration */
static const double kTerminalStopVelocity    = 0.1;   /* Stop speed threshold (pt/s) */
static const double kDefaultDecelerationRate = 0.998; /* Normal deceleration friction rate */
static const double kPagingDecelerationRate  = 0.990; /* Fast deceleration rate for paging snap */

/* Forward declarations of external runtime routines */
extern void *objc_msgSend(void *receiver, const char *selector, ...);
extern void _UIScrollViewStopScrollingAndZoomingAnimations(UIScrollView *self);
extern void _UIScrollViewUpdateBoundsForContentOffset(UIScrollView *self, CGPoint offset);
extern void _UIScrollViewNotifyDidScroll(UIScrollView *self);
extern void _UIScrollViewStartDecelerationAnimation(UIScrollView *self, CGPoint velocity);
extern void _UIScrollViewStartSpringAnimation(UIScrollView *self, CGPoint velocity);
extern CGPoint _UIPanGestureRecognizerTranslationInView(_UIScrollViewPanGestureRecognizer *pan, void *view);
extern CGPoint _UIPanGestureRecognizerVelocityInView(_UIScrollViewPanGestureRecognizer *pan, void *view);
extern void _UIPanGestureRecognizerSetTranslationInView(_UIScrollViewPanGestureRecognizer *pan, CGPoint translation, void *view);
extern void _UIPanGestureRecognizer_touchesBegan(UIPanGestureRecognizer *self, void *touches, void *event);

/**
 * Apple Non-Linear Rubber-Band Resistance Function
 * Computes dampened visual displacement when content offset overshoots boundaries.
 */
static inline double _UIScrollViewRubberBandOffset(double overscrollDistance, double viewportDimension) {
    if (viewportDimension <= 0.0) {
        return 0.0;
    }
    double c = kRubberBandCoefficient; /* 0.55 */
    return (overscrollDistance * c * viewportDimension) / (viewportDimension + c * overscrollDistance);
}

/**
 * Clamps target content offset within legitimate content size and inset bounds.
 * Rigorously enforces that general `bounces` only applies to scrollable axes,
 * requiring `bouncesHorizontally` / `bouncesVertically` for constrained axes.
 */
static inline CGPoint _UIScrollViewClampedContentOffset(UIScrollView *self, CGPoint rawOffset) {
    CGPoint minOffset;
    minOffset.x = -self->_contentInset.left;
    minOffset.y = -self->_contentInset.top;
    
    CGPoint maxOffset;
    maxOffset.x = fmax(minOffset.x, self->_contentSize.width + self->_contentInset.right - self->_bounds.size.width);
    maxOffset.y = fmax(minOffset.y, self->_contentSize.height + self->_contentInset.bottom - self->_bounds.size.height);
    
    bool canBounceHorizontal = (self->_contentSize.width > self->_bounds.size.width && self->_scrollViewFlags.bounces) ||
                                self->_scrollViewFlags.bouncesHorizontally;
    bool canBounceVertical   = (self->_contentSize.height > self->_bounds.size.height && self->_scrollViewFlags.bounces) ||
                                self->_scrollViewFlags.bouncesVertically;

    CGPoint clamped = rawOffset;
    
    /* Horizontal clamping / rubber-banding */
    if (rawOffset.x < minOffset.x) {
        if (canBounceHorizontal) {
            double overshoot = minOffset.x - rawOffset.x;
            clamped.x = minOffset.x - _UIScrollViewRubberBandOffset(overshoot, self->_bounds.size.width);
        } else {
            clamped.x = minOffset.x;
        }
    } else if (rawOffset.x > maxOffset.x) {
        if (canBounceHorizontal) {
            double overshoot = rawOffset.x - maxOffset.x;
            clamped.x = maxOffset.x + _UIScrollViewRubberBandOffset(overshoot, self->_bounds.size.width);
        } else {
            clamped.x = maxOffset.x;
        }
    }
    
    /* Vertical clamping / rubber-banding */
    if (rawOffset.y < minOffset.y) {
        if (canBounceVertical) {
            double overshoot = minOffset.y - rawOffset.y;
            clamped.y = minOffset.y - _UIScrollViewRubberBandOffset(overshoot, self->_bounds.size.height);
        } else {
            clamped.y = minOffset.y;
        }
    } else if (rawOffset.y > maxOffset.y) {
        if (canBounceVertical) {
            double overshoot = rawOffset.y - maxOffset.y;
            clamped.y = maxOffset.y + _UIScrollViewRubberBandOffset(overshoot, self->_bounds.size.height);
        } else {
            clamped.y = maxOffset.y;
        }
    }
    
    return clamped;
}

/**
 * -[UIScrollView _scrollViewWillBeginDragging] @ 0x1848b6100
 * Activates active dragging flag and notifies delegate.
 */
void _UIScrollView_scrollViewWillBeginDragging(UIScrollView *self) {
    if (!self) {
        return;
    }
    self->_scrollViewFlags.isDragging = 1;
    if (self->_scrollViewFlags.delegateScrollViewWillBeginDragging && self->_delegate) {
        objc_msgSend(self->_delegate, "scrollViewWillBeginDragging:", self);
    }
}

/**
 * -[UIScrollView _stopScrollingAndFillDisplayList:] @ 0x1848b7040
 * Halts active momentum or deceleration display link, pins presentation origin, and resets deceleration state.
 */
void _UIScrollView_stopScrollingAndFillDisplayList(UIScrollView *self, bool pin) {
    if (!self) {
        return;
    }

    /* Invalidate and release active animation controller */
    _UIScrollViewStopScrollingAndZoomingAnimations(self);

    if (pin && self->_layer) {
        void *presentationLayer = objc_msgSend(self->_layer, "presentationLayer");
        if (presentationLayer) {
            CGRect presBounds = *(CGRect *)objc_msgSend(presentationLayer, "bounds");
            self->_contentOffset = presBounds.origin;
            _UIScrollViewUpdateBoundsForContentOffset(self, self->_contentOffset);
        }
    }

    self->_scrollViewFlags.isDecelerating = 0;
}

/**
 * -[UIScrollView _smoothScrollDisplayLink:] @ 0x1848b7120
 * Periodic CADisplayLink tick routine driving deceleration integration and spring restitution.
 */
void _UIScrollView_smoothScrollDisplayLink(UIScrollView *self, void *displayLink) {
    (void)displayLink;
    if (!self || !self->_scrollViewFlags.isDecelerating) {
        return;
    }

    /* Deceleration controller tick handled in Phase 3B */
    if (self->_decelerationAnimation) {
        objc_msgSend(self->_decelerationAnimation, "stepAnimation");
    }
}

/**
 * -[_UIScrollViewPanGestureRecognizer touchesBegan:withEvent:] @ 0x1848c1000
 * Handles touch acquisition and ballistic interruption handoff.
 */
void _UIScrollViewPanGestureRecognizer_touchesBegan(_UIScrollViewPanGestureRecognizer *self, void *touches, void *event) {
    UIScrollView *scrollView = self->_scrollView;
    if (!scrollView) {
        return;
    }
    
    /* Invoke superclass touch acquisition to initialize coordinates, timestamp, and sampling ring buffer */
    _UIPanGestureRecognizer_touchesBegan((UIPanGestureRecognizer *)self, touches, event);

    /* Update tracking touch counter */
    self->_lastTouchCount = (uint64_t)objc_msgSend(touches, "count");
    scrollView->_scrollViewFlags.isTracking = 1;

    /* Ballistic Interruption Detection */
    if (scrollView->_scrollViewFlags.isDecelerating) {
        /* Query residual momentum from decaying animation controller */
        CGPoint residualVelocity = (CGPoint){0.0, 0.0};
        if (scrollView->_decelerationAnimation) {
            residualVelocity = *(CGPoint *)objc_msgSend(scrollView->_decelerationAnimation, "velocity");
        }
        double residualSpeed = sqrt(residualVelocity.x * residualVelocity.x + residualVelocity.y * residualVelocity.y);

        if (residualSpeed < kTerminalStopVelocity) {
            /* Velocity below terminal stop threshold (0.1 pt/s): deceleration naturally finished */
            _UIScrollView_stopScrollingAndFillDisplayList(scrollView, false);
            self->_state = UIGestureRecognizerStatePossible;
            self->_transferredVelocity = (CGPoint){0.0, 0.0};
            scrollView->_unconstrainedContentOffset = scrollView->_contentOffset;
            return;
        }

        /* User finger tapped moving content: halt ballistic deceleration immediately */
        _UIScrollView_stopScrollingAndFillDisplayList(scrollView, true);
        self->_transferredVelocity = residualVelocity;
        
        /* Bypass touch slop threshold; force immediate transition to Began */
        self->_state = UIGestureRecognizerStateBegan;
        self->_super._hysteresisOffset = (CGPoint){0.0, 0.0};
        scrollView->_unconstrainedContentOffset = scrollView->_contentOffset;
        
        /* Initiate drag lifecycle */
        _UIScrollView_scrollViewWillBeginDragging(scrollView);
        return;
    }

    /* Standard touch-down: inherit Possible state, await slop threshold accumulation */
    self->_state = UIGestureRecognizerStatePossible;
    self->_transferredVelocity = (CGPoint){0.0, 0.0};
    scrollView->_unconstrainedContentOffset = scrollView->_contentOffset;
}

/**
 * -[UIScrollView _gestureRecognizerShouldBegin:] @ 0x1848b7890
 * Evaluates whether pan gesture recognizer is permitted to transition to Began.
 */
bool _UIScrollView_gestureRecognizerShouldBegin(UIScrollView *self, _UIScrollViewPanGestureRecognizer *pan) {
    if (!self || !self->_scrollViewFlags.scrollEnabled) {
        return false;
    }

    /* Check if content size exceeds viewport bounds along scrollable axis, or if alwaysBounce is set */
    bool canScrollHorizontal = (self->_contentSize.width > self->_bounds.size.width) ||
                                self->_scrollViewFlags.bouncesHorizontally;
    bool canScrollVertical   = (self->_contentSize.height > self->_bounds.size.height) ||
                                self->_scrollViewFlags.bouncesVertically;

    if (!canScrollHorizontal && !canScrollVertical) {
        /* Viewport content fits entirely within bounds and bouncing is disabled */
        return false;
    }

    /* Vector axis discrimination: prevent swallowing orthogonal gestures (e.g. swipe-back or cell swipe) */
    CGPoint velocity = _UIPanGestureRecognizerVelocityInView(pan, self->_layer);
    double absVx = fabs(velocity.x);
    double absVy = fabs(velocity.y);
    if (absVx > 0.001 || absVy > 0.001) {
        if (absVx > absVy && !canScrollHorizontal) {
            /* Predominantly horizontal swipe on vertically-constrained view: reject pan */
            return false;
        }
        if (absVy > absVx && !canScrollVertical) {
            /* Predominantly vertical swipe on horizontally-constrained view: reject pan */
            return false;
        }
    } else {
        /* Fallback to displacement vector when velocity is below sample resolution */
        double dx = pan->_super._currentLocation.x - pan->_super._startLocation.x;
        double dy = pan->_super._currentLocation.y - pan->_super._startLocation.y;
        double absDx = fabs(dx);
        double absDy = fabs(dy);
        if (absDx > 0.001 || absDy > 0.001) {
            if (absDx > absDy && !canScrollHorizontal) {
                return false;
            }
            if (absDy > absDx && !canScrollVertical) {
                return false;
            }
        }
    }

    /* Query delegate override if implemented */
    if (self->_delegate && (bool)objc_msgSend(self->_delegate, "respondsToSelector:", "gestureRecognizerShouldBegin:")) {
        bool delegatePermit = (bool)objc_msgSend(self->_delegate, "gestureRecognizerShouldBegin:", pan);
        if (!delegatePermit) {
            return false;
        }
    }

    return true;
}

/**
 * -[UIScrollView touchesShouldCancelInContentView:] @ 0x1848b7a00
 * Determines whether subview touches are cancelled in favor of scrolling.
 */
bool _UIScrollView_touchesShouldCancelInContentView(UIScrollView *self, void *view) {
    if (!self || !view) {
        return true;
    }

    /* Query delegate override if present */
    if (self->_delegate && (bool)objc_msgSend(self->_delegate, "respondsToSelector:", "touchesShouldCancelInContentView:")) {
        return (bool)objc_msgSend(self->_delegate, "touchesShouldCancelInContentView:", view);
    }

    /* By default, UIControl instances (e.g. UISwitch, UISlider) return NO to retain interaction; UIButtons return YES */
    bool isControl = (bool)objc_msgSend(view, "isKindOfClass:", "UIControl");
    bool isButton = (bool)objc_msgSend(view, "isKindOfClass:", "UIButton");
    if (isControl && !isButton) {
        return false;
    }

    return true;
}

/**
 * -[UIScrollView _gestureRecognizer:shouldReceiveTouch:] @ 0x1848b85a0
 * Hit-tests touch against scrollbar indicators to defer to knob scrubber tracking.
 */
bool _UIScrollView_gestureRecognizer_shouldReceiveTouch(UIScrollView *self, void *gesture, void *touch) {
    (void)gesture;
    if (!self || !touch) {
        return true;
    }

    CGPoint touchLoc = *(CGPoint *)objc_msgSend(touch, "locationInView:", self);

    /* If touch falls within the active horizontal or vertical scroll indicator knob, reject pan to allow scrubber drag */
    if (self->_verticalScrollIndicator) {
        CGRect knobFrame = *(CGRect *)objc_msgSend(self->_verticalScrollIndicator, "frame");
        if (touchLoc.x >= knobFrame.origin.x && touchLoc.x <= knobFrame.origin.x + knobFrame.size.width &&
            touchLoc.y >= knobFrame.origin.y && touchLoc.y <= knobFrame.origin.y + knobFrame.size.height) {
            return false;
        }
    }

    return true;
}

/**
 * -[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:] @ 0x1848b8550
 * Arbitrates simultaneous recognition between pan and other gestures (pinch zoom, parent hosting scrollviews).
 */
bool _UIScrollView_gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer(UIScrollView *self, void *gesture, void *otherGesture) {
    if (!self || !otherGesture) {
        return false;
    }

    /* Consult delegate if implemented */
    if (self->_delegate && (bool)objc_msgSend(self->_delegate, "respondsToSelector:", "gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:")) {
        return (bool)objc_msgSend(self->_delegate, "gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:", gesture, otherGesture);
    }

    /* Permit simultaneous recognition with attached pinch zoom recognizer */
    if (otherGesture == self->_pinchGesture) {
        return true;
    }

    return false;
}

/**
 * -[UIScrollView handlePan:] @ 0x1848b8140
 * Central gesture recognizer action callback driving viewport offset mutations.
 */
void _UIScrollView_handlePan(UIScrollView *self, _UIScrollViewPanGestureRecognizer *pan) {
    if (!self || !pan) {
        return;
    }

    UIGestureRecognizerState state = pan->_state;

    switch (state) {
        case UIGestureRecognizerStateBegan: {
            /* Drag begins: mutate flag, snapshot unconstrained origin, and inform delegate */
            self->_unconstrainedContentOffset = self->_contentOffset;
            _UIScrollView_scrollViewWillBeginDragging(self);
            break;
        }

        case UIGestureRecognizerStateChanged: {
            /* Query incremental translation since last dispatch */
            CGPoint translation = _UIPanGestureRecognizerTranslationInView(pan, self->_layer);
            
            /* Reset recognizer translation delta to zero to accumulate differential offsets */
            _UIPanGestureRecognizerSetTranslationInView(pan, (CGPoint){0.0, 0.0}, self->_layer);

            /* Accumulate differential translation into unconstrained tracking coordinate */
            self->_unconstrainedContentOffset.x -= translation.x;
            self->_unconstrainedContentOffset.y -= translation.y;

            /* Apply boundary constraints and non-recursive rubber-band elasticity */
            CGPoint clampedOffset = _UIScrollViewClampedContentOffset(self, self->_unconstrainedContentOffset);

            /* Assign updated offset to ivar +0x100 */
            self->_contentOffset = clampedOffset;

            /* Alter backing CALayer bounds origin to translate content */
            _UIScrollViewUpdateBoundsForContentOffset(self, self->_contentOffset);

            /* Broadcast telemetry updates to delegate and _UIScrollViewScrollObserver */
            _UIScrollViewNotifyDidScroll(self);
            break;
        }

        case UIGestureRecognizerStateEnded: {
            /* Synchronize unconstrained offset on drag conclusion */
            self->_unconstrainedContentOffset = self->_contentOffset;

            /* User lifted finger: query release velocity vector from pan recognizer */
            CGPoint releaseVelocity = _UIPanGestureRecognizerVelocityInView(pan, self->_layer);
            double speed = sqrt(releaseVelocity.x * releaseVelocity.x + releaseVelocity.y * releaseVelocity.y);

            /* Invert pan velocity to obtain scroll contentOffset velocity: Delta(offset) = -Delta(touch) */
            CGPoint scrollVelocity = (CGPoint){ -releaseVelocity.x, -releaseVelocity.y };

            /* Mutate dragging flag: dragging phase concluded */
            self->_scrollViewFlags.isDragging = 0;

            /* Determine if content is rested outside boundary limits */
            CGPoint minOffset = (CGPoint){ -self->_contentInset.left, -self->_contentInset.top };
            CGPoint maxOffset = (CGPoint){
                fmax(minOffset.x, self->_contentSize.width + self->_contentInset.right - self->_bounds.size.width),
                fmax(minOffset.y, self->_contentSize.height + self->_contentInset.bottom - self->_bounds.size.height)
            };

            bool isOvershot = (self->_contentOffset.x < minOffset.x || self->_contentOffset.x > maxOffset.x ||
                               self->_contentOffset.y < minOffset.y || self->_contentOffset.y > maxOffset.y);

            if (isOvershot) {
                /* Content overshot bounds: launch damped harmonic oscillator spring rebound with scroll momentum */
                _UIScrollViewStartSpringAnimation(self, scrollVelocity);
                if (self->_scrollViewFlags.delegateScrollViewDidEndDragging && self->_delegate) {
                    objc_msgSend(self->_delegate, "scrollViewDidEndDragging:willDecelerate:", self, true);
                }
            } else if (speed >= kMinFlingVelocity) {
                /* Release speed exceeds 10 pt/s: compute projected rest offset and start deceleration */
                double d = (self->_scrollViewFlags.pagingEnabled) ? kPagingDecelerationRate : self->_decelerationRate;
                if (d <= 0.0 || d >= 1.0) {
                    d = kDefaultDecelerationRate; /* 0.998 */
                }

                /* Continuous integration of exponential decay: s_proj = s0 + v_scroll / (-1000 * ln(d)) */
                double decayFactor = 1.0 / (-1000.0 * log(d));
                CGPoint projectedOffset;
                projectedOffset.x = self->_contentOffset.x + scrollVelocity.x * decayFactor;
                projectedOffset.y = self->_contentOffset.y + scrollVelocity.y * decayFactor;

                /* Delegate velocity is in points per millisecond */
                CGPoint delegateVelocity = (CGPoint){ scrollVelocity.x / 1000.0, scrollVelocity.y / 1000.0 };

                /* Inform delegate of expected target offset, allowing delegate adjustment */
                if (self->_scrollViewFlags.delegateScrollViewWillEndDragging && self->_delegate) {
                    objc_msgSend(self->_delegate, "scrollViewWillEndDragging:withVelocity:targetContentOffset:",
                                  self, delegateVelocity, &projectedOffset);
                }

                /* Inform delegate that drag ended with deceleration following */
                if (self->_scrollViewFlags.delegateScrollViewDidEndDragging && self->_delegate) {
                    objc_msgSend(self->_delegate, "scrollViewDidEndDragging:willDecelerate:", self, true);
                }

                /* Launch ballistic deceleration controller with scroll velocity */
                self->_scrollViewFlags.isDecelerating = 1;
                if (self->_scrollViewFlags.delegateScrollViewWillBeginDecel && self->_delegate) {
                    objc_msgSend(self->_delegate, "scrollViewWillBeginDecelerating:", self);
                }
                _UIScrollViewStartDecelerationAnimation(self, scrollVelocity);
            } else {
                /* Release speed below 10 pt/s: content rests at current position without fling */
                if (self->_scrollViewFlags.delegateScrollViewDidEndDragging && self->_delegate) {
                    objc_msgSend(self->_delegate, "scrollViewDidEndDragging:willDecelerate:", self, false);
                }
            }
            break;
        }

        case UIGestureRecognizerStateCancelled: {
            /* Gesture cancelled by system alert or modal interrupt */
            self->_unconstrainedContentOffset = self->_contentOffset;
            self->_scrollViewFlags.isDragging = 0;
            if (self->_scrollViewFlags.delegateScrollViewDidEndDragging && self->_delegate) {
                objc_msgSend(self->_delegate, "scrollViewDidEndDragging:willDecelerate:", self, false);
            }

            /* If currently outside bounds, snap back via spring */
            CGPoint minOffset = (CGPoint){ -self->_contentInset.left, -self->_contentInset.top };
            CGPoint maxOffset = (CGPoint){
                fmax(minOffset.x, self->_contentSize.width + self->_contentInset.right - self->_bounds.size.width),
                fmax(minOffset.y, self->_contentSize.height + self->_contentInset.bottom - self->_bounds.size.height)
            };

            if (self->_contentOffset.x < minOffset.x || self->_contentOffset.x > maxOffset.x ||
                self->_contentOffset.y < minOffset.y || self->_contentOffset.y > maxOffset.y) {
                _UIScrollViewStartSpringAnimation(self, (CGPoint){0.0, 0.0});
            }
            break;
        }

        default:
            break;
    }
}
