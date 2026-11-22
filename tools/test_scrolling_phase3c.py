#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 3C: Rubber-Banding, Boundary Resistance & Bounce
Tests:
- Rubber-band non-linear rational forward formula and exact analytical inverse
- IEEE 754 precision unpack for resistance coefficient (c = 0.55)
- Boundary geometry accessor calculations (minOffset, maxOffset, adjustedContentInset)
- Kinetic collision detection, fractional timestep calculation, and spring handoff
- Second-order harmonic oscillator spring ODE parameters (m=1.0, k=100.0, c=18.0, zeta=0.90)
- Edge-case policy flags and degenerate content size bounds collapse
- C pseudocode compilation and native verification test harness execution
- Findings dossier anti-placeholder compliance and structure
- Evidence ledger Phase 3C cross-validation integrity
"""

import unittest
import json
import re
import struct
import math
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BANNED_PLACEHOLDER_PATTERNS = [
    r"TODO",
    r"TBD",
    r"FIXME",
    r"PLACEHOLDER",
    r"<insert\b",
    r"<add\b",
    r"not yet implemented",
    r"to be determined",
    r"left as an exercise",
    r"\bxxx\b",
    r"\byyy\b",
    r"\bzzz\b",
    r"\.{4,}",
    r"…",
    r"\bLorem ipsum\b",
    r"as seen in.*example",
    r"unknown_address",
    r"0x00000000\b",
    r"\[TBD\]"
]

class TestScrollingPhase3CAdversarial(unittest.TestCase):

    def setUp(self):
        self.rubber_formula_json = PROJECT_ROOT / "artifacts/scrolling/rubber_band_formula.json"
        self.bounce_params_json = PROJECT_ROOT / "artifacts/scrolling/bounce_parameters.json"
        self.pseudocode_file = PROJECT_ROOT / "artifacts/scrolling/pseudocode/rubberBand_offset.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/03C_RUBBER_BANDING_BOUNCE.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.shared_cache_slice = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.01"

    def test_rubber_band_formula_schema_and_values(self):
        """R1: Test rubber-band rational formula, IEEE 754 0.55 constant, and dimension d."""
        self.assertTrue(self.rubber_formula_json.is_file(), "rubber_band_formula.json must exist")
        with open(self.rubber_formula_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Forward and Inverse formulas
        math_model = data.get("mathematical_model", {})
        fwd = math_model.get("forward_equation", {})
        self.assertIn("x_rubber", fwd.get("formula", ""))
        self.assertIn("formula_latex", fwd)

        inv = math_model.get("inverse_equation", {})
        self.assertIn("formula_latex", inv)
        self.assertIn("c * (d -", inv.get("formula", ""))

        # 2. Coefficients: c = 0.55
        coeff = data.get("coefficients", {}).get("primary_drag_resistance_c", {})
        self.assertEqual(coeff.get("value_decimal"), 0.55)
        self.assertEqual(coeff.get("ieee754_double_hex"), "0x3fe199999999999a")
        self.assertEqual(coeff.get("constant_vm_address"), "0x1865166d0")

        # Unpack IEEE 754 double
        raw_bytes = bytes.fromhex(coeff["ieee754_double_hex"][2:])
        unpacked_val = struct.unpack(">d", raw_bytes)[0]
        self.assertAlmostEqual(unpacked_val, 0.55, places=9)

        # 3. Dimension d definition
        dim = data.get("dimension_parameter_d", {})
        self.assertIn("bounds.size", dim.get("physical_definition", ""))
        self.assertIn("bounds.size.width", dim.get("horizontal_axis", {}).get("dimension_source", ""))
        self.assertIn("bounds.size.height", dim.get("vertical_axis", {}).get("dimension_source", ""))

    def test_rubber_band_forward_and_inverse_numerical_precision(self):
        """R1: Test forward rational curve and inverse roundtrip accuracy across displacements."""
        d = 852.0 # iPhone 18 visible height
        c = 0.55

        def forward(x):
            abs_x = abs(x)
            r = (1.0 - 1.0 / ((abs_x * c / d) + 1.0)) * d
            return -r if x < 0 else r

        def inverse(y):
            abs_y = abs(y)
            self.assertLess(abs_y, d, "Visual overscroll cannot exceed viewport dimension d")
            unconstrained = (abs_y * d) / (c * (d - abs_y))
            return -unconstrained if y < 0 else unconstrained

        # Test varying positive and negative displacements
        test_inputs = [0.1, 1.0, 5.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 5000.0]
        for x in test_inputs:
            for sign in [1.0, -1.0]:
                x_val = x * sign
                y_val = forward(x_val)
                # Ensure strictly monotonic and bounded by d
                self.assertLess(abs(y_val), d)
                # Ensure exact inverse reconstruction
                x_rec = inverse(y_val)
                self.assertAlmostEqual(x_val, x_rec, places=7)

        # Test initial tangency slope at zero: dy/dx = c = 0.55
        eps = 1e-6
        dy_dx = (forward(eps) - forward(0.0)) / eps
        self.assertAlmostEqual(dy_dx, c, places=5)

    def test_bounce_parameters_schema_and_spring_ode(self):
        """R4: Test harmonic oscillator spring ODE parameters and underdamped regime."""
        self.assertTrue(self.bounce_params_json.is_file(), "bounce_parameters.json must exist")
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        spring_params = data.get("bounce_back_spring_parameters", {}).get("parameters", {})
        self.assertEqual(spring_params.get("mass_m", {}).get("value"), 1.0)
        self.assertEqual(spring_params.get("stiffness_k", {}).get("default_value"), 100.0)
        self.assertEqual(spring_params.get("damping_c", {}).get("value"), 18.0)
        self.assertEqual(spring_params.get("damping_ratio_zeta", {}).get("value"), 0.90)
        self.assertEqual(spring_params.get("undamped_natural_frequency_omega_n", {}).get("value_rad_per_sec"), 10.0)

        # Verify damped angular frequency omega_d = omega_n * sqrt(1 - zeta^2)
        expected_omega_d = 10.0 * math.sqrt(1.0 - 0.90**2) # 4.358898943540674
        actual_omega_d = spring_params.get("damped_angular_frequency_omega_d", {}).get("value_rad_per_sec")
        self.assertAlmostEqual(actual_omega_d, expected_omega_d, places=7)

        # Settling thresholds
        settle = data.get("bounce_back_spring_parameters", {}).get("settling_and_rest_conditions", {})
        self.assertEqual(settle.get("displacement_epsilon_pt"), 0.5)
        self.assertEqual(settle.get("velocity_epsilon_pt_per_sec"), 0.5)

    def test_boundary_geometry_calculation_and_insets(self):
        """R2: Test minimum/maximum content offset formulas and adjustedContentInset."""
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        geom = data.get("boundary_geometry_calculation", {})
        routines = geom.get("routines", {})
        self.assertIn("minimum_content_offset", routines)
        self.assertIn("maximum_content_offset", routines)
        self.assertIn("clamped_content_offset", routines)

        min_f = routines["minimum_content_offset"]["formula"]
        self.assertEqual(min_f["x"], "-adjustedContentInset.left")
        self.assertEqual(min_f["y"], "-adjustedContentInset.top")

        # R2: Test adjusted_content_offset_if_necessary
        self.assertIn("adjusted_content_offset_if_necessary", routines)
        adj_routine = routines["adjusted_content_offset_if_necessary"]
        self.assertEqual(adj_routine.get("virtual_address"), "0x1848b7fc0")
        self.assertIn("tracking_or_decelerating", adj_routine.get("formula", {}))
        self.assertIn("idle_state", adj_routine.get("formula", {}))

        # Test adjustment behaviors
        modes = geom.get("adjusted_content_inset_rules", {}).get("adjustment_behavior_modes", {})
        self.assertIn("UIScrollViewContentInsetAdjustmentAutomatic", modes)
        self.assertIn("UIScrollViewContentInsetAdjustmentScrollableAxes", modes)
        self.assertIn("UIScrollViewContentInsetAdjustmentNever", modes)
        self.assertIn("UIScrollViewContentInsetAdjustmentAlways", modes)

    def test_edge_case_and_policy_flags_gating(self):
        """R5: Test policy flags (bounces, alwaysBounce) and contentSize < bounds.size."""
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        flags = data.get("policy_flags_and_edge_cases", {}).get("flags", {})
        self.assertIn("bounces", flags)
        self.assertIn("alwaysBounceVertical", flags)
        self.assertIn("alwaysBounceHorizontal", flags)
        self.assertIn("bouncesZoom", flags)

        # Verify bouncesZoom formula
        bz = flags.get("bouncesZoom", {})
        self.assertEqual(bz.get("damping_coefficient_c_zoom"), 0.25)
        self.assertIn("below_min_formula", bz)
        self.assertIn("above_max_formula", bz)

        edge_cases = data.get("policy_flags_and_edge_cases", {}).get("edge_cases", {})
        self.assertIn("content_smaller_than_viewport", edge_cases)
        self.assertIn("zero_content_size", edge_cases)
        self.assertIn("pull_to_refresh_pinning", edge_cases)

    def test_inverse_rubber_band_asymptotic_singularity_and_edge_cases(self):
        """R1: Adversarial edge cases: y >= d, y = d, d <= 0, c <= 0, x = 0."""
        d = 852.0
        c = 0.55

        def safe_inverse(y, dimension=d, coefficient=c):
            if abs(y) < 1e-9:
                return 0.0
            dim = dimension if dimension > 1.0 else 1.0
            coeff = coefficient if coefficient > 0.0 else 0.55
            abs_y = abs(y)
            if abs_y >= dim * 0.9999:
                abs_y = dim * 0.9999
            unconstrained = (abs_y * dim) / (coeff * (dim - abs_y))
            return -unconstrained if y < 0 else unconstrained

        # 1. Zero and negative zero
        self.assertEqual(safe_inverse(0.0), 0.0)
        self.assertEqual(safe_inverse(-0.0), 0.0)

        # 2. Asymptotic boundary: y = d and y > d
        res_at_d = safe_inverse(d)
        self.assertTrue(math.isfinite(res_at_d) and res_at_d > 0.0)
        res_past_d = safe_inverse(d * 2.0)
        self.assertTrue(math.isfinite(res_past_d) and res_past_d > 0.0)
        res_neg_d = safe_inverse(-d)
        self.assertTrue(math.isfinite(res_neg_d) and res_neg_d < 0.0)

        # 3. Degenerate dimension (d <= 0) and coefficient (c <= 0)
        res_deg = safe_inverse(10.0, dimension=0.0, coefficient=0.0)
        self.assertTrue(math.isfinite(res_deg) and res_deg > 0.0)

    def test_zoom_rubber_band_scaling_adversarial(self):
        """R5: Test logarithmic zoom rubber-band damping under bounds breach."""
        min_scale = 1.0
        max_scale = 4.0
        c_zoom = 0.25

        def zoom_rubber_band(scale, bounces_zoom=True):
            if scale < min_scale:
                if not bounces_zoom:
                    return min_scale
                delta = (min_scale - scale) / min_scale
                return min_scale - math.log(1.0 + delta) * c_zoom * min_scale
            elif scale > max_scale:
                if not bounces_zoom:
                    return max_scale
                delta = (scale - max_scale) / max_scale
                return max_scale + math.log(1.0 + delta) * c_zoom * max_scale
            else:
                return scale

        # Inside bounds: 1:1 identity
        self.assertEqual(zoom_rubber_band(2.5, True), 2.5)

        # Below minimum scale with bouncesZoom: damped compression
        damped_min = zoom_rubber_band(0.5, bounces_zoom=True)
        self.assertLess(damped_min, 1.0)
        self.assertGreater(damped_min, 0.5)

        # Below minimum scale without bouncesZoom: hard clamp
        self.assertEqual(zoom_rubber_band(0.5, bounces_zoom=False), 1.0)

        # Above maximum scale with bouncesZoom: damped expansion
        damped_max = zoom_rubber_band(6.0, bounces_zoom=True)
        self.assertGreater(damped_max, 4.0)
        self.assertLess(damped_max, 6.0)

        # Above maximum scale without bouncesZoom: hard clamp
        self.assertEqual(zoom_rubber_band(6.0, bounces_zoom=False), 4.0)

    def test_touch_release_overscroll_spring_handoff(self):
        """R4: Test touch-up overscroll restitution parameters in bounce_parameters.json."""
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        transitions = data.get("ballistic_vs_drag_transitions", {})
        self.assertIn("touch_release_overscroll_restitution", transitions)
        touch_up = transitions["touch_release_overscroll_restitution"]
        self.assertIn("initial_displacement_x0", touch_up.get("initial_conditions", {}))
        self.assertIn("initial_velocity_v0", touch_up.get("initial_conditions", {}))
        self.assertIn("axis_specific_policy_gating", touch_up)

    def test_pull_to_refresh_dynamic_spring_parameters(self):
        """R4: Verify pull-to-refresh stiffness, damping, and elevated natural frequency ODE."""
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        params = data.get("bounce_back_spring_parameters", {}).get("parameters", {})
        k_pull = params.get("stiffness_k", {}).get("pull_to_refresh_value")
        self.assertEqual(k_pull, 180.0)

        c_pull = params.get("damping_c", {}).get("pull_to_refresh_value")
        self.assertAlmostEqual(c_pull, 24.14953415699773, places=6)

        omega_n_pull = params.get("undamped_natural_frequency_omega_n", {}).get("pull_to_refresh_value_rad_per_sec")
        self.assertAlmostEqual(omega_n_pull, math.sqrt(180.0), places=6)

        omega_d_pull = params.get("damped_angular_frequency_omega_d", {}).get("pull_to_refresh_value_rad_per_sec")
        expected_omega_d_pull = math.sqrt(180.0) * math.sqrt(1.0 - 0.90**2)
        self.assertAlmostEqual(omega_d_pull, expected_omega_d_pull, places=6)

        # Verify damping ratio is preserved at 0.90
        zeta_pull = c_pull / (2.0 * math.sqrt(k_pull * 1.0))
        self.assertAlmostEqual(zeta_pull, 0.90, places=6)

    def test_spring_animation_lifecycle_routine_schema(self):
        """R3/R6: Verify updatePosition:timestamp: lifecycle routine specification."""
        with open(self.bounce_params_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        spring_block = data.get("bounce_back_spring_parameters", {})
        self.assertIn("lifecycle_routine", spring_block)
        routine = spring_block["lifecycle_routine"]
        self.assertEqual(routine.get("virtual_address"), "0x1848c8100")
        self.assertIn("updatePosition:timestamp:", routine.get("method", ""))

    def test_zoom_rubber_band_negative_and_nan_adversarial(self):
        """R5: Adversarial zoom rubber-banding: s <= 0, s -> -inf, NaN, min == max."""
        min_scale = 1.0
        max_scale = 4.0
        c_zoom = 0.25

        def safe_zoom_rubber_band(scale, min_s=min_scale, max_s=max_scale, bounces_zoom=True):
            if math.isnan(scale) or math.isinf(scale):
                return min_s
            actual_min = min_s if min_s > 0.0 else 1.0
            actual_max = max_s if max_s >= actual_min else actual_min
            if scale < actual_min:
                if not bounces_zoom:
                    return actual_min
                clamped_scale = 0.0 if scale < 0.0 else scale
                delta = (actual_min - clamped_scale) / actual_min
                damped = math.log(1.0 + delta) * c_zoom * actual_min
                result = actual_min - damped
                min_allowed = actual_min * (1.0 - math.log(2.0) * c_zoom)
                return min_allowed if result < min_allowed else result
            elif scale > actual_max:
                if not bounces_zoom:
                    return actual_max
                delta = (scale - actual_max) / actual_max
                damped = math.log(1.0 + delta) * c_zoom * actual_max
                return actual_max + damped
            else:
                return scale

        # Degenerate negative zoom scale: MUST NEVER be negative or zero
        res_neg = safe_zoom_rubber_band(-100.0)
        self.assertGreater(res_neg, 0.0)
        self.assertGreaterEqual(res_neg, 1.0 * (1.0 - math.log(2.0) * 0.25))

        res_zero = safe_zoom_rubber_band(0.0)
        self.assertGreater(res_zero, 0.0)

        # Non-finite inputs
        res_nan = safe_zoom_rubber_band(float("nan"))
        self.assertEqual(res_nan, 1.0)
        res_inf = safe_zoom_rubber_band(float("inf"))
        self.assertEqual(res_inf, 1.0)

        # Inverted zoom bounds (maxScale < minScale)
        res_inv = safe_zoom_rubber_band(5.0, min_s=3.0, max_s=1.0)
        self.assertGreater(res_inv, 3.0)


    def test_c_pseudocode_compilation_and_native_execution(self):
        """R6: Compile and execute C pseudocode verification test harness."""
        self.assertTrue(self.pseudocode_file.is_file(), "rubberBand_offset.pseudo.c must exist")
        test_bin = PROJECT_ROOT / "tools" / "test_rubber_band_runner"
        try:
            comp = subprocess.run(
                ["clang", "-DRUBBER_BAND_VERIFICATION_TESTS", "-O2", str(self.pseudocode_file), "-o", str(test_bin), "-lm"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertEqual(comp.returncode, 0, f"Clang compile failed:\n{comp.stderr}")
            run_res = subprocess.run([str(test_bin)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(run_res.returncode, 0, f"Test runner execution failed:\n{run_res.stderr}")
            self.assertIn("ALL PHASE 3C MATHEMATICAL ASSERTIONS PASSED", run_res.stdout)
        finally:
            if test_bin.exists():
                test_bin.unlink()

    def test_findings_dossier_structure_and_anti_placeholder(self):
        """R6: Verify findings document size >= 2500 bytes and zero placeholders."""
        self.assertTrue(self.findings_md.is_file(), "03C_RUBBER_BANDING_BOUNCE.md must exist")
        content = self.findings_md.read_text(encoding="utf-8")
        self.assertGreaterEqual(len(content.encode("utf-8")), 2500)

        for pat in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pat, content, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Banned placeholder '{pat}' found in findings document")

        # Required markers
        required_markers = [
            "0.55", "0x1865166d0", "0x184ae00c0", "0x1848b7f40", "0x1848b7f60",
            "adjustedContentInset", "alwaysBounceVertical", "alwaysBounceHorizontal"
        ]
        for m in required_markers:
            self.assertIn(m, content, f"Missing required marker '{m}' in findings document")

        # Check for Mermaid diagrams and tables
        self.assertIn("```mermaid", content)
        self.assertIn("sequenceDiagram", content)
        self.assertIn("|", content)

    def test_evidence_ledger_phase3c_integrity(self):
        """R6: Verify Phase 3C entries in evidence_ledger.jsonl."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        phase3c_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_3C":
                    phase3c_entries.append(entry)

        self.assertGreaterEqual(len(phase3c_entries), 10, "Must contain >= 10 Phase 3C confirmed entries")
        for e in phase3c_entries:
            self.assertTrue(e["id"].startswith("BOUNCE-"))
            self.assertEqual(e["confidence"], "CONFIRMED")
            self.assertTrue(e["binary_path"].endswith("dyld_shared_cache_arm64e.01"))
            self.assertTrue((PROJECT_ROOT / e["binary_path"]).is_file())
            self.assertTrue(e["address"].startswith("0x18"))

    def test_scroll_progress_phase3c_completion(self):
        """R6: Verify scroll_progress.json marks phase_3c completed and unlocks 3d."""
        with open(self.progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        phase3c = data.get("phases", {}).get("phase_3c_rubber_band", {})
        self.assertEqual(phase3c.get("status"), "completed")
        self.assertTrue(phase3c.get("entry_criteria_met"))
        self.assertEqual(phase3c.get("verified_by"), "tools/verify_phase.py phase_3c_rubber_band")

        phase3d = data.get("phases", {}).get("phase_3d_snapping", {})
        self.assertTrue(phase3d.get("entry_criteria_met"), "Phase 3D must be unlocked")

    def test_rubber_band_without_decoration_behavior(self):
        """R1: Test _rubberBandOffsetWithoutDecorationForOffset calculation without in-bounds offset."""
        d = 852.0
        c = 0.55
        min_offset = -79.0
        max_offset = 1200.0

        def rubber_band_without_decoration(offset, min_b, max_b, range_d, bounces=True):
            if offset < min_b:
                if not bounces:
                    return min_b
                delta = offset - min_b
                rubber = (1.0 - 1.0 / ((abs(delta) * c / range_d) + 1.0)) * range_d * (-1.0 if delta < 0 else 1.0)
                return min_b + rubber
            elif offset > max_b:
                if not bounces:
                    return max_b
                delta = offset - max_b
                rubber = (1.0 - 1.0 / ((abs(delta) * c / range_d) + 1.0)) * range_d * (-1.0 if delta < 0 else 1.0)
                return max_b + rubber
            else:
                return offset

        # Inside bounds: identical
        self.assertEqual(rubber_band_without_decoration(100.0, min_offset, max_offset, d), 100.0)

        # Outside min bound: damped offset past min
        res_min = rubber_band_without_decoration(-179.0, min_offset, max_offset, d)
        self.assertLess(res_min, min_offset)
        self.assertGreater(res_min, -179.0)

        # Bounces disabled: pinned
        self.assertEqual(rubber_band_without_decoration(-179.0, min_offset, max_offset, d, bounces=False), min_offset)

    def test_boundary_collision_detection_jitter_resilience(self):
        """R3: Test boundary collision detection when currentOffset is bordering or beyond boundary."""
        min_offset = 0.0
        dt = 0.016
        decel_rate = 0.998

        def detect_collision(cur_off, next_off, cur_vel):
            breached_x = False
            residual_vx = 0.0
            if next_off < min_offset and (cur_vel < 0.0 or cur_off >= min_offset):
                breached_x = True
                denom = next_off - cur_off
                fraction = (min_offset - cur_off) / denom if abs(denom) > 1e-9 else 0.0
                fraction = max(0.0, min(1.0, fraction))
                residual_vx = cur_vel * math.pow(decel_rate, 1000.0 * fraction * dt)
            return breached_x, residual_vx

        # Normal crossing: 10.0 -> -15.0
        b_norm, v_norm = detect_collision(10.0, -15.0, -200.0)
        self.assertTrue(b_norm)
        self.assertLess(v_norm, 0.0)

        # Bordering jitter: -1e-11 -> -5.0 with negative velocity
        b_jitter, v_jitter = detect_collision(-1e-11, -5.0, -200.0)
        self.assertTrue(b_jitter, "Must detect outward boundary breach even when cur_off <= min_offset")
        self.assertEqual(v_jitter, -200.0, "Fraction must clamp to 0.0 preserving full impact velocity")

    def test_pull_to_refresh_can_bounce_vertical_override(self):
        """R5: Test that active pull-to-refresh overrides non-scrollable vertical content bounds."""
        def can_bounce_vertical(bounces, always_bounce, content_h, bounds_h, insets_v, refresh_active):
            if bounds_h <= 0.0 or not bounces:
                return False
            if always_bounce or refresh_active:
                return True
            return (content_h + insets_v) > bounds_h

        # Small content, alwaysBounce=0, refresh=False -> cannot bounce
        self.assertFalse(can_bounce_vertical(True, False, 500.0, 852.0, 153.0, False))

        # Small content, alwaysBounce=0, refresh=True -> MUST bounce!
        self.assertTrue(can_bounce_vertical(True, False, 500.0, 852.0, 153.0, True))

        # Master bounces=False -> cannot bounce even with refresh
        self.assertFalse(can_bounce_vertical(False, False, 500.0, 852.0, 153.0, True))

    def test_zero_bounds_and_null_pointer_safety(self):
        """R5: Test zero-bounds viewport geometry collapse and negative dimension safety."""
        def compute_max_offset(content_w, bounds_w, insets_left, insets_right):
            min_x = -insets_left
            if bounds_w <= 0.0:
                return min_x
            eff_w = content_w + insets_right - bounds_w
            return max(min_x, eff_w)

        # Normal view
        self.assertEqual(compute_max_offset(1000.0, 400.0, 0.0, 0.0), 600.0)

        # Zero-bounds view: collapses to min_x
        self.assertEqual(compute_max_offset(1000.0, 0.0, 20.0, 20.0), -20.0)
        self.assertEqual(compute_max_offset(0.0, -10.0, 0.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
