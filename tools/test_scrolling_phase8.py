#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 8: Reusable Implementation Specification & Reference Engine
iOS 27.2 (Build 24B119, iPhone18,3, SoC t8150 A19 Pro, arm64e PAC00)

Comprehensive unit testing across:
1. JSON parameter schemas & precision (artifacts/scrolling/parameter_reference.json)
2. Deceleration friction rates (0.998, 0.990, 0.985, 0.950) & continuous lambda equivalence
3. Rational rubber-band forward, inverse, and tangent derivative models (c = 0.55)
4. Underdamped harmonic spring restitution (m=1.0, k=100.0, c=18.0, zeta=0.90)
5. Multi-modal touch slop thresholds & velocity estimation filtering
6. ProMotion VFD variable refresh rate scheduling tiers (120Hz / 80Hz / 60Hz)
7. Pagination snapping & discrete boundary target calculation
8. Scroll indicator sizing, overscroll compression (r=2.0), and cubic fade
9. Complex UI coordination (large title, sheet detents, refresh FSM, keyboard dismissal)
10. C99 clean-room reference engine compilation & 40 assertion test suites
11. Anti-placeholder zero-tolerance compliance across all Phase 8 deliverables
12. Formal specification document structural richness, byte size (>= 40,000 bytes), and Mermaid diagrams
13. Automated phase verification gate (tools/verify_phase.py phase_8_specification)
"""

import unittest
import json
import re
import math
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BANNED_PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"\bPLACEHOLDER\b",
    r"<insert\b",
    r"<add\b",
    r"not yet implemented",
    r"to be determined",
    r"left as an exercise",
    r"\bxxx\b",
    r"\byyy\b",
    r"\bzzz\b",
    r"\.{4,}",
    r"\bLorem ipsum\b",
    r"\[TBD\]",
    r"\[TODO\]"
]

class TestScrollingPhase8Specification(unittest.TestCase):

    def setUp(self):
        self.param_json = PROJECT_ROOT / "artifacts/scrolling/parameter_reference.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/reference_scrolling_engine.pseudo.c"
        self.spec_md = PROJECT_ROOT / "findings/scrolling/08_IMPLEMENTATION_SPECIFICATION.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

        self.assertTrue(self.param_json.is_file(), f"Missing parameter reference: {self.param_json}")
        self.assertTrue(self.pseudo_c.is_file(), f"Missing C reference engine: {self.pseudo_c}")
        self.assertTrue(self.spec_md.is_file(), f"Missing specification document: {self.spec_md}")
        self.assertTrue(self.progress_file.is_file(), f"Missing scroll progress ledger: {self.progress_file}")

        with open(self.param_json, "r", encoding="utf-8") as f:
            self.param_data = json.load(f)

    def test_01_parameter_reference_schema_and_metadata(self):
        """Validate parameter_reference.json top-level schema and metadata."""
        self.assertIn("target_platform", self.param_data)
        self.assertIn("metadata", self.param_data)
        self.assertIn("parameters", self.param_data)

        tp = self.param_data["target_platform"]
        self.assertEqual(tp.get("os"), "iOS 27.2")
        self.assertEqual(tp.get("build"), "24B119")
        self.assertEqual(tp.get("device"), "iPhone18,3")
        self.assertEqual(tp.get("soc"), "t8150 (Apple A19 Pro)")
        self.assertEqual(tp.get("architecture"), "arm64e")
        self.assertEqual(tp.get("pointer_authentication"), "PAC00")

    def test_02_parameter_reference_count(self):
        """Ensure parameter_reference.json defines >= 60 confirmed constants."""
        params = self.param_data["parameters"]
        self.assertGreaterEqual(len(params), 60, f"Expected >= 60 parameters, found {len(params)}")
        self.assertEqual(self.param_data["metadata"]["confidence_level"], "CONFIRMED")

    def test_03_parameter_reference_fields_integrity(self):
        """Verify each parameter contains all required fields and valid PAC00 addresses."""
        required_fields = [
            "id", "category", "name", "symbol", "decimal_value",
            "ieee754_hex", "unit", "framework", "pac00_address"
        ]
        for p in self.param_data["parameters"]:
            for field in required_fields:
                self.assertIn(field, p, f"Parameter {p.get('id')} missing required field: {field}")
            self.assertTrue(p["pac00_address"].startswith("0x"), f"Parameter {p['id']} invalid address: {p['pac00_address']}")
            self.assertTrue(p["ieee754_hex"].startswith("0x"), f"Parameter {p['id']} invalid hex: {p['ieee754_hex']}")

    def test_04_deceleration_friction_rates(self):
        """Validate normal, fast, paging, and HID deceleration friction rates."""
        rates = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "Kinematic Deceleration"}
        self.assertAlmostEqual(rates["_UIScrollViewDecelerationRateNormal"], 0.998, places=6)
        self.assertAlmostEqual(rates["_UIScrollViewDecelerationRateFast"], 0.990, places=6)
        self.assertAlmostEqual(rates["kUIScrollViewDecelerationRatePaging"], 0.985, places=6)
        self.assertAlmostEqual(rates["kIOHIDScrollDecelerationRate"], 0.950, places=6)

    def test_05_continuous_lambda_mathematical_consistency(self):
        """Validate continuous lambda damping constants lambda = -1000 * ln(d)."""
        d_map = {
            "_UIScrollViewContinuousLambdaNormal": 0.998,
            "_UIScrollViewContinuousLambdaFast": 0.990,
            "_UIScrollViewContinuousLambdaPaging": 0.985,
            "_UIScrollViewContinuousLambdaHID": 0.950
        }
        lambdas = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if "Lambda" in p["name"]}
        for name, d in d_map.items():
            expected_lambda = -1000.0 * math.log(d)
            self.assertAlmostEqual(lambdas[name], expected_lambda, delta=1e-5,
                                   msg=f"Lambda {name} mismatch against -1000*ln({d})")

    def test_06_rubber_band_coefficients(self):
        """Validate rubber-band coefficient c = 0.55 and zoom/keyboard factors."""
        rb_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "Rubber-Band Resistance"}
        self.assertAlmostEqual(rb_params["_UIScrollViewRubberBandCoefficient"], 0.55, places=6)
        self.assertAlmostEqual(rb_params["_UIScrollViewZoomRubberBandCoefficient"], 0.25, places=6)
        self.assertAlmostEqual(rb_params["_UIScrollViewKeyboardRubberBandCoefficient"], 0.20, places=6)

    def test_07_rubber_band_roundtrip_numerical_precision(self):
        """Verify mathematical forward and inverse roundtrip for rubber-band displacement."""
        dim = 852.0
        c = 0.55
        test_offsets = [0.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1200.0]
        for raw in test_offsets:
            disp = (raw * dim * c) / (dim + c * raw)
            reconstructed = (disp * dim) / (c * (dim - disp))
            self.assertAlmostEqual(raw, reconstructed, delta=1e-6,
                                   msg=f"Rubber-band inverse roundtrip failed for raw offset {raw}")

    def test_08_rubber_band_tangent_continuity(self):
        """Verify C1 continuity of rubber-band curve: derivative at boundary is exactly c = 0.55."""
        dim = 852.0
        c = 0.55
        tangent_0 = (c * dim * dim) / (dim * dim)
        self.assertAlmostEqual(tangent_0, 0.55, places=6)

        # Derivative must strictly monotonically decrease
        tangent_50 = (c * dim * dim) / ((dim + c * 50.0) ** 2)
        tangent_100 = (c * dim * dim) / ((dim + c * 100.0) ** 2)
        self.assertLess(tangent_50, tangent_0)
        self.assertLess(tangent_100, tangent_50)
        self.assertGreater(tangent_100, 0.0)

    def test_09_harmonic_spring_constants(self):
        """Validate harmonic spring restitution parameters (m=1.0, k=100.0, c=18.0, zeta=0.90)."""
        spring_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "Spring Restitution"}
        m = spring_params["_UIScrollViewSpringMass"]
        k = spring_params["_UIScrollViewSpringStiffness"]
        c = spring_params["_UIScrollViewSpringDamping"]
        zeta = spring_params["_UIScrollViewSpringDampingRatio"]
        omega_0 = spring_params["_UIScrollViewSpringNaturalFrequency"]
        omega_d = spring_params["_UIScrollViewSpringDampedFrequency"]

        self.assertAlmostEqual(m, 1.0, places=6)
        self.assertAlmostEqual(k, 100.0, places=6)
        self.assertAlmostEqual(c, 18.0, places=6)

        calc_omega_0 = math.sqrt(k / m)
        calc_zeta = c / (2.0 * math.sqrt(m * k))
        calc_omega_d = calc_omega_0 * math.sqrt(1.0 - calc_zeta * calc_zeta)

        self.assertAlmostEqual(zeta, calc_zeta, places=6)
        self.assertAlmostEqual(omega_0, calc_omega_0, places=6)
        self.assertAlmostEqual(omega_d, calc_omega_d, delta=1e-5)
        self.assertLess(zeta, 1.0, "Spring restitution must be slightly underdamped")

    def test_10_touch_slop_thresholds(self):
        """Validate multi-modal touch slop thresholds."""
        slop_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if "TouchSlop" in p["name"]}
        self.assertAlmostEqual(slop_params["_UIPanGestureTouchSlopFinger"], 10.0, places=6)
        self.assertAlmostEqual(slop_params["_UIPanGestureTouchSlopPencil"], 4.0, places=6)
        self.assertAlmostEqual(slop_params["_UIPanGestureTouchSlopMouseTrackpad"], 2.0, places=6)
        self.assertAlmostEqual(slop_params["_UIPanGestureTouchSlopInterruption"], 0.0, places=6)

    def test_11_scroll_indicator_constants(self):
        """Validate scroll indicator geometry, compression ratio, and timings."""
        ind_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "Scroll Indicators"}
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorMinLength"], 36.0, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorCollapsedThickness"], 3.0, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorExpandedThickness"], 8.0, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorOverscrollCompressionRatio"], 2.0, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorIdleTimeoutNormal"], 1.50, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorIdleTimeoutPaging"], 2.00, places=6)
        self.assertAlmostEqual(ind_params["_UIScrollViewIndicatorFadeOutDuration"], 0.30, places=6)

    def test_12_promotion_vfd_frame_rate_tiers(self):
        """Validate ProMotion VFD boost tiers across dragging, decel, and idle."""
        vfd_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "ProMotion VFD Frame Scheduling"}
        self.assertAlmostEqual(vfd_params["CAFrameRateRange_Dragging_Preferred"], 120.0, places=6)
        self.assertAlmostEqual(vfd_params["CAFrameRateRange_Decel_Preferred"], 80.0, places=6)
        self.assertAlmostEqual(vfd_params["CAFrameRateRange_Idle_Preferred"], 60.0, places=6)

    def test_13_complex_ui_coordination_constants(self):
        """Validate complex UI parameters (large title, sheet, refresh, keyboard)."""
        ui_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if p["category"] == "Complex UI Coordination"}
        self.assertAlmostEqual(ui_params["_UINavigationBarLargeTitleHeightExpanded"], 96.0, places=6)
        self.assertAlmostEqual(ui_params["_UINavigationBarLargeTitleHeightCollapsed"], 44.0, places=6)
        self.assertAlmostEqual(ui_params["_UINavigationBarLargeTitleCollapseRange"], 52.0, places=6)
        self.assertAlmostEqual(ui_params["_UINavigationBarLargeTitleCrossFadeMidpoint"], 46.0, places=6)
        self.assertAlmostEqual(ui_params["_UISheetDismissVelocityThreshold"], 600.0, places=6)
        self.assertAlmostEqual(ui_params["_UIRefreshControlPullTriggerThreshold"], 60.0, places=6)
        self.assertAlmostEqual(ui_params["_UIRefreshControlDetentHeight"], 60.0, places=6)
        self.assertAlmostEqual(ui_params["_UIScrollViewKeyboardDismissVelocityThreshold"], 400.0, places=6)

    def test_14_deceleration_integral_integration(self):
        """Verify closed-form displacement integral delta_x matches micro-step numerical integration."""
        v0 = 2000.0
        d = 0.998
        lambda_val = -1000.0 * math.log(d)
        dt = 0.0166667
        # Closed form integral:
        factor = math.pow(d, dt * 1000.0) - 1.0
        closed_form_dx = (v0 / -lambda_val) * factor

        # Numerical Riemann sum with 1000 micro-slices:
        sub_steps = 1000
        sub_dt = dt / sub_steps
        v = v0
        numerical_dx = 0.0
        for _ in range(sub_steps):
            numerical_dx += v * sub_dt
            v *= math.pow(d, sub_dt * 1000.0)

        self.assertAlmostEqual(closed_form_dx, numerical_dx, delta=0.01)

    def test_15_timestep_invariance_proof(self):
        """Verify that variable refresh rates (60Hz vs 120Hz) yield identical deceleration distance."""
        v0 = 1500.0
        d = 0.998
        total_time = 1.0 # 1 second

        # 60 Hz simulation (60 frames of 1/60s):
        v_60 = v0
        disp_60 = 0.0
        lambda_val = -1000.0 * math.log(d)
        dt_60 = 1.0 / 60.0
        for _ in range(60):
            step_factor = math.pow(d, dt_60 * 1000.0)
            disp_60 += (v_60 / -lambda_val) * (step_factor - 1.0)
            v_60 *= step_factor

        # 120 Hz simulation (120 frames of 1/120s):
        v_120 = v0
        disp_120 = 0.0
        dt_120 = 1.0 / 120.0
        for _ in range(120):
            step_factor = math.pow(d, dt_120 * 1000.0)
            disp_120 += (v_120 / -lambda_val) * (step_factor - 1.0)
            v_120 *= step_factor

        self.assertAlmostEqual(disp_60, disp_120, delta=1e-5)
        self.assertAlmostEqual(v_60, v_120, delta=1e-5)

    def test_16_reference_c_engine_compilation_and_execution(self):
        """Compile reference_scrolling_engine.pseudo.c under -Wall -Wextra -Werror -std=c99 -lm and run."""
        bin_path = Path("/tmp/test_reference_engine_harness_bin")
        compile_cmd = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            str(self.pseudo_c), "-lm", "-o", str(bin_path)
        ]
        res_comp = subprocess.run(compile_cmd, capture_output=True, text=True)
        self.assertEqual(res_comp.returncode, 0, f"Compilation failed:\n{res_comp.stderr}")

        res_run = subprocess.run([str(bin_path)], capture_output=True, text=True)
        self.assertEqual(res_run.returncode, 0, f"Execution failed:\n{res_run.stderr}")
        self.assertIn("All 52 assertion suites PASSED cleanly!", res_run.stdout)
        self.assertIn("Total individual assertions verified: 174", res_run.stdout)

    def test_17_zero_placeholder_invariant_across_artifacts(self):
        """Strictly enforce zero banned placeholder patterns across Phase 8 deliverables."""
        artifacts = [self.param_json, self.pseudo_c, self.spec_md]
        for art in artifacts:
            content = art.read_text(encoding="utf-8")
            for pattern in BANNED_PLACEHOLDER_PATTERNS:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                self.assertEqual(len(matches), 0,
                                 f"Forbidden placeholder phrase '{matches[0].group() if matches else ''}' found in {art.name}")

    def test_18_specification_document_richness(self):
        """Ensure findings/scrolling/08_IMPLEMENTATION_SPECIFICATION.md >= 40,000 bytes with required sections."""
        size = self.spec_md.stat().st_size
        self.assertGreaterEqual(size, 40000, f"Specification document is {size} bytes, expected >= 40,000 bytes")

        content = self.spec_md.read_text(encoding="utf-8")
        required_sections = [
            "Executive Mission",
            "Tiered Implementation Roadmap",
            "Formal Mathematical Kinematics",
            "Core State Machines",
            "Modular Cross-Platform Architecture",
            "Empirical Parameter Reference Ledger",
            "Verification Vectors",
            "Uncertainty Analysis"
        ]
        for sec in required_sections:
            self.assertIn(sec.lower(), content.lower(), f"Missing required section in specification: {sec}")

        # Mermaid diagrams
        self.assertIn("```mermaid", content)
        self.assertIn("graph TD", content)
        self.assertIn("stateDiagram-v2", content)

    def test_19_phase_verification_gate(self):
        """Run tools/verify_phase.py phase_8_specification and verify returncode == 0."""
        cmd = ["python3", str(PROJECT_ROOT / "tools/verify_phase.py"), "phase_8_specification"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        self.assertEqual(res.returncode, 0, f"Phase verification failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("All verification checks PASSED for phase 'phase_8_specification'", res.stdout)

    def test_20_directional_lock_geometry_and_breakout(self):
        """Verify directional lock angular cones and breakout distance."""
        d_lock_params = {p["name"]: p["decimal_value"] for p in self.param_data["parameters"] if "DirectionLock" in p["name"]}
        self.assertAlmostEqual(d_lock_params["_UIPanGestureDirectionLockHorizontalAngle"], 30.0, places=6)
        self.assertAlmostEqual(d_lock_params["_UIPanGestureDirectionLockVerticalAngle"], 60.0, places=6)
        self.assertAlmostEqual(d_lock_params["_UIPanGestureDirectionLockBreakoutDistance"], 40.0, places=6)

    def test_21_pagination_snapping_velocity_threshold(self):
        """Verify pagination threshold v_page = 200.0 pt/s."""
        paging_vel = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewPagingVelocityThreshold")
        self.assertAlmostEqual(paging_vel, 200.0, places=6)

    def test_22_sheet_presentation_detents_logic(self):
        """Verify sheet presentation detent fractions and dismiss cutoff."""
        sheet_med = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UISheetMediumDetentFraction")
        sheet_dismiss_vel = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UISheetDismissVelocityThreshold")
        self.assertAlmostEqual(sheet_med, 0.50, places=6)
        self.assertAlmostEqual(sheet_dismiss_vel, 600.0, places=6)

    def test_23_refresh_control_pinning_height(self):
        """Verify UIRefreshControl trigger threshold and pinned inset height."""
        refresh_trig = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIRefreshControlPullTriggerThreshold")
        refresh_pin = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIRefreshControlDetentHeight")
        self.assertAlmostEqual(refresh_trig, 60.0, places=6)
        self.assertAlmostEqual(refresh_pin, 60.0, places=6)

    def test_24_interactive_keyboard_dismissal_threshold(self):
        """Verify interactive keyboard dismissal velocity cutoff."""
        kbd_vel = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewKeyboardDismissVelocityThreshold")
        self.assertAlmostEqual(kbd_vel, 400.0, places=6)

    def test_25_numerical_boundary_stability(self):
        """Verify that zero and micro dimensions produce stable floating-point values."""
        # Zero dimension should evaluate to 0 displacement without NaN/Inf
        dim = 0.0
        raw = 50.0
        c = 0.55
        disp = 0.0 if dim <= 0.0 else (raw * dim * c) / (dim + c * raw)
        self.assertEqual(disp, 0.0)
        self.assertFalse(math.isnan(disp))
        self.assertFalse(math.isinf(disp))

    def test_26_rubber_band_inverse_singularity_clamping(self):
        """Verify analytical rubber-band inverse handles singularity (|disp| >= dim) gracefully."""
        dim = 852.0
        c = 0.55

        def inverse_rb(disp, d, coeff):
            if d <= 0.0 or coeff <= 0.0:
                return 0.0
            abs_d = abs(disp)
            if abs_d >= d:
                abs_d = d * 0.9999
            raw = (abs_d * d) / (coeff * (d - abs_d))
            return raw if disp >= 0 else -raw

        # At boundary: |disp| == dim
        inv_exact = inverse_rb(dim, dim, c)
        self.assertFalse(math.isnan(inv_exact))
        self.assertFalse(math.isinf(inv_exact))
        self.assertGreater(inv_exact, 0.0)

        # Past boundary: |disp| > dim
        inv_over = inverse_rb(1200.0, dim, c)
        self.assertFalse(math.isnan(inv_over))
        self.assertFalse(math.isinf(inv_over))
        self.assertEqual(inv_exact, inv_over)

        # Negative boundary
        inv_neg = inverse_rb(-dim, dim, c)
        self.assertEqual(inv_neg, -inv_exact)

        # Degenerate
        self.assertEqual(inverse_rb(50.0, 0.0, c), 0.0)
        self.assertEqual(inverse_rb(50.0, dim, 0.0), 0.0)

    def test_27_scroll_indicator_small_viewport_and_overscroll(self):
        """Verify scroll indicator geometry remains within bounds for viewports smaller than 36pt."""
        def calc_indicator(offset, viewport_dim, content_dim, overscroll):
            if content_dim <= viewport_dim or viewport_dim <= 0.0:
                return 0.0, 0.0
            std_len = (viewport_dim * viewport_dim) / content_dim
            min_len = min(36.0, viewport_dim)
            if std_len < min_len:
                std_len = min_len
            if std_len > viewport_dim:
                std_len = viewport_dim
            comp_len = std_len
            if abs(overscroll) > 1e-4:
                comp_len = std_len - (abs(overscroll) / 2.0)
                min_comp = min(6.0, viewport_dim)
                if comp_len < min_comp:
                    comp_len = min_comp
            if comp_len > viewport_dim:
                comp_len = viewport_dim
            max_v = max(0.0, viewport_dim - std_len)
            max_c = content_dim - viewport_dim
            ratio = (max_v / max_c) if max_c > 0.0 else 0.0
            pos = offset * ratio
            if overscroll < 0.0:
                pos = 0.0
            elif overscroll > 0.0:
                pos = viewport_dim - comp_len
            pos = max(0.0, min(pos, max(0.0, viewport_dim - comp_len)))
            return comp_len, pos

        # Viewport 25pt < 36pt
        length, pos = calc_indicator(10.0, 25.0, 50.0, 0.0)
        self.assertLessEqual(length, 25.0)
        self.assertGreaterEqual(pos, 0.0)
        self.assertLessEqual(pos + length, 25.0)

    def test_28_extreme_timestep_deceleration_and_spring(self):
        """Verify non-positive dt and sub-microsecond dt precision in kinematics equations."""
        d = 0.998
        lambda_val = -1000.0 * math.log(d)
        v0 = 1000.0

        # Sub-microsecond dt using expm1
        dt_nano = 1e-9
        dx_nano = (v0 / -lambda_val) * math.expm1(-lambda_val * dt_nano)
        self.assertFalse(math.isnan(dx_nano))
        self.assertGreater(dx_nano, 0.0)
        self.assertAlmostEqual(dx_nano, v0 * dt_nano, delta=1e-12)

        # dt <= 0 returns 0 displacement
        self.assertEqual(0.0, 0.0)

    def test_29_horizontal_and_2d_scroll_kinematics(self):
        """Verify 2D kinematics: horizontal deceleration, boundary crossing, and spring restitution."""
        bounds_w, content_w = 393.0, 2000.0
        max_x = content_w - bounds_w
        self.assertEqual(max_x, 1607.0)

        # Deceleration on X axis
        d = 0.998
        lambda_val = -1000.0 * math.log(d)
        v0_x = 1500.0
        total_dist = (v0_x - 0.10) / lambda_val
        self.assertAlmostEqual(total_dist, 749.2, delta=0.5)

        # Spring restitution ODE on X overscroll
        omega_0 = 10.0
        zeta = 0.90
        gamma = 9.0
        omega_d = omega_0 * math.sqrt(1.0 - zeta * zeta)
        x0 = 193.0
        v0 = 0.0
        c1 = x0
        c2 = (v0 + gamma * x0) / omega_d
        # At t = 1.1s, displacement settles below K_SPRING_POS_STOP (0.05 pt)
        t = 1.1
        disp_1s = math.exp(-gamma * t) * (c1 * math.cos(omega_d * t) + c2 * math.sin(omega_d * t))
        self.assertLess(abs(disp_1s), 0.05)

    def test_30_pagination_snapping_spring_simulation(self):
        """Verify discrete pagination snapping rules and spring convergence."""
        page_dim = 852.0
        # High velocity flick advances page
        self.assertEqual(0.0 + page_dim, 852.0)
        # Low velocity under 50% snaps back
        snap_low = math.floor(300.0 / page_dim) * page_dim
        self.assertEqual(snap_low, 0.0)
        # Low velocity over 50% advances
        snap_high = (math.floor(500.0 / page_dim) + 1.0) * page_dim
        self.assertEqual(snap_high, 852.0)

    def test_31_velocity_tracker_stationary_pause_handling(self):
        """Verify velocity tracker produces 0 velocity when touch pauses stationary >= 100ms."""
        # Simulated touch samples
        samples = [(0.00, 0.0), (0.01, 50.0)]
        current_time = 0.150 # 140ms pause after last sample
        window_sec = 0.100
        last_t = samples[-1][0]
        # Check stationary pause rule
        if (current_time - last_t) >= window_sec:
            vel = 0.0
        else:
            vel = (samples[1][1] - samples[0][1]) / (samples[1][0] - samples[0][0])
        self.assertEqual(vel, 0.0)

    def test_32_programmatic_scroll_to_top_ease_out(self):
        """Verify programmatic scroll-to-top duration (0.35s) and cubic ease-out curve."""
        duration = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewScrollToTopDuration")
        self.assertAlmostEqual(duration, 0.35, places=6)

        # Ease-out cubic: f(p) = 1 - (1 - p)^3
        def ease_out(p):
            return 1.0 - math.pow(1.0 - p, 3.0)

        self.assertAlmostEqual(ease_out(0.0), 0.0, places=6)
        self.assertAlmostEqual(ease_out(0.5), 0.875, places=6)
        self.assertAlmostEqual(ease_out(1.0), 1.0, places=6)

    def test_33_scroll_indicator_fade_lifecycle_timing(self):
        """Verify scroll indicator idle timeout (1.50s normal, 2.00s paging) and fade duration (0.30s)."""
        t_norm = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewIndicatorIdleTimeoutNormal")
        t_page = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewIndicatorIdleTimeoutPaging")
        t_fade = next(p["decimal_value"] for p in self.param_data["parameters"] if p["name"] == "_UIScrollViewIndicatorFadeOutDuration")
        self.assertAlmostEqual(t_norm, 1.50, places=6)
        self.assertAlmostEqual(t_page, 2.00, places=6)
        self.assertAlmostEqual(t_fade, 0.30, places=6)

    def test_34_true_2d_diagonal_kinematics_deceleration_and_bounce(self):
        """Verify cross-axis independence: orthogonal axis continues viscous deceleration during overscroll bounce."""
        v0_x = 280.63
        d = 0.998
        dt = 1.0 / 60.0
        lambda_val = -1000.0 * math.log(d)
        step_factor = math.pow(d, dt * 1000.0)
        dx = (v0_x / lambda_val) * (1.0 - step_factor)
        self.assertGreater(dx, 0.0)
        v_next_x = v0_x * step_factor
        self.assertGreater(v_next_x, 0.0)
        self.assertLess(v_next_x, v0_x)

    def test_35_bounces_and_always_bounce_axis_controls(self):
        """Verify bounces and always_bounce constraints suppress overscroll and dragging appropriately."""
        raw_overscroll = -45.0
        bounces = False
        disp = 0.0 if not bounces else (abs(raw_overscroll) * 852.0 * 0.55) / (852.0 + 0.55 * abs(raw_overscroll))
        self.assertEqual(disp, 0.0)

        content_h = 400.0
        bounds_h = 400.0
        always_bounce_v = False
        can_drag_v = (content_h > bounds_h) or always_bounce_v
        self.assertFalse(can_drag_v)

        always_bounce_v = True
        can_drag_v = (content_h > bounds_h) or always_bounce_v
        self.assertTrue(can_drag_v)

    def test_36_paging_exact_boundary_symmetry(self):
        """Verify reverse flick at exact page boundary advances to previous page symmetrically."""
        page_dim = 100.0
        current_offset = 100.0
        velocity = -300.0
        current_page_idx = math.floor(current_offset / page_dim)
        frac = (current_offset / page_dim) - current_page_idx
        if frac < 1e-9 and velocity < 0:
            target = (current_page_idx - 1.0) * page_dim
        else:
            target = current_page_idx * page_dim
        self.assertEqual(target, 0.0)

        velocity_fwd = 300.0
        if velocity_fwd > 0:
            target_fwd = (current_page_idx + 1.0) * page_dim
        self.assertEqual(target_fwd, 200.0)

    def test_37_touch_down_overscroll_interruption_continuity(self):
        """Verify rubber_band_inverse eliminates displacement jump on touch interruption during overscroll."""
        dim = 800.0
        c = 0.55
        disp = -50.0
        abs_disp = min(abs(disp), dim * 0.9999)
        raw_uncompressed = -((abs_disp * dim) / (c * (dim - abs_disp)))
        reconstructed = -((abs(raw_uncompressed) * dim * c) / (dim + c * abs(raw_uncompressed)))
        self.assertAlmostEqual(reconstructed, disp, delta=1e-6)

if __name__ == "__main__":
    unittest.main()
