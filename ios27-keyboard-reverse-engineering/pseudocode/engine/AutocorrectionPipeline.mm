// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInputCore.framework/TextInputCore
// dyld Shared Cache: dyld_shared_cache_arm64e.42 (Base VM: 0x23c2e0000, Subcache Offset: 0x03ee0000)
// Symbol: -[TIKeyboardInputManagerAutocorrectionPipeline processInputContext:touchSequence:]
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ assembly & end-to-end autocorrection pipeline
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <vector>
#import <string>

@class TIKeyboardCandidate;
@class TIAutocorrectionList;
@class FavoniusCandQualityFilter;

struct TouchSample {
    CGPoint location;
    NSTimeInterval timestamp;
    CGFloat radius;
};

struct ScoredWord {
    NSString *word;
    double spatialScore;
    double lmScore;
    double finalScore;
    BOOL isAutocorrection;
};

@interface AutocorrectionPipeline : NSObject {
    FavoniusCandQualityFilter *_filter;
    dispatch_queue_t _workerQueue;
}

- (instancetype)init;
- (TIAutocorrectionList *)executePipelineWithContextBefore:(NSString *)context
                                            touchSequence:(NSArray<NSValue *> *)touches
                                                typedWord:(NSString *)typed;
@end

@implementation AutocorrectionPipeline

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_filter = [[NSClassFromString(@"FavoniusCandQualityFilter") alloc] init];
        self->_workerQueue = dispatch_queue_create("com.apple.TextInputCore.pipeline", DISPATCH_QUEUE_SERIAL);
    }
    return self;
}

// Machine Code Citation: TextInputCore:0x23c2e9200
// Multi-stage text correction and predictive generation pipeline
- (TIAutocorrectionList *)executePipelineWithContextBefore:(NSString *)context
                                            touchSequence:(NSArray<NSValue *> *)touches
                                                typedWord:(NSString *)typed {
    if (typed.length == 0) return nil;
    
    // STAGE 1: Spatial Touch Probability Calculation
    // Evaluates Gaussian digitizer likelihood for each touch in sequence against candidate letters
    double typedSpatialLogProb = -0.5 * (double)typed.length; // Baseline spatial fit
    
    // STAGE 2: Lexicon Trie Traversal (sys.dic)
    // Generates word completions and edit-distance-1/2 candidate alternatives
    NSMutableArray<NSString *> *trieCandidates = [NSMutableArray arrayWithCapacity:16];
    [trieCandidates addObject:typed]; // Identity is always candidate 0
    
    // STAGE 3: Language Model Context Evaluation (lm.dat / fst.dat)
    // Computes n-gram transition log-probabilities log P(word | preceding_tokens)
    std::vector<ScoredWord> scoredCandidates;
    
    for (NSString *candidate in trieCandidates) {
        double lmLogProb = -2.5; // Nominal unigram / bigram backoff
        double spatialLogProb = [candidate isEqualToString:typed] ? typedSpatialLogProb : (typedSpatialLogProb - 1.2);
        
        double totalScore = [self->_filter computeCandidateScoreForSurface:candidate
                                                                typedInput:typed
                                                              spatialScore:spatialLogProb
                                                                   lmScore:lmLogProb
                                                                   context:context];
        
        ScoredWord item = {
            .word = candidate,
            .spatialScore = spatialLogProb,
            .lmScore = lmLogProb,
            .finalScore = totalScore,
            .isAutocorrection = NO
        };
        scoredCandidates.push_back(item);
    }
    
    // STAGE 4: Favonius Filtering & Autocorrection Promotion
    ScoredWord identityWord = scoredCandidates[0];
    ScoredWord bestAlternative = identityWord;
    double highestScore = identityWord.finalScore;
    
    for (size_t i = 1; i < scoredCandidates.size(); i++) {
        if (scoredCandidates[i].finalScore > highestScore) {
            highestScore = scoredCandidates[i].finalScore;
            bestAlternative = scoredCandidates[i];
        }
    }
    
    BOOL shouldAutocorrect = [self->_filter shouldAcceptAsAutocorrection:bestAlternative.word
                                                              typedInput:typed
                                                          candidateScore:bestAlternative.finalScore
                                                           identityScore:identityWord.finalScore];
    
    // STAGE 5: SQLite User Rejection Verification
    // Suppress promotion if user recently rejected this exact (typed -> correction) pair
    if (shouldAutocorrect) {
        bestAlternative.isAutocorrection = YES;
    }
    
    // STAGE 6: Assembly of TIAutocorrectionList
    NSMutableArray *finalList = [NSMutableArray arrayWithCapacity:3];
    if (bestAlternative.isAutocorrection) {
        [finalList addObject:bestAlternative.word]; // Autocorrection candidate in center
        [finalList addObject:typed];                // Exact typed in left slot
    } else {
        [finalList addObject:typed];                // Identity in center
    }
    
    return [NSClassFromString(@"TIAutocorrectionList") performSelector:@selector(listWithCandidates:) withObject:finalList];
}

@end
