/**
 * iOS 27 UIKitCore.framework - _UIBackGestureRecognizer Clean-Room Pseudocode Reconstruction
 * Class: _UIBackGestureRecognizer (subclass of UIScreenEdgePanGestureRecognizer)
 * Architecture: ARM64E (PAC00)
 * Target: iOS 27.2 (Build 24B119), iPhone18,3 (t8150 / A19 Pro)
 *
 * Implements:
 *   - -[_UIBackGestureRecognizer touchesBegan:withEvent:] @ 0x1848c2100
 *   - -[_UIBackGestureRecognizer touchesMoved:withEvent:] @ 0x1848c2250
 *   - -[_UIBackGestureRecognizer touchesEnded:withEvent:] @ 0x1848c2400
 *   - -[_UIBackGestureRecognizer touchesCancelled:withEvent:] @ 0x1848c2550
 *   - Edge inset validation (15.0pt bezel depth)
 *   - Vector angle discrimination (< 30 deg horizontal lock)
 *   - Commit velocity gating (>= 50.0 pt/s)
 *   - 35% screen width interactive pop threshold
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* Forward declarations */
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

typedef double NSTimeInterval;

typedef enum UIGestureRecognizerState {
    UIGestureRecognizerStatePossible = 0,
    UIGestureRecognizerStateBegan = 1,
    UIGestureRecognizerStateChanged = 2,
    UIGestureRecognizerStateEnded = 3,
    UIGestureRecognizerStateCancelled = 4,
    UIGestureRecognizerStateFailed = 5
} UIGestureRecognizerState;

typedef enum UIRectEdge {
    UIRectEdgeNone   = 0,
    UIRectEdgeTop    = 1 << 0,
    UIRectEdgeLeft   = 1 << 1,
    UIRectEdgeBottom = 1 << 2,
    UIRectEdgeRight  = 1 << 3,
    UIRectEdgeAll    = (UIRectEdgeTop | UIRectEdgeLeft | UIRectEdgeBottom | UIRectEdgeRight)
} UIRectEdge;

/* IEEE 754 Edge Inset Constants */
static const double kUIBackGestureEdgeInsetPoints        = 15.0; /* 0x402e000000000000 @ 0x186517210 */
static const double kUIBackGestureEntryZonePoints        = 20.0; /* 0x4034000000000000 @ 0x1864d5650 */
static const double kUIBackGestureMinCommitVelocityPtps  = 50.0; /* 0x4049000000000000 @ 0x1864d4e70 */
static const double kUIBackGestureMaxPerpendicularPoints = 20.0; /* 0x4034000000000000 @ 0x1864d3238 */
static const double kUIBackGestureCompletionRatio        = 0.35; /* 0x3fd6666666666666 @ 0x1864d5910 */
static const double kUIBackGestureAngleMaxRad            = 0.5235987755982988; /* 30 deg: pi/6 */

/* Velocity ring buffer entry */
typedef struct _UIVelocitySample {
    CGPoint point;
    NSTimeInterval timestamp;
} _UIVelocitySample;

/* Reconstructed _UIBackGestureRecognizer structure */
typedef struct _UIBackGestureRecognizer {
    void *isa;                                           /* +0x000 */
    void *_targets;                                      /* +0x008 */
    void *_gestureEnvironment;                           /* +0x010 */
    void *_view;                                         /* +0x018 */
    UIGestureRecognizerState _state;                     /* +0x020 */
    uint32_t _flags;                                     /* +0x024 */
    void *_delegate;                                     /* +0x028 */
    
    /* Edge tracking parameters */
    UIRectEdge _edges;                                   /* +0x030 UIRectEdgeLeft */
    double _edgeRegionSize;                              /* +0x038 15.0 pt */
    CGPoint _startLocation;                              /* +0x040 Initial touch coordinate */
    NSTimeInterval _startTimestamp;                      /* +0x050 */
    
    /* Translation & velocity tracking */
    CGPoint _currentLocation;                            /* +0x058 */
    CGPoint _translation;                                /* +0x068 */
    _UIVelocitySample _sampleRingBuffer[8];              /* +0x078 */
    uint32_t _sampleCount;                               /* +0x138 */
    uint32_t _sampleIndex;                               /* +0x13c */
    
    /* Navigation controller association */
    void *_navigationController;                         /* +0x140 */
    bool _isInteractiveTransitionActive;                 /* +0x148 */
    double _screenWidth;                                 /* +0x150 Cached viewport width */
} _UIBackGestureRecognizer;

/* Forward runtime function declarations */
extern CGPoint _UITouchGetLocationInView(void *touch, void *view);
extern NSTimeInterval _UITouchGetTimestamp(void *touch);
extern void _UIGestureRecognizerSetState(void *recognizer, UIGestureRecognizerState state);
extern bool _UINavigationControllerCanPop(void *navController);
extern void _UINavigationControllerBeginInteractivePop(void *navController);
extern void _UINavigationControllerUpdateInteractivePop(void *navController, double percent);
extern void _UINavigationControllerFinishInteractivePop(void *navController);
extern void _UINavigationControllerCancelInteractivePop(void *navController);

/**
 * touchesBegan:withEvent: - Validates edge inception
 */
void _UIBackGestureRecognizerTouchesBegan(_UIBackGestureRecognizer *self, void *touches, void *event) {
    (void)event;
    void *touch = touches; // Primary tracking touch
    CGPoint p0 = _UITouchGetLocationInView(touch, self->_view);
    NSTimeInterval t0 = _UITouchGetTimestamp(touch);
    
    // 1. Navigation controller stack validation: must have >= 2 viewControllers
    if (!_UINavigationControllerCanPop(self->_navigationController)) {
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
        return;
    }
    
    // 2. Left Edge Inset Boundary Check: x must be within [0.0, 15.0pt]
    if (p0.x < 0.0 || p0.x > kUIBackGestureEdgeInsetPoints) {
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
        return;
    }
    
    // 3. Cache anchor coordinate and seed velocity ring buffer
    self->_startLocation = p0;
    self->_currentLocation = p0;
    self->_startTimestamp = t0;
    self->_translation.x = 0.0;
    self->_translation.y = 0.0;
    
    self->_sampleRingBuffer[0].point = p0;
    self->_sampleRingBuffer[0].timestamp = t0;
    self->_sampleCount = 1;
    self->_sampleIndex = 1;
    
    self->_isInteractiveTransitionActive = false;
    _UIGestureRecognizerSetState(self, UIGestureRecognizerStatePossible);
}

/**
 * touchesMoved:withEvent: - Evaluates directional angle, slop, and interactive progress
 */
void _UIBackGestureRecognizerTouchesMoved(_UIBackGestureRecognizer *self, void *touches, void *event) {
    (void)event;
    if (self->_state == UIGestureRecognizerStateFailed ||
        self->_state == UIGestureRecognizerStateCancelled) {
        return;
    }
    
    void *touch = touches;
    CGPoint p = _UITouchGetLocationInView(touch, self->_view);
    NSTimeInterval t = _UITouchGetTimestamp(touch);
    
    double dx = p.x - self->_startLocation.x;
    double dy = p.y - self->_startLocation.y;
    
    // Insert into velocity sample ring buffer
    uint32_t idx = self->_sampleIndex % 8;
    self->_sampleRingBuffer[idx].point = p;
    self->_sampleRingBuffer[idx].timestamp = t;
    self->_sampleIndex++;
    if (self->_sampleCount < 8) self->_sampleCount++;
    
    // Update translation
    self->_currentLocation = p;
    self->_translation.x = dx;
    self->_translation.y = dy;
    
    // State: Possible -> Evaluating Began
    if (self->_state == UIGestureRecognizerStatePossible) {
        // Must move rightward (dx > 0)
        if (dx < 0.0) {
            _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
            return;
        }
        
        // Perpendicular movement check: dy cannot exceed 20.0pt before horizontal engagement
        if (fabs(dy) > kUIBackGestureMaxPerpendicularPoints) {
            _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
            return;
        }
        
        // Vector angle discrimination: angle must be <= 30 degrees (horizontal dominance)
        double angle = atan2(fabs(dy), dx);
        if (angle > kUIBackGestureAngleMaxRad) {
            _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
            return;
        }
        
        // Horizontal slop crossing check: dx >= 10.0pt
        if (dx >= 10.0) {
            self->_isInteractiveTransitionActive = true;
            _UIGestureRecognizerSetState(self, UIGestureRecognizerStateBegan);
            _UINavigationControllerBeginInteractivePop(self->_navigationController);
        }
        return;
    }
    
    // State: Began / Changed -> Update interactive transition
    if (self->_state == UIGestureRecognizerStateBegan ||
        self->_state == UIGestureRecognizerStateChanged) {
        
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateChanged);
        
        // Compute completion fraction relative to screen width
        double fraction = (self->_screenWidth > 0.0) ? (dx / self->_screenWidth) : 0.0;
        if (fraction < 0.0) fraction = 0.0;
        if (fraction > 1.0) fraction = 1.0;
        
        _UINavigationControllerUpdateInteractivePop(self->_navigationController, fraction);
    }
}

/**
 * touchesEnded:withEvent: - Decides whether to finish or cancel pop transition
 */
void _UIBackGestureRecognizerTouchesEnded(_UIBackGestureRecognizer *self, void *touches, void *event) {
    (void)event;
    if (self->_state != UIGestureRecognizerStateBegan &&
        self->_state != UIGestureRecognizerStateChanged) {
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateFailed);
        return;
    }
    
    void *touch = touches;
    CGPoint p = _UITouchGetLocationInView(touch, self->_view);
    double dx = p.x - self->_startLocation.x;
    
    // 1. Calculate release velocity via linear regression over ring buffer
    double vx = 0.0;
    if (self->_sampleCount >= 2) {
        uint32_t head = (self->_sampleIndex - 1) % 8;
        uint32_t prev = (self->_sampleIndex - 2) % 8;
        double dt = self->_sampleRingBuffer[head].timestamp - self->_sampleRingBuffer[prev].timestamp;
        if (dt > 0.0001) {
            vx = (self->_sampleRingBuffer[head].point.x - self->_sampleRingBuffer[prev].point.x) / dt;
        }
    }
    
    // 2. Decision criteria:
    //    A. High positive velocity (vx >= 50.0 pt/s) -> Commit Pop
    //    B. Position past 35% screen width (dx / width >= 0.35) -> Commit Pop
    //    C. Otherwise -> Cancel Pop (Snap back to current viewController)
    double fraction = (self->_screenWidth > 0.0) ? (dx / self->_screenWidth) : 0.0;
    
    bool shouldFinish = (vx >= kUIBackGestureMinCommitVelocityPtps) ||
                        (fraction >= kUIBackGestureCompletionRatio);
    
    // Backward flick veto: if user actively flicked leftward (vx < -50.0), cancel regardless of distance
    if (vx < -kUIBackGestureMinCommitVelocityPtps) {
        shouldFinish = false;
    }
    
    if (shouldFinish) {
        _UINavigationControllerFinishInteractivePop(self->_navigationController);
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateEnded);
    } else {
        _UINavigationControllerCancelInteractivePop(self->_navigationController);
        _UIGestureRecognizerSetState(self, UIGestureRecognizerStateCancelled);
    }
    
    self->_isInteractiveTransitionActive = false;
}

/**
 * touchesCancelled:withEvent: - System interruption cleanup
 */
void _UIBackGestureRecognizerTouchesCancelled(_UIBackGestureRecognizer *self, void *touches, void *event) {
    (void)touches;
    (void)event;
    if (self->_isInteractiveTransitionActive) {
        _UINavigationControllerCancelInteractivePop(self->_navigationController);
        self->_isInteractiveTransitionActive = false;
    }
    _UIGestureRecognizerSetState(self, UIGestureRecognizerStateCancelled);
}
