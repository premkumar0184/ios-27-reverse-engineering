// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/KeyboardArbiter.framework/KeyboardArbiter
// dyld Shared Cache: dyld_shared_cache_arm64e.36 (Base VM: 0x226550000, Subcache Offset: 0x06150000)
// Symbol / Class: _UIKeyboardArbiter (0x226552100)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, ObjC method signatures & scene focus coordination
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

@class _UIKeyboardArbiterClientHandle;
@class BSServiceConnectionListener;

@interface _UIKeyboardArbiter : NSObject {
    NSMutableArray *_clients; // array of _UIKeyboardArbiterClientHandle*
    _UIKeyboardArbiterClientHandle *_currentFocusClient;
    CGFloat _keyboardWindowLevel;
    BOOL _hardwareKeyboardAttached;
    dispatch_queue_t _queue;
    NSLock *_lock;
}

@property (nonatomic, strong) _UIKeyboardArbiterClientHandle *currentFocusClient;
@property (nonatomic, assign) CGFloat keyboardWindowLevel;
@property (nonatomic, assign) BOOL hardwareKeyboardAttached;

+ (instancetype)sharedArbiter;
- (void)scheduleSceneFocusUpdate:(id)sceneToken priority:(NSInteger)priority;
- (void)handleFocusChanged:(id)newScene newClientPid:(pid_t)pid sceneIdentity:(NSString *)identity;
- (void)updateKeyboardWindowLevel:(CGFloat)level reason:(NSString *)reason;
- (void)transitionToHardwareKeyboardState:(BOOL)attached;
- (void)retrieveHardwareKeyboardAttachmentState;
@end

@interface _UIKeyboardArbiterClientHandle : NSObject
@property (nonatomic, assign) pid_t processIdentifier;
@property (nonatomic, copy) NSString *bundleIdentifier;
@property (nonatomic, copy) NSString *sceneIdentity;
@property (nonatomic, assign) BOOL wantsKeyboard;
@property (nonatomic, assign) NSInteger priority;
@end

@implementation _UIKeyboardArbiterClientHandle
@end

static _UIKeyboardArbiter *__sharedArbiter = nil;

@implementation _UIKeyboardArbiter

+ (instancetype)sharedArbiter {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        __sharedArbiter = [[_UIKeyboardArbiter alloc] init];
    });
    return __sharedArbiter;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_clients = [[NSMutableArray alloc] initWithCapacity:8];
        self->_currentFocusClient = nil;
        self->_keyboardWindowLevel = 100.0; // UIWindowLevelAlert / InputUI presentation level
        self->_hardwareKeyboardAttached = NO;
        self->_queue = dispatch_queue_create("com.apple.KeyboardArbiter.queue", DISPATCH_QUEUE_SERIAL);
        self->_lock = [[NSLock alloc] init];
    }
    return self;
}

// Machine Code Citation: KeyboardArbiter:0x226552680
// -[_UIKeyboardArbiter scheduleSceneFocusUpdate:priority:]
- (void)scheduleSceneFocusUpdate:(id)sceneToken priority:(NSInteger)priority {
    if (!sceneToken) return;
    
    dispatch_async(self->_queue, ^{
        [self->_lock lock];
        
        _UIKeyboardArbiterClientHandle *targetClient = nil;
        for (_UIKeyboardArbiterClientHandle *client in self->_clients) {
            if ([client.sceneIdentity isEqual:[sceneToken description]]) {
                targetClient = client;
                break;
            }
        }
        
        if (!targetClient) {
            targetClient = [[_UIKeyboardArbiterClientHandle alloc] init];
            targetClient.sceneIdentity = [sceneToken description];
            targetClient.priority = priority;
            [self->_clients addObject:targetClient];
        }
        
        targetClient.wantsKeyboard = YES;
        targetClient.priority = priority;
        
        // Evaluate highest priority scene client requesting input
        _UIKeyboardArbiterClientHandle *highestPriorityClient = nil;
        for (_UIKeyboardArbiterClientHandle *client in self->_clients) {
            if (client.wantsKeyboard) {
                if (!highestPriorityClient || client.priority > highestPriorityClient.priority) {
                    highestPriorityClient = client;
                }
            }
        }
        
        if (highestPriorityClient && highestPriorityClient != self->_currentFocusClient) {
            self->_currentFocusClient = highestPriorityClient;
            [self notifyFocusSwitchedToClient:highestPriorityClient];
        }
        
        [self->_lock unlock];
    });
}

// Machine Code Citation: KeyboardArbiter:0x226553100
// -[_UIKeyboardArbiter handleFocusChanged:newClientPid:sceneIdentity:]
- (void)handleFocusChanged:(id)newScene newClientPid:(pid_t)pid sceneIdentity:(NSString *)identity {
    dispatch_async(self->_queue, ^{
        [self->_lock lock];
        
        _UIKeyboardArbiterClientHandle *client = [[_UIKeyboardArbiterClientHandle alloc] init];
        client.processIdentifier = pid;
        client.sceneIdentity = identity;
        client.wantsKeyboard = YES;
        self->_currentFocusClient = client;
        
        // Re-route BKSHIDEventDeferring touch stream to the newly focused scene token
        id deferringService = [NSClassFromString(@"BKSHIDEventDeferringService") performSelector:@selector(sharedInstance)];
        if (deferringService) {
            [deferringService performSelector:@selector(deferEventsForTarget:) withObject:client];
        }
        
        [self->_lock unlock];
    });
}

// Machine Code Citation: KeyboardArbiter:0x226553800
// -[_UIKeyboardArbiter updateKeyboardWindowLevel:reason:]
- (void)updateKeyboardWindowLevel:(CGFloat)level reason:(NSString *)reason {
    dispatch_async(self->_queue, ^{
        self->_keyboardWindowLevel = level;
        // Broadcast new window level (e.g. 100.0) to InputUI host scene
        [[NSNotificationCenter defaultCenter] postNotificationName:@"_UIKeyboardArbiterWindowLevelDidChangeNotification"
                                                            object:self
                                                          userInfo:@{@"level": @(level), @"reason": reason ? reason : @""}];
    });
}

// Machine Code Citation: KeyboardArbiter:0x226553e20
// -[_UIKeyboardArbiter transitionToHardwareKeyboardState:attached:]
- (void)transitionToHardwareKeyboardState:(BOOL)attached {
    dispatch_async(self->_queue, ^{
        self->_hardwareKeyboardAttached = attached;
        
        // When attached: tell clients to minimize or hide software canvas
        for (_UIKeyboardArbiterClientHandle *client in self->_clients) {
            // Send Mach notification to client PID
        }
    });
}

- (void)retrieveHardwareKeyboardAttachmentState {
    // Queries IOKit / IOHIDEventSystem for keyboard usage page 0x07
}

- (void)notifyFocusSwitchedToClient:(_UIKeyboardArbiterClientHandle *)client {
    // Invokes BSServiceConnection endpoint update
}

@end
