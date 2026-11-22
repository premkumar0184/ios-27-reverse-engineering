# Agent Prompt: Gesture RE Phase 1B — Symbol Discovery

## Objective
Enumerate all Objective-C classes, protocols, and Swift types in `Gestures.framework`. Map the class hierarchy. Identify the gesture recognizer concrete classes and the arbitration/arena classes in `UIKitCore`. Extract ivar layouts for `UIGestureRecognizer` and its subclasses.

## Prerequisites
- `gest_phase_1a_workspace_baseline` must be `completed`.
- `artifacts/gesture/phase_1a_workspace_baseline.json` must exist and have `toolchain_trusted: true`.

## Step-by-Step Instructions

### Step 0: Graphify Orientation
```bash
graphify query "UIGestureRecognizer class hierarchy subclass"
graphify query "UIGestureRecognizerArena _UIGestureEnvironment"
graphify explain "UIGestureRecognizer"
```

### Step 1: Enumerate Classes in Gestures.framework
```json
{ "ServerName": "rea", "ToolName": "get_objc_classes", "Arguments": {} }
```
(After opening `Gestures.framework`.) Record ALL class names. Expected classes include:
- `UIGestureRecognizer` (may be in UIKitCore, re-exported)
- `UIPanGestureRecognizer`, `UISwipeGestureRecognizer`, `UITapGestureRecognizer`
- `UILongPressGestureRecognizer`, `UIPinchGestureRecognizer`, `UIRotationGestureRecognizer`
- `UIScreenEdgePanGestureRecognizer`
- Private: `_UISystemGestureGate`, `_UIGestureEnvironment`, `UIGestureRecognizerArena`
- Private: `_UIScreenEdgePanGestureRecognizer` subclasses (Back, NC, CC, Reachability variants)

### Step 2: Enumerate Protocols
```json
{ "ServerName": "rea", "ToolName": "get_objc_protocols", "Arguments": {} }
```
Expected protocols:
- `UIGestureRecognizerDelegate`
- `_UIGestureRecognizerArenaDelegate`
- `_UIGestureRecognizerArenaClient`
- `UIGestureRecognizerArena` (private protocol if exists)

### Step 3: Inspect UIGestureRecognizer ivar layout
```json
{
  "ServerName": "rea",
  "ToolName": "inspect_native_data_type",
  "Arguments": { "name": "UIGestureRecognizer" }
}
```
Key ivars to extract:
- `_state` (UIGestureRecognizerState enum encoding)
- `_touchSlop` / `_minimumMovement` / `_allowedMovement` (threshold storage ivar names may vary)
- `_velocityThreshold`
- `_minimumPressDuration` (for LongPress)
- `_numberOfTapsRequired`, `_numberOfTouchesRequired` (for Tap)
- `_minimumNumberOfTouches`, `_maximumNumberOfTouches` (for Pan/Pinch)
- `_swipeDirection` (UISwipeGestureRecognizerDirection bitmask)

### Step 4: Map Arbitration Classes in UIKitCore
Open UIKitCore (subcache `.01`):
```json
{
  "ServerName": "rea",
  "ToolName": "open_binary",
  "Arguments": {
    "path": "/home/prem/Projects/iOS 27/artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e",
    "image_path": "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore"
  }
}
```
Search for:
- `UIGestureRecognizerArena` — the collision resolution class
- `_UIGestureEnvironment` — the per-window gesture environment
- `_UISystemGestureGate` — system gesture pass-through gate

For each, run `inspect_native_data_type` and `procedure_pseudo_code` on key methods.

### Step 5: Extract Class Hierarchy
Identify inheritance chains:
```
UIGestureRecognizer
├── UIPanGestureRecognizer
│   └── UIScreenEdgePanGestureRecognizer
│       ├── _UIBackGestureRecognizer (Back swipe)
│       ├── _UINotificationCenterGestureRecognizer (NC pull)
│       ├── _UIControlCenterGestureRecognizer (CC pull)
│       └── _UIReachabilityGestureRecognizer (Reachability swipe-down)
├── UISwipeGestureRecognizer
├── UITapGestureRecognizer
│   └── UIDoubleTapGestureRecognizer (if separate)
├── UILongPressGestureRecognizer
├── UIPinchGestureRecognizer
└── UIRotationGestureRecognizer
```

### Step 6: Write Artifacts
Write two artifacts:

**`artifacts/gesture/symbol_inventory.json`**:
```json
{
  "Gestures_framework": {
    "objc_classes": [ ... ],
    "protocols": [ ... ],
    "private_classes": [ ... ]
  },
  "UIKitCore_gesture_classes": {
    "UIGestureRecognizer": { "ivars": [ ... ], "methods": [ ... ] },
    "UIGestureRecognizerArena": { "methods": [ ... ] },
    "_UIGestureEnvironment": { ... }
  }
}
```

**`artifacts/gesture/class_hierarchy_map.json`**:
```json
{
  "hierarchy": {
    "UIGestureRecognizer": {
      "subclasses": [ "UIPanGestureRecognizer", "UISwipeGestureRecognizer", ... ]
    },
    "UIScreenEdgePanGestureRecognizer": {
      "subclasses": [ "_UIBackGestureRecognizer", ... ]
    }
  },
  "arbitration_classes": [ "UIGestureRecognizerArena", "_UIGestureEnvironment" ]
}
```

### Step 7: Verify & Complete
```bash
python3 tools/verify_phase.py gest_phase_1b_symbol_discovery
```

## Required Output Artifacts
- `artifacts/gesture/symbol_inventory.json` — All classes, protocols, and ivar layouts
- `artifacts/gesture/class_hierarchy_map.json` — Class inheritance tree

## Confidence Gate
Do not proceed to Phase 2 unless ≥ 8 concrete recognizer classes are identified and the arbitration class (`UIGestureRecognizerArena` or equivalent) has at least one method decompiled.
