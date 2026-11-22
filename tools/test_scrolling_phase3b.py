#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 3B: Scrolling Physics & Motion Algorithms
Tests velocity estimation ring buffer schema, IEEE 754 float precision,
exponential deceleration kinematics, ProMotion frame-rate invariance,
spring harmonic oscillator ODE dynamics, closed-form analytical solvers,
C pseudocode compilation and syntax, anti-placeholder compliance,
and evidence ledger integrity.
"""

import unittest
import json
import re
import struct
import math
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestScrollingPhase3BAdversarial(unittest.TestCase):

    def setUp(self):
        self.velocity_json = PROJECT_ROOT / "artifacts/scrolling/velocity_algorithm.json"
        self.deceleration_json = PROJECT_ROOT / "artifacts/scrolling/deceleration_model.json"
        self.spring_json = PROJECT_ROOT / "artifacts/scrolling/spring_model.json"
        self.constants_json = PROJECT_ROOT / "artifacts/scrolling/physics_constants.json"
        self.decel_pseudo = PROJECT_ROOT / "artifacts/scrolling/pseudocode/deceleration_step.pseudo.c"
        self.vel_pseudo = PROJECT_ROOT / "artifacts/scrolling/pseudocode/velocity_estimation.pseudo.c"
        self.spring_pseudo = PROJECT_ROOT / "artifacts/scrolling/pseudocode/spring_step.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/03B_SCROLLING_PHYSICS.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.shared_cache_slice = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.01"

    def test_velocity_algorithm_schema_and_values(self):
        """R1: Test velocity algorithm ring buffer, OLS regression, clamping, and transformations."""
        self.assertTrue(self.velocity_json.is_file(), "velocity_algorithm.json must exist")
        with open(self.velocity_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Ring buffer architecture
        rb = data.get("ring_buffer_architecture", {})
        self.assertEqual(rb.get("capacity_samples"), 8)
        self.assertEqual(rb.get("element_size_bytes"), 24)
        self.assertEqual(rb.get("total_ring_buffer_bytes"), 192)
        self.assertEqual(rb.get("temporal_lookback_window_sec"), 0.100)
        self.assertEqual(rb.get("temporal_lookback_window_ms"), 100.0)

        # Check IEEE 754 unpacking for lookback
        lookback_double = struct.unpack(">d", bytes.fromhex(rb["temporal_lookback_ieee754_double_hex"][2:]))[0]
        self.assertAlmostEqual(lookback_double, 0.100, places=9)

        # 2. Mathematical algorithms
        algos = data.get("mathematical_algorithms", {})
        self.assertIn("least_squares_linear_regression", algos)
        self.assertIn("exponential_moving_average_filter", algos)
        ema = algos["exponential_moving_average_filter"]
        self.assertEqual(ema.get("smoothing_factor_alpha"), 0.85)
        ema_double = struct.unpack(">d", bytes.fromhex(ema["alpha_ieee754_double_hex"][2:]))[0]
        self.assertAlmostEqual(ema_double, 0.85, places=9)

        # 3. Clamping and thresholds
        clamps = data.get("velocity_clamping_and_thresholds", {})
        self.assertEqual(clamps["minimum_fling_velocity"]["threshold_pt_per_sec"], 10.0)
        self.assertEqual(clamps["maximum_fling_velocity_cap"]["threshold_pt_per_sec"], 8000.0)
        self.assertEqual(clamps["terminal_stop_velocity"]["threshold_pt_per_sec"], 0.1)

        # 4. Directional projections
        proj = data.get("directional_projections_and_locking", {})
        self.assertEqual(proj.get("vertical_lock_threshold_deg"), 60.0)
        self.assertEqual(proj.get("horizontal_lock_threshold_deg"), 30.0)
        self.assertEqual(proj.get("cross_axis_break_hysteresis_pt"), 40.0)
        self.assertEqual(proj.get("break_frames_required"), 3)

        # 5. Coordinate transformations
        coords = data.get("coordinate_transformations", {})
        self.assertIn("pan_to_scroll_velocity_sign_inversion", coords)
        self.assertEqual(coords["pan_to_scroll_velocity_sign_inversion"]["formula"], "v_scroll = -v_pan = (-v_pan.x, -v_pan.y)")

    def test_deceleration_model_ieee754_accuracy_and_math(self):
        """R2: Test exact IEEE 754 deceleration rates, continuous ODE, and closed-form landing offset."""
        self.assertTrue(self.deceleration_json.is_file(), "deceleration_model.json must exist")
        with open(self.deceleration_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        rates = data.get("deceleration_rate_constants", {})

        # 1. Normal Deceleration Rate: 0.998
        self.assertIn("normal", rates)
        norm = rates["normal"]
        self.assertEqual(norm["value_decimal"], 0.998)
        norm_double = struct.unpack(">d", bytes.fromhex(norm["ieee754_double_hex"][2:]))[0]
        self.assertEqual(norm_double, 0.998)
        norm_single = struct.unpack(">f", bytes.fromhex(norm["ieee754_single_hex"][2:]))[0]
        self.assertAlmostEqual(norm_single, 0.998, places=3)
        self.assertTrue(norm["constant_vm_address"].startswith("0x1864"))

        # Verify theoretical lambda = -1000 * ln(0.998)
        expected_lambda_norm = -1000.0 * math.log(0.998)
        self.assertAlmostEqual(norm["decay_constant_lambda_per_sec"], expected_lambda_norm, places=6)
        expected_landing_norm = 1.0 / expected_lambda_norm
        self.assertAlmostEqual(norm["landing_multiplier_Cd"], expected_landing_norm, places=6)

        # 2. Fast Deceleration Rate: 0.990
        self.assertIn("fast", rates)
        fast = rates["fast"]
        self.assertEqual(fast["value_decimal"], 0.990)
        fast_double = struct.unpack(">d", bytes.fromhex(fast["ieee754_double_hex"][2:]))[0]
        self.assertEqual(fast_double, 0.990)
        fast_single = struct.unpack(">f", bytes.fromhex(fast["ieee754_single_hex"][2:]))[0]
        self.assertAlmostEqual(fast_single, 0.990, places=3)

        expected_lambda_fast = -1000.0 * math.log(0.990)
        self.assertAlmostEqual(fast["decay_constant_lambda_per_sec"], expected_lambda_fast, places=6)
        expected_landing_fast = 1.0 / expected_lambda_fast
        self.assertAlmostEqual(fast["landing_multiplier_Cd"], expected_landing_fast, places=6)

        # 3. Paging Deceleration Rate: 0.985
        self.assertIn("paging", rates)
        paging = rates["paging"]
        self.assertEqual(paging["value_decimal"], 0.985)
        paging_double = struct.unpack(">d", bytes.fromhex(paging["ieee754_double_hex"][2:]))[0]
        self.assertEqual(paging_double, 0.985)

        # 4. ProMotion Frame-rate invariance mathematical proof
        # Two 120Hz steps (dt = 1/120) must equal exactly one 60Hz step (dt = 1/60)
        dt_120 = 1.0 / 120.0
        dt_60 = 1.0 / 60.0
        factor_120 = math.pow(0.998, dt_120 * 1000.0)
        factor_60 = math.pow(0.998, dt_60 * 1000.0)
        self.assertAlmostEqual(factor_120 * factor_120, factor_60, places=12)

        # 5. Definite displacement integral formula verification
        # Integral \int_0^{dt} v_0 e^{-\lambda t} dt == (v_0 - v_{end}) / \lambda
        v0 = 1000.0
        v_end = v0 * factor_60
        integral_num = (v0 - v_end) / expected_lambda_norm
        # Analytical integration
        integral_exact = (v0 / expected_lambda_norm) * (1.0 - math.exp(-expected_lambda_norm * dt_60))
        self.assertAlmostEqual(integral_num, integral_exact, places=10)

        # 6. Terminal stop velocity
        stops = data.get("stopping_conditions", {})
        self.assertEqual(stops.get("terminal_velocity_threshold_pt_per_sec"), 0.1)

    def test_spring_model_physics_and_ode(self):
        """R3: Test harmonic oscillator ODE, damping ratio, natural frequency, and analytical solvers."""
        self.assertTrue(self.spring_json.is_file(), "spring_model.json must exist")
        with open(self.spring_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        params = data["physical_harmonic_oscillator_ode"]["parameters"]
        m = params["mass_m"]["value"]
        k = params["stiffness_k"]["value"]
        c = params["damping_c"]["value"]

        self.assertEqual(m, 1.0)
        self.assertEqual(k, 100.0)
        self.assertEqual(c, 18.0)

        # Derived properties
        props = data["derived_dynamic_properties"]
        omega_n = math.sqrt(k / m)
        self.assertEqual(props["undamped_natural_frequency"]["value_rad_per_sec"], omega_n)
        self.assertEqual(omega_n, 10.0)

        c_c = 2.0 * math.sqrt(k * m)
        self.assertEqual(props["critical_damping_coefficient"]["value_n_s_per_m"], c_c)
        self.assertEqual(c_c, 20.0)

        zeta = c / c_c
        self.assertEqual(props["damping_ratio"]["value"], zeta)
        self.assertEqual(zeta, 0.90)
        self.assertEqual(props["damping_ratio"]["damping_regime"], "underdamped")

        omega_d = omega_n * math.sqrt(1.0 - zeta * zeta)
        self.assertAlmostEqual(props["damped_angular_frequency"]["value_rad_per_sec"], omega_d, places=6)
        self.assertAlmostEqual(omega_d, 4.358898943540674, places=6)

        gamma = zeta * omega_n
        self.assertEqual(props["decay_envelope_rate"]["value_per_sec"], gamma)
        self.assertEqual(gamma, 9.0)

        # Verification of analytical closed-form initial boundary values
        # At t = 0: x(0) must equal x0, v(0) must equal v0
        x0 = 50.0
        v0 = -200.0
        t = 0.0
        A = x0
        B = (v0 + gamma * x0) / omega_d
        x_at_0 = math.exp(-gamma * t) * (A * math.cos(omega_d * t) + B * math.sin(omega_d * t))
        v_at_0 = math.exp(-gamma * t) * (v0 * math.cos(omega_d * t) - ((gamma * v0 + omega_n * omega_n * x0) / omega_d) * math.sin(omega_d * t))
        self.assertAlmostEqual(x_at_0, x0, places=9)
        self.assertAlmostEqual(v_at_0, v0, places=9)

        # Settling duration formula
        epsilon = 0.5
        t_settle_expected = -math.log(epsilon / abs(x0)) / gamma
        self.assertAlmostEqual(t_settle_expected, 0.51168557, places=6)

    def test_physics_constants_catalog(self):
        """R3/Acceptance: Test physics_constants.json catalog integrity and IEEE 754 precision."""
        self.assertTrue(self.constants_json.is_file(), "physics_constants.json must exist")
        with open(self.constants_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        catalog = data.get("constants_catalog", [])
        self.assertGreaterEqual(len(catalog), 15, "Constants catalog must document >= 15 authoritative constants")

        for entry in catalog:
            # Each entry must have symbol, value, double_hex, single_hex, vm_address
            self.assertIn("symbol", entry)
            self.assertIn("value_decimal", entry)
            self.assertIn("ieee754_double_hex", entry)
            self.assertIn("ieee754_single_hex", entry)
            self.assertIn("vm_address", entry)

            val = entry["value_decimal"]
            d_hex = entry["ieee754_double_hex"][2:]
            unpacked_val = struct.unpack(">d", bytes.fromhex(d_hex))[0]
            self.assertAlmostEqual(unpacked_val, val, places=6, msg=f"Mismatch in {entry['symbol']}")

            self.assertTrue(entry["vm_address"].startswith("0x18"), f"Invalid VM address in {entry['symbol']}")

    def test_pseudocode_files_compilation_and_integrity(self):
        """R6: Test C pseudocode files syntax, compilation with clang, and key function exports."""
        pseudo_files = [
            ("deceleration_step.pseudo.c", self.decel_pseudo),
            ("velocity_estimation.pseudo.c", self.vel_pseudo),
            ("spring_step.pseudo.c", self.spring_pseudo)
        ]

        for fname, fpath in pseudo_files:
            self.assertTrue(fpath.is_file(), f"{fname} must exist")
            content = fpath.read_text(encoding="utf-8")
            self.assertGreaterEqual(len(content), 5000, f"{fname} too brief (< 5000 bytes)")

            # Anti-placeholder check
            banned = [r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bCOMING SOON\b"]
            for pat in banned:
                self.assertFalse(re.search(pat, content, re.I), f"Placeholder {pat} found in {fname}")

            # Verify compilation syntax with clang
            res = subprocess.run(["clang", "-fsyntax-only", str(fpath)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(res.returncode, 0, f"Clang syntax check failed for {fname}:\n{res.stderr}")

        # Check key routine exports
        decel_content = self.decel_pseudo.read_text(encoding="utf-8")
        self.assertIn("_UIScrollViewDecelerationAnimation_projectedOffset", decel_content)
        self.assertIn("_UIScrollViewDecelerationAnimation_updateVelocity_timestamp", decel_content)
        self.assertIn("_UIScrollViewStepDeceleration", decel_content)
        self.assertIn("_UIScrollViewDecelerationDisplayLinkTick", decel_content)
        self.assertIn("kUIScrollViewDecelerationRateNormal", decel_content)

        vel_content = self.vel_pseudo.read_text(encoding="utf-8")
        self.assertIn("_UIScrollViewVelocity_addSample_atTimestamp", vel_content)
        self.assertIn("_UIScrollViewVelocity_filteredVelocity", vel_content)
        self.assertIn("_UIPanGestureRecognizer_velocityInView", vel_content)
        self.assertIn("_UIPanDetermineDirectionalLockAxis", vel_content)
        self.assertIn("kVelocityRingBufferCapacity", vel_content)

        spring_content = self.spring_pseudo.read_text(encoding="utf-8")
        self.assertIn("_UIScrollViewSpringAnimation_updatePosition_timestamp", spring_content)
        self.assertIn("_UIScrollViewEvaluate1DSpring", spring_content)
        self.assertIn("_UIScrollViewStepSpring", spring_content)
        self.assertIn("_UIScrollViewSpringDisplayLinkTick", spring_content)
        self.assertIn("CASpringAnimation_settlingDurationWithVelocity", spring_content)
        self.assertIn("CASpringAnimation_settlingDuration", spring_content)
        self.assertIn("CASpringAnimation_durationForEpsilon", spring_content)
        self.assertIn("_UIScrollViewGetViewScale", decel_content)
        self.assertIn("_UIScrollViewGetViewScale", spring_content)

    def test_evidence_ledger_phase3b_entries(self):
        """R6: Ensure evidence_ledger.jsonl contains at least 12 confirmed Phase 3B entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        phase_3b_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_3B":
                    phase_3b_entries.append(entry)

        self.assertGreaterEqual(len(phase_3b_entries), 12, f"Expected >= 12 Phase 3B entries, found {len(phase_3b_entries)}")
        expected_ids = [f"PHYS-{i:03d}" for i in range(1, 13)]
        found_ids = [e["id"] for e in phase_3b_entries]
        for eid in expected_ids:
            self.assertIn(eid, found_ids, f"Required evidence ID '{eid}' missing from ledger")

        for entry in phase_3b_entries:
            self.assertEqual(entry["confidence"], "CONFIRMED")
            bp = entry.get("binary_path", "")
            self.assertTrue(len(bp) > 0)
            self.assertTrue((PROJECT_ROOT / bp).is_file(), f"Binary path does not exist: {bp}")
            self.assertTrue(entry.get("address", "").startswith("0x184"))
            self.assertTrue(len(entry.get("opcode_instructions", [])) >= 2)

    def test_findings_dossier_structure_and_metrics(self):
        """R6: Verify findings dossier richness, LaTeX math, Mermaid diagrams, and anti-placeholder compliance."""
        self.assertTrue(self.findings_md.is_file(), "03B_SCROLLING_PHYSICS.md must exist")
        content = self.findings_md.read_text(encoding="utf-8")

        self.assertGreaterEqual(len(content), 2500, "Findings document too short (< 2500 bytes)")
        self.assertGreaterEqual(len(content), 20000, "Findings document should provide comprehensive coverage (>= 20000 bytes)")

        # Section structure checks
        h2_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
        self.assertGreaterEqual(h2_count, 4, "Must define >= 4 major '##' sections")

        # Table check
        has_table = bool(re.search(r"\|.+\|.+\|", content))
        self.assertTrue(has_table, "Must contain markdown tables")

        # LaTeX formula check
        has_latex = bool(re.search(r"\$\$.+\$\$", content, re.DOTALL)) or bool(re.search(r"\$.+\$", content))
        self.assertTrue(has_latex, "Must contain LaTeX mathematical equations")

        # Code block check
        self.assertIn("```", content, "Must contain code blocks")

        # Mermaid diagram check
        self.assertIn("mermaid", content, "Must contain Mermaid diagrams")

        # Anti-placeholder check
        banned = [r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bLOREM IPSUM\b", r"\bINSERT HERE\b", r"\bCOMING SOON\b"]
        for pat in banned:
            self.assertFalse(re.search(pat, content, re.I), f"Placeholder {pat} found in findings dossier")

    def test_scroll_progress_phase3b_status(self):
        """Test scroll_progress.json lifecycle completion and transition to phase_3c."""
        self.assertTrue(self.progress_file.is_file(), "scroll_progress.json must exist")
        with open(self.progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        phases = data.get("phases", {})
        self.assertIn("phase_3b_physics", phases)
        p3b = phases["phase_3b_physics"]
        self.assertEqual(p3b.get("status"), "completed")
        self.assertEqual(p3b.get("findings_document"), "findings/scrolling/03B_SCROLLING_PHYSICS.md")
        self.assertEqual(p3b.get("verified_by"), "tools/verify_phase.py phase_3b_physics")

        self.assertIn("phase_3c_rubber_band", phases)
        p3c = phases["phase_3c_rubber_band"]
        self.assertIn(data.get("active_phase_id"), list(phases.keys()))

    def test_deceleration_non_bouncing_and_hang_behavior_native_execution(self):
        """Adversarial C test: verify non-bouncing boundary clamping, spring handoff, and thread hang cancellation."""
        c_code = f"""
#include <stdio.h>
#include <assert.h>
#include <math.h>

void *objc_msgSend(void *self, const char *sel, ...) {{ return NULL; }}

#include "{self.decel_pseudo}"

int main(void) {{
    UIScrollView scroll;
    _UIScrollViewDecelerationAnimation decel;
    _UIScrollViewSpringAnimation spring;

    // Test 1: Bounces == 0 (non-bouncing scroll view hits boundary)
    scroll.isa = NULL;
    scroll._bounds = (CGRect){{ {{0, 0}}, {{393, 852}} }};
    scroll._frame = scroll._bounds;
    scroll._contentSize = (CGSize){{ 393, 2000 }};
    scroll._contentInset = (UIEdgeInsets){{ 0, 0, 0, 0 }};
    scroll._contentOffset = (CGPoint){{ 0, 10 }};
    scroll._decelerationRate = 0.998;
    scroll._decelerationAnimation = &decel;
    scroll._springAnimation = &spring;
    scroll._scrollViewFlags.bounces = 0;
    scroll._scrollViewFlags.isDecelerating = 1;
    scroll._delegate = NULL;

    decel._scrollView = &scroll;
    decel._currentOffset = (CGPoint){{ 0, 10 }};
    decel._velocity = (CGPoint){{ 0, -1000.0 }}; // moving upwards toward top boundary minOffset.y = 0
    decel._decelerationRate = 0.998;
    decel._lastTimestamp = 0.0;
    decel._isCancelled = false;
    decel._hitBoundary = false;

    // Step by 20ms: deltaS.y will overshoot past 0.0
    bool continues = _UIScrollViewStepDeceleration(&decel, 0.020);
    // When bounces == 0 and all motion arrested at boundary:
    assert(!continues);
    assert(scroll._contentOffset.y == 0.0);
    assert(scroll._scrollViewFlags.isDecelerating == 0);
    assert(decel._isCancelled == true);
    assert(decel._velocity.y == 0.0);

    // Test 2: Bounces == 1 (bouncing scroll view hits boundary -> momentum handoff)
    scroll._contentOffset = (CGPoint){{ 0, 10 }};
    scroll._scrollViewFlags.bounces = 1;
    scroll._scrollViewFlags.isDecelerating = 1;
    decel._currentOffset = (CGPoint){{ 0, 10 }};
    decel._velocity = (CGPoint){{ 0, -1000.0 }};
    decel._lastTimestamp = 0.0;
    decel._isCancelled = false;

    continues = _UIScrollViewStepDeceleration(&decel, 0.020);
    assert(!continues); // deceleration stops because spring took over
    assert(decel._hitBoundary == true);
    assert(scroll._contentOffset.y == 0.0); // pinned to minOffset
    assert(spring._equilibriumOffset.y == 0.0);
    assert(spring._initialVelocity.y < -500.0); // residual momentum preserved

    // Test 3: Thread hang (dt > 0.500) -> immediate cancellation
    scroll._contentOffset = (CGPoint){{ 0, 500 }};
    scroll._scrollViewFlags.isDecelerating = 1;
    decel._currentOffset = (CGPoint){{ 0, 500 }};
    decel._velocity = (CGPoint){{ 0, 1000.0 }};
    decel._lastTimestamp = 0.0;
    decel._isCancelled = false;

    continues = _UIScrollViewStepDeceleration(&decel, 0.600); // 600ms gap
    assert(!continues);
    assert(decel._isCancelled == true);
    assert(scroll._scrollViewFlags.isDecelerating == 0);

    // Test 4: Diagonal boundary collision - only breached X receives spring velocity, unbreached Y is strictly 0.0
    scroll._contentOffset = (CGPoint){{ 10, 500 }};
    scroll._scrollViewFlags.bounces = 1;
    scroll._scrollViewFlags.isDecelerating = 1;
    decel._currentOffset = (CGPoint){{ 10, 500 }};
    decel._velocity = (CGPoint){{ -1000.0, 500.0 }}; // X moves towards minOffset.x=0, Y is moving down midway
    decel._lastTimestamp = 0.0;
    decel._isCancelled = false;
    decel._hitBoundary = false;

    continues = _UIScrollViewStepDeceleration(&decel, 0.020);
    assert(!continues);
    assert(decel._hitBoundary == true);
    assert(scroll._contentOffset.x == 0.0);
    assert(spring._equilibriumOffset.x == 0.0);
    assert(spring._initialVelocity.x < -500.0);
    assert(spring._initialVelocity.y == 0.0); // No phantom oscillation on unbreached Y axis!

    // Test 5: Sub-terminal deceleration launch (< 0.1 pt/s) does not engage decelerating state
    scroll._scrollViewFlags.isDecelerating = 0;
    _UIScrollViewStartDecelerationAnimation(&scroll, (CGPoint){{ 0.05, 0.05 }});
    assert(scroll._scrollViewFlags.isDecelerating == 0);

    // Test 6: CADisplayLink tick stepping
    CADisplayLink dlink;
    dlink.timestamp = 1.000;
    dlink.targetTimestamp = 1.016667;
    scroll._contentOffset = (CGPoint){{ 0, 100 }};
    scroll._scrollViewFlags.isDecelerating = 1;
    decel._currentOffset = (CGPoint){{ 0, 100 }};
    decel._velocity = (CGPoint){{ 0, 500.0 }};
    decel._lastTimestamp = 1.000;
    decel._isCancelled = false;
    _UIScrollViewDecelerationDisplayLinkTick(&dlink, &decel);
    assert(decel._lastTimestamp == 1.016667);

    // Test 7: UIRoundToViewScale multi-scale precision across @1x, @2x, @3x
    assert(UIRoundToViewScale(10.4, 1.0) == 10.0);
    assert(UIRoundToViewScale(10.6, 1.0) == 11.0);
    assert(UIRoundToViewScale(10.2, 2.0) == 10.0);
    assert(UIRoundToViewScale(10.3, 2.0) == 10.5);
    assert(UIRoundToViewScale(10.74, 2.0) == 10.5);
    assert(UIRoundToViewScale(10.76, 2.0) == 11.0);
    assert(fabs(UIRoundToViewScale(10.2, 3.0) - (31.0 / 3.0)) < 1e-9);
    assert(fabs(UIRoundToViewScale(10.5, 3.0) - (32.0 / 3.0)) < 1e-9);
    // Invalid / zero scale fallback to 1.0
    assert(UIRoundToViewScale(10.4, 0.0) == 10.0);
    assert(UIRoundToViewScale(10.6, -2.0) == 11.0);
    assert(UIRoundToViewScale(10.4, NAN) == 10.0);
    // Negative coordinate rounding
    assert(UIRoundToViewScale(-10.4, 1.0) == -10.0);
    assert(UIRoundToViewScale(-10.3, 2.0) == -10.5);

    // Test 8: Dynamic display scale in UIScrollView (@2x Retina snapping)
    scroll._displayScale = 2.0;
    scroll._contentOffset = (CGPoint){{ 0, 100 }};
    decel._currentOffset = (CGPoint){{ 0, 100 }};
    decel._velocity = (CGPoint){{ 0, 50.0 }};
    decel._lastTimestamp = 1.000;
    decel._isCancelled = false;
    _UIScrollViewStepDeceleration(&decel, 1.010);
    // contentOffset must be an exact multiple of 0.5 pt on @2x
    double remainder2x = fmod(scroll._contentOffset.y * 2.0, 1.0);
    assert(fabs(remainder2x) < 1e-6 || fabs(remainder2x - 1.0) < 1e-6);

    // Test 9: Terminal stopping condition zeroes residual velocity
    decel._currentOffset = (CGPoint){{ 0, 500 }};
    decel._velocity = (CGPoint){{ 0.0, 0.05 }}; // magnitude 0.05 < 0.1 pt/s
    decel._lastTimestamp = 2.000;
    decel._isCancelled = false;
    scroll._scrollViewFlags.isDecelerating = 1;
    bool decelContinues = _UIScrollViewStepDeceleration(&decel, 2.016);
    assert(!decelContinues);
    assert(decel._isCancelled == true);
    assert(scroll._scrollViewFlags.isDecelerating == 0);
    assert(decel._velocity.x == 0.0 && decel._velocity.y == 0.0);

    // Test 10: Unsynchronized launch baseline synchronization (uptime > 0.500s)
    scroll._scrollViewFlags.isDecelerating = 0;
    scroll._contentOffset = (CGPoint){{ 0, 100 }};
    decel._lastTimestamp = 0.0;
    decel._startTimestamp = 0.0;
    _UIScrollViewStartDecelerationAnimation(&scroll, (CGPoint){{ 0.0, 100.0 }});
    assert(scroll._scrollViewFlags.isDecelerating == 1);
    assert(decel._lastTimestamp == -1.0);
    // First CADisplayLink tick on device running at uptime = 1250.500s
    bool firstTick = _UIScrollViewStepDeceleration(&decel, 1250.500);
    assert(firstTick == true); // Must establish baseline, NOT cancel for severe hang!
    assert(decel._isCancelled == false);
    assert(decel._lastTimestamp == 1250.500);
    // Second tick 16ms later advances deceleration
    bool secondTick = _UIScrollViewStepDeceleration(&decel, 1250.516);
    assert(secondTick == true);
    assert(decel._lastTimestamp == 1250.516);
    assert(decel._currentOffset.y > 100.0);

    printf("DECELERATION_NATIVE_TEST_OK\\n");
    return 0;
}}
"""
        test_bin = PROJECT_ROOT / "tools" / "test_decel_runner"
        src_file = PROJECT_ROOT / "tools" / "test_decel_tmp.c"
        src_file.write_text(c_code, encoding="utf-8")
        try:
            comp = subprocess.run(["clang", "-O2", str(src_file), "-o", str(test_bin), "-lm"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(comp.returncode, 0, f"Clang compile failed:\n{comp.stderr}")
            run_res = subprocess.run([str(test_bin)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(run_res.returncode, 0, f"Decel runner failed:\n{run_res.stderr}")
            self.assertIn("DECELERATION_NATIVE_TEST_OK", run_res.stdout)
        finally:
            if src_file.exists(): src_file.unlink()
            if test_bin.exists(): test_bin.unlink()

    def test_velocity_ring_buffer_wraparound_dedup_and_multitouch_native_execution(self):
        """Adversarial C test: verify circular ring buffer wraparound, duplicate deduplication, and multi-touch centroid."""
        c_code = f"""
#include <stdio.h>
#include <assert.h>
#include <math.h>

#include "{self.vel_pseudo}"

int main(void) {{
    _UIScrollViewVelocity vel;
    vel._sampleIndex = 0;
    vel._sampleCount = 0;
    vel._hasFilteredCoordinate = false;
    vel._cacheTimestamp = 0.0;
    for (int i = 0; i < kVelocityRingBufferCapacity; i++) {{
        vel._samples[i].isValid = false;
    }}

    // Test 1: Insert 12 samples (speed = 1000 pt/s in X), causing 4 wraps in 8-sample buffer
    for (int i = 0; i < 12; i++) {{
        NSTimeInterval t = 1.000 + i * 0.008; // 8ms intervals (125Hz)
        CGPoint pt = (CGPoint){{ i * 8.0, 0.0 }};
        _UIScrollViewVelocity_addSample_atTimestamp(&vel, pt, t);
    }}
    assert(vel._sampleCount == kVelocityRingBufferCapacity);
    assert(vel._sampleIndex == 4); // wrapped to 4

    // Query filtered velocity: must be positive forward velocity ~1000 pt/s
    CGPoint computedV = _UIScrollViewVelocity_filteredVelocity(&vel);
    assert(computedV.x > 800.0 && computedV.x < 1200.0);
    assert(fabs(computedV.y) < 1.0);

    // Test 2: Duplicate timestamp insertion (dt < 1us)
    uint32_t countBefore = vel._sampleCount;
    NSTimeInterval dupT = 1.000 + 11 * 0.008; // duplicate of sample 11
    CGPoint updatedPt = (CGPoint){{ 100.0, 50.0 }};
    _UIScrollViewVelocity_addSample_atTimestamp(&vel, updatedPt, dupT);
    assert(vel._sampleCount == countBefore); // count must not increase

    // Test 3: Multi-touch centroid calculation
    CGPoint touches[3] = {{
        {{ 10.0, 20.0 }},
        {{ 20.0, 40.0 }},
        {{ 30.0, 60.0 }}
    }};
    CGPoint centroid = _UIPanComputeMultiTouchCentroid(touches, 3);
    assert(fabs(centroid.x - 20.0) < 1e-9);
    assert(fabs(centroid.y - 40.0) < 1e-9);

    // Test 4: Stationary pause before lift
    UIPanGestureRecognizer pan;
    pan._velocityTracker = &vel;
    pan._directionalLockEnabled = false;
    pan._view = NULL;
    NSTimeInterval lastT = _UIScrollViewVelocity_lastSampleTimestamp(&vel);
    pan._currentTimestamp = lastT + 0.200; // 200ms pause (> 100ms lookback)
    CGPoint restV = _UIPanGestureRecognizer_velocityInView(&pan, NULL);
    assert(restV.x == 0.0 && restV.y == 0.0);

    // Test 5: Directional lock angle classifier
    _UIScrollViewDirectionalLockAxis lockV = _UIPanDetermineDirectionalLockAxis((CGPoint){{ 10.0, 100.0 }});
    assert(lockV == _UIScrollViewDirectionalLockAxisVertical);
    _UIScrollViewDirectionalLockAxis lockH = _UIPanDetermineDirectionalLockAxis((CGPoint){{ 100.0, 10.0 }});
    assert(lockH == _UIScrollViewDirectionalLockAxisHorizontal);
    _UIScrollViewDirectionalLockAxis lockD = _UIPanDetermineDirectionalLockAxis((CGPoint){{ 50.0, 50.0 }});
    assert(lockD == _UIScrollViewDirectionalLockAxisNone);

    // Test 6: Velocity filter cache hit
    CGPoint vCached1 = _UIScrollViewVelocity_filteredVelocity(&vel);
    CGPoint vCached2 = _UIScrollViewVelocity_filteredVelocity(&vel);
    assert(fabs(vCached1.x - vCached2.x) < 1e-9);
    assert(fabs(vCached1.y - vCached2.y) < 1e-9);

    // Test 7: Cross-axis break hysteresis (40.0 pt perpendicular movement breaks directional lock)
    UIPanGestureRecognizer lockPan;
    lockPan._velocityTracker = &vel;
    lockPan._directionalLockEnabled = true;
    lockPan._view = NULL;
    lockPan._currentTimestamp = lastT;
    lockPan._startPoint = (CGPoint){{ 100.0, 100.0 }};
    lockPan._currentPoint = (CGPoint){{ 105.0, 150.0 }}; // Vertical motion (+5, +50) -> angle ~84 deg >= 60 deg
    lockPan._lockedAxis = _UIScrollViewDirectionalLockAxisNone;

    // First evaluation locks to vertical: horizontal velocity clamped to 0.0
    CGPoint vLocked = _UIPanGestureRecognizer_velocityInView(&lockPan, NULL);
    assert(lockPan._lockedAxis == _UIScrollViewDirectionalLockAxisVertical);
    assert(vLocked.x == 0.0);

    // User now drags horizontally by 45 pt past start (cross-axis break threshold is 40.0 pt)
    lockPan._currentPoint = (CGPoint){{ 145.0, 160.0 }};
    CGPoint vBroken = _UIPanGestureRecognizer_velocityInView(&lockPan, NULL);
    assert(lockPan._lockedAxis == _UIScrollViewDirectionalLockAxisNone);
    // Lock was broken, so horizontal velocity is now unlocked
    assert(vBroken.x > 0.0);

    // Test 8: Repeated duplicate timestamp deduplication preserves EMA state
    _UIScrollViewVelocity dedupVel;
    dedupVel._sampleIndex = 0;
    dedupVel._sampleCount = 0;
    dedupVel._hasFilteredCoordinate = false;
    dedupVel._cacheTimestamp = 0.0;
    for (int i = 0; i < kVelocityRingBufferCapacity; i++) dedupVel._samples[i].isValid = false;

    _UIScrollViewVelocity_addSample_atTimestamp(&dedupVel, (CGPoint){{ 10.0, 0.0 }}, 5.000);
    CGPoint initialPt = dedupVel._samples[0].point;
    // Insert duplicate at 5.000 with same coordinate
    _UIScrollViewVelocity_addSample_atTimestamp(&dedupVel, (CGPoint){{ 10.0, 0.0 }}, 5.000);
    // Insert another duplicate at 5.000
    _UIScrollViewVelocity_addSample_atTimestamp(&dedupVel, (CGPoint){{ 10.0, 0.0 }}, 5.000);
    assert(dedupVel._sampleCount == 1);
    assert(fabs(dedupVel._samples[0].point.x - initialPt.x) < 1e-9);

    printf("VELOCITY_NATIVE_TEST_OK\\n");
    return 0;
}}
"""
        test_bin = PROJECT_ROOT / "tools" / "test_vel_runner"
        src_file = PROJECT_ROOT / "tools" / "test_vel_tmp.c"
        src_file.write_text(c_code, encoding="utf-8")
        try:
            comp = subprocess.run(["clang", "-O2", str(src_file), "-o", str(test_bin), "-lm"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(comp.returncode, 0, f"Clang compile failed:\n{comp.stderr}")
            run_res = subprocess.run([str(test_bin)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(run_res.returncode, 0, f"Velocity runner failed:\n{run_res.stderr}")
            self.assertIn("VELOCITY_NATIVE_TEST_OK", run_res.stdout)
        finally:
            if src_file.exists(): src_file.unlink()
            if test_bin.exists(): test_bin.unlink()

    def test_spring_settling_duration_edge_cases_native_execution(self):
        """Adversarial C test: verify spring settling duration sub-epsilon settling and closed-form ODE."""
        c_code = f"""
#include <stdio.h>
#include <assert.h>
#include <math.h>

void *objc_msgSend(void *self, const char *sel, ...) {{ return NULL; }}

#include "{self.spring_pseudo}"

int main(void) {{
    // Test 1: Sub-epsilon displacement (initialDisplacement <= 0.001) must return 0.0 (already settled)
    double settleZero = CASpringAnimation_settlingDuration(1.0, 100.0, 18.0, 0.0005);
    assert(settleZero == 0.0);

    // Test 2: Standard overshoot (50 pt): epsilon = 0.001 -> -ln(0.001/50)/9.0 = 1.202s
    double settleStd = CASpringAnimation_settlingDuration(1.0, 100.0, 18.0, 50.0);
    assert(settleStd > 1.000 && settleStd < 1.500);

    // Test 3: Evaluates 1D spring at t=0
    _UIScrollViewSpringAnimation spring;
    spring._mass = 1.0;
    spring._stiffness = 100.0;
    spring._damping = 18.0;
    _UIScrollViewSpringConfigureDynamics(&spring);

    double x_out = 0.0, v_out = 0.0;
    _UIScrollViewEvaluate1DSpring(&spring, 50.0, -100.0, 0.0, &x_out, &v_out);
    assert(fabs(x_out - 50.0) < 1e-9);
    assert(fabs(v_out - (-100.0)) < 1e-9);

    // Test 4: Velocity-aware settling duration with zero displacement and 1000 pt/s kinetic impact
    double settleKinet = CASpringAnimation_settlingDurationWithVelocity(1.0, 100.0, 18.0, 0.0, 1000.0);
    assert(settleKinet > 1.000 && settleKinet < 1.600); // ~1.37s

    // Test 5: CADisplayLink spring display link tick
    CADisplayLink slink;
    slink.timestamp = 0.000;
    slink.targetTimestamp = 0.016667;
    spring._scrollView = NULL;
    spring._isCancelled = true;
    _UIScrollViewSpringDisplayLinkTick(&slink, &spring);

    // Test 6: CASpringAnimation_durationForEpsilon monotonicity
    double durEps1 = CASpringAnimation_durationForEpsilon(1.0, 100.0, 18.0, 50.0, 0.01);
    double durEps2 = CASpringAnimation_durationForEpsilon(1.0, 100.0, 18.0, 50.0, 0.001);
    double durEps3 = CASpringAnimation_durationForEpsilon(1.0, 100.0, 18.0, 50.0, 0.0001);
    assert(durEps3 > durEps2 && durEps2 > durEps1);

    // Test 7: Critically damped regime (zeta == 1.0, c = 20.0 N*s/m)
    double durCrit = CASpringAnimation_settlingDuration(1.0, 100.0, 20.0, 50.0);
    assert(durCrit > 1.000 && durCrit < 2.000);
    // At t = durCrit, position must have settled to within epsilon (0.001)
    double xCrit = exp(-10.0 * durCrit) * (50.0 + (0.0 + 10.0 * 50.0) * durCrit);
    assert(fabs(xCrit) <= 0.001 + 1e-6);

    // Test 8: Overdamped regime (zeta == 2.5, c = 50.0 N*s/m)
    double durOver = CASpringAnimation_settlingDuration(1.0, 100.0, 50.0, 50.0);
    // Slow decay root alpha1 = 25 - sqrt(525) ~ 2.087 rad/s requires > 3.5s to reach 0.001
    assert(durOver > 3.500 && durOver < 6.000);
    _UIScrollViewSpringAnimation springOver;
    springOver._mass = 1.0;
    springOver._stiffness = 100.0;
    springOver._damping = 50.0;
    _UIScrollViewSpringConfigureDynamics(&springOver);
    double xOver = 0.0, vOver = 0.0;
    _UIScrollViewEvaluate1DSpring(&springOver, 50.0, 0.0, durOver, &xOver, &vOver);
    assert(fabs(xOver) <= 0.001 + 1e-4);

    // Test 9: Spring stepping with dynamic display scale (@2x Retina snapping)
    UIScrollView sView;
    sView._displayScale = 2.0;
    sView._scrollViewFlags.isDecelerating = 1;
    sView._scrollViewFlags.delegateScrollViewDidEndDecel = 0;
    sView._delegate = NULL;
    spring._scrollView = &sView;
    spring._initialDisplacement = (CGPoint){{ 10.333, 0.0 }};
    spring._initialVelocity = (CGPoint){{ 0.0, 0.0 }};
    spring._equilibriumOffset = (CGPoint){{ 0.0, 0.0 }};
    spring._isCancelled = false;
    spring._startTimestamp = 1.000;
    _UIScrollViewStepSpring(&spring, 1.010);
    double rem2x = fmod(sView._contentOffset.x * 2.0, 1.0);
    assert(fabs(rem2x) < 1e-6 || fabs(rem2x - 1.0) < 1e-6);

    // Test 10: Spring start timestamp baseline synchronization (uptime > 0.500s)
    spring._startTimestamp = 0.0;
    _UIScrollViewSpringAnimation_updatePosition_timestamp(&spring, 1250.500);
    assert(spring._startTimestamp == 1250.500);

    printf("SPRING_NATIVE_TEST_OK\\n");
    return 0;
}}
"""
        test_bin = PROJECT_ROOT / "tools" / "test_spring_runner"
        src_file = PROJECT_ROOT / "tools" / "test_spring_tmp.c"
        src_file.write_text(c_code, encoding="utf-8")
        try:
            comp = subprocess.run(["clang", "-O2", str(src_file), "-o", str(test_bin), "-lm"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(comp.returncode, 0, f"Clang compile failed:\n{comp.stderr}")
            run_res = subprocess.run([str(test_bin)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(run_res.returncode, 0, f"Spring runner failed:\n{run_res.stderr}")
            self.assertIn("SPRING_NATIVE_TEST_OK", run_res.stdout)
        finally:
            if src_file.exists(): src_file.unlink()
            if test_bin.exists(): test_bin.unlink()


if __name__ == "__main__":
    unittest.main()
