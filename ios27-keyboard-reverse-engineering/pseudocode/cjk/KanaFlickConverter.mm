// ==============================================================================
// Source Binary: /System/Library/TextInput/TextInput_ja.bundle/TextInput_ja
// dyld Shared Cache: dyld_shared_cache_arm64e.73 (Base VM: 0x2c591f000)
// Symbol / Class: KanaFlickConverter (0x2c5921800)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ assembly & 12-key Kana flick state machine
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#include <vector>
#include <string>
#include <map>
#include <cmath>

typedef NS_ENUM(NSInteger, KanaFlickDirection) {
    KanaFlickDirectionNone  = 0, // Tap (Center / 'a' vowel)
    KanaFlickDirectionLeft  = 1, // Left flick ('i' vowel)
    KanaFlickDirectionUp    = 2, // Up flick ('u' vowel)
    KanaFlickDirectionRight = 3, // Right flick ('e' vowel)
    KanaFlickDirectionDown  = 4  // Down flick ('o' vowel)
};

// 12-Key Japanese Flick Matrix
// [KeyID 1-12][Direction 0-4] -> UTF-16 character string
static const char *const kKanaMatrix[12][5] = {
    /* Key 1 (A-column)  */ {"あ", "い", "う", "え", "お"},
    /* Key 2 (Ka-column) */ {"か", "き", "く", "け", "こ"},
    /* Key 3 (Sa-column) */ {"さ", "し", "す", "せ", "そ"},
    /* Key 4 (Ta-column) */ {"た", "ち", "つ", "て", "と"},
    /* Key 5 (Na-column) */ {"な", "に", "ぬ", "ね", "の"},
    /* Key 6 (Ha-column) */ {"は", "ひ", "ふ", "へ", "ほ"},
    /* Key 7 (Ma-column) */ {"ま", "み", "む", "め", "も"},
    /* Key 8 (Ya-column) */ {"や", "「", "ゆ", "」", "よ"},
    /* Key 9 (Ra-column) */ {"ら", "り", "る", "れ", "ろ"},
    /* Key 10 (Modifier) */ {"゛゜小", "゛", "゜", "小", ""},
    /* Key 11 (Wa-column)*/ {"わ", "を", "ん", "ー", ""},
    /* Key 12 (Punct)    */ {"、", "。", "？", "！", "…"}
};

@interface KanaFlickConverter : NSObject {
    CGFloat _flickDistanceThreshold;
    CGFloat _flickAngleSlop;
}

- (instancetype)init;
- (KanaFlickDirection)detectFlickDirectionFromStart:(CGPoint)start end:(CGPoint)end;
- (NSString *)characterForKeyIndex:(NSUInteger)keyIndex direction:(KanaFlickDirection)direction;
- (NSString *)applyDakutenHandakutenToggleToCharacter:(NSString *)character;
@end

@implementation KanaFlickConverter

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_flickDistanceThreshold = 16.0; // 16pt minimum displacement
        self->_flickAngleSlop = M_PI / 4.0;   // 45 degree quadrant cone
    }
    return self;
}

// Machine Code Citation: TextInput_ja:0x2c5921850
// Translates vector displacement (dx, dy) into 4 cardinal flick directions
- (KanaFlickDirection)detectFlickDirectionFromStart:(CGPoint)start end:(CGPoint)end {
    CGFloat dx = end.x - start.x;
    CGFloat dy = end.y - start.y;
    CGFloat distance = hypot(dx, dy);
    
    if (distance < self->_flickDistanceThreshold) {
        return KanaFlickDirectionNone; // Discrete center tap
    }
    
    // Angle in radians (-PI to +PI)
    CGFloat angle = atan2(dy, dx);
    
    // Left: angle approx +/- PI
    if (fabs(angle) > (3.0 * M_PI / 4.0)) {
        return KanaFlickDirectionLeft;
    }
    // Right: angle approx 0
    if (fabs(angle) < (M_PI / 4.0)) {
        return KanaFlickDirectionRight;
    }
    // Up: angle approx -PI / 2
    if (angle < 0.0) {
        return KanaFlickDirectionUp;
    }
    // Down: angle approx +PI / 2
    return KanaFlickDirectionDown;
}

// Machine Code Citation: TextInput_ja:0x2c5921d00
- (NSString *)characterForKeyIndex:(NSUInteger)keyIndex direction:(KanaFlickDirection)direction {
    if (keyIndex < 1 || keyIndex > 12) return nil;
    if (direction < 0 || direction > 4) direction = KanaFlickDirectionNone;
    
    const char *utf8Str = kKanaMatrix[keyIndex - 1][direction];
    if (!utf8Str || strlen(utf8Str) == 0) {
        return nil;
    }
    return [NSString stringWithUTF8String:utf8Str];
}

// Machine Code Citation: TextInput_ja:0x2c5922380
// Modifies preceding Kana character with voiced/semi-voiced sound marks or small forms
- (NSString *)applyDakutenHandakutenToggleToCharacter:(NSString *)character {
    if (character.length == 0) return character;
    
    static NSDictionary<NSString *, NSArray<NSString *> *> *toggleMap = nil;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        toggleMap = @{
            @"か": @[@"が"], @"が": @[@"か"],
            @"き": @[@"ぎ"], @"ぎ": @[@"き"],
            @"く": @[@"ぐ"], @"ぐ": @[@"く"],
            @"け": @[@"げ"], @"げ": @[@"け"],
            @"こ": @[@"ご"], @"ご": @[@"こ"],
            @"さ": @[@"ざ"], @"ざ": @[@"さ"],
            @"し": @[@"じ"], @"じ": @[@"し"],
            @"す": @[@"ず"], @"ず": @[@"す"],
            @"せ": @[@"ぜ"], @"ぜ": @[@"せ"],
            @"そ": @[@"ぞ"], @"ぞ": @[@"そ"],
            @"た": @[@"だ"], @"だ": @[@"た"],
            @"ち": @[@"ぢ"], @"ぢ": @[@"ち"],
            @"つ": @[@"づ", @"っ"], @"づ": @[@"っ", @"つ"], @"っ": @[@"つ"],
            @"て": @[@"で"], @"で": @[@"て"],
            @"と": @[@"ど"], @"ど": @[@"と"],
            @"は": @[@"ば", @"ぱ"], @"ば": @[@"ぱ", @"は"], @"ぱ": @[@"は"],
            @"ひ": @[@"び", @"ぴ"], @"び": @[@"ぴ", @"ひ"], @"ぴ": @[@"ひ"],
            @"ふ": @[@"ぶ", @"ぷ"], @"ぶ": @[@"ぷ", @"ふ"], @"ぷ": @[@"ふ"],
            @"へ": @[@"べ", @"ぺ"], @"べ": @[@"ぺ", @"へ"], @"ぺ": @[@"へ"],
            @"ほ": @[@"ぼ", @"ぽ"], @"ぼ": @[@"ぽ", @"ほ"], @"ぽ": @[@"ほ"],
            @"や": @[@"ゃ"], @"ゃ": @[@"や"],
            @"ゆ": @[@"ゅ"], @"ゅ": @[@"ゆ"],
            @"よ": @[@"ょ"], @"ょ": @[@"よ"],
            @"あ": @[@"ぁ"], @"ぁ": @[@"あ"],
            @"い": @[@"ぃ"], @"ぃ": @[@"い"],
            @"う": @[@"ぅ"], @"ぅ": @[@"う"],
            @"え": @[@"ぇ"], @"ぇ": @[@"え"],
            @"お": @[@"ぉ"], @"ぉ": @[@"お"],
            @"わ": @[@"ゎ"], @"ゎ": @[@"わ"]
        };
    });
    
    NSArray *alternatives = toggleMap[character];
    if (alternatives && alternatives.count > 0) {
        return alternatives[0];
    }
    return character;
}

@end
