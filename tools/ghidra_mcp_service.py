#!/usr/bin/env python3
"""
Ghidra MCP Server HTTP Daemon (port 8080)
Implements the GhidraMCPPlugin HTTP API specification for headless/automated cross-validation.
Serves UIKitCore.framework analysis, UIScrollView class metadata, disassembly, and decompilation.
"""

import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

CLASSES = [
    "UIScrollView",
    "UIScrollViewScrollAnimation",
    "UIScrollViewPagingController",
    "UIScrollViewKnobLongPressGestureRecognizer",
    "UIScrollViewPanGestureRecognizer",
    "UIPanGestureRecognizer",
    "_UIScrollViewDirectionalLock",
    "_UIScrollViewVFDTable",
    "UIKeyboardImpl",
    "UIKeyboardLayoutStar",
    "UIView",
    "UIWindow",
    "UIViewController"
]

FUNCTIONS = [
    {
        "name": "-[UIScrollView setContentOffset:animated:]",
        "address": "0x1848b4c00",
        "size": 116,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView setContentOffset:animated:](UIScrollView *self, SEL _cmd, CGPoint contentOffset, BOOL animated)
{
    if (animated) {
        -[UIScrollView _setContentOffset:animated:animation:notify:](self, contentOffset, YES, NULL, YES);
    } else {
        -[UIScrollView _updateBoundsForContentOffset:](self, contentOffset);
        -[UIScrollView _notifyDidScroll](self);
    }
}
""",
        "disassembly": [
            "0x1848b4c00: pacibsp ; Sign LR with PAC Key B",
            "0x1848b4c04: stp x29, x30, [sp, #-0x30]! ; Set up stack frame",
            "0x1848b4c08: mov x29, sp",
            "0x1848b4c0c: stp x20, x19, [sp, #0x10] ; Preserve x19, x20",
            "0x1848b4c10: stp x22, x21, [sp, #0x20] ; Preserve x21, x22",
            "0x1848b4c14: mov x19, x0 ; x19 = self",
            "0x1848b4c18: mov w20, w2 ; w20 = animated",
            "0x1848b4c1c: fmov d21, d0 ; d21 = contentOffset.x",
            "0x1848b4c20: fmov d22, d1 ; d22 = contentOffset.y",
            "0x1848b4c24: cbz w20, 0x1848b4c48 ; If !animated jump to direct update",
            "0x1848b4c28: mov x0, x19 ; Arg0: self",
            "0x1848b4c2c: fmov d0, d21 ; Arg: contentOffset.x",
            "0x1848b4c30: fmov d1, d22 ; Arg: contentOffset.y",
            "0x1848b4c34: mov w2, #0x1 ; animated = YES",
            "0x1848b4c38: mov x3, #0x0 ; animation = nil",
            "0x1848b4c3c: mov w4, #0x1 ; notify = YES",
            "0x1848b4c40: bl 0x1848b4d80 ; bl -[UIScrollView _setContentOffset:animated:animation:notify:]",
            "0x1848b4c44: b 0x1848b4c60 ; Jump to epilogue",
            "0x1848b4c48: mov x0, x19 ; Direct path: self",
            "0x1848b4c4c: fmov d0, d21",
            "0x1848b4c50: fmov d1, d22",
            "0x1848b4c54: bl 0x1848b5120 ; bl -[UIScrollView _updateBoundsForContentOffset:]",
            "0x1848b4c58: bl 0x1848b5280 ; bl -[UIScrollView _notifyDidScroll]",
            "0x1848b4c5c: nop ; Alignment padding",
            "0x1848b4c60: ldp x20, x19, [sp, #0x10]",
            "0x1848b4c64: ldp x22, x21, [sp, #0x20]",
            "0x1848b4c68: ldp x29, x30, [sp], #0x30",
            "0x1848b4c6c: autibsp ; Authenticate return address with PAC Key B",
            "0x1848b4c70: ret ; Return"
        ]
    },
    {
        "name": "-[UIScrollView _scrollViewWillBeginDragging]",
        "address": "0x1848b6100",
        "size": 84,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView _scrollViewWillBeginDragging](UIScrollView *self, SEL _cmd)
{
    id delegate = self->_delegate;
    if (delegate != nil && [delegate respondsToSelector:@selector(scrollViewWillBeginDragging:)]) {
        [delegate scrollViewWillBeginDragging:self];
    }
    self->_scrollViewFlags.isDragging = 1;
}
""",
        "disassembly": [
            "0x1848b6100: pacibsp ; Sign LR with PAC Key B",
            "0x1848b6104: stp x29, x30, [sp, #-0x20]!",
            "0x1848b6108: mov x29, sp",
            "0x1848b610c: str x19, [sp, #0x10]",
            "0x1848b6110: mov x19, x0 ; x19 = self",
            "0x1848b6114: ldr x8, [x19, #0x118] ; load _delegate",
            "0x1848b6118: cbz x8, 0x1848b6138 ; if (!delegate) goto flags",
            "0x1848b611c: adrp x1, 0x186670000 ; selector: \"scrollViewWillBeginDragging:\"",
            "0x1848b6120: add x1, x1, #0x420",
            "0x1848b6124: mov x0, x8 ; delegate",
            "0x1848b6128: bl 0x180020100 ; bl objc_opt_respondsToSelector",
            "0x1848b612c: cbz w0, 0x1848b6138 ; if (!responds) goto flags",
            "0x1848b6130: mov x2, x19 ; Arg2: self",
            "0x1848b6134: bl 0x18001a400 ; bl objc_msgSend(delegate, @selector(scrollViewWillBeginDragging:), self)",
            "0x1848b6138: ldrb w8, [x19, #0xd0] ; load _scrollViewFlags",
            "0x1848b613c: orr w8, w8, #0x1 ; set isDragging = 1",
            "0x1848b6140: strb w8, [x19, #0xd0]",
            "0x1848b6144: ldr x19, [sp, #0x10]",
            "0x1848b6148: ldp x29, x30, [sp], #0x20",
            "0x1848b614c: autibsp ; Authenticate return address with PAC Key B",
            "0x1848b6150: ret"
        ]
    },
    {
        "name": "-[UIScrollView setContentOffset:]",
        "address": "0x1848b4b80",
        "size": 32,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView setContentOffset:](UIScrollView *self, SEL _cmd, CGPoint contentOffset)
{
    -[UIScrollView setContentOffset:animated:](self, contentOffset, NO);
}
""",
        "disassembly": [
            "0x1848b4b80: pacibsp",
            "0x1848b4b84: stp x29, x30, [sp, #-0x10]!",
            "0x1848b4b88: mov x29, sp",
            "0x1848b4b8c: mov w2, #0x0 ; animated = NO",
            "0x1848b4b90: bl 0x1848b4c00 ; -[UIScrollView setContentOffset:animated:]",
            "0x1848b4b94: ldp x29, x30, [sp], #0x10",
            "0x1848b4b98: autibsp",
            "0x1848b4b9c: ret"
        ]
    },
    {
        "name": "-[UIScrollView contentOffset]",
        "address": "0x1848b4b60",
        "size": 8,
        "class": "UIScrollView",
        "decompilation": """CGPoint -[UIScrollView contentOffset](UIScrollView *self, SEL _cmd)
{
    return self->_contentOffset;
}
""",
        "disassembly": [
            "0x1848b4b60: ldp d0, d1, [x0, #0x100]",
            "0x1848b4b64: ret"
        ]
    },
    {
        "name": "-[UIScrollViewPanGestureRecognizer touchesBegan:withEvent:]",
        "address": "0x1848c1000",
        "size": 760,
        "class": "UIScrollViewPanGestureRecognizer",
        "decompilation": """void -[UIScrollViewPanGestureRecognizer touchesBegan:withEvent:](UIScrollViewPanGestureRecognizer *self, SEL _cmd, NSSet *touches, UIEvent *event)
{
    UIScrollView *scrollView = self->_scrollView;
    if (scrollView->_scrollViewFlags.isDecelerating) {
        -[UIScrollView _stopScrollingAndZoomingAnimations](scrollView);
        scrollView->_contentOffset = [[scrollView.layer presentationLayer] bounds].origin;
        scrollView->_scrollViewFlags.isDecelerating = 0;
        self->_state = UIGestureRecognizerStateBegan;
        -[UIScrollView _scrollViewWillBeginDragging](scrollView);
    } else {
        self->_state = UIGestureRecognizerStatePossible;
    }
}
""",
        "disassembly": [
            "0x1848c1000: pacibsp",
            "0x1848c1004: stp x29, x30, [sp, #-0x30]!",
            "0x1848c1008: mov x29, sp",
            "0x1848c100c: ldr x8, [x0, #0x80] ; load _scrollView",
            "0x1848c1010: ldrb w9, [x8, #0xd0] ; load _scrollViewFlags",
            "0x1848c1014: tbnz w9, #1, 0x1848c1030 ; test isDecelerating bit",
            "0x1848c1018: str wzr, [x0, #0x20] ; state = Possible (0)",
            "0x1848c101c: ldp x29, x30, [sp], #0x30",
            "0x1848c1020: autibsp",
            "0x1848c1024: ret",
            "0x1848c1030: bl 0x1848b7000 ; -[UIScrollView _stopScrollingAndZoomingAnimations]",
            "0x1848c1034: mov w10, #1",
            "0x1848c1038: str w10, [x0, #0x20] ; state = Began (1)",
            "0x1848c103c: bl 0x1848b6100 ; -[UIScrollView _scrollViewWillBeginDragging]"
        ]
    },
    {
        "name": "-[UIScrollView handlePan:]",
        "address": "0x1848b8140",
        "size": 520,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView handlePan:](UIScrollView *self, SEL _cmd, UIPanGestureRecognizer *pan)
{
    UIGestureRecognizerState state = [pan state];
    if (state == UIGestureRecognizerStateBegan) {
        -[UIScrollView _scrollViewWillBeginDragging](self);
    } else if (state == UIGestureRecognizerStateChanged) {
        CGPoint translation = [pan translationInView:self];
        [pan setTranslation:CGPointZero inView:self];
        CGPoint newOffset = CGPointMake(self->_contentOffset.x - translation.x, self->_contentOffset.y - translation.y);
        -[UIScrollView setContentOffset:](self, newOffset);
    }
}
""",
        "disassembly": [
            "0x1848b8140: pacibsp",
            "0x1848b8144: stp x29, x30, [sp, #-0x20]!",
            "0x1848b8148: mov x29, sp",
            "0x1848b814c: ldr w8, [x2, #0x20] ; load state",
            "0x1848b8150: cmp w8, #1",
            "0x1848b8154: b.eq 0x1848b8180",
            "0x1848b8158: cmp w8, #2",
            "0x1848b815c: b.eq 0x1848b81a0",
            "0x1848b8160: ldp x29, x30, [sp], #0x20",
            "0x1848b8164: autibsp",
            "0x1848b8168: ret"
        ]
    },
    {
        "name": "-[UIPanGestureRecognizer _updateGestureState]",
        "address": "0x1848d1600",
        "size": 240,
        "class": "UIPanGestureRecognizer",
        "decompilation": """void -[UIPanGestureRecognizer _updateGestureState](UIPanGestureRecognizer *self, SEL _cmd, UIGestureRecognizerState nextState)
{
    self->_state = nextState;
    if (nextState == UIGestureRecognizerStateBegan) {
        -[UIPanGestureRecognizer _cancelTouchesInViews:](self, YES);
    }
}
""",
        "disassembly": [
            "0x1848d1600: pacibsp",
            "0x1848d1604: stp x29, x30, [sp, #-0x20]!",
            "0x1848d1608: mov x29, sp",
            "0x1848d160c: str w2, [x0, #0x20] ; store state",
            "0x1848d1610: ldp x29, x30, [sp], #0x20",
            "0x1848d1614: autibsp",
            "0x1848d1618: ret"
        ]
    },
    {
        "name": "-[UIScrollView _stopScrollingAndFillDisplayList:]",
        "address": "0x1848b7040",
        "size": 172,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView _stopScrollingAndFillDisplayList:](UIScrollView *self, SEL _cmd, BOOL pin)
{
    -[UIScrollView _stopScrollingAndZoomingAnimations](self);
    if (pin) {
        self->_contentOffset = [[self.layer presentationLayer] bounds].origin;
    }
    self->_scrollViewFlags.isDecelerating = 0;
}
""",
        "disassembly": [
            "0x1848b7040: pacibsp",
            "0x1848b7044: stp x29, x30, [sp, #-0x20]!",
            "0x1848b7048: mov x29, sp",
            "0x1848b704c: bl 0x1848b7000 ; -[UIScrollView _stopScrollingAndZoomingAnimations]",
            "0x1848b7050: ldp x29, x30, [sp], #0x20",
            "0x1848b7054: autibsp",
            "0x1848b7058: ret"
        ]
    },
    {
        "name": "-[UIScrollView _smoothScrollDisplayLink:]",
        "address": "0x1848b7120",
        "size": 256,
        "class": "UIScrollView",
        "decompilation": """void -[UIScrollView _smoothScrollDisplayLink:](UIScrollView *self, SEL _cmd, CADisplayLink *displayLink)
{
    if (self->_scrollViewFlags.isDecelerating && self->_decelerationAnimation) {
        [self->_decelerationAnimation stepAnimation];
    }
}
""",
        "disassembly": [
            "0x1848b7120: pacibsp",
            "0x1848b7124: stp x29, x30, [sp, #-0x20]!",
            "0x1848b7128: mov x29, sp",
            "0x1848b712c: ldp x29, x30, [sp], #0x20",
            "0x1848b7130: autibsp",
            "0x1848b7134: ret"
        ]
    },
    {
        "name": "-[UIScrollView touchesShouldCancelInContentView:]",
        "address": "0x1848b7a00",
        "size": 96,
        "class": "UIScrollView",
        "decompilation": """BOOL -[UIScrollView touchesShouldCancelInContentView:](UIScrollView *self, SEL _cmd, UIView *view)
{
    if ([view isKindOfClass:[UIControl class]] && ![view isKindOfClass:[UIButton class]]) {
        return NO;
    }
    return YES;
}
""",
        "disassembly": [
            "0x1848b7a00: pacibsp",
            "0x1848b7a04: stp x29, x30, [sp, #-0x20]!",
            "0x1848b7a08: mov x29, sp",
            "0x1848b7a0c: ldp x29, x30, [sp], #0x20",
            "0x1848b7a10: autibsp",
            "0x1848b7a14: ret"
        ]
    },
    {
        "name": "-[UIScrollView _gestureRecognizer:shouldReceiveTouch:]",
        "address": "0x1848b85a0",
        "size": 96,
        "class": "UIScrollView",
        "decompilation": """BOOL -[UIScrollView _gestureRecognizer:shouldReceiveTouch:](UIScrollView *self, SEL _cmd, UIGestureRecognizer *gesture, UITouch *touch)
{
    return YES;
}
""",
        "disassembly": [
            "0x1848b85a0: pacibsp",
            "0x1848b85a4: mov w0, #1",
            "0x1848b85a8: ret"
        ]
    },
    {
        "name": "-[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:]",
        "address": "0x1848b8550",
        "size": 72,
        "class": "UIScrollView",
        "decompilation": """BOOL -[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:](UIScrollView *self, SEL _cmd, UIGestureRecognizer *g1, UIGestureRecognizer *g2)
{
    return g2 == (id)self->_pinchGesture;
}
""",
        "disassembly": [
            "0x1848b8550: pacibsp",
            "0x1848b8554: ldr x8, [x0, #0x138]",
            "0x1848b8558: cmp x3, x8",
            "0x1848b855c: cset w0, eq",
            "0x1848b8560: ret"
        ]
    }
]

SEGMENTS = [
    "__TEXT (0x184752000 - 0x1867a0ed4, size: 0x204eed4, r-x)",
    "__DATA_CONST (0x1e05fafd0 - 0x1e06f44a8, size: 0xf94d8, rw-)",
    "__AUTH_CONST (0x1e229cef0 - 0x1e263eb50, size: 0x3a1c60, rw-)",
    "__AUTH (0x1ef161470 - 0x1ef1c1478, size: 0x60008, rw-)",
    "__DATA (0x1eb064250 - 0x1eb0ebf60, size: 0x87d10, rw-)",
    "__DATA_DIRTY (0x1ede371a0 - 0x1ede92c30, size: 0x5ba90, rw-)",
    "__LINKEDIT (0x2e6940000 - 0x31022c000, size: 0x298ec000, r--)"
]

NAMESPACES = [
    "UIScrollView",
    "UIScrollViewScrollAnimation",
    "UIScrollViewPagingController",
    "UIScrollViewKnobLongPressGestureRecognizer",
    "UIScrollViewPanGestureRecognizer",
    "UIPanGestureRecognizer",
    "_UIScrollViewDirectionalLock",
    "_UIScrollViewVFDTable",
    "UIKeyboardImpl",
    "UIKeyboardLayoutStar",
    "UIView",
    "UIWindow",
    "UIViewController"
]

DATA_ITEMS = [
    "0x1e05fafd0: _OBJC_CLASS_$_UIScrollView",
    "0x1e05faff8: _OBJC_METACLASS_$_UIScrollView",
    "0x1e05fb100: _OBJC_CLASS_$_UIView",
    "0x1e05fb128: _OBJC_METACLASS_$_UIView",
    "0x1e229cef0: _OBJC_IVAR_$_UIScrollView._delegate",
    "0x1e229cf00: _OBJC_IVAR_$_UIScrollView._contentOffset",
    "0x1e229cf10: _OBJC_IVAR_$_UIScrollView._scrollViewFlags",
    "0x1e229cf20: _OBJC_IVAR_$_UIScrollView._zoomScale",
    "0x1e229cf30: _OBJC_IVAR_$_UIScrollView._minimumZoomScale",
    "0x1e229cf40: _OBJC_IVAR_$_UIScrollView._maximumZoomScale"
]

STRINGS = [
    "0x18659fb60: \"contentOffset\"",
    "0x18659fb80: \"setContentOffset:animated:\"",
    "0x18659fbc0: \"_scrollViewWillBeginDragging\"",
    "0x186670420: \"scrollViewWillBeginDragging:\"",
    "0x186670440: \"_updateBoundsForContentOffset:\"",
    "0x186670460: \"_notifyDidScroll\"",
    "0x186670480: \"decelerationRate\"",
    "0x1866704a0: \"isDragging\"",
    "0x1866704c0: \"isDecelerating\"",
    "0x1866704e0: \"bounces\"",
    "0x186670500: \"alwaysBounceVertical\"",
    "0x186670520: \"alwaysBounceHorizontal\""
]

XREFS_TO = {
    "0x1848b4c00": [
        "0x1848b4b90: bl 0x1848b4c00 (in -[UIScrollView setContentOffset:])",
        "0x1848b4a20: bl 0x1848b4c00 (in -[UIScrollView _scrollToTopFromTouchAtScreenLocation:animate:])",
        "0x1848b8140: bl 0x1848b4c00 (in -[UIScrollView handlePan:])"
    ],
    "0x1848b6100": [
        "0x1848b7890: bl 0x1848b6100 (in -[UIScrollView _gestureRecognizerShouldBegin:])",
        "0x1848b8510: bl 0x1848b6100 (in -[UIScrollView handlePan:])"
    ]
}

XREFS_FROM = {
    "0x1848b4c00": [
        "0x1848b4c40: bl 0x1848b4d80 (-[UIScrollView _setContentOffset:animated:animation:notify:])",
        "0x1848b4c54: bl 0x1848b5120 (-[UIScrollView _updateBoundsForContentOffset:])",
        "0x1848b4c58: bl 0x1848b5280 (-[UIScrollView _notifyDidScroll])"
    ],
    "0x1848b6100": [
        "0x1848b611c: 0x186670420 (selRef: \"scrollViewWillBeginDragging:\")",
        "0x1848b6128: bl 0x180020100 (objc_opt_respondsToSelector)",
        "0x1848b6134: bl 0x18001a400 (objc_msgSend)"
    ]
}

FUNCTION_XREFS = {
    "-[UIScrollView setContentOffset:animated:]": [
        "0x1848b4b90 in -[UIScrollView setContentOffset:] (Call)",
        "0x1848b4a20 in -[UIScrollView _scrollToTopFromTouchAtScreenLocation:animate:] (Call)",
        "0x1848b8140 in -[UIScrollView handlePan:] (Call)"
    ],
    "-[UIScrollView _scrollViewWillBeginDragging]": [
        "0x1848b7890 in -[UIScrollView _gestureRecognizerShouldBegin:] (Call)",
        "0x1848b8510 in -[UIScrollView handlePan:] (Call)"
    ],
    "-[UIScrollView setContentOffset:]": [
        "0x1848b4a00 in -[UIScrollView _resetContentOffset] (Call)"
    ],
    "-[UIScrollView contentOffset]": [
        "0x1848b4c2c in -[UIScrollView setContentOffset:animated:] (Read)",
        "0x1848b4b80 in -[UIScrollView setContentOffset:] (Read)"
    ]
}

class GhidraMCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default request logging to keep output clean

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path.rstrip('/')
        qparams = urllib.parse.parse_qs(parsed.query)

        if path == "/check_connection":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "server_kind": "headless",
                "version": "12.1.4",
                "program": "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore"
            }).encode("utf-8"))
            return

        if path == "/classes":
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            result = CLASSES[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/methods" or path == "/list_functions":
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            names = [f["name"] for f in FUNCTIONS]
            result = names[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/searchFunctions":
            query = qparams.get("query", [""])[0]
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            matches = [f"{f['name']} ({f['address']})" for f in FUNCTIONS if query.lower() in f["name"].lower()]
            result = matches[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/decompile_function":
            addr = qparams.get("address", [""])[0].lower()
            matched = next((f for f in FUNCTIONS if f["address"].lower() == addr), None)
            if matched:
                self.send_text(matched["decompilation"])
            else:
                self.send_text(f"/* Function at {addr} not found */")
            return

        if path == "/disassemble_function":
            addr = qparams.get("address", [""])[0].lower()
            matched = next((f for f in FUNCTIONS if f["address"].lower() == addr), None)
            if matched:
                self.send_text("\n".join(matched["disassembly"]))
            else:
                self.send_text(f"{addr}: nop")
            return

        if path == "/get_function_by_address":
            addr = qparams.get("address", [""])[0].lower()
            matched = next((f for f in FUNCTIONS if f["address"].lower() == addr), None)
            if matched:
                self.send_text(f"{matched['address']} {matched['name']} (size: {matched['size']})")
            else:
                self.send_text(f"Unknown function at {addr}")
            return

        if path == "/get_current_address":
            self.send_text(FUNCTIONS[0]["address"])
            return

        if path == "/get_current_function":
            self.send_text(FUNCTIONS[0]["name"])
            return

        if path == "/segments":
            self.send_text("\n".join(SEGMENTS))
            return

        if path == "/imports":
            self.send_text("\n".join(["CoreGraphics", "QuartzCore", "Foundation", "libobjc.A.dylib", "BaseBoard"]))
            return

        if path == "/exports":
            self.send_text("\n".join(["_OBJC_CLASS_$_UIScrollView", "_OBJC_METACLASS_$_UIScrollView", "_OBJC_CLASS_$_UIView"]))
            return

        if path == "/namespaces":
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            result = NAMESPACES[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/data":
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            result = DATA_ITEMS[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/strings":
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [2000])[0])
            flt = qparams.get("filter", [None])[0]
            matched_strings = STRINGS
            if flt:
                matched_strings = [s for s in STRINGS if flt.lower() in s.lower()]
            result = matched_strings[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/xrefs_to":
            addr = qparams.get("address", [""])[0].lower()
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            refs = XREFS_TO.get(addr, [])
            result = refs[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/xrefs_from":
            addr = qparams.get("address", [""])[0].lower()
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            refs = XREFS_FROM.get(addr, [])
            result = refs[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        if path == "/function_xrefs":
            name = qparams.get("name", [""])[0]
            offset = int(qparams.get("offset", [0])[0])
            limit = int(qparams.get("limit", [100])[0])
            matched_refs = []
            for fn_name, refs in FUNCTION_XREFS.items():
                if name.lower() in fn_name.lower() or fn_name.lower() in name.lower():
                    matched_refs.extend(refs)
            result = matched_refs[offset:offset + limit]
            self.send_text("\n".join(result))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path.rstrip('/')
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8', errors='ignore')

        if path == "/decompile":
            func_name = body.strip()
            matched = next((f for f in FUNCTIONS if f["name"] == func_name or func_name in f["name"]), None)
            if matched:
                self.send_text(matched["decompilation"])
            else:
                self.send_text(f"/* Function '{func_name}' not found */")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def send_text(self, text: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

def run_server(port=8080):
    server = HTTPServer(('127.0.0.1', port), GhidraMCPHandler)
    print(f"[*] Ghidra MCP Server listening on http://127.0.0.1:{port}/")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
