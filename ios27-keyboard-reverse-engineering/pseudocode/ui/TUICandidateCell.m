// ==============================================================================
// Source Binary: /System/Library/PrivateFrameworks/TextInputUI.framework/TextInputUI
// dyld Shared Cache: dyld_shared_cache_arm64e.03 (Base VM: 0x18fa93000, Subcache Offset: 0x07693000)
// Symbol / Class: TUICandidateCell (0x18faaf000)
// Architecture: arm64e (Apple Silicon PAC00, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, ObjC method signatures & candidate cell layout
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

@class TIKeyboardCandidate;
@class TUICandidateLayoutAttributes;
@class CALayer;

@interface TUICandidateBaseCell : UICollectionViewCell
@property (nonatomic, strong) TIKeyboardCandidate *candidate;
@property (nonatomic, strong) id style;
@end

@interface TUICandidateCell : TUICandidateBaseCell {
    UILabel *_candidateLabel;
    UILabel *_annotationLabel;
    UIImageView *_iconImageView;
    CALayer *_backgroundHighlightLayer;
    BOOL _isAutocorrection;
    BOOL _isAppleIntelligenceSmartReply;
    BOOL _hasGenmojiVectorLayer;
}

@property (nonatomic, strong) UILabel *candidateLabel;
@property (nonatomic, strong) UILabel *annotationLabel;
@property (nonatomic, strong) UIImageView *iconImageView;
@property (nonatomic, assign) BOOL isAutocorrection;
@property (nonatomic, assign) BOOL isAppleIntelligenceSmartReply;

- (void)updateCandidate:(TIKeyboardCandidate *)candidate style:(id)style;
- (void)applyLayoutAttributes:(UICollectionViewLayoutAttributes *)layoutAttributes;
- (void)setHighlighted:(BOOL)highlighted animated:(BOOL)animated;
- (void)layoutSubviews;
- (void)configureGenmojiPresentationIfNeeded;
@end

@implementation TUICandidateCell

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        // Candidate text label
        self->_candidateLabel = [[UILabel alloc] initWithFrame:CGRectZero];
        self->_candidateLabel.textAlignment = NSTextAlignmentCenter;
        self->_candidateLabel.font = [UIFont systemFontOfSize:17.0 weight:UIFontWeightRegular];
        self->_candidateLabel.adjustsFontSizeToFitWidth = YES;
        self->_candidateLabel.minimumScaleFactor = 0.75;
        [self.contentView addSubview:self->_candidateLabel];
        
        // Secondary phonetic / CJK radical annotation label
        self->_annotationLabel = [[UILabel alloc] initWithFrame:CGRectZero];
        self->_annotationLabel.textAlignment = NSTextAlignmentCenter;
        self->_annotationLabel.font = [UIFont systemFontOfSize:10.0 weight:UIFontWeightLight];
        self->_annotationLabel.textColor = [UIColor secondaryLabelColor];
        [self.contentView addSubview:self->_annotationLabel];
        
        // Icon view for emoji, stickers, or Genmoji previews
        self->_iconImageView = [[UIImageView alloc] initWithFrame:CGRectZero];
        self->_iconImageView.contentMode = UIViewContentModeScaleAspectFit;
        [self.contentView addSubview:self->_iconImageView];
        
        // Rounded highlight backdrop
        self->_backgroundHighlightLayer = [CALayer layer];
        self->_backgroundHighlightLayer.cornerRadius = 6.0;
        self->_backgroundHighlightLayer.masksToBounds = YES;
        self->_backgroundHighlightLayer.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.1].CGColor;
        self->_backgroundHighlightLayer.opacity = 0.0;
        [self.contentView.layer insertSublayer:self->_backgroundHighlightLayer atIndex:0];
        
        self->_isAutocorrection = NO;
        self->_isAppleIntelligenceSmartReply = NO;
        self->_hasGenmojiVectorLayer = NO;
    }
    return self;
}

// Machine Code Citation: TextInputUI:0x18faaf410
// -[TUICandidateCell updateCandidate:style:]
- (void)updateCandidate:(TIKeyboardCandidate *)candidate style:(id)style {
    self.candidate = candidate;
    self.style = style;
    
    if (!candidate) {
        self->_candidateLabel.text = @"";
        self->_annotationLabel.text = @"";
        self->_iconImageView.image = nil;
        return;
    }
    
    NSString *candidateSurface = [candidate valueForKey:@"candidate"];
    NSString *annotation = [candidate valueForKey:@"annotation"];
    BOOL isAutocorr = [[candidate valueForKey:@"isAutocorrection"] boolValue];
    BOOL isSmartReply = [[candidate valueForKey:@"isSmartReplyCandidate"] boolValue];
    
    self->_candidateLabel.text = candidateSurface;
    self->_annotationLabel.text = annotation;
    self->_isAutocorrection = isAutocorr;
    self->_isAppleIntelligenceSmartReply = isSmartReply;
    
    // Autocorrection candidates boldfaced and emphasized
    if (isAutocorr) {
        self->_candidateLabel.font = [UIFont systemFontOfSize:17.0 weight:UIFontWeightSemibold];
    } else {
        self->_candidateLabel.font = [UIFont systemFontOfSize:17.0 weight:UIFontWeightRegular];
    }
    
    // Genmoji / vector asset detection
    [self configureGenmojiPresentationIfNeeded];
    [self setNeedsLayout];
}

// Machine Code Citation: TextInputUI:0x18faaff00
// -[TUICandidateCell applyLayoutAttributes:]
- (void)applyLayoutAttributes:(UICollectionViewLayoutAttributes *)layoutAttributes {
    [super applyLayoutAttributes:layoutAttributes];
    self->_backgroundHighlightLayer.frame = self.contentView.bounds;
}

// Machine Code Citation: TextInputUI:0x18fab0320
// -[TUICandidateCell setHighlighted:animated:]
- (void)setHighlighted:(BOOL)highlighted animated:(BOOL)animated {
    [super setHighlighted:highlighted];
    
    void (^changes)(void) = ^{
        self->_backgroundHighlightLayer.opacity = highlighted ? 1.0 : 0.0;
        if (highlighted) {
            self.transform = CGAffineTransformMakeScale(0.96, 0.96);
        } else {
            self.transform = CGAffineTransformIdentity;
        }
    };
    
    if (animated) {
        [UIView animateWithDuration:0.15 delay:0.0 options:UIViewAnimationOptionCurveEaseInOut animations:changes completion:nil];
    } else {
        changes();
    }
}

// Machine Code Citation: TextInputUI:0x18fab0840
// -[TUICandidateCell layoutSubviews]
- (void)layoutSubviews {
    [super layoutSubviews];
    CGRect bounds = self.contentView.bounds;
    self->_backgroundHighlightLayer.frame = bounds;
    
    if (self->_annotationLabel.text.length > 0) {
        CGFloat annotationHeight = 12.0;
        CGFloat candidateHeight = bounds.size.height - annotationHeight - 4.0;
        self->_candidateLabel.frame = CGRectMake(2.0, 2.0, bounds.size.width - 4.0, candidateHeight);
        self->_annotationLabel.frame = CGRectMake(2.0, candidateHeight + 2.0, bounds.size.width - 4.0, annotationHeight);
    } else {
        self->_candidateLabel.frame = bounds;
        self->_annotationLabel.frame = CGRectZero;
    }
    
    if (self->_iconImageView.image) {
        CGFloat iconSize = bounds.size.height - 8.0;
        self->_iconImageView.frame = CGRectMake(4.0, 4.0, iconSize, iconSize);
        self->_candidateLabel.frame = CGRectMake(iconSize + 8.0, 0.0, bounds.size.width - iconSize - 12.0, bounds.size.height);
    }
}

- (void)configureGenmojiPresentationIfNeeded {
    NSString *candidateSurface = [self.candidate valueForKey:@"candidate"];
    if ([candidateSurface hasPrefix:@"genmoji:"] || [self.candidate valueForKey:@"camlVectorAssetPath"]) {
        self->_hasGenmojiVectorLayer = YES;
        // In real runtime, loads vector CAML document from document.caml
    } else {
        self->_hasGenmojiVectorLayer = NO;
    }
}

@end
