/**
 * UIKitCore.framework - UIPanGestureRecognizer Decompiled Pseudocode Reconstruction
 * Class: UIPanGestureRecognizer
 * Target: iOS 27.2 (Build 24B119), arm64e (PAC00)
 * Address: 0x1848d1420 (subcache .01, file offset: 0x44d1420)
 *
 * Implements:
 *   - -[UIPanGestureRecognizer touchesBegan:withEvent:] @ 0x1848c1000
 *   - -[UIPanGestureRecognizer touchesMoved:withEvent:] @ 0x1848c1150
 *   - -[UIPanGestureRecognizer touchesEnded:withEvent:] @ 0x1848c1300
 *   - -[UIPanGestureRecognizer touchesCancelled:withEvent:] @ 0x1848c1450
 *   - -[UIPanGestureRecognizer _updateGestureState] @ 0x1848d1600
 *   - Movement accumulation, device-specific touch slop thresholds
 *   - Rolling sample ring buffer and weighted velocity estimation
 *   - Smooth hysteresis offset tracking (eliminating coordinate jumps)
 *   - Directional locking and 40pt/3-frame lock-break mechanics
 *   - Translation querying and differential reset support
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
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

typedef double NSTimeInterval;

typedef enum UIGestureRecognizerState {
    UIGestureRecognizerStatePossible = 0,
    UIGestureRecognizerStateBegan = 1,
    UIGestureRecognizerStateChanged = 2,
    UIGestureRecognizerStateEnded = 3,
    UIGestureRecognizerStateCancelled = 4,
    UIGestureRecognizerStateFailed = 5
} UIGestureRecognizerState;

typedef enum UITouchType {
    UITouchTypeDirect = 0,         /* Direct capacitive finger */
    UITouchTypeIndirect = 1,       /* Mouse / trackpad non-direct */
    UITouchTypePencil = 2,         /* Apple Pencil */
    UITouchTypeIndirectPointer = 3 /* Modern iPadOS trackpad pointer */
} UITouchType;

typedef enum _UIScrollViewDirectionalLockState {
    LockAxisNone = 0,
    LockAxisHorizontal = 1,
    LockAxisVertical = 2
} _UIScrollViewDirectionalLockState;

/* Velocity sample ring buffer entry */
typedef struct _UIVelocitySample {
    CGPoint point;
    NSTimeInterval timestamp;
} _UIVelocitySample;

/* Reconstructed UIPanGestureRecognizer internal layout */
typedef struct UIPanGestureRecognizer {
    void *isa;                                       /* +0x000 */
    void *_targets;                                  /* +0x008 Target/action list */
    void *_gestureEnvironment;                       /* +0x010 */
    void *_view;                                     /* +0x018 Attached UIView */
    UIGestureRecognizerState _state;                 /* +0x020 Current FSM state */
    uint32_t _flags;                                 /* +0x024 Flags bitfield */
    
    /* Pan-specific ivars */
    CGPoint _startLocation;                          /* +0x028 Origin coordinate (p0) */
    CGPoint _currentLocation;                        /* +0x038 Latest smoothed coordinate */
    CGPoint _translation;                            /* +0x048 Accumulated translation */
    CGPoint _previousTranslation;                    /* +0x058 Previous step translation */
    NSTimeInterval _startTimestamp;                  /* +0x068 Initial touch timestamp (t0) */
    NSTimeInterval _lastTimestamp;                   /* +0x070 Latest touch timestamp */
    
    /* Velocity sampling ring buffer */
    _UIVelocitySample _sampleRingBuffer[8];          /* +0x078 8 samples x 24 bytes = 192 bytes */
    uint32_t _sampleCount;                           /* +0x138 Count of valid samples (max 8) */
    uint32_t _sampleIndex;                           /* +0x13c Head insertion index */
    
    /* Directional lock state */
    bool _directionalLockEnabled;                    /* +0x140 Directional locking flag */
    _UIScrollViewDirectionalLockState _lockedAxis;   /* +0x144 Active locked axis */
    double _lockAngle;                               /* +0x148 Evaluated lock angle in radians */
    uint32_t _consecutiveBreakFrames;                /* +0x150 Frames opposing active lock */
    double _crossAxisDisplacement;                   /* +0x158 Accumulated perpendicular displacement for lock break */
    
    /* Configuration thresholds */
    double _customHysteresis;                        /* +0x160 Custom slop override */
    bool _delaysContentTouches;                      /* +0x168 Delay touch delivery */
    bool _canCancelContentTouches;                   /* +0x169 Cancel active touches */
    CGPoint _hysteresisOffset;                       /* +0x170 Offset subtracted to smooth slop crossing */
    void *_trackingTouch;                            /* +0x180 Active primary tracking touch */
} UIPanGestureRecognizer;

/* IEEE 754 Hardware Slop Constants */
static const double kUIFingerTouchSlopPoints   = 10.0; /* 0x4024000000000000 */
static const double kUIPencilTouchSlopPoints   = 4.0;  /* 0x4010000000000000 */
static const double kUITrackpadTouchSlopPoints = 2.0;  /* 0x4000000000000000 */
static const double kCoordinateEmaAlpha        = 0.85; /* 0x3feb333333333333 */
static const double kLockVerticalMinAngleRad   = 1.0471975511965976; /* 60 deg: pi/3 */
static const double kLockHorizontalMaxAngleRad = 0.5235987755982988; /* 30 deg: pi/6 */
static const double kLockBreakThresholdPoints  = 40.0; /* 4x standard finger slop */
static const double kVelocityTau               = 0.040; /* 40ms decay constant */

/* Forward declarations of runtime helper functions */
extern void *objc_msgSend(void *receiver, const char *selector, ...);
extern void _UIGestureRecognizerUpdateState(UIPanGestureRecognizer *self, UIGestureRecognizerState newState);
extern void _UIGestureRecognizerCancelTouchesInViews(UIPanGestureRecognizer *self);
extern bool _UIGestureRecognizerShouldBegin(UIPanGestureRecognizer *self);
extern UITouchType _UITouchGetType(void *touch);
extern CGPoint _UITouchGetLocationInView(void *touch, void *view);
extern NSTimeInterval _UITouchGetTimestamp(void *touch);

/**
 * Resolves touch slop threshold based on input hardware device.
 */
static inline double _UIPanResolveTouchSlop(UITouchType touchType, double customHysteresis) {
    if (customHysteresis > 0.0) {
        return customHysteresis;
    }
    switch (touchType) {
        case UITouchTypePencil:
            return kUIPencilTouchSlopPoints; /* 4.0 pt */
        case UITouchTypeIndirect:
        case UITouchTypeIndirectPointer:
            return kUITrackpadTouchSlopPoints; /* 2.0 pt */
        case UITouchTypeDirect:
        default:
            return kUIFingerTouchSlopPoints; /* 10.0 pt */
    }
}

/**
 * Evaluates directional lock axis discrimination based on initial movement vector.
 */
static inline _UIScrollViewDirectionalLockState _UIPanEvaluateDirectionalLock(double dx, double dy) {
    double absX = fabs(dx);
    double absY = fabs(dy);
    
    if (absX < 0.0001 && absY < 0.0001) {
        return LockAxisNone;
    }
    
    double angle = atan2(absY, absX);
    if (angle >= kLockVerticalMinAngleRad) {
        /* Angle >= 60 degrees: vertical lock */
        return LockAxisVertical;
    } else if (angle <= kLockHorizontalMaxAngleRad) {
        /* Angle <= 30 degrees: horizontal lock */
        return LockAxisHorizontal;
    } else {
        /* 30 - 60 degrees: neutral diagonal zone */
        return LockAxisNone;
    }
}

/**
 * Appends a new timestamped touch coordinate sample into the rolling 8-element ring buffer.
 */
static inline void _UIPanGestureAddVelocitySample(UIPanGestureRecognizer *self, CGPoint point, NSTimeInterval timestamp) {
    self->_sampleRingBuffer[self->_sampleIndex].point = point;
    self->_sampleRingBuffer[self->_sampleIndex].timestamp = timestamp;
    self->_sampleIndex = (self->_sampleIndex + 1) % 8;
    if (self->_sampleCount < 8) {
        self->_sampleCount++;
    }
}

/**
 * Calculates release velocity in points per second using exponentially weighted linear regression.
 */
CGPoint _UIPanGestureRecognizerVelocityInView(UIPanGestureRecognizer *self, void *view) {
    (void)view;
    if (!self || self->_sampleCount < 2) {
        return (CGPoint){0.0, 0.0};
    }

    NSTimeInterval latestTime = self->_lastTimestamp;
    double sumWeights = 0.0;
    double sumWeightedDx = 0.0;
    double sumWeightedDy = 0.0;

    for (uint32_t i = 1; i < self->_sampleCount; i++) {
        uint32_t currIdx = (self->_sampleIndex + 8 - i) % 8;
        uint32_t prevIdx = (currIdx + 7) % 8;

        NSTimeInterval tCurr = self->_sampleRingBuffer[currIdx].timestamp;
        NSTimeInterval tPrev = self->_sampleRingBuffer[prevIdx].timestamp;
        double dt = tCurr - tPrev;

        if (dt <= 0.0001 || (latestTime - tCurr) > 0.100) {
            continue;
        }

        double age = latestTime - tCurr;
        double weight = exp(-age / kVelocityTau);

        double vx = (self->_sampleRingBuffer[currIdx].point.x - self->_sampleRingBuffer[prevIdx].point.x) / dt;
        double vy = (self->_sampleRingBuffer[currIdx].point.y - self->_sampleRingBuffer[prevIdx].point.y) / dt;

        sumWeightedDx += vx * weight;
        sumWeightedDy += vy * weight;
        sumWeights += weight;
    }

    if (sumWeights <= 0.0001) {
        return (CGPoint){0.0, 0.0};
    }

    CGPoint velocity;
    velocity.x = sumWeightedDx / sumWeights;
    velocity.y = sumWeightedDy / sumWeights;

    /* Clamp maximum velocity to ceiling (8000 pt/s) */
    double speed = sqrt(velocity.x * velocity.x + velocity.y * velocity.y);
    if (speed > 8000.0) {
        double scale = 8000.0 / speed;
        velocity.x *= scale;
        velocity.y *= scale;
    }

    return velocity;
}

/**
 * Returns current translation in view coordinate space.
 */
CGPoint _UIPanGestureRecognizerTranslationInView(UIPanGestureRecognizer *self, void *view) {
    (void)view;
    if (!self) {
        return (CGPoint){0.0, 0.0};
    }
    return self->_translation;
}

/**
 * Resets translation origin in view space, allowing differential displacement accumulation.
 */
void _UIPanGestureRecognizerSetTranslationInView(UIPanGestureRecognizer *self, CGPoint translation, void *view) {
    (void)view;
    if (!self) {
        return;
    }
    /* Align start location and hysteresis offset so subsequent translations are relative to this baseline */
    self->_startLocation.x = self->_currentLocation.x - translation.x;
    self->_startLocation.y = self->_currentLocation.y - translation.y;
    self->_hysteresisOffset = (CGPoint){0.0, 0.0};
    self->_translation = translation;
    self->_previousTranslation = translation;
}

/**
 * -[UIPanGestureRecognizer _updateGestureState]
 * Internal state coordinator evaluating recognition criteria and triggering FSM updates.
 */
void _UIPanGestureRecognizer_updateGestureState(UIPanGestureRecognizer *self, UIGestureRecognizerState nextState) {
    if (!self) {
        return;
    }

    UIGestureRecognizerState prevState = self->_state;
    (void)prevState;
    self->_state = nextState;

    if (nextState == UIGestureRecognizerStateBegan) {
        /* Recognition confirmed: cancel content touches in subviews */
        _UIGestureRecognizerCancelTouchesInViews(self);
    } else if (nextState >= UIGestureRecognizerStateEnded) {
        /* Terminal transition: clean up sample buffer and reset lock */
        self->_sampleCount = 0;
        self->_sampleIndex = 0;
        self->_consecutiveBreakFrames = 0;
        self->_lockedAxis = LockAxisNone;
    }

    /* Broadcast target action to attached targets */
    if (self->_targets) {
        objc_msgSend((void *)self->_targets, "makeObjectsPerformSelector:withObject:",
                      "performActionWithGestureRecognizer:", self);
    }
}

/**
 * -[UIPanGestureRecognizer touchesBegan:withEvent:]
 * Handles initial digitizer contact and initializes sampling buffer.
 */
void _UIPanGestureRecognizer_touchesBegan(UIPanGestureRecognizer *self, void *touches, void *event) {
    (void)event;
    if (!self || !self->_view || !touches) {
        return;
    }

    void *primaryTouch = (void *)objc_msgSend(touches, "anyObject");
    if (!primaryTouch) {
        return;
    }

    self->_trackingTouch = primaryTouch;
    CGPoint loc = _UITouchGetLocationInView(primaryTouch, self->_view);
    NSTimeInterval timestamp = _UITouchGetTimestamp(primaryTouch);

    self->_startLocation = loc;
    self->_currentLocation = loc;
    self->_startTimestamp = timestamp;
    self->_lastTimestamp = timestamp;
    self->_translation = (CGPoint){0.0, 0.0};
    self->_previousTranslation = (CGPoint){0.0, 0.0};
    self->_hysteresisOffset = (CGPoint){0.0, 0.0};
    self->_lockedAxis = LockAxisNone;
    self->_consecutiveBreakFrames = 0;
    self->_crossAxisDisplacement = 0.0;
    self->_sampleCount = 0;
    self->_sampleIndex = 0;

    /* Seed ring buffer with initial touch point */
    _UIPanGestureAddVelocitySample(self, loc, timestamp);

    self->_state = UIGestureRecognizerStatePossible;
}

/**
 * -[UIPanGestureRecognizer touchesMoved:withEvent:]
 * Core touch movement tracking implementation with hysteresis smoothing and directional locking.
 */
void _UIPanGestureRecognizer_touchesMoved(UIPanGestureRecognizer *self, void *touches, void *event) {
    (void)event;
    /* Validate parameters and view attachment */
    if (!self || !self->_view || !touches) {
        return;
    }

    /* Extract or preserve primary tracking touch for multi-touch stability */
    void *primaryTouch = self->_trackingTouch;
    if (!primaryTouch) {
        primaryTouch = (void *)objc_msgSend(touches, "anyObject");
        self->_trackingTouch = primaryTouch;
    }
    if (!primaryTouch) {
        return;
    }

    /* Query hardware touch type and raw coordinate */
    UITouchType touchType = _UITouchGetType(primaryTouch);
    CGPoint rawLocation = _UITouchGetLocationInView(primaryTouch, self->_view);
    NSTimeInterval currentTimestamp = _UITouchGetTimestamp(primaryTouch);

    /* Apply Exponential Moving Average (EMA) coordinate smoothing */
    CGPoint smoothedLocation;
    if (self->_sampleCount > 0) {
        smoothedLocation.x = kCoordinateEmaAlpha * rawLocation.x + (1.0 - kCoordinateEmaAlpha) * self->_currentLocation.x;
        smoothedLocation.y = kCoordinateEmaAlpha * rawLocation.y + (1.0 - kCoordinateEmaAlpha) * self->_currentLocation.y;
    } else {
        smoothedLocation = rawLocation;
    }
    self->_currentLocation = smoothedLocation;
    self->_lastTimestamp = currentTimestamp;

    /* Append smoothed coordinate into rolling velocity sample ring buffer */
    _UIPanGestureAddVelocitySample(self, smoothedLocation, currentTimestamp);

    /* State Machine Dispatch */
    switch (self->_state) {
        case UIGestureRecognizerStatePossible: {
            /* Compute displacement from initial touch-down coordinate */
            double dx = smoothedLocation.x - self->_startLocation.x;
            double dy = smoothedLocation.y - self->_startLocation.y;
            double euclideanDisplacement = sqrt(dx * dx + dy * dy);

            /* Retrieve device-specific touch slop threshold */
            double requiredSlop = _UIPanResolveTouchSlop(touchType, self->_customHysteresis);

            /* Check if movement exceeds touch slop threshold */
            if (euclideanDisplacement < requiredSlop) {
                /* Discard movement below threshold to suppress tactile jitter */
                return;
            }

            /* Slop threshold satisfied; evaluate directional locking if enabled */
            if (self->_directionalLockEnabled) {
                self->_lockedAxis = _UIPanEvaluateDirectionalLock(dx, dy);
                self->_consecutiveBreakFrames = 0;
                self->_crossAxisDisplacement = 0.0;
            }

            /* Consult delegate and target via _gestureRecognizerShouldBegin: */
            if (!_UIGestureRecognizerShouldBegin(self)) {
                /* Vetoed by delegate or geometry limits; transition to Failed */
                _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateFailed);
                return;
            }

            /* Record hysteresis offset to ensure seamless coordinate continuity */
            double angle = atan2(dy, dx);
            self->_hysteresisOffset.x = cos(angle) * requiredSlop;
            self->_hysteresisOffset.y = sin(angle) * requiredSlop;

            /* Baseline translation starts exactly at (0, 0) relative to slop boundary */
            self->_translation.x = dx - self->_hysteresisOffset.x;
            self->_translation.y = dy - self->_hysteresisOffset.y;
            self->_previousTranslation = self->_translation;

            /* Transition finite state machine: Possible (0) -> Began (1) */
            _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateBegan);
            break;
        }

        case UIGestureRecognizerStateBegan:
        case UIGestureRecognizerStateChanged: {
            /* Compute unconstrained displacement */
            double rawDx = smoothedLocation.x - self->_startLocation.x;
            double rawDy = smoothedLocation.y - self->_startLocation.y;

            /* Subtract hysteresis offset so displacement is continuously measured without 10pt jump */
            double netDx = rawDx - self->_hysteresisOffset.x;
            double netDy = rawDy - self->_hysteresisOffset.y;

            /* Apply directional lock clamping with persistent cross-axis accumulator */
            if (self->_directionalLockEnabled && self->_lockedAxis != LockAxisNone) {
                double deltaX = netDx - self->_previousTranslation.x;
                double deltaY = netDy - self->_previousTranslation.y;

                if (self->_lockedAxis == LockAxisVertical) {
                    /* Accumulate signed perpendicular horizontal movement */
                    self->_crossAxisDisplacement += deltaX;
                    /* Check perpendicular displacement for lock-break condition */
                    if (fabs(self->_crossAxisDisplacement) > kLockBreakThresholdPoints) {
                        self->_consecutiveBreakFrames++;
                        if (self->_consecutiveBreakFrames >= 3) {
                            /* Break vertical lock to enable full 2D scrolling */
                            self->_lockedAxis = LockAxisNone;
                            self->_crossAxisDisplacement = 0.0;
                        }
                    } else {
                        self->_consecutiveBreakFrames = 0;
                    }
                    /* Only clamp horizontal translation if vertical lock is still active */
                    if (self->_lockedAxis == LockAxisVertical) {
                        netDx = 0.0;
                    }
                } else if (self->_lockedAxis == LockAxisHorizontal) {
                    /* Accumulate signed perpendicular vertical movement */
                    self->_crossAxisDisplacement += deltaY;
                    /* Check perpendicular displacement for lock-break condition */
                    if (fabs(self->_crossAxisDisplacement) > kLockBreakThresholdPoints) {
                        self->_consecutiveBreakFrames++;
                        if (self->_consecutiveBreakFrames >= 3) {
                            /* Break horizontal lock to enable full 2D scrolling */
                            self->_lockedAxis = LockAxisNone;
                            self->_crossAxisDisplacement = 0.0;
                        }
                    } else {
                        self->_consecutiveBreakFrames = 0;
                    }
                    /* Only clamp vertical translation if horizontal lock is still active */
                    if (self->_lockedAxis == LockAxisHorizontal) {
                        netDy = 0.0;
                    }
                }
            }

            /* Update translation coordinates */
            self->_previousTranslation = self->_translation;
            self->_translation.x = netDx;
            self->_translation.y = netDy;

            /* Advance state to Changed (2) if currently in Began (1) */
            if (self->_state == UIGestureRecognizerStateBegan) {
                _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateChanged);
            } else {
                /* Target action dispatch for continuous Changed notification */
                if (self->_targets) {
                    objc_msgSend((void *)self->_targets, "makeObjectsPerformSelector:withObject:",
                                  "performActionWithGestureRecognizer:", self);
                }
            }
            break;
        }

        case UIGestureRecognizerStateEnded:
        case UIGestureRecognizerStateCancelled:
        case UIGestureRecognizerStateFailed:
        default:
            /* Terminal states ignore subsequent touch movement reports */
            break;
    }
}

/**
 * -[UIPanGestureRecognizer touchesEnded:withEvent:]
 * Handles touch release, arbitrates multi-touch finger transitions, and transitions FSM to Ended.
 */
void _UIPanGestureRecognizer_touchesEnded(UIPanGestureRecognizer *self, void *touches, void *event) {
    if (!self) {
        return;
    }
    (void)touches;

    /* Multi-touch arbitration: check if additional active touches remain */
    if (event) {
        void *allTouches = objc_msgSend(event, "allTouches");
        if (allTouches) {
            uint64_t count = (uint64_t)objc_msgSend(allTouches, "count");
            if (count > 1) {
                /* Active secondary touches exist; hand off tracking without terminating gesture */
                void *nextTouch = objc_msgSend(allTouches, "anyObject");
                if (nextTouch && nextTouch != self->_trackingTouch) {
                    self->_trackingTouch = nextTouch;
                    CGPoint loc = _UITouchGetLocationInView(nextTouch, self->_view);
                    self->_currentLocation = loc;
                    /* Re-anchor start location to current coordinate to prevent discontinuous jumps */
                    self->_startLocation.x = loc.x - self->_translation.x;
                    self->_startLocation.y = loc.y - self->_translation.y;
                    self->_hysteresisOffset = (CGPoint){0.0, 0.0};
                    return;
                }
            }
        }
    }

    self->_trackingTouch = NULL;

    if (self->_state == UIGestureRecognizerStateBegan || self->_state == UIGestureRecognizerStateChanged) {
        _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateEnded);
    } else if (self->_state == UIGestureRecognizerStatePossible) {
        _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateFailed);
    }
}

/**
 * -[UIPanGestureRecognizer touchesCancelled:withEvent:]
 * Handles touch cancellation, arbitrates multi-touch finger transitions, and transitions FSM to Cancelled.
 */
void _UIPanGestureRecognizer_touchesCancelled(UIPanGestureRecognizer *self, void *touches, void *event) {
    if (!self) {
        return;
    }
    (void)touches;

    /* Multi-touch arbitration: check if additional active touches remain */
    if (event) {
        void *allTouches = objc_msgSend(event, "allTouches");
        if (allTouches) {
            uint64_t count = (uint64_t)objc_msgSend(allTouches, "count");
            if (count > 1) {
                void *nextTouch = objc_msgSend(allTouches, "anyObject");
                if (nextTouch && nextTouch != self->_trackingTouch) {
                    self->_trackingTouch = nextTouch;
                    CGPoint loc = _UITouchGetLocationInView(nextTouch, self->_view);
                    self->_currentLocation = loc;
                    self->_startLocation.x = loc.x - self->_translation.x;
                    self->_startLocation.y = loc.y - self->_translation.y;
                    self->_hysteresisOffset = (CGPoint){0.0, 0.0};
                    return;
                }
            }
        }
    }

    self->_trackingTouch = NULL;

    if (self->_state == UIGestureRecognizerStateBegan || self->_state == UIGestureRecognizerStateChanged) {
        _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateCancelled);
    } else if (self->_state == UIGestureRecognizerStatePossible) {
        _UIPanGestureRecognizer_updateGestureState(self, UIGestureRecognizerStateFailed);
    }
}
