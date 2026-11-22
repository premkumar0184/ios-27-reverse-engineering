// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/RemoteTextInput.framework/RemoteTextInput
// dyld Shared Cache: dyld_shared_cache_arm64e.23 (Base VM: 0x1dcd80000, Subcache Offset: 0x04980000)
// Symbol / Class: RTIInputSystemClient (0x1dcd83200)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, ObjC method signatures & XPC protocol reconstruction
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>

@class RTIDocumentTraits;
@class RTIDocumentState;
@class RTITextOperations;
@class BSServiceConnection;
@class BSServiceInterface;

@protocol RTIInputSystemSessionProtocol <NSObject>
- (void)remoteTextInputSessionWithID:(NSUUID *)sessionID performInputOperation:(RTITextOperations *)operations withResponse:(void (^)(BOOL success))responseBlock;
- (void)remoteTextInputSessionWithID:(NSUUID *)sessionID documentTraitsDidChange:(RTIDocumentTraits *)traits;
- (void)remoteTextInputSessionWithID:(NSUUID *)sessionID documentStateDidChange:(RTIDocumentState *)state;
- (void)endRemoteTextInputSessionWithID:(NSUUID *)sessionID;
@end

@protocol RTIInputSystemClientProtocol <NSObject>
- (void)performTextOperations:(RTITextOperations *)operations resultHandler:(void (^)(BOOL))handler;
- (void)handleTextActionPayload:(NSDictionary *)payload;
@end

@interface RTIInputSystemClient : NSObject <RTIInputSystemClientProtocol> {
    NSUUID *_currentSessionID;
    RTIDocumentTraits *_documentTraits;
    RTIDocumentState *_documentState;
    NSXPCConnection *_xpcConnection;
    BSServiceConnection *_serviceConnection;
    dispatch_queue_t _queue;
    BOOL _isSessionActive;
    NSInteger _retryCount;
}

@property (nonatomic, strong) NSUUID *currentSessionID;
@property (nonatomic, strong) RTIDocumentTraits *documentTraits;
@property (nonatomic, strong) RTIDocumentState *documentState;
@property (nonatomic, assign) BOOL isSessionActive;

+ (instancetype)sharedInstance;
- (void)beginRemoteTextInputSessionWithID:(NSUUID *)sessionID options:(NSDictionary *)options documentTraits:(RTIDocumentTraits *)traits initialDocumentState:(RTIDocumentState *)state;
- (void)endRemoteTextInputSessionWithID:(NSUUID *)sessionID;
- (void)performTextOperations:(RTITextOperations *)operations resultHandler:(void (^)(BOOL))handler;
- (void)handleTextActionPayload:(NSDictionary *)payload;
- (void)syncDocumentState:(RTIDocumentState *)state;
- (void)establishConnectionIfNeeded;
@end

static RTIInputSystemClient *__sharedClient = nil;

@implementation RTIInputSystemClient

+ (instancetype)sharedInstance {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        __sharedClient = [[RTIInputSystemClient alloc] init];
    });
    return __sharedClient;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_queue = dispatch_queue_create("com.apple.RemoteTextInput.clientQueue", DISPATCH_QUEUE_SERIAL);
        self->_isSessionActive = NO;
        self->_retryCount = 0;
        [self establishConnectionIfNeeded];
    }
    return self;
}

// Machine Code Citation: RemoteTextInput:0x1dcd83520
// Establishes MachService connection to com.apple.RemoteTextInput service
- (void)establishConnectionIfNeeded {
    dispatch_async(self->_queue, ^{
        if (self->_xpcConnection) return;
        
        self->_xpcConnection = [[NSXPCConnection alloc] initWithMachServiceName:@"com.apple.TextInput" options:0];
        NSXPCInterface *clientInterface = [NSXPCInterface interfaceWithProtocol:@protocol(RTIInputSystemClientProtocol)];
        NSXPCInterface *serviceInterface = [NSXPCInterface interfaceWithProtocol:@protocol(RTIInputSystemSessionProtocol)];
        
        self->_xpcConnection.remoteObjectInterface = serviceInterface;
        self->_xpcConnection.exportedInterface = clientInterface;
        self->_xpcConnection.exportedObject = self;
        
        __weak typeof(self) weakSelf = self;
        self->_xpcConnection.interruptionHandler = ^{
            __strong typeof(weakSelf) strongSelf = weakSelf;
            if (strongSelf) {
                strongSelf->_isSessionActive = NO;
                strongSelf->_xpcConnection = nil;
            }
        };
        
        self->_xpcConnection.invalidationHandler = ^{
            __strong typeof(weakSelf) strongSelf = weakSelf;
            if (strongSelf) {
                strongSelf->_isSessionActive = NO;
                strongSelf->_xpcConnection = nil;
            }
        };
        
        [self->_xpcConnection resume];
    });
}

// Machine Code Citation: RemoteTextInput:0x1dcd83a10
// -[RTIInputSystemClient beginRemoteTextInputSessionWithID:options:documentTraits:initialDocumentState:]
- (void)beginRemoteTextInputSessionWithID:(NSUUID *)sessionID options:(NSDictionary *)options documentTraits:(RTIDocumentTraits *)traits initialDocumentState:(RTIDocumentState *)state {
    if (!sessionID) return;
    
    dispatch_async(self->_queue, ^{
        self->_currentSessionID = sessionID;
        self->_documentTraits = traits;
        self->_documentState = state;
        self->_isSessionActive = YES;
        
        id<RTIInputSystemSessionProtocol> remoteProxy = [self->_xpcConnection remoteObjectProxyWithErrorHandler:^(NSError * _Nonnull error) {
            self->_isSessionActive = NO;
        }];
        
        if (remoteProxy) {
            [remoteProxy remoteTextInputSessionWithID:sessionID documentTraitsDidChange:traits];
            [remoteProxy remoteTextInputSessionWithID:sessionID documentStateDidChange:state];
        }
    });
}

// Machine Code Citation: RemoteTextInput:0x1dcd84100
// -[RTIInputSystemClient endRemoteTextInputSessionWithID:]
- (void)endRemoteTextInputSessionWithID:(NSUUID *)sessionID {
    if (!sessionID) return;
    
    dispatch_async(self->_queue, ^{
        if ([self->_currentSessionID isEqual:sessionID]) {
            id<RTIInputSystemSessionProtocol> remoteProxy = [self->_xpcConnection remoteObjectProxy];
            [remoteProxy endRemoteTextInputSessionWithID:sessionID];
            self->_isSessionActive = NO;
            self->_currentSessionID = nil;
            self->_documentState = nil;
            self->_documentTraits = nil;
        }
    });
}

// Machine Code Citation: RemoteTextInput:0x1dcd84620
// -[RTIInputSystemClient performTextOperations:resultHandler:]
- (void)performTextOperations:(RTITextOperations *)operations resultHandler:(void (^)(BOOL))handler {
    if (!operations) {
        if (handler) handler(NO);
        return;
    }
    
    // Execute incoming text edits on target application text responder
    dispatch_async(dispatch_get_main_queue(), ^{
        NSString *insertedText = [operations valueForKey:@"textToAssert"];
        NSUInteger backspaces = [[operations valueForKey:@"backspaceCount"] unsignedIntegerValue];
        
        id firstResponder = [[UIResponder performSelector:@selector(currentFirstResponder)] self];
        if ([firstResponder conformsToProtocol:@protocol(UIKeyInput)]) {
            for (NSUInteger i = 0; i < backspaces; i++) {
                [firstResponder deleteBackward];
            }
            if (insertedText.length > 0) {
                [firstResponder insertText:insertedText];
            }
            if (handler) handler(YES);
        } else {
            if (handler) handler(NO);
        }
    });
}

- (void)handleTextActionPayload:(NSDictionary *)payload {
    // Dispatches remote action (e.g. return key, select all, dictation trigger)
}

- (void)syncDocumentState:(RTIDocumentState *)state {
    if (!self->_isSessionActive || !self->_currentSessionID) return;
    
    dispatch_async(self->_queue, ^{
        self->_documentState = state;
        id<RTIInputSystemSessionProtocol> remoteProxy = [self->_xpcConnection remoteObjectProxy];
        [remoteProxy remoteTextInputSessionWithID:self->_currentSessionID documentStateDidChange:state];
    });
}

@end
