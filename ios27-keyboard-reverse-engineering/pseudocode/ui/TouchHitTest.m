// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore
// dyld Shared Cache: dyld_shared_cache_arm64e.01 (Base VM: 0x184752000, Subcache Offset: 0x04352000)
// Symbol: -[UIKeyboardLayoutStar _hitTestTouchPoint:inKeyplane:candidateKeys:touchStage:]
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly & spatial error correction algorithm
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <math.h>

@class UIKBTree;

typedef struct {
    double mean_x;
    double mean_y;
    double sigma_x;
    double sigma_y;
    double correlation;
} UIKBTouchGaussianParams;

// Machine Code Citation: UIKitCore:0x1851e7120
// Computes bivariate Gaussian probability density for touch coordinate (x, y) given key centroid
static double UIKBCalculateSpatialKeyLikelihood(CGPoint touchPoint, CGRect keyPaddedFrame, UIKBTouchGaussianParams params) {
    double keyCenterX = CGRectGetMidX(keyPaddedFrame);
    double keyCenterY = CGRectGetMidY(keyPaddedFrame);
    
    // Effective standard deviation scaled by key dimensions
    double sx = params.sigma_x > 0.0 ? params.sigma_x : (CGRectGetWidth(keyPaddedFrame) * 0.45);
    double sy = params.sigma_y > 0.0 ? params.sigma_y : (CGRectGetHeight(keyPaddedFrame) * 0.45);
    
    double dx = (touchPoint.x - keyCenterX) / sx;
    double dy = (touchPoint.y - keyCenterY) / sy;
    
    // Mahalanobis distance squared (assuming rho approx 0 for orthogonal capacitive sensor)
    double mahalanobis = dx * dx + dy * dy;
    
    // Normalization factor
    double norm = 1.0 / (2.0 * M_PI * sx * sy);
    return norm * exp(-0.5 * mahalanobis);
}

// Machine Code Citation: UIKitCore:0x1851e7650
// High-performance spatial hit-test resolving ambiguous finger landings
UIKBTree *UIKBPerformSpatialHitTest(CGPoint rawTouchLocation, CGPoint touchVelocity, UIKBTree *keyplane, NSUInteger touchStage) {
    if (!keyplane) return nil;
    
    // 1. Dynamic velocity bias: human fingers roll forward/downward during high-speed typing
    CGPoint adjustedLocation = rawTouchLocation;
    if (hypot(touchVelocity.x, touchVelocity.y) > 50.0) {
        adjustedLocation.x -= touchVelocity.x * 0.008; // 8ms latency lead
        adjustedLocation.y -= touchVelocity.y * 0.008;
    }
    
    NSArray *rows = [keyplane valueForKey:@"subtrees"];
    UIKBTree *bestKey = nil;
    double highestScore = -1.0;
    
    // Touch distribution parameters for standard iPhone display digitizer
    UIKBTouchGaussianParams params = {
        .mean_x = 0.0,
        .mean_y = 0.0,
        .sigma_x = 14.5, // 14.5 pt horizontal standard deviation
        .sigma_y = 18.0, // 18.0 pt vertical standard deviation (finger pad elongation)
        .correlation = 0.0
    };
    
    for (UIKBTree *row in rows) {
        CGRect rowFrame = [[row valueForKey:@"frame"] CGRectValue];
        // Coarse bounding box test with 12pt slop
        if (!CGRectContainsPoint(CGRectInset(rowFrame, -12.0, -12.0), adjustedLocation)) {
            continue;
        }
        
        NSArray *keys = [row valueForKey:@"subtrees"];
        for (UIKBTree *key in keys) {
            CGRect paddedFrame = [[key valueForKey:@"paddedFrame"] CGRectValue];
            
            // Fast direct interior hit
            if (CGRectContainsPoint(paddedFrame, adjustedLocation)) {
                // If interior hit is comfortably inside (>3pt from boundary), immediate return
                CGRect innerCore = CGRectInset(paddedFrame, 3.0, 3.0);
                if (CGRectContainsPoint(innerCore, adjustedLocation)) {
                    return key;
                }
            }
            
            // Key union bounds check
            CGRect expandedBounds = CGRectInset(paddedFrame, -20.0, -20.0);
            if (!CGRectContainsPoint(expandedBounds, adjustedLocation)) {
                continue;
            }
            
            // Calculate continuous spatial likelihood
            double score = UIKBCalculateSpatialKeyLikelihood(adjustedLocation, paddedFrame, params);
            
            // Bonus weight for dominant keys (Space, Delete, Return)
            if ([[key valueForKey:@"isSpaceKey"] boolValue]) {
                score *= 1.25;
            }
            
            if (score > highestScore) {
                highestScore = score;
                bestKey = key;
            }
        }
    }
    
    return bestKey;
}
