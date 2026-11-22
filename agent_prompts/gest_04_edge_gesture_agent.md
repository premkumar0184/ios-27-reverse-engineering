# Agent Prompt: Gesture RE Phase 4 — Edge Gesture Thresholds & Exclusion Zones

## Objective
Reverse engineer the four system edge gestures: Back swipe, Notification Centre pull, Control Centre pull, and Reachability swipe-down. Extract exact edge inset widths (pt), entry velocities (pt/s), exclusion zones, and the inter-gesture priority enforcement that prevents conflicts between them.

## Prerequisites
- `gest_phase_3_arbitration_state_machine` must be `completed`.
- Phase 1B identified `_UIBackGestureRecognizer`, `_UINotificationCenterGestureRecognizer`, `_UIControlCenterGestureRecognizer`, `_UIReachabilityGestureRecognizer` subclasses.

## Background Context

| Gesture | Edge | Activation Zone | Expected Approx Values |
|---------|------|----------------|------------------------|
| Back Swipe | Left edge | 15–20 pt from screen left | velocity ≥ ~50 pt/s |
| NC Pull | Top edge | Full width | velocity downward ≥ threshold |
| CC Pull | Top-right corner | Right ~1/3 of top edge, iOS 27 may use dynamic sizing | velocity downward ≥ threshold |
| Reachability | Home indicator region (bottom) | Swipe-down on home bar | velocity downward ≥ threshold |

These are **approximate public knowledge** values — your job is to find the exact binary constants.

## Step-by-Step Instructions

### Step 0: Graphify Orientation
```bash
graphify query "edge pan gesture back swipe screen edge"
graphify query "notification center control center edge inset gesture"
graphify query "UIScreenEdgePanGestureRecognizer edge exclusion"
```

### Step 1: Open SpringBoard + Gestures.framework
System edge gestures are typically registered in SpringBoard, with recognition logic in Gestures.framework/UIKitCore.

Open SpringBoard (subcache `.36`):
```json
{
  "ServerName": "rea",
  "ToolName": "open_binary",
  "Arguments": {
    "path": "/home/prem/Projects/iOS 27/artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e",
    "image_path": "/System/Library/PrivateFrameworks/SpringBoard.framework/SpringBoard"
  }
}
```
Search for edge gesture registrations:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "BackGesture" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "edgeRecognizer" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "NotificationCenter" } }
```

### Step 2: Extract Edge Inset Widths
In `UIScreenEdgePanGestureRecognizer` (UIKitCore or Gestures.framework):
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "edges" } }
```
Decompile:
- `[UIScreenEdgePanGestureRecognizer _touchesBegan:withEvent:]` — where edge region is checked
- Look for `UIEdgeInsets` comparisons or `x < edgeWidth` predicates

Also search for:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "edgeWidth" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "exclusionZone" } }
```

### Step 3: Back Gesture — _UIBackGestureRecognizer
Target the private subclass:
```json
{
  "ServerName": "rea",
  "ToolName": "inspect_native_data_type",
  "Arguments": { "name": "_UIBackGestureRecognizer" }
}
```
Decompile its `touchesBegan:`, `touchesMoved:` methods. Find:
- Left-edge activation width (pt) — expected ~15–25 pt
- Minimum velocity to commit (pt/s)
- Maximum vertical movement before cancellation (pt) — prevents triggering during downward swipes
- Whether there's a "bezel" mode for narrow-frame devices

### Step 4: NC/CC Pull — Notification & Control Centre Recognizers
Target `_UINotificationCenterGestureRecognizer` and `_UIControlCenterGestureRecognizer`.

For each, find:
- `topEdgeInset` — height of active zone from screen top (pt)
- `minimumVelocity` — downward pull velocity to commit (pt/s)
- For CC: horizontal exclusion zone (which fraction of top edge activates CC vs NC)

Search in SpringBoard for registration:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "SBControlCenterController" } }
```

### Step 5: Reachability — _UIReachabilityGestureRecognizer
Find the home-bar swipe-down threshold:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "Reachability" } }
```
Document:
- Home indicator region height (pt) — the activation strip at bottom
- Minimum downward velocity (pt/s) to trigger Reachability vs dismissing it
- Whether haptic feedback address is cited nearby (indicating confirmation point)

### Step 6: Inter-Gesture Priority Enforcement
When Back swipe and NC/CC pull both begin in a corner (top-left = CC risk + Back risk on iPad), how is conflict resolved?

Search for:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "conflict" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "exclusiveTouch" } }
```
Decompile any priority-override or conflict-resolution function.

### Step 7: Write Phase Artifacts

**`artifacts/gesture/edge_gesture_config.json`**:
```json
{
  "schema_version": "1.0",
  "edge_gestures": {
    "Back": {
      "recognizer_class": "_UIBackGestureRecognizer",
      "activation_edge": "UIRectEdgeLeft",
      "edge_inset_pt": { "value": <int>, "address": "0x<addr>", "confidence": "[EXTRACTED]" },
      "min_velocity_ptps": { "value": <float>, "address": "0x<addr>", "confidence": "[EXTRACTED]" },
      "max_perpendicular_movement_pt": { ... },
      "disabled_conditions": ["UINavigationController at root", "modal presented fullscreen"]
    },
    "NotificationCentre": {
      "recognizer_class": "_UINotificationCenterGestureRecognizer",
      "activation_edge": "UIRectEdgeTop",
      "top_inset_height_pt": { ... },
      "horizontal_zone": "full_width",
      "min_velocity_ptps": { ... }
    },
    "ControlCentre": {
      "recognizer_class": "_UIControlCenterGestureRecognizer",
      "activation_edge": "UIRectEdgeTop",
      "top_inset_height_pt": { ... },
      "horizontal_zone": "right_fraction",
      "right_fraction": { "value": <float>, "confidence": "[EXTRACTED|INFERRED]" },
      "min_velocity_ptps": { ... }
    },
    "Reachability": {
      "recognizer_class": "_UIReachabilityGestureRecognizer",
      "activation_edge": "UIRectEdgeBottom",
      "home_bar_region_height_pt": { ... },
      "min_velocity_ptps": { ... }
    }
  },
  "inter_gesture_conflicts": [ ... ]
}
```

**`findings/gesture/04_EDGE_GESTURES.md`** — Must be ≥ 4,000 bytes, contain:
- Edge zone diagram (ASCII or Mermaid)
- Per-gesture threshold table with address evidence
- Priority enforcement mechanism with decompiled pseudocode
- Conflict resolution rules (what happens at corner regions)

### Step 8: Write Pseudocode
Write `artifacts/gesture/pseudocode/back_gesture_recognizer.pseudo.c` — clean-room C pseudocode for `_UIBackGestureRecognizer` touch handling.

### Step 9: Verify & Complete
```bash
python3 tools/verify_phase.py gest_phase_4_edge_gestures
```

## Required Output Artifacts
- `artifacts/gesture/edge_gesture_config.json`
- `findings/gesture/04_EDGE_GESTURES.md` (≥ 4,000 bytes)
- `artifacts/gesture/pseudocode/back_gesture_recognizer.pseudo.c`

## Confidence Gate
Do not proceed to Phase 5 unless:
- All 4 edge gesture classes are located and decompiled
- Edge inset widths for Back gesture and NC/CC pull have binary evidence
- Priority conflict mechanism between system gestures is documented
