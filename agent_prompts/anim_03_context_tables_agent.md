# Agent Prompt: Phase 3 — Context Parameter Tables & UIKit Timing Curves

## Mission
Expand and verify the per-animation-context parameter table from Phase 2. Add non-spring timing curves (cubic Bézier, custom CAMediaTimingFunction). Produce the complete cross-context comparison matrix.

**Skills to use**: `rea`, `graphify`, `agency-evidence-collector` (for evidence cross-check)

## Pre-Execution
```bash
graphify query "UIKit animation timing curve cubic bezier"
graphify query "CAMediaTimingFunction parameters"
# Load Phase 2 reference
cat artifacts/animation/animation_physics_reference.json | python3 -c "
import json,sys; d=json.load(sys.stdin)
contexts = d.get('animation_contexts', {})
unknowns = [k for k,v in contexts.items() if v.get('confidence') == 'UNKNOWN']
print(f'Contexts with UNKNOWN confidence: {unknowns}')
"
```

## Step 1: Upgrade UNKNOWN Contexts from Phase 2

For each `animation_context` that has `confidence: UNKNOWN` in `animation_physics_reference.json`:
1. Try REA string search to find context-identifying string in source binary
2. Trace xrefs from that string → function → parameter
3. If still not found, attempt cross-reference from call graph (what calls the animation function?)
4. Document the investigation trail — even `[UNKNOWN]` requires documenting what was tried

## Step 2: Non-Spring Timing Curves

Some iOS animations use cubic Bézier curves (`CAMediaTimingFunction`), not springs. Extract:
- `kCAMediaTimingFunctionDefault` values
- `kCAMediaTimingFunctionEaseIn`, `EaseOut`, `EaseInEaseOut`
- Any custom `CAMediaTimingFunction` defined in `UIKitCore` or `SystemUIAnimationKit`
- SwiftUI's `.easeIn`, `.easeOut`, custom `Animation` types mapping

For each, extract the control points (cp1x, cp1y, cp2x, cp2y) from the binary.

## Step 3: Interactive Transition Parameters

Extract parameters for interruptible animations (`UIViewPropertyAnimator`):
- Completion threshold (at what `fractionComplete` does it snap to end?)
- Reverse threshold
- Spring velocity blending on interruption
- `scrubsLinearly` behavior

## Step 4: ProMotion Frame Rate Hints per Animation Type

From QuartzCore and UIKitCore, extract `CAFrameRateRange` preferred/min/max values associated with animation contexts:
- Modal presentation: preferred FPS
- Notification banner: preferred FPS
- Homescreen icon drag: preferred FPS

## Required Deliverables

### `artifacts/animation/timing_curve_reference.json`
```json
{
  "cubic_bezier_curves": {
    "kCAMediaTimingFunctionDefault": { "cp1": [0.25, 0.1], "cp2": [0.25, 1.0], "source_address": "0x...", "confidence": "EXTRACTED" },
    "kCAMediaTimingFunctionEaseIn": { ... },
    "custom_sheet_dismiss": { ... }
  },
  "frame_rate_hints": {
    "modal_presentation": { "preferred": 120, "minimum": 60, "maximum": 120, "source_address": "0x...", "confidence": "EXTRACTED" },
    "notification_banner": { ... }
  }
}
```

### `artifacts/animation/cross_context_matrix.json`
Full table: every animation context × (spring_params OR bezier_params) × frame_rate_hint × settling_time.

### `findings/animation/03_CONTEXT_TABLES.md`
Technical write-up with context taxonomy diagram, full parameter table, timing curve comparison.

## Completion Gate
`python3 tools/verify_phase.py anim_phase_3_context_tables`

Verification checks:
- `timing_curve_reference.json` valid, has ≥ 4 cubic Bézier definitions
- `cross_context_matrix.json` has ≥ 10 animation contexts
- No context in matrix has `confidence: UNKNOWN` without documented investigation trail
