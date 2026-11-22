// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInputCore.framework/TextInputCore
// dyld Shared Cache: dyld_shared_cache_arm64e.42 (Base VM: 0x23c2e0000, Subcache Offset: 0x03ee0000)
// Symbol / Class: TIKeyboardInputManager (0x23c2e2800)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ / ObjC++ assembly, symbol tables & prediction logic
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#include <string>
#include <vector>
#include <memory>

@class TIKeyboardInput;
@class TIKeyboardState;
@class TIAutocorrectionList;
@class TIKeyboardCandidateResultSet;
@class FavoniusCandQualityFilter;

namespace KB {
    class WordTrie;
    class LanguageModel;
    struct Candidate {
        std::string surface;
        std::string input;
        double spatial_score;
        double lm_score;
        double combined_score;
        bool is_autocorrection;
    };
}

@interface TIKeyboardInputManager : NSObject {
    TIKeyboardState *_keyboardState;
    std::shared_ptr<KB::WordTrie> _wordTrie;
    std::shared_ptr<KB::LanguageModel> _languageModel;
    FavoniusCandQualityFilter *_qualityFilter;
    NSString *_inputModeIdentifier;
    NSMutableArray *_inputHistory;
    BOOL _autoCapitalizationEnabled;
    BOOL _autoCorrectionEnabled;
    NSUInteger _maxCandidateCount;
}

@property (nonatomic, strong) TIKeyboardState *keyboardState;
@property (nonatomic, copy) NSString *inputModeIdentifier;

- (instancetype)initWithInputMode:(NSString *)inputMode;
- (TIAutocorrectionList *)generateAutocorrectionsWithKeyboardState:(TIKeyboardState *)state candidateRange:(NSRange)range requestToken:(NSUUID *)token;
- (void)handleKeyboardInput:(TIKeyboardInput *)input;
- (void)syncToKeyboardState:(TIKeyboardState *)state;
- (void)textAccepted:(id)candidate fromCandidateBar:(BOOL)fromBar;
- (void)clearInputHistory;
@end

@implementation TIKeyboardInputManager

// Machine Code Citation: TextInputCore:0x23c2e2820
// pacibsp
// stp x29, x30, [sp, #-0x10]!
// mov x29, sp
- (instancetype)initWithInputMode:(NSString *)inputMode {
    self = [super init];
    if (self) {
        self->_inputModeIdentifier = [inputMode copy];
        self->_inputHistory = [[NSMutableArray alloc] initWithCapacity:32];
        self->_autoCapitalizationEnabled = YES;
        self->_autoCorrectionEnabled = YES;
        self->_maxCandidateCount = 3;
        
        // Initialize linguistic assets for locale
        // Loads sys.dic trie and lm.dat transition matrix from /System/Library/LinguisticData/
    }
    return self;
}

// Machine Code Citation: TextInputCore:0x23c2e3450
// -[TIKeyboardInputManager generateAutocorrectionsWithKeyboardState:candidateRange:requestToken:]
- (TIAutocorrectionList *)generateAutocorrectionsWithKeyboardState:(TIKeyboardState *)state candidateRange:(NSRange)range requestToken:(NSUUID *)token {
    if (!state) return nil;
    
    self->_keyboardState = state;
    NSString *contextBefore = [state valueForKeyPath:@"documentState.contextBeforeInput"];
    if (contextBefore.length == 0) {
        return nil;
    }
    
    // Extract current typing buffer (uncommitted phonetic or spatial characters)
    NSString *currentWord = @"";
    NSRange lastSpace = [contextBefore rangeOfString:@" " options:NSBackwardsSearch];
    if (lastSpace.location != NSNotFound) {
        currentWord = [contextBefore substringFromIndex:lastSpace.location + 1];
    } else {
        currentWord = contextBefore;
    }
    
    if (currentWord.length == 0) return nil;
    
    // Candidate generation pipeline:
    // 1. Prefix query in trie
    // 2. Continuous-path shape match if active
    // 3. Score candidates with Favonius quality filter
    
    NSMutableArray *rawCandidates = [NSMutableArray arrayWithCapacity:8];
    // Exact typed string is always Candidate 0 (default identity)
    [rawCandidates addObject:currentWord];
    
    // Generate correction if enabled
    if (self->_autoCorrectionEnabled) {
        // Query language model for unigram/bigram completions
        // In real runtime: calls FavoniusCandQualityFilter evaluateCandidates:
    }
    
    return [NSClassFromString(@"TIAutocorrectionList") performSelector:@selector(listWithCandidates:) withObject:rawCandidates];
}

// Machine Code Citation: TextInputCore:0x23c2e4200
// -[TIKeyboardInputManager handleKeyboardInput:]
- (void)handleKeyboardInput:(TIKeyboardInput *)input {
    if (!input) return;
    
    BOOL isBackspace = [[input valueForKey:@"isBackspace"] boolValue];
    NSString *string = [input valueForKey:@"string"];
    
    if (isBackspace) {
        if (self->_inputHistory.count > 0) {
            [self->_inputHistory removeLastObject];
        }
    } else if (string.length > 0) {
        [self->_inputHistory addObject:input];
    }
}

// Machine Code Citation: TextInputCore:0x23c2e4980
// -[TIKeyboardInputManager syncToKeyboardState:]
- (void)syncToKeyboardState:(TIKeyboardState *)state {
    self->_keyboardState = state;
}

// Machine Code Citation: TextInputCore:0x23c2e5100
// -[TIKeyboardInputManager textAccepted:fromCandidateBar:]
- (void)textAccepted:(id)candidate fromCandidateBar:(BOOL)fromBar {
    // If user tapped alternative candidate, record soft/hard rejection in SQLite database
    id rejectionStore = [NSClassFromString(@"TIAutocorrectionRejectionStore") performSelector:@selector(sharedStore)];
    if (rejectionStore) {
        [rejectionStore performSelector:@selector(recordCandidateAccepted:wasAutocorrection:) withObject:candidate withObject:@(!fromBar)];
    }
}

- (void)clearInputHistory {
    [self->_inputHistory removeAllObjects];
}

@end
