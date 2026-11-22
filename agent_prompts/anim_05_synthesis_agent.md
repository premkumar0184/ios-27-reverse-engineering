# Agent Prompt: Phase 5 — Cross-Validation, Clean-Room Spec & Knowledge Graph Update

## Mission
Cross-validate all extracted constants against each other and against the scrolling RE baseline. Write the publication-grade `IOS_27_ANIMATION_PHYSICS_RE.md`. Update the graphify knowledge graph. Produce the clean-room implementation specification.

**Skills to use**: `rea`, `graphify`, `agency-evidence-collector`, `ponytail` (clean spec), `agency-research-synthesist`

## Pre-Execution
```bash
# Validate all prior phase artifacts exist
python3 tools/verify_phase.py anim_phase_1a_workspace_baseline
python3 tools/verify_phase.py anim_phase_1b_symbol_discovery
python3 tools/verify_phase.py anim_phase_2_physics_extraction
python3 tools/verify_phase.py anim_phase_3_context_tables
python3 tools/verify_phase.py anim_phase_4_modern_api
```

## Step 1: Cross-Validation Matrix

Build a cross-validation matrix verifying:
1. **Scrolling anchor consistency**: The UIScrollView spring ($m=1, k=100, c=18$) must be consistent with the perceptual duration formula: $d = 2\pi/\sqrt{k/m} = 0.628s$, $\zeta = c/(2\sqrt{km}) = 0.90$. Verify this against the `modern_api_verification.json` formula.
2. **Context table internal consistency**: For each extracted context, verify $c = 2m\omega_n\zeta = 4\pi(\zeta/d)$ holds.
3. **Formula cross-check**: For every context with both $(k, m, c)$ and $(d, b)$ extracted, verify the conversion formulas produce matching values.

```python
# tools/verify_animation_constants.py (create this tool)
import json, math
from pathlib import Path

physics = json.loads(Path('artifacts/animation/animation_physics_reference.json').read_text())
modern = json.loads(Path('artifacts/animation/modern_api_verification.json').read_text())

for context_name, ctx in physics['animation_contexts'].items():
    if 'stiffness' in ctx and 'perceptual_duration' in ctx:
        d = ctx['perceptual_duration']
        k_expected = (2 * math.pi / d) ** 2
        k_actual = ctx['stiffness']
        discrepancy = abs(k_expected - k_actual) / k_expected
        assert discrepancy < 0.01, f"{context_name}: k mismatch {k_expected:.4f} vs {k_actual:.4f}"
        print(f"✓ {context_name}: k consistent")
```

## Step 2: Reference Implementation (Clean-Room Spec)

Using `ponytail` mode, write the clean-room C implementation spec. This is the most valuable deliverable — a complete, correct, platform-agnostic implementation of iOS 27 animation physics that anyone can port.

### `artifacts/animation/pseudocode/reference_animation_engine.pseudo.c`

Structure:
```c
// iOS 27 Animation Physics Engine — Clean-Room Specification
// Source: Static binary analysis of iOS 27.2 (24B119) dyld_shared_cache_arm64e
// All constants extracted at EXTRACTED confidence level

// ═══════════════════════════════════════════════════════════════
// PART 1: Spring Parameter Tables (extracted per animation context)
// ═══════════════════════════════════════════════════════════════

typedef struct {
    double perceptual_duration;  // seconds
    double bounce;               // [-1, 1]
    double stiffness;            // k (N/m), derived
    double damping;              // c (N·s/m), derived
    double mass;                 // m (kg), always 1.0
    double zeta;                 // damping ratio, derived
    double settling_time_ms;     // milliseconds
} iOS27SpringContext;

static const iOS27SpringContext kModalSheetPresent = { ... };
static const iOS27SpringContext kNotificationBannerIn = { ... };
// ... all extracted contexts

// ═══════════════════════════════════════════════════════════════
// PART 2: perceptualDuration + bounce → CASpringAnimation conversion
// (from -[CASpringAnimation initWithPerceptualDuration:bounce:])
// ═══════════════════════════════════════════════════════════════

void ios27_spring_from_perceptual(double duration, double bounce, double *k, double *c, double *m) {
    *m = 1.0;
    *k = (2.0 * M_PI / duration) * (2.0 * M_PI / duration);
    double omega_n = sqrt(*k / *m);
    double zeta = (bounce >= 0.0) ? (1.0 - bounce) : (1.0 / (1.0 + bounce));
    *c = 2.0 * (*m) * omega_n * zeta;
}
```

## Step 3: Publication-Grade Report

### `IOS_27_ANIMATION_PHYSICS_RE.md` (project root)

Follow the same structure as `IOS_27_SCROLLING_REVERSE_ENGINEERING.md`. Sections:
1. Executive Summary & Target Baseline
2. Empirical Methodology
3. Animation Framework Architecture (call chain diagram)
4. Core Spring Physics Engine
5. Modern perceptual duration/bounce API
6. Per-Context Parameter Tables
7. Non-Spring Timing Curves
8. ProMotion Frame Rate Hints per Animation
9. Cross-Validation Matrix
10. Clean-Room Implementation Specification
11. Known Gaps & Static Analysis Limitations
12. Confidence Classification Summary

Minimum length: **50,000 bytes**.

## Step 4: Knowledge Graph Update

```bash
# Update graphify with all new animation findings
graphify findings/animation/ artifacts/animation/ --update --mode deep --no-viz

# Then query to verify new nodes are present
graphify query "animation physics spring perceptual duration"
graphify query "SystemUIAnimationKit modal sheet parameters"
```

## Required Deliverables

| Artifact | Location | Min Size |
|----------|----------|----------|
| `IOS_27_ANIMATION_PHYSICS_RE.md` | project root | 50,000 bytes |
| `reference_animation_engine.pseudo.c` | `artifacts/animation/pseudocode/` | populated with all contexts |
| `cross_validation_matrix.json` | `artifacts/animation/` | all contexts validated |
| `verify_animation_constants.py` | `tools/` | runnable, all assertions pass |
| Updated `graphify-out/` | project root | new animation nodes visible |

## Completion Gate
`python3 tools/verify_phase.py anim_phase_5_synthesis`

Verification checks:
- `IOS_27_ANIMATION_PHYSICS_RE.md` ≥ 50,000 bytes, no placeholder text
- `tools/verify_animation_constants.py` runs without assertion errors
- `cross_validation_matrix.json` valid, all contexts show `validated: true`
- `graphify-out/GRAPH_REPORT.md` timestamp updated after graphify --update run
- `progress.json` animation project `overall_status` updated to `completed`
