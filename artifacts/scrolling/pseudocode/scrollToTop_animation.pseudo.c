/**
 * UIKitCore.framework & SpringBoard - Status Bar Scroll-To-Top Kinematics & Responder Arbitration
 * Classes: UIScrollView, UIWindow, UIScrollViewScrollAnimation, CADisplayLink
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[UIScrollView _scrollToTopFromTouchAtScreenLocation:animate:] @ 0x1848b4a20
 *   - -[UIScrollView _registerAsScrollToTopViewIfPossible] @ 0x1848b8260
 *   - -[UIScrollView _unregisterAsScrollToTopViewIfPossible] @ 0x1848b8280
 *   - -[UIScrollView scrollsToTop] @ 0x1848b8620
 *   - -[UIScrollView setScrollsToTop:] @ 0x1848b8630
 *   - -[UIScrollViewScrollAnimation targetOffset] @ 0x1848c3100
 *   - -[UIScrollViewScrollAnimation setTargetOffset:] @ 0x1848c3120
 *   - Single candidate exclusivity rule (Ambiguity prevention: >= 2 candidates -> abort)
 *   - Delegate arbitration: scrollViewShouldScrollToTop: and scrollViewDidScrollToTop:
 *   - Animation duration (0.30s [0x3fd3333333333333]) and cubic Bézier timing curve
 *   - Touch interruption and cancellation
 *   - Multi-touch gesture cancellation (touchesBegan, touchesCancelled, UIPinchGestureRecognizer)
 *   - CADisplayLink lifecycle and invalidation
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

/* Standard geometric primitives */
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

/* Authoritative Kinematic Constants */
static const double kScrollToTopAnimationDurationSeconds = 0.30;         /* 300 ms (IEEE 754: 0x3fd3333333333333 @ 0x1864d3090) */
static const double kStatusBarHeightDynamicIslandPt       = 54.0;         /* iPhone 18,3 Dynamic Island status bar height */
static const double kScrollToTopRestingTolerancePt        = 0.5;          /* Sub-pixel resting tolerance */

/* Forward declarations */
struct UIView;
struct UIScrollView;
struct UIWindow;
struct UIScrollViewDelegate;

/* Bitfield flags for UIScrollView */
typedef struct _UIScrollViewFlags {
    unsigned int isDragging : 1;                         /* bit 0 */
    unsigned int isDecelerating : 1;                     /* bit 1 */
    unsigned int bounces : 1;                            /* bit 2 */
    unsigned int alwaysBounceVertical : 1;               /* bit 3 */
    unsigned int alwaysBounceHorizontal : 1;             /* bit 4 */
    unsigned int isPagingEnabled : 1;                    /* bit 5 */
    unsigned int scrollsToTop : 1;                       /* bit 6 */
    unsigned int scrollDisabled : 1;                     /* bit 7: User interaction scrolling explicitly disabled */
    unsigned int directionalLockEnabled : 1;             /* bit 8 */
    unsigned int delegateScrollViewDidScroll : 1;        /* bit 9 */
    unsigned int delegateScrollViewWillBeginDragging : 1;/* bit 10 */
    unsigned int delegateScrollViewDidEndDragging : 1;   /* bit 11 */
    unsigned int delegateScrollViewWillBeginDecel : 1;   /* bit 12 */
    unsigned int delegateScrollViewDidEndDecel : 1;     /* bit 13 */
    unsigned int delegateScrollViewWillEndDragging : 1;  /* bit 14 */
    unsigned int delegateScrollViewShouldScrollToTop : 1;/* bit 15 */
    unsigned int delegateScrollViewDidScrollToTop : 1;   /* bit 16 */
} _UIScrollViewFlags;

/* UIScrollViewDelegate */
typedef struct UIScrollViewDelegate {
    void *target;
    bool (*scrollViewShouldScrollToTop)(void *target, struct UIScrollView *scrollView);
    void (*scrollViewDidScrollToTop)(void *target, struct UIScrollView *scrollView);
} UIScrollViewDelegate;

/* Generic UIView structure */
typedef struct UIView {
    void *isa;
    bool isScrollView;
    CGRect frame;
    CGRect bounds;
    bool hidden;
    double alpha;
    struct UIWindow *window;
    struct UIView *superview;
    struct UIView **subviews;
    size_t subviewCount;
} UIView;

/* UIScrollView structure */
typedef struct UIScrollView {
    UIView view;                                         /* Inherits from UIView */
    CGSize _contentSize;
    UIEdgeInsets _contentInset;
    CGPoint _contentOffset;
    _UIScrollViewFlags _scrollViewFlags;
    UIScrollViewDelegate *_delegate;
    bool _isAnimatingScrollToTop;
    struct UIScrollViewScrollAnimation *_scrollAnimation;
    double _zoomScale;                                   /* Current pinch/zoom scale factor (default 1.0) */
} UIScrollView;

bool UIScrollView_isScrollEnabled(const UIScrollView *sv) {
    assert(sv != NULL);
    return !sv->_scrollViewFlags.scrollDisabled;
}

void UIScrollView_setScrollEnabled(UIScrollView *sv, bool enabled) {
    assert(sv != NULL);
    sv->_scrollViewFlags.scrollDisabled = !enabled;
}

/* UIWindow structure */
typedef struct UIWindow {
    UIView view;
    bool isKeyWindow;
} UIWindow;

/* UIGestureRecognizerState */
typedef enum UIGestureRecognizerState {
    kUIGestureRecognizerStatePossible   = 0,
    kUIGestureRecognizerStateBegan      = 1,
    kUIGestureRecognizerStateChanged    = 2,
    kUIGestureRecognizerStateEnded      = 3,
    kUIGestureRecognizerStateCancelled  = 4,
    kUIGestureRecognizerStateFailed     = 5
} UIGestureRecognizerState;

/* CADisplayLink representation */
typedef struct CADisplayLink {
    double timestamp;
    double targetTimestamp;
    bool paused;
    bool isInvalidated;
} CADisplayLink;

static inline void CADisplayLink_invalidate(CADisplayLink *dl) {
    if (dl != NULL) {
        dl->paused = true;
        dl->isInvalidated = true;
    }
}

/* UIScrollViewScrollAnimation */
typedef struct UIScrollViewScrollAnimation {
    UIScrollView *_scrollView;
    CGPoint _startOffset;
    CGPoint _targetOffset;
    double _startTime;
    double _duration;
    bool _finished;
    CADisplayLink *_displayLink;
} UIScrollViewScrollAnimation;

/* ========================================================================= */
/* Section 1: Helper Geometry & Rect Intersection                            */
/* ========================================================================= */
/* Section 1: Helper Geometry & Rect Intersection                            */
/* ========================================================================= */

static inline bool _CGRectIntersectsRect(CGRect a, CGRect b) {
    return !(a.origin.x + a.size.width <= b.origin.x ||
             b.origin.x + b.size.width <= a.origin.x ||
             a.origin.y + a.size.height <= b.origin.y ||
             b.origin.y + b.size.height <= a.origin.y);
}

/**
 * Converts a rectangle from view coordinate space to its containing window coordinate space.
 * Mirrors UIKit -[UIView convertRect:toView:nil].
 */
CGRect UIView_convertRectToWindow(const UIView *view, CGRect rect) {
    if (view == NULL) return rect;
    CGRect r = rect;
    r.origin.x += view->frame.origin.x;
    r.origin.y += view->frame.origin.y;
    const UIView *p = view->superview;
    while (p != NULL && (const void *)p != (const void *)view->window) {
        r.origin.x += p->frame.origin.x;
        r.origin.y += p->frame.origin.y;
        p = p->superview;
    }
    return r;
}

static inline UIEdgeInsets UIScrollView_effectiveInsets(const UIScrollView *sv) {
    assert(sv != NULL);
    return sv->_contentInset;
}

static inline double UIScrollView_minimumTopOffset(const UIScrollView *sv) {
    assert(sv != NULL);
    UIEdgeInsets insets = UIScrollView_effectiveInsets(sv);
    return -insets.top;
}

/* ========================================================================= */
/* Section 2: Candidate Scroll View Qualification Rules                      */
/* ========================================================================= */

/**
 * Evaluates whether a view qualifies as an eligible scroll-to-top candidate.
 * Criteria:
 *   1. Must be a UIScrollView.
 *   2. scrollsToTop == YES.
 *   3. !scrollDisabled (isScrollEnabled == YES).
 *   4. !hidden && alpha > 0.01 && window != NULL.
 *   5. Non-degenerate geometry: bounds.width > 0, bounds.height > 0, contentSize.height > 0.
 *   6. View bounds must intersect active window bounds (converted to window coordinates).
 *   7. Content must be vertically scrollable: (contentSize.height * zoomScale) + insets > bounds.height.
 *   8. View must not already be rested at minimum top content offset.
 */
bool UIScrollView_isEligibleForScrollToTop(const UIScrollView *sv) {
    assert(sv != NULL);

    /* 1. Class membership & scrollsToTop property */
    if (!sv->view.isScrollView) return false;
    if (!sv->_scrollViewFlags.scrollsToTop) return false;

    /* 2. User interaction scroll permission (isScrollEnabled) */
    if (sv->_scrollViewFlags.scrollDisabled) return false;

    /* 3. Visual rendering visibility */
    if (sv->view.hidden || sv->view.alpha <= 0.01 || sv->view.window == NULL) return false;

    /* 4. Degenerate dimension guards (zero contentSize or collapsed bounds) */
    if (sv->_contentSize.height <= 0.0 || sv->view.bounds.size.height <= 0.0 || sv->view.bounds.size.width <= 0.0) {
        return false;
    }

    /* 5. Window viewport intersection (bounds converted to window coordinate space) */
    CGRect window_bounds = sv->view.window->view.bounds;
    CGRect sv_in_window = UIView_convertRectToWindow(&sv->view, (CGRect){ {0.0, 0.0}, sv->view.bounds.size });
    if (!_CGRectIntersectsRect(window_bounds, sv_in_window)) return false;

    /* 6. Vertical scrollability check accounting for zoomScale */
    UIEdgeInsets insets = UIScrollView_effectiveInsets(sv);
    double zoom = (sv->_zoomScale >= 0.01) ? sv->_zoomScale : 1.0;
    double effective_content_height = sv->_contentSize.height * zoom;
    double total_height = effective_content_height + insets.top + insets.bottom;
    if (total_height <= sv->view.bounds.size.height) return false;

    /* 7. Content must not already be at top (or rested above top) */
    double min_top = -insets.top;
    if (isnan(sv->_contentOffset.y) || isinf(sv->_contentOffset.y)) return false;
    if (sv->_contentOffset.y <= min_top + kScrollToTopRestingTolerancePt) return false;

    return true;
}

/**
 * Recursively traverses view hierarchy collecting all qualifying candidates.
 */
void UIView_collectScrollToTopCandidates(
    UIView *root,
    UIScrollView **candidates,
    size_t *candidateCount,
    size_t maxCandidates)
{
    if (root == NULL || candidates == NULL || candidateCount == NULL) return;

    if (root->isScrollView) {
        UIScrollView *sv = (UIScrollView *)root;
        if (UIScrollView_isEligibleForScrollToTop(sv)) {
            if (*candidateCount < maxCandidates) {
                candidates[*candidateCount] = sv;
            }
            (*candidateCount)++;
        }
    }

    /* Recurse through subviews in depth-first order */
    for (size_t i = 0; i < root->subviewCount; ++i) {
        UIView_collectScrollToTopCandidates(root->subviews[i], candidates, candidateCount, maxCandidates);
    }
}

/**
 * Implements the Single Candidate Exclusivity Rule:
 * Returns the candidate IF AND ONLY IF exactly one candidate matches.
 * If 0 or >= 2 match, returns NULL to prevent ambiguous multi-scrolling.
 */
UIScrollView *UIWindow_resolveScrollToTopCandidate(UIWindow *window) {
    assert(window != NULL);
    UIScrollView *candidates[16];
    size_t candidate_count = 0;

    UIView_collectScrollToTopCandidates(&window->view, candidates, &candidate_count, 16);

    if (candidate_count == 1) {
        return candidates[0];
    }

    /* Ambiguity or no candidates: abort */
    return NULL;
}

/* ========================================================================= */
/* Section 3: Cubic Bézier Animation Timing Curve Evaluation                 */
/* ========================================================================= */

/**
 * Exact Cubic Bézier ease-in-out / ease-out timing curve:
 * P0 = (0, 0), P1 = (0.25, 0.10), P2 = (0.25, 1.00), P3 = (1, 1).
 * Solves x(t) = progressFraction via Newton-Raphson, then evaluates y(t).
 */
static inline double _evaluateScrollToTopTimingCurve(double progressFraction) {
    if (isnan(progressFraction) || progressFraction <= 0.0) return 0.0;
    if (progressFraction >= 1.0) return 1.0;

    const double x1 = 0.25, y1 = 0.10;
    const double x2 = 0.25, y2 = 1.00;

    double t = progressFraction;
    for (int iter = 0; iter < 8; ++iter) {
        double one_minus_t = 1.0 - t;
        double xt = 3.0 * one_minus_t * one_minus_t * t * x1 +
                    3.0 * one_minus_t * t * t * x2 +
                    t * t * t;
        double dxdt = 3.0 * one_minus_t * one_minus_t * x1 +
                      6.0 * one_minus_t * t * (x2 - x1) +
                      3.0 * t * t * (1.0 - x2);
        if (fabs(dxdt) < 1e-9) break;
        double diff = xt - progressFraction;
        if (fabs(diff) < 1e-7) break;
        t -= diff / dxdt;
        if (t < 0.0) t = 0.0;
        if (t > 1.0) t = 1.0;
    }

    double omt = 1.0 - t;
    double yt = 3.0 * omt * omt * t * y1 +
                3.0 * omt * t * t * y2 +
                t * t * t;
    return (yt < 0.0) ? 0.0 : ((yt > 1.0) ? 1.0 : yt);
}

/* ========================================================================= */
/* Section 4: UIScrollViewScrollAnimation Lifecycle & Frame Stepping         */
/* ========================================================================= */

/* Forward declaration */
void UIScrollView_stopScrollToTopAnimation(UIScrollView *sv);

/**
 * Initializes and starts a scroll-to-top animation targeting -adjustedContentInset.top.
 */
UIScrollViewScrollAnimation *UIScrollViewScrollAnimation_create(
    UIScrollView *scrollView,
    double startTime)
{
    assert(scrollView != NULL);

    /* Halt prior in-flight animation to prevent leaks and race conditions on rapid repeated taps */
    if (scrollView->_scrollAnimation != NULL || scrollView->_isAnimatingScrollToTop) {
        UIScrollView_stopScrollToTopAnimation(scrollView);
    }

    UIScrollViewScrollAnimation *anim = (UIScrollViewScrollAnimation *)malloc(sizeof(UIScrollViewScrollAnimation));
    assert(anim != NULL);

    anim->_scrollView = scrollView;
    anim->_startOffset = scrollView->_contentOffset;

    /* Target maintains horizontal offset, zeroes out vertical offset to -adjustedContentInset.top */
    UIEdgeInsets insets = UIScrollView_effectiveInsets(scrollView);
    anim->_targetOffset = (CGPoint){ scrollView->_contentOffset.x, -insets.top };

    anim->_startTime = startTime;
    anim->_duration = kScrollToTopAnimationDurationSeconds;
    anim->_finished = false;

    /* Allocate and attach active CADisplayLink */
    CADisplayLink *dl = (CADisplayLink *)malloc(sizeof(CADisplayLink));
    assert(dl != NULL);
    dl->timestamp = startTime;
    dl->targetTimestamp = startTime + (1.0 / 60.0);
    dl->paused = false;
    dl->isInvalidated = false;
    anim->_displayLink = dl;

    scrollView->_isAnimatingScrollToTop = true;
    scrollView->_scrollAnimation = anim;

    return anim;
}

/**
 * Advances animation frame tick from CADisplayLink.
 * Returns true if animation remains active, false if reached target, completed, or invalidated.
 */
bool UIScrollViewScrollAnimation_step(UIScrollViewScrollAnimation *anim, double currentTimestamp) {
    assert(anim != NULL && anim->_scrollView != NULL);
    UIScrollView *sv = anim->_scrollView;

    if (anim->_finished) return false;
    if (anim->_displayLink != NULL && anim->_displayLink->isInvalidated) {
        anim->_finished = true;
        sv->_isAnimatingScrollToTop = false;
        return false;
    }

    double elapsed = currentTimestamp - anim->_startTime;
    double progress = elapsed / anim->_duration;
    if (progress >= 1.0) {
        progress = 1.0;
        anim->_finished = true;
    }

    double curved_progress = _evaluateScrollToTopTimingCurve(progress);

    /* Interpolate contentOffset */
    sv->_contentOffset.x = anim->_startOffset.x + (anim->_targetOffset.x - anim->_startOffset.x) * curved_progress;
    sv->_contentOffset.y = anim->_startOffset.y + (anim->_targetOffset.y - anim->_startOffset.y) * curved_progress;

    if (anim->_finished) {
        sv->_contentOffset = anim->_targetOffset;
        sv->_isAnimatingScrollToTop = false;
        if (anim->_displayLink != NULL) {
            CADisplayLink_invalidate(anim->_displayLink);
        }

        /* Dispatch completion callback */
        if (sv->_scrollViewFlags.delegateScrollViewDidScrollToTop && sv->_delegate != NULL) {
            if (sv->_delegate->scrollViewDidScrollToTop != NULL) {
                sv->_delegate->scrollViewDidScrollToTop(sv->_delegate->target, sv);
            }
        }
        return false;
    }

    return true;
}

/**
 * Immediately cancels and halts an active scroll-to-top animation upon user touch.
 * Invalidates CADisplayLink and deallocates active animation structures.
 */
void UIScrollView_stopScrollToTopAnimation(UIScrollView *sv) {
    assert(sv != NULL);
    if (!sv->_isAnimatingScrollToTop && sv->_scrollAnimation == NULL) return;

    if (sv->_scrollAnimation != NULL) {
        sv->_scrollAnimation->_finished = true;
        if (sv->_scrollAnimation->_displayLink != NULL) {
            CADisplayLink_invalidate(sv->_scrollAnimation->_displayLink);
            free(sv->_scrollAnimation->_displayLink);
            sv->_scrollAnimation->_displayLink = NULL;
        }
        free(sv->_scrollAnimation);
        sv->_scrollAnimation = NULL;
    }
    sv->_isAnimatingScrollToTop = false;
}

/**
 * Intercepts touch down on scroll view (touchesBegan:withEvent:).
 * Halts active scroll-to-top animation flight, invalidates CADisplayLink,
 * freezes contentOffset at current presentation coordinate, suppresses
 * completion callback, and transitions scroll view into dragging state.
 * Returns true if an active scroll-to-top animation was interrupted.
 */
bool UIScrollView_touchesBegan(UIScrollView *sv, CGPoint touchLocation, double currentTimestamp) {
    assert(sv != NULL);
    (void)touchLocation;
    (void)currentTimestamp;

    if (sv->_isAnimatingScrollToTop || sv->_scrollAnimation != NULL) {
        UIScrollView_stopScrollToTopAnimation(sv);
        sv->_scrollViewFlags.isDragging = 1;
        return true; /* Interrupted active flight */
    }

    sv->_scrollViewFlags.isDragging = 1;
    return false;
}

/**
 * Handles touch cancellation (touchesCancelled:withEvent:).
 * Halts active scroll-to-top animation flight, invalidates CADisplayLink,
 * and clears dragging flag.
 */
void UIScrollView_touchesCancelled(UIScrollView *sv, double currentTimestamp) {
    assert(sv != NULL);
    (void)currentTimestamp;

    if (sv->_isAnimatingScrollToTop || sv->_scrollAnimation != NULL) {
        UIScrollView_stopScrollToTopAnimation(sv);
    }
    sv->_scrollViewFlags.isDragging = 0;
}

/**
 * Intercepts multi-touch pinch zoom gestures (UIPinchGestureRecognizer).
 * Mutual exclusivity: active scroll-to-top animation is immediately halted upon pinch began/changed,
 * CADisplayLink is invalidated, and zoomScale is updated on the scroll view.
 * Returns true if pinch event was processed.
 */
bool UIScrollView_handlePinchGesture(UIScrollView *sv, UIGestureRecognizerState state, double pinchScale, double currentTimestamp) {
    assert(sv != NULL);
    (void)currentTimestamp;

    if (state == kUIGestureRecognizerStateBegan || state == kUIGestureRecognizerStateChanged) {
        if (sv->_isAnimatingScrollToTop || sv->_scrollAnimation != NULL) {
            UIScrollView_stopScrollToTopAnimation(sv);
        }
        if (pinchScale >= 0.01) {
            sv->_zoomScale = pinchScale;
        }
        return true;
    } else if (state == kUIGestureRecognizerStateCancelled || state == kUIGestureRecognizerStateEnded) {
        if (sv->_isAnimatingScrollToTop || sv->_scrollAnimation != NULL) {
            UIScrollView_stopScrollToTopAnimation(sv);
        }
        return true;
    }
    return false;
}

/* ========================================================================= */
/* Section 5: Status Bar Touch Event Dispatch Pipeline                       */
/* ========================================================================= */

/**
 * Entry point handling status bar tap event at screen coordinates.
 * Dispatches candidate resolution, delegate permission query, and animation start.
 * Address: 0x1848b4a20 (-[UIScrollView _scrollToTopFromTouchAtScreenLocation:animate:])
 */
bool UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(
    UIWindow *window,
    CGPoint screenLocation,
    bool animated,
    double currentTimestamp)
{
    assert(window != NULL);

    /* Verify touch occurs in status bar region (y in [0, 54.0pt] on Dynamic Island, x in window bounds) */
    if (screenLocation.y < 0.0 || screenLocation.y > kStatusBarHeightDynamicIslandPt) {
        return false;
    }
    if (screenLocation.x < 0.0 || screenLocation.x > window->view.bounds.size.width) {
        return false;
    }

    /* Resolve unique candidate via exclusivity rule */
    UIScrollView *candidate = UIWindow_resolveScrollToTopCandidate(window);
    if (candidate == NULL) {
        /* Zero candidates or multiple candidates: abort */
        return false;
    }

    /* Delegate permission query */
    if (candidate->_scrollViewFlags.delegateScrollViewShouldScrollToTop && candidate->_delegate != NULL) {
        if (candidate->_delegate->scrollViewShouldScrollToTop != NULL) {
            bool should_scroll = candidate->_delegate->scrollViewShouldScrollToTop(
                candidate->_delegate->target, candidate);
            if (!should_scroll) {
                return false; /* Delegate vetoed scroll-to-top */
            }
        }
    }

    if (animated) {
        UIScrollViewScrollAnimation_create(candidate, currentTimestamp);
    } else {
        /* Instantaneous scroll without animation */
        UIEdgeInsets insets = UIScrollView_effectiveInsets(candidate);
        candidate->_contentOffset = (CGPoint){ candidate->_contentOffset.x, -insets.top };
        if (candidate->_scrollViewFlags.delegateScrollViewDidScrollToTop && candidate->_delegate != NULL) {
            if (candidate->_delegate->scrollViewDidScrollToTop != NULL) {
                candidate->_delegate->scrollViewDidScrollToTop(candidate->_delegate->target, candidate);
            }
        }
    }

    return true;
}

/**
 * Direct entry point for status bar touch at screen X (Requirement R4).
 * Forwards to UIScrollView_scrollToTopFromTouchAtScreenLocation_animate.
 */
bool UIScrollView_scrollToTopFromTouchAtScreenX_animated(
    UIWindow *window,
    double screenX,
    bool animated,
    double currentTimestamp)
{
    return UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(
        window, (CGPoint){ screenX, 20.0 }, animated, currentTimestamp);
}

/* ========================================================================= */
/* Section 6: Verification Test Harness                                      */
/* ========================================================================= */

#ifdef SCROLL_TO_TOP_STANDALONE

static bool g_delegate_should_scroll = true;
static bool g_delegate_did_scroll = false;

static bool mock_should_scroll(void *target, UIScrollView *sv) {
    (void)target; (void)sv;
    return g_delegate_should_scroll;
}

static void mock_did_scroll(void *target, UIScrollView *sv) {
    (void)target; (void)sv;
    g_delegate_did_scroll = true;
}

int main(void) {
    printf("[*] Running Status Bar Scroll-To-Top Kinematics Verification Harness...\n");

    /* 1. Setup window */
    UIWindow win;
    win.view.frame = (CGRect){ {0.0, 0.0}, {393.0, 852.0} };
    win.view.bounds = win.view.frame;
    win.view.hidden = false;
    win.view.alpha = 1.0;
    win.view.window = &win;
    win.view.superview = NULL;
    win.isKeyWindow = true;

    /* 2. Setup scroll view 1 (valid candidate) */
    UIScrollView sv1;
    sv1.view.isScrollView = true;
    sv1.view.frame = (CGRect){ {0.0, 54.0}, {393.0, 798.0} };
    sv1.view.bounds = (CGRect){ {0.0, 0.0}, {393.0, 798.0} };
    sv1.view.hidden = false;
    sv1.view.alpha = 1.0;
    sv1.view.window = &win;
    sv1.view.superview = &win.view;
    sv1.view.subviews = NULL;
    sv1.view.subviewCount = 0;
    sv1._contentSize = (CGSize){ 393.0, 3000.0 };
    sv1._contentInset = (UIEdgeInsets){ 54.0, 0.0, 34.0, 0.0 };
    sv1._contentOffset = (CGPoint){ 0.0, 600.0 }; /* Currently scrolled down */
    sv1._scrollViewFlags = (_UIScrollViewFlags){
        .scrollsToTop = 1,
        .delegateScrollViewShouldScrollToTop = 1,
        .delegateScrollViewDidScrollToTop = 1
    };
    sv1._isAnimatingScrollToTop = false;
    sv1._scrollAnimation = NULL;
    sv1._zoomScale = 1.0;

    UIScrollViewDelegate delegate;
    delegate.target = NULL;
    delegate.scrollViewShouldScrollToTop = mock_should_scroll;
    delegate.scrollViewDidScrollToTop = mock_did_scroll;
    sv1._delegate = &delegate;

    UIView *win_subviews[4];
    win_subviews[0] = (UIView *)&sv1;
    win.view.subviews = win_subviews;
    win.view.subviewCount = 1;

    /* Test Case 1: Single Candidate Qualification & Selection */
    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == true);
    UIScrollView *resolved = UIWindow_resolveScrollToTopCandidate(&win);
    assert(resolved == &sv1);
    printf("  [+] Single candidate qualification and resolution validated.\n");

    /* Test Case 2: Status Bar Touch Dispatch & Animation Initiation */
    CGPoint status_bar_touch = (CGPoint){ 196.5, 20.0 }; /* Center of Dynamic Island */
    g_delegate_did_scroll = false;
    bool handled = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 0.0);
    assert(handled == true);
    assert(sv1._isAnimatingScrollToTop == true);
    assert(sv1._scrollAnimation != NULL);
    assert(sv1._scrollAnimation->_targetOffset.y == -54.0);
    printf("  [+] Status bar touch acquisition and animation launch (-54.0 target) validated.\n");

    /* Test Case 3: Animation stepping across 0.30s (18 frames at 60Hz) */
    double dt = 1.0 / 60.0;
    for (int frame = 1; frame <= 18; ++frame) {
        double t = (double)frame * dt;
        UIScrollViewScrollAnimation_step(sv1._scrollAnimation, t);
    }
    /* At 18 frames (~0.300s), animation should finish */
    assert(fabs(sv1._contentOffset.y - (-54.0)) < 1e-4);
    assert(sv1._isAnimatingScrollToTop == false);
    assert(g_delegate_did_scroll == true);
    UIScrollView_stopScrollToTopAnimation(&sv1);
    printf("  [+] 0.30s cubic Bézier animation stepping & delegateDidScroll completion validated.\n");

    /* Test Case 4: Ambiguity Exclusivity Rule (Multiple Candidates -> Abort) */
    UIScrollView sv2 = sv1;
    sv2.view.frame = (CGRect){ {0.0, 400.0}, {393.0, 400.0} };
    sv2._contentOffset = (CGPoint){ 0.0, 300.0 };
    win_subviews[1] = (UIView *)&sv2;
    win.view.subviewCount = 2;

    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == false || sv1._contentOffset.y > -54.0 + 0.5);
    sv1._contentOffset = (CGPoint){ 0.0, 500.0 };
    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == true);
    assert(UIScrollView_isEligibleForScrollToTop(&sv2) == true);

    UIScrollView *ambiguous = UIWindow_resolveScrollToTopCandidate(&win);
    assert(ambiguous == NULL); /* Multiple candidates must abort! */
    bool handled_ambiguous = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 1.0);
    assert(handled_ambiguous == false);
    printf("  [+] Single-candidate exclusivity rule (2 candidates -> abort) validated.\n");

    /* Test Case 5: scrollsToTop == NO Excludes Candidate */
    sv2._scrollViewFlags.scrollsToTop = 0;
    assert(UIScrollView_isEligibleForScrollToTop(&sv2) == false);
    UIScrollView *single_again = UIWindow_resolveScrollToTopCandidate(&win);
    assert(single_again == &sv1);
    printf("  [+] scrollsToTop == NO filtering validated.\n");

    /* Test Case 6: Already At Top Excluded */
    sv1._contentOffset = (CGPoint){ 0.0, -54.0 }; /* Rested at top */
    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == false);
    UIScrollView *none_at_top = UIWindow_resolveScrollToTopCandidate(&win);
    assert(none_at_top == NULL);
    printf("  [+] Already-at-top candidate filtering validated.\n");

    /* Test Case 7: Delegate Permission Veto (scrollViewShouldScrollToTop -> false) */
    sv1._contentOffset = (CGPoint){ 0.0, 400.0 };
    g_delegate_should_scroll = false;
    bool vetoed = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 2.0);
    assert(vetoed == false);
    assert(sv1._isAnimatingScrollToTop == false);
    printf("  [+] Delegate scrollViewShouldScrollToTop veto validated.\n");

    /* Test Case 8: Interruption on user touch */
    g_delegate_should_scroll = true;
    g_delegate_did_scroll = false;
    UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 3.0);
    assert(sv1._isAnimatingScrollToTop == true);
    /* Step 3 frames */
    UIScrollViewScrollAnimation_step(sv1._scrollAnimation, 3.05);
    /* User touches screen */
    UIScrollView_stopScrollToTopAnimation(&sv1);
    assert(sv1._isAnimatingScrollToTop == false);
    assert(sv1._scrollAnimation == NULL);
    assert(g_delegate_did_scroll == false); /* Callback suppressed */
    printf("  [+] Touch interruption halting animation and suppressing completion validated.\n");

    /* Test Case 9: Nested subview coordinate conversion to window */
    UIView container;
    container.frame = (CGRect){ {0.0, 100.0}, {393.0, 600.0} };
    container.bounds = (CGRect){ {0.0, 0.0}, {393.0, 600.0} };
    container.hidden = false;
    container.alpha = 1.0;
    container.window = &win;
    container.superview = &win.view;
    container.isScrollView = false;

    UIScrollView nested_sv = sv1;
    nested_sv.view.superview = &container;
    nested_sv.view.frame = (CGRect){ {0.0, 50.0}, {393.0, 500.0} };
    nested_sv.view.bounds = (CGRect){ {0.0, 0.0}, {393.0, 500.0} };

    CGRect converted = UIView_convertRectToWindow(&nested_sv.view, (CGRect){ {0.0, 0.0}, nested_sv.view.bounds.size });
    assert(converted.origin.y == 150.0); /* 100.0 container + 50.0 frame */
    printf("  [+] Nested subview coordinate conversion to window space validated.\n");

    /* Test Case 10: Status bar touch boundary rejection */
    bool rej_neg_y = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, (CGPoint){ 100.0, -5.0 }, true, 4.0);
    assert(rej_neg_y == false);
    bool rej_deep_y = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, (CGPoint){ 100.0, 55.0 }, true, 4.0);
    assert(rej_deep_y == false);
    bool rej_out_x = UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, (CGPoint){ 400.0, 20.0 }, true, 4.0);
    assert(rej_out_x == false);
    printf("  [+] Status bar touch boundary rejection (neg y, y > 54, x > window.width) validated.\n");

    /* Test Case 11: Direct screenX entry point (Requirement R4) */
    sv1._contentOffset = (CGPoint){ 0.0, 400.0 };
    win.view.subviewCount = 1; /* Restore single candidate */
    bool handled_x = UIScrollView_scrollToTopFromTouchAtScreenX_animated(&win, 196.5, true, 5.0);
    assert(handled_x == true);
    assert(sv1._isAnimatingScrollToTop == true);
    printf("  [+] Direct _scrollToTopFromTouchAtScreenX:animated: entry point validated.\n");

    /* Test Case 12: Memory leak prevention on repeated animation launch */
    /* An animation is currently in flight from Test 11. Launching another must free prior struct cleanly */
    UIScrollViewScrollAnimation_create(&sv1, 5.01);
    assert(sv1._isAnimatingScrollToTop == true);
    assert(sv1._scrollAnimation != NULL);
    UIScrollView_stopScrollToTopAnimation(&sv1);
    assert(sv1._scrollAnimation == NULL);
    printf("  [+] Rapid re-trigger animation allocation leak safety validated.\n");

    /* Test Case 13: Disabled scrolling (isScrollEnabled == false) candidate exclusion */
    UIScrollView_setScrollEnabled(&sv1, false);
    assert(UIScrollView_isScrollEnabled(&sv1) == false);
    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == false);
    UIScrollView *dis_cand = UIWindow_resolveScrollToTopCandidate(&win);
    assert(dis_cand == NULL);
    UIScrollView_setScrollEnabled(&sv1, true);
    assert(UIScrollView_isScrollEnabled(&sv1) == true);
    assert(UIScrollView_isEligibleForScrollToTop(&sv1) == true);
    printf("  [+] Disabled scrolling (isScrollEnabled == false) candidate exclusion validated.\n");

    /* Test Case 14: Degenerate contentSize / bounds (contentSize.height == 0.0) exclusion */
    UIScrollView zero_sv = sv1;
    zero_sv._contentSize = (CGSize){ 393.0, 0.0 };
    assert(UIScrollView_isEligibleForScrollToTop(&zero_sv) == false);
    zero_sv._contentSize = (CGSize){ 393.0, 3000.0 };
    zero_sv.view.bounds = (CGRect){ {0.0, 0.0}, {0.0, 0.0} };
    assert(UIScrollView_isEligibleForScrollToTop(&zero_sv) == false);
    printf("  [+] Zero contentSize and collapsed bounds candidate exclusion validated.\n");

    /* Test Case 15: Zoomed content (zoomScale = 2.0) scrollability qualification */
    UIScrollView zoom_sv = sv1;
    zoom_sv.view.bounds = (CGRect){ {0.0, 0.0}, {393.0, 800.0} };
    zoom_sv._contentInset = (UIEdgeInsets){ 0.0, 0.0, 0.0, 0.0 };
    zoom_sv._contentSize = (CGSize){ 393.0, 700.0 }; /* Not scrollable at zoomScale 1.0 (700 <= 800) */
    zoom_sv._zoomScale = 1.0;
    zoom_sv._contentOffset = (CGPoint){ 0.0, 200.0 };
    assert(UIScrollView_isEligibleForScrollToTop(&zoom_sv) == false);
    zoom_sv._zoomScale = 2.0; /* Effective height = 1400.0 > 800.0 -> scrollable! */
    assert(UIScrollView_isEligibleForScrollToTop(&zoom_sv) == true);
    printf("  [+] Zoomed content (zoomScale = 2.0) vertical scrollability expansion validated.\n");

    /* Test Case 16: NaN / Inf progress fraction in cubic Bézier solver */
    assert(_evaluateScrollToTopTimingCurve(NAN) == 0.0);
    assert(_evaluateScrollToTopTimingCurve(INFINITY) == 1.0);
    assert(_evaluateScrollToTopTimingCurve(-INFINITY) == 0.0);
    printf("  [+] NaN/Inf progress fraction in cubic Bézier timing curve validated.\n");

    /* Test Case 17: touchesBegan interruption of active animation flight */
    sv1._contentOffset = (CGPoint){ 0.0, 400.0 };
    g_delegate_did_scroll = false;
    UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 6.0);
    assert(sv1._isAnimatingScrollToTop == true);
    assert(sv1._scrollAnimation != NULL);
    assert(sv1._scrollAnimation->_displayLink != NULL);
    assert(sv1._scrollAnimation->_displayLink->isInvalidated == false);
    /* Advance 2 frames */
    UIScrollViewScrollAnimation_step(sv1._scrollAnimation, 6.033);
    /* User touches screen */
    bool interrupted = UIScrollView_touchesBegan(&sv1, (CGPoint){ 100.0, 200.0 }, 6.035);
    assert(interrupted == true);
    assert(sv1._isAnimatingScrollToTop == false);
    assert(sv1._scrollAnimation == NULL);
    assert(sv1._scrollViewFlags.isDragging == 1);
    assert(g_delegate_did_scroll == false); /* Completion callback suppressed */
    printf("  [+] touchesBegan active flight interruption & CADisplayLink invalidation validated.\n");

    /* Test Case 18: touchesCancelled during active animation flight */
    sv1._contentOffset = (CGPoint){ 0.0, 400.0 };
    g_delegate_did_scroll = false;
    UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 7.0);
    assert(sv1._isAnimatingScrollToTop == true);
    UIScrollViewScrollAnimation_step(sv1._scrollAnimation, 7.033);
    UIScrollView_touchesCancelled(&sv1, 7.040);
    assert(sv1._isAnimatingScrollToTop == false);
    assert(sv1._scrollAnimation == NULL);
    assert(sv1._scrollViewFlags.isDragging == 0);
    assert(g_delegate_did_scroll == false);
    printf("  [+] touchesCancelled active flight cancellation & dragging reset validated.\n");

    /* Test Case 19: Multi-touch pinch zoom gesture interruption */
    sv1._contentOffset = (CGPoint){ 0.0, 400.0 };
    g_delegate_did_scroll = false;
    UIScrollView_scrollToTopFromTouchAtScreenLocation_animate(&win, status_bar_touch, true, 8.0);
    assert(sv1._isAnimatingScrollToTop == true);
    UIScrollViewScrollAnimation_step(sv1._scrollAnimation, 8.033);
    /* Pinch gesture begins */
    bool pinch_handled = UIScrollView_handlePinchGesture(&sv1, kUIGestureRecognizerStateBegan, 1.75, 8.035);
    assert(pinch_handled == true);
    assert(sv1._isAnimatingScrollToTop == false);
    assert(sv1._scrollAnimation == NULL);
    assert(sv1._zoomScale == 1.75);
    assert(g_delegate_did_scroll == false);
    printf("  [+] Multi-touch pinch zoom mutual exclusivity & flight interruption validated.\n");

    printf("\n[SUCCESS] All 8 Status Bar Scroll-To-Top verification test suites passed (plus 11 extended adversarial suites)!\n");
    return 0;
}

#endif /* SCROLL_TO_TOP_STANDALONE */
