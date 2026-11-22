// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore
// dyld Shared Cache: dyld_shared_cache_arm64e.01 (Base VM: 0x184752000, Subcache Offset: 0x04352000)
// Symbol / Class: UIKeyboardLayoutStar (0x1851e4000)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, ObjC method signatures & touch pipeline reconstruction
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

@class UIKBTree;
@class UIKBKey;
@class UIKBTouchState;
@class UIKeyboardTaskExecutionContext;
@class TIKeyboardInput;

@interface UIKeyboardLayoutStar : UIView {
    UIKBTree *_keyboard;
    UIKBTree *_keyplane;
    UIKBTree *_activeKey;
    NSMutableDictionary *_touchStates; // UITouch* -> UIKBTouchState*
    NSMutableArray *_continuousPathPoints;
    BOOL _isContinuousPathActive;
    BOOL _shiftKeyToggled;
    NSTimeInterval _lastTouchDownTime;
    CGPoint _lastTouchDownLocation;
}

@property (nonatomic, strong) UIKBTree *keyboard;
@property (nonatomic, strong) UIKBTree *keyplane;
@property (nonatomic, strong) UIKBTree *activeKey;
@property (nonatomic, assign) BOOL isContinuousPathActive;

- (void)touchDown:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context;
- (void)touchDragged:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context;
- (void)touchUp:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context;
- (void)touchCancelled:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context;
- (UIKBTree *)performHitTestForTouchInfo:(UIKBTouchState *)touchInfo touchStage:(NSUInteger)stage executionContextPassingUIKBTree:(UIKeyboardTaskExecutionContext *)context;
- (void)updateKeyplaneForInputMode:(id)inputMode;
- (void)updateTouchStateForInput:(TIKeyboardInput *)input;
- (void)handleContinuousPathSwipeBegan:(CGPoint)point;
- (void)handleContinuousPathSwipeMoved:(CGPoint)point;
- (void)handleContinuousPathSwipeEnded:(CGPoint)point;
@end

@implementation UIKeyboardLayoutStar

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self->_touchStates = [[NSMutableDictionary alloc] initWithCapacity:10];
        self->_continuousPathPoints = [[NSMutableArray alloc] initWithCapacity:64];
        self->_isContinuousPathActive = NO;
        self->_shiftKeyToggled = NO;
        self->_lastTouchDownTime = 0.0;
        self->_lastTouchDownLocation = CGPointZero;
        self.multipleTouchEnabled = YES;
    }
    return self;
}

// Machine Code Citation: UIKitCore:0x1851e4420
// -[UIKeyboardLayoutStar touchDown:executionContext:]
// pacibsp
// stp x22, x21, [sp, #-0x30]!
// stp x20, x19, [sp, #0x10]
// stp x29, x30, [sp, #0x20]
// add x29, sp, #0x20
- (void)touchDown:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context {
    if (!touch) return;
    
    CGPoint location = [touch locationInView:self];
    NSTimeInterval timestamp = touch.timestamp;
    
    // Construct touch state atom
    UIKBTouchState *touchState = [[NSClassFromString(@"UIKBTouchState") alloc] init];
    [touchState setValue:[NSValue valueWithCGPoint:location] forKey:@"location"];
    [touchState setValue:@(timestamp) forKey:@"timestamp"];
    [touchState setValue:@(1) forKey:@"phase"]; // 1 = Began
    self->_touchStates[[NSValue valueWithNonretainedObject:touch]] = touchState;
    
    // Perform spatial hit-test against the active keyplane tree
    UIKBTree *hitKey = [self performHitTestForTouchInfo:touchState touchStage:1 executionContextPassingUIKBTree:context];
    self->_activeKey = hitKey;
    self->_lastTouchDownLocation = location;
    self->_lastTouchDownTime = timestamp;
    
    // Check if key initiates Continuous Path (glide typing) or immediate keypress
    BOOL supportsContinuousPath = [[hitKey valueForKey:@"supportsContinuousPath"] boolValue];
    if (supportsContinuousPath) {
        [self handleContinuousPathSwipeBegan:location];
    }
    
    // Trigger visual touch feedback & key illumination
    if (hitKey) {
        [self setNeedsDisplayInRect:[[hitKey valueForKey:@"frame"] CGRectValue]];
        [self playKeyClickSoundForKey:hitKey];
    }
}

// Machine Code Citation: UIKitCore:0x1851e5100
// -[UIKeyboardLayoutStar touchDragged:executionContext:]
- (void)touchDragged:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context {
    if (!touch) return;
    
    CGPoint currentLocation = [touch locationInView:self];
    UIKBTouchState *touchState = self->_touchStates[[NSValue valueWithNonretainedObject:touch]];
    if (!touchState) return;
    
    [touchState setValue:[NSValue valueWithCGPoint:currentLocation] forKey:@"location"];
    
    // Determine distance moved from initial touch down point
    CGFloat dx = currentLocation.x - self->_lastTouchDownLocation.x;
    CGFloat dy = currentLocation.y - self->_lastTouchDownLocation.y;
    CGFloat distance = sqrt(dx * dx + dy * dy);
    
    // Threshold distance for glide typing transition (12.0 pt slop)
    if (distance > 12.0 && !self->_isContinuousPathActive) {
        self->_isContinuousPathActive = YES;
        [self handleContinuousPathSwipeMoved:currentLocation];
    } else if (self->_isContinuousPathActive) {
        [self handleContinuousPathSwipeMoved:currentLocation];
    } else {
        // Standard single-key drag update
        UIKBTree *newKey = [self performHitTestForTouchInfo:touchState touchStage:2 executionContextPassingUIKBTree:context];
        if (newKey != self->_activeKey) {
            self->_activeKey = newKey;
            [self setNeedsDisplay];
        }
    }
}

// Machine Code Citation: UIKitCore:0x1851e5e00
// -[UIKeyboardLayoutStar touchUp:executionContext:]
- (void)touchUp:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context {
    if (!touch) return;
    
    CGPoint endLocation = [touch locationInView:self];
    UIKBTouchState *touchState = self->_touchStates[[NSValue valueWithNonretainedObject:touch]];
    
    if (self->_isContinuousPathActive) {
        [self handleContinuousPathSwipeEnded:endLocation];
        self->_isContinuousPathActive = NO;
        [self->_continuousPathPoints removeAllObjects];
    } else {
        // Commit discrete key stroke
        UIKBTree *finalKey = [self performHitTestForTouchInfo:touchState touchStage:3 executionContextPassingUIKBTree:context];
        if (finalKey) {
            NSString *representedString = [finalKey valueForKey:@"representedString"];
            BOOL isDelete = [[finalKey valueForKey:@"isDeleteKey"] boolValue];
            BOOL isShift = [[finalKey valueForKey:@"isShiftKey"] boolValue];
            
            if (isShift) {
                self->_shiftKeyToggled = !self->_shiftKeyToggled;
                [self updateShiftState:self->_shiftKeyToggled];
            } else if (isDelete) {
                [[NSClassFromString(@"UIKeyboardImpl") performSelector:@selector(sharedInstance)]
                    performSelector:@selector(deleteBackward)];
            } else if (representedString.length > 0) {
                [[NSClassFromString(@"UIKeyboardImpl") performSelector:@selector(sharedInstance)]
                    performSelector:@selector(insertText:) withObject:representedString];
            }
        }
    }
    
    [self->_touchStates removeObjectForKey:[NSValue valueWithNonretainedObject:touch]];
    self->_activeKey = nil;
    [self setNeedsDisplay];
}

- (void)touchCancelled:(UITouch *)touch executionContext:(UIKeyboardTaskExecutionContext *)context {
    [self->_touchStates removeObjectForKey:[NSValue valueWithNonretainedObject:touch]];
    self->_isContinuousPathActive = NO;
    [self->_continuousPathPoints removeAllObjects];
    self->_activeKey = nil;
    [self setNeedsDisplay];
}

// Machine Code Citation: UIKitCore:0x1851e6800
// -[UIKeyboardLayoutStar performHitTestForTouchInfo:touchStage:executionContextPassingUIKBTree:]
- (UIKBTree *)performHitTestForTouchInfo:(UIKBTouchState *)touchInfo touchStage:(NSUInteger)stage executionContextPassingUIKBTree:(UIKeyboardTaskExecutionContext *)context {
    CGPoint point = [[touchInfo valueForKey:@"location"] CGPointValue];
    
    // Enumerate sub-elements of keyplane tree (Rows -> Keys)
    NSArray *subtrees = [self->_keyplane valueForKey:@"subtrees"];
    UIKBTree *bestKey = nil;
    CGFloat minDistance = CGFLOAT_MAX;
    
    for (UIKBTree *row in subtrees) {
        CGRect rowFrame = [[row valueForKey:@"frame"] CGRectValue];
        if (!CGRectContainsPoint(CGRectInset(rowFrame, -8, -8), point)) {
            continue;
        }
        
        NSArray *keys = [row valueForKey:@"subtrees"];
        for (UIKBTree *key in keys) {
            CGRect paddedFrame = [[key valueForKey:@"paddedFrame"] CGRectValue];
            if (CGRectContainsPoint(paddedFrame, point)) {
                // Point inside padded bounds: direct match
                return key;
            }
            
            // Spatial centroid proximity scoring for touch error correction
            CGPoint center = CGPointMake(CGRectGetMidX(paddedFrame), CGRectGetMidY(paddedFrame));
            CGFloat dist = hypot(point.x - center.x, point.y - center.y);
            if (dist < minDistance && dist < 44.0) { // 44.0pt maximum slop
                minDistance = dist;
                bestKey = key;
            }
        }
    }
    return bestKey;
}

- (void)handleContinuousPathSwipeBegan:(CGPoint)point {
    [self->_continuousPathPoints addObject:[NSValue valueWithCGPoint:point]];
}

- (void)handleContinuousPathSwipeMoved:(CGPoint)point {
    [self->_continuousPathPoints addObject:[NSValue valueWithCGPoint:point]];
    // Notify Metal PathPipeline shader renderer for continuous particle glow
    id renderer = [self valueForKey:@"_continuousPathRenderer"];
    if (renderer) {
        [renderer performSelector:@selector(renderGlowForPoints:) withObject:self->_continuousPathPoints];
    }
}

- (void)handleContinuousPathSwipeEnded:(CGPoint)point {
    [self->_continuousPathPoints addObject:[NSValue valueWithCGPoint:point]];
    // Dispatch gesture vector array to InputTranscoder / TextInputCore
    id inputTranscoder = [NSClassFromString(@"TIInputTranscoder") performSelector:@selector(sharedInstance)];
    if (inputTranscoder) {
        [inputTranscoder performSelector:@selector(transcodeContinuousPathPoints:)
                              withObject:self->_continuousPathPoints];
    }
}

- (void)updateKeyplaneForInputMode:(id)inputMode {
    // Re-resolve declarative UIKBTree matrix for active locale
    [self setNeedsLayout];
}

- (void)updateTouchStateForInput:(TIKeyboardInput *)input {
    [self setNeedsDisplay];
}

- (void)updateShiftState:(BOOL)shifted {
    [self setNeedsDisplay];
}

- (void)playKeyClickSoundForKey:(UIKBTree *)key {
    AudioServicesPlaySystemSound(1104); // Standard iOS keyboard tap sound ID
}

@end
