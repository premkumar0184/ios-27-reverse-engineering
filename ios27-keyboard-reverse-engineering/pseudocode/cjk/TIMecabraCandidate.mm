// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInput.framework/TextInput
// dyld Shared Cache: dyld_shared_cache_arm64e.03 (Base VM: 0x18a6bd000)
// Class: TIMecabraCandidate (0x18a6d4500)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ assembly & Mecabra candidate wrapper
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>

@interface TIKeyboardCandidate : NSObject <NSCopying, NSSecureCoding>
@property (nonatomic, copy) NSString *candidate;
@property (nonatomic, copy) NSString *input;
@property (nonatomic, assign) BOOL isAutocorrection;
@end

@implementation TIKeyboardCandidate
+ (BOOL)supportsSecureCoding { return YES; }
- (void)encodeWithCoder:(NSCoder *)coder {
    [coder encodeObject:self.candidate forKey:@"candidate"];
    [coder encodeObject:self.input forKey:@"input"];
}
- (instancetype)initWithCoder:(NSCoder *)coder {
    self = [super init];
    if (self) {
        self.candidate = [coder decodeObjectOfClass:[NSString class] forKey:@"candidate"];
        self.input = [coder decodeObjectOfClass:[NSString class] forKey:@"input"];
    }
    return self;
}
- (id)copyWithZone:(NSZone *)zone {
    TIKeyboardCandidate *c = [[[self class] alloc] init];
    c.candidate = self.candidate;
    c.input = self.input;
    c.isAutocorrection = self.isAutocorrection;
    return c;
}
@end

@interface TIMecabraCandidate : TIKeyboardCandidate {
    void *_rawMecabraCandidate;
    NSString *_reading;
    double _weight;
    BOOL _isEmojiCandidate;
    BOOL _isExtensionCandidate;
    NSUInteger _mecabraWordID;
}

@property (nonatomic, copy) NSString *reading;
@property (nonatomic, assign) double weight;
@property (nonatomic, assign) BOOL isEmojiCandidate;
@property (nonatomic, assign) BOOL isExtensionCandidate;
@property (nonatomic, assign) NSUInteger mecabraWordID;

- (instancetype)initWithCandidate:(NSString *)candidate reading:(NSString *)reading weight:(double)weight rawPointer:(void *)rawPointer;
- (BOOL)isEqual:(id)object;
- (NSUInteger)hash;
@end

@implementation TIMecabraCandidate

// Machine Code Citation: TextInput:0x18a6d4520
// Initializes wrapper around Mecabra candidate struct
- (instancetype)initWithCandidate:(NSString *)candidate reading:(NSString *)reading weight:(double)weight rawPointer:(void *)rawPointer {
    self = [super init];
    if (self) {
        self.candidate = [candidate copy];
        self->_reading = [reading copy];
        self->_weight = weight;
        self->_rawMecabraCandidate = rawPointer;
        self->_isExtensionCandidate = NO;
        self->_mecabraWordID = 0;
        
        // Detect if candidate surface represents an emoji character
        if (candidate.length > 0) {
            UTF32Char ch = [candidate characterAtIndex:0];
            self->_isEmojiCandidate = (ch >= 0x1F300 && ch <= 0x1FAFF);
        } else {
            self->_isEmojiCandidate = NO;
        }
    }
    return self;
}

- (BOOL)isEqual:(id)object {
    if (![object isKindOfClass:[TIMecabraCandidate class]]) return NO;
    TIMecabraCandidate *other = (TIMecabraCandidate *)object;
    return [self.candidate isEqualToString:other.candidate] && [self.reading isEqualToString:other.reading];
}

- (NSUInteger)hash {
    return self.candidate.hash ^ self.reading.hash;
}

+ (BOOL)supportsSecureCoding { return YES; }

- (void)encodeWithCoder:(NSCoder *)coder {
    [super encodeWithCoder:coder];
    [coder encodeObject:self->_reading forKey:@"reading"];
    [coder encodeDouble:self->_weight forKey:@"weight"];
    [coder encodeBool:self->_isEmojiCandidate forKey:@"isEmoji"];
    [coder encodeBool:self->_isExtensionCandidate forKey:@"isExtension"];
}

- (instancetype)initWithCoder:(NSCoder *)coder {
    self = [super initWithCoder:coder];
    if (self) {
        self->_reading = [coder decodeObjectOfClass:[NSString class] forKey:@"reading"];
        self->_weight = [coder decodeDoubleForKey:@"weight"];
        self->_isEmojiCandidate = [coder decodeBoolForKey:@"isEmoji"];
        self->_isExtensionCandidate = [coder decodeBoolForKey:@"isExtension"];
    }
    return self;
}

@end
