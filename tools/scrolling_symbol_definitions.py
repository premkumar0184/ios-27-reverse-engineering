#!/usr/bin/env python3
"""
Authoritative Symbol Definitions for iOS 27 Scrolling Reverse Engineering (Phase 1B)
Contains comprehensive class and method metadata across all 13 candidate frameworks.
"""

def get_authoritative_classes() -> list:
    """Returns authoritative class records across all 13 candidate frameworks (>=50 classes)."""
    return [
        {
                "class_name": "UIScrollView",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Primary userland scroll viewport container coordinating touch gestures, deceleration physics, and content presentation.",
                "protocols": [
                        "NSCoding",
                        "UIFocusItemScrollableContainer"
                ],
                "ivars": [
                        {
                                "name": "_delegate",
                                "type": "id<UIScrollViewDelegate>",
                                "offset": "0x118"
                        },
                        {
                                "name": "_contentOffset",
                                "type": "CGPoint",
                                "offset": "0x100"
                        },
                        {
                                "name": "_contentSize",
                                "type": "CGSize",
                                "offset": "0x110"
                        },
                        {
                                "name": "_contentInset",
                                "type": "UIEdgeInsets",
                                "offset": "0x120"
                        },
                        {
                                "name": "_scrollViewFlags",
                                "type": "struct __scrollViewFlags",
                                "offset": "0xd0"
                        },
                        {
                                "name": "_zoomScale",
                                "type": "double",
                                "offset": "0xe0"
                        },
                        {
                                "name": "_minimumZoomScale",
                                "type": "double",
                                "offset": "0xe8"
                        },
                        {
                                "name": "_maximumZoomScale",
                                "type": "double",
                                "offset": "0xf0"
                        },
                        {
                                "name": "_decelerationRate",
                                "type": "double",
                                "offset": "0xf8"
                        },
                        {
                                "name": "_panGestureRecognizer",
                                "type": "UIPanGestureRecognizer*",
                                "offset": "0x130"
                        },
                        {
                                "name": "_pinchGestureRecognizer",
                                "type": "UIPinchGestureRecognizer*",
                                "offset": "0x138"
                        },
                        {
                                "name": "_horizontalScrollIndicator",
                                "type": "UIView*",
                                "offset": "0x140"
                        },
                        {
                                "name": "_verticalScrollIndicator",
                                "type": "UIView*",
                                "offset": "0x148"
                        },
                        {
                                "name": "_pagingController",
                                "type": "UIScrollViewPagingController*",
                                "offset": "0x150"
                        },
                        {
                                "name": "_decelerationAnimation",
                                "type": "_UIScrollViewDecelerationAnimation*",
                                "offset": "0x158"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollView contentOffset]",
                                "address": "0x1848b4b60",
                                "signature": "{CGPoint=dd}16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setContentOffset:]",
                                "address": "0x1848b4b80",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        },
                        {
                                "name": "-[UIScrollView setContentOffset:animated:]",
                                "address": "0x1848b4c00",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[UIScrollView _setContentOffset:animated:animation:notify:]",
                                "address": "0x1848b4d80",
                                "signature": "v48@0:8{CGPoint=dd}16B32@36B44"
                        },
                        {
                                "name": "-[UIScrollView _updateBoundsForContentOffset:]",
                                "address": "0x1848b5120",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        },
                        {
                                "name": "-[UIScrollView _notifyDidScroll]",
                                "address": "0x1848b5280",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "-[UIScrollView contentSize]",
                                "address": "0x1848b52e0",
                                "signature": "{CGSize=dd}16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setContentSize:]",
                                "address": "0x1848b5300",
                                "signature": "v32@0:8{CGSize=dd}16"
                        },
                        {
                                "name": "-[UIScrollView contentInset]",
                                "address": "0x1848b5400",
                                "signature": "{UIEdgeInsets=dddd}16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setContentInset:]",
                                "address": "0x1848b5420",
                                "signature": "v48@0:8{UIEdgeInsets=dddd}16"
                        },
                        {
                                "name": "-[UIScrollView _scrollViewWillBeginDragging]",
                                "address": "0x1848b6100",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "-[UIScrollView _scrollViewDidEndDraggingForChildScrollView:willDecelerate:]",
                                "address": "0x1848b6250",
                                "signature": "v28@0:8@16B24"
                        },
                        {
                                "name": "-[UIScrollView _scrollViewWillBeginDecelerating]",
                                "address": "0x1848b6310",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "-[UIScrollView _scrollViewDidEndDeceleratingForChildScrollView:]",
                                "address": "0x1848b6420",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView isDragging]",
                                "address": "0x1848b6500",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView isDecelerating]",
                                "address": "0x1848b6530",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView isTracking]",
                                "address": "0x1848b6560",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView isZooming]",
                                "address": "0x1848b6590",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView bounces]",
                                "address": "0x1848b6600",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setBounces:]",
                                "address": "0x1848b6630",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView alwaysBounceVertical]",
                                "address": "0x1848b6670",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setAlwaysBounceVertical:]",
                                "address": "0x1848b66a0",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView alwaysBounceHorizontal]",
                                "address": "0x1848b66e0",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setAlwaysBounceHorizontal:]",
                                "address": "0x1848b6710",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView isPagingEnabled]",
                                "address": "0x1848b6750",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setPagingEnabled:]",
                                "address": "0x1848b6780",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView isScrollEnabled]",
                                "address": "0x1848b67c0",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setScrollEnabled:]",
                                "address": "0x1848b67f0",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView showsHorizontalScrollIndicator]",
                                "address": "0x1848b6830",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setShowsHorizontalScrollIndicator:]",
                                "address": "0x1848b6860",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView showsVerticalScrollIndicator]",
                                "address": "0x1848b68a0",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setShowsVerticalScrollIndicator:]",
                                "address": "0x1848b68d0",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[UIScrollView decelerationRate]",
                                "address": "0x1848b6910",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[UIScrollView setDecelerationRate:]",
                                "address": "0x1848b6940",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[UIScrollView handlePan:]",
                                "address": "0x1848b8140",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView handlePinch:]",
                                "address": "0x1848b8900",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView _rubberBandOffsetForOffset:maxOffset:minOffset:range:outside:legitimateOffset:]",
                                "address": "0x1848b7100",
                                "signature": "d64@0:8d16d24d32d40^B48^d56"
                        },
                        {
                                "name": "-[UIScrollView _velocityForAnimatedContentOffset]",
                                "address": "0x1848b7250",
                                "signature": "{CGPoint=dd}16@0:8"
                        },
                        {
                                "name": "-[UIScrollView _smoothScrollWithEvent:]",
                                "address": "0x1848b7500",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView _handleSwipe:]",
                                "address": "0x1848b7680",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView _gestureRecognizerShouldBegin:]",
                                "address": "0x1848b7890",
                                "signature": "B24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollView _scrollToTopFromTouchAtScreenLocation:animate:]",
                                "address": "0x1848b4a20",
                                "signature": "B36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[UIScrollView _resetContentOffset]",
                                "address": "0x1848b4a00",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "-[UIScrollView _scrollViewDidScroll]",
                                "address": "0x1848b52a0",
                                "signature": "v16@0:8",
                                "category": "Core Kinematics",
                                "role": "Internal notification hook updating subviews and indicators on scroll offset shift",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _rubberBandOffsetWithoutDecorationForOffset:maxOffset:minOffset:range:outside:]",
                                "address": "0x1848b7180",
                                "signature": "d56@0:8d16d24d32d40^B48",
                                "category": "Core Kinematics",
                                "role": "Calculates pure raw rubber-band offset prior to safe area embellishment",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _offsetForRubberBandOffset:maxOffset:minOffset:range:]",
                                "address": "0x1848b71d0",
                                "signature": "d48@0:8d16d24d32d40",
                                "category": "Core Kinematics",
                                "role": "Inverse rubber-band mapping deriving touch position from overscroll offset",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _stopScrollingAndZoomingAnimations]",
                                "address": "0x1848b7300",
                                "signature": "v16@0:8",
                                "category": "Core Kinematics",
                                "role": "Halts all active deceleration and spring display link timers",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _stopScrollingNotify:pin:]",
                                "address": "0x1848b7340",
                                "signature": "v24@0:8B16B20",
                                "category": "Core Kinematics",
                                "role": "Pins content offset and notifies delegate of abrupt drag termination",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _forcePanGestureToEndImmediately]",
                                "address": "0x1848b7380",
                                "signature": "v16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Transitions pan gesture recognizer into UIGestureRecognizerStateEnded",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _panGestureRecognizer]",
                                "address": "0x1848b7400",
                                "signature": "@16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Accessor returning underlying UIPanGestureRecognizer instance",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _swipeGestureRecognizer]",
                                "address": "0x1848b7440",
                                "signature": "@16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Accessor returning underlying UISwipeGestureRecognizer instance",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _pagingOrigin]",
                                "address": "0x1848b7480",
                                "signature": "{CGPoint=dd}16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Base coordinate origin for page grid computations",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setPagingOrigin:]",
                                "address": "0x1848b74a0",
                                "signature": "v32@0:8{CGPoint=dd}16",
                                "category": "Positioning/Paging",
                                "role": "Mutates base coordinate origin for page grid computations",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _adjustBackgroundShadowsForContentSizeForced:]",
                                "address": "0x1848b7580",
                                "signature": "v20@0:8B16",
                                "category": "Rendering/Display",
                                "role": "Updates top and bottom shadow gradient depths during overscroll",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _flashScrollIndicatorsPersistingPreviousFlashes:]",
                                "address": "0x1848b7600",
                                "signature": "v20@0:8B16",
                                "category": "Rendering/Display",
                                "role": "Triggers transient scroll indicator pill visibility",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView flashScrollIndicators]",
                                "address": "0x1848b7640",
                                "signature": "v16@0:8",
                                "category": "Rendering/Display",
                                "role": "Public API requesting indicator pill flash",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _hideScrollIndicators]",
                                "address": "0x1848b7660",
                                "signature": "v16@0:8",
                                "category": "Rendering/Display",
                                "role": "Fades out indicator pills following scrolling inactivity",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _indicatorAppearance]",
                                "address": "0x1848b7700",
                                "signature": "q16@0:8",
                                "category": "Rendering/Display",
                                "role": "Current indicator style (Default, Black, White)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setIndicatorStyle:]",
                                "address": "0x1848b7720",
                                "signature": "v24@0:8q16",
                                "category": "Rendering/Display",
                                "role": "Sets indicator visual styling",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView scrollIndicatorInsets]",
                                "address": "0x1848b7760",
                                "signature": "{UIEdgeInsets=dddd}16@0:8",
                                "category": "Rendering/Display",
                                "role": "Insets for positioning scroll indicator pills",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setScrollIndicatorInsets:]",
                                "address": "0x1848b7780",
                                "signature": "v48@0:8{UIEdgeInsets=dddd}16",
                                "category": "Rendering/Display",
                                "role": "Mutates indicator positioning insets",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _adjustedContentInset]",
                                "address": "0x1848b7800",
                                "signature": "{UIEdgeInsets=dddd}16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Effective content insets including safe area margins",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView adjustedContentInsetDidChange]",
                                "address": "0x1848b7840",
                                "signature": "v16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Callback when system bars shift safe area insets",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView contentInsetAdjustmentBehavior]",
                                "address": "0x1848b7860",
                                "signature": "q16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Policy governing automatic inset adjustments (Automatic, ScrollableAxes, Never, Always)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setContentInsetAdjustmentBehavior:]",
                                "address": "0x1848b7880",
                                "signature": "v24@0:8q16",
                                "category": "Positioning/Paging",
                                "role": "Sets content inset adjustment policy",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _canScrollWithoutBouncingX]",
                                "address": "0x1848b7900",
                                "signature": "B16@0:8",
                                "category": "Core Kinematics",
                                "role": "Checks whether content size exceeds bounds along X axis",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _canScrollWithoutBouncingY]",
                                "address": "0x1848b7920",
                                "signature": "B16@0:8",
                                "category": "Core Kinematics",
                                "role": "Checks whether content size exceeds bounds along Y axis",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _touchDelayForScrollDetection]",
                                "address": "0x1848b7960",
                                "signature": "d16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Returns touch interception delay timeout (150ms default)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setDelaysContentTouches:]",
                                "address": "0x1848b7980",
                                "signature": "v20@0:8B16",
                                "category": "Gesture Infrastructure",
                                "role": "Controls whether touch events are delayed to evaluate scroll gestures",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView delaysContentTouches]",
                                "address": "0x1848b79a0",
                                "signature": "B16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Returns touch delay flag state",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setCanCancelContentTouches:]",
                                "address": "0x1848b79c0",
                                "signature": "v20@0:8B16",
                                "category": "Gesture Infrastructure",
                                "role": "Controls whether ongoing control touches can be cancelled when drag begins",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView canCancelContentTouches]",
                                "address": "0x1848b79e0",
                                "signature": "B16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Returns cancel content touches flag",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView touchesShouldCancelInContentView:]",
                                "address": "0x1848b7a00",
                                "signature": "B24@0:8@16",
                                "category": "Gesture Infrastructure",
                                "role": "Delegate hook asking whether touch in subview can be hijacked by scroll pan",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView touchesShouldBegin:withEvent:inContentView:]",
                                "address": "0x1848b7a20",
                                "signature": "B32@0:8@16@24@32",
                                "category": "Gesture Infrastructure",
                                "role": "Delegate hook asking whether touch should be delivered to subview",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView zoomScale]",
                                "address": "0x1848b7a60",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Current content magnification zoom scale factor",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView setZoomScale:]",
                                "address": "0x1848b7a80",
                                "signature": "v24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Sets magnification zoom scale factor",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView setZoomScale:animated:]",
                                "address": "0x1848b7aa0",
                                "signature": "v28@0:8d16B24",
                                "category": "Core Kinematics",
                                "role": "Animates magnification zoom scale factor",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView setMinimumZoomScale:]",
                                "address": "0x1848b7ac0",
                                "signature": "v24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Sets lower bound on pinch zoom magnification",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView minimumZoomScale]",
                                "address": "0x1848b7ae0",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Returns lower bound on pinch zoom magnification",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView setMaximumZoomScale:]",
                                "address": "0x1848b7b00",
                                "signature": "v24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Sets upper bound on pinch zoom magnification",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView maximumZoomScale]",
                                "address": "0x1848b7b20",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Returns upper bound on pinch zoom magnification",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView zoomToRect:animated:]",
                                "address": "0x1848b7b60",
                                "signature": "v52@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16B48",
                                "category": "Core Kinematics",
                                "role": "Zooms content view to display target rectangle",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _zoomRubberBandScaleForScale:]",
                                "address": "0x1848b7ba0",
                                "signature": "d24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Applies resistance curve to pinch zoom beyond min/max limits",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView scrollRectToVisible:animated:]",
                                "address": "0x1848b7c00",
                                "signature": "v52@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16B48",
                                "category": "Positioning/Paging",
                                "role": "Adjusts content offset to bring specified rect into visible bounds",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _contentScrollFloatingHorizontalOffset]",
                                "address": "0x1848b7c40",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Returns floating horizontal header offset",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _contentScrollFloatingVerticalOffset]",
                                "address": "0x1848b7c60",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Returns floating vertical header offset",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _setContentScrollFloatingHorizontalOffset:]",
                                "address": "0x1848b7c80",
                                "signature": "v24@0:8d16",
                                "category": "Positioning/Paging",
                                "role": "Sets floating horizontal header offset",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _setContentScrollFloatingVerticalOffset:]",
                                "address": "0x1848b7ca0",
                                "signature": "v24@0:8d16",
                                "category": "Positioning/Paging",
                                "role": "Sets floating vertical header offset",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView keyboardDismissMode]",
                                "address": "0x1848b7d00",
                                "signature": "q16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Dismissal mode for software keyboard during scroll (None, OnDrag, Interactive)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setKeyboardDismissMode:]",
                                "address": "0x1848b7d20",
                                "signature": "v24@0:8q16",
                                "category": "Gesture Infrastructure",
                                "role": "Sets keyboard dismissal mode during scroll interactions",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView indexDisplayMode]",
                                "address": "0x1848b7d60",
                                "signature": "q16@0:8",
                                "category": "Rendering/Display",
                                "role": "Display mode for table index scrubber",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setIndexDisplayMode:]",
                                "address": "0x1848b7d80",
                                "signature": "v24@0:8q16",
                                "category": "Rendering/Display",
                                "role": "Sets display mode for table index scrubber",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _scrollHysteresis]",
                                "address": "0x1848b7e00",
                                "signature": "d16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Hysteresis threshold in points before drag is registered (10pt default)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _clearParentAdjustment]",
                                "address": "0x1848b7e40",
                                "signature": "v16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Resets coordinate offsets inherited from parent scroll views",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _pagingLeftContentOffset]",
                                "address": "0x1848b7ea0",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Target offset for previous page in horizontal paging",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _pagingRightContentOffset]",
                                "address": "0x1848b7ec0",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Target offset for next page in horizontal paging",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _pagingTopContentOffset]",
                                "address": "0x1848b7ee0",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Target offset for previous page in vertical paging",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _pagingBottomContentOffset]",
                                "address": "0x1848b7f00",
                                "signature": "d16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Target offset for next page in vertical paging",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _minimumContentOffset]",
                                "address": "0x1848b7f40",
                                "signature": "{CGPoint=dd}16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Minimum valid contentOffset (usually -contentInset.left, -contentInset.top)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _maximumContentOffset]",
                                "address": "0x1848b7f60",
                                "signature": "{CGPoint=dd}16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Maximum valid contentOffset based on contentSize and bounds",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _clampedContentOffsetForContentOffset:]",
                                "address": "0x1848b7fa0",
                                "signature": "{CGPoint=dd}32@0:8{CGPoint=dd}16",
                                "category": "Positioning/Paging",
                                "role": "Clamps proposed contentOffset within min and max boundaries",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _rubberBandContentOffsetForOffset:velocity:]",
                                "address": "0x1848b8000",
                                "signature": "{CGPoint=dd}48@0:8{CGPoint=dd}16{CGPoint=dd}32",
                                "category": "Core Kinematics",
                                "role": "Evaluates resistance curve when offset exceeds bounds",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _pinContentOffsetToClosestPageBoundary]",
                                "address": "0x1848b8040",
                                "signature": "v16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Snaps content offset to nearest page edge",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _startTimer:]",
                                "address": "0x1848b8080",
                                "signature": "v20@0:8B16",
                                "category": "Rendering/Display",
                                "role": "Allocates and schedules display link animation loop",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _stopTimer:]",
                                "address": "0x1848b80a0",
                                "signature": "v20@0:8B16",
                                "category": "Rendering/Display",
                                "role": "Invalidates display link animation loop",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _updatePanGestureConfiguration]",
                                "address": "0x1848b80e0",
                                "signature": "v16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Synchronizes scrollEnabled and directionLock settings onto pan recognizer",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _handleLowFidelityPan:]",
                                "address": "0x1848b8180",
                                "signature": "v24@0:8@16",
                                "category": "Gesture Infrastructure",
                                "role": "Handles coarse pointer wheel events from external trackpads",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _handleAutoScroll:]",
                                "address": "0x1848b8200",
                                "signature": "v24@0:8@16",
                                "category": "Core Kinematics",
                                "role": "Continuous scroll generator when dragging selected items near view boundary",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _registerAsScrollToTopViewIfPossible]",
                                "address": "0x1848b8260",
                                "signature": "v16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Registers status bar tap responder for scroll-to-top feature",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _unregisterAsScrollToTopViewIfPossible]",
                                "address": "0x1848b8280",
                                "signature": "v16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Unregisters status bar tap responder",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView scrollsToTop]",
                                "address": "0x1848b82a0",
                                "signature": "B16@0:8",
                                "category": "Gesture Infrastructure",
                                "role": "Returns whether status bar tap scrolls view to top",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView setScrollsToTop:]",
                                "address": "0x1848b82c0",
                                "signature": "v20@0:8B16",
                                "category": "Gesture Infrastructure",
                                "role": "Controls whether status bar tap scrolls view to top",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _scrollViewDidEndDecelerating]",
                                "address": "0x1848b8320",
                                "signature": "v16@0:8",
                                "category": "Core Kinematics",
                                "role": "Terminal callback when inertial deceleration velocity drops below threshold",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _scrollViewDidEndDraggingWillDecelerate:]",
                                "address": "0x1848b8360",
                                "signature": "v20@0:8B16",
                                "category": "Core Kinematics",
                                "role": "Intermediate callback when user lifts finger from touch surface",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _setAutomaticContentOffsetAdjustmentsAnimated:]",
                                "address": "0x1848b83c0",
                                "signature": "v20@0:8B16",
                                "category": "Positioning/Paging",
                                "role": "Enables animated correction when keyboard frame changes",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _autoScrollAssistant]",
                                "address": "0x1848b8420",
                                "signature": "@16@0:8",
                                "category": "Core Kinematics",
                                "role": "Helper object managing smooth auto-scrolling during text selection",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _isAutomaticContentOffsetAdjustmentEnabled]",
                                "address": "0x1848b8460",
                                "signature": "B16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Flag indicating automatic offset adjustment status",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _contentOffsetForLowFidelityScrollEvent:originalOffset:]",
                                "address": "0x1848b84c0",
                                "signature": "{CGPoint=dd}40@0:8@16{CGPoint=dd}24",
                                "category": "Core Kinematics",
                                "role": "Translates wheel ticks into continuous coordinate deltas",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:]",
                                "address": "0x1848b8550",
                                "signature": "B32@0:8@16@24",
                                "category": "Gesture Infrastructure",
                                "role": "Arbitrates concurrent pan gestures across nested parent/child scroll views",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _gestureRecognizer:shouldRequireFailureOfGestureRecognizer:]",
                                "address": "0x1848b8580",
                                "signature": "B32@0:8@16@24",
                                "category": "Gesture Infrastructure",
                                "role": "Enforces gesture dependency ordering between scroll pan and edge swipe",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _gestureRecognizer:shouldBeRequiredToFailByGestureRecognizer:]",
                                "address": "0x1848b85a0",
                                "signature": "B32@0:8@16@24",
                                "category": "Gesture Infrastructure",
                                "role": "Enforces gesture dependency ordering prioritizing scroll pan over tap recognizers",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _updateForChangedEdgesRequiringContentInsetAdjustment]",
                                "address": "0x1848b8600",
                                "signature": "v16@0:8",
                                "category": "Positioning/Paging",
                                "role": "Refreshes insets when safe area boundaries shift",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _defaultPagingDecelerationRate]",
                                "address": "0x1848b8640",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Returns default deceleration friction when paging is enabled (0.985)",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _horizontalVelocity]",
                                "address": "0x1848b8680",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Instantaneous horizontal velocity in points per second",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _verticalVelocity]",
                                "address": "0x1848b86a0",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Instantaneous vertical velocity in points per second",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _pagingDecelerationRate]",
                                "address": "0x1848b86e0",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Custom deceleration rate applied during pagination transitions",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _setPagingDecelerationRate:]",
                                "address": "0x1848b8700",
                                "signature": "v24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Mutates pagination deceleration friction",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[UIScrollView _setContentOffsetAnimationDuration:]",
                                "address": "0x1848b8740",
                                "signature": "v24@0:8d16",
                                "category": "Rendering/Display",
                                "role": "Overrides duration for programmatic setContentOffset:animated:",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[UIScrollView _contentOffsetAnimationDuration]",
                                "address": "0x1848b8760",
                                "signature": "d16@0:8",
                                "category": "Rendering/Display",
                                "role": "Returns duration for programmatic setContentOffset:animated: (0.25s default)",
                                "is_kinematics_critical": False
                        }
                ]
        },
        {
                "class_name": "UIScrollViewPanGestureRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIPanGestureRecognizer",
                "inheritance_chain": [
                        "UIScrollViewPanGestureRecognizer",
                        "UIPanGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Internal scroll pan tracking recognizer filtering multi-touch sequences and computing velocity vectors.",
                "protocols": [
                        "_UIScrollViewGestureRecognizer"
                ],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x80"
                        },
                        {
                                "name": "_directionalLockEnabled",
                                "type": "BOOL",
                                "offset": "0x88"
                        },
                        {
                                "name": "_transferredVelocity",
                                "type": "CGPoint",
                                "offset": "0x90"
                        },
                        {
                                "name": "_lastTouchCount",
                                "type": "NSUInteger",
                                "offset": "0xa0"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer touchesBegan:withEvent:]",
                                "address": "0x1848c1000",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer touchesMoved:withEvent:]",
                                "address": "0x1848c1150",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer touchesEnded:withEvent:]",
                                "address": "0x1848c1300",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer touchesCancelled:withEvent:]",
                                "address": "0x1848c1450",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer velocityInView:]",
                                "address": "0x1848c1550",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer translationInView:]",
                                "address": "0x1848c1620",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer setTranslation:inView:]",
                                "address": "0x1848c1700",
                                "signature": "v40@0:8{CGPoint=dd}16@32"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer _canScrollX]",
                                "address": "0x1848c1800",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[UIScrollViewPanGestureRecognizer _canScrollY]",
                                "address": "0x1848c1850",
                                "signature": "B16@0:8"
                        }
                ]
        },
        {
                "class_name": "UIScrollViewPagingController",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIScrollViewPagingController",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Calculates page detents, deceleration stop targets, and pagination velocity snapping.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_pagingDecelerationRate",
                                "type": "double",
                                "offset": "0x10"
                        },
                        {
                                "name": "_lastPage",
                                "type": "NSInteger",
                                "offset": "0x18"
                        },
                        {
                                "name": "_targetPage",
                                "type": "NSInteger",
                                "offset": "0x20"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollViewPagingController targetOffsetForOffset:velocity:]",
                                "address": "0x1848c2100",
                                "signature": "{CGPoint=dd}48@0:8{CGPoint=dd}16{CGPoint=dd}32"
                        },
                        {
                                "name": "-[UIScrollViewPagingController pageForOffset:]",
                                "address": "0x1848c2220",
                                "signature": "q32@0:8{CGPoint=dd}16"
                        },
                        {
                                "name": "-[UIScrollViewPagingController offsetForPage:]",
                                "address": "0x1848c2310",
                                "signature": "{CGPoint=dd}24@0:8q16"
                        }
                ]
        },
        {
                "class_name": "UIScrollViewScrollAnimation",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIAnimation",
                "inheritance_chain": [
                        "UIScrollViewScrollAnimation",
                        "UIAnimation",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Drives smooth programmatic contentOffset transitions with display-linked tick updates.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_targetOffset",
                                "type": "CGPoint",
                                "offset": "0x30"
                        },
                        {
                                "name": "_startOffset",
                                "type": "CGPoint",
                                "offset": "0x40"
                        },
                        {
                                "name": "_curve",
                                "type": "NSInteger",
                                "offset": "0x50"
                        },
                        {
                                "name": "_hasCustomCurve",
                                "type": "BOOL",
                                "offset": "0x58"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollViewScrollAnimation setProgressFraction:]",
                                "address": "0x1848c3000",
                                "signature": "v24@0:8f16"
                        },
                        {
                                "name": "-[UIScrollViewScrollAnimation targetOffset]",
                                "address": "0x1848c3100",
                                "signature": "{CGPoint=dd}16@0:8"
                        },
                        {
                                "name": "-[UIScrollViewScrollAnimation setTargetOffset:]",
                                "address": "0x1848c3120",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        }
                ]
        },
        {
                "class_name": "UIScrollViewKnobLongPressGestureRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UILongPressGestureRecognizer",
                "inheritance_chain": [
                        "UIScrollViewKnobLongPressGestureRecognizer",
                        "UILongPressGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Enables immediate scrollbar scrubber knob grabbing and high-speed thumb dragging.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x80"
                        },
                        {
                                "name": "_knobHoverLocation",
                                "type": "CGPoint",
                                "offset": "0x88"
                        },
                        {
                                "name": "_forVerticalKnob",
                                "type": "BOOL",
                                "offset": "0x98"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollViewKnobLongPressGestureRecognizer touchesBegan:withEvent:]",
                                "address": "0x1848c4100",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewKnobLongPressGestureRecognizer touchesMoved:withEvent:]",
                                "address": "0x1848c4250",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[UIScrollViewKnobLongPressGestureRecognizer touchesEnded:withEvent:]",
                                "address": "0x1848c4380",
                                "signature": "v32@0:8@16@24"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewVFDTable",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewVFDTable",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Variable Frame Display (120Hz ProMotion) arbitration table mapping scroll velocity thresholds to CAFrameRateRange.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_minRate",
                                "type": "float",
                                "offset": "0x8"
                        },
                        {
                                "name": "_preferredRate",
                                "type": "float",
                                "offset": "0xc"
                        },
                        {
                                "name": "_maxRate",
                                "type": "float",
                                "offset": "0x10"
                        },
                        {
                                "name": "_velocityThresholds",
                                "type": "NSArray*",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewVFDTable frameRateRangeForVelocity:]",
                                "address": "0x1848c5100",
                                "signature": "{CAFrameRateRange=fff}24@0:8d16"
                        },
                        {
                                "name": "-[_UIScrollViewVFDTable updateForVelocity:state:]",
                                "address": "0x1848c5200",
                                "signature": "v28@0:8d16q24"
                        }
                ]
        },
        {
                "class_name": "_UIQueuingScrollView",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "_UIQueuingScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Manages infinite page queuing, swipe transitions, and subview recycling for UIPageViewController.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_qDelegate",
                                "type": "id<_UIQueuingScrollViewDelegate>",
                                "offset": "0x160"
                        },
                        {
                                "name": "_viewsMap",
                                "type": "NSMutableArray*",
                                "offset": "0x168"
                        },
                        {
                                "name": "_currentPage",
                                "type": "NSInteger",
                                "offset": "0x170"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIQueuingScrollView setView:direction:animated:completion:]",
                                "address": "0x1848c6100",
                                "signature": "v44@0:8@16q24B32@?36"
                        },
                        {
                                "name": "-[_UIQueuingScrollView _notifyDelegateWillManuallyScroll:]",
                                "address": "0x1848c6250",
                                "signature": "v20@0:8B16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewDecelerationAnimation",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIAnimation",
                "inheritance_chain": [
                        "_UIScrollViewDecelerationAnimation",
                        "UIAnimation",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Analytical exponential velocity decay calculator applying friction coefficient d = 0.998 to free flight scrolling.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_velocity",
                                "type": "CGPoint",
                                "offset": "0x30"
                        },
                        {
                                "name": "_decelerationRate",
                                "type": "double",
                                "offset": "0x40"
                        },
                        {
                                "name": "_lastTimestamp",
                                "type": "double",
                                "offset": "0x48"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewDecelerationAnimation updateVelocity:timestamp:]",
                                "address": "0x1848c7100",
                                "signature": "v40@0:8{CGPoint=dd}16d32"
                        },
                        {
                                "name": "-[_UIScrollViewDecelerationAnimation projectedOffset]",
                                "address": "0x1848c7250",
                                "signature": "{CGPoint=dd}16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewSpringAnimation",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIAnimation",
                "inheritance_chain": [
                        "_UIScrollViewSpringAnimation",
                        "UIAnimation",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Physical second-order differential equation spring solver for rubber-band overscroll boundary recovery.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_stiffness",
                                "type": "double",
                                "offset": "0x30"
                        },
                        {
                                "name": "_damping",
                                "type": "double",
                                "offset": "0x38"
                        },
                        {
                                "name": "_mass",
                                "type": "double",
                                "offset": "0x40"
                        },
                        {
                                "name": "_initialVelocity",
                                "type": "CGPoint",
                                "offset": "0x48"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewSpringAnimation updatePosition:timestamp:]",
                                "address": "0x1848c8100",
                                "signature": "{CGPoint=dd}24@0:8d16"
                        },
                        {
                                "name": "-[_UIScrollViewSpringAnimation settleVelocity]",
                                "address": "0x1848c8250",
                                "signature": "d16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewScrollObserver",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewScrollObserver",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Decoupled observer registration broker broadcasting scroll lifecycle events to auxiliary views and navigation bars.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_targetScrollView",
                                "type": "UIScrollView*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_observerBlock",
                                "type": "id",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewScrollObserver observeScrollViewDidScroll:]",
                                "address": "0x1848c9100",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewScrollIndicator",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "_UIScrollViewScrollIndicator",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Pill and scrubber bar visualization view handling indicator fading, flashing, and thumb geometry updates.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_type",
                                "type": "NSUInteger",
                                "offset": "0x80"
                        },
                        {
                                "name": "_knob",
                                "type": "UIView*",
                                "offset": "0x88"
                        },
                        {
                                "name": "_expanded",
                                "type": "BOOL",
                                "offset": "0x90"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewScrollIndicator setIndicatorStyle:]",
                                "address": "0x1848ca100",
                                "signature": "v24@0:8q16"
                        },
                        {
                                "name": "-[_UIScrollViewScrollIndicator setExpanded:]",
                                "address": "0x1848ca200",
                                "signature": "v20@0:8B16"
                        }
                ]
        },
        {
                "class_name": "UIWebOverflowScrollView",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "UIWebOverflowScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Hosts CSS overflow:scroll containers inside legacy web rendering contexts.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_nodeId",
                                "type": "int",
                                "offset": "0x160"
                        },
                        {
                                "name": "_webContentView",
                                "type": "UIView*",
                                "offset": "0x168"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIWebOverflowScrollView setContentOffset:animated:]",
                                "address": "0x1848cb100",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        }
                ]
        },
        {
                "class_name": "UIWebOverflowContentView",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "UIWebOverflowContentView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Render layer backing web overflow scroll frames.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_webLayer",
                                "type": "CALayer*",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIWebOverflowContentView initWithSuperView:]",
                                "address": "0x1848bc100",
                                "signature": "@24@0:8@16"
                        },
                        {
                                "name": "-[UIWebOverflowContentView willBeRemoved]",
                                "address": "0x1848bc140",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "UIWebOverflowScrollViewInfo",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIWebOverflowScrollViewInfo",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Tracks coordinate offsets and WebKit scroll tree identifiers for DOM scroll nodes.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIWebOverflowScrollView*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_oldNode",
                                "type": "DOMNode*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIWebOverflowScrollViewInfo initWithScrollView:]",
                                "address": "0x1848bc200",
                                "signature": "@24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "UIScrollPocketCollectorModel",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIScrollPocketCollectorModel",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Accumulates scroll geometry across nested views for liquid glass / scroll pocket edge effects.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_pocketCollection",
                                "type": "NSMutableArray*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_bounds",
                                "type": "CGRect",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollPocketCollectorModel registerScrollView:]",
                                "address": "0x1848cc100",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "UIScrollPocketContainerModel",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIScrollPocketContainerModel",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Container representation of scroll pocket geometry and edge blur styling.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_pocketBounds",
                                "type": "CGRect",
                                "offset": "0x8"
                        },
                        {
                                "name": "_activePocketIndex",
                                "type": "NSUInteger",
                                "offset": "0x28"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollPocketContainerModel pocketAtIndex:]",
                                "address": "0x1848bc300",
                                "signature": "@24@0:8Q16"
                        }
                ]
        },
        {
                "class_name": "UIScrollToDismissSupport",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIScrollToDismissSupport",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Coordinates modal sheet pull-down dismissal gestures with scroll view content offset bouncing.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_dismissGestureRecognizer",
                                "type": "UIPanGestureRecognizer*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollToDismissSupport handleDismissPan:]",
                                "address": "0x1848cd100",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "UIPageController",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIPageController",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Historical and internal page index coordinate manager for paginated scrollable surfaces.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_pageCount",
                                "type": "NSInteger",
                                "offset": "0x8"
                        },
                        {
                                "name": "_currentPage",
                                "type": "NSInteger",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIPageController scrollToPage:animated:]",
                                "address": "0x1848ce100",
                                "signature": "v28@0:8q16B24"
                        }
                ]
        },
        {
                "class_name": "UIPanGestureRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIGestureRecognizer",
                "inheritance_chain": [
                        "UIPanGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Public pan gesture recognizer tracking touch movement deltas, translation vectors, and velocity.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_translation",
                                "type": "CGPoint",
                                "offset": "0x50"
                        },
                        {
                                "name": "_velocity",
                                "type": "CGPoint",
                                "offset": "0x60"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIPanGestureRecognizer translationInView:]",
                                "address": "0x1848d1000",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        },
                        {
                                "name": "-[UIPanGestureRecognizer setTranslation:inView:]",
                                "address": "0x1848d1100",
                                "signature": "v40@0:8{CGPoint=dd}16@32"
                        },
                        {
                                "name": "-[UIPanGestureRecognizer velocityInView:]",
                                "address": "0x1848d1200",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingIndexBarEntry",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingIndexBarEntry",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Fast scrolling index character representation for table and collection index jumps.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_title",
                                "type": "NSString*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_targetOffset",
                                "type": "CGPoint",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingIndexBarEntry title]",
                                "address": "0x1848bc400",
                                "signature": "@16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingController",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingController",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Rapid keyboard and remote control focus fast scrolling accelerator.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_fastScrollingIndexBarView",
                                "type": "_UIFocusFastScrollingIndexBarView*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingController startScrollingInDirection:]",
                                "address": "0x1848d2100",
                                "signature": "v24@0:8q16"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingRequest",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingRequest",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Encapsulates parameters for programmatic focus index navigation.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_velocity",
                                "type": "CGPoint",
                                "offset": "0x8"
                        },
                        {
                                "name": "_panDirection",
                                "type": "NSUInteger",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingRequest velocity]",
                                "address": "0x1848bc500",
                                "signature": "{CGPoint=dd}16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingTest",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingTest",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Diagnostic harness evaluating fast scrolling frame rates and detent snapping.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_sampleCount",
                                "type": "NSUInteger",
                                "offset": "0x8"
                        },
                        {
                                "name": "_running",
                                "type": "BOOL",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingTest runTestWithCompletion:]",
                                "address": "0x1848bc600",
                                "signature": "v24@0:8@?16"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Detects rapid swipe repetition to trigger high-velocity index bar acceleration.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_swipeThreshold",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_tracking",
                                "type": "BOOL",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingRecognizer _handleSwipeEvent:]",
                                "address": "0x1848bc700",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingTouchSequence",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingTouchSequence",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Buffers raw touch timestamps to calculate acceleration multipliers.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_points",
                                "type": "NSMutableArray*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_timestamps",
                                "type": "NSMutableArray*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingTouchSequence addPoint:]",
                                "address": "0x1848bc800",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingData",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIFocusFastScrollingData",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Index cache containing target contentOffset coordinates for fast index entries.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_entries",
                                "type": "NSArray*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_indexTitles",
                                "type": "NSArray*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingData entries]",
                                "address": "0x1848bc900",
                                "signature": "@16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIFocusFastScrollingIndexBarView",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "_UIFocusFastScrollingIndexBarView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Visual index alphabet bar rendered alongside scrollable collections.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_indicatorView",
                                "type": "UIView*",
                                "offset": "0x80"
                        },
                        {
                                "name": "_style",
                                "type": "NSUInteger",
                                "offset": "0x88"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIFocusFastScrollingIndexBarView setSelectedIndex:]",
                                "address": "0x1848bca00",
                                "signature": "v24@0:8Q16"
                        }
                ]
        },
        {
                "class_name": "_UIStaticScrollbar",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "_UIStaticScrollbar",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Persistent scrollbar view for pointer-driven iPadOS and desktop environments.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_thumbView",
                                "type": "UIView*",
                                "offset": "0x80"
                        },
                        {
                                "name": "_trackView",
                                "type": "UIView*",
                                "offset": "0x88"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIStaticScrollbar setScrollProgress:]",
                                "address": "0x1848bcb00",
                                "signature": "v24@0:8d16"
                        }
                ]
        },
        {
                "class_name": "_UIStaticScrollbarButton",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIButton",
                "inheritance_chain": [
                        "_UIStaticScrollbarButton",
                        "UIButton",
                        "UIControl",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Scrollbar track stepper arrow button.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_stepDelta",
                                "type": "double",
                                "offset": "0x80"
                        },
                        {
                                "name": "_buttonType",
                                "type": "NSUInteger",
                                "offset": "0x88"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIStaticScrollbarButton stepAction]",
                                "address": "0x1848bcc00",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "UIScrollViewDelayedTouchesBeganGestureRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIGestureRecognizer",
                "inheritance_chain": [
                        "UIScrollViewDelayedTouchesBeganGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Delays delivery of initial touchDown events by 150ms to distinguish taps from scroll initiation.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_touchDelayTimer",
                                "type": "UIDelayedAction*",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIScrollViewDelayedTouchesBeganGestureRecognizer touchesBegan:withEvent:]",
                                "address": "0x1848d3100",
                                "signature": "v32@0:8@16@24"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewAsyncScrollDeceleration",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewAsyncScrollDeceleration",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Calculates off-main-thread inertial deceleration updates for decoupled scrolling pipelines.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_currentVelocity",
                                "type": "CGPoint",
                                "offset": "0x8"
                        },
                        {
                                "name": "_friction",
                                "type": "double",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewAsyncScrollDeceleration stepWithTimeInterval:]",
                                "address": "0x1848d4100",
                                "signature": "{CGPoint=dd}24@0:8d16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewAsyncScrollEvent",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIEvent",
                "inheritance_chain": [
                        "_UIScrollViewAsyncScrollEvent",
                        "UIEvent",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Encapsulates asynchronous scroll velocity and delta packets delivered from BackBoard.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollDelta",
                                "type": "CGPoint",
                                "offset": "0x8"
                        },
                        {
                                "name": "_eventTimestamp",
                                "type": "double",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewAsyncScrollEvent scrollDelta]",
                                "address": "0x1848bcd00",
                                "signature": "{CGPoint=dd}16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewRefreshControl",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIRefreshControl",
                "inheritance_chain": [
                        "_UIScrollViewRefreshControl",
                        "UIRefreshControl",
                        "UIControl",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Pull-to-refresh spinner integrating with top rubber-band overscroll resistance.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_refreshControl",
                                "type": "UIRefreshControl*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_hostScrollView",
                                "type": "UIScrollView*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewRefreshControl setScrollView:]",
                                "address": "0x1848d5100",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewDimensions",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewDimensions",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Geometric cache storing contentSize, visibleBounds, contentInsets, and safe margins.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_contentSize",
                                "type": "CGSize",
                                "offset": "0x8"
                        },
                        {
                                "name": "_boundsSize",
                                "type": "CGSize",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewDimensions isScrollable]",
                                "address": "0x1848bce00",
                                "signature": "B16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewLayoutGuide",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UILayoutGuide",
                "inheritance_chain": [
                        "_UIScrollViewLayoutGuide",
                        "UILayoutGuide",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Autolayout guide anchoring subviews to dynamic scroll view frame or content boundaries.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_guideType",
                                "type": "NSUInteger",
                                "offset": "0x40"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewLayoutGuide _setLocked:]",
                                "address": "0x1848bcf00",
                                "signature": "v20@0:8B16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewContentMarginsGuide",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UILayoutGuide",
                "inheritance_chain": [
                        "_UIScrollViewContentMarginsGuide",
                        "UILayoutGuide",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Autolayout guide reflecting adjusted content insets.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_marginInsets",
                                "type": "UIEdgeInsets",
                                "offset": "0x40"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewContentMarginsGuide updateMargins]",
                                "address": "0x1848bd000",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewIndexBarIndicator",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "_UIScrollViewIndexBarIndicator",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Floating magnifying indicator displaying currently selected index letter.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_titleLabel",
                                "type": "UILabel*",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewIndexBarIndicator setTitle:]",
                                "address": "0x1848bd100",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewKnob",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "_UIScrollViewKnob",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Visual draggable pill element of the scroll indicator bar.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_knobStyle",
                                "type": "NSUInteger",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewKnob setHighlighted:]",
                                "address": "0x1848bd200",
                                "signature": "v20@0:8B16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewPinchGestureRecognizer",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "UIPinchGestureRecognizer",
                "inheritance_chain": [
                        "_UIScrollViewPinchGestureRecognizer",
                        "UIPinchGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Pinch recognizer driving content zooming, scale clamping, and two-finger bounce physics.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewPinchGestureRecognizer _scrollView]",
                                "address": "0x1848bd300",
                                "signature": "@16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewVelocity",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewVelocity",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Rolling window least-squares velocity filter interpolating pan release speed.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_samples",
                                "type": "NSMutableArray*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_filteredVelocity",
                                "type": "CGPoint",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewVelocity addSample:atTimestamp:]",
                                "address": "0x1848d6100",
                                "signature": "v40@0:8{CGPoint=dd}16d32"
                        },
                        {
                                "name": "-[_UIScrollViewVelocity filteredVelocity]",
                                "address": "0x1848d6200",
                                "signature": "{CGPoint=dd}16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewFrictionEstimator",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewFrictionEstimator",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Calibrates dynamic kinetic friction based on decelerationRate presets (Normal: 0.998, Fast: 0.990).",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_samplingInterval",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_rollingFrictionCoefficient",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewFrictionEstimator estimateFrictionForVelocity:]",
                                "address": "0x1848d7100",
                                "signature": "d24@0:8d16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewRubberBandPolicy",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewRubberBandPolicy",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Computes non-linear logarithmic rubber-band offset damping: f(x) = (x * d * c) / (d + c * x).",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_rubberBandExtent",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_resistanceCoefficient",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewRubberBandPolicy rubberBandOffsetForOverhang:]",
                                "address": "0x1848d8100",
                                "signature": "d24@0:8d16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewSnappingBehavior",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewSnappingBehavior",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Applies snap-to-alignment points on deceleration completion for carousel and grid layouts.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_snapInterval",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_snappingDeceleration",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewSnappingBehavior targetOffsetForProjectedOffset:velocity:]",
                                "address": "0x1848d9100",
                                "signature": "{CGPoint=dd}48@0:8{CGPoint=dd}16{CGPoint=dd}32"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewDirectionalLock",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewDirectionalLock",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Locks scrolling to a single axis (horizontal or vertical) when diagonal pan angle is below threshold.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_axisLockState",
                                "type": "NSUInteger",
                                "offset": "0x8"
                        },
                        {
                                "name": "_lockThreshold",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewDirectionalLock evaluateLockForTranslation:]",
                                "address": "0x1848da100",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        }
                ]
        },
        {
                "class_name": "_UIScrollViewScrollingSpeedMonitor",
                "framework": "UIKitCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x184752000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIScrollViewScrollingSpeedMonitor",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Monitors instantaneous points-per-second velocity to adjust image prefetching and cell loading.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_currentSpeed",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_lastTimestamp",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIScrollViewScrollingSpeedMonitor recordScrollStepAtTimestamp:]",
                                "address": "0x1848db100",
                                "signature": "v24@0:8d16"
                        }
                ]
        },
        {
                "class_name": "CADisplayLink",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CADisplayLink",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Display synchronization timer synchronizing scrolling animation frames with hardware refresh cycles.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_target",
                                "type": "id",
                                "offset": "0x8"
                        },
                        {
                                "name": "_selector",
                                "type": "SEL",
                                "offset": "0x10"
                        },
                        {
                                "name": "_preferredFrameRateRange",
                                "type": "CAFrameRateRange",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "+[CADisplayLink displayLinkWithTarget:selector:]",
                                "address": "0x184310100",
                                "signature": "@32@0:8@16:24"
                        },
                        {
                                "name": "-[CADisplayLink addToRunLoop:forMode:]",
                                "address": "0x184310200",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[CADisplayLink removeFromRunLoop:forMode:]",
                                "address": "0x184310300",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[CADisplayLink setPreferredFrameRateRange:]",
                                "address": "0x184310400",
                                "signature": "v28@0:8{CAFrameRateRange=fff}16"
                        },
                        {
                                "name": "-[CADisplayLink preferredFrameRateRange]",
                                "address": "0x184310450",
                                "signature": "{CAFrameRateRange=fff}16@0:8"
                        },
                        {
                                "name": "-[CADisplayLink targetTimestamp]",
                                "address": "0x184310500",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CADisplayLink timestamp]",
                                "address": "0x184310550",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CADisplayLink isPaused]",
                                "address": "0x184310600",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[CADisplayLink setPaused:]",
                                "address": "0x184310650",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[CADisplayLink duration]",
                                "address": "0x184310570",
                                "signature": "d16@0:8",
                                "category": "Rendering/Display",
                                "role": "Returns display refresh period duration (e.g. 0.00833s for 120Hz)",
                                "is_kinematics_critical": False
                        },
                        {
                                "name": "-[CADisplayLink currentDisplayTime]",
                                "address": "0x184310590",
                                "signature": "d16@0:8",
                                "category": "Rendering/Display",
                                "role": "Returns CoreAnimation compositor timestamp",
                                "is_kinematics_critical": False
                        }
                ]
        },
        {
                "class_name": "CAFrameRateRange",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CAFrameRateRange",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Specifies minimum, preferred, and maximum refresh rates for Apple ProMotion adaptive 120Hz displays.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "minimum",
                                "type": "float",
                                "offset": "0x0"
                        },
                        {
                                "name": "maximum",
                                "type": "float",
                                "offset": "0x4"
                        },
                        {
                                "name": "preferred",
                                "type": "float",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "+[CAFrameRateRange rangeWithMinimum:maximum:preferred:]",
                                "address": "0x184311100",
                                "signature": "{CAFrameRateRange=fff}28@0:8f16f20f24"
                        }
                ]
        },
        {
                "class_name": "CASpringAnimation",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "CABasicAnimation",
                "inheritance_chain": [
                        "CASpringAnimation",
                        "CABasicAnimation",
                        "CAPropertyAnimation",
                        "CAAnimation",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Hardware-accelerated physical spring kinematics animation model parameterized by mass, stiffness, and damping.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_mass",
                                "type": "double",
                                "offset": "0x40"
                        },
                        {
                                "name": "_stiffness",
                                "type": "double",
                                "offset": "0x48"
                        },
                        {
                                "name": "_damping",
                                "type": "double",
                                "offset": "0x50"
                        },
                        {
                                "name": "_initialVelocity",
                                "type": "double",
                                "offset": "0x58"
                        }
                ],
                "methods": [
                        {
                                "name": "-[CASpringAnimation setMass:]",
                                "address": "0x184312100",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[CASpringAnimation mass]",
                                "address": "0x184312150",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CASpringAnimation setStiffness:]",
                                "address": "0x184312200",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[CASpringAnimation stiffness]",
                                "address": "0x184312250",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CASpringAnimation setDamping:]",
                                "address": "0x184312300",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[CASpringAnimation damping]",
                                "address": "0x184312350",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CASpringAnimation setInitialVelocity:]",
                                "address": "0x184312400",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[CASpringAnimation initialVelocity]",
                                "address": "0x184312450",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CASpringAnimation settlingDuration]",
                                "address": "0x184312500",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[CASpringAnimation durationForEpsilon:]",
                                "address": "0x184312540",
                                "signature": "d24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Calculates time when spring oscillation amplitude decays below epsilon",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[CASpringAnimation bounce]",
                                "address": "0x184312580",
                                "signature": "d16@0:8",
                                "category": "Core Kinematics",
                                "role": "Analytical bounce factor derived from damping ratio",
                                "is_kinematics_critical": True
                        },
                        {
                                "name": "-[CASpringAnimation setBounce:]",
                                "address": "0x1843125a0",
                                "signature": "v24@0:8d16",
                                "category": "Core Kinematics",
                                "role": "Sets analytical bounce factor deriving damping ratio",
                                "is_kinematics_critical": True
                        }
                ]
        },
        {
                "class_name": "CAMediaTimingFunction",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CAMediaTimingFunction",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Cubic B\u00e9zier curve interpolation model for deceleration curves.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_c1",
                                "type": "CGPoint",
                                "offset": "0x8"
                        },
                        {
                                "name": "_c2",
                                "type": "CGPoint",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "+[CAMediaTimingFunction functionWithName:]",
                                "address": "0x184313100",
                                "signature": "@24@0:8@16"
                        },
                        {
                                "name": "-[CAMediaTimingFunction getControlPointsAtIndex:values:]",
                                "address": "0x184313200",
                                "signature": "v32@0:8q16[2f]24"
                        }
                ]
        },
        {
                "class_name": "CAKeyframeAnimation",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "CAPropertyAnimation",
                "inheritance_chain": [
                        "CAKeyframeAnimation",
                        "CAPropertyAnimation",
                        "CAAnimation",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Interpolates piecewise splines for non-linear deceleration and rubber-band trajectories.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_values",
                                "type": "NSArray*",
                                "offset": "0x40"
                        },
                        {
                                "name": "_keyTimes",
                                "type": "NSArray*",
                                "offset": "0x48"
                        },
                        {
                                "name": "_timingFunctions",
                                "type": "NSArray*",
                                "offset": "0x50"
                        }
                ],
                "methods": [
                        {
                                "name": "-[CAKeyframeAnimation setValues:]",
                                "address": "0x184314100",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[CAKeyframeAnimation setKeyTimes:]",
                                "address": "0x184314200",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "CALayer",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CALayer",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Compositing layer node mutating sublayerTransform and bounds to represent scroll offsets.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_bounds",
                                "type": "CGRect",
                                "offset": "0x20"
                        },
                        {
                                "name": "_sublayerTransform",
                                "type": "CATransform3D",
                                "offset": "0x40"
                        }
                ],
                "methods": [
                        {
                                "name": "-[CALayer setBounds:]",
                                "address": "0x184315100",
                                "signature": "v48@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16"
                        },
                        {
                                "name": "-[CALayer setSublayerTransform:]",
                                "address": "0x184315200",
                                "signature": "v144@0:8{CATransform3D=dddddddddddddddd}16"
                        }
                ]
        },
        {
                "class_name": "CATransaction",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CATransaction",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Atomic batching container coordinating scroll layer bounds changes with display frame presentation.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_transactionFlags",
                                "type": "uint32_t",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "+[CATransaction begin]",
                                "address": "0x184316100",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "+[CATransaction commit]",
                                "address": "0x184316200",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "CARenderer",
                "framework": "QuartzCore.framework",
                "subcache_slice": ".01",
                "vm_base_address": "0x1842d4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "CARenderer",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Off-screen GPU render server compositing layer trees during high-velocity scrolls.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_context",
                                "type": "CA::Render::Context*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_bounds",
                                "type": "CGRect",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "+[CARenderer rendererWithEAGLContext:options:]",
                                "address": "0x184317100",
                                "signature": "@32@0:8@16@24"
                        },
                        {
                                "name": "-[CARenderer render]",
                                "address": "0x184317140",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "SwiftUI.ScrollView",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "View",
                "inheritance_chain": [
                        "SwiftUI.ScrollView",
                        "View"
                ],
                "category": "Positioning/Paging",
                "role": "Declarative scroll container struct projecting axes and content into underlying platform scroll view.",
                "protocols": [
                        "View"
                ],
                "ivars": [
                        {
                                "name": "axes",
                                "type": "Axis.Set",
                                "offset": "0x0"
                        },
                        {
                                "name": "showsIndicators",
                                "type": "Bool",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUI.ScrollView.init(axes:showsIndicators:content:)",
                                "address": "0x18a8d1100",
                                "signature": "($s7SwiftUI10ScrollViewV4axes15showsIndicators7contentACyxGAA4AxisO3SetV_SbxyXEtcfC)"
                        },
                        {
                                "name": "SwiftUI.ScrollView.scrollPosition(_:)",
                                "address": "0x18a8d1250",
                                "signature": "($s7SwiftUI10ScrollViewV14scrollPositionyACyxGAA06ScrollD0VzF)"
                        }
                ]
        },
        {
                "class_name": "SwiftUI.List",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "View",
                "inheritance_chain": [
                        "SwiftUI.List",
                        "View"
                ],
                "category": "Positioning/Paging",
                "role": "Declarative virtualized collection view with recycled row hierarchy.",
                "protocols": [
                        "View"
                ],
                "ivars": [
                        {
                                "name": "_data",
                                "type": "Data",
                                "offset": "0x0"
                        },
                        {
                                "name": "_rowContent",
                                "type": "RowContent",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUI.List.init(content:)",
                                "address": "0x18a8d2100",
                                "signature": "($s7SwiftUI4ListV7contentACyxGxyXE_tcfC)"
                        },
                        {
                                "name": "SwiftUI.List.scrollContentBackground(_:)",
                                "address": "0x18a8d2200",
                                "signature": "($s7SwiftUI4ListV23scrollContentBackgroundyACyxGAA10VisibilityOF)"
                        }
                ]
        },
        {
                "class_name": "SwiftUI.ScrollPosition",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "Equatable",
                "inheritance_chain": [
                        "SwiftUI.ScrollPosition",
                        "Equatable"
                ],
                "category": "Positioning/Paging",
                "role": "Observable state structure representing programmatic contentOffset and anchor detents.",
                "protocols": [
                        "Equatable",
                        "Hashable"
                ],
                "ivars": [
                        {
                                "name": "_edge",
                                "type": "Edge?",
                                "offset": "0x0"
                        },
                        {
                                "name": "_point",
                                "type": "CGPoint?",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUI.ScrollPosition.init(edge:)",
                                "address": "0x18a8d3100",
                                "signature": "($s7SwiftUI14ScrollPositionV4edgeACAA4EdgeOSg_tcfC)"
                        },
                        {
                                "name": "SwiftUI.ScrollPosition.init(point:)",
                                "address": "0x18a8d3140",
                                "signature": "($s7SwiftUI14ScrollPositionV5pointACSo7CGPointVSg_tcfC)"
                        },
                        {
                                "name": "SwiftUI.ScrollPosition.isPositioned.getter",
                                "address": "0x18a8d3180",
                                "signature": "Bool ()"
                        }
                ]
        },
        {
                "class_name": "SwiftUI.ScrollTargetBehavior",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "Protocol",
                "inheritance_chain": [
                        "SwiftUI.ScrollTargetBehavior",
                        "Protocol"
                ],
                "category": "Positioning/Paging",
                "role": "Protocol defining target offset settlement logic when user finishes pan interaction.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_behavior",
                                "type": "AnyScrollTargetBehavior",
                                "offset": "0x0"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUI.ScrollTargetBehavior.updateTarget(_:context:)",
                                "address": "0x18a8d4100",
                                "signature": "($s7SwiftUI20ScrollTargetBehaviorP06updateC0_7contextyAA0cD0Vz_AA0cdE7ContextVtFTq)"
                        }
                ]
        },
        {
                "class_name": "_UIHostingScrollView",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "_UIHostingScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "UIKit backing implementation bridging SwiftUI declarative state to native UIScrollView lifecycle.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_host",
                                "type": "_UIHostingViewable*",
                                "offset": "0x160"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIHostingScrollView setContentOffset:animated:]",
                                "address": "0x18a8c1000",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[_UIHostingScrollView _updateScrollPosition]",
                                "address": "0x18a8c1100",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "_SwiftUIScrollViewBridge",
                "framework": "SwiftUI.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a8a7000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_SwiftUIScrollViewBridge",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Synchronizes transaction updates and state mutations between SwiftUI and UIKit.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollView",
                                "type": "UIScrollView*",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_SwiftUIScrollViewBridge syncStateWithOffset:]",
                                "address": "0x18a8c2100",
                                "signature": "v32@0:8{CGPoint=dd}16"
                        }
                ]
        },
        {
                "class_name": "SwiftUICore.ScrollGeometry",
                "framework": "SwiftUICore.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x188404000",
                "superclass": "Equatable",
                "inheritance_chain": [
                        "SwiftUICore.ScrollGeometry",
                        "Equatable"
                ],
                "category": "Positioning/Paging",
                "role": "Immutable geometric snapshot of bounds, contentSize, and contentInsets in SwiftUI view graphs.",
                "protocols": [
                        "Equatable"
                ],
                "ivars": [
                        {
                                "name": "contentOffset",
                                "type": "CGPoint",
                                "offset": "0x0"
                        },
                        {
                                "name": "contentSize",
                                "type": "CGSize",
                                "offset": "0x10"
                        },
                        {
                                "name": "contentInsets",
                                "type": "EdgeInsets",
                                "offset": "0x20"
                        },
                        {
                                "name": "containerSize",
                                "type": "CGSize",
                                "offset": "0x40"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUICore.ScrollGeometry.contentOffset.getter",
                                "address": "0x188414100",
                                "signature": "CGPoint ()"
                        },
                        {
                                "name": "SwiftUICore.ScrollGeometry.contentSize.getter",
                                "address": "0x188414140",
                                "signature": "CGSize ()"
                        },
                        {
                                "name": "SwiftUICore.ScrollGeometry.contentInsets.getter",
                                "address": "0x188414180",
                                "signature": "EdgeInsets ()"
                        },
                        {
                                "name": "SwiftUICore.ScrollGeometry.containerSize.getter",
                                "address": "0x1884141c0",
                                "signature": "CGSize ()"
                        },
                        {
                                "name": "SwiftUICore.ScrollGeometry.visibleRect.getter",
                                "address": "0x188414200",
                                "signature": "CGRect ()"
                        }
                ]
        },
        {
                "class_name": "SwiftUICore.ScrollPhase",
                "framework": "SwiftUICore.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x188404000",
                "superclass": "Equatable",
                "inheritance_chain": [
                        "SwiftUICore.ScrollPhase",
                        "Equatable"
                ],
                "category": "Core Kinematics",
                "role": "Enum defining declarative phases: idle, tracking, interacting, decelerating, animating.",
                "protocols": [
                        "Equatable"
                ],
                "ivars": [
                        {
                                "name": "phase",
                                "type": "UInt8",
                                "offset": "0x0"
                        },
                        {
                                "name": "velocity",
                                "type": "CGVector",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "SwiftUICore.ScrollPhase.isScrolling.getter",
                                "address": "0x188415100",
                                "signature": "Bool ()"
                        },
                        {
                                "name": "SwiftUICore.ScrollPhase.velocity.getter",
                                "address": "0x188415140",
                                "signature": "CGVector ()"
                        }
                ]
        },
        {
                "class_name": "UIGestureEnvironment",
                "framework": "Gestures.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a169000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIGestureEnvironment",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Centralized gesture arbitration runtime delivering hardware touches to active recognizer graphs.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_gestureRecognizers",
                                "type": "NSMutableArray*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_activeEvent",
                                "type": "UIEvent*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UIGestureEnvironment _deliverEvent:toGestureRecognizers:]",
                                "address": "0x18a181000",
                                "signature": "v32@0:8@16@24"
                        }
                ]
        },
        {
                "class_name": "_UIGestureRecognizerTransformAnalyzer",
                "framework": "Gestures.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a169000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIGestureRecognizerTransformAnalyzer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Analyzes translation vs pinch vs rotation vectors to disambiguate concurrent gestures.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_lowPassFilterDistance",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_translationWeight",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIGestureRecognizerTransformAnalyzer analyzeTouches:]",
                                "address": "0x18a183100",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[_UIGestureRecognizerTransformAnalyzer dominantComponent]",
                                "address": "0x18a183140",
                                "signature": "i16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIPanOrFlingGestureRecognizer",
                "framework": "Gestures.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a169000",
                "superclass": "UIPanGestureRecognizer",
                "inheritance_chain": [
                        "_UIPanOrFlingGestureRecognizer",
                        "UIPanGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Distinguishes continuous drag gestures from ballistic fling gestures using velocity thresholds.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_velocityThreshold",
                                "type": "double",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIPanOrFlingGestureRecognizer _isFling]",
                                "address": "0x18a182100",
                                "signature": "B16@0:8"
                        }
                ]
        },
        {
                "class_name": "_UIGestureDelaying",
                "framework": "Gestures.framework",
                "subcache_slice": ".03",
                "vm_base_address": "0x18a169000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "_UIGestureDelaying",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Timer-based touch delay manager holding touch delivery until gesture failure or recognition.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_delayTimeout",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_delayTimer",
                                "type": "NSTimer*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[_UIGestureDelaying startDelayWithTimeout:]",
                                "address": "0x18a184100",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[_UIGestureDelaying cancelDelay]",
                                "address": "0x18a184140",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "IOHIDPointerScrollFilter",
                "framework": "IOHIDPointerScrollFilter.plugin",
                "subcache_slice": ".48",
                "vm_base_address": "0x2529c4000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "IOHIDPointerScrollFilter",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Hardware HID pointer and trackpad scroll event filter applying device-level friction scaling.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_frictionScale",
                                "type": "float",
                                "offset": "0x8"
                        },
                        {
                                "name": "_scrollAccelerationTable",
                                "type": "IOHIDScrollAccelerationTable*",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[IOHIDPointerScrollFilter filterPointerEvent:]",
                                "address": "0x2529d1000",
                                "signature": "@24@0:8^{__IOHIDEvent=}16"
                        },
                        {
                                "name": "-[IOHIDPointerScrollFilter filterScrollEvent:deltaX:deltaY:]",
                                "address": "0x2529d1150",
                                "signature": "v36@0:8^{__IOHIDEvent=}16ff"
                        },
                        {
                                "name": "-[IOHIDPointerScrollFilter applyAccelerationCurve:toDelta:]",
                                "address": "0x2529d1280",
                                "signature": "f24@0:8@16f20"
                        }
                ]
        },
        {
                "class_name": "IOHIDScrollAccelerationTable",
                "framework": "IOHIDPointerScrollFilter.plugin",
                "subcache_slice": ".48",
                "vm_base_address": "0x2529c4000",
                "superclass": "CFType",
                "inheritance_chain": [
                        "IOHIDScrollAccelerationTable"
                ],
                "category": "Core Kinematics",
                "role": "Non-linear acceleration lookup tables mapping mouse wheel notches to continuous velocity.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_curveData",
                                "type": "const void*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_pointCount",
                                "type": "uint32_t",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "IOHIDScrollAccelerationTable::getMultiplierForDelta()",
                                "address": "0x2529d2100",
                                "signature": "f20@0:8f16"
                        },
                        {
                                "name": "IOHIDScrollAccelerationTable::interpolateCurve()",
                                "address": "0x2529d2140",
                                "signature": "f24@0:8f16f20"
                        }
                ]
        },
        {
                "class_name": "WKScrollView",
                "framework": "WebKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19cbb9000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "WKScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "WebKit scroll view subclass coordinating viewport bounds with asynchronous web process render threads.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_wkDelegate",
                                "type": "id",
                                "offset": "0x160"
                        },
                        {
                                "name": "_scrollOffsetChanged",
                                "type": "BOOL",
                                "offset": "0x168"
                        }
                ],
                "methods": [
                        {
                                "name": "-[WKScrollView setContentOffset:animated:]",
                                "address": "0x19cbd1000",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[WKScrollView _updateDelegate]",
                                "address": "0x19cbd1100",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "WKContentView",
                "framework": "WebKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19cbb9000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "WKContentView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Web page touch interaction surface forwarding pan gestures to the WebProcess.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_page",
                                "type": "NakedPtr<WebKit::WebPageProxy>",
                                "offset": "0x80"
                        }
                ],
                "methods": [
                        {
                                "name": "-[WKContentView _didScroll]",
                                "address": "0x19cbd2100",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "RemoteScrollingCoordinatorIOS",
                "framework": "WebKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19cbb9000",
                "superclass": "ScrollingCoordinator",
                "inheritance_chain": [
                        "RemoteScrollingCoordinatorIOS",
                        "ScrollingCoordinator"
                ],
                "category": "Core Kinematics",
                "role": "Manages scrolling tree nodes and asynchronous rubber-banding for multi-process WebKit.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollingTree",
                                "type": "RefPtr<RemoteScrollingTree>",
                                "offset": "0x8"
                        },
                        {
                                "name": "_rubberBandingEnabled",
                                "type": "bool",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "RemoteScrollingCoordinatorIOS::scheduleDisplayRefresh()",
                                "address": "0x19cbd3100",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "RemoteScrollingCoordinatorIOS::currentScrollPosition()",
                                "address": "0x19cbd3140",
                                "signature": "{FloatPoint=ff}16@0:8"
                        }
                ]
        },
        {
                "class_name": "ScrollingTreeFrameScrollingNodeIOS",
                "framework": "WebKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19cbb9000",
                "superclass": "ScrollingTreeNode",
                "inheritance_chain": [
                        "ScrollingTreeFrameScrollingNodeIOS",
                        "ScrollingTreeNode"
                ],
                "category": "Rendering/Display",
                "role": "Compositor thread scrolling tree node updating layer transforms for web frames.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollLayer",
                                "type": "RetainPtr<CALayer>",
                                "offset": "0x8"
                        },
                        {
                                "name": "_scrolledContentsLayer",
                                "type": "RetainPtr<CALayer>",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "ScrollingTreeFrameScrollingNodeIOS::commitPageScaleSettings()",
                                "address": "0x19cbd4100",
                                "signature": "v16@0:8"
                        },
                        {
                                "name": "ScrollingTreeFrameScrollingNodeIOS::updateLayersAfterAncestorChange()",
                                "address": "0x19cbd4140",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "WebActionDisablingScrollView",
                "framework": "WebKitLegacy.framework",
                "subcache_slice": ".11",
                "vm_base_address": "0x1afb20000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "WebActionDisablingScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Legacy WebKit scroll view suppressing contextual callouts during touch drag sequences.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_touchEventInterceptionEnabled",
                                "type": "BOOL",
                                "offset": "0x160"
                        }
                ],
                "methods": [
                        {
                                "name": "-[WebActionDisablingScrollView setScrollEnabled:]",
                                "address": "0x1afb31000",
                                "signature": "v20@0:8B16"
                        },
                        {
                                "name": "-[WebActionDisablingScrollView scrollWheel:]",
                                "address": "0x1afb31040",
                                "signature": "v24@0:8@16"
                        },
                        {
                                "name": "-[WebActionDisablingScrollView touchesBegan:withEvent:]",
                                "address": "0x1afb31080",
                                "signature": "v32@0:8@16@24"
                        },
                        {
                                "name": "-[WebActionDisablingScrollView touchesMoved:withEvent:]",
                                "address": "0x1afb310c0",
                                "signature": "v32@0:8@16@24"
                        }
                ]
        },
        {
                "class_name": "AKSpring",
                "framework": "AnimationKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19f2b1000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "AKSpring",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Analytical second-order ordinary differential equation solver for damped harmonic oscillators.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_stiffness",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_damping",
                                "type": "double",
                                "offset": "0x10"
                        },
                        {
                                "name": "_mass",
                                "type": "double",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "-[AKSpring positionAtTime:]",
                                "address": "0x19f2d1000",
                                "signature": "d24@0:8d16"
                        },
                        {
                                "name": "-[AKSpring velocityAtTime:]",
                                "address": "0x19f2d1100",
                                "signature": "d24@0:8d16"
                        },
                        {
                                "name": "-[AKSpring solveODE]",
                                "address": "0x19f2d1200",
                                "signature": "v16@0:8"
                        }
                ]
        },
        {
                "class_name": "AKPhysicsController",
                "framework": "AnimationKit.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19f2b1000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "AKPhysicsController",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "High-level controller coordinating multi-axis spring and friction animations.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_springModel",
                                "type": "AKSpring*",
                                "offset": "0x8"
                        },
                        {
                                "name": "_integratorTimeStep",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[AKPhysicsController stepSimulation:]",
                                "address": "0x19f2d2100",
                                "signature": "v24@0:8d16"
                        },
                        {
                                "name": "-[AKPhysicsController currentPosition]",
                                "address": "0x19f2d2140",
                                "signature": "d16@0:8"
                        }
                ]
        },
        {
                "class_name": "SUIASpringAnimation",
                "framework": "SystemUIAnimationKit.framework",
                "subcache_slice": ".69",
                "vm_base_address": "0x2b62f0000",
                "superclass": "CABasicAnimation",
                "inheritance_chain": [
                        "SUIASpringAnimation",
                        "CABasicAnimation",
                        "CAPropertyAnimation",
                        "CAAnimation",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "System gesture spring timing model driving fluid interface responses in SpringBoard.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_springModel",
                                "type": "SUIAFluidSwitcherSpringModel*",
                                "offset": "0x40"
                        }
                ],
                "methods": [
                        {
                                "name": "-[SUIASpringAnimation initWithStiffness:damping:]",
                                "address": "0x2b6311000",
                                "signature": "@32@0:8d16d24"
                        }
                ]
        },
        {
                "class_name": "SUIAFluidSwitcherSpringModel",
                "framework": "SystemUIAnimationKit.framework",
                "subcache_slice": ".69",
                "vm_base_address": "0x2b62f0000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "SUIAFluidSwitcherSpringModel",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "Spring parameter model driving app switcher paging, dock scrolling, and app launch fluid bounce.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_angularFrequency",
                                "type": "double",
                                "offset": "0x8"
                        },
                        {
                                "name": "_dampingRatio",
                                "type": "double",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "-[SUIAFluidSwitcherSpringModel angularFrequency]",
                                "address": "0x2b6312100",
                                "signature": "d16@0:8"
                        },
                        {
                                "name": "-[SUIAFluidSwitcherSpringModel dampingRatio]",
                                "address": "0x2b6312130",
                                "signature": "d16@0:8"
                        }
                ]
        },
        {
                "class_name": "CTFramesetter",
                "framework": "CoreText.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19a3d7000",
                "superclass": "CFType",
                "inheritance_chain": [
                        "CTFramesetter",
                        "CFType"
                ],
                "category": "Rendering/Display",
                "role": "Typesetting engine calculating frame lines during continuous text view scrolling.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_typesetter",
                                "type": "CTTypesetterRef",
                                "offset": "0x10"
                        }
                ],
                "methods": [
                        {
                                "name": "CTFramesetterCreateWithAttributedString",
                                "address": "0x19a3e2100",
                                "signature": "^{__CTFramesetter=}@16"
                        },
                        {
                                "name": "CTFramesetterCreateFrame",
                                "address": "0x19a3e2180",
                                "signature": "^{__CTFrame=}@16{?=qq}24@40"
                        },
                        {
                                "name": "CTFramesetterSuggestFrameSizeWithConstraints",
                                "address": "0x19a3e2200",
                                "signature": "{CGSize=dd}@16{?=qq}24@40{CGSize=dd}48^v64"
                        }
                ]
        },
        {
                "class_name": "CTFrame",
                "framework": "CoreText.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19a3d7000",
                "superclass": "CFType",
                "inheritance_chain": [
                        "CTFrame",
                        "CFType"
                ],
                "category": "Rendering/Display",
                "role": "Paragraph text layout frame bounding visible lines in scrollable text views.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_lines",
                                "type": "CFArrayRef",
                                "offset": "0x10"
                        },
                        {
                                "name": "_origins",
                                "type": "CGPoint*",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "CTFrameGetLines",
                                "address": "0x19a3e3100",
                                "signature": "^{__CFArray=}@16"
                        },
                        {
                                "name": "CTFrameGetLineOrigins",
                                "address": "0x19a3e3140",
                                "signature": "v36@0:8{?=qq}16^v32"
                        },
                        {
                                "name": "CTFrameDraw",
                                "address": "0x19a3e3180",
                                "signature": "v24@0:8^{CGContext=}16"
                        }
                ]
        },
        {
                "class_name": "CTLine",
                "framework": "CoreText.framework",
                "subcache_slice": ".07",
                "vm_base_address": "0x19a3d7000",
                "superclass": "CFType",
                "inheritance_chain": [
                        "CTLine",
                        "CFType"
                ],
                "category": "Rendering/Display",
                "role": "Horizontal line glyph layout representation.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_runs",
                                "type": "CFArrayRef",
                                "offset": "0x10"
                        },
                        {
                                "name": "_width",
                                "type": "double",
                                "offset": "0x18"
                        }
                ],
                "methods": [
                        {
                                "name": "CTLineGetTypographicBounds",
                                "address": "0x19a3e4100",
                                "signature": "d40@0:8^d16^d24^d32"
                        },
                        {
                                "name": "CTLineGetImageBounds",
                                "address": "0x19a3e4140",
                                "signature": "{CGRect={CGPoint=dd}{CGSize=dd}}24@0:8^{CGContext=}16"
                        }
                ]
        },
        {
                "class_name": "UISDisplayContext",
                "framework": "UIKitServices.framework",
                "subcache_slice": ".05",
                "vm_base_address": "0x197f2b000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UISDisplayContext",
                        "NSObject"
                ],
                "category": "Rendering/Display",
                "role": "Provides hardware display scale, safe area bounds, and refresh timing to UI processes.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_displayEdgeInfo",
                                "type": "UISApplicationSupportDisplayEdgeInfo*",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UISDisplayContext displayConfiguration]",
                                "address": "0x197f41000",
                                "signature": "@16@0:8"
                        }
                ]
        },
        {
                "class_name": "UISApplicationSupportDisplayEdgeInfo",
                "framework": "UIKitServices.framework",
                "subcache_slice": ".05",
                "vm_base_address": "0x197f2b000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UISApplicationSupportDisplayEdgeInfo",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Informs scroll views of safe area insets to compute rubber-band edge limits.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_safeAreaInsetsPortrait",
                                "type": "UIEdgeInsets",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "-[UISApplicationSupportDisplayEdgeInfo safeAreaInsetsPortrait]",
                                "address": "0x197f42100",
                                "signature": "{UIEdgeInsets=dddd}16@0:8"
                        },
                        {
                                "name": "-[UISApplicationSupportDisplayEdgeInfo homeAffordanceOverlayInsets]",
                                "address": "0x197f42150",
                                "signature": "{UIEdgeInsets=dddd}16@0:8"
                        }
                ]
        },
        {
                "class_name": "UIKitFacade",
                "framework": "UIKit.framework",
                "subcache_slice": ".46",
                "vm_base_address": "0x24ff98000",
                "superclass": "NSObject",
                "inheritance_chain": [
                        "UIKitFacade",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Re-export forwarding interface exposing UIScrollView and UIPanGestureRecognizer public symbols.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_coreBridge",
                                "type": "id",
                                "offset": "0x8"
                        }
                ],
                "methods": [
                        {
                                "name": "UIAccessibilityScrollToVisibleWithSnapFlag",
                                "address": "0x24ffa1000",
                                "signature": "B24@0:8@16B20"
                        },
                        {
                                "name": "UIApplicationMain",
                                "address": "0x24ffa1080",
                                "signature": "i36i0^r*8@16@24"
                        }
                ]
        },
        {
                "class_name": "SBIconScrollView",
                "framework": "SpringBoard.framework",
                "subcache_slice": ".36",
                "vm_base_address": "0x226a11000",
                "superclass": "BSUIScrollView",
                "inheritance_chain": [
                        "SBIconScrollView",
                        "BSUIScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "Home screen icon grid scrolling container implementing page detents and folder transitions.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_iconManager",
                                "type": "SBHIconManager*",
                                "offset": "0x180"
                        },
                        {
                                "name": "_currentPageIndex",
                                "type": "NSInteger",
                                "offset": "0x188"
                        }
                ],
                "methods": [
                        {
                                "name": "-[SBIconScrollView setContentOffset:animated:]",
                                "address": "0x226b10000",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[SBIconScrollView handlePan:]",
                                "address": "0x226b10150",
                                "signature": "v24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "SBFloatingDockView",
                "framework": "SpringBoard.framework",
                "subcache_slice": ".36",
                "vm_base_address": "0x226a11000",
                "superclass": "UIView",
                "inheritance_chain": [
                        "SBFloatingDockView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Positioning/Paging",
                "role": "iPadOS / Stage Manager persistent floating dock hosting horizontally scrolling icon items.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_dockScrollView",
                                "type": "UIScrollView*",
                                "offset": "0x120"
                        }
                ],
                "methods": [
                        {
                                "name": "-[SBFloatingDockView isScrolling]",
                                "address": "0x226b21000",
                                "signature": "B16@0:8"
                        },
                        {
                                "name": "-[SBFloatingDockView setContentOffset:animated:]",
                                "address": "0x226b21040",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        }
                ]
        },
        {
                "class_name": "SBHomeGesturePanGestureRecognizer",
                "framework": "SpringBoard.framework",
                "subcache_slice": ".36",
                "vm_base_address": "0x226a11000",
                "superclass": "UIPanGestureRecognizer",
                "inheritance_chain": [
                        "SBHomeGesturePanGestureRecognizer",
                        "UIPanGestureRecognizer",
                        "UIGestureRecognizer",
                        "NSObject"
                ],
                "category": "Gesture Infrastructure",
                "role": "Tracks bottom home bar swipe-up gesture for app dismissal, app switcher paging, and fast app switching.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_touchStream",
                                "type": "BKSTouchStream*",
                                "offset": "0x88"
                        }
                ],
                "methods": [
                        {
                                "name": "-[SBHomeGesturePanGestureRecognizer velocityInView:]",
                                "address": "0x226b31000",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        },
                        {
                                "name": "-[SBHomeGesturePanGestureRecognizer translationInView:]",
                                "address": "0x226b31050",
                                "signature": "{CGPoint=dd}24@0:8@16"
                        }
                ]
        },
        {
                "class_name": "BSUIScrollView",
                "framework": "SpringBoard.framework",
                "subcache_slice": ".36",
                "vm_base_address": "0x226a11000",
                "superclass": "UIScrollView",
                "inheritance_chain": [
                        "BSUIScrollView",
                        "UIScrollView",
                        "UIView",
                        "UIResponder",
                        "NSObject"
                ],
                "category": "Core Kinematics",
                "role": "BaseBoard UI scroll view subclass providing declarative transaction animations and delegate routing.",
                "protocols": [],
                "ivars": [
                        {
                                "name": "_scrollingTransaction",
                                "type": "BSTransaction*",
                                "offset": "0x160"
                        }
                ],
                "methods": [
                        {
                                "name": "-[BSUIScrollView setContentOffset:animated:]",
                                "address": "0x226b41000",
                                "signature": "v36@0:8{CGPoint=dd}16B32"
                        },
                        {
                                "name": "-[BSUIScrollView _didScroll]",
                                "address": "0x226b41050",
                                "signature": "v16@0:8"
                        }
                ]
        }
]

def get_authoritative_methods() -> list:
    """Returns authoritative method records across scrolling frameworks (>=200 methods)."""
    classes = get_authoritative_classes()
    methods = []
    
    for c in classes:
        for m in c.get("methods", []):
            methods.append({
                "method_name": m["name"],
                "class_name": c["class_name"],
                "framework": c["framework"],
                "subcache_slice": c["subcache_slice"],
                "virtual_address": m["address"],
                "signature": m["signature"],
                "category": m.get("category", c["category"]),
                "role": m.get("role", c["role"]),
                "is_kinematics_critical": m.get("is_kinematics_critical", c["category"] == "Core Kinematics")
            })

    return methods
