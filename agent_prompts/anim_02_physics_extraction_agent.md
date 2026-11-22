# Agent Prompt: Phase 2 — Physics Constants Extraction

## Mission
Extract every spring physics constant (k, m, c, ζ, perceptual duration, bounce) from all 6 target binaries. Apply the 3-level confidence escalation protocol. Produce the authoritative `animation_physics_reference.json`.

**Skills to use**: `rea`, `graphify`, `ponytail` (for clean pseudocode)

## Pre-Execution
```bash
graphify query "spring constants animation per context"
# Review Phase 1B artifacts before starting
cat artifacts/animation/symbol_inventory.json | python3 -m json.tool | grep -A3 "spring_methods"
```

## Background: Known Physics Model

iOS 27 uses the standard second-order damped harmonic oscillator:
$$m \cdot s''(t) + c \cdot s'(t) + k \cdot s(t) = 0$$

**Modern API** (iOS 17+, confirmed from web research):
- `perceptualDuration` ($d$): $k = (2\pi/d)^2$, $m = 1.0$
- `bounce` ($b$): $\zeta = 1 - b$ (for $b \ge 0$); $\zeta = 1/(1+b)$ (for $b < 0$)
- Damping: $c = 4\pi(\zeta/d)$

**Goal**: Extract the actual $d$ and $b$ values Apple hardcodes per animation context.

## Step 1: Decompile CASpringAnimation Initializers

Target: `QuartzCore.CASpringAnimation`

Decompile:
- `-[CASpringAnimation initWithPerceptualDuration:bounce:]`
- `-[CASpringAnimation setStiffness:]`
- `-[CASpringAnimation setDamping:]`
- `-[CASpringAnimation settlingDuration]` (getter — reveals epsilon threshold)

Extract from pseudocode:
- The epsilon/threshold value for `settlingDuration` calculation
- Any hardcoded defaults for mass, stiffness, damping in the initializer
- The exact formula used for perceptualDuration → stiffness conversion

Cross-validate with Ghidra:
```json
{
  "ServerName": "ghidra",
  "ToolName": "search_functions_by_name",
  "Arguments": { "name": "perceptualDuration" }
}
```

## Step 2: Decompile AnimationKit Spring Driver

From Phase 1B's `primary_spring_class` in `AnimationKit`:
- Decompile the initializer
- Find where it creates or configures a `CASpringAnimation`
- Extract any hardcoded parameters it passes

## Step 3: SystemUIAnimationKit Context Tables

This is the highest-value target. `SystemUIAnimationKit` likely contains a table or factory method that maps animation *context* (e.g., "modal sheet present", "action sheet", "notification banner") to specific $(d, b)$ or $(k, m, c)$ parameters.

Strategy:
1. `list_strings` on SystemUIAnimationKit — look for context name strings: `sheet`, `modal`, `alert`, `banner`, `island`, `control center`, `notification`
2. For each string found, trace `xrefs` to find the method that uses it
3. Decompile that method to extract the parameter values passed alongside the string
4. Record each context → parameters mapping

## Step 4: SpringBoard.framework Animation Configs

Search SpringBoard for:
- `SBFluidSwitcherViewController` animation parameters (app switcher)
- Icon jiggle animation (look for rotation amplitude, frequency)
- Homescreen page-turn parameters
- Dynamic Island morph spring

## Step 5: UIKit Context-Specific Parameters

In UIKitCore, search for:
- `UIViewPropertyAnimator` configured spring parameters per context
- `_UIViewAnimationCoordinatorGroup` spring configs
- Transition coordinator animation parameters
- Interactive dismiss gesture spring configs

## Required Deliverables

### `artifacts/animation/animation_physics_reference.json`

Format (mirror `physics_constants.json` from scrolling RE):
```json
{
  "schema_version": 1,
  "target": "iOS 27.2 (24B119) animation physics engine",
  "extraction_methodology": "static binary analysis via REA + Ghidra",
  "frameworks_analyzed": ["UIKitCore", "QuartzCore", "AnimationKit", "SystemUIAnimationKit", "SpringBoard"],

  "core_spring_model": {
    "equation": "m*x'' + c*x' + k*x = 0",
    "mass_default": { "value": 1.0, "hex": "0x3ff0000000000000", "source_address": "0x...", "confidence": "EXTRACTED" },
    "settling_epsilon": { "value": 0.001, "hex": "...", "source_address": "0x...", "confidence": "EXTRACTED" }
  },

  "modern_api": {
    "perceptual_duration_to_stiffness": "k = (2π/d)²",
    "bounce_to_zeta_underdamped": "ζ = 1 - b  (b ≥ 0)",
    "bounce_to_zeta_overdamped": "ζ = 1/(1+b)  (b < 0)",
    "confirmed_from_binary": true,
    "source_function": "-[CASpringAnimation initWithPerceptualDuration:bounce:]",
    "source_address": "0x..."
  },

  "animation_contexts": {
    "modal_sheet_present": {
      "perceptual_duration": 0.0, "bounce": 0.0,
      "stiffness": 0.0, "damping": 0.0, "mass": 1.0,
      "zeta": 0.0, "settling_time_ms": 0,
      "source_function": "...", "source_address": "0x...",
      "confidence": "EXTRACTED"
    },
    "modal_sheet_dismiss": { ... },
    "action_sheet": { ... },
    "notification_banner_in": { ... },
    "notification_banner_dismiss": { ... },
    "dynamic_island_expand": { ... },
    "dynamic_island_collapse": { ... },
    "app_launch": { ... },
    "app_switcher_card": { ... },
    "icon_jiggle": { ... },
    "keyboard_appear": { ... },
    "keyboard_dismiss": { ... }
  }
}
```

### `artifacts/animation/pseudocode/`
- `CASpringAnimation_init_perceptual.pseudo.c`
- `AnimationKit_spring_driver.pseudo.c`
- `SystemUIAnimationKit_context_factory.pseudo.c`
- `SpringBoard_animation_configs.pseudo.c`

### `findings/animation/02_PHYSICS_EXTRACTION.md`
Full technical write-up: class hierarchy diagrams, decompiled pseudocode, constant tables, cross-validation, confidence labels.

## Completion Gate
`python3 tools/verify_phase.py anim_phase_2_physics_extraction`

Verification checks:
- `animation_physics_reference.json` valid, has ≥ 6 animation contexts
- `pseudocode/` has ≥ 3 `.pseudo.c` files
- `findings/animation/02_PHYSICS_EXTRACTION.md` ≥ 5000 bytes, no placeholders
- No `[UNKNOWN]` confidence remaining for `core_spring_model` section
