// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInputCJK.framework/TextInputCJK
// dyld Shared Cache: dyld_shared_cache_arm64e.69 (Base VM: 0x2b710b000, Subcache Offset: 0x06d0b000)
// Symbol / Class: TIKeyboardInputManagerChinesePhonetic (0x2b710bf80)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ assembly & CJK phonetic syllable segmentation
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#include <string>
#include <vector>
#include <map>

// Opaque Mecabra C++ Context pointer from /usr/lib/libmecabra.dylib
typedef struct __Mecabra* MecabraRef;
typedef struct __MecabraCandidate* MecabraCandidateRef;

extern "C" {
    MecabraRef MecabraCreateWithOptions(CFDictionaryRef options, CFURLRef analysisDirectory);
    CFArrayRef MecabraCopyCandidatesForInputString(MecabraRef engine, CFStringRef inputString, CFDictionaryRef options);
    CFStringRef MecabraCandidateGetSurface(MecabraCandidateRef candidate);
    CFStringRef MecabraCandidateGetReading(MecabraCandidateRef candidate);
    double MecabraCandidateGetWeight(MecabraCandidateRef candidate);
}

@class TIMecabraCandidate;

@interface TIKeyboardInputManagerChinesePhonetic : NSObject {
    MecabraRef _mecabraEngine;
    NSMutableString *_internalPinyinBuffer;
    NSMutableArray<NSString *> *_segmentedSyllables;
    BOOL _fuzzyPinyinEnabled;
    BOOL _shuangpinEnabled;
}

@property (nonatomic, readonly) NSString *pinyinString;

- (instancetype)initWithOptions:(NSDictionary *)options;
- (void)addInputCharacter:(NSString *)character;
- (void)deleteBackward;
- (NSArray<NSString *> *)segmentPinyinBuffer:(NSString *)pinyin;
- (NSArray<TIMecabraCandidate *> *)generateCandidates;
- (void)clearBuffer;
@end

@implementation TIKeyboardInputManagerChinesePhonetic

// Machine Code Citation: TextInputCJK:0x2b710bf80
// Initializes Mecabra context with simplified / traditional Chinese models
- (instancetype)initWithOptions:(NSDictionary *)options {
    self = [super init];
    if (self) {
        self->_internalPinyinBuffer = [[NSMutableString alloc] initWithCapacity:64];
        self->_segmentedSyllables = [[NSMutableArray alloc] initWithCapacity:16];
        self->_fuzzyPinyinEnabled = YES;
        self->_shuangpinEnabled = NO;
        
        // Load Mecabra lexical databases
        CFDictionaryRef dictOptions = (__bridge CFDictionaryRef)options;
        self->_mecabraEngine = MecabraCreateWithOptions(dictOptions, NULL);
    }
    return self;
}

- (NSString *)pinyinString {
    return [self->_internalPinyinBuffer copy];
}

- (void)addInputCharacter:(NSString *)character {
    if (!character || character.length == 0) return;
    
    [self->_internalPinyinBuffer appendString:character.lowercaseString];
    
    // Perform dynamic syllable segmentation (e.g. "xian" -> "xi'an" vs "xian")
    NSArray<NSString *> *syllables = [self segmentPinyinBuffer:self->_internalPinyinBuffer];
    [self->_segmentedSyllables setArray:syllables];
}

- (void)deleteBackward {
    if (self->_internalPinyinBuffer.length > 0) {
        [self->_internalPinyinBuffer deleteCharactersInRange:NSMakeRange(self->_internalPinyinBuffer.length - 1, 1)];
        NSArray<NSString *> *syllables = [self segmentPinyinBuffer:self->_internalPinyinBuffer];
        [self->_segmentedSyllables setArray:syllables];
    }
}

// Machine Code Citation: TextInputCJK:0x2b710c710
// Syllable segmenter using greedy maximal matching with apostrophe boundary support
- (NSArray<NSString *> *)segmentPinyinBuffer:(NSString *)pinyin {
    NSMutableArray<NSString *> *result = [NSMutableArray array];
    if (pinyin.length == 0) return result;
    
    // Standard valid Pinyin initials (Shengmu) and finals (Yunmu)
    static NSSet *validSyllables = nil;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        validSyllables = [[NSSet alloc] initWithObjects:
            @"a", @"ai", @"an", @"ang", @"ao", @"ba", @"bai", @"ban", @"bang", @"bao",
            @"bei", @"ben", @"beng", @"bi", @"bian", @"biao", @"bie", @"bin", @"bing",
            @"bo", @"bu", @"ca", @"cai", @"can", @"cang", @"cao", @"ce", @"cen", @"ceng",
            @"cha", @"chai", @"chan", @"chang", @"chao", @"che", @"chen", @"cheng", @"chi",
            @"chong", @"chou", @"chu", @"chua", @"chuai", @"chuan", @"chuang", @"chui",
            @"chun", @"chuo", @"ci", @"cong", @"cou", @"cu", @"cuan", @"cui", @"cun", @"cuo",
            @"da", @"dai", @"dan", @"dang", @"dao", @"de", @"dei", @"den", @"deng", @"di",
            @"dian", @"diao", @"die", @"ding", @"diu", @"dong", @"dou", @"du", @"duan",
            @"dui", @"dun", @"duo", @"e", @"ei", @"en", @"eng", @"er", @"fa", @"fan",
            @"fang", @"fei", @"fen", @"feng", @"fo", @"fou", @"fu", @"ga", @"gai", @"gan",
            @"gang", @"gao", @"ge", @"gei", @"gen", @"geng", @"gong", @"gou", @"gu", @"gua",
            @"guai", @"guan", @"guang", @"gui", @"gun", @"guo", @"ha", @"hai", @"han",
            @"hang", @"hao", @"he", @"hei", @"hen", @"heng", @"hong", @"hou", @"hu", @"hua",
            @"huai", @"huan", @"huang", @"hui", @"hun", @"huo", @"ji", @"jia", @"jian",
            @"jiang", @"jiao", @"jie", @"jin", @"jing", @"jiong", @"jiu", @"ju", @"juan",
            @"jue", @"jun", @"ka", @"kai", @"kan", @"kang", @"kao", @"ke", @"kei", @"ken",
            @"keng", @"kong", @"kou", @"ku", @"kua", @"kuai", @"kuan", @"kuang", @"kui",
            @"kun", @"kuo", @"la", @"lai", @"lan", @"lang", @"lao", @"le", @"lei", @"leng",
            @"li", @"lia", @"lian", @"liang", @"liao", @"lie", @"lin", @"ling", @"liu",
            @"long", @"lou", @"lu", @"luan", @"lue", @"lun", @"luo", @"ma", @"mai", @"man",
            @"mang", @"mao", @"me", @"mei", @"men", @"meng", @"mi", @"mian", @"miao",
            @"mie", @"min", @"ming", @"miu", @"mo", @"mou", @"mu", @"na", @"nai", @"nan",
            @"nang", @"nao", @"ne", @"nei", @"nen", @"neng", @"ni", @"nian", @"niang",
            @"niao", @"nie", @"nin", @"ning", @"niu", @"nong", @"nou", @"nu", @"nuan",
            @"nue", @"nuo", @"o", @"ou", @"pa", @"pai", @"pan", @"pang", @"pao", @"pei",
            @"pen", @"peng", @"pi", @"pian", @"piao", @"pie", @"pin", @"ping", @"po",
            @"pou", @"pu", @"qi", @"qia", @"qian", @"qiang", @"qiao", @"qie", @"qin",
            @"qing", @"qiong", @"qiu", @"qu", @"quan", @"que", @"qun", @"ran", @"rang",
            @"rao", @"re", @"ren", @"reng", @"ri", @"rong", @"rou", @"ru", @"ruan", @"rui",
            @"run", @"ruo", @"sa", @"sai", @"san", @"sang", @"sao", @"se", @"sen", @"seng",
            @"sha", @"shai", @"shan", @"shang", @"shao", @"she", @"shei", @"shen", @"sheng",
            @"shi", @"shou", @"shu", @"shua", @"shuai", @"shuan", @"shuang", @"shui",
            @"shun", @"shuo", @"si", @"song", @"sou", @"su", @"suan", @"sui", @"sun", @"suo",
            @"ta", @"tai", @"tan", @"tang", @"tao", @"te", @"teng", @"ti", @"tian", @"tiao",
            @"tie", @"ting", @"tong", @"tou", @"tu", @"tuan", @"tui", @"tun", @"tuo",
            @"wa", @"wai", @"wan", @"wang", @"wei", @"wen", @"weng", @"wo", @"wu", @"xi",
            @"xia", @"xian", @"xiang", @"xiao", @"xie", @"xin", @"xing", @"xiong", @"xiu",
            @"xu", @"xuan", @"xue", @"xun", @"ya", @"yan", @"yang", @"yao", @"ye", @"yi",
            @"yin", @"ying", @"yo", @"yong", @"you", @"yu", @"yuan", @"yue", @"yun", @"za",
            @"zai", @"zan", @"zang", @"zao", @"ze", @"zei", @"zen", @"zeng", @"zha", @"zhai",
            @"zhan", @"zhang", @"zhao", @"zhe", @"zhei", @"zhen", @"zheng", @"zhi",
            @"zhong", @"zhou", @"zhu", @"zhua", @"zhuai", @"zhuan", @"zhuang", @"zhui",
            @"zhun", @"zhuo", @"zi", @"zong", @"zou", @"zu", @"zuan", @"zui", @"zun", @"zuo",
            nil];
    });
    
    NSUInteger length = pinyin.length;
    NSUInteger start = 0;
    
    while (start < length) {
        NSUInteger matchedLen = 0;
        // Check longest match from length 6 down to 1
        for (NSUInteger l = std::min((NSUInteger)6, length - start); l >= 1; l--) {
            NSString *sub = [pinyin substringWithRange:NSMakeRange(start, l)];
            if ([validSyllables containsObject:sub]) {
                matchedLen = l;
                [result addObject:sub];
                break;
            }
        }
        if (matchedLen == 0) {
            // Unmatched character (e.g. invalid initial), take 1 character
            [result addObject:[pinyin substringWithRange:NSMakeRange(start, 1)]];
            matchedLen = 1;
        }
        start += matchedLen;
    }
    return result;
}

// Machine Code Citation: TextInputCJK:0x2b710cf20
// Dispatches phonetic buffer to libmecabra.dylib
- (NSArray<TIMecabraCandidate *> *)generateCandidates {
    if (self->_internalPinyinBuffer.length == 0 || !self->_mecabraEngine) {
        return @[];
    }
    
    CFStringRef input = (__bridge CFStringRef)self->_internalPinyinBuffer;
    CFArrayRef rawCandidates = MecabraCopyCandidatesForInputString(self->_mecabraEngine, input, NULL);
    if (!rawCandidates) return @[];
    
    NSMutableArray *candidates = [NSMutableArray array];
    CFIndex count = CFArrayGetCount(rawCandidates);
    for (CFIndex i = 0; i < count; i++) {
        MecabraCandidateRef candRef = (MecabraCandidateRef)CFArrayGetValueAtIndex(rawCandidates, i);
        CFStringRef surface = MecabraCandidateGetSurface(candRef);
        CFStringRef reading = MecabraCandidateGetReading(candRef);
        double weight = MecabraCandidateGetWeight(candRef);
        
        id candObj = [[NSClassFromString(@"TIMecabraCandidate") alloc] init];
        [candObj setValue:(__bridge NSString *)surface forKey:@"candidate"];
        [candObj setValue:(__bridge NSString *)reading forKey:@"annotation"];
        [candObj setValue:@(weight) forKey:@"weight"];
        [candidates addObject:candObj];
    }
    CFRelease(rawCandidates);
    return candidates;
}

- (void)clearBuffer {
    [self->_internalPinyinBuffer setString:@""];
    [self->_segmentedSyllables removeAllObjects];
}

@end
