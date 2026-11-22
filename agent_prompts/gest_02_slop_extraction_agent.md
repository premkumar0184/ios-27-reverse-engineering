# Agent Prompt: Gesture RE Phase 2 — Slop & Velocity Threshold Extraction

## Objective
Extract all per-gesture slop (pt), velocity (pt/s), and hold-duration (ms) threshold constants from `Gestures.framework` and `UIKitCore`. Produce a complete threshold table covering every recognizer type including system/private recognizers.

## Prerequisites
- `gest_phase_1b_symbol_discovery` must be `completed`.
- The class hierarchy and ivar names from Phase 1B guide your search addresses.

## Target Constants Per Recognizer Type

| Recognizer | Constants to Find |
|-----------|-------------------|
| **Tap** | Move-tolerance slop (pt), max inter-tap interval (ms), required tap count |
| **Double-Tap** | Same as Tap + max time between taps (ms) |
| **Long Press** | Minimum press duration (ms), move-tolerance slop (pt), required touches |
| **Pan** | Touch-slop tier table [10/4/2/0 pt] (already known), minimum velocity to cancel |
| **Swipe** | Touch-slop (pt), minimum velocity (pt/s), maximum perpendicular movement (pt) |
| **Edge Swipe (generic)** | Edge inset width (pt), entry zone width (pt), minimum velocity (pt/s) |
| **Pinch** | Minimum scale change to begin (ratio), minimum touches = 2 |
| **Rotation** | Minimum rotation to begin (radians), minimum touches = 2 |

## Step-by-Step Instructions

### Step 0: Graphify Orientation
```bash
graphify query "gesture slop velocity threshold minimum duration"
graphify query "UISwipeGestureRecognizer velocity swipe direction"
graphify query "UILongPressGestureRecognizer minimumPressDuration"
```

### Step 1: Search for Threshold Symbols by Name
In Gestures.framework:
```json
{
  "ServerName": "rea",
  "ToolName": "search_procedures",
  "Arguments": { "query": "slop" }
}
```
Repeat for: `threshold`, `velocity`, `duration`, `movement`, `tolerance`, `swipe`, `begin`, `cancel`.

Also use `list_strings` to find numeric constants embedded as debug strings or assertions:
```json
{ "ServerName": "rea", "ToolName": "list_strings", "Arguments": {} }
```
Look for strings like: `"touchSlop"`, `"minimumVelocity"`, `"velocityThreshold"`, `"pressDuration"`, `"swipeVelocity"`, `"edgeWidth"`, `"allowedMovement"`.

### Step 2: Decompile Key Threshold-Setting Functions
For each discovered function, run `procedure_pseudo_code`:
```json
{
  "ServerName": "rea",
  "ToolName": "procedure_pseudo_code",
  "Arguments": { "procedure_address": "0x<address>" }
}
```
Focus on:
- `[UISwipeGestureRecognizer _touchesMoved:withEvent:]` — where swipe direction and velocity are evaluated
- `[UILongPressGestureRecognizer _touchesBegan:withEvent:]` — where timer fires for press duration
- `[UIPanGestureRecognizer _beginPan:]` — where the slop tiers are checked
- `[UITapGestureRecognizer _touchesEnded:withEvent:]` — tap movement tolerance check

### Step 3: Read Raw Threshold Bytes
For each identified threshold constant address, read raw bytes:
```json
{
  "ServerName": "rea",
  "ToolName": "read_bytes",
  "Arguments": { "address": "0x<address>", "size": 8 }
}
```
Interpret as:
- `int32`: for integer point values
- `float64` (CGFloat on arm64): for floating-point thresholds
- Compare to expected ranges: slop 0–50 pt, velocity 50–2000 pt/s, duration 50–2000 ms

### Step 4: Cross-Validate with Ghidra
For the 3 most important threshold-setting functions, run Ghidra independently:
```json
{
  "ServerName": "ghidra",
  "ToolName": "decompile_function",
  "Arguments": { "name": "UISwipeGestureRecognizer_touchesMoved" }
}
```
If values differ between REA and Ghidra, flag as `[TENTATIVE]` and document both readings.

### Step 5: Write Phase Artifacts

**`artifacts/gesture/per_gesture_threshold_table.json`**:
```json
{
  "schema_version": "1.0",
  "extraction_target": "iOS 27.2 build 24B119",
  "thresholds": {
    "Tap": {
      "move_slop_pt": { "value": <int>, "address": "0x<addr>", "confidence": "[EXTRACTED]" },
      "max_duration_ms": { "value": <int>, "address": "0x<addr>", "confidence": "[EXTRACTED]" },
      "required_tap_count": 1
    },
    "DoubleTap": {
      "move_slop_pt": { ... },
      "max_inter_tap_ms": { ... },
      "required_tap_count": 2
    },
    "LongPress": {
      "min_duration_ms": { "value": 500, "address": "0x<addr>", "confidence": "[EXTRACTED]" },
      "move_slop_pt": { ... }
    },
    "Pan": {
      "slop_tiers_pt": [10, 4, 2, 0],
      "slop_tier_addresses": ["0x<addr0>", "0x<addr1>", "0x<addr2>", "0x<addr3>"],
      "confidence": "[EXTRACTED — from scrolling RE]"
    },
    "Swipe": {
      "move_slop_pt": { ... },
      "min_velocity_ptps": { ... },
      "max_perpendicular_pt": { ... }
    },
    "EdgeSwipe_generic": {
      "edge_inset_width_pt": { ... },
      "entry_zone_width_pt": { ... },
      "min_velocity_ptps": { ... }
    },
    "Pinch": {
      "min_scale_delta": { ... },
      "required_touches": 2
    },
    "Rotation": {
      "min_rotation_radians": { ... },
      "required_touches": 2
    }
  }
}
```

**`findings/gesture/02_SLOP_EXTRACTION.md`** — Must be ≥ 5,000 bytes, contain:
- `##` sections per recognizer type
- Address tables: `| Symbol | Address | Raw Hex | Value | Type | Confidence |`
- Decompiled pseudocode excerpts showing where thresholds are applied
- Cross-validation results (REA vs Ghidra)
- Known vs newly extracted comparison (pan slop tiers as baseline)

### Step 6: Verify & Complete
```bash
python3 tools/verify_phase.py gest_phase_2_slop_extraction
```

## Required Output Artifacts
- `artifacts/gesture/per_gesture_threshold_table.json`
- `findings/gesture/02_SLOP_EXTRACTION.md` (≥ 5,000 bytes, no placeholders)

## Confidence Gate
Do not proceed to Phase 3 unless ≥ 6 recognizer types have at least one threshold extracted at `[EXTRACTED]` or `[INFERRED]` confidence.

## Anti-Hallucination Rules
- Never fabricate velocity thresholds. If a constant is not found in binary, mark `[UNKNOWN]`.
- Do not assume UIKit default values from public docs — find the actual binary constants.
- Pan slop tiers [10/4/2/0] are pre-confirmed from scrolling RE — do not re-invent them.
