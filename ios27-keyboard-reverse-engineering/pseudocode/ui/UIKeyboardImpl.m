// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore
// dyld Shared Cache: dyld_shared_cache_arm64e.01 (Base VM: 0x184752000, Subcache Offset: 0x04352000)
// Symbol / Class: UIKeyboardImpl (0x1851b2400)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, ObjC method signatures & reconstructed state machine
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

// Forward declarations of internal types verified from UIKitCore and TextInput
@class UIKeyboardLayoutStar;
@class UIKeyboardTaskQueue;
@class UIKeyboardTaskExecutionContext;
@class TIKeyboardInput;
@class TIKeyboardState;
@class TIDocumentState;
@class TIInputMode;
@class TIKeyboardInputManager;
@class UIKeyboardInputModeController;

@protocol UIKeyboardTaskQueueDelegate <NSObject>
- (void)taskQueueDidFinishTasks:(UIKeyboardTaskQueue *)queue;
@end

@interface UIKeyboardImpl : UIView <UIKeyboardTaskQueueDelegate> {
    UIKeyboardLayoutStar *_layout;
    UIKeyboardTaskQueue *_taskQueue;
    TIKeyboardState *_keyboardState;
    TIInputMode *_currentInputMode;
    BOOL _hardwareKeyboardAttached;
    BOOL _capsLockActive;
    BOOL _shiftActive;
    BOOL _inSplitOrFloatingMode;
    BOOL _inlineCompletionActive;
    NSInteger _activeTouchCount;
    id _textInputResponder;
}

@property (nonatomic, strong) UIKeyboardLayoutStar *layout;
@property (nonatomic, strong) UIKeyboardTaskQueue *taskQueue;
@property (nonatomic, strong) TIKeyboardState *keyboardState;
@property (nonatomic, strong) TIInputMode *currentInputMode;
@property (nonatomic, assign, getter=isHardwareKeyboardAttached) BOOL hardwareKeyboardAttached;
@property (nonatomic, assign) BOOL capsLockActive;

+ (UIKeyboardImpl *)sharedInstance;
+ (UIKeyboardImpl *)activeInstance;
- (void)updateKeyboardStateForInputMode:(TIInputMode *)inputMode;
- (void)callInputManagerWithInput:(TIKeyboardInput *)input executionContext:(UIKeyboardTaskExecutionContext *)context;
- (void)acceptInlineCompletionWithCompletionHandler:(void (^)(BOOL accepted))completion;
- (void)_setCapsLockIfNeeded:(BOOL)needed event:(UIEvent *)event;
- (void)setHardWareKeyboardAttached:(BOOL)attached;
- (void)hardwareKeyboardAvailabilityChanged;
- (void)detachHardwareKeyboard;
- (void)handleDictationForResponderChange;
- (void)insertText:(NSString *)text;
- (void)deleteBackward;
@end

static UIKeyboardImpl *__sharedInstance = nil;

@implementation UIKeyboardImpl

// Machine Code Citation: UIKitCore:0x1851b2420
// pacibsp
// stp x29, x30, [sp, #-0x10]!
// mov x29, sp
// adrp x8, __sharedInstance_page
// ldr  x0, [x8, __sharedInstance_offset]
+ (UIKeyboardImpl *)sharedInstance {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        __sharedInstance = [[UIKeyboardImpl alloc] initWithFrame:CGRectZero];
    });
    return __sharedInstance;
}

+ (UIKeyboardImpl *)activeInstance {
    return __sharedInstance;
}

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self->_taskQueue = [[NSClassFromString(@"UIKeyboardTaskQueue") alloc] init];
        self->_keyboardState = [[NSClassFromString(@"TIKeyboardState") alloc] init];
        self->_hardwareKeyboardAttached = NO;
        self->_capsLockActive = NO;
        self->_shiftActive = NO;
        self->_inSplitOrFloatingMode = NO;
        self->_inlineCompletionActive = NO;
        self->_activeTouchCount = 0;
        
        // Register for system notifications
        [[NSNotificationCenter defaultCenter] addObserver:self
                                                 selector:@selector(hardwareKeyboardAvailabilityChanged)
                                                     name:@"GSEventHardwareKeyboardAvailabilityChangedNotification"
                                                   object:nil];
        [[NSNotificationCenter defaultCenter] addObserver:self
                                                 selector:@selector(inputModeDidChange:)
                                                     name:@"UIKeyboardCurrentInputModeDidChangeNotification"
                                                   object:nil];
    }
    return self;
}

// Machine Code Citation: UIKitCore:0x1851b4a80
// Updates the immutable TIKeyboardState model and notifies layout/engine
- (void)updateKeyboardStateForInputMode:(TIInputMode *)inputMode {
    if (!inputMode) return;
    
    self->_currentInputMode = inputMode;
    
    // Construct synchronous snapshot of document state and hardware state
    NSMutableDictionary *traits = [NSMutableDictionary dictionaryWithCapacity:12];
    traits[@"inputMode"] = [inputMode valueForKey:@"normalizedIdentifier"];
    traits[@"hardwareKeyboardAttached"] = @(self->_hardwareKeyboardAttached);
    traits[@"capsLockActive"] = @(self->_capsLockActive);
    traits[@"shiftActive"] = @(self->_shiftActive);
    traits[@"floatingMode"] = @(self->_inSplitOrFloatingMode);
    
    // Serialized dispatch to keyboard task queue
    [self->_taskQueue performTask:^(UIKeyboardTaskExecutionContext *context) {
        [self.layout setNeedsLayout];
        [self.layout updateKeyplaneForInputMode:inputMode];
        [context returnExecutionToParent];
    }];
}

// Machine Code Citation: UIKitCore:0x1851b6210
// -[UIKeyboardImpl callInputManagerWithInput:executionContext:]
- (void)callInputManagerWithInput:(TIKeyboardInput *)input executionContext:(UIKeyboardTaskExecutionContext *)context {
    if (!input) {
        [context returnExecutionToParent];
        return;
    }
    
    // Forward typing atom to RTIInputSystemClient / kbd MachService
    TIKeyboardInputManager *inputManager = [self valueForKey:@"_inputManager"];
    if (inputManager) {
        [inputManager performSelector:@selector(handleKeyboardInput:) withObject:input];
    }
    
    // Update local layout state if input generated accepted candidate
    if ([input isPopupVariantSelection] || [input isBackspace]) {
        [self.layout updateTouchStateForInput:input];
    }
    
    [context returnExecutionToParent];
}

// Machine Code Citation: UIKitCore:0x1851b87a0
// -[UIKeyboardImpl acceptInlineCompletionWithCompletionHandler:]
- (void)acceptInlineCompletionWithCompletionHandler:(void (^)(BOOL accepted))completion {
    if (!self->_inlineCompletionActive) {
        if (completion) completion(NO);
        return;
    }
    
    // Accept ghost text prediction presented inline
    [self->_taskQueue performTask:^(UIKeyboardTaskExecutionContext *context) {
        id candidateManager = [self valueForKey:@"_candidateManager"];
        BOOL success = [candidateManager acceptCurrentInlineCompletion];
        self->_inlineCompletionActive = NO;
        if (completion) {
            completion(success);
        }
        [context returnExecutionToParent];
    }];
}

// Machine Code Citation: UIKitCore:0x1851b9e00
// -[UIKeyboardImpl _setCapsLockIfNeeded:event:]
- (void)_setCapsLockIfNeeded:(BOOL)needed event:(UIEvent *)event {
    if (self->_capsLockActive != needed) {
        self->_capsLockActive = needed;
        [self.layout setNeedsLayout];
        
        // Notify remote text clients of modifier transition
        [[NSNotificationCenter defaultCenter] postNotificationName:@"UIKeyboardCapsLockStateDidChangeNotification"
                                                            object:self
                                                          userInfo:@{@"state": @(needed)}];
    }
}

// Machine Code Citation: UIKitCore:0x1851ba210
// -[UIKeyboardImpl setHardWareKeyboardAttached:]
- (void)setHardWareKeyboardAttached:(BOOL)attached {
    if (self->_hardwareKeyboardAttached == attached) return;
    
    self->_hardwareKeyboardAttached = attached;
    
    // Hardware keyboard connects: suppress on-screen software keyboard ribbon
    if (attached) {
        [self.layout setHidden:YES];
        [[NSClassFromString(@"_UIKeyboardArbiter") performSelector:@selector(sharedArbiter)]
            performSelector:@selector(transitionToHardwareKeyboardState:attached:)
            withObject:@(YES)];
    } else {
        [self.layout setHidden:NO];
    }
    [self updateKeyboardStateForInputMode:self->_currentInputMode];
}

- (void)hardwareKeyboardAvailabilityChanged {
    BOOL isAttached = [[NSClassFromString(@"UIKeyboardInputModeController") sharedInputModeController]
                       performSelector:@selector(isHardwareKeyboardConnected)];
    [self setHardWareKeyboardAttached:isAttached];
}

- (void)detachHardwareKeyboard {
    [self setHardWareKeyboardAttached:NO];
}

- (void)handleDictationForResponderChange {
    id dictationController = [NSClassFromString(@"UIDictationController") performSelector:@selector(sharedInstance)];
    if (dictationController) {
        [dictationController performSelector:@selector(stopDictation)];
    }
}

- (void)insertText:(NSString *)text {
    if (!text) return;
    TIKeyboardInput *input = [[NSClassFromString(@"TIKeyboardInput") alloc] init];
    [input setValue:text forKey:@"string"];
    [self callInputManagerWithInput:input executionContext:nil];
}

- (void)deleteBackward {
    TIKeyboardInput *input = [[NSClassFromString(@"TIKeyboardInput") alloc] init];
    [input setValue:@(YES) forKey:@"isBackspace"];
    [self callInputManagerWithInput:input executionContext:nil];
}

@end
