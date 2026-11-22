# Agent Prompt: Gesture RE Phase 3 — Arbitration State Machine

## Objective
Reverse engineer the full gesture recognizer arbitration state machine implemented in `UIGestureRecognizerArena` / `_UIGestureEnvironment`. Document every state, every state-transition predicate, and the simultaneous-recognition rules that determine which recognizer "wins" when multiple fire at once.

## Prerequisites
- `gest_phase_2_slop_extraction` must be `completed`.
- Phase 1B class hierarchy and Phase 2 threshold values inform state transition predicates.

## State Machine Reference

The public UIGestureRecognizerState enum:
```
UIGestureRecognizerStatePossible   = 0  // Default, waiting for touch
UIGestureRecognizerStateBegan      = 1  // Discrete: not used; Continuous: gesture recognized
UIGestureRecognizerStateChanged    = 2  // Continuous: gesture updated
UIGestureRecognizerStateEnded      = 3  // (Recognized for discrete gestures)
UIGestureRecognizerStateCancelled  = 4  // System interrupted
UIGestureRecognizerStateFailed     = 5  // Did not recognize
UIGestureRecognizerStateRecognized = UIGestureRecognizerStateEnded
```

Your job is to find the **private predicates** controlling each transition.

## Step-by-Step Instructions

### Step 0: Graphify Orientation
```bash
graphify query "UIGestureRecognizerArena state machine transition"
graphify query "gesture recognizer simultaneous shouldRecognizeSimultaneously"
graphify path "UIGestureRecognizerArena" "_UIGestureEnvironment"
```

### Step 1: Decompile Arena State Machine Core

Open UIKitCore. Search for the arbitration entry points:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "arena" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "arbitrat" } }
```
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "shouldBegin" } }
```

Key functions to decompile:
1. `[UIGestureRecognizerArena _recognizerShouldBegin:]` — the "can I start?" gate
2. `[UIGestureRecognizerArena _gestureRecognizer:shouldReceiveTouch:]` — touch routing
3. `[_UIGestureEnvironment _deliverEvent:toGestureRecognizers:usingBlock:]` — the event fan-out
4. `[UIGestureRecognizer _setState:]` — the raw state setter (reveals guard conditions)
5. `[UIGestureRecognizer _cancelIfActive]` — cancellation pathway

### Step 2: Map State Transitions
For each state transition, document:
- **Trigger**: what event causes it (touch began/moved/ended, timer, system interrupt)
- **Predicate**: the condition tested (slop exceeded? velocity met? duration elapsed?)
- **Side effect**: what happens to competing recognizers (fail, cancel, or allow simultaneous)

Expected state machine transitions:

```
Possible ──touchesMoved + slopExceeded──► Began      (continuous)
Possible ──touchesEnded + recognized──────► Recognized  (discrete/tap)
Possible ──slopExceeded but wrong dir──► Failed      (swipe direction mismatch)
Possible ──systemInterrupt──────────────► Cancelled
Began    ──touchesMoved──────────────────► Changed
Changed  ──touchesEnded──────────────────► Ended
Changed  ──systemInterrupt──────────────► Cancelled
Began/Changed ──requiresFailureOf(r2)──► blocked until r2 fails
```

### Step 3: Simultaneous Recognition Rules
Find the arbitration logic:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "simultaneous" } }
```
Decompile the function that calls the delegate's `shouldRecognizeSimultaneouslyWithGestureRecognizer:`. Document:
- Priority ordering (which recognizer wins by default?)
- Failure requirements (`requiresGestureRecognizerToFail:` chain)
- System gesture override (do `_UISystemGestureGate` recognizers bypass arbitration?)

### Step 4: Extract Arena Priority Table
Search for a static priority/ordering table:
```json
{ "ServerName": "rea", "ToolName": "search_procedures", "Arguments": { "query": "priority" } }
```
Also check for integer priority ivars in `UIGestureRecognizer` (may be `_priority` or `_systemPriority`).

Expected priority ordering (highest wins):
1. System gestures (Back swipe, NC, CC) — highest
2. Gesture recognizers on views with `delaysTouchesBegan`
3. App-registered recognizers on higher Z-order views
4. App-registered recognizers on lower Z-order views

### Step 5: Write Phase Artifacts

**`artifacts/gesture/gesture_arbitration_state_machine.json`**:
```json
{
  "schema_version": "1.0",
  "states": {
    "Possible": {
      "value": 0,
      "description": "Initial state. Waiting for touch sequence to match gesture pattern."
    },
    "Began": {
      "value": 1,
      "description": "Continuous gesture recognized. Sent for pan/pinch/rotate."
    },
    "Changed": { "value": 2, ... },
    "Ended": { "value": 3, ... },
    "Cancelled": { "value": 4, ... },
    "Failed": { "value": 5, ... }
  },
  "transitions": [
    {
      "from": "Possible",
      "to": "Began",
      "trigger": "touchesMoved",
      "predicate": "delta > slopTier[currentTouchCount]",
      "applies_to": ["Pan", "Pinch", "Rotation"],
      "source_function": "UIPanGestureRecognizer._beginPan",
      "source_address": "0x<addr>",
      "confidence": "[EXTRACTED]"
    },
    ...
  ],
  "arbitration_rules": {
    "default_winner": "highest_view_z_order_wins",
    "simultaneous_allowed_by_default": false,
    "failure_requirement_chain": true,
    "system_gesture_priority": "overrides_all",
    "source_function": "UIGestureRecognizerArena._recognizerShouldBegin",
    "source_address": "0x<addr>",
    "confidence": "[EXTRACTED]"
  },
  "priority_ordering": [
    { "tier": 1, "recognizers": ["_UIBackGestureRecognizer", "_UINotificationCenterGestureRecognizer", "_UIControlCenterGestureRecognizer"], "priority_value": <int> },
    { "tier": 2, "recognizers": ["UIScreenEdgePanGestureRecognizer"], "priority_value": <int> },
    { "tier": 3, "recognizers": ["App recognizers"], "priority_value": <int> }
  ]
}
```

**`findings/gesture/03_ARBITRATION_STATE_MACHINE.md`** — Must be ≥ 5,000 bytes, contain:
- Full state diagram in Mermaid:
  ```mermaid
  stateDiagram-v2
    [*] --> Possible
    Possible --> Began : touchesMoved + slopExceeded (continuous)
    Possible --> Recognized : touchesEnded (discrete)
    ...
  ```
- Transition predicate table with binary evidence
- Simultaneous recognition decision flowchart
- Priority tier table with addresses
- Decompiled pseudocode for `_setState:` and `_deliverEvent:toGestureRecognizers:`

### Step 6: Verify & Complete
```bash
python3 tools/verify_phase.py gest_phase_3_arbitration_state_machine
```

## Required Output Artifacts
- `artifacts/gesture/gesture_arbitration_state_machine.json`
- `findings/gesture/03_ARBITRATION_STATE_MACHINE.md` (≥ 5,000 bytes)

## Confidence Gate
Do not proceed to Phase 4 unless:
- All 6 state machine states are documented
- At least 5 state transitions have binary-evidence predicates
- The simultaneous-recognition arbitration function is decompiled
