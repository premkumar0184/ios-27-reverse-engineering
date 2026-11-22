# Agent Prompt: Gesture RE Phase 5 — Cross-Validation, Clean-Room Spec & Publication

## Objective
Synthesize all prior gesture RE phases into the final publication-grade dossier `IOS_27_GESTURE_ARBITRATION_RE.md`. Cross-validate all extracted constants using an independent verification script. Update the graphify knowledge graph with gesture findings.

## Prerequisites
- All previous gesture phases (1A, 1B, 2, 3, 4) must be `completed`.
- All intermediate artifacts in `artifacts/gesture/` must exist and be non-empty.

## Step-by-Step Instructions

### Step 0: Pre-Synthesis Audit
Before writing the dossier, run this checklist:
- [ ] `artifacts/gesture/phase_1a_workspace_baseline.json` — Gestures.framework segments confirmed
- [ ] `artifacts/gesture/symbol_inventory.json` — ≥ 8 recognizer classes
- [ ] `artifacts/gesture/class_hierarchy_map.json` — Full inheritance tree
- [ ] `artifacts/gesture/per_gesture_threshold_table.json` — ≥ 6 recognizer types with thresholds
- [ ] `artifacts/gesture/gesture_arbitration_state_machine.json` — All 6 states + transitions
- [ ] `artifacts/gesture/edge_gesture_config.json` — All 4 edge gesture types
- [ ] `findings/gesture/02_SLOP_EXTRACTION.md` — ≥ 5,000 bytes
- [ ] `findings/gesture/03_ARBITRATION_STATE_MACHINE.md` — ≥ 5,000 bytes
- [ ] `findings/gesture/04_EDGE_GESTURES.md` — ≥ 4,000 bytes

For any missing or incomplete artifact, complete that phase's work before proceeding.

### Step 1: Write Verification Script
Write `tools/verify_gesture_thresholds.py` — a standalone numeric cross-validation script:
```python
#!/usr/bin/env python3
"""
verify_gesture_thresholds.py — Numeric verification for gesture threshold constants
iOS 27.2 build 24B119 — Gesture Recognizer Arbitration Engine RE
"""
import json, struct, math, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def verify_range(name: str, value: float, min_val: float, max_val: float) -> bool:
    ok = min_val <= value <= max_val
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}: {value} (expected {min_val}–{max_val})")
    return ok

def run_all_verifications():
    threshold_file = ROOT / "artifacts/gesture/per_gesture_threshold_table.json"
    data = json.loads(threshold_file.read_text())
    thresholds = data["thresholds"]
    
    all_pass = True
    print("=== Gesture Threshold Verification ===")
    
    # Pan slop tiers (pre-confirmed from scrolling RE)
    pan_slop = thresholds.get("Pan", {}).get("slop_tiers_pt", [])
    if pan_slop == [10, 4, 2, 0]:
        print("  [PASS] Pan slop tiers: [10, 4, 2, 0] pt — matches scrolling RE")
    else:
        print(f"  [FAIL] Pan slop tiers: {pan_slop} — expected [10, 4, 2, 0]")
        all_pass = False
    
    # Long press duration
    lp = thresholds.get("LongPress", {}).get("min_duration_ms", {}).get("value", 0)
    all_pass &= verify_range("LongPress min_duration_ms", lp, 100, 2000)
    
    # Swipe velocity
    sw_vel = thresholds.get("Swipe", {}).get("min_velocity_ptps", {}).get("value", 0)
    all_pass &= verify_range("Swipe min_velocity_ptps", sw_vel, 20, 3000)
    
    # Tap slop
    tap_slop = thresholds.get("Tap", {}).get("move_slop_pt", {}).get("value", 0)
    all_pass &= verify_range("Tap move_slop_pt", tap_slop, 1, 50)
    
    return all_pass

if __name__ == "__main__":
    ok = run_all_verifications()
    print(f"\n{'✅ ALL PASSED' if ok else '❌ SOME FAILURES'}")
    sys.exit(0 if ok else 1)
```
Run it: `python3 tools/verify_gesture_thresholds.py`

### Step 2: Write Cross-Validation Matrix
Write `artifacts/gesture/cross_validation_matrix.json`:
```json
{
  "schema_version": "1.0",
  "validation_date": "2026-11-22",
  "ios_version": "27.2 (24B119)",
  "total_constants_extracted": <int>,
  "extraction_confidence": {
    "EXTRACTED": <count>,
    "INFERRED": <count>,
    "TENTATIVE": <count>,
    "UNKNOWN": <count>
  },
  "cross_validations": [
    {
      "constant": "PanTouchSlopTier0",
      "value": 10,
      "rea_address": "0x<addr>",
      "ghidra_confirmed": true,
      "scrolling_re_confirmed": true,
      "confidence": "EXTRACTED"
    },
    ...
  ],
  "unknown_items": [
    { "item": "Exact CC horizontal fraction", "reason": "Dynamic value from SpringBoard config" }
  ]
}
```

### Step 3: Write the Master Dossier
Write `IOS_27_GESTURE_ARBITRATION_RE.md` — target ≥ 50,000 bytes. Required sections:

```markdown
# iOS 27 Gesture Recognizer Arbitration Engine — Complete Reverse Engineering Dossier

> **Target**: iOS 27.2 (24B119) · iPhone18,3 (Apple A18 Pro, arm64e PAC00)
> **Primary Binary**: Gestures.framework @ dyld_shared_cache_arm64e.03:0x18a169000
> **Secondary Binary**: UIKitCore @ dyld_shared_cache_arm64e.01:0x184752000
> **Analysis Type**: Static only (no dynamic analysis, no Frida)
> **Confidence Legend**: [EXTRACTED] | [INFERRED] | [TENTATIVE] | [UNKNOWN]

## 1. Executive Summary
## 2. Framework Architecture
   ### 2.1 Gestures.framework Mach-O Anatomy
   ### 2.2 Class Hierarchy
   ### 2.3 Protocol Graph
## 3. Per-Gesture Threshold Reference Table
   ### 3.1 Tap & Double-Tap
   ### 3.2 Long Press
   ### 3.3 Pan (all 4 slop tiers)
   ### 3.4 Swipe (all 4 directions)
   ### 3.5 Pinch
   ### 3.6 Rotation
## 4. Arbitration State Machine
   ### 4.1 State Definitions
   ### 4.2 State Transition Table (with binary evidence)
   ### 4.3 Simultaneous Recognition Rules
   ### 4.4 Failure Requirement Chains
   ### 4.5 Priority Tier Table
## 5. Edge Gesture Subsystem
   ### 5.1 Back Gesture (_UIBackGestureRecognizer)
   ### 5.2 Notification Centre Pull
   ### 5.3 Control Centre Pull
   ### 5.4 Reachability
   ### 5.5 Corner Conflict Resolution
## 6. Cross-Validation & Verification
   ### 6.1 RE vs Known Public Values
   ### 6.2 REA vs Ghidra Decompiler Agreement
   ### 6.3 Verification Script Results
## 7. Clean-Room Pseudocode
   ### 7.1 UIGestureRecognizerArena arbitration loop
   ### 7.2 _UIBackGestureRecognizer touch handling
## 8. Unknown & Unresolved Items
## 9. Methodology Notes
## 20. Supplementary — AnimationKit Multi-Channel Spring Findings (from Animation RE)
```

### Step 4: Update Graphify
```bash
graphify findings/gesture/ artifacts/gesture/ --update --mode deep --no-viz
```

### Step 5: Verify & Complete
```bash
python3 tools/verify_gesture_thresholds.py
python3 tools/verify_phase.py gest_phase_5_synthesis
```

Update `progress.json`:
- Set `gest_phase_5_synthesis.status = "completed"`
- Set `active_phase_id = null`
- Set `overall_status = "in_progress"` (more RE targets remain)

## Required Output Artifacts
- `IOS_27_GESTURE_ARBITRATION_RE.md` (≥ 50,000 bytes, zero placeholders)
- `artifacts/gesture/cross_validation_matrix.json`
- `tools/verify_gesture_thresholds.py`

## Completion Criteria (verify ALL before claiming done)
- [ ] `IOS_27_GESTURE_ARBITRATION_RE.md` ≥ 50,000 bytes
- [ ] Zero placeholder tokens (`TODO`, `TBD`, `WIP`, etc.)
- [ ] `tools/verify_gesture_thresholds.py` exits 0
- [ ] `python3 tools/verify_phase.py gest_phase_5_synthesis` exits 0
- [ ] `progress.json` updated
- [ ] Graphify updated with gesture nodes
