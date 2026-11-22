/**
 * iOS 27 Reverse Engineering Pipeline: Specialized Scrolling Implementations
 * Subsystems: SwiftUI.framework, WebKit.framework, UIKitCore (UITextView, UICollectionView, UITableView), UIAccessibility
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00), SoC t8150 (A19 Pro)
 *
 * Compiles cleanly under: gcc -Wall -Wextra -Werror -std=c99 specialized_scroll.pseudo.c -lm
 * Contains 38 rigorous unit assertion test suites in main().
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/* ========================================================================= */
/* 1. Core Geometric Types and Mathematics Primitives                        */
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

static inline double clamp_double(double val, double min_val, double max_val) {
    if (val < min_val) return min_val;
    if (val > max_val) return max_val;
    return val;
}

/* ========================================================================= */
/* 2. SwiftUI Declarative Scrolling Engine Types & Mechanics                 */
/* ========================================================================= */

typedef enum ScrollPositionTargetType {
    kScrollPositionTargetPoint = 0,
    kScrollPositionTargetEdge  = 1,
    kScrollPositionTargetID    = 2
} ScrollPositionTargetType;

typedef enum ScrollEdge {
    kScrollEdgeTop      = 0,
    kScrollEdgeLeading  = 1,
    kScrollEdgeBottom   = 2,
    kScrollEdgeTrailing = 3
} ScrollEdge;

typedef struct UnitPoint {
    double x;
    double y;
} UnitPoint;

typedef struct SwiftUI_ScrollPosition {
    ScrollPositionTargetType targetType;
    CGPoint pointValue;
    ScrollEdge edgeValue;
    int64_t targetID;
    UnitPoint anchor;
    bool isPositioned;
} SwiftUI_ScrollPosition;

typedef struct SwiftUICore_ScrollGeometry {
    CGPoint contentOffset;
    CGSize contentSize;
    UIEdgeInsets contentInsets;
    CGSize boundsSize;
} SwiftUICore_ScrollGeometry;

typedef enum SwiftUICore_ScrollPhase {
    kScrollPhaseIdle         = 0,
    kScrollPhaseInteracting    = 1,
    kScrollPhaseDecelerating = 2,
    kScrollPhaseAnimating    = 3
} SwiftUICore_ScrollPhase;

typedef struct _UIHostingScrollView {
    CGPoint contentOffset;
    CGSize contentSize;
    UIEdgeInsets contentInsets;
    CGRect bounds;
    bool isDragging;
    bool isDecelerating;
    bool programmaticScrollAnimating;
    bool isScrollEnabled;
    bool showsHorizontalScrollIndicator;
    bool showsVerticalScrollIndicator;

    /* SwiftUI coordination ivars */
    bool isProgrammaticUpdate;
    bool scrollDisabledOverride;
    bool geometryListenerRegistered;
    int scrollTargetBehaviorMode; /* 0 = none, 1 = paging, 2 = viewAligned */
    uint32_t echoSuppressionCounter;
} _UIHostingScrollView;

static inline SwiftUI_ScrollPosition swiftui_scroll_position_init_point(CGPoint pt) {
    SwiftUI_ScrollPosition pos;
    pos.targetType = kScrollPositionTargetPoint;
    pos.pointValue = pt;
    pos.edgeValue = kScrollEdgeTop;
    pos.targetID = 0;
    pos.anchor.x = 0.0;
    pos.anchor.y = 0.0;
    pos.isPositioned = true;
    return pos;
}

static inline SwiftUI_ScrollPosition swiftui_scroll_position_init_edge(ScrollEdge edge) {
    SwiftUI_ScrollPosition pos;
    pos.targetType = kScrollPositionTargetEdge;
    pos.pointValue = CGPointMake(0.0, 0.0);
    pos.edgeValue = edge;
    pos.targetID = 0;
    pos.anchor.x = 0.0;
    pos.anchor.y = 0.0;
    pos.isPositioned = true;
    return pos;
}

static inline SwiftUI_ScrollPosition swiftui_scroll_position_init_id(int64_t id_val, UnitPoint anchor) {
    SwiftUI_ScrollPosition pos;
    pos.targetType = kScrollPositionTargetID;
    pos.pointValue = CGPointMake(0.0, 0.0);
    pos.edgeValue = kScrollEdgeTop;
    pos.targetID = id_val;
    pos.anchor = anchor;
    pos.isPositioned = true;
    return pos;
}

static inline CGPoint swiftui_bridge_calculate_target_offset(CGSize contentSize, CGSize boundsSize, UnitPoint anchor, CGPoint itemOrigin, CGSize itemSize) {
    CGPoint target;
    double rawX = itemOrigin.x - anchor.x * (boundsSize.width - itemSize.width);
    double rawY = itemOrigin.y - anchor.y * (boundsSize.height - itemSize.height);
    double maxX = contentSize.width - boundsSize.width;
    double maxY = contentSize.height - boundsSize.height;
    if (maxX < 0.0) maxX = 0.0;
    if (maxY < 0.0) maxY = 0.0;
    target.x = clamp_double(rawX, 0.0, maxX);
    target.y = clamp_double(rawY, 0.0, maxY);
    return target;
}

static inline void swiftui_hosting_scroll_view_set_content_offset(_UIHostingScrollView *view, CGPoint newOffset, bool animated, bool isProgrammatic) {
    if (isProgrammatic) {
        view->isProgrammaticUpdate = true;
        view->echoSuppressionCounter++;
    }
    view->contentOffset = newOffset;
    if (animated) {
        view->programmaticScrollAnimating = true;
    }
    /* When programmatic update completes, suppress feedback echo */
    if (isProgrammatic && !animated) {
        view->isProgrammaticUpdate = false;
    }
}

static inline SwiftUICore_ScrollGeometry swiftui_hosting_scroll_view_get_geometry(const _UIHostingScrollView *view) {
    SwiftUICore_ScrollGeometry geom;
    geom.contentOffset = view->contentOffset;
    geom.contentSize = view->contentSize;
    geom.contentInsets = view->contentInsets;
    geom.boundsSize = view->bounds.size;
    return geom;
}

static inline SwiftUICore_ScrollPhase swiftui_hosting_scroll_view_get_phase(const _UIHostingScrollView *view) {
    if (view->isDragging) {
        return kScrollPhaseInteracting;
    }
    if (view->isDecelerating) {
        return kScrollPhaseDecelerating;
    }
    if (view->programmaticScrollAnimating) {
        return kScrollPhaseAnimating;
    }
    return kScrollPhaseIdle;
}

static inline bool swiftui_gesture_should_recognize_simultaneously(bool isSimultaneousModifierDeclared, bool isHighPriorityModifierDeclared) {
    if (isSimultaneousModifierDeclared) {
        return true;
    }
    if (isHighPriorityModifierDeclared) {
        return false;
    }
    /* Default UIKit arbitration */
    return false;
}

/* ========================================================================= */
/* 3. WebKit Multi-Process Viewport Scrolling Architecture                   */
/* ========================================================================= */

typedef enum WebKitOverscrollBehavior {
    kOverscrollBehaviorAuto    = 0,
    kOverscrollBehaviorContain = 1,
    kOverscrollBehaviorNone    = 2
} WebKitOverscrollBehavior;

typedef struct ScrollingTreeScrollingNodeIOS {
    uint64_t nodeID;
    CGPoint currentPosition;
    CGPoint layerTransformOffset;
    WebKitOverscrollBehavior overscrollBehaviorX;
    WebKitOverscrollBehavior overscrollBehaviorY;
    bool hasPendingCommit;
} ScrollingTreeScrollingNodeIOS;

typedef struct WKScrollView {
    CGPoint contentOffset;
    CGSize contentSize;
    UIEdgeInsets contentInsets;
    CGRect bounds;
    bool isDragging;
    bool isDecelerating;
    uint32_t internalDelegateCallbacksCount;
    uint32_t externalDelegateCallbacksCount;
    ScrollingTreeScrollingNodeIOS scrollingNode;
} WKScrollView;

static inline void webkit_scrolling_tree_apply_async_transform(ScrollingTreeScrollingNodeIOS *node, CGPoint newPosition) {
    node->currentPosition = newPosition;
    /* Layer transform translation: CATransform3DMakeTranslation(-pos.x, -pos.y, 0) */
    node->layerTransformOffset.x = -newPosition.x;
    node->layerTransformOffset.y = -newPosition.y;
    node->hasPendingCommit = true;
}

static inline void webkit_scroll_view_set_content_offset(WKScrollView *view, CGPoint newOffset) {
    view->contentOffset = newOffset;
    view->internalDelegateCallbacksCount++;
    view->externalDelegateCallbacksCount++;
    webkit_scrolling_tree_apply_async_transform(&view->scrollingNode, newOffset);
}

static inline double webkit_compute_rubber_band_displacement(WebKitOverscrollBehavior behavior, double currentOffset, double minOffset, double maxOffset, double dimension) {
    if (behavior == kOverscrollBehaviorNone || dimension <= 0.0) {
        /* CSS overscroll-behavior: none strictly suppresses rubber-band bounce, and non-positive dimension guards against division by zero */
        return 0.0;
    }
    double overscroll = 0.0;
    if (currentOffset < minOffset) {
        overscroll = currentOffset - minOffset;
    } else if (currentOffset > maxOffset) {
        overscroll = currentOffset - maxOffset;
    } else {
        return 0.0;
    }

    /* Authoritative rational formula: f(x) = (1 - 1 / ((|x| * c / d) + 1)) * d * sgn(x) with c = 0.55 */
    const double c = 0.55;
    double absOverscroll = fabs(overscroll);
    double resistance = (1.0 - (1.0 / ((absOverscroll * c / dimension) + 1.0))) * dimension;
    return (overscroll < 0.0) ? -resistance : resistance;
}

typedef struct WebKitWheelEventQueue {
    bool isAsyncDispatchImmediate;
    bool activeListenerBlocked;
    double timeoutAccumulatorMs;
    uint32_t coalescedEventsCount;
} WebKitWheelEventQueue;

static inline void webkit_wheel_event_process(WebKitWheelEventQueue *queue, bool isPassiveListener, double deltaMs) {
    if (isPassiveListener) {
        /* Passive listeners never block UIProcess asynchronous scrolling */
        queue->isAsyncDispatchImmediate = true;
        queue->activeListenerBlocked = false;
        queue->coalescedEventsCount++;
        queue->timeoutAccumulatorMs = 0.0;
    } else {
        queue->activeListenerBlocked = true;
        queue->timeoutAccumulatorMs += deltaMs;
        if (queue->timeoutAccumulatorMs >= 100.0) {
            /* Active listener exceeded 100ms timeout: unblock and fallback to async scrolling */
            queue->activeListenerBlocked = false;
            queue->isAsyncDispatchImmediate = true;
            queue->coalescedEventsCount++;
        } else {
            queue->isAsyncDispatchImmediate = false;
        }
    }
}

/* --- WebCore Tile Cache and Memory Pressure Eviction Engine --- */

typedef enum TilePurgeState {
    kTilePurgeStateNone     = 0,
    kTilePurgeStateVolatile = 1,
    kTilePurgeStatePurged   = 2
} TilePurgeState;

typedef struct WebCoreTile {
    int64_t tileID;
    CGRect tileRect;
    TilePurgeState purgeState;
    bool isVisibleInViewport;
    bool isPreloadCoverage;
} WebCoreTile;

typedef struct WebCoreTileController {
    WebCoreTile tiles[16];
    uint32_t tileCount;
    uint32_t memoryPressureWarningLevel; /* 0 = normal, 1 = warning, 2 = critical */
    uint32_t totalPurgedTiles;
    uint32_t fallbackCheckerboardFrames;
} WebCoreTileController;

static inline void webkit_tile_controller_handle_memory_pressure(WebCoreTileController *tc, uint32_t warningLevel) {
    tc->memoryPressureWarningLevel = warningLevel;
    if (warningLevel == 0) return;

    for (uint32_t i = 0; i < tc->tileCount; i++) {
        if (!tc->tiles[i].isVisibleInViewport) {
            if (warningLevel == 1) {
                /* Moderate memory pressure: secondary coverage tiles marked volatile */
                tc->tiles[i].purgeState = kTilePurgeStateVolatile;
            } else if (warningLevel >= 2) {
                /* Extreme OOM: non-visible tiles immediately purged */
                tc->tiles[i].purgeState = kTilePurgeStatePurged;
                tc->totalPurgedTiles++;
            }
        }
    }
}

static inline bool webkit_scrolling_tree_render_tile(const WebCoreTileController *tc, uint32_t tileIndex) {
    if (tileIndex >= tc->tileCount) return false;
    if (tc->tiles[tileIndex].purgeState == kTilePurgeStatePurged) {
        /* Tile was purged under OOM: UIProcess displays checkerboard fallback */
        return false;
    }
    return true; /* Render cached IOSurface */
}

/* ========================================================================= */
/* 4. UITextView & TextKit Kinetic Auto-Scroll Mechanics                     */
/* ========================================================================= */

typedef struct UITextViewContext {
    CGPoint contentOffset;
    CGSize contentSize;
    UIEdgeInsets contentInsets;
    CGRect bounds;
    CGRect caretRect;
    double maxAutoScrollVelocity;  /* 1400.0 pt/s */
    double edgeProximityBandDepth; /* 44.0 pt */
    double velocityRampingExponent;/* 2.0 (quadratic) */
    double caretSafetyMargin;      /* 8.0 pt */
} UITextViewContext;

static inline bool textview_cursor_auto_scroll(UITextViewContext *view, CGRect newCaretRect) {
    view->caretRect = newCaretRect;
    double visibleMinY = view->contentOffset.y + view->contentInsets.top;
    double visibleMaxY = view->contentOffset.y + view->bounds.size.height - view->contentInsets.bottom;
    double caretTop = newCaretRect.origin.y - view->caretSafetyMargin;
    double caretBottom = newCaretRect.origin.y + newCaretRect.size.height + view->caretSafetyMargin;

    if (caretTop < visibleMinY) {
        double targetY = caretTop - view->contentInsets.top;
        if (targetY < -view->contentInsets.top) targetY = -view->contentInsets.top;
        view->contentOffset.y = targetY;
        return true;
    }
    if (caretBottom > visibleMaxY) {
        double targetY = caretBottom - view->bounds.size.height + view->contentInsets.bottom;
        double maxScrollY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
        if (targetY > maxScrollY) targetY = maxScrollY;
        view->contentOffset.y = targetY;
        return true;
    }
    return false;
}

typedef struct TextDragVelocity2D {
    double vx; /* pt/s, negative = scroll left, positive = scroll right */
    double vy; /* pt/s, negative = scroll up, positive = scroll down */
    bool isScrollingX;
    bool isScrollingY;
} TextDragVelocity2D;

static inline double textview_calculate_selection_drag_velocity(const UITextViewContext *view, CGPoint touchLocation, bool *outScrollDown) {
    double topEdge = view->bounds.origin.y + view->contentInsets.top;
    double bottomEdge = view->bounds.origin.y + view->bounds.size.height - view->contentInsets.bottom;
    double effectiveHeight = bottomEdge - topEdge;
    if (effectiveHeight <= 0.0) {
        *outScrollDown = false;
        return 0.0;
    }

    /* Dynamic normalization: proximity depth cannot exceed half the effective dimension (prevents zone overlap in compact viewports) */
    double dEdge = view->edgeProximityBandDepth;
    double maxHalfBand = effectiveHeight * 0.5;
    if (dEdge > maxHalfBand && maxHalfBand > 0.0) {
        dEdge = maxHalfBand;
    }
    if (dEdge <= 0.0) {
        *outScrollDown = false;
        return 0.0;
    }

    double vMax = view->maxAutoScrollVelocity;
    double p = view->velocityRampingExponent;

    /* Top boundary breached */
    if (touchLocation.y <= topEdge + dEdge) {
        *outScrollDown = false;
        double dist = touchLocation.y - topEdge;
        if (dist <= 0.0) {
            return vMax;
        }
        double ratio = (dEdge - dist) / dEdge;
        return vMax * pow(ratio, p);
    }

    /* Bottom boundary breached */
    if (touchLocation.y >= bottomEdge - dEdge) {
        *outScrollDown = true;
        double dist = bottomEdge - touchLocation.y;
        if (dist <= 0.0) {
            return vMax;
        }
        double ratio = (dEdge - dist) / dEdge;
        return vMax * pow(ratio, p);
    }

    *outScrollDown = false;
    return 0.0;
}

static inline TextDragVelocity2D textview_calculate_selection_drag_velocity_2d(const UITextViewContext *view, CGPoint touchLocation) {
    TextDragVelocity2D vel;
    vel.vx = 0.0;
    vel.vy = 0.0;
    vel.isScrollingX = false;
    vel.isScrollingY = false;

    double topEdge = view->bounds.origin.y + view->contentInsets.top;
    double bottomEdge = view->bounds.origin.y + view->bounds.size.height - view->contentInsets.bottom;
    double leftEdge = view->bounds.origin.x + view->contentInsets.left;
    double rightEdge = view->bounds.origin.x + view->bounds.size.width - view->contentInsets.right;

    double effH = bottomEdge - topEdge;
    double effW = rightEdge - leftEdge;
    if (effH < 0.0) effH = 0.0;
    if (effW < 0.0) effW = 0.0;

    double dEdgeY = view->edgeProximityBandDepth;
    if (dEdgeY > effH * 0.5 && effH > 0.0) dEdgeY = effH * 0.5;

    double dEdgeX = view->edgeProximityBandDepth;
    if (dEdgeX > effW * 0.5 && effW > 0.0) dEdgeX = effW * 0.5;

    double vMax = view->maxAutoScrollVelocity;
    double p = view->velocityRampingExponent;

    /* Y-Axis calculation */
    if (effH > 0.0 && dEdgeY > 0.0) {
        if (touchLocation.y <= topEdge + dEdgeY) {
            vel.isScrollingY = true;
            double dist = touchLocation.y - topEdge;
            double mag = (dist <= 0.0) ? vMax : vMax * pow((dEdgeY - dist) / dEdgeY, p);
            vel.vy = -mag; /* Scroll up */
        } else if (touchLocation.y >= bottomEdge - dEdgeY) {
            vel.isScrollingY = true;
            double dist = bottomEdge - touchLocation.y;
            double mag = (dist <= 0.0) ? vMax : vMax * pow((dEdgeY - dist) / dEdgeY, p);
            vel.vy = +mag; /* Scroll down */
        }
    }

    /* X-Axis calculation */
    if (effW > 0.0 && dEdgeX > 0.0) {
        if (touchLocation.x <= leftEdge + dEdgeX) {
            vel.isScrollingX = true;
            double dist = touchLocation.x - leftEdge;
            double mag = (dist <= 0.0) ? vMax : vMax * pow((dEdgeX - dist) / dEdgeX, p);
            vel.vx = -mag; /* Scroll left */
        } else if (touchLocation.x >= rightEdge - dEdgeX) {
            vel.isScrollingX = true;
            double dist = rightEdge - touchLocation.x;
            double mag = (dist <= 0.0) ? vMax : vMax * pow((dEdgeX - dist) / dEdgeX, p);
            vel.vx = +mag; /* Scroll right */
        }
    }

    return vel;
}

/* --- TextKit 2 Multi-Container & Exclusion Path Slicing Engine --- */

typedef struct TextContainerGeometry {
    int64_t containerIndex;
    CGPoint containerOrigin; /* Position within multi-container layout canvas */
    CGSize containerSize;
    UIEdgeInsets containerInsets;
} TextContainerGeometry;

typedef struct TextKit2ExclusionObstacle {
    CGPoint center;
    double radius; /* Circular exclusion obstacle */
    bool isActive;
} TextKit2ExclusionObstacle;

typedef struct TextKit2LineFragmentSlice {
    double startX;
    double width;
} TextKit2LineFragmentSlice;

typedef struct TextKit2LineFragment {
    double lineY;
    double lineHeight;
    TextKit2LineFragmentSlice slices[8];
    uint32_t sliceCount;
} TextKit2LineFragment;

typedef struct TextKit2Interval {
    double start;
    double end;
} TextKit2Interval;

static inline void textkit2_compute_line_fragment_slices_multi(
    double containerWidth,
    double lineY,
    double lineHeight,
    const TextKit2ExclusionObstacle *obstacles,
    uint32_t obstacleCount,
    double obstacleMargin,
    TextKit2LineFragment *outFragment
) {
    outFragment->lineY = lineY;
    outFragment->lineHeight = lineHeight;
    outFragment->sliceCount = 0;

    if (containerWidth <= 0.0) return;

    double lineCenterY = lineY + lineHeight * 0.5;

    /* 1. Collect all active exclusion intervals intersecting this line */
    TextKit2Interval rawIntervals[16];
    uint32_t rawCount = 0;

    for (uint32_t i = 0; i < obstacleCount && rawCount < 16; i++) {
        const TextKit2ExclusionObstacle *obs = &obstacles[i];
        if (!obs || !obs->isActive) continue;

        double dy = fabs(lineCenterY - obs->center.y);
        double effectiveRadius = obs->radius + obstacleMargin;
        if (dy >= effectiveRadius) continue;

        double dx = sqrt(effectiveRadius * effectiveRadius - dy * dy);
        double left = obs->center.x - dx;
        double right = obs->center.x + dx;

        /* Clamp to container bounds */
        if (left < 0.0) left = 0.0;
        if (right > containerWidth) right = containerWidth;

        if (left < right) {
            rawIntervals[rawCount].start = left;
            rawIntervals[rawCount].end = right;
            rawCount++;
        }
    }

    if (rawCount == 0) {
        /* No obstacles intersecting this line: single full-width slice */
        outFragment->slices[0].startX = 0.0;
        outFragment->slices[0].width = containerWidth;
        outFragment->sliceCount = 1;
        return;
    }

    /* 2. Sort intervals by start ascending (insertion sort for small N) */
    for (uint32_t i = 1; i < rawCount; i++) {
        TextKit2Interval key = rawIntervals[i];
        int j = (int)i - 1;
        while (j >= 0 && rawIntervals[j].start > key.start) {
            rawIntervals[j + 1] = rawIntervals[j];
            j--;
        }
        rawIntervals[j + 1] = key;
    }

    /* 3. Merge overlapping / contiguous intervals (exact 1D interval union) */
    TextKit2Interval merged[16];
    uint32_t mergedCount = 0;
    merged[0] = rawIntervals[0];
    mergedCount = 1;

    for (uint32_t i = 1; i < rawCount; i++) {
        if (rawIntervals[i].start <= merged[mergedCount - 1].end) {
            if (rawIntervals[i].end > merged[mergedCount - 1].end) {
                merged[mergedCount - 1].end = rawIntervals[i].end;
            }
        } else {
            merged[mergedCount++] = rawIntervals[i];
        }
    }

    /* 4. Perform boolean difference [0, containerWidth] \ union(merged) to generate valid slices */
    double currX = 0.0;
    for (uint32_t i = 0; i < mergedCount && outFragment->sliceCount < 8; i++) {
        if (merged[i].start > currX) {
            outFragment->slices[outFragment->sliceCount].startX = currX;
            outFragment->slices[outFragment->sliceCount].width = merged[i].start - currX;
            outFragment->sliceCount++;
        }
        if (merged[i].end > currX) {
            currX = merged[i].end;
        }
    }

    if (currX < containerWidth && outFragment->sliceCount < 8) {
        outFragment->slices[outFragment->sliceCount].startX = currX;
        outFragment->slices[outFragment->sliceCount].width = containerWidth - currX;
        outFragment->sliceCount++;
    }
}

static inline void textkit2_compute_line_fragment_slices(
    double containerWidth,
    double lineY,
    double lineHeight,
    const TextKit2ExclusionObstacle *obstacle,
    double obstacleMargin,
    TextKit2LineFragment *outFragment
) {
    if (obstacle) {
        textkit2_compute_line_fragment_slices_multi(containerWidth, lineY, lineHeight, obstacle, 1, obstacleMargin, outFragment);
    } else {
        textkit2_compute_line_fragment_slices_multi(containerWidth, lineY, lineHeight, NULL, 0, obstacleMargin, outFragment);
    }
}

typedef struct TextKit2MultiContainerContext {
    TextContainerGeometry containers[4];
    uint32_t containerCount;
    int64_t activeContainerIndex;
    CGRect activeCaretRectLocal;
    CGPoint projectedViewportTarget;
} TextKit2MultiContainerContext;

static inline CGPoint textkit2_project_caret_to_viewport(
    TextKit2MultiContainerContext *ctx,
    int64_t containerIndex,
    CGRect localCaretRect,
    double safetyPadding
) {
    assert(containerIndex >= 0 && containerIndex < (int64_t)ctx->containerCount);
    ctx->activeContainerIndex = containerIndex;
    ctx->activeCaretRectLocal = localCaretRect;

    const TextContainerGeometry *tc = &ctx->containers[containerIndex];
    /* Global canvas coordinate = containerOrigin + localCaretOrigin */
    double globalCaretX = tc->containerOrigin.x + localCaretRect.origin.x;
    double globalCaretY = tc->containerOrigin.y + localCaretRect.origin.y;

    /* Viewport target centered or aligned with safety padding */
    CGPoint target;
    target.x = globalCaretX - safetyPadding;
    target.y = globalCaretY - safetyPadding;
    if (target.x < 0.0) target.x = 0.0;
    if (target.y < 0.0) target.y = 0.0;
    ctx->projectedViewportTarget = target;
    return target;
}

static inline CGPoint textkit2_project_caret_with_exclusion(
    TextKit2MultiContainerContext *ctx,
    int64_t containerIndex,
    const TextKit2LineFragment *fragment,
    uint32_t sliceIndex,
    double localSliceOffset,
    double safetyPadding
) {
    assert(containerIndex >= 0 && containerIndex < (int64_t)ctx->containerCount);
    assert(sliceIndex < fragment->sliceCount);

    ctx->activeContainerIndex = containerIndex;
    const TextContainerGeometry *tc = &ctx->containers[containerIndex];

    const TextKit2LineFragmentSlice *sl = &fragment->slices[sliceIndex];
    double localCaretX = sl->startX + localSliceOffset;
    double localCaretY = fragment->lineY;

    ctx->activeCaretRectLocal = CGRectMake(localCaretX, localCaretY, 2.0, fragment->lineHeight);

    double globalCaretX = tc->containerOrigin.x + localCaretX;
    double globalCaretY = tc->containerOrigin.y + localCaretY;

    CGPoint target;
    target.x = globalCaretX - safetyPadding;
    target.y = globalCaretY - safetyPadding;
    if (target.x < 0.0) target.x = 0.0;
    if (target.y < 0.0) target.y = 0.0;
    ctx->projectedViewportTarget = target;
    return target;
}

/* ========================================================================= */
/* 5. UICollectionView / UITableView Prefetching Engine & Snapping           */
/* ========================================================================= */

typedef struct _UICollectionViewPrefetchingContext {
    double currentScrollVelocity;
    double lookaheadWindow;
    double minRatio;       /* 1.5 */
    double maxRatio;       /* 4.0 */
    double leadTimeSec;    /* 0.25 s */
    double ballisticCancellationVelocity; /* 3000.0 pt/s */
    uint32_t activePrefetchRequestsCount;
    bool isPrefetchCancelled;
} _UICollectionViewPrefetchingContext;

typedef struct CollectionViewPrefetchRange {
    double startY;
    double endY;
    double windowSize;
    int32_t scrollDirection; /* +1 = down, -1 = up, 0 = stationary */
    bool directionReversed;
    bool isCancelled;
} CollectionViewPrefetchRange;

static inline double collectionview_compute_lookahead_window(_UICollectionViewPrefetchingContext *ctx, double scrollVelocity, double viewportDimension) {
    ctx->currentScrollVelocity = scrollVelocity;
    double absVelocity = fabs(scrollVelocity);
    double minWindow = ctx->minRatio * viewportDimension;
    double maxWindow = ctx->maxRatio * viewportDimension;
    double velocityProportionalWindow = absVelocity * ctx->leadTimeSec;

    double window = velocityProportionalWindow;
    if (window < minWindow) window = minWindow;
    if (window > maxWindow) window = maxWindow;
    ctx->lookaheadWindow = window;

    if (absVelocity >= ctx->ballisticCancellationVelocity) {
        ctx->isPrefetchCancelled = true;
    } else {
        ctx->isPrefetchCancelled = false;
    }
    return window;
}

static inline CollectionViewPrefetchRange collectionview_compute_prefetch_range(
    _UICollectionViewPrefetchingContext *ctx,
    double scrollVelocity,
    double currentOffset,
    double viewportDimension
) {
    CollectionViewPrefetchRange range;
    range.isCancelled = false;
    range.directionReversed = false;

    /* Detect direction reversal (positive <-> negative with non-zero magnitude) */
    if ((ctx->currentScrollVelocity > 0.0 && scrollVelocity < 0.0) ||
        (ctx->currentScrollVelocity < 0.0 && scrollVelocity > 0.0)) {
        range.directionReversed = true;
    }

    double window = collectionview_compute_lookahead_window(ctx, scrollVelocity, viewportDimension);
    range.windowSize = window;

    /* Ballistic cancellation or direction reversal cancels existing prefetch tasks */
    if (ctx->isPrefetchCancelled || range.directionReversed) {
        ctx->isPrefetchCancelled = true;
        range.isCancelled = true;
    } else {
        range.isCancelled = false;
    }

    if (scrollVelocity > 0.0) {
        range.scrollDirection = 1;
        range.startY = currentOffset + viewportDimension;
        range.endY = currentOffset + viewportDimension + window;
    } else if (scrollVelocity < 0.0) {
        range.scrollDirection = -1;
        range.startY = currentOffset - window;
        range.endY = currentOffset;
    } else {
        range.scrollDirection = 0;
        range.startY = currentOffset;
        range.endY = currentOffset + viewportDimension;
    }

    return range;
}

typedef struct CellReusePool {
    int64_t items[16];
    uint32_t count;
    uint32_t totalAllocated;
    uint32_t totalReused;
} CellReusePool;

static inline void cell_reuse_pool_enqueue(CellReusePool *pool, int64_t itemID) {
    if (pool->count < 16) {
        pool->items[pool->count++] = itemID;
    }
}

static inline int64_t cell_reuse_pool_dequeue(CellReusePool *pool) {
    if (pool->count > 0) {
        pool->totalReused++;
        return pool->items[--pool->count];
    }
    pool->totalAllocated++;
    return -1; /* Allocate brand new cell */
}

typedef struct OrthogonalScrollerContext {
    CGPoint mainContentOffset;
    CGPoint sectionContentOffset;
    CGSize sectionContentSize;
    CGRect sectionBounds;
    bool isMainScrollerVertical;
} OrthogonalScrollerContext;

typedef enum OrthogonalGestureLockState {
    kOrthogonalLockNone        = 0,
    kOrthogonalLockVertical    = 1,
    kOrthogonalLockHorizontal  = 2
} OrthogonalGestureLockState;

static inline OrthogonalGestureLockState collectionview_orthogonal_gesture_resolve_lock(
    double deltaX, double deltaY,
    OrthogonalGestureLockState currentLock,
    double crossAxisDisplacement
) {
    double absX = fabs(deltaX);
    double absY = fabs(deltaY);

    /* If already locked, directional lock breaking requires 40.0pt cross-axis displacement (GEST-003, GEST-010) */
    if (currentLock == kOrthogonalLockHorizontal) {
        /* Currently locked to horizontal section */
        if (absY >= 1.7320508 * absX && crossAxisDisplacement >= 40.0) {
            return kOrthogonalLockVertical; /* Broke lock to main vertical */
        }
        return kOrthogonalLockHorizontal; /* Retain horizontal lock across indeterminate [30 deg, 60 deg] */
    }
    if (currentLock == kOrthogonalLockVertical) {
        /* Currently locked to main vertical scroller */
        if (absY <= 0.5773503 * absX && crossAxisDisplacement >= 40.0) {
            return kOrthogonalLockHorizontal; /* Broke lock to horizontal section */
        }
        return kOrthogonalLockVertical; /* Retain vertical lock across indeterminate [30 deg, 60 deg] */
    }

    /* Initial lock resolution (no lock yet established) */
    if (absY >= 1.7320508 * absX) {
        return kOrthogonalLockVertical;
    }
    if (absY <= 0.5773503 * absX) {
        return kOrthogonalLockHorizontal;
    }
    /* In indeterminate 45-degree zone during initial slop breach: default to main vertical scroller */
    return kOrthogonalLockVertical;
}

static inline bool collectionview_orthogonal_gesture_should_lock(double deltaX, double deltaY) {
    return collectionview_orthogonal_gesture_resolve_lock(deltaX, deltaY, kOrthogonalLockNone, 0.0) == kOrthogonalLockVertical;
}

/* ========================================================================= */
/* 6. Accessibility & Hardware Keyboard Scrolling Mechanics                  */
/* ========================================================================= */

typedef enum UIAccessibilityScrollDirection {
    kAccessibilityScrollRight    = 1,
    kAccessibilityScrollLeft     = 2,
    kAccessibilityScrollUp       = 3,
    kAccessibilityScrollDown     = 4,
    kAccessibilityScrollNext     = 5,
    kAccessibilityScrollPrevious = 6
} UIAccessibilityScrollDirection;

typedef struct AccessibilityScrollViewState {
    CGPoint contentOffset;
    CGSize contentSize;
    UIEdgeInsets contentInsets;
    CGRect bounds;
    double pageTurnOverlapPt; /* 44.0 pt */
    double keyboardDiscreteStepPt; /* 40.0 pt */
} AccessibilityScrollViewState;

static inline bool accessibility_scroll_dispatch(AccessibilityScrollViewState *view, UIAccessibilityScrollDirection direction) {
    double minX = -view->contentInsets.left;
    double maxX = view->contentSize.width - view->bounds.size.width + view->contentInsets.right;
    double minY = -view->contentInsets.top;
    double maxY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
    if (maxX < minX) maxX = minX;
    if (maxY < minY) maxY = minY;

    double stepY = view->bounds.size.height - view->pageTurnOverlapPt;
    if (stepY <= 0.0) stepY = view->bounds.size.height;
    double stepX = view->bounds.size.width - view->pageTurnOverlapPt;
    if (stepX <= 0.0) stepX = view->bounds.size.width;

    CGPoint oldOffset = view->contentOffset;
    CGPoint newOffset = oldOffset;

    switch (direction) {
        case kAccessibilityScrollDown:
        case kAccessibilityScrollNext:
            newOffset.y += stepY;
            break;
        case kAccessibilityScrollUp:
        case kAccessibilityScrollPrevious:
            newOffset.y -= stepY;
            break;
        case kAccessibilityScrollRight:
            newOffset.x += stepX;
            break;
        case kAccessibilityScrollLeft:
            newOffset.x -= stepX;
            break;
        default:
            return false;
    }

    newOffset.x = clamp_double(newOffset.x, minX, maxX);
    newOffset.y = clamp_double(newOffset.y, minY, maxY);

    if (fabs(newOffset.x - oldOffset.x) < 0.5 && fabs(newOffset.y - oldOffset.y) < 0.5) {
        return false; /* Boundary reached: no scroll executed */
    }
    view->contentOffset = newOffset;
    return true;
}

typedef struct AccessibilityScrollStatus {
    uint32_t pageNumber;
    uint32_t totalPages;
    double scrollPercentage;
    char announcementString[64];
    bool boundaryFeedbackTriggered;
} AccessibilityScrollStatus;

static inline AccessibilityScrollStatus accessibility_compute_scroll_status(
    const AccessibilityScrollViewState *view,
    bool isDetentPaged
) {
    AccessibilityScrollStatus status;
    status.boundaryFeedbackTriggered = false;

    double minY = -view->contentInsets.top;
    double maxY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
    if (maxY < minY) maxY = minY;

    double totalRange = maxY - minY;
    if (totalRange <= 0.0) {
        status.scrollPercentage = 100.0;
    } else {
        status.scrollPercentage = clamp_double((view->contentOffset.y - minY) / totalRange * 100.0, 0.0, 100.0);
    }

    if (isDetentPaged) {
        double pageHeight = view->bounds.size.height - view->pageTurnOverlapPt;
        if (pageHeight <= 0.0) pageHeight = (view->bounds.size.height > 0.0) ? view->bounds.size.height : 1.0;

        double totalContentH = view->contentSize.height;
        uint32_t totalP = (uint32_t)ceil(totalContentH / pageHeight);
        if (totalP == 0) totalP = 1;

        double currentY = view->contentOffset.y + view->contentInsets.top;
        uint32_t currentP;
        if (view->contentOffset.y >= maxY - 0.5) {
            currentP = totalP; /* At bottom boundary, detent page is the final page */
        } else {
            currentP = (uint32_t)floor((currentY + 0.5 * pageHeight) / pageHeight) + 1;
        }
        if (currentP > totalP) currentP = totalP;
        if (currentP < 1) currentP = 1;

        status.pageNumber = currentP;
        status.totalPages = totalP;
        snprintf(status.announcementString, sizeof(status.announcementString), "Page %u of %u", currentP, totalP);
    } else {
        status.pageNumber = 0;
        status.totalPages = 0;
        snprintf(status.announcementString, sizeof(status.announcementString), "%.0f percent", status.scrollPercentage);
    }

    return status;
}

static inline bool accessibility_scroll_dispatch_with_feedback(
    AccessibilityScrollViewState *view,
    UIAccessibilityScrollDirection direction,
    bool isDetentPaged,
    AccessibilityScrollStatus *outStatus
) {
    bool didScroll = accessibility_scroll_dispatch(view, direction);
    *outStatus = accessibility_compute_scroll_status(view, isDetentPaged);
    if (!didScroll) {
        outStatus->boundaryFeedbackTriggered = true;
    }
    return didScroll;
}

static inline void keyboard_scroll_arrow_step(AccessibilityScrollViewState *view, bool isVertical, bool isForward) {
    double step = view->keyboardDiscreteStepPt;
    if (!isForward) step = -step;

    if (isVertical) {
        double minY = -view->contentInsets.top;
        double maxY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
        if (maxY < minY) maxY = minY;
        view->contentOffset.y = clamp_double(view->contentOffset.y + step, minY, maxY);
    } else {
        double minX = -view->contentInsets.left;
        double maxX = view->contentSize.width - view->bounds.size.width + view->contentInsets.right;
        if (maxX < minX) maxX = minX;
        view->contentOffset.x = clamp_double(view->contentOffset.x + step, minX, maxX);
    }
}

static inline void keyboard_scroll_page_step(AccessibilityScrollViewState *view, bool isPageDown) {
    double step = view->bounds.size.height - view->keyboardDiscreteStepPt;
    if (step <= 0.0) step = view->bounds.size.height;
    if (!isPageDown) step = -step;

    double minY = -view->contentInsets.top;
    double maxY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
    if (maxY < minY) maxY = minY;
    view->contentOffset.y = clamp_double(view->contentOffset.y + step, minY, maxY);
}

static inline void keyboard_scroll_home_end_step(AccessibilityScrollViewState *view, bool isEnd) {
    double minY = -view->contentInsets.top;
    double maxY = view->contentSize.height - view->bounds.size.height + view->contentInsets.bottom;
    if (maxY < minY) maxY = minY;
    view->contentOffset.y = isEnd ? maxY : minY;
}

/* --- Hardware Magic Keyboard Key Repeat & Continuous Velocity Ramping Engine --- */

typedef struct KeyboardRepeatState {
    bool isKeyDown;
    bool isVertical;
    bool isForward;
    double initialDelaySec;        /* 0.400 s (400ms iOS default initial key repeat delay) */
    double repeatIntervalSec;      /* 0.0333 s (30Hz sustained key repeat rate) */
    double keyHeldDurationSec;     /* Total duration key has been continuously held */
    double timeSinceLastRepeatSec; /* Time accumulator for repeat intervals */
    uint32_t repeatCount;          /* Number of repeated step events fired */
    bool isContinuousRamping;      /* Active continuous velocity mode flag */
    double currentVelocity;        /* pt/s current velocity */
    double maxContinuousVelocity;  /* 2400.0 pt/s terminal keyboard scroll velocity */
    double accelerationRate;       /* 1600.0 pt/s^2 linear acceleration rate */
} KeyboardRepeatState;

static inline KeyboardRepeatState keyboard_repeat_init(void) {
    KeyboardRepeatState state;
    state.isKeyDown = false;
    state.isVertical = true;
    state.isForward = true;
    state.initialDelaySec = 0.400;        /* 400ms initial repeat delay */
    state.repeatIntervalSec = 1.0 / 30.0; /* 30Hz repeat rate */
    state.keyHeldDurationSec = 0.0;
    state.timeSinceLastRepeatSec = 0.0;
    state.repeatCount = 0;
    state.isContinuousRamping = false;
    state.currentVelocity = 0.0;
    state.maxContinuousVelocity = 2400.0; /* 2400 pt/s terminal cap */
    state.accelerationRate = 1600.0;      /* 1600 pt/s^2 */
    return state;
}

static inline void keyboard_repeat_key_down(
    KeyboardRepeatState *state,
    AccessibilityScrollViewState *view,
    bool isVertical,
    bool isForward
) {
    state->isKeyDown = true;
    state->isVertical = isVertical;
    state->isForward = isForward;
    state->keyHeldDurationSec = 0.0;
    state->timeSinceLastRepeatSec = 0.0;
    state->repeatCount = 0;
    state->isContinuousRamping = false;
    state->currentVelocity = 0.0;

    /* Immediate initial discrete step on key press */
    keyboard_scroll_arrow_step(view, isVertical, isForward);
}

static inline void keyboard_repeat_tick(
    KeyboardRepeatState *state,
    AccessibilityScrollViewState *view,
    double deltaSec
) {
    if (!state->isKeyDown) return;

    double prevHeld = state->keyHeldDurationSec;
    state->keyHeldDurationSec += deltaSec;

    /* Prior to initial delay expiration, no repeats trigger */
    if (state->keyHeldDurationSec < state->initialDelaySec) {
        return;
    }

    /* Calculate elapsed time after initial delay for repeat accumulator */
    if (prevHeld < state->initialDelaySec) {
        /* Transitioned across initial delay threshold in this tick */
        state->timeSinceLastRepeatSec += (state->keyHeldDurationSec - state->initialDelaySec);
    } else {
        /* Already beyond initial delay */
        state->timeSinceLastRepeatSec += deltaSec;
    }

    /* Process all accumulated repeat ticks at the repeat interval with floating point epsilon */
    while (state->timeSinceLastRepeatSec >= state->repeatIntervalSec - 1e-7) {
        state->timeSinceLastRepeatSec -= state->repeatIntervalSec;
        if (state->timeSinceLastRepeatSec < 0.0) state->timeSinceLastRepeatSec = 0.0;
        state->repeatCount++;

        /* After >= 3 repeated ticks, transition to continuous velocity ramping */
        if (state->repeatCount >= 3) {
            state->isContinuousRamping = true;
        }

        keyboard_scroll_arrow_step(view, state->isVertical, state->isForward);
    }

    if (state->isContinuousRamping) {
        double activeHeldTime = state->keyHeldDurationSec - state->initialDelaySec;
        double baseVel = view->keyboardDiscreteStepPt / state->repeatIntervalSec; /* 40 / (1/30) = 1200.0 pt/s */
        double v = baseVel + state->accelerationRate * activeHeldTime;
        if (v > state->maxContinuousVelocity) {
            v = state->maxContinuousVelocity;
        }
        state->currentVelocity = v;
    }
}

static inline void keyboard_repeat_key_up(KeyboardRepeatState *state) {
    state->isKeyDown = false;
    state->isContinuousRamping = false;
    state->currentVelocity = 0.0;
    state->keyHeldDurationSec = 0.0;
    state->timeSinceLastRepeatSec = 0.0;
}

/* ========================================================================= */
/* 7. Comprehensive Unit Assertion Suites (38 Suites)                        */
/* ========================================================================= */

static void test_suite_01_swiftui_scroll_position_init(void) {
    SwiftUI_ScrollPosition posPt = swiftui_scroll_position_init_point(CGPointMake(120.0, 340.0));
    assert(posPt.targetType == kScrollPositionTargetPoint);
    assert(posPt.pointValue.x == 120.0 && posPt.pointValue.y == 340.0);
    assert(posPt.isPositioned == true);

    SwiftUI_ScrollPosition posEdge = swiftui_scroll_position_init_edge(kScrollEdgeBottom);
    assert(posEdge.targetType == kScrollPositionTargetEdge);
    assert(posEdge.edgeValue == kScrollEdgeBottom);
    assert(posEdge.isPositioned == true);

    UnitPoint anchor = { 0.5, 0.5 };
    SwiftUI_ScrollPosition posID = swiftui_scroll_position_init_id(42, anchor);
    assert(posID.targetType == kScrollPositionTargetID);
    assert(posID.targetID == 42);
    assert(posID.anchor.x == 0.5 && posID.anchor.y == 0.5);
    printf("  [PASS] Suite 01: SwiftUI ScrollPosition Initializers\n");
}

static void test_suite_02_swiftui_bridge_target_offset(void) {
    CGSize contentSize = CGSizeMake(393.0, 2000.0);
    CGSize boundsSize = CGSizeMake(393.0, 852.0);
    UnitPoint anchorCenter = { 0.5, 0.5 };
    CGPoint itemOrigin = CGPointMake(0.0, 1000.0);
    CGSize itemSize = CGSizeMake(393.0, 100.0);

    CGPoint target = swiftui_bridge_calculate_target_offset(contentSize, boundsSize, anchorCenter, itemOrigin, itemSize);
    /* target.y = 1000 - 0.5 * (852 - 100) = 1000 - 376 = 624.0 */
    assert(fabs(target.y - 624.0) < 1e-6);
    assert(target.x == 0.0);
    printf("  [PASS] Suite 02: SwiftUI Bridge Anchor Target Calculation\n");
}

static void test_suite_03_swiftui_scroll_geometry(void) {
    _UIHostingScrollView view;
    view.contentOffset = CGPointMake(0.0, 450.0);
    view.contentSize = CGSizeMake(393.0, 3000.0);
    view.contentInsets = UIEdgeInsetsMake(59.0, 0.0, 34.0, 0.0);
    view.bounds = CGRectMake(0.0, 450.0, 393.0, 852.0);

    SwiftUICore_ScrollGeometry geom = swiftui_hosting_scroll_view_get_geometry(&view);
    assert(geom.contentOffset.y == 450.0);
    assert(geom.contentSize.height == 3000.0);
    assert(geom.contentInsets.top == 59.0);
    assert(geom.boundsSize.height == 852.0);
    printf("  [PASS] Suite 03: SwiftUICore ScrollGeometry Extraction\n");
}

static void test_suite_04_swiftui_scroll_phase_transitions(void) {
    _UIHostingScrollView view;
    view.isDragging = false;
    view.isDecelerating = false;
    view.programmaticScrollAnimating = false;
    assert(swiftui_hosting_scroll_view_get_phase(&view) == kScrollPhaseIdle);

    view.isDragging = true;
    assert(swiftui_hosting_scroll_view_get_phase(&view) == kScrollPhaseInteracting);

    view.isDragging = false;
    view.isDecelerating = true;
    assert(swiftui_hosting_scroll_view_get_phase(&view) == kScrollPhaseDecelerating);

    view.isDecelerating = false;
    view.programmaticScrollAnimating = true;
    assert(swiftui_hosting_scroll_view_get_phase(&view) == kScrollPhaseAnimating);
    printf("  [PASS] Suite 04: SwiftUI ScrollPhase State Mapping\n");
}

static void test_suite_05_swiftui_echo_suppression(void) {
    _UIHostingScrollView view;
    view.contentOffset = CGPointMake(0.0, 0.0);
    view.isProgrammaticUpdate = false;
    view.echoSuppressionCounter = 0;
    view.programmaticScrollAnimating = false;

    swiftui_hosting_scroll_view_set_content_offset(&view, CGPointMake(0.0, 500.0), true, true);
    assert(view.contentOffset.y == 500.0);
    assert(view.isProgrammaticUpdate == true);
    assert(view.echoSuppressionCounter == 1);
    assert(view.programmaticScrollAnimating == true);
    printf("  [PASS] Suite 05: SwiftUI Programmatic Echo Suppression\n");
}

static void test_suite_06_swiftui_gesture_arbitration(void) {
    assert(swiftui_gesture_should_recognize_simultaneously(true, false) == true);
    assert(swiftui_gesture_should_recognize_simultaneously(false, true) == false);
    assert(swiftui_gesture_should_recognize_simultaneously(false, false) == false);
    printf("  [PASS] Suite 06: SwiftUI Gesture Priority Arbitration\n");
}

static void test_suite_07_webkit_split_delegate(void) {
    WKScrollView wkView;
    wkView.contentOffset = CGPointMake(0.0, 0.0);
    wkView.internalDelegateCallbacksCount = 0;
    wkView.externalDelegateCallbacksCount = 0;

    webkit_scroll_view_set_content_offset(&wkView, CGPointMake(0.0, 320.0));
    assert(wkView.contentOffset.y == 320.0);
    assert(wkView.internalDelegateCallbacksCount == 1);
    assert(wkView.externalDelegateCallbacksCount == 1);
    assert(wkView.scrollingNode.layerTransformOffset.y == -320.0);
    printf("  [PASS] Suite 07: WebKit WKScrollView Split Delegate Routing\n");
}

static void test_suite_08_webkit_scrolling_tree_layer_transform(void) {
    ScrollingTreeScrollingNodeIOS node;
    node.nodeID = 1001;
    node.currentPosition = CGPointMake(0.0, 0.0);
    node.hasPendingCommit = false;

    webkit_scrolling_tree_apply_async_transform(&node, CGPointMake(150.0, 450.0));
    assert(node.currentPosition.x == 150.0 && node.currentPosition.y == 450.0);
    assert(node.layerTransformOffset.x == -150.0 && node.layerTransformOffset.y == -450.0);
    assert(node.hasPendingCommit == true);
    printf("  [PASS] Suite 08: WebKit Async Scrolling Tree Layer Transform\n");
}

static void test_suite_09_webkit_overscroll_behavior_auto(void) {
    double dimension = 852.0;
    double offset = -100.0;
    double disp = webkit_compute_rubber_band_displacement(kOverscrollBehaviorAuto, offset, 0.0, 1000.0, dimension);
    /* With c = 0.55: |x|*c/d = 100*0.55/852 = 55/852 ~ 0.064554 */
    /* f(x) = (1 - 1/(1 + 0.064554))*852 = (1 - 0.93936)*852 ~ 51.66 pt */
    assert(disp < 0.0);
    assert(fabs(fabs(disp) - 51.66) < 1.0);
    printf("  [PASS] Suite 09: WebKit Overscroll Behavior Auto (Rubber-Band Active)\n");
}

static void test_suite_10_webkit_overscroll_behavior_contain(void) {
    double dimension = 852.0;
    double offset = 1100.0;
    double disp = webkit_compute_rubber_band_displacement(kOverscrollBehaviorContain, offset, 0.0, 1000.0, dimension);
    assert(disp > 0.0);
    assert(fabs(disp - 51.66) < 1.0);
    printf("  [PASS] Suite 10: WebKit Overscroll Behavior Contain (Local Bounce Only)\n");
}

static void test_suite_11_webkit_overscroll_behavior_none(void) {
    double dimension = 852.0;
    double offset = -100.0;
    double disp = webkit_compute_rubber_band_displacement(kOverscrollBehaviorNone, offset, 0.0, 1000.0, dimension);
    assert(disp == 0.0);
    printf("  [PASS] Suite 11: WebKit Overscroll Behavior None (Zero Rubber-Band)\n");
}

static void test_suite_12_webkit_passive_wheel_listener(void) {
    WebKitWheelEventQueue queue;
    queue.isAsyncDispatchImmediate = false;
    queue.activeListenerBlocked = true;
    queue.timeoutAccumulatorMs = 0.0;
    queue.coalescedEventsCount = 0;

    webkit_wheel_event_process(&queue, true, 8.33);
    assert(queue.isAsyncDispatchImmediate == true);
    assert(queue.activeListenerBlocked == false);
    assert(queue.coalescedEventsCount == 1);
    printf("  [PASS] Suite 12: WebKit Passive Wheel Listener Immediate Dispatch\n");
}

static void test_suite_13_webkit_active_wheel_timeout(void) {
    WebKitWheelEventQueue queue;
    queue.isAsyncDispatchImmediate = false;
    queue.activeListenerBlocked = false;
    queue.timeoutAccumulatorMs = 0.0;
    queue.coalescedEventsCount = 0;

    /* First 50ms: remains blocked */
    webkit_wheel_event_process(&queue, false, 50.0);
    assert(queue.activeListenerBlocked == true);
    assert(queue.isAsyncDispatchImmediate == false);

    /* Another 55ms: total 105ms >= 100ms threshold -> drops block and resumes async */
    webkit_wheel_event_process(&queue, false, 55.0);
    assert(queue.activeListenerBlocked == false);
    assert(queue.isAsyncDispatchImmediate == true);
    printf("  [PASS] Suite 13: WebKit Active Wheel Listener Timeout Fallback\n");
}

static void test_suite_14_textview_cursor_auto_scroll_within_bounds(void) {
    UITextViewContext tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 2000.0);
    tv.contentInsets = UIEdgeInsetsMake(20.0, 0.0, 20.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 600.0);
    tv.caretSafetyMargin = 8.0;

    CGRect inBoundsCaret = CGRectMake(20.0, 150.0, 2.0, 20.0);
    bool didScroll = textview_cursor_auto_scroll(&tv, inBoundsCaret);
    assert(didScroll == false);
    assert(tv.contentOffset.y == 0.0);
    printf("  [PASS] Suite 14: UITextView Caret Within Bounds (No Auto-Scroll)\n");
}

static void test_suite_15_textview_cursor_auto_scroll_below_bounds(void) {
    UITextViewContext tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 2000.0);
    tv.contentInsets = UIEdgeInsetsMake(20.0, 0.0, 20.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 600.0);
    tv.caretSafetyMargin = 8.0;

    CGRect outBoundsCaret = CGRectMake(20.0, 620.0, 2.0, 20.0);
    bool didScroll = textview_cursor_auto_scroll(&tv, outBoundsCaret);
    assert(didScroll == true);
    /* target = 620 + 20 + 8 - 600 + 20 = 68.0 */
    assert(tv.contentOffset.y == 68.0);
    printf("  [PASS] Suite 15: UITextView Caret Below Bounds Auto-Scroll\n");
}

static void test_suite_16_textview_selection_drag_velocity_ramping(void) {
    UITextViewContext tv;
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.edgeProximityBandDepth = 44.0;
    tv.maxAutoScrollVelocity = 1400.0;
    tv.velocityRampingExponent = 2.0;

    bool scrollDown = false;
    /* Touch at 22pt from top: dist = 22, ratio = (44 - 22)/44 = 0.5. v = 1400 * 0.5^2 = 350.0 */
    double vTopHalf = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, 22.0), &scrollDown);
    assert(scrollDown == false);
    assert(fabs(vTopHalf - 350.0) < 1e-6);

    /* Touch at 0pt (extreme top edge): dist = 0, ratio = 1.0. v = 1400.0 */
    double vTopEdge = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, 0.0), &scrollDown);
    assert(vTopEdge == 1400.0);
    printf("  [PASS] Suite 16: UITextView Quadratic Drag Velocity Ramping\n");
}

static void test_suite_17_textview_selection_drag_outside_clamp(void) {
    UITextViewContext tv;
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.edgeProximityBandDepth = 44.0;
    tv.maxAutoScrollVelocity = 1400.0;
    tv.velocityRampingExponent = 2.0;

    bool scrollDown = false;
    /* Touch beyond top boundary (-15.0 pt): must clamp to vMax */
    double vOutside = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, -15.0), &scrollDown);
    assert(scrollDown == false);
    assert(vOutside == 1400.0);
    printf("  [PASS] Suite 17: UITextView Selection Drag Outside Edge Clamping\n");
}

static void test_suite_18_textview_selection_drag_center_inactive(void) {
    UITextViewContext tv;
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.edgeProximityBandDepth = 44.0;
    tv.maxAutoScrollVelocity = 1400.0;
    tv.velocityRampingExponent = 2.0;

    bool scrollDown = false;
    double vCenter = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, 400.0), &scrollDown);
    assert(vCenter == 0.0);
    printf("  [PASS] Suite 18: UITextView Selection Drag Inactive in Viewport Center\n");
}

static void test_suite_19_collectionview_prefetch_min_window(void) {
    _UICollectionViewPrefetchingContext ctx;
    ctx.minRatio = 1.5;
    ctx.maxRatio = 4.0;
    ctx.leadTimeSec = 0.25;
    ctx.ballisticCancellationVelocity = 3000.0;

    double viewportH = 800.0;
    /* Slow scroll: 100 pt/s -> |v| * 0.25 = 25 pt < 1.5 * 800 (1200 pt). Window must clamp to 1200 pt */
    double w = collectionview_compute_lookahead_window(&ctx, 100.0, viewportH);
    assert(w == 1200.0);
    assert(ctx.isPrefetchCancelled == false);
    printf("  [PASS] Suite 19: UICollectionView Prefetch Minimum Lookahead Clamp\n");
}

static void test_suite_20_collectionview_prefetch_velocity_proportional(void) {
    _UICollectionViewPrefetchingContext ctx;
    ctx.minRatio = 1.5;
    ctx.maxRatio = 4.0;
    ctx.leadTimeSec = 0.25;
    ctx.ballisticCancellationVelocity = 3000.0;

    double viewportH = 800.0;
    /* Moderate scroll: 6000 pt/s * 0.25 = 1500 pt -> within [1200, 3200] */
    double w = collectionview_compute_lookahead_window(&ctx, 6000.0, viewportH);
    assert(w == 1500.0);
    assert(ctx.isPrefetchCancelled == true); /* >= 3000 cancels background loads */
    printf("  [PASS] Suite 20: UICollectionView Prefetch Velocity Proportional Window\n");
}

static void test_suite_21_collectionview_prefetch_max_clamp(void) {
    _UICollectionViewPrefetchingContext ctx;
    ctx.minRatio = 1.5;
    ctx.maxRatio = 4.0;
    ctx.leadTimeSec = 0.25;
    ctx.ballisticCancellationVelocity = 3000.0;

    double viewportH = 800.0;
    /* Extreme velocity: 20000 pt/s * 0.25 = 5000 pt > 4.0 * 800 (3200 pt). Clamps to 3200 pt */
    double w = collectionview_compute_lookahead_window(&ctx, 20000.0, viewportH);
    assert(w == 3200.0);
    assert(ctx.isPrefetchCancelled == true);
    printf("  [PASS] Suite 21: UICollectionView Prefetch Maximum Lookahead Clamp\n");
}

static void test_suite_22_collectionview_reuse_pool_recycling(void) {
    CellReusePool pool;
    pool.count = 0;
    pool.totalAllocated = 0;
    pool.totalReused = 0;

    /* First dequeue on empty pool triggers new allocation */
    int64_t c1 = cell_reuse_pool_dequeue(&pool);
    assert(c1 == -1);
    assert(pool.totalAllocated == 1);

    /* Enqueue recycled cell */
    cell_reuse_pool_enqueue(&pool, 101);
    assert(pool.count == 1);

    /* Next dequeue reuses cell 101 */
    int64_t c2 = cell_reuse_pool_dequeue(&pool);
    assert(c2 == 101);
    assert(pool.totalReused == 1);
    assert(pool.count == 0);
    printf("  [PASS] Suite 22: UICollectionView Cell Reuse Pool Recycling\n");
}

static void test_suite_23_collectionview_orthogonal_gesture_locking(void) {
    /* Pure vertical drag: deltaX = 5, deltaY = 50 -> 50 >= 1.732 * 5 (8.66) -> vertical lock */
    assert(collectionview_orthogonal_gesture_should_lock(5.0, 50.0) == true);

    /* Pure horizontal drag: deltaX = 50, deltaY = 5 -> 5 <= 0.577 * 50 (28.8) -> horizontal lock */
    assert(collectionview_orthogonal_gesture_should_lock(50.0, 5.0) == false);
    printf("  [PASS] Suite 23: UICollectionView Orthogonal Gesture Directional Locking\n");
}

static void test_suite_24_accessibility_scroll_directions(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 500.0);
    tv.contentSize = CGSizeMake(393.0, 3000.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.pageTurnOverlapPt = 44.0;

    /* Down / Next scroll: offset increases by (800 - 44) = 756 pt */
    bool okDown = accessibility_scroll_dispatch(&tv, kAccessibilityScrollDown);
    assert(okDown == true);
    assert(tv.contentOffset.y == 1256.0);

    /* Up / Previous scroll: offset decreases by 756 pt */
    bool okUp = accessibility_scroll_dispatch(&tv, kAccessibilityScrollUp);
    assert(okUp == true);
    assert(tv.contentOffset.y == 500.0);
    printf("  [PASS] Suite 24: Accessibility VoiceOver Scroll Direction Routing\n");
}

static void test_suite_25_accessibility_scroll_boundary_rejection(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 1000.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 1000.0);
    tv.pageTurnOverlapPt = 44.0;

    /* Viewport matches content size: scrolling up or down must return false */
    bool okUp = accessibility_scroll_dispatch(&tv, kAccessibilityScrollUp);
    assert(okUp == false);
    assert(tv.contentOffset.y == 0.0);

    bool okDown = accessibility_scroll_dispatch(&tv, kAccessibilityScrollDown);
    assert(okDown == false);
    assert(tv.contentOffset.y == 0.0);
    printf("  [PASS] Suite 25: Accessibility Scroll Boundary Rejection\n");
}

static void test_suite_26_keyboard_arrow_stepping(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 100.0);
    tv.contentSize = CGSizeMake(393.0, 2000.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.keyboardDiscreteStepPt = 40.0;

    /* Arrow down: +40 pt */
    keyboard_scroll_arrow_step(&tv, true, true);
    assert(tv.contentOffset.y == 140.0);

    /* Arrow up: -40 pt */
    keyboard_scroll_arrow_step(&tv, true, false);
    assert(tv.contentOffset.y == 100.0);
    printf("  [PASS] Suite 26: Hardware Keyboard Arrow Key Discrete Stepping\n");
}

static void test_suite_27_keyboard_page_stepping(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 3000.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.keyboardDiscreteStepPt = 40.0;

    /* Page Down: +(800 - 40) = +760 pt */
    keyboard_scroll_page_step(&tv, true);
    assert(tv.contentOffset.y == 760.0);

    /* Page Up: -760 pt */
    keyboard_scroll_page_step(&tv, false);
    assert(tv.contentOffset.y == 0.0);
    printf("  [PASS] Suite 27: Hardware Keyboard Page Up / Page Down Viewport Stepping\n");
}

static void test_suite_28_keyboard_home_end_jump(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 500.0);
    tv.contentSize = CGSizeMake(393.0, 3000.0);
    tv.contentInsets = UIEdgeInsetsMake(20.0, 0.0, 30.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.keyboardDiscreteStepPt = 40.0;

    /* End jump: maxY = 3000 - 800 + 30 = 2230.0 */
    keyboard_scroll_home_end_step(&tv, true);
    assert(tv.contentOffset.y == 2230.0);

    /* Home jump: minY = -20.0 */
    keyboard_scroll_home_end_step(&tv, false);
    assert(tv.contentOffset.y == -20.0);
    printf("  [PASS] Suite 28: Hardware Keyboard Home / End Boundary Jump\n");
}

static void test_suite_29_webkit_tile_cache_memory_pressure(void) {
    WebCoreTileController tc;
    tc.tileCount = 3;
    tc.memoryPressureWarningLevel = 0;
    tc.totalPurgedTiles = 0;
    tc.fallbackCheckerboardFrames = 0;

    /* Tile 0: visible in active viewport */
    tc.tiles[0].tileID = 100;
    tc.tiles[0].tileRect = CGRectMake(0, 0, 393, 256);
    tc.tiles[0].purgeState = kTilePurgeStateNone;
    tc.tiles[0].isVisibleInViewport = true;
    tc.tiles[0].isPreloadCoverage = false;

    /* Tile 1: secondary preload coverage (not currently visible) */
    tc.tiles[1].tileID = 101;
    tc.tiles[1].tileRect = CGRectMake(0, 256, 393, 256);
    tc.tiles[1].purgeState = kTilePurgeStateNone;
    tc.tiles[1].isVisibleInViewport = false;
    tc.tiles[1].isPreloadCoverage = true;

    /* Tile 2: distant tile (not visible) */
    tc.tiles[2].tileID = 102;
    tc.tiles[2].tileRect = CGRectMake(0, 512, 393, 256);
    tc.tiles[2].purgeState = kTilePurgeStateNone;
    tc.tiles[2].isVisibleInViewport = false;
    tc.tiles[2].isPreloadCoverage = false;

    /* Moderate memory pressure (level 1) -> secondary tiles marked volatile */
    webkit_tile_controller_handle_memory_pressure(&tc, 1);
    assert(tc.tiles[0].purgeState == kTilePurgeStateNone);
    assert(tc.tiles[1].purgeState == kTilePurgeStateVolatile);
    assert(webkit_scrolling_tree_render_tile(&tc, 0) == true);
    assert(webkit_scrolling_tree_render_tile(&tc, 1) == true);

    /* Critical OOM memory pressure (level 2) -> non-visible tiles purged */
    webkit_tile_controller_handle_memory_pressure(&tc, 2);
    assert(tc.tiles[0].purgeState == kTilePurgeStateNone); /* Visible preserved */
    assert(tc.tiles[1].purgeState == kTilePurgeStatePurged);
    assert(tc.tiles[2].purgeState == kTilePurgeStatePurged);
    assert(tc.totalPurgedTiles == 2);
    assert(webkit_scrolling_tree_render_tile(&tc, 0) == true);
    assert(webkit_scrolling_tree_render_tile(&tc, 1) == false); /* Fallback checkerboard */
    printf("  [PASS] Suite 29: WebCore Tile Cache OOM Eviction & UIProcess Checkerboard Fallback\n");
}

static void test_suite_30_textkit2_multi_container_caret_projection(void) {
    TextKit2MultiContainerContext ctx;
    ctx.containerCount = 2;
    ctx.activeContainerIndex = 0;

    /* Container 0: Column 1 at origin (0, 0), size (190, 800) */
    ctx.containers[0].containerIndex = 0;
    ctx.containers[0].containerOrigin = CGPointMake(0.0, 0.0);
    ctx.containers[0].containerSize = CGSizeMake(190.0, 800.0);
    ctx.containers[0].containerInsets = UIEdgeInsetsMake(10.0, 10.0, 10.0, 10.0);

    /* Container 1: Column 2 at origin (200, 0), size (190, 800) */
    ctx.containers[1].containerIndex = 1;
    ctx.containers[1].containerOrigin = CGPointMake(200.0, 0.0);
    ctx.containers[1].containerSize = CGSizeMake(190.0, 800.0);
    ctx.containers[1].containerInsets = UIEdgeInsetsMake(10.0, 10.0, 10.0, 10.0);

    /* Caret inside container 0 at (20, 150) */
    CGRect localCaret0 = CGRectMake(20.0, 150.0, 2.0, 18.0);
    CGPoint target0 = textkit2_project_caret_to_viewport(&ctx, 0, localCaret0, 8.0);
    assert(fabs(target0.x - 12.0) < 1e-6); /* 0 + 20 - 8 */
    assert(fabs(target0.y - 142.0) < 1e-6); /* 0 + 150 - 8 */

    /* Caret transitions to container 1 at (30, 200) */
    CGRect localCaret1 = CGRectMake(30.0, 200.0, 2.0, 18.0);
    CGPoint target1 = textkit2_project_caret_to_viewport(&ctx, 1, localCaret1, 8.0);
    assert(fabs(target1.x - 222.0) < 1e-6); /* 200 + 30 - 8 */
    assert(fabs(target1.y - 192.0) < 1e-6); /* 0 + 200 - 8 */
    printf("  [PASS] Suite 30: TextKit 2 Multi-Container Caret Coordinate Projection\n");
}

static void test_suite_31_collectionview_orthogonal_45deg_hysteresis(void) {
    /* 1. Established Horizontal Lock: 45-degree diagonal movement retains horizontal lock */
    OrthogonalGestureLockState lock = collectionview_orthogonal_gesture_resolve_lock(
        20.0, 20.0, kOrthogonalLockHorizontal, 10.0 /* cross-axis < 40.0pt */
    );
    assert(lock == kOrthogonalLockHorizontal);

    /* 2. Established Vertical Lock: 45-degree diagonal movement retains vertical lock */
    lock = collectionview_orthogonal_gesture_resolve_lock(
        20.0, 20.0, kOrthogonalLockVertical, 10.0 /* cross-axis < 40.0pt */
    );
    assert(lock == kOrthogonalLockVertical);

    /* 3. Horizontal lock broken by strong vertical motion with cross-axis displacement >= 40.0pt */
    lock = collectionview_orthogonal_gesture_resolve_lock(
        5.0, 50.0, kOrthogonalLockHorizontal, 45.0 /* cross-axis >= 40.0pt */
    );
    assert(lock == kOrthogonalLockVertical);

    /* 4. Horizontal lock NOT broken if vertical angle met but cross-axis displacement < 40.0pt */
    lock = collectionview_orthogonal_gesture_resolve_lock(
        5.0, 50.0, kOrthogonalLockHorizontal, 25.0 /* cross-axis < 40.0pt */
    );
    assert(lock == kOrthogonalLockHorizontal);

    printf("  [PASS] Suite 31: UICollectionView Orthogonal 45-Degree Gesture Hysteresis & Lock Breaking\n");
}

static void test_suite_32_textview_narrow_viewport_drag_velocity_normalization(void) {
    UITextViewContext tv;
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 60.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.edgeProximityBandDepth = 44.0;
    tv.maxAutoScrollVelocity = 1400.0;
    tv.velocityRampingExponent = 2.0;

    bool scrollDown = false;
    /* In a 60pt viewport, dEdge is clamped to 30.0pt (half viewport). */
    /* Touch at y = 35.0pt is in bottom half (> 30.0pt). Must scroll DOWN. */
    double vBottom = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, 35.0), &scrollDown);
    assert(scrollDown == true);
    /* dist = 60 - 35 = 25pt. ratio = (30 - 25)/30 = 5/30 = 1/6. v = 1400 * (1/36) ~ 38.89 */
    assert(fabs(vBottom - (1400.0 / 36.0)) < 1e-4);

    /* Touch at y = 25.0pt is in top half (< 30.0pt). Must scroll UP. */
    double vTop = textview_calculate_selection_drag_velocity(&tv, CGPointMake(200.0, 25.0), &scrollDown);
    assert(scrollDown == false);
    assert(fabs(vTop - (1400.0 / 36.0)) < 1e-4);

    printf("  [PASS] Suite 32: UITextView Narrow Viewport Drag Velocity Normalization\n");
}

static void test_suite_33_textview_selection_drag_2d_velocity(void) {
    UITextViewContext tv;
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.edgeProximityBandDepth = 44.0;
    tv.maxAutoScrollVelocity = 1400.0;
    tv.velocityRampingExponent = 2.0;

    /* Touch at top-right corner: x = 371.0 (22pt from right edge), y = 22.0 (22pt from top edge) */
    TextDragVelocity2D vel = textview_calculate_selection_drag_velocity_2d(&tv, CGPointMake(371.0, 22.0));
    assert(vel.isScrollingX == true);
    assert(vel.isScrollingY == true);
    /* vy = -350.0 pt/s (scroll up), vx = +350.0 pt/s (scroll right) */
    assert(fabs(vel.vy - (-350.0)) < 1e-4);
    assert(fabs(vel.vx - 350.0) < 1e-4);

    printf("  [PASS] Suite 33: UITextView Selection Drag 2D Velocity Vector Ramping\n");
}

static void test_suite_34_collectionview_prefetch_directional_interval_and_reversal(void) {
    _UICollectionViewPrefetchingContext ctx;
    ctx.minRatio = 1.5;
    ctx.maxRatio = 4.0;
    ctx.leadTimeSec = 0.25;
    ctx.ballisticCancellationVelocity = 3000.0;
    ctx.currentScrollVelocity = 0.0;
    ctx.isPrefetchCancelled = false;

    double viewportH = 800.0;
    double currentOffset = 1000.0;

    /* 1. Forward scroll down: v = +1600 pt/s -> window = 1200 pt (min clamp) */
    CollectionViewPrefetchRange rDown = collectionview_compute_prefetch_range(&ctx, 1600.0, currentOffset, viewportH);
    assert(rDown.scrollDirection == 1);
    assert(rDown.directionReversed == false);
    assert(rDown.isCancelled == false);
    assert(rDown.startY == 1800.0); /* 1000 + 800 */
    assert(rDown.endY == 3000.0);   /* 1800 + 1200 */

    /* 2. Sudden gesture reversal upward: v = -1200 pt/s */
    CollectionViewPrefetchRange rUp = collectionview_compute_prefetch_range(&ctx, -1200.0, currentOffset, viewportH);
    assert(rUp.scrollDirection == -1);
    assert(rUp.directionReversed == true); /* Direction reversal detected */
    assert(rUp.isCancelled == true);       /* In-flight forward prefetch cancelled */
    assert(rUp.startY == -200.0);          /* 1000 - 1200 */
    assert(rUp.endY == 1000.0);

    printf("  [PASS] Suite 34: UICollectionView Directional Prefetch Interval & Reversal Invalidation\n");
}

static void test_suite_35_textkit2_exclusion_path_fragment_slicing(void) {
    TextKit2MultiContainerContext ctx;
    ctx.containerCount = 1;
    ctx.containers[0].containerIndex = 0;
    ctx.containers[0].containerOrigin = CGPointMake(50.0, 100.0);
    ctx.containers[0].containerSize = CGSizeMake(300.0, 800.0);
    ctx.containers[0].containerInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);

    TextKit2ExclusionObstacle obst;
    obst.center = CGPointMake(150.0, 200.0);
    obst.radius = 50.0;
    obst.isActive = true;

    TextKit2LineFragment frag;
    textkit2_compute_line_fragment_slices(300.0, 200.0, 20.0, &obst, 10.0, &frag);
    /* dy = |210 - 200| = 10. effR = 60. dx = sqrt(3600 - 100) = sqrt(3500) ~ 59.16 */
    /* obstLeft = 150 - 59.16 = 90.84. obstRight = 150 + 59.16 = 209.16 */
    assert(frag.sliceCount == 2);
    assert(fabs(frag.slices[0].startX - 0.0) < 1e-4);
    assert(fabs(frag.slices[0].width - 90.8392) < 1e-3);
    assert(fabs(frag.slices[1].startX - 209.1608) < 1e-3);

    /* Project caret within Slice 1 at local offset 15.0pt */
    CGPoint target = textkit2_project_caret_with_exclusion(&ctx, 0, &frag, 1, 15.0, 8.0);
    /* localCaretX = 209.1608 + 15.0 = 224.1608 */
    /* globalCaretX = 50.0 + 224.1608 = 274.1608. target.x = 274.1608 - 8 = 266.1608 */
    assert(fabs(target.x - 266.1608) < 1e-3);
    /* localCaretY = 200.0. globalCaretY = 100 + 200 = 300. target.y = 300 - 8 = 292.0 */
    assert(fabs(target.y - 292.0) < 1e-4);

    printf("  [PASS] Suite 35: TextKit 2 Exclusion Path Line Fragment Slicing\n");
}

static void test_suite_36_accessibility_detent_scroll_status_and_boundary_feedback(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 3200.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.pageTurnOverlapPt = 44.0;
    tv.keyboardDiscreteStepPt = 40.0;

    AccessibilityScrollStatus status;
    /* Step 1: Forward scroll from page 1 */
    bool ok1 = accessibility_scroll_dispatch_with_feedback(&tv, kAccessibilityScrollDown, true, &status);
    assert(ok1 == true);
    assert(status.pageNumber == 2);
    assert(status.totalPages == 5);
    assert(strcmp(status.announcementString, "Page 2 of 5") == 0);
    assert(status.boundaryFeedbackTriggered == false);

    /* Advance to end (3200 - 800 = 2400 max offset) */
    tv.contentOffset.y = 2400.0;
    bool okBoundary = accessibility_scroll_dispatch_with_feedback(&tv, kAccessibilityScrollDown, true, &status);
    assert(okBoundary == false); /* Boundary hit */
    assert(status.boundaryFeedbackTriggered == true); /* Auditory/haptic feedback alert triggered */
    assert(status.pageNumber == 5);

    printf("  [PASS] Suite 36: Accessibility Detent Status Announcements & Boundary Feedback\n");
}

static void test_suite_37_textkit2_multi_obstacle_boolean_slicing(void) {
    /* Scenario 1: Two overlapping obstacles intersecting the same line fragment */
    TextKit2ExclusionObstacle obstacles[2];
    /* Obstacle 0 at (150, 200), radius 50 + margin 10 = 60. On line y=190 (lineCenter = 200), dy=0 -> dx=60 -> [90, 210] */
    obstacles[0].center = CGPointMake(150.0, 200.0);
    obstacles[0].radius = 50.0;
    obstacles[0].isActive = true;

    /* Obstacle 1 at (190, 200), radius 40 + margin 10 = 50. On line y=190, dy=0 -> dx=50 -> [140, 240] */
    obstacles[1].center = CGPointMake(190.0, 200.0);
    obstacles[1].radius = 40.0;
    obstacles[1].isActive = true;

    TextKit2LineFragment fragOverlapping;
    textkit2_compute_line_fragment_slices_multi(400.0, 190.0, 20.0, obstacles, 2, 10.0, &fragOverlapping);
    /* dy = 0. Obs 0: [90, 210]. Obs 1: [140, 240]. Merged union: [90, 240] */
    /* Container width 400. Boolean difference: Slice 0: [0, 90], Slice 1: [240, 400] */
    assert(fragOverlapping.sliceCount == 2);
    assert(fabs(fragOverlapping.slices[0].startX - 0.0) < 1e-4);
    assert(fabs(fragOverlapping.slices[0].width - 90.0) < 1e-4);
    assert(fabs(fragOverlapping.slices[1].startX - 240.0) < 1e-4);
    assert(fabs(fragOverlapping.slices[1].width - 160.0) < 1e-4);

    /* Scenario 2: Two disjoint obstacles on the line */
    TextKit2ExclusionObstacle disjointObs[2];
    /* Obs 0 at (100, 200), radius 30 + margin 10 = 40 -> [60, 140] */
    disjointObs[0].center = CGPointMake(100.0, 200.0);
    disjointObs[0].radius = 30.0;
    disjointObs[0].isActive = true;
    /* Obs 1 at (300, 200), radius 30 + margin 10 = 40 -> [260, 340] */
    disjointObs[1].center = CGPointMake(300.0, 200.0);
    disjointObs[1].radius = 30.0;
    disjointObs[1].isActive = true;

    TextKit2LineFragment fragDisjoint;
    textkit2_compute_line_fragment_slices_multi(400.0, 190.0, 20.0, disjointObs, 2, 10.0, &fragDisjoint);
    /* Three slices: [0, 60], [140, 260], [340, 400] */
    assert(fragDisjoint.sliceCount == 3);
    assert(fabs(fragDisjoint.slices[0].startX - 0.0) < 1e-4);
    assert(fabs(fragDisjoint.slices[0].width - 60.0) < 1e-4);
    assert(fabs(fragDisjoint.slices[1].startX - 140.0) < 1e-4);
    assert(fabs(fragDisjoint.slices[1].width - 120.0) < 1e-4);
    assert(fabs(fragDisjoint.slices[2].startX - 340.0) < 1e-4);
    assert(fabs(fragDisjoint.slices[2].width - 60.0) < 1e-4);

    /* Scenario 3: Full width obstacle covering line [0, 400] */
    TextKit2ExclusionObstacle fullObs;
    fullObs.center = CGPointMake(200.0, 200.0);
    fullObs.radius = 250.0;
    fullObs.isActive = true;
    TextKit2LineFragment fragFull;
    textkit2_compute_line_fragment_slices_multi(400.0, 190.0, 20.0, &fullObs, 1, 10.0, &fragFull);
    assert(fragFull.sliceCount == 0); /* Entire line excluded */

    printf("  [PASS] Suite 37: TextKit 2 Multi-Obstacle Overlapping & Disjoint Boolean Slicing\n");
}

static void test_suite_38_keyboard_hardware_repeat_kinematics(void) {
    AccessibilityScrollViewState tv;
    tv.contentOffset = CGPointMake(0.0, 0.0);
    tv.contentSize = CGSizeMake(393.0, 5000.0);
    tv.contentInsets = UIEdgeInsetsMake(0.0, 0.0, 0.0, 0.0);
    tv.bounds = CGRectMake(0.0, 0.0, 393.0, 800.0);
    tv.keyboardDiscreteStepPt = 40.0;
    tv.pageTurnOverlapPt = 44.0;

    KeyboardRepeatState rep = keyboard_repeat_init();

    /* 1. Key Down: immediate initial step of 40.0pt */
    keyboard_repeat_key_down(&rep, &tv, true, true);
    assert(rep.isKeyDown == true);
    assert(rep.repeatCount == 0);
    assert(tv.contentOffset.y == 40.0);

    /* 2. Hold for 200ms (< 400ms initial repeat delay): offset remains unchanged */
    keyboard_repeat_tick(&rep, &tv, 0.200);
    assert(rep.repeatCount == 0);
    assert(tv.contentOffset.y == 40.0);

    /* 3. Advance to 500ms (100ms past initial delay at 30Hz ~ 33.3ms period -> 3 repeat steps) */
    keyboard_repeat_tick(&rep, &tv, 0.300); /* Total 500ms */
    /* 100ms / (1/30s) = 3 ticks. Each tick +40.0pt. Offset = 40 + 3*40 = 160.0 */
    assert(rep.repeatCount == 3);
    assert(rep.isContinuousRamping == true);
    assert(tv.contentOffset.y == 160.0);

    /* 4. Prolonged holding for an additional 1.0s (total held = 1.5s, active held = 1.1s) */
    keyboard_repeat_tick(&rep, &tv, 1.000);
    /* Velocity ramps: v = 1200 + 1600 * 1.1 = 1200 + 1760 = 2960 -> clamped to 2400.0 pt/s */
    assert(rep.currentVelocity == 2400.0);

    /* 5. Key Up releases state */
    keyboard_repeat_key_up(&rep);
    assert(rep.isKeyDown == false);
    assert(rep.isContinuousRamping == false);
    assert(rep.currentVelocity == 0.0);

    printf("  [PASS] Suite 38: Hardware Keyboard Key Repeat Timing & Velocity Ramping\n");
}

int main(void) {
    printf("=================================================================\n");
    printf("Specialized Scrolling Implementations Test Suite (iOS 27 arm64e)\n");
    printf("=================================================================\n");

    test_suite_01_swiftui_scroll_position_init();
    test_suite_02_swiftui_bridge_target_offset();
    test_suite_03_swiftui_scroll_geometry();
    test_suite_04_swiftui_scroll_phase_transitions();
    test_suite_05_swiftui_echo_suppression();
    test_suite_06_swiftui_gesture_arbitration();
    test_suite_07_webkit_split_delegate();
    test_suite_08_webkit_scrolling_tree_layer_transform();
    test_suite_09_webkit_overscroll_behavior_auto();
    test_suite_10_webkit_overscroll_behavior_contain();
    test_suite_11_webkit_overscroll_behavior_none();
    test_suite_12_webkit_passive_wheel_listener();
    test_suite_13_webkit_active_wheel_timeout();
    test_suite_14_textview_cursor_auto_scroll_within_bounds();
    test_suite_15_textview_cursor_auto_scroll_below_bounds();
    test_suite_16_textview_selection_drag_velocity_ramping();
    test_suite_17_textview_selection_drag_outside_clamp();
    test_suite_18_textview_selection_drag_center_inactive();
    test_suite_19_collectionview_prefetch_min_window();
    test_suite_20_collectionview_prefetch_velocity_proportional();
    test_suite_21_collectionview_prefetch_max_clamp();
    test_suite_22_collectionview_reuse_pool_recycling();
    test_suite_23_collectionview_orthogonal_gesture_locking();
    test_suite_24_accessibility_scroll_directions();
    test_suite_25_accessibility_scroll_boundary_rejection();
    test_suite_26_keyboard_arrow_stepping();
    test_suite_27_keyboard_page_stepping();
    test_suite_28_keyboard_home_end_jump();
    test_suite_29_webkit_tile_cache_memory_pressure();
    test_suite_30_textkit2_multi_container_caret_projection();
    test_suite_31_collectionview_orthogonal_45deg_hysteresis();
    test_suite_32_textview_narrow_viewport_drag_velocity_normalization();
    test_suite_33_textview_selection_drag_2d_velocity();
    test_suite_34_collectionview_prefetch_directional_interval_and_reversal();
    test_suite_35_textkit2_exclusion_path_fragment_slicing();
    test_suite_36_accessibility_detent_scroll_status_and_boundary_feedback();
    test_suite_37_textkit2_multi_obstacle_boolean_slicing();
    test_suite_38_keyboard_hardware_repeat_kinematics();

    printf("\nAll 38 Specialized Scrolling unit test suites PASSED with 0 failures.\n");
    return 0;
}
