# Agent Prompt: Phase 1B — Animation Symbol Discovery

## Mission
Build a comprehensive symbol inventory of all animation-physics-relevant classes, methods, and global variables across all 6 target frameworks. This is reconnaissance — do not decompile yet. Catalog everything first.

**Skills to use**: `rea`, `graphify`, `investigate-codebase`

## Pre-Execution
```bash
graphify query "CASpringAnimation properties stiffness damping"
graphify query "UISpringTimingParameters animation"
graphify query "perceptual duration bounce QuartzCore"
```

## Step 1: Class Hierarchy Enumeration

For each framework, run `get_objc_classes` and filter for animation-relevant classes. Priority prefixes:

| Prefix | Framework | Significance |
|--------|-----------|-------------|
| `CASpringAnimation` | QuartzCore | The core spring primitive |
| `UISpringTimingParameters` | UIKitCore | UIKit spring config |
| `UIViewPropertyAnimator` | UIKitCore | Animation driver |
| `_UITimingFunction*` | UIKitCore | Timing curve internals |
| `AK*` | AnimationKit | Private animation kit classes |
| `SUIAK*` / `SUIA*` | SystemUIAnimationKit | System UI animation classes |
| `SBAnimation*` / `SBSpring*` | SpringBoard | Homescreen/SpringBoard animations |

Also run `analyze_swift_types` on `AnimationKit` and `SystemUIAnimationKit` — they may be primarily Swift.
Run `demangle_swift` on any mangled symbols found.

## Step 2: Global Variable Discovery

For each framework, search for float/double global variables with animation-physics names:

```json
{
  "ServerName": "rea",
  "ToolName": "search_procedures",
  "Arguments": {
    "query": "spring stiffness damping bounce perceptual"
  }
}
```

Also scan strings: `list_strings` and filter for:
- `spring`, `damp`, `stiff`, `mass`, `bounce`, `perceptual`, `duration`, `timing`, `curve`
- Numeric strings: `0.998`, `0.990`, `100`, `18.0`
- Error/debug strings mentioning animation physics

## Step 3: Cross-Framework Call Graph Sketch

For each major class found, run `procedure_callers` on its `init` and primary configuration methods to determine:
- Does `AnimationKit` call into `QuartzCore.CASpringAnimation`?
- Does `SystemUIAnimationKit` call into `AnimationKit`?
- Does `SpringBoard` call `SystemUIAnimationKit`?

This maps the call chain: `SpringBoard → SystemUIAnimationKit → AnimationKit → CASpringAnimation → QuartzCore`

## Required Deliverables

### `artifacts/animation/symbol_inventory.json`
```json
{
  "UIKitCore": {
    "objc_classes": ["UISpringTimingParameters", "_UITimingFunctionSpring", ...],
    "swift_types": [...],
    "animation_globals": [
      { "name": "_UIScrollViewSpringMass", "address": "0x1848c8110", "confirmed_value": 1.0 }
    ],
    "spring_methods": [
      { "class": "UISpringTimingParameters", "method": "initWithMass:stiffness:damping:initialVelocity:", "address": "0x..." }
    ]
  },
  "QuartzCore": { ... },
  "AnimationKit": {
    "primary_spring_class": "AK<ClassName>",
    "call_targets_quartzcore": true
  },
  "SystemUIAnimationKit": { ... },
  "SpringBoard": { ... },
  "SwiftUI": { ... }
}
```

### `artifacts/animation/call_chain_map.json`
Document the call chain from SpringBoard down to CASpringAnimation.

## Completion Gate
`python3 tools/verify_phase.py anim_phase_1b_symbol_discovery`

Verification checks:
- `symbol_inventory.json` exists, is valid JSON, has all 6 frameworks populated
- At least 5 animation-physics classes discovered per framework
- `call_chain_map.json` has at least 3 edges in the SpringBoard → QuartzCore chain
