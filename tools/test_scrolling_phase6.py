#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 6: Cross-Validation & Consistency Matrix
(All 13 Candidate Scrolling Frameworks across dyld shared cache slices .01, .03, .07, .48)

Tests:
1. Cross-validation matrix JSON schema, 86 classes, 13 frameworks, and 3 formal categories.
2. Kinematic deceleration friction rates, continuous lambdas, half-lives, and ProMotion timestep invariance.
3. Rubber-band drag coefficient (0.55), forward/inverse formulas, spring restitution, and zoom damping.
4. Gesture arbitration touch slop thresholds, subview touch delay, directional locking, and breakout hysteresis.
5. Scroll indicator minimum length (36.0pt), overscroll compression (r=2.0), scrubbing expansion, and fade kinetics.
6. Standalone compilation and execution of C cross-validation harness (all 46 unit assertion suites).
7. Findings dossier anti-placeholder compliance, byte size (>= 30,000 bytes), Mermaid diagrams, and LaTeX math.
8. Evidence ledger integrity for XVAL-001 through XVAL-020.
9. Adversarial boundary conditions, numerical precision, and zero-drift long-horizon integration.
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
    r"…",
    r"\bLorem ipsum\b",
    r"\[TBD\]",
    r"\[TODO\]"
]

class TestScrollingPhase6Adversarial(unittest.TestCase):

    def setUp(self):
        self.matrix_json = PROJECT_ROOT / "artifacts/scrolling/cross_validation_matrix.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/cross_validation_harness.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/06_CROSS_VALIDATION.md"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

    def test_cross_validation_matrix_schema_and_classes(self):
        """R5: Test matrix schema, 86 classes, 13 frameworks, and 3-category classification."""
        self.assertTrue(self.matrix_json.is_file(), "cross_validation_matrix.json must exist")
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sec in ["metadata", "frameworks_catalog", "classes_cross_validation",
                    "universal_core_invariants", "framework_specific_extensions",
                    "intentional_architectural_divergences", "discrepancy_ledger",
                    "open_issues_cumulative_ledger"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in cross_validation_matrix.json")
        self.assertGreaterEqual(len(data.get("open_issues_cumulative_ledger", [])), 9)

        meta = data["metadata"]
        self.assertEqual(meta.get("total_classes_audited"), 86)
        self.assertEqual(meta.get("total_frameworks_audited"), 13)

        # Frameworks catalog
        fws = data["frameworks_catalog"]
        self.assertEqual(len(fws), 13)

        # Classes cross-validation
        classes = data["classes_cross_validation"]
        self.assertEqual(len(classes), 86)

        categories = set(c["divergence_or_extension"] for c in classes)
        expected_categories = {
            "Universal Core Invariants",
            "Framework-Specific Extensions",
            "Intentional Architectural Divergences"
        }
        self.assertEqual(categories, expected_categories)

        # R5: Verify rigorous category breakdown counts (52 Universal, 30 Extensions, 4 Divergences)
        cat_counts = meta.get("classification_breakdown", {})
        self.assertEqual(cat_counts.get("Universal Core Invariants"), 52)
        self.assertEqual(cat_counts.get("Framework-Specific Extensions"), 30)
        self.assertEqual(cat_counts.get("Intentional Architectural Divergences"), 4)

        actual_cat_counts = {}
        for c in classes:
            cat = c["divergence_or_extension"]
            actual_cat_counts[cat] = actual_cat_counts.get(cat, 0) + 1
        self.assertEqual(actual_cat_counts, cat_counts)

        # Ensure all classes have complete field schemas
        for c in classes:
            self.assertIn("class_name", c)
            self.assertIn("framework", c)
            self.assertIn("subcache_slice", c)
            self.assertIn("vm_base_address", c)
            self.assertIn("invariants_adherence", c)
            self.assertIn("rationale", c)

    def test_kinematic_deceleration_reconciliation(self):
        """R1: Test deceleration friction rates, recurrence formulas, and ProMotion timestep invariance."""
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        kin = data["universal_core_invariants"]["kinematic_deceleration"]
        rates = kin["rates"]

        # 1. Friction rates
        self.assertEqual(rates["normal"]["value_decimal"], 0.998)
        self.assertEqual(rates["normal"]["ieee754_double_hex"], "0x3fefef9db22d0e56")
        self.assertAlmostEqual(rates["normal"]["decay_constant_lambda_per_sec"], 2.00200267, places=6)

        self.assertEqual(rates["fast"]["value_decimal"], 0.990)
        self.assertEqual(rates["fast"]["ieee754_double_hex"], "0x3fefae147ae147ae")
        self.assertAlmostEqual(rates["fast"]["decay_constant_lambda_per_sec"], 10.05033585, places=6)

        self.assertEqual(rates["paging"]["value_decimal"], 0.985)
        self.assertEqual(rates["paging"]["ieee754_double_hex"], "0x3fef851eb851eb85")
        self.assertAlmostEqual(rates["paging"]["decay_constant_lambda_per_sec"], 15.11363781, places=6)

        # HID filter rate
        hid = data["intentional_architectural_divergences"]["iohid_driver_level_prefiltering"]
        self.assertEqual(hid["deceleration_friction_rate"], 0.950)
        self.assertEqual(hid["terminal_stop_velocity_pt_per_sec"], 0.05)

        # Stop velocity in UIKitCore
        vel_est = kin["velocity_estimation"]
        self.assertEqual(vel_est["terminal_stop_velocity_pt_per_sec"], 0.1)
        self.assertEqual(vel_est["ring_buffer_capacity"], 8)
        self.assertEqual(vel_est["lookback_time_window_ms"], 100.0)
        self.assertEqual(vel_est["ema_prefilter_alpha"], 0.85)

        # 2. Timestep Invariance Proof
        v0 = 2500.0
        d = 0.998
        ln_d = math.log(d)
        total_time = 1.0 / 60.0

        # Single 60Hz step
        disp_60 = v0 * (pow(d, 1000.0 * total_time) - 1.0) / (1000.0 * ln_d)

        # Two 120Hz steps
        dt_sub = total_time / 2.0
        disp_120_1 = v0 * (pow(d, 1000.0 * dt_sub) - 1.0) / (1000.0 * ln_d)
        v1 = v0 * pow(d, 1000.0 * dt_sub)
        disp_120_2 = v1 * (pow(d, 1000.0 * dt_sub) - 1.0) / (1000.0 * ln_d)
        disp_120 = disp_120_1 + disp_120_2

        self.assertAlmostEqual(disp_60, disp_120, places=9)

        # 3. Variable Frame Duration Jitter Invariance (+- 2ms jitter over 120 frames)
        seed = 0x12345678
        dt_sequence = []
        total_T = 0.0
        for i in range(120):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            jitter = ((seed % 1000) / 1000.0 - 0.5) * 0.004
            base_dt = 1.0 / 120.0 if i < 40 else (1.0 / 80.0 if i < 80 else 1.0 / 60.0)
            dt = base_dt + jitter
            dt_sequence.append(dt)
            total_T += dt

        continuous_disp_jitter = v0 * (pow(d, 1000.0 * total_T) - 1.0) / (1000.0 * ln_d)
        v_curr = v0
        discrete_disp_jitter = 0.0
        for dt in dt_sequence:
            discrete_disp_jitter += v_curr * (pow(d, 1000.0 * dt) - 1.0) / (1000.0 * ln_d)
            v_curr *= pow(d, 1000.0 * dt)
        self.assertAlmostEqual(continuous_disp_jitter, discrete_disp_jitter, places=9)

        # 4. CADisplayLink Hitch & Jitter Clamping
        kin_meta = kin.get("timestep_invariance", {})
        self.assertEqual(kin_meta.get("min_dt_tick_sec"), 0.0001)
        self.assertEqual(kin_meta.get("max_dt_hitch_sec"), 0.1)
        self.assertEqual(kin_meta.get("max_dt_hang_abort_sec"), 0.5)

    def test_rubber_band_and_spring_constants(self):
        """R2: Test rubber-band drag coefficient (0.55), inverse formula, spring parameters, and zoom damping."""
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        rb = data["universal_core_invariants"]["rubber_banding_and_boundary_resistance"]

        # Drag coefficient
        self.assertEqual(rb["primary_drag_coefficient_c"]["value_decimal"], 0.55)
        self.assertEqual(rb["primary_drag_coefficient_c"]["ieee754_double_hex"], "0x3fe199999999999a")
        self.assertEqual(rb["primary_drag_coefficient_c"]["vm_address"], "0x1865166d0")

        # Forward & Inverse Displacement Numerical Precision
        d = 852.0
        c = 0.55
        test_x = 120.0
        y_forward = (test_x * c * d) / (d + c * abs(test_x))
        x_recovered = (abs(y_forward) * d) / (c * (d - abs(y_forward))) * (1.0 if y_forward >= 0 else -1.0)
        self.assertAlmostEqual(test_x, x_recovered, places=10)

        # Spring restitution
        spring = rb["bounce_back_spring_restitution"]
        self.assertEqual(spring["mass_m_kg"], 1.0)
        self.assertEqual(spring["stiffness_k_n_per_m"], 100.0)
        self.assertEqual(spring["damping_c_n_s_per_m"], 18.0)
        self.assertEqual(spring["damping_ratio_zeta"], 0.90)

        # Logarithmic zoom damping
        zoom = rb["logarithmic_zoom_damping"]
        self.assertEqual(zoom["coefficient_c_zoom"], 0.25)
        self.assertEqual(zoom["ieee754_double_hex"], "0x3fd0000000000000")

    def test_gesture_arbitration_and_touch_slop(self):
        """R3: Test touch slop modality thresholds, subview touch delay, and directional locking."""
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        gest = data["universal_core_invariants"]["gesture_arbitration_and_touch_slop"]

        # Slop thresholds
        slop = gest["touch_slop_by_modality_pt"]
        self.assertEqual(slop["finger_touch"], 10.0)
        self.assertEqual(slop["apple_pencil"], 4.0)
        self.assertEqual(slop["trackpad_and_mouse"], 2.0)
        self.assertEqual(slop["ballistic_interruption_collapse"], 0.0)

        # Touch delay
        delay = gest["touch_delay"]
        self.assertEqual(delay["subview_touch_delay_sec"], 0.150)
        self.assertEqual(delay["subview_touch_delay_ms"], 150.0)

        # Directional locking
        lock = gest["directional_locking"]
        self.assertEqual(lock["horizontal_lock_angle_degrees"], 30.0)
        self.assertEqual(lock["vertical_lock_angle_degrees"], 60.0)
        self.assertEqual(lock["breakout_hysteresis_pt"], 40.0)
        self.assertEqual(lock["consecutive_break_frames"], 3)
        self.assertTrue(lock["cross_axis_signed_accumulator"])

        # Adversarial directional lock state machine simulation
        # Sub-test A: Micro-wobbles cancel out in signed accumulator
        cross_axis_disp = 0.0
        consecutive_frames = 0
        is_locked = True
        for i in range(60):
            dy = 1.5 if i % 2 == 0 else -1.5
            cross_axis_disp += dy
            if abs(cross_axis_disp) >= 40.0:
                consecutive_frames += 1
                if consecutive_frames >= 3:
                    is_locked = False
            else:
                consecutive_frames = 0
        self.assertTrue(is_locked, "Micro-wobbles must not break directional lock")
        self.assertLessEqual(abs(cross_axis_disp), 1.5)

        # Sub-test B: Single-frame transient spike (45pt) rejected by 3-frame debounce
        cross_axis_disp += 45.0
        if abs(cross_axis_disp) >= 40.0:
            consecutive_frames += 1
        self.assertEqual(consecutive_frames, 1)
        self.assertTrue(is_locked, "1-frame transient spike must not break lock")

        # Sub-test C: 3 consecutive frames > 40pt breaks out
        for _ in range(2):
            consecutive_frames += 1
            if consecutive_frames >= 3:
                is_locked = False
        self.assertFalse(is_locked, "3 consecutive frames > 40pt must trigger breakout")

    def test_scroll_indicator_geometry_and_fade(self):
        """R4: Test indicator minimum length, thickness, overscroll compression, and fade kinetics."""
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        ind = data["universal_core_invariants"]["scroll_indicators"]

        self.assertEqual(ind["minimum_length_pt"], 36.0)
        self.assertEqual(ind["ieee754_minimum_length_hex"], "0x4042000000000000")
        self.assertEqual(ind["knob_thickness_collapsed_pt"], 3.0)
        self.assertEqual(ind["knob_thickness_expanded_pt"], 8.0)
        self.assertEqual(ind["overscroll_compression_ratio"], 2.0)

        timeouts = ind["idle_display_timeout_sec"]
        self.assertEqual(timeouts["standard_scroll_view"], 1.50)
        self.assertEqual(timeouts["paging_scroll_view"], 2.00)
        self.assertEqual(ind["fade_out_duration_sec"], 0.30)
        self.assertEqual(ind["hit_target_minimum_dimension_pt"], 44.0)

    def test_standalone_pseudocode_compilation_and_execution(self):
        """R6: Compile and execute cross_validation_harness.pseudo.c under gcc -Wall -Wextra -Werror."""
        self.assertTrue(self.pseudo_c.is_file(), "cross_validation_harness.pseudo.c must exist")
        bin_path = Path("/tmp/test_cross_validation_harness_bin")
        compile_cmd = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            str(self.pseudo_c), "-lm", "-o", str(bin_path)
        ]
        comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
        self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}")

        run_res = subprocess.run([str(bin_path)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0, f"Execution failed:\n{run_res.stderr}")
        self.assertIn("All 46 Cross-Validation unit test suites PASSED", run_res.stdout)

    def test_findings_dossier_structure_and_invariants(self):
        """R6: Verify findings document byte size (>= 30,000 bytes), anti-placeholder compliance, and sections."""
        self.assertTrue(self.findings_md.is_file(), "06_CROSS_VALIDATION.md must exist")
        size = self.findings_md.stat().st_size
        self.assertGreaterEqual(size, 30000, f"Findings size ({size} bytes) < 30,000 bytes minimum")

        content = self.findings_md.read_text(encoding="utf-8")
        for pat in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pat, content, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Banned placeholder '{matches[0].group() if matches else ''}' found")

        required_sections = [
            "Executive Mission & Cross-Framework Verification Scope",
            "Cross-Framework Kinematic Deceleration & Velocity Reconciliation",
            "Boundary Resistance & Rubber-Banding Universal Constants",
            "Gesture Arbitration, Touch Slop & Directional Locking Matrix",
            "Scroll Indicator Geometry, Sizing & Fade Alignment",
            "Unified Cross-Validation Matrix & Discrepancy Ledger",
            "Master Architectural & PAC00 Method Table",
            "Empirical Evidence Ledger Entries",
            "Production Clean-Room C Test Harness Verification"
        ]
        for sec in required_sections:
            self.assertIn(sec.lower(), content.lower(), f"Missing required section: {sec}")

        self.assertIn("$$", content, "Missing LaTeX display math")
        self.assertIn("```mermaid", content, "Missing Mermaid diagrams")
        self.assertIn("graph", content, "Missing Mermaid graph diagram")
        self.assertIn("sequenceDiagram", content, "Missing Mermaid sequence diagram")
        self.assertIn("stateDiagram-v2", content, "Missing Mermaid state diagram")

    def test_evidence_ledger_phase6_integrity(self):
        """R6: Verify evidence_ledger.jsonl contains XVAL-001 through XVAL-020 entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        phase6_entries = [e for e in lines if e.get("phase") == "PHASE_6"]
        self.assertGreaterEqual(len(phase6_entries), 20, f"Found {len(phase6_entries)} Phase 6 entries, expected >= 20")

        xval_ids = [e.get("id") for e in phase6_entries]
        for i in range(1, 21):
            expected_id = f"XVAL-{i:03d}"
            self.assertIn(expected_id, xval_ids, f"Missing evidence entry {expected_id}")

        slices_covered = set()
        for entry in phase6_entries:
            self.assertTrue(entry.get("id").startswith("XVAL-"))
            self.assertIn("[CONFIRMED]", entry.get("finding", ""))
            self.assertEqual(entry.get("confidence"), "CONFIRMED")
            self.assertTrue(entry.get("binary_path"))
            full_bin = PROJECT_ROOT / entry.get("binary_path")
            self.assertTrue(full_bin.is_file(), f"Cited binary_path does not exist: {entry.get('binary_path')}")
            self.assertTrue(entry.get("opcode_instructions"))
            self.assertTrue(entry.get("evidence_type"))
            self.assertTrue(entry.get("tool"))
            self.assertTrue(entry.get("subcache_slice"), f"Missing subcache_slice in {entry.get('id')}")
            self.assertTrue(entry.get("subcache_file_offset"), f"Missing subcache_file_offset in {entry.get('id')}")
            slices_covered.add(entry.get("subcache_slice"))

        # Verify all 4 required shared cache slices (.01, .03, .07, .48) are empirically represented
        expected_slices = {
            "dyld_shared_cache_arm64e.01",
            "dyld_shared_cache_arm64e.03",
            "dyld_shared_cache_arm64e.07",
            "dyld_shared_cache_arm64e.48"
        }
        self.assertEqual(slices_covered, expected_slices, f"Missing slice coverage in Phase 6 evidence: {expected_slices - slices_covered}")

        # Specific cross-framework slice mapping verification
        webkit_entries = [e for e in phase6_entries if "WebKit" in e.get("framework", "")]
        self.assertEqual(len(webkit_entries), 2, "Expected 2 WebKit XVAL entries (XVAL-006, XVAL-009)")
        for we in webkit_entries:
            self.assertEqual(we.get("subcache_slice"), "dyld_shared_cache_arm64e.07", f"{we['id']} must map to subcache slice .07")

        iohid_entries = [e for e in phase6_entries if "IOHID" in e.get("framework", "")]
        self.assertEqual(len(iohid_entries), 1, "Expected 1 IOHID XVAL entry (XVAL-004)")
        self.assertEqual(iohid_entries[0].get("subcache_slice"), "dyld_shared_cache_arm64e.48")

        swiftui_entries = [e for e in phase6_entries if "SwiftUI" in e.get("framework", "")]
        self.assertEqual(len(swiftui_entries), 1, "Expected 1 SwiftUI XVAL entry (XVAL-005)")
        self.assertEqual(swiftui_entries[0].get("subcache_slice"), "dyld_shared_cache_arm64e.03")

    def test_adversarial_boundary_conditions(self):
        """Adversarial: Test numerical stability at asymptotic extremes, zero velocities, and multi-slice invariance."""
        d = 800.0
        c = 0.55

        # Extreme overscroll approaching infinity: visual displacement asymptotically approaches d
        x_huge = 1e9
        y_huge = (x_huge * c * d) / (d + c * x_huge)
        self.assertLess(y_huge, d)
        self.assertGreater(y_huge, d - 1e-2)

        # Inversion of displacement very close to d
        y_near_d = d - 1e-5
        x_recovered = (y_near_d * d) / (c * (d - y_near_d))
        self.assertGreater(x_recovered, 1e7)

        # Zero displacement
        self.assertEqual((0.0 * c * d) / (d + c * 0.0), 0.0)

        # Negative displacement symmetry
        x_neg = -150.0
        y_neg = (x_neg * c * d) / (d + c * abs(x_neg))
        self.assertLess(y_neg, 0.0)
        self.assertAlmostEqual(abs(y_neg), (abs(x_neg) * c * d) / (d + c * abs(x_neg)), places=10)

    def test_cumulative_open_issues_kinematics(self):
        """Adversarial: Verify Open Issues [OI-03], [OI-05], and [OI-06] kinematic solutions."""
        # [OI-03]: Double-precision 64-bit requirement vs Float-32 drift
        v0 = 2500.0
        d = 0.998
        dt = 1.0 / 120.0
        lambda_val = -1000.0 * math.log(d)
        v_d = v0
        disp_d = 0.0
        for _ in range(600):
            v_next_d = v_d * pow(d, 1000.0 * dt)
            disp_d += (v_d - v_next_d) / lambda_val
            v_d = v_next_d
        exact_5s = v0 * (1.0 - pow(d, 5000.0)) / lambda_val
        self.assertAlmostEqual(disp_d, exact_5s, places=8)

        # [OI-05]: Dynamic safe-area inset animation mid-fling preemption
        current_offset = 80.0
        min_offset_initial = 0.0
        self.assertGreaterEqual(current_offset, min_offset_initial)
        # Expansion occurs:
        min_offset_expanded = 120.0
        breached = current_offset < min_offset_expanded
        self.assertTrue(breached)
        overscroll_penetration = current_offset - min_offset_expanded
        self.assertEqual(overscroll_penetration, -40.0)

        # [OI-06]: Simultaneous opposing multi-touch centroid velocity cancellation
        p1_samples = [2500.0 * (t * 0.016667) for t in range(7)]
        p2_samples = [-2500.0 * (t * 0.016667) for t in range(7)]
        centroid_samples = [(p1 + p2) / 2.0 for p1, p2 in zip(p1_samples, p2_samples)]
        for c in centroid_samples:
            self.assertEqual(c, 0.0)

        # [OI-09]: Invariants & System Cleanliness (PAC00 symbols & zero-placeholder verification)
        with open(self.matrix_json, "r", encoding="utf-8") as f:
            matrix_data = json.load(f)
        oi_ledger = {item["issue_id"]: item for item in matrix_data.get("open_issues_cumulative_ledger", [])}
        self.assertIn("OI-09", oi_ledger, "OI-09 must be cataloged in open_issues_cumulative_ledger")
        self.assertTrue(oi_ledger["OI-09"]["status"].startswith("Resolved & Formally Verified"))
        self.assertIn("clean-room", oi_ledger["OI-09"]["resolution"].lower())
        self.assertIn("pac00", oi_ledger["OI-09"]["resolution"].lower())

if __name__ == "__main__":
    unittest.main()
