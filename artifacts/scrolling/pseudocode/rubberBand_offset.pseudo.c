/**
 * UIKitCore.framework - UIScrollView Rubber-Banding, Boundary Resistance & Bounce Restitution
 * Classes: UIScrollView, _UIScrollViewRubberBandPolicy, _UIScrollViewSpringAnimation
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 *
 * Implements:
 *   - -[UIScrollView _rubberBandOffsetForOffset:maxOffset:minOffset:range:outside:legitimateOffset:] @ 0x1848b7100 / 0x184ae00c0
 *   - -[UIScrollView _rubberBandOffsetWithoutDecorationForOffset:maxOffset:minOffset:range:outside:] @ 0x1848b7180 / 0x184b1e5f4
 *   - -[UIScrollView _offsetForRubberBandOffset:maxOffset:minOffset:range:] @ 0x1848b71d0 (Exact Inverse)
 *   - -[UIScrollView _minimumContentOffset] @ 0x1848b7f40
 *   - -[UIScrollView _maximumContentOffset] @ 0x1848b7f60
 *   - -[UIScrollView _clampedContentOffsetForContentOffset:] @ 0x1848b7fa0
 *   - -[UIScrollView _adjustedContentOffsetIfNecessary] @ 0x1848b7fc0
 *   - -[UIScrollView _adjustedContentInset] @ 0x1848b7800
 *   - -[UIScrollView _rubberBandContentOffsetForOffset:velocity:] @ 0x1848b8000
 *   - -[UIScrollView _zoomRubberBandScaleForScale:] @ 0x1848b7ba0
 *   - Touch-up overscroll bounce-back spring handoff (x0 != 0, v0 = release velocity)
 *   - Ballistic collision momentum handoff to damped harmonic oscillator spring (x0 = 0, v0 = v_impact)
 *
 * Mathematical Proof:
 *   Forward: f(x) = (1.0 - 1.0 / ((|x| * c / d) + 1.0)) * d * sgn(x)
 *   Inverse: f^-1(y) = (|y| * d) / (c * (d - |y|)) * sgn(y)
 *   Zoom:    s_rubber = s_lim +/- ln(1 + |delta| / s_lim) * c_zoom * s_lim
 *   Constants: c = 0.55 (IEEE 754: 0x3fe199999999999a @ 0x1865166d0)
 *              c_zoom = 0.25 (Logarithmic zoom resistance coefficient)
 *              d = bounds.size.width / bounds.size.height (viewport dimension)
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

/* Standard UIKit / CoreGraphics geometric primitives */
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

/* Content Inset Adjustment Behaviors */
typedef enum UIScrollViewContentInsetAdjustmentBehavior {
    UIScrollViewContentInsetAdjustmentAutomatic = 0,
    UIScrollViewContentInsetAdjustmentScrollableAxes = 1,
    UIScrollViewContentInsetAdjustmentNever = 2,
    UIScrollViewContentInsetAdjustmentAlways = 3
} UIScrollViewContentInsetAdjustmentBehavior;

/* Bitfield flags for UIScrollView (_scrollViewFlags at offset +0xd0) */
typedef struct _UIScrollViewFlags {
    unsigned int isDragging : 1;                         /* bit 0 */
    unsigned int isDecelerating : 1;                     /* bit 1 */
    unsigned int bounces : 1;                            /* bit 2 */
    unsigned int alwaysBounceVertical : 1;               /* bit 3 */
    unsigned int alwaysBounceHorizontal : 1;             /* bit 4 */
    unsigned int bouncesZoom : 1;                        /* bit 5 */
    unsigned int directionalLockEnabled : 1;             /* bit 6 */
    unsigned int pagingEnabled : 1;                      /* bit 7 */
    unsigned int delaysContentTouches : 1;               /* bit 8 */
    unsigned int canCancelContentTouches : 1;            /* bit 9 */
    unsigned int delegateScrollViewDidScroll : 1;        /* bit 10 */
    unsigned int delegateScrollViewWillBeginDragging : 1;/* bit 11 */
    unsigned int delegateScrollViewDidEndDragging : 1;   /* bit 12 */
    unsigned int delegateScrollViewDidEndDecelerating : 1;/* bit 13 */
} _UIScrollViewFlags;

/* Forward declarations */
typedef struct UIScrollView UIScrollView;
typedef struct _UIScrollViewSpringAnimation _UIScrollViewSpringAnimation;

/* Damped harmonic oscillator boundary restitution spring layout */
struct _UIScrollViewSpringAnimation {
    void *isa;
    UIScrollView *scrollView;
    double mass;                     /* m = 1.0 kg (0x3ff0000000000000) */
    double stiffness;                /* k = 100.0 N/m (0x4059000000000000) */
    double damping;                  /* c = 18.0 N*s/m (0x4032000000000000) */
    double dampingRatio;             /* zeta = 0.90 (0x3feccccccccccccd) */
    double naturalFrequency;         /* omega_n = 10.0 rad/s */
    double dampedFrequency;          /* omega_d = 4.358898943540674 rad/s */
    double epsilonPosition;          /* 0.5 pt settling threshold */
    double epsilonVelocity;          /* 0.5 pt/s settling threshold */
    CGPoint initialDisplacement;     /* x0 relative to equilibrium boundary */
    CGPoint initialVelocity;         /* v0 residual impact or touch release velocity */
    CGPoint equilibriumOffset;       /* resting boundary contentOffset */
    double startTime;
};

/* UIScrollView internal layout reconstruction */
struct UIScrollView {
    void *isa;                                           /* +0x000 */
    _UIScrollViewFlags _scrollViewFlags;                 /* +0xd0 */
    CGPoint _contentOffset;                              /* +0x100 */
    CGSize _contentSize;                                 /* +0x110 */
    void *_delegate;                                     /* +0x118 */
    UIEdgeInsets _contentInset;                          /* +0x120 */
    CGRect _bounds;                                      /* +0x140 */
    UIEdgeInsets _safeAreaInsets;                        /* +0x160 */
    UIScrollViewContentInsetAdjustmentBehavior _contentInsetAdjustmentBehavior; /* +0x180 */
    _UIScrollViewSpringAnimation *_springAnimation;      /* +0x188 */
    double _zoomScale;                                   /* +0x190 */
    double _minimumZoomScale;                            /* +0x198 */
    double _maximumZoomScale;                            /* +0x1a0 */
    bool _refreshControlActive;                          /* UIRefreshControl pull-to-refresh state */
    double _refreshControlHeight;                        /* Typically 60.0 pt */
};

/* Authoritative IEEE 754 constants from UIKitCore binary (__const section @ 0x1865166d0) */
static const double kRubberBandCoefficient = 0.55;       /* 0x3fe199999999999a */
static const double kRubberBandMinDimension = 1.0;       /* Minimum dimension divisor guard */
static const double kZoomRubberBandCoefficient = 0.25;   /* Logarithmic zoom resistance coefficient */
static const double kSpringMass = 1.0;                   /* 0x3ff0000000000000 */
static const double kSpringStiffnessDefault = 100.0;     /* 0x4059000000000000 */
static const double kSpringStiffnessPull = 180.0;        /* 0x4066800000000000 */
static const double kSpringDampingDefault = 18.0;        /* 0x4032000000000000 */
static const double kSpringDampingPull = 24.14953415699773; /* 0x403826477d94cf34: 2*0.90*sqrt(180) */
static const double kSpringDampingRatio = 0.90;          /* 0x3feccccccccccccd */
static const double kSpringNaturalFrequency = 10.0;      /* 0x4024000000000000 */
static const double kSpringNaturalFrequencyPull = 13.416407864998739; /* 0x402ad533f815d2a6: sqrt(180) */
static const double kSpringDampedFrequency = 4.358898943540674; /* 0x40116f8334644df9 */
static const double kSpringDampedFrequencyPull = 5.848076606883688; /* 0x4017646ec7b25866 */
static const double kSpringSettleThresholdPos = 0.5;     /* 0.5 pt */
static const double kSpringSettleThresholdVel = 0.5;     /* 0.5 pt/s */

/* ========================================================================= */
/* 1. Core Forward & Inverse Rubber-Banding Mathematical Functions           */
/* ========================================================================= */

/**
 * Pure 1D scalar forward rubber-band resistance curve.
 * Maps unconstrained drag overscroll displacement x past boundary and viewport
 * dimension d to constrained visual offset x_rubber.
 *
 * Exact formula:
 *   f(x) = (1.0 - 1.0 / ((|x| * c / d) + 1.0)) * d * sgn(x)
 *
 * Equivalent rational form:
 *   f(x) = (x * d * c) / (d + c * |x|)
 *
 * Hardware assembly sequence from 0x184ae00dc:
 *   fsub d0, d0, d10      ; delta = offset - bound (x)
 *   fdiv d0, d0, d1        ; x / d
 *   adrp x8, 0x186516000
 *   ldr  d2, [x8, #0x6d0]  ; load c = 0.55
 *   fmul d0, d0, d2        ; (x / d) * c
 *   fmov d2, #1.00000000
 *   fadd d0, d0, d2        ; (x / d) * c + 1.0
 *   fdiv d0, d2, d0        ; 1.0 / ((x / d) * c + 1.0)
 *   fsub d0, d2, d0        ; 1.0 - 1.0 / ((x / d) * c + 1.0)
 *   fmul d0, d1, d0        ; (1.0 - 1.0 / ((x * c / d) + 1.0)) * d
 */
double _scrollViewRubberBandValue(double x, double dimension, double coefficient) {
    if (fabs(x) < 1e-9) {
        return 0.0;
    }
    double d = (dimension > kRubberBandMinDimension) ? dimension : kRubberBandMinDimension;
    double c = (coefficient > 0.0) ? coefficient : kRubberBandCoefficient;
    
    double absX = fabs(x);
    double ratio = (absX * c) / d;
    double rubber = (1.0 - (1.0 / (ratio + 1.0))) * d;
    
    return (x < 0.0) ? -rubber : rubber;
}

/**
 * Pure 1D scalar exact analytical inverse rubber-band transformation.
 * Maps visual rubber-banded overscroll offset y back to unconstrained touch
 * displacement x:
 *
 * Algebraic Derivation:
 *   y = (1 - 1 / (x * c / d + 1)) * d
 *   y / d = 1 - 1 / (x * c / d + 1)
 *   1 / (x * c / d + 1) = 1 - y / d = (d - y) / d
 *   x * c / d + 1 = d / (d - y)
 *   x * c / d = d / (d - y) - 1 = y / (d - y)
 *   x = (y * d) / (c * (d - y))
 *
 * Domain restriction: |y| < d (asymptote at viewport dimension d).
 * Clamped strictly below asymptote to prevent division by zero or negative divergence.
 */
double _scrollViewInverseRubberBandValue(double y, double dimension, double coefficient) {
    if (fabs(y) < 1e-9) {
        return 0.0;
    }
    double d = (dimension > kRubberBandMinDimension) ? dimension : kRubberBandMinDimension;
    double c = (coefficient > 0.0) ? coefficient : kRubberBandCoefficient;
    
    double absY = fabs(y);
    /* Clamp strictly below asymptote d to prevent division by zero or negative divergence */
    if (absY >= d * 0.9999) {
        absY = d * 0.9999;
    }
    
    double unconstrained = (absY * d) / (c * (d - absY));
    return (y < 0.0) ? -unconstrained : unconstrained;
}

/* ========================================================================= */
/* 2. Boundary and Content Inset Geometry Computation                        */
/* ========================================================================= */

/**
 * Reconstructs -[UIScrollView _adjustedContentInset] @ 0x1848b7800
 * Evaluates safe area insets modulation governed by contentInsetAdjustmentBehavior.
 */
UIEdgeInsets UIScrollView_adjustedContentInset(UIScrollView *self) {
    if (!self) {
        return (UIEdgeInsets){0.0, 0.0, 0.0, 0.0};
    }
    UIEdgeInsets adjusted = self->_contentInset;
    
    switch (self->_contentInsetAdjustmentBehavior) {
        case UIScrollViewContentInsetAdjustmentNever:
            /* Never add safeAreaInsets */
            break;
            
        case UIScrollViewContentInsetAdjustmentAlways:
            /* Always add safeAreaInsets unconditionally */
            adjusted.top += self->_safeAreaInsets.top;
            adjusted.left += self->_safeAreaInsets.left;
            adjusted.bottom += self->_safeAreaInsets.bottom;
            adjusted.right += self->_safeAreaInsets.right;
            break;
            
        case UIScrollViewContentInsetAdjustmentScrollableAxes: {
            /* Only add along axes where content overflows or alwaysBounce is enabled */
            bool horizScrollable = (self->_contentSize.width > self->_bounds.size.width) ||
                                   self->_scrollViewFlags.alwaysBounceHorizontal;
            bool vertScrollable = (self->_contentSize.height > self->_bounds.size.height) ||
                                  self->_scrollViewFlags.alwaysBounceVertical;
            
            if (horizScrollable) {
                adjusted.left += self->_safeAreaInsets.left;
                adjusted.right += self->_safeAreaInsets.right;
            }
            if (vertScrollable) {
                adjusted.top += self->_safeAreaInsets.top;
                adjusted.bottom += self->_safeAreaInsets.bottom;
            }
            break;
        }
            
        case UIScrollViewContentInsetAdjustmentAutomatic:
        default: {
            /* Default: Include vertical and horizontal safeAreaInsets if view can scroll or is in container */
            adjusted.top += self->_safeAreaInsets.top;
            adjusted.left += self->_safeAreaInsets.left;
            adjusted.bottom += self->_safeAreaInsets.bottom;
            adjusted.right += self->_safeAreaInsets.right;
            break;
        }
    }
    
    return adjusted;
}

/**
 * Reconstructs -[UIScrollView _minimumContentOffset] @ 0x1848b7f40
 * Minimum valid contentOffset equals negative adjusted content inset origin.
 * If UIRefreshControl is pinned, minOffset.y shifts downward by refreshControlHeight.
 */
CGPoint UIScrollView_minimumContentOffset(UIScrollView *self) {
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }
    UIEdgeInsets insets = UIScrollView_adjustedContentInset(self);
    CGPoint minOffset;
    minOffset.x = -insets.left;
    minOffset.y = -insets.top;
    
    if (self->_refreshControlActive) {
        minOffset.y -= (self->_refreshControlHeight > 0.0) ? self->_refreshControlHeight : 60.0;
    }
    
    return minOffset;
}

/**
 * Reconstructs -[UIScrollView _maximumContentOffset] @ 0x1848b7f60
 * Maximum valid contentOffset is derived from contentSize, bounds.size, and insets.
 * If content is smaller than viewport, maxOffset is clamped to minOffset.
 * If viewport bounds are zero or negative, collapses directly to minOffset.
 */
CGPoint UIScrollView_maximumContentOffset(UIScrollView *self) {
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }
    CGPoint minOffset = UIScrollView_minimumContentOffset(self);
    if (self->_bounds.size.width <= 0.0 || self->_bounds.size.height <= 0.0) {
        return minOffset;
    }
    UIEdgeInsets insets = UIScrollView_adjustedContentInset(self);
    CGPoint maxOffset;
    
    double effectiveWidth = self->_contentSize.width + insets.right - self->_bounds.size.width;
    double effectiveHeight = self->_contentSize.height + insets.bottom - self->_bounds.size.height;
    
    maxOffset.x = (effectiveWidth > minOffset.x) ? effectiveWidth : minOffset.x;
    maxOffset.y = (effectiveHeight > minOffset.y) ? effectiveHeight : minOffset.y;
    
    return maxOffset;
}

/**
 * Reconstructs -[UIScrollView _clampedContentOffsetForContentOffset:] @ 0x1848b7fa0
 * Strictly clamps proposed offset within [_minimumContentOffset, _maximumContentOffset].
 */
CGPoint UIScrollView_clampedContentOffsetForContentOffset(UIScrollView *self, CGPoint proposedOffset) {
    if (!self) {
        return proposedOffset;
    }
    CGPoint minOffset = UIScrollView_minimumContentOffset(self);
    CGPoint maxOffset = UIScrollView_maximumContentOffset(self);
    
    CGPoint clamped;
    if (proposedOffset.x < minOffset.x) {
        clamped.x = minOffset.x;
    } else if (proposedOffset.x > maxOffset.x) {
        clamped.x = maxOffset.x;
    } else {
        clamped.x = proposedOffset.x;
    }
    
    if (proposedOffset.y < minOffset.y) {
        clamped.y = minOffset.y;
    } else if (proposedOffset.y > maxOffset.y) {
        clamped.y = maxOffset.y;
    } else {
        clamped.y = proposedOffset.y;
    }
    
    return clamped;
}

/**
 * Reconstructs -[UIScrollView _adjustedContentOffsetIfNecessary] @ 0x1848b7fc0
 * Adjusts and clamps current contentOffset during layout mutations (e.g. bounds resize,
 * contentSize change, insets update). If view is actively tracking or decelerating,
 * active overscroll is preserved; otherwise, contentOffset is clamped to valid bounds.
 */
CGPoint UIScrollView_adjustedContentOffsetIfNecessary(UIScrollView *self) {
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }
    if (self->_scrollViewFlags.isDragging || self->_scrollViewFlags.isDecelerating) {
        /* Preserve current offset during active user touch tracking or ballistic deceleration */
        return self->_contentOffset;
    }
    
    CGPoint clamped = UIScrollView_clampedContentOffsetForContentOffset(self, self->_contentOffset);
    self->_contentOffset = clamped;
    return clamped;
}

/* ========================================================================= */
/* 3. Drag Overscroll Resistance & Policy Gating Routines                    */
/* ========================================================================= */

/**
 * Checks whether vertical bounce is permitted for current scroll view layout.
 */
bool UIScrollView_canBounceVertical(UIScrollView *self) {
    if (!self || self->_bounds.size.height <= 0.0) {
        return false;
    }
    if (!self->_scrollViewFlags.bounces) {
        return false;
    }
    if (self->_scrollViewFlags.alwaysBounceVertical || self->_refreshControlActive) {
        return true;
    }
    UIEdgeInsets insets = UIScrollView_adjustedContentInset(self);
    double scrollableHeight = self->_contentSize.height + insets.top + insets.bottom;
    return scrollableHeight > self->_bounds.size.height;
}

/**
 * Checks whether horizontal bounce is permitted for current scroll view layout.
 */
bool UIScrollView_canBounceHorizontal(UIScrollView *self) {
    if (!self || self->_bounds.size.width <= 0.0) {
        return false;
    }
    if (!self->_scrollViewFlags.bounces) {
        return false;
    }
    if (self->_scrollViewFlags.alwaysBounceHorizontal) {
        return true;
    }
    UIEdgeInsets insets = UIScrollView_adjustedContentInset(self);
    double scrollableWidth = self->_contentSize.width + insets.left + insets.right;
    return scrollableWidth > self->_bounds.size.width;
}

/**
 * Reconstructs -[UIScrollView _rubberBandOffsetForOffset:maxOffset:minOffset:range:outside:legitimateOffset:]
 * VM Address: 0x1848b7100 / 0x184ae00c0
 *
 * Parameters:
 *   offset: Proposed unconstrained 1D coordinate (contentOffset.x or contentOffset.y)
 *   maxOffset: Maximum allowable boundary offset
 *   minOffset: Minimum allowable boundary offset
 *   range: Reference viewport dimension d (bounds.size.width or bounds.size.height)
 *   outside: Out-parameter set to true if offset exceeds boundaries
 *   legitimateOffset: Out-parameter set to the clamped valid in-bounds offset
 */
double UIScrollView_rubberBandOffsetForOffset(UIScrollView *self,
                                              double offset,
                                              double maxOffset,
                                              double minOffset,
                                              double range,
                                              bool *outside,
                                              double *legitimateOffset) {
    if (!self) {
        if (outside) *outside = false;
        if (legitimateOffset) *legitimateOffset = offset;
        return offset;
    }
    if (offset < minOffset) {
        if (outside) *outside = true;
        if (legitimateOffset) *legitimateOffset = minOffset;
        
        if (!self->_scrollViewFlags.bounces) {
            return minOffset;
        }
        
        double delta = offset - minOffset; /* delta is negative */
        double rubber = _scrollViewRubberBandValue(delta, range, kRubberBandCoefficient);
        return minOffset + rubber;
    } else if (offset > maxOffset) {
        if (outside) *outside = true;
        if (legitimateOffset) *legitimateOffset = maxOffset;
        
        if (!self->_scrollViewFlags.bounces) {
            return maxOffset;
        }
        
        double delta = offset - maxOffset; /* delta is positive */
        double rubber = _scrollViewRubberBandValue(delta, range, kRubberBandCoefficient);
        return maxOffset + rubber;
    } else {
        if (outside) *outside = false;
        if (legitimateOffset) *legitimateOffset = offset;
        return offset;
    }
}

/**
 * Reconstructs -[UIScrollView _rubberBandOffsetWithoutDecorationForOffset:maxOffset:minOffset:range:outside:]
 * VM Address: 0x1848b7180 / 0x184b1e5f4
 * Evaluates raw rubber-band offset along a 1D axis without calculating or modifying legitimate in-bounds offset.
 */
double UIScrollView_rubberBandOffsetWithoutDecorationForOffset(UIScrollView *self,
                                                               double offset,
                                                               double maxOffset,
                                                               double minOffset,
                                                               double range,
                                                               bool *outside) {
    return UIScrollView_rubberBandOffsetForOffset(self, offset, maxOffset, minOffset, range, outside, NULL);
}

/**
 * Reconstructs -[UIScrollView _offsetForRubberBandOffset:maxOffset:minOffset:range:]
 * VM Address: 0x1848b71d0
 * Inverse mapping deriving unconstrained drag touch position from rubber-banded offset.
 */
double UIScrollView_offsetForRubberBandOffset(UIScrollView *self,
                                              double rubberOffset,
                                              double maxOffset,
                                              double minOffset,
                                              double range) {
    (void)self;
    if (maxOffset < minOffset) {
        maxOffset = minOffset;
    }
    if (rubberOffset < minOffset) {
        double rubberDelta = rubberOffset - minOffset;
        double unconstrainedDelta = _scrollViewInverseRubberBandValue(rubberDelta, range, kRubberBandCoefficient);
        return minOffset + unconstrainedDelta;
    } else if (rubberOffset > maxOffset) {
        double rubberDelta = rubberOffset - maxOffset;
        double unconstrainedDelta = _scrollViewInverseRubberBandValue(rubberDelta, range, kRubberBandCoefficient);
        return maxOffset + unconstrainedDelta;
    } else {
        return rubberOffset;
    }
}

/**
 * Reconstructs 2D coordinate transformation:
 * -[UIScrollView _rubberBandContentOffsetForOffset:velocity:] @ 0x1848b8000
 * Evaluates horizontal and vertical axes independently, enforcing axis-specific
 * bounce gating policies (alwaysBounceVertical, alwaysBounceHorizontal, bounces).
 */
CGPoint UIScrollView_rubberBandContentOffsetForOffset(UIScrollView *self, CGPoint unconstrainedOffset, CGPoint velocity) {
    (void)velocity;
    if (!self) {
        return unconstrainedOffset;
    }
    CGPoint minOffset = UIScrollView_minimumContentOffset(self);
    CGPoint maxOffset = UIScrollView_maximumContentOffset(self);
    
    CGPoint result;
    bool outsideX = false, outsideY = false;
    double legitX = 0.0, legitY = 0.0;
    
    bool canBounceX = UIScrollView_canBounceHorizontal(self);
    bool canBounceY = UIScrollView_canBounceVertical(self);
    
    if (canBounceX) {
        result.x = UIScrollView_rubberBandOffsetForOffset(self, unconstrainedOffset.x, maxOffset.x, minOffset.x,
                                                          self->_bounds.size.width, &outsideX, &legitX);
    } else {
        /* Pinned to valid bounds along horizontal axis */
        result.x = (unconstrainedOffset.x < minOffset.x) ? minOffset.x :
                   (unconstrainedOffset.x > maxOffset.x) ? maxOffset.x : unconstrainedOffset.x;
        outsideX = (unconstrainedOffset.x < minOffset.x || unconstrainedOffset.x > maxOffset.x);
        legitX = result.x;
    }
    
    if (canBounceY) {
        result.y = UIScrollView_rubberBandOffsetForOffset(self, unconstrainedOffset.y, maxOffset.y, minOffset.y,
                                                          self->_bounds.size.height, &outsideY, &legitY);
    } else {
        /* Pinned to valid bounds along vertical axis */
        result.y = (unconstrainedOffset.y < minOffset.y) ? minOffset.y :
                   (unconstrainedOffset.y > maxOffset.y) ? maxOffset.y : unconstrainedOffset.y;
        outsideY = (unconstrainedOffset.y < minOffset.y || unconstrainedOffset.y > maxOffset.y);
        legitY = result.y;
    }
    
    return result;
}

/**
 * Reconstructs -[UIScrollView _zoomRubberBandScaleForScale:] @ 0x1848b7ba0
 * Maps unconstrained zoom scale outside [minimumZoomScale, maximumZoomScale]
 * to rubber-banded scale factor using logarithmic damping (c_zoom = 0.25).
 */
double UIScrollView_zoomRubberBandScaleForScale(UIScrollView *self, double proposedScale) {
    if (isnan(proposedScale) || isinf(proposedScale)) {
        if (!self) return 1.0;
        return (self->_minimumZoomScale > 0.0) ? self->_minimumZoomScale : 1.0;
    }
    if (!self) {
        return (proposedScale > 0.0) ? proposedScale : 1.0;
    }
    double minScale = (self->_minimumZoomScale > 0.0) ? self->_minimumZoomScale : 1.0;
    double maxScale = (self->_maximumZoomScale >= minScale) ? self->_maximumZoomScale : minScale;
    
    if (proposedScale < minScale) {
        if (!self->_scrollViewFlags.bouncesZoom) {
            return minScale;
        }
        /* Clamp negative/degenerate proposed scale to 0.0 to prevent inverted scale matrix */
        double clampedScale = (proposedScale < 0.0) ? 0.0 : proposedScale;
        double delta = (minScale - clampedScale) / minScale;
        double damped = log(1.0 + delta) * kZoomRubberBandCoefficient * minScale;
        double result = minScale - damped;
        /* Enforce strictly positive lower bound: minScale * (1 - ln(2)*0.25) ~ 0.8267 * minScale */
        double minAllowed = minScale * (1.0 - log(2.0) * kZoomRubberBandCoefficient);
        return (result < minAllowed) ? minAllowed : result;
    } else if (proposedScale > maxScale) {
        if (!self->_scrollViewFlags.bouncesZoom) {
            return maxScale;
        }
        double delta = (proposedScale - maxScale) / maxScale;
        double damped = log(1.0 + delta) * kZoomRubberBandCoefficient * maxScale;
        return maxScale + damped;
    } else {
        return proposedScale;
    }
}

/* ========================================================================= */
/* 4. Ballistic Boundary Impact & Momentum Spring Handoff                     */
/* ========================================================================= */

/**
 * Handles boundary collision during inertial deceleration stepping.
 * When ballistic trajectory hits a boundary:
 * If bouncing is prohibited along an axis, collision is inelastic: offset is pinned and velocity is zeroed.
 * If bouncing is permitted, deceleration animation halts, content offset is pinned, and residual velocity
 * is transferred into _UIScrollViewSpringAnimation (x0 = 0.0, v0 = v_boundary).
 */
void UIScrollView_handleBoundaryCollision(UIScrollView *self,
                                          CGPoint currentOffset,
                                          CGPoint nextOffset,
                                          CGPoint currentVelocity,
                                          double dt,
                                          double decelerationRate) {
    if (!self) {
        return;
    }
    CGPoint minOffset = UIScrollView_minimumContentOffset(self);
    CGPoint maxOffset = UIScrollView_maximumContentOffset(self);
    
    bool breachedX = false, breachedY = false;
    double boundaryX = currentOffset.x, boundaryY = currentOffset.y;
    double residualVx = 0.0, residualVy = 0.0;
    
    /* Horizontal collision check: detects boundary crossing or ongoing outward motion beyond boundary */
    if (nextOffset.x < minOffset.x && (currentVelocity.x < 0.0 || currentOffset.x >= minOffset.x)) {
        breachedX = true;
        boundaryX = minOffset.x;
        double denom = nextOffset.x - currentOffset.x;
        double fraction = (fabs(denom) > 1e-9) ? (minOffset.x - currentOffset.x) / denom : 0.0;
        fraction = (fraction < 0.0) ? 0.0 : (fraction > 1.0) ? 1.0 : fraction;
        residualVx = currentVelocity.x * pow(decelerationRate, 1000.0 * fraction * dt);
    } else if (nextOffset.x > maxOffset.x && (currentVelocity.x > 0.0 || currentOffset.x <= maxOffset.x)) {
        breachedX = true;
        boundaryX = maxOffset.x;
        double denom = nextOffset.x - currentOffset.x;
        double fraction = (fabs(denom) > 1e-9) ? (maxOffset.x - currentOffset.x) / denom : 0.0;
        fraction = (fraction < 0.0) ? 0.0 : (fraction > 1.0) ? 1.0 : fraction;
        residualVx = currentVelocity.x * pow(decelerationRate, 1000.0 * fraction * dt);
    }
    
    /* Vertical collision check: detects boundary crossing or ongoing outward motion beyond boundary */
    if (nextOffset.y < minOffset.y && (currentVelocity.y < 0.0 || currentOffset.y >= minOffset.y)) {
        breachedY = true;
        boundaryY = minOffset.y;
        double denom = nextOffset.y - currentOffset.y;
        double fraction = (fabs(denom) > 1e-9) ? (minOffset.y - currentOffset.y) / denom : 0.0;
        fraction = (fraction < 0.0) ? 0.0 : (fraction > 1.0) ? 1.0 : fraction;
        residualVy = currentVelocity.y * pow(decelerationRate, 1000.0 * fraction * dt);
    } else if (nextOffset.y > maxOffset.y && (currentVelocity.y > 0.0 || currentOffset.y <= maxOffset.y)) {
        breachedY = true;
        boundaryY = maxOffset.y;
        double denom = nextOffset.y - currentOffset.y;
        double fraction = (fabs(denom) > 1e-9) ? (maxOffset.y - currentOffset.y) / denom : 0.0;
        fraction = (fraction < 0.0) ? 0.0 : (fraction > 1.0) ? 1.0 : fraction;
        residualVy = currentVelocity.y * pow(decelerationRate, 1000.0 * fraction * dt);
    }
    
    if (!breachedX && !breachedY) {
        return; /* No boundary breach */
    }
    
    bool canBounceX = UIScrollView_canBounceHorizontal(self);
    bool canBounceY = UIScrollView_canBounceVertical(self);
    
    /* Check for axis where bounce is disabled */
    if ((breachedX && !canBounceX) || (breachedY && !canBounceY)) {
        if (breachedX && !canBounceX) {
            self->_contentOffset.x = boundaryX;
            residualVx = 0.0;
        }
        if (breachedY && !canBounceY) {
            self->_contentOffset.y = boundaryY;
            residualVy = 0.0;
        }
        
        bool xSpring = breachedX && canBounceX;
        bool ySpring = breachedY && canBounceY;
        
        if (!xSpring && !ySpring) {
            /* Neither breached axis allows bounce */
            if (!breachedX) {
                self->_contentOffset.x = nextOffset.x;
            }
            if (!breachedY) {
                self->_contentOffset.y = nextOffset.y;
            }
            
            /* If an unbreached axis has residual velocity, deceleration continues */
            bool unbreachedMotion = (!breachedX && fabs(currentVelocity.x) > 10.0) ||
                                    (!breachedY && fabs(currentVelocity.y) > 10.0);
            self->_scrollViewFlags.isDecelerating = unbreachedMotion ? 1 : 0;
            return;
        }
    }
    
    /* Launch _UIScrollViewSpringAnimation for axes allowing bounce */
    if (!self->_springAnimation) {
        self->_springAnimation = (_UIScrollViewSpringAnimation *)malloc(sizeof(_UIScrollViewSpringAnimation));
    }
    
    _UIScrollViewSpringAnimation *spring = self->_springAnimation;
    spring->scrollView = self;
    spring->mass = kSpringMass;
    if (self->_refreshControlActive) {
        spring->stiffness = kSpringStiffnessPull;
        spring->damping = kSpringDampingPull;
        spring->dampingRatio = kSpringDampingRatio;
        spring->naturalFrequency = kSpringNaturalFrequencyPull;
        spring->dampedFrequency = kSpringDampedFrequencyPull;
    } else {
        spring->stiffness = kSpringStiffnessDefault;
        spring->damping = kSpringDampingDefault;
        spring->dampingRatio = kSpringDampingRatio;
        spring->naturalFrequency = kSpringNaturalFrequency;
        spring->dampedFrequency = kSpringDampedFrequency;
    }
    spring->epsilonPosition = kSpringSettleThresholdPos;
    spring->epsilonVelocity = kSpringSettleThresholdVel;
    
    /* Pin to collision boundary for breached axes; preserve current step for unbreached axes */
    self->_contentOffset.x = breachedX ? boundaryX : nextOffset.x;
    self->_contentOffset.y = breachedY ? boundaryY : nextOffset.y;
    
    spring->equilibriumOffset.x = breachedX ? boundaryX : nextOffset.x;
    spring->equilibriumOffset.y = breachedY ? boundaryY : nextOffset.y;
    
    /* Displacement relative to equilibrium is initially 0.0 */
    spring->initialDisplacement.x = 0.0;
    spring->initialDisplacement.y = 0.0;
    
    /* Residual velocity is transferred into spring kinetic energy */
    spring->initialVelocity.x = (breachedX && canBounceX) ? residualVx : 0.0;
    spring->initialVelocity.y = (breachedY && canBounceY) ? residualVy : 0.0;
    spring->startTime = 0.0;
    
    /* Mark decelerating */
    self->_scrollViewFlags.isDecelerating = 1;
}

/* ========================================================================= */
/* 5. Touch Release Overscroll Restitution (x0 != 0)                         */
/* ========================================================================= */

/**
 * Reconstructs touch-up / drag-end overscroll restitution:
 * -[UIScrollView _scrollViewDidEndDraggingWithDeceleration:velocity:]
 * When user releases finger while overscrolled, launches _UIScrollViewSpringAnimation
 * with initial displacement x0 = currentOffset - targetBoundary and initial velocity v0.
 * Strictly respects axis-specific bounce permissions (canBounceHorizontal / canBounceVertical).
 */
void UIScrollView_handleTouchUp(UIScrollView *self, CGPoint releaseVelocity) {
    if (!self) {
        return;
    }
    self->_scrollViewFlags.isDragging = 0;
    
    CGPoint minOffset = UIScrollView_minimumContentOffset(self);
    CGPoint maxOffset = UIScrollView_maximumContentOffset(self);
    
    bool overscrolledX = false, overscrolledY = false;
    double targetX = self->_contentOffset.x;
    double targetY = self->_contentOffset.y;
    double dispX = 0.0, dispY = 0.0;
    
    if (self->_contentOffset.x < minOffset.x) {
        overscrolledX = true;
        targetX = minOffset.x;
        dispX = self->_contentOffset.x - minOffset.x;
    } else if (self->_contentOffset.x > maxOffset.x) {
        overscrolledX = true;
        targetX = maxOffset.x;
        dispX = self->_contentOffset.x - maxOffset.x;
    }
    
    if (self->_contentOffset.y < minOffset.y) {
        overscrolledY = true;
        targetY = minOffset.y;
        dispY = self->_contentOffset.y - minOffset.y;
    } else if (self->_contentOffset.y > maxOffset.y) {
        overscrolledY = true;
        targetY = maxOffset.y;
        dispY = self->_contentOffset.y - maxOffset.y;
    }
    
    if (!overscrolledX && !overscrolledY) {
        /* In-bounds: let normal deceleration proceed if velocity is non-zero */
        if (fabs(releaseVelocity.x) > 10.0 || fabs(releaseVelocity.y) > 10.0) {
            self->_scrollViewFlags.isDecelerating = 1;
        }
        return;
    }
    
    bool canBounceX = UIScrollView_canBounceHorizontal(self);
    bool canBounceY = UIScrollView_canBounceVertical(self);
    
    /* Check axis-specific bounce permissions */
    bool willBounceX = overscrolledX && canBounceX;
    bool willBounceY = overscrolledY && canBounceY;
    
    /* Pin non-bounceable overscrolled axes immediately to boundary */
    if (overscrolledX && !canBounceX) {
        self->_contentOffset.x = targetX;
        dispX = 0.0;
        releaseVelocity.x = 0.0;
    }
    if (overscrolledY && !canBounceY) {
        self->_contentOffset.y = targetY;
        dispY = 0.0;
        releaseVelocity.y = 0.0;
    }
    
    /* If neither axis is allowed to bounce, snap to equilibrium and terminate */
    if (!willBounceX && !willBounceY) {
        self->_contentOffset.x = targetX;
        self->_contentOffset.y = targetY;
        self->_scrollViewFlags.isDecelerating = 0;
        return;
    }
    
    /* If master bounces switch is disabled */
    if (!self->_scrollViewFlags.bounces) {
        self->_contentOffset.x = targetX;
        self->_contentOffset.y = targetY;
        self->_scrollViewFlags.isDecelerating = 0;
        return;
    }
    
    /* Launch _UIScrollViewSpringAnimation with non-zero initial displacement */
    if (!self->_springAnimation) {
        self->_springAnimation = (_UIScrollViewSpringAnimation *)malloc(sizeof(_UIScrollViewSpringAnimation));
    }
    
    _UIScrollViewSpringAnimation *spring = self->_springAnimation;
    spring->scrollView = self;
    spring->mass = kSpringMass;
    if (self->_refreshControlActive) {
        spring->stiffness = kSpringStiffnessPull;
        spring->damping = kSpringDampingPull;
        spring->dampingRatio = kSpringDampingRatio;
        spring->naturalFrequency = kSpringNaturalFrequencyPull;
        spring->dampedFrequency = kSpringDampedFrequencyPull;
    } else {
        spring->stiffness = kSpringStiffnessDefault;
        spring->damping = kSpringDampingDefault;
        spring->dampingRatio = kSpringDampingRatio;
        spring->naturalFrequency = kSpringNaturalFrequency;
        spring->dampedFrequency = kSpringDampedFrequency;
    }
    spring->epsilonPosition = kSpringSettleThresholdPos;
    spring->epsilonVelocity = kSpringSettleThresholdVel;
    
    spring->equilibriumOffset.x = targetX;
    spring->equilibriumOffset.y = targetY;
    
    /* Initial displacement relative to boundary for permitted axes */
    spring->initialDisplacement.x = willBounceX ? dispX : 0.0;
    spring->initialDisplacement.y = willBounceY ? dispY : 0.0;
    
    /* Finger release velocity for permitted axes */
    spring->initialVelocity.x = willBounceX ? releaseVelocity.x : 0.0;
    spring->initialVelocity.y = willBounceY ? releaseVelocity.y : 0.0;
    spring->startTime = 0.0;
    
    self->_scrollViewFlags.isDecelerating = 1;
}

/**
 * Parameterized closed-form evaluation of harmonic boundary spring ODE at time t:
 *   x(t) = e^(-gamma * t) * (A * cos(omega_d * t) + B * sin(omega_d * t))
 *   v(t) = e^(-gamma * t) * ((B * omega_d - A * gamma) * cos(omega_d * t) -
 *                           (A * omega_d + B * gamma) * sin(omega_d * t))
 */
void _UIScrollViewSpringEvaluateWithParameters(double t,
                                               double x0,
                                               double v0,
                                               double dampingRatio,
                                               double naturalFrequency,
                                               double dampedFrequency,
                                               double *outPos,
                                               double *outVel) {
    double gamma = dampingRatio * naturalFrequency;
    double omega_d = (dampedFrequency > 0.0) ? dampedFrequency : (naturalFrequency * sqrt(1.0 - dampingRatio * dampingRatio));
    
    double A = x0;
    double B = (v0 + gamma * x0) / omega_d;
    
    double expDecay = exp(-gamma * t);
    double cosTerm = cos(omega_d * t);
    double sinTerm = sin(omega_d * t);
    
    *outPos = expDecay * (A * cosTerm + B * sinTerm);
    *outVel = expDecay * ((B * omega_d - A * gamma) * cosTerm - (A * omega_d + B * gamma) * sinTerm);
}

/**
 * Standard closed-form evaluation with default spring constants.
 */
void _UIScrollViewSpringEvaluate(double t,
                                 double x0,
                                 double v0,
                                 double *outPos,
                                 double *outVel) {
    _UIScrollViewSpringEvaluateWithParameters(t, x0, v0,
                                              kSpringDampingRatio,
                                              kSpringNaturalFrequency,
                                              kSpringDampedFrequency,
                                              outPos, outVel);
}

/**
 * Reconstructs -[_UIScrollViewSpringAnimation updatePosition:timestamp:] @ 0x1848c8100
 * Evaluates continuous analytical harmonic spring ODE at given timestamp,
 * updates target UIScrollView contentOffset, checks settling thresholds,
 * and snaps to equilibriumOffset when settled.
 * Returns true if animation has settled and terminated.
 */
bool _UIScrollViewSpringAnimation_updatePosition(_UIScrollViewSpringAnimation *spring, double timestamp) {
    if (!spring || !spring->scrollView) {
        return true;
    }
    
    double t = timestamp - spring->startTime;
    if (t < 0.0) {
        t = 0.0;
    }
    
    double posX = 0.0, velX = 0.0;
    double posY = 0.0, velY = 0.0;
    
    if (fabs(spring->initialDisplacement.x) > 1e-9 || fabs(spring->initialVelocity.x) > 1e-9) {
        _UIScrollViewSpringEvaluateWithParameters(t,
                                                  spring->initialDisplacement.x,
                                                  spring->initialVelocity.x,
                                                  spring->dampingRatio,
                                                  spring->naturalFrequency,
                                                  spring->dampedFrequency,
                                                  &posX, &velX);
    }
    
    if (fabs(spring->initialDisplacement.y) > 1e-9 || fabs(spring->initialVelocity.y) > 1e-9) {
        _UIScrollViewSpringEvaluateWithParameters(t,
                                                  spring->initialDisplacement.y,
                                                  spring->initialVelocity.y,
                                                  spring->dampingRatio,
                                                  spring->naturalFrequency,
                                                  spring->dampedFrequency,
                                                  &posY, &velY);
    }
    
    double epsPos = (spring->epsilonPosition > 0.0) ? spring->epsilonPosition : kSpringSettleThresholdPos;
    double epsVel = (spring->epsilonVelocity > 0.0) ? spring->epsilonVelocity : kSpringSettleThresholdVel;
    
    /* Check settling condition on all active axes */
    bool settledX = (fabs(posX) < epsPos) && (fabs(velX) < epsVel);
    bool settledY = (fabs(posY) < epsPos) && (fabs(velY) < epsVel);
    
    if (settledX && settledY) {
        /* Snap strictly to equilibrium */
        spring->scrollView->_contentOffset.x = spring->equilibriumOffset.x;
        spring->scrollView->_contentOffset.y = spring->equilibriumOffset.y;
        spring->scrollView->_scrollViewFlags.isDecelerating = 0;
        return true;
    } else {
        spring->scrollView->_contentOffset.x = spring->equilibriumOffset.x + (settledX ? 0.0 : posX);
        spring->scrollView->_contentOffset.y = spring->equilibriumOffset.y + (settledY ? 0.0 : posY);
        return false;
    }
}

/* ========================================================================= */
/* 6. Verification Test Suite & Mathematical Consistency Suite               */
/* ========================================================================= */

#ifdef RUBBER_BAND_VERIFICATION_TESTS

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    printf("============================================================\n");
    printf("Executing Phase 3C Rubber-Banding & Boundary Verification\n");
    printf("============================================================\n");
    
    double d = 852.0; /* iPhone 18 visible height */
    double c = 0.55;
    
    /* 1. Forward vs Inverse exact roundtrip verification */
    printf("[*] Test 1: Testing exact forward <-> inverse roundtrips...\n");
    double testDeltas[] = { 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0, 1600.0 };
    for (int i = 0; i < 10; i++) {
        double x = testDeltas[i];
        double y_rubber = _scrollViewRubberBandValue(x, d, c);
        double x_recovered = _scrollViewInverseRubberBandValue(y_rubber, d, c);
        double err = fabs(x - x_recovered);
        printf("  x = %7.1f pt -> rubber = %7.2f pt -> recovered = %7.2f pt (error: %.2e pt)\n",
               x, y_rubber, x_recovered, err);
        assert(err < 1e-8);
        
        /* Negative symmetry */
        double y_neg = _scrollViewRubberBandValue(-x, d, c);
        assert(fabs(y_neg + y_rubber) < 1e-12);
        double x_neg_rec = _scrollViewInverseRubberBandValue(y_neg, d, c);
        assert(fabs(x_neg_rec + x) < 1e-8);
    }
    printf("  [+] Forward-inverse roundtrip passed with machine precision (< 1e-8 pt).\n");
    
    /* 2. Asymptotic bound & singular pole input test */
    printf("[*] Test 2: Testing asymptotic bound and pole robustness (y >= d)...\n");
    double extremeX = 1e8;
    double extremeY = _scrollViewRubberBandValue(extremeX, d, c);
    printf("  For x = 1e8 pt: y_rubber = %.6f pt (viewport d = %.1f pt)\n", extremeY, d);
    assert(extremeY < d);
    assert(fabs(d - extremeY) < 1.0);
    
    /* Test inverse at pole: y = d, y > d, zero, negative zero */
    double atPole = _scrollViewInverseRubberBandValue(d, d, c);
    assert(!isnan(atPole) && !isinf(atPole) && atPole > 0.0);
    double pastPole = _scrollViewInverseRubberBandValue(d * 1.5, d, c);
    assert(!isnan(pastPole) && !isinf(pastPole) && pastPole > 0.0);
    double zeroInv = _scrollViewInverseRubberBandValue(0.0, d, c);
    assert(zeroInv == 0.0);
    double negZeroInv = _scrollViewInverseRubberBandValue(-0.0, d, c);
    assert(negZeroInv == 0.0);
    printf("  [+] Asymptotic pole and degenerate inputs handled safely without NaN/Inf.\n");
    
    /* 3. Inset geometry and boundary calculation */
    printf("[*] Test 3: Testing boundary calculation geometry...\n");
    UIScrollView sv;
    sv._bounds.size.width = 393.0;
    sv._bounds.size.height = 852.0;
    sv._contentSize.width = 393.0;
    sv._contentSize.height = 2000.0;
    sv._contentInset.top = 20.0;
    sv._contentInset.left = 0.0;
    sv._contentInset.bottom = 40.0;
    sv._contentInset.right = 0.0;
    sv._safeAreaInsets.top = 59.0;    /* Dynamic Island */
    sv._safeAreaInsets.left = 0.0;
    sv._safeAreaInsets.bottom = 34.0; /* Home indicator */
    sv._safeAreaInsets.right = 0.0;
    sv._contentInsetAdjustmentBehavior = UIScrollViewContentInsetAdjustmentAutomatic;
    sv._scrollViewFlags.isDragging = 0;
    sv._scrollViewFlags.isDecelerating = 0;
    sv._scrollViewFlags.bounces = 1;
    sv._scrollViewFlags.alwaysBounceVertical = 0;
    sv._scrollViewFlags.alwaysBounceHorizontal = 0;
    sv._scrollViewFlags.bouncesZoom = 1;
    sv._minimumZoomScale = 1.0;
    sv._maximumZoomScale = 5.0;
    sv._springAnimation = NULL;
    sv._refreshControlActive = false;
    sv._refreshControlHeight = 60.0;
    
    UIEdgeInsets adj = UIScrollView_adjustedContentInset(&sv);
    assert(adj.top == 79.0);     /* 20 + 59 */
    assert(adj.bottom == 74.0);  /* 40 + 34 */
    
    CGPoint minO = UIScrollView_minimumContentOffset(&sv);
    assert(minO.x == 0.0);
    assert(minO.y == -79.0);
    
    CGPoint maxO = UIScrollView_maximumContentOffset(&sv);
    assert(maxO.x == 0.0);
    /* 2000 + 74 - 852 = 1222.0 */
    assert(maxO.y == 1222.0);
    printf("  [+] Boundary calculations verified: min = (%.1f, %.1f), max = (%.1f, %.1f)\n",
           minO.x, minO.y, maxO.x, maxO.y);
    
    /* 4. Axis-specific policy gating (alwaysBounceVertical = 0 vs 1 with small content) */
    printf("[*] Test 4: Testing axis-specific policy gating (contentSize < bounds)...\n");
    sv._contentSize.height = 500.0; /* smaller than 852 */
    CGPoint maxSmall = UIScrollView_maximumContentOffset(&sv);
    assert(maxSmall.y == minO.y); /* Collapses to minOffset */
    
    /* With alwaysBounceVertical = 0: vertical dragging MUST NOT rubber-band */
    sv._scrollViewFlags.alwaysBounceVertical = 0;
    CGPoint dragAttempt;
    dragAttempt.x = 0.0;
    dragAttempt.y = minO.y + 100.0; /* proposed overscroll */
    CGPoint velZero = {0.0, 0.0};
    CGPoint resNoBounce = UIScrollView_rubberBandContentOffsetForOffset(&sv, dragAttempt, velZero);
    assert(resNoBounce.y == minO.y); /* strictly pinned! */
    
    /* With alwaysBounceVertical = 1: vertical dragging rubber-bands */
    sv._scrollViewFlags.alwaysBounceVertical = 1;
    CGPoint resBounce = UIScrollView_rubberBandContentOffsetForOffset(&sv, dragAttempt, velZero);
    assert(resBounce.y > minO.y); /* rubber-banded offset past boundary */
    printf("  [+] Axis policy gating verified: pinned when alwaysBounce=0, rubber-banded when alwaysBounce=1.\n");
    
    /* 5. _adjustedContentOffsetIfNecessary layout updates */
    printf("[*] Test 5: Testing _adjustedContentOffsetIfNecessary...\n");
    sv._scrollViewFlags.isDragging = 0;
    sv._scrollViewFlags.isDecelerating = 0;
    sv._contentOffset.y = 5000.0; /* out-of-bounds offset */
    CGPoint adjusted = UIScrollView_adjustedContentOffsetIfNecessary(&sv);
    assert(adjusted.y == maxSmall.y); /* clamped to maxSmall */
    
    /* While dragging: offset preserved */
    sv._scrollViewFlags.isDragging = 1;
    sv._contentOffset.y = -200.0; /* active overscroll */
    CGPoint preserved = UIScrollView_adjustedContentOffsetIfNecessary(&sv);
    assert(preserved.y == -200.0);
    sv._scrollViewFlags.isDragging = 0;
    printf("  [+] _adjustedContentOffsetIfNecessary verified (clamped when idle, preserved when dragging).\n");
    
    /* 6. Zoom rubber-band scaling */
    printf("[*] Test 6: Testing zoom rubber-band scaling (_zoomRubberBandScaleForScale)...\n");
    sv._minimumZoomScale = 1.0;
    sv._maximumZoomScale = 4.0;
    sv._scrollViewFlags.bouncesZoom = 1;
    double zoomDampedMin = UIScrollView_zoomRubberBandScaleForScale(&sv, 0.5);
    assert(zoomDampedMin < 1.0 && zoomDampedMin > 0.5);
    double zoomDampedMax = UIScrollView_zoomRubberBandScaleForScale(&sv, 6.0);
    assert(zoomDampedMax > 4.0 && zoomDampedMax < 6.0);
    
    /* Degenerate negative and extreme inputs: strictly bounded positive */
    double zoomNeg = UIScrollView_zoomRubberBandScaleForScale(&sv, -100.0);
    assert(zoomNeg > 0.0 && zoomNeg >= 1.0 * (1.0 - log(2.0) * kZoomRubberBandCoefficient));
    double zoomZero = UIScrollView_zoomRubberBandScaleForScale(&sv, 0.0);
    assert(zoomZero > 0.0);
    double zoomNan = UIScrollView_zoomRubberBandScaleForScale(&sv, NAN);
    assert(zoomNan == 1.0);
    
    sv._scrollViewFlags.bouncesZoom = 0;
    assert(UIScrollView_zoomRubberBandScaleForScale(&sv, 0.5) == 1.0);
    assert(UIScrollView_zoomRubberBandScaleForScale(&sv, 6.0) == 4.0);
    printf("  [+] Zoom rubber-band scaling verified (logarithmic damping with bouncesZoom, clamped without, safe against degenerate inputs).\n");
    
    /* 7. Touch-up overscroll bounce restitution (x0 != 0) with alwaysBounce = 1 */
    printf("[*] Test 7: Testing touch-up bounce restitution and spring settling (bounce enabled)...\n");
    sv._scrollViewFlags.alwaysBounceVertical = 1;
    sv._contentOffset.x = 0.0;
    sv._contentOffset.y = minO.y - 80.0; /* pulled 80pt past top boundary */
    CGPoint touchUpVel = {0.0, 0.0};
    UIScrollView_handleTouchUp(&sv, touchUpVel);
    assert(sv._springAnimation != NULL);
    assert(sv._springAnimation->initialDisplacement.y == -80.0);
    assert(sv._springAnimation->equilibriumOffset.y == minO.y);
    assert(sv._scrollViewFlags.isDecelerating == 1);
    
    /* Evaluate spring at t = 1.5s */
    double x_spring, v_spring;
    _UIScrollViewSpringEvaluate(1.5, sv._springAnimation->initialDisplacement.y, 0.0, &x_spring, &v_spring);
    assert(fabs(x_spring) < 0.1);
    assert(fabs(v_spring) < 0.1);
    printf("  [+] Touch-up bounce handoff verified (x0 = -80.0 pt -> settled < 0.1 pt at 1.5s).\n");
    
    /* 8. Touch-up overscroll policy gating on non-bounceable axis (contentSize < bounds, alwaysBounce = 0) */
    printf("[*] Test 8: Testing touch-up policy gating on non-bounceable axis (must NOT bounce)...\n");
    sv._contentSize.height = 500.0; /* smaller than 852.0 */
    sv._scrollViewFlags.alwaysBounceVertical = 0;
    sv._scrollViewFlags.alwaysBounceHorizontal = 0;
    sv._contentOffset.y = minO.y - 80.0; /* displaced into overscroll */
    if (sv._springAnimation) {
        free(sv._springAnimation);
        sv._springAnimation = NULL;
    }
    UIScrollView_handleTouchUp(&sv, touchUpVel);
    /* MUST be strictly pinned to minO.y and NOT launch spring animation */
    assert(sv._contentOffset.y == minO.y);
    assert(sv._scrollViewFlags.isDecelerating == 0);
    printf("  [+] Non-bounceable touch-up strictly pinned: offset = %.1f, isDecelerating = %u\n",
           sv._contentOffset.y, sv._scrollViewFlags.isDecelerating);
    
    /* 9. Pull-to-refresh dynamic spring parameters and updatePosition:timestamp: lifecycle */
    printf("[*] Test 9: Testing pull-to-refresh dynamic spring parameters and updatePosition lifecycle...\n");
    sv._contentSize.height = 2000.0;
    sv._scrollViewFlags.alwaysBounceVertical = 1;
    sv._refreshControlActive = true;
    sv._refreshControlHeight = 60.0;
    CGPoint minPinned = UIScrollView_minimumContentOffset(&sv);
    assert(minPinned.y == -79.0 - 60.0); /* -139.0 pt */
    sv._contentOffset.y = minPinned.y - 50.0; /* overscrolled past pinned refresh */
    UIScrollView_handleTouchUp(&sv, touchUpVel);
    assert(sv._springAnimation != NULL);
    assert(sv._springAnimation->stiffness == kSpringStiffnessPull); /* 180.0 */
    assert(fabs(sv._springAnimation->damping - kSpringDampingPull) < 1e-6); /* 24.15 */
    assert(fabs(sv._springAnimation->naturalFrequency - kSpringNaturalFrequencyPull) < 1e-6); /* 13.42 */
    
    /* Test frame tick updates via _UIScrollViewSpringAnimation_updatePosition */
    sv._springAnimation->startTime = 0.0;
    bool settled_at_0 = _UIScrollViewSpringAnimation_updatePosition(sv._springAnimation, 0.0);
    assert(!settled_at_0);
    assert(sv._scrollViewFlags.isDecelerating == 1);
    
    /* Fast settling under stiffer pull-to-refresh spring */
    bool settled_at_1 = _UIScrollViewSpringAnimation_updatePosition(sv._springAnimation, 1.0);
    assert(settled_at_1);
    assert(sv._contentOffset.y == minPinned.y); /* strictly snapped to equilibrium */
    assert(sv._scrollViewFlags.isDecelerating == 0);
    sv._refreshControlActive = false;
    printf("  [+] Pull-to-refresh dynamic spring lifecycle verified (k = 180, c = 24.15, settled at 1.0s).\n");
    
    /* 10. 2D diagonal boundary collision unbreached axis preservation */
    printf("[*] Test 10: Testing 2D diagonal collision unbreached axis coordinate preservation...\n");
    if (sv._springAnimation) {
        free(sv._springAnimation);
        sv._springAnimation = NULL;
    }
    CGPoint curPt = { 10.0, 100.0 };
    CGPoint nextPt = { -15.0, 120.0 }; /* X breaches minOffset.x (0), Y remains in bounds (moves 100 -> 120) */
    CGPoint curVel = { -200.0, 100.0 };
    
    /* 10A: Inelastic collision (alwaysBounceHorizontal = 0): X pinned, Y preserved, deceleration continues */
    sv._scrollViewFlags.alwaysBounceHorizontal = 0;
    sv._scrollViewFlags.alwaysBounceVertical = 1;
    UIScrollView_handleBoundaryCollision(&sv, curPt, nextPt, curVel, 0.016, 0.998);
    assert(sv._contentOffset.x == 0.0);    /* Breached X pinned to minOffset.x */
    assert(sv._contentOffset.y == 120.0);  /* Unbreached Y preserved at nextOffset.y! */
    assert(sv._scrollViewFlags.isDecelerating == 1); /* Y continues decelerating */
    
    /* 10B: Elastic spring collision (alwaysBounceHorizontal = 1): X bounces, Y equilibrium preserved */
    sv._scrollViewFlags.alwaysBounceHorizontal = 1;
    UIScrollView_handleBoundaryCollision(&sv, curPt, nextPt, curVel, 0.016, 0.998);
    assert(sv._contentOffset.x == 0.0);
    assert(sv._contentOffset.y == 120.0);
    assert(sv._springAnimation != NULL);
    assert(sv._springAnimation->equilibriumOffset.x == 0.0);
    assert(sv._springAnimation->equilibriumOffset.y == 120.0); /* Equilibrium at nextOffset.y */
    assert(sv._springAnimation->initialVelocity.x < 0.0); /* Residual velocity transfer */
    
    /* 10C: Step 2D spring animation: verify dynamic compression along X while Y remains stably pinned at 120.0 */
    sv._springAnimation->startTime = 0.0;
    bool step_early = _UIScrollViewSpringAnimation_updatePosition(sv._springAnimation, 0.08);
    assert(!step_early);
    assert(sv._contentOffset.x < 0.0); /* Compressed into overscroll along X */
    assert(sv._contentOffset.y == 120.0); /* Stable at 120.0 along unbreached Y */
    assert(sv._scrollViewFlags.isDecelerating == 1);
    
    /* Step to full settling at t = 1.5s */
    bool step_settled = _UIScrollViewSpringAnimation_updatePosition(sv._springAnimation, 1.5);
    assert(step_settled);
    assert(sv._contentOffset.x == 0.0); /* Restituted back to 0.0 boundary */
    assert(sv._contentOffset.y == 120.0);
    assert(sv._scrollViewFlags.isDecelerating == 0);
    printf("  [+] 2D diagonal collision & dynamic spring step verified: X compressed then settled to 0.0, Y preserved at 120.0\n");
    
    if (sv._springAnimation) {
        free(sv._springAnimation);
        sv._springAnimation = NULL;
    }
    
    /* 11. Test UIScrollView_rubberBandOffsetWithoutDecorationForOffset & boundary breach jitter resilience */
    printf("[*] Test 11: Testing _rubberBandOffsetWithoutDecorationForOffset and boundary jitter...\n");
    bool outsideFlag = false;
    double rawRubber = UIScrollView_rubberBandOffsetWithoutDecorationForOffset(&sv, -100.0, 1000.0, 0.0, 852.0, &outsideFlag);
    assert(outsideFlag == true);
    assert(rawRubber < 0.0 && rawRubber > -100.0);
    
    /* Boundary jitter test: currentOffset is slightly outside (-1e-11) moving further outward with negative velocity */
    CGPoint jitterCur = { -1e-11, 50.0 };
    CGPoint jitterNext = { -5.0, 50.0 };
    CGPoint jitterVel = { -200.0, 0.0 };
    sv._contentOffset = jitterCur;
    sv._scrollViewFlags.alwaysBounceHorizontal = 1;
    UIScrollView_handleBoundaryCollision(&sv, jitterCur, jitterNext, jitterVel, 0.016, 0.998);
    assert(sv._springAnimation != NULL);
    assert(sv._contentOffset.x == 0.0); /* Successfully caught breach despite bordering offset! */
    assert(sv._springAnimation->initialVelocity.x < 0.0);
    if (sv._springAnimation) {
        free(sv._springAnimation);
        sv._springAnimation = NULL;
    }
    printf("  [+] _rubberBandOffsetWithoutDecorationForOffset and boundary jitter detection verified.\n");
    
    /* 12. Defensive NULL robustness & zero-bounds collapse */
    printf("[*] Test 12: Testing NULL pointer robustness & zero-bounds collapse...\n");
    assert(UIScrollView_zoomRubberBandScaleForScale(NULL, 2.0) == 2.0);
    assert(UIScrollView_zoomRubberBandScaleForScale(NULL, NAN) == 1.0);
    assert(UIScrollView_canBounceVertical(NULL) == false);
    assert(UIScrollView_canBounceHorizontal(NULL) == false);
    
    /* Zero-bounds view: bounds.size = (0, 0) */
    UIScrollView zeroSV = sv;
    zeroSV._bounds.size.width = 0.0;
    zeroSV._bounds.size.height = 0.0;
    assert(UIScrollView_canBounceHorizontal(&zeroSV) == false);
    assert(UIScrollView_canBounceVertical(&zeroSV) == false);
    CGPoint zeroMin = UIScrollView_minimumContentOffset(&zeroSV);
    CGPoint zeroMax = UIScrollView_maximumContentOffset(&zeroSV);
    assert(zeroMax.x == zeroMin.x && zeroMax.y == zeroMin.y);
    
    /* Pull-to-refresh active vertical bounce permission override */
    zeroSV._bounds.size.height = 852.0;
    zeroSV._contentSize.height = 400.0; /* smaller than bounds */
    zeroSV._scrollViewFlags.alwaysBounceVertical = 0;
    zeroSV._refreshControlActive = false;
    assert(UIScrollView_canBounceVertical(&zeroSV) == false);
    zeroSV._refreshControlActive = true;
    assert(UIScrollView_canBounceVertical(&zeroSV) == true);
    printf("  [+] NULL safety, 0-bounds collapse, and refreshControlActive bounce override verified.\n");
    
    printf("\n>>> ALL PHASE 3C MATHEMATICAL ASSERTIONS PASSED <<<\n");
    return 0;
}

#endif /* RUBBER_BAND_VERIFICATION_TESTS */
