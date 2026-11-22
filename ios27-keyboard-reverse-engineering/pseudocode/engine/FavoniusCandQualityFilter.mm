// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInputCore.framework/TextInputCore
// dyld Shared Cache: dyld_shared_cache_arm64e.42 (Base VM: 0x23c2e0000, Subcache Offset: 0x03ee0000)
// Symbol / Class: FavoniusCandQualityFilter (0x23c2e8100)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled C++ assembly & Favonius statistical candidate filter
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>

struct FavoniusWeights {
    double alpha_lm;        // Weight for language model n-gram probability (default 1.20)
    double beta_spatial;    // Weight for touch digitizer Gaussian spatial likelihood (default 0.95)
    double gamma_edit_dist; // Penalty per character insertion/deletion/substitution (default 1.80)
    double delta_case;      // Penalty for capitalization mismatch (default 0.75)
    double min_autocorrect_margin; // Confidence delta required over identity string (default 2.40)
};

@interface FavoniusCandQualityFilter : NSObject {
    FavoniusWeights _weights;
    NSSet<NSString *> *_suppressionBlacklist;
    NSMutableDictionary<NSString *, NSNumber *> *_rejectionHistoryPenalty;
}

- (instancetype)init;
- (double)computeCandidateScoreForSurface:(NSString *)candidate
                            typedInput:(NSString *)typed
                        spatialScore:(double)spatialLogProb
                             lmScore:(double)lmLogProb
                             context:(NSString *)precedingContext;
- (BOOL)shouldAcceptAsAutocorrection:(NSString *)candidate
                          typedInput:(NSString *)typed
                      candidateScore:(double)candScore
                       identityScore:(double)identScore;
- (NSUInteger)levenshteinDistance:(NSString *)s1 otherString:(NSString *)s2;
@end

@implementation FavoniusCandQualityFilter

- (instancetype)init {
    self = [super init];
    if (self) {
        self->_weights = (FavoniusWeights){
            .alpha_lm = 1.20,
            .beta_spatial = 0.95,
            .gamma_edit_dist = 1.80,
            .delta_case = 0.75,
            .min_autocorrect_margin = 2.40
        };
        self->_suppressionBlacklist = [[NSSet alloc] initWithObjects:@"profanity_filter_symbol", nil];
        self->_rejectionHistoryPenalty = [[NSMutableDictionary alloc] initWithCapacity:64];
    }
    return self;
}

// Machine Code Citation: TextInputCore:0x23c2e8340
// Evaluates composite log-likelihood score for candidate word
- (double)computeCandidateScoreForSurface:(NSString *)candidate
                            typedInput:(NSString *)typed
                        spatialScore:(double)spatialLogProb
                             lmScore:(double)lmLogProb
                             context:(NSString *)precedingContext {
    if (!candidate || !typed) return -1e9;
    
    // 1. Edit distance penalty
    NSUInteger editDistance = [self levenshteinDistance:candidate otherString:typed];
    double editPenalty = (double)editDistance * self->_weights.gamma_edit_dist;
    
    // 2. Case mismatch penalty
    double casePenalty = 0.0;
    if (typed.length > 0 && candidate.length > 0) {
        BOOL typedUpper = [[NSCharacterSet uppercaseLetterCharacterSet] characterIsMember:[typed characterAtIndex:0]];
        BOOL candUpper = [[NSCharacterSet uppercaseLetterCharacterSet] characterIsMember:[candidate characterAtIndex:0]];
        if (typedUpper != candUpper) {
            casePenalty = self->_weights.delta_case;
        }
    }
    
    // 3. User rejection history penalty dampening
    double rejectionPenalty = 0.0;
    NSNumber *penaltyRecord = self->_rejectionHistoryPenalty[[NSString stringWithFormat:@"%@->%@", typed, candidate]];
    if (penaltyRecord) {
        rejectionPenalty = [penaltyRecord doubleValue];
    }
    
    // Composite log-likelihood
    double totalScore = (self->_weights.alpha_lm * lmLogProb)
                      + (self->_weights.beta_spatial * spatialLogProb)
                      - editPenalty
                      - casePenalty
                      - rejectionPenalty;
    
    return totalScore;
}

// Machine Code Citation: TextInputCore:0x23c2e8a10
// Decides whether candidate displaces typed word automatically
- (BOOL)shouldAcceptAsAutocorrection:(NSString *)candidate
                          typedInput:(NSString *)typed
                      candidateScore:(double)candScore
                       identityScore:(double)identScore {
    if ([candidate isEqualToString:typed]) {
        return NO;
    }
    
    // Blacklist check
    if ([self->_suppressionBlacklist containsObject:candidate.lowercaseString]) {
        return NO;
    }
    
    // Margin gating: candidate score must exceed identity score by required confidence margin
    double delta = candScore - identScore;
    return (delta >= self->_weights.min_autocorrect_margin);
}

- (NSUInteger)levenshteinDistance:(NSString *)s1 otherString:(NSString *)s2 {
    NSUInteger len1 = s1.length;
    NSUInteger len2 = s2.length;
    if (len1 == 0) return len2;
    if (len2 == 0) return len1;
    
    std::vector<std::vector<NSUInteger>> d(len1 + 1, std::vector<NSUInteger>(len2 + 1));
    for (NSUInteger i = 0; i <= len1; i++) d[i][0] = i;
    for (NSUInteger j = 0; j <= len2; j++) d[0][j] = j;
    
    for (NSUInteger i = 1; i <= len1; i++) {
        for (NSUInteger j = 1; j <= len2; j++) {
            NSUInteger cost = ([s1 characterAtIndex:i - 1] == [s2 characterAtIndex:j - 1]) ? 0 : 1;
            d[i][j] = std::min({
                d[i - 1][j] + 1,       // deletion
                d[i][j - 1] + 1,       // insertion
                d[i - 1][j - 1] + cost // substitution
            });
        }
    }
    return d[len1][len2];
}

@end
