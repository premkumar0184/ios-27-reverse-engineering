# Agent Prompt: Phase 4 — Modern perceptual duration/bounce API Verification

## Mission
Decompile and verify the exact binary implementation of the iOS 17+ `perceptualDuration + bounce` API in `QuartzCore`. Confirm the conversion formulas exactly, extract any deviation from the theoretical model, and document the full initializer chain.

**Skills to use**: `rea`, `graphify`, `ponytail` (clean pseudocode)

## Background (Known from Web Research, Needs Binary Confirmation)

Theoretical model (needs binary verification):
- $k = (2\pi/d)^2$, $m = 1.0$
- For $b \ge 0$: $\zeta = 1 - b$
- For $b < 0$: $\zeta = 1/(1+b)$
- $c = 2m\omega_n\zeta = 4\pi(\zeta/d)$

**Critical questions for binary verification:**
1. Is $k = (2\pi/d)^2$ the exact formula, or does Apple use a modified natural frequency?
2. What is the epsilon threshold for `settlingDuration`?
3. Is there a `clamp` on the bounce parameter (e.g., $b \in [-1, 1]$)?
4. Does `allowsOverdamping: false` change the bounce→ζ formula?

## Step 1: Full Decompile of -[CASpringAnimation initWithPerceptualDuration:bounce:]

This is the entry point. Decompile completely via REA first, then cross-validate with Ghidra.

Look for:
- The constant `2π` or `6.2831...` in floating point
- Division, squaring operations on `d`
- Branching on sign of `b`
- Clamp operations (fmin/fmax)
- Calls to `setStiffness:` / `setDamping:` with derived values

Produce `pseudocode/CASpringAnimation_perceptual_init.pseudo.c`.

## Step 2: Decompile settlingDuration Getter

The `settlingDuration` property computes how long the spring takes to settle within `epsilon` of the target. Find the epsilon value — this tells you when Apple considers an animation "done".

Decompile `-[CASpringAnimation settlingDuration]` and extract:
- The epsilon threshold (likely `0.001` or `1e-4`)
- The logarithm formula used (expected: $t_{settle} \approx -\ln(\epsilon) / (\zeta \omega_n)$)

## Step 3: SwiftUI Spring.Animation Passthrough

Decompile the SwiftUI `Animation.spring(duration:bounce:)` factory and trace how it converts to `CASpringAnimation`. Does it call `-[CASpringAnimation initWithPerceptualDuration:bounce:]` directly, or does it go through `AnimationKit` first?

## Step 4: Cross-Framework Chain Verification

Confirm the full chain for a SwiftUI `.spring()` animation:
```
SwiftUI.Animation.spring(duration:bounce:)
  → AnimationKit.AK<SpringDriver>.init(duration:bounce:)   [if AnimationKit is in the chain]
  → QuartzCore.CASpringAnimation.initWithPerceptualDuration:bounce:
  → CASpringAnimation.setStiffness: / setDamping: / setMass:
```

## Required Deliverables

### `artifacts/animation/modern_api_verification.json`
```json
{
  "perceptual_api_confirmed": true,
  "stiffness_formula": "k = pow(2 * M_PI / d, 2)",
  "stiffness_formula_exact": true,
  "bounce_to_zeta_underdamped": "zeta = 1.0 - b",
  "bounce_to_zeta_overdamped": "zeta = 1.0 / (1.0 + b)",
  "bounce_clamp_min": -1.0,
  "bounce_clamp_max": 1.0,
  "settling_epsilon": 0.001,
  "settling_formula": "t = -log(epsilon) / (zeta * omega_n)",
  "swiftui_passthrough_chain": ["SwiftUI.spring", "AnimationKit.AKSpring", "CASpringAnimation"],
  "source_functions": {
    "perceptual_init": "-[CASpringAnimation initWithPerceptualDuration:bounce:]",
    "settling_duration": "-[CASpringAnimation settlingDuration]"
  },
  "source_addresses": {
    "perceptual_init": "0x...",
    "settling_duration": "0x..."
  },
  "confidence": "EXTRACTED"
}
```

### `artifacts/animation/pseudocode/CASpringAnimation_perceptual_init.pseudo.c`
Clean-room C pseudocode of the full initializer.

### `artifacts/animation/pseudocode/CASpringAnimation_settlingDuration.pseudo.c`
Clean-room pseudocode of the settling duration getter.

### `findings/animation/04_MODERN_API.md`
Full write-up: initializer chain, formula verification, deviations from theoretical model.

## Completion Gate
`python3 tools/verify_phase.py anim_phase_4_modern_api`

Verification checks:
- `modern_api_verification.json` valid, `perceptual_api_confirmed` is `true`
- Both pseudocode files exist and are non-empty
- `findings/animation/04_MODERN_API.md` ≥ 3000 bytes, no placeholders
