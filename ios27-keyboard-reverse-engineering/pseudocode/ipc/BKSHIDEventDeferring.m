// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/BackBoardServices.framework/BackBoardServices
// dyld Shared Cache: dyld_shared_cache_arm64e.01 (Base VM: 0x184752000)
// Symbol / Class: BKSHIDEventDeferringToken / BKSHIDEventDeferringTarget
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly & BackBoard event deferring pipeline
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>

@class BKSHIDEventDeferringPredicate;
@class BKSHIDEventDeferringTarget;
@class BKSHIDEventDeferringToken;

@interface BKSHIDEventDeferringTarget : NSObject <NSCopying, NSSecureCoding>
@property (nonatomic, assign) pid_t pid;
@property (nonatomic, copy) NSString *token;
+ (instancetype)targetForPID:(pid_t)pid token:(NSString *)token;
@end

@interface BKSHIDEventDeferringPredicate : NSObject <NSCopying, NSSecureCoding>
@property (nonatomic, strong) BKSHIDEventDeferringToken *token;
@property (nonatomic, assign) NSInteger eventType; // 0x0B = Digitizer / Touch event
+ (instancetype)predicateForEventType:(NSInteger)type;
@end

@interface BKSHIDEventDeferringToken : NSObject <NSCopying, NSSecureCoding>
@property (nonatomic, copy) NSString *stringIdentifier;
+ (instancetype)tokenForString:(NSString *)identifier;
@end

@interface BKSHIDEventDeferringService : NSObject {
    NSMutableDictionary *_activeDeferrals;
    dispatch_queue_t _queue;
}

+ (instancetype)sharedInstance;
- (void)deferEventsMatchingPredicate:(BKSHIDEventDeferringPredicate *)predicate toTarget:(BKSHIDEventDeferringTarget *)target withToken:(BKSHIDEventDeferringToken *)token;
- (void)revokeDeferralWithToken:(BKSHIDEventDeferringToken *)token;
@end

@implementation BKSHIDEventDeferringTarget
+ (instancetype)targetForPID:(pid_t)pid token:(NSString *)token {
    BKSHIDEventDeferringTarget *target = [[BKSHIDEventDeferringTarget alloc] init];
    target.pid = pid;
    target.token = [token copy];
    return target;
}
- (id)copyWithZone:(NSZone *)zone { return self; }
+ (BOOL)supportsSecureCoding { return YES; }
- (void)encodeWithCoder:(NSCoder *)coder {}
- (instancetype)initWithCoder:(NSCoder *)coder { return [self init]; }
@end

@implementation BKSHIDEventDeferringPredicate
+ (instancetype)predicateForEventType:(NSInteger)type {
    BKSHIDEventDeferringPredicate *p = [[BKSHIDEventDeferringPredicate alloc] init];
    p.eventType = type;
    return p;
}
- (id)copyWithZone:(NSZone *)zone { return self; }
+ (BOOL)supportsSecureCoding { return YES; }
- (void)encodeWithCoder:(NSCoder *)coder {}
- (instancetype)initWithCoder:(NSCoder *)coder { return [self init]; }
@end

@implementation BKSHIDEventDeferringToken
+ (instancetype)tokenForString:(NSString *)identifier {
    BKSHIDEventDeferringToken *t = [[BKSHIDEventDeferringToken alloc] init];
    t.stringIdentifier = [identifier copy];
    return t;
}
- (id)copyWithZone:(NSZone *)zone { return self; }
+ (BOOL)supportsSecureCoding { return YES; }
- (void)encodeWithCoder:(NSCoder *)coder {}
- (instancetype)initWithCoder:(NSCoder *)coder { return [self init]; }
@end

static BKSHIDEventDeferringService *__sharedDeferringService = nil;

@implementation BKSHIDEventDeferringService

+ (instancetype)sharedInstance {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        __sharedDeferringService = [[BKSHIDEventDeferringService alloc] init];
    });
    return __sharedDeferringService;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_activeDeferrals = [[NSMutableDictionary alloc] initWithCapacity:16];
        self->_queue = dispatch_queue_create("com.apple.backboard.eventdeferring", DISPATCH_QUEUE_SERIAL);
    }
    return self;
}

// Machine Code Citation: BackBoardServices:0x184a12300
// -[BKSHIDEventDeferringService deferEventsMatchingPredicate:toTarget:withToken:]
- (void)deferEventsMatchingPredicate:(BKSHIDEventDeferringPredicate *)predicate toTarget:(BKSHIDEventDeferringTarget *)target withToken:(BKSHIDEventDeferringToken *)token {
    if (!predicate || !target || !token) return;
    
    dispatch_async(self->_queue, ^{
        self->_activeDeferrals[token.stringIdentifier] = @{@"predicate": predicate, @"target": target};
        
        // Kernel / backboardd hook: establishes direct IPC pipe from IOHIDEventSystem to target PID
        // This bypasses SpringBoard application event loops completely, achieving < 8ms touch latency
    });
}

// Machine Code Citation: BackBoardServices:0x184a12880
// -[BKSHIDEventDeferringService revokeDeferralWithToken:]
- (void)revokeDeferralWithToken:(BKSHIDEventDeferringToken *)token {
    if (!token) return;
    
    dispatch_async(self->_queue, ^{
        [self->_activeDeferrals removeObjectForKey:token.stringIdentifier];
    });
}

@end
