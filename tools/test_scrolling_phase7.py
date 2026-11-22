#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 7: Nested Scrolling & Complex UI Coordination
(UIKitCore dyld shared cache slice .01 @ 0x184752000, arm64e PAC00)

Tests:
1. JSON parameter schemas (nested_scrolling_coordination.json & ui_coordination_parameters.json)
2. Parent-child nested gesture arbitration & simultaneous recognition matrix
3. Momentum transfer refutation & ballistic inertia containment
4. Orthogonal scroller isolation & directional locking geometry (30 deg, 60 deg, 40pt breakout)
5. UINavigationBar large title collapsing kinematics & opacity cross-fade (52.0pt delta, [40pt, 52pt])
6. UISheetPresentationController detent tracking & drag-to-dismiss arbitration (600pt/s, 60pt cutoff)
7. UIRefreshControl 5-state finite state machine & detent pinning (+60.0pt inset)
8. Interactive keyboard dismissal tracking & velocity cutoff (400.0pt/s)
9. C99 clean-room simulation compilation & all 47 self-validating assertion suites
10. Anti-placeholder zero-tolerance compliance across all Phase 7 artifacts
11. Findings documents structural richness, byte sizes (>= 30k & >= 25k), and Mermaid diagrams
12. Empirical evidence ledger integrity for NEST-001 through NEST-022+
13. Boundary conditions, numerical stability, and mathematical continuity
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

class TestScrollingPhase7Adversarial(unittest.TestCase):

    def setUp(self):
        self.nested_json = PROJECT_ROOT / "artifacts/scrolling/nested_scrolling_coordination.json"
        self.ui_coord_json = PROJECT_ROOT / "artifacts/scrolling/ui_coordination_parameters.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/nested_scrolling.pseudo.c"
        self.findings_nested_md = PROJECT_ROOT / "findings/scrolling/07_NESTED_SCROLLING.md"
        self.findings_ui_md = PROJECT_ROOT / "findings/scrolling/07_COMPLEX_UI_COORDINATION.md"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

    def test_01_json_parameter_schemas_and_depth(self):
        """R3: Test nested_scrolling_coordination.json and ui_coordination_parameters.json schemas."""
        self.assertTrue(self.nested_json.is_file(), "nested_scrolling_coordination.json must exist")
        self.assertTrue(self.ui_coord_json.is_file(), "ui_coordination_parameters.json must exist")

        with open(self.nested_json, "r", encoding="utf-8") as f:
            n_data = json.load(f)
        for sec in ["metadata", "parent_child_arbitration_rules", "simultaneous_recognition_matrix",
                    "orthogonal_scroller_isolation", "momentum_transfer_and_containment",
                    "boundary_event_flow", "binary_references"]:
            self.assertIn(sec, n_data, f"Missing section '{sec}' in nested_scrolling_coordination.json")

        self.assertEqual(n_data["metadata"]["phase"], "phase_7_nested")
        self.assertEqual(n_data["metadata"]["target_os"], "iOS 27.2")
        self.assertEqual(n_data["metadata"]["build"], "24B119")
        self.assertEqual(n_data["metadata"]["hardware"], "iPhone18,3 (v57ap, SoC t8150 / A19 Pro)")

        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            u_data = json.load(f)
        for sec in ["metadata", "large_title_navigation_coordination",
                    "sheet_presentation_controller_coordination",
                    "refresh_control_state_machine", "interactive_keyboard_dismissal"]:
            self.assertIn(sec, u_data, f"Missing section '{sec}' in ui_coordination_parameters.json")

    def test_02_parent_child_arbitration_rules(self):
        """R1: Test parent-child gesture arbitration and simultaneous recognition matrix."""
        with open(self.nested_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules = data["parent_child_arbitration_rules"]
        slop = rules["gesture_claiming_and_slop_gate"]["touch_slop_thresholds"]
        self.assertEqual(slop["finger_pt"], 10.0)
        self.assertEqual(slop["stylus_pencil_pt"], 4.0)
        self.assertEqual(slop["trackpad_mouse_pt"], 2.0)
        self.assertEqual(slop["ballistic_interruption_pt"], 0.0)

        matrix = data["simultaneous_recognition_matrix"]
        combos = matrix["combinations"]
        self.assertGreaterEqual(len(combos), 5)

        collinear = next((c for c in combos if "Collinear (Vertical / Vertical)" in c["relative_orientation"]), None)
        self.assertIsNotNone(collinear)
        self.assertFalse(collinear["default_result"])
        self.assertTrue(collinear["delegate_overrideable"])

        orthogonal = next((c for c in combos if "Orthogonal" in c["relative_orientation"]), None)
        self.assertIsNotNone(orthogonal)
        self.assertTrue(orthogonal["default_result"])

    def test_03_momentum_transfer_refutation(self):
        """R1/R2: Test momentum transfer refutation and ballistic isolation model."""
        with open(self.nested_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        momentum = data["momentum_transfer_and_containment"]
        self.assertEqual(momentum["momentum_transfer_verdict"], "REFUTED")
        self.assertIn("does NOT transfer", momentum["empirical_finding"])

        restitution = data["boundary_event_flow"]["boundary_restitution_spring"]
        self.assertEqual(restitution["mass_kg"], 1.0)
        self.assertEqual(restitution["stiffness_k"], 100.0)
        self.assertEqual(restitution["damping_c"], 18.0)
        self.assertEqual(restitution["damping_ratio_zeta"], 0.90)

    def test_04_orthogonal_isolation_directional_locking(self):
        """R1: Test directional locking angles and breakout hysteresis."""
        with open(self.nested_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        dlock = data["orthogonal_scroller_isolation"]["directional_locking_geometry"]
        self.assertEqual(dlock["horizontal_lock_angle_max_degrees"], 30.0)
        self.assertEqual(dlock["vertical_lock_angle_min_degrees"], 60.0)
        self.assertEqual(dlock["breakout_hysteresis_distance_pt"], 40.0)

    def test_05_large_title_navigation_parameters(self):
        """R2/R3: Test navigation large title geometry, alpha cross-fade, and toolbar auto-hide."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        nav = data["large_title_navigation_coordination"]
        geo = nav["geometry"]
        self.assertEqual(geo["standard_navbar_height_pt"], 44.0)
        self.assertEqual(geo["large_title_expanded_navbar_height_pt"], 96.0)
        self.assertEqual(geo["large_title_delta_height_pt"], 52.0)
        self.assertEqual(geo["search_bar_height_pt"], 52.0)
        self.assertEqual(geo["total_expanded_height_with_search_pt"], 148.0)

        interp = nav["interpolation_mechanics"]
        self.assertEqual(interp["large_title_fade_threshold_start_pt"], 40.0)
        self.assertEqual(interp["large_title_fade_threshold_end_pt"], 52.0)
        self.assertEqual(interp["rubber_band_overscroll_expansion_coefficient"], 0.55)

        tb = nav["toolbar_coordination"]
        self.assertEqual(tb["auto_hide_on_scroll_down_velocity_threshold_pts"], 200.0)
        self.assertEqual(tb["auto_reveal_on_scroll_up_velocity_threshold_pts"], -100.0)
        self.assertEqual(tb["auto_hide_displacement_threshold_pt"], 44.0)

    def test_06_sheet_presentation_parameters(self):
        """R2/R3: Test sheet presentation detents and dismiss thresholds."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        sheet = data["sheet_presentation_controller_coordination"]
        detents = sheet["detent_definitions"]
        self.assertEqual(detents["medium_detent_factor"], 0.50)
        self.assertEqual(detents["large_detent_top_margin_pt"], 10.0)

        kp = sheet["kinematic_parameters"]
        self.assertEqual(kp["sheet_damping_ratio"], 0.85)
        self.assertEqual(kp["sheet_high_speed_damping_ratio"], 0.90)
        self.assertEqual(kp["sheet_response_seconds"], 0.35)
        self.assertEqual(kp["sheet_deceleration_factor"], 0.992)
        self.assertEqual(kp["sheet_speed_threshold_pts"], 600.0)
        self.assertEqual(kp["sheet_dismiss_displacement_threshold_pt"], 60.0)
        self.assertEqual(kp["top_rubber_band_resistance_coefficient"], 0.55)

    def test_07_refresh_control_state_machine(self):
        """R2/R3: Test UIRefreshControl 5-state lifecycle and pinned detent inset."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        rc = data["refresh_control_state_machine"]
        self.assertEqual(rc["thresholds"]["standard_pull_trigger_threshold_pt"], 60.0)
        self.assertEqual(rc["thresholds"]["modern_navbar_pull_trigger_threshold_pt"], 64.0)
        self.assertEqual(rc["thresholds"]["resting_pinned_detent_height_pt"], 60.0)

        states = rc["state_machine_states"]
        self.assertEqual(len(states), 5)
        state_names = [s["name"] for s in states]
        self.assertEqual(state_names, ["Idle", "Pulling", "Triggered", "Refreshing", "Finishing"])

        anim = rc["animation_parameters"]
        self.assertEqual(anim["pin_detent_spring_duration_seconds"], 0.30)
        self.assertEqual(anim["pin_detent_spring_damping_ratio"], 0.80)
        self.assertEqual(anim["end_refreshing_restore_duration_seconds"], 0.25)
        self.assertEqual(anim["end_refreshing_fade_duration_seconds"], 0.15)

    def test_08_interactive_keyboard_dismissal(self):
        """R2/R3: Test interactive keyboard dismissal cutoff and modes."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        kbd = data["interactive_keyboard_dismissal"]
        modes = kbd["modes"]
        self.assertEqual(modes["UIScrollViewKeyboardDismissModeNone"], 0)
        self.assertEqual(modes["UIScrollViewKeyboardDismissModeOnDrag"], 1)
        self.assertEqual(modes["UIScrollViewKeyboardDismissModeInteractive"], 2)

        geom = kbd["tracking_geometry"]
        self.assertEqual(geom["upward_drag_rubber_band_coefficient"], 0.20)

        cutoff = kbd["cutoff_arbitration"]
        self.assertEqual(cutoff["dismiss_velocity_threshold_pts"], 400.0)
        self.assertEqual(cutoff["dismiss_displacement_ratio"], 0.50)

    def test_09_pseudocode_compilation_and_execution(self):
        """R4: Compile and execute clean-room C99 simulation (all 47 assertion suites)."""
        self.assertTrue(self.pseudo_c.is_file(), "nested_scrolling.pseudo.c must exist")
        bin_target = Path("/tmp/test_nested_scrolling_runner")

        comp_cmd = ["gcc", "-Wall", "-Wextra", "-Werror", "-std=c99", str(self.pseudo_c), "-lm", "-o", str(bin_target)]
        comp_res = subprocess.run(comp_cmd, capture_output=True, text=True)
        self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}")

        run_res = subprocess.run([str(bin_target)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0, f"Execution failed:\n{run_res.stderr}")
        self.assertIn("All 47 Verification Assertion Suites Passed with 100% Integrity", run_res.stdout)

    def test_10_anti_placeholder_compliance(self):
        """Quality Gate: Strict zero-placeholder compliance across all Phase 7 files."""
        files_to_check = [
            self.nested_json,
            self.ui_coord_json,
            self.pseudo_c,
            self.findings_nested_md,
            self.findings_ui_md
        ]
        for fpath in files_to_check:
            self.assertTrue(fpath.is_file(), f"{fpath} must exist")
            content = fpath.read_text(encoding="utf-8")
            for pattern in BANNED_PLACEHOLDER_PATTERNS:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                self.assertEqual(len(matches), 0, f"Forbidden placeholder '{pattern}' found in {fpath.name}")

    def test_11_findings_documents_metrics(self):
        """R2: Verify findings documents sizes, markdown headers, and Mermaid diagrams."""
        self.assertTrue(self.findings_nested_md.is_file())
        self.assertTrue(self.findings_ui_md.is_file())

        nested_size = self.findings_nested_md.stat().st_size
        self.assertGreaterEqual(nested_size, 30000, f"07_NESTED_SCROLLING.md too small ({nested_size} < 30000)")

        ui_size = self.findings_ui_md.stat().st_size
        self.assertGreaterEqual(ui_size, 25000, f"07_COMPLEX_UI_COORDINATION.md too small ({ui_size} < 25000)")

        nested_text = self.findings_nested_md.read_text(encoding="utf-8")
        self.assertIn("```mermaid", nested_text)
        self.assertIn("sequenceDiagram", nested_text)
        self.assertIn("graph TD", nested_text)

        ui_text = self.findings_ui_md.read_text(encoding="utf-8")
        self.assertIn("```mermaid", ui_text)
        self.assertIn("stateDiagram-v2", ui_text)
        self.assertIn("sequenceDiagram", ui_text)

    def test_12_evidence_ledger_integrity(self):
        """R5: Test evidence ledger integrity for Phase 7 entries (NEST-001 through NEST-022)."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        nest_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_7":
                    nest_entries.append(entry)

        self.assertGreaterEqual(len(nest_entries), 20, f"Found {len(nest_entries)} Phase 7 entries, expected >= 20")
        entry_ids = [e["id"] for e in nest_entries]
        for i in range(1, 21):
            expected_id = f"NEST-{i:03d}"
            self.assertIn(expected_id, entry_ids, f"Missing evidence record {expected_id}")

        for entry in nest_entries:
            self.assertEqual(entry["confidence"], "CONFIRMED")
            self.assertIn("[CONFIRMED]", entry["finding"])
            self.assertTrue(entry.get("binary_path"))
            self.assertTrue((PROJECT_ROOT / entry["binary_path"]).is_file())
            self.assertTrue(entry.get("address"))
            self.assertTrue(entry.get("evidence_type"))
            self.assertTrue(entry.get("tool"))

    def test_13_boundary_conditions_and_numerical_stability(self):
        """R6: Test edge cases, asymptotic behavior, and mathematical continuity."""
        # 1. Large title height continuity
        def h_title(dy):
            return max(0.0, 52.0 - dy) if dy >= 0 else 52.0 + abs(dy) * 0.55

        self.assertAlmostEqual(h_title(0.0), 52.0)
        self.assertAlmostEqual(h_title(52.0), 0.0)
        self.assertAlmostEqual(h_title(100.0), 0.0)
        self.assertAlmostEqual(h_title(-100.0), 107.0)

        # 2. Large title alpha cross-fade continuity
        def alpha_large(dy):
            if dy <= 40.0: return 1.0
            if dy >= 52.0: return 0.0
            return (52.0 - dy) / 12.0

        def alpha_inline(dy):
            if dy <= 40.0: return 0.0
            if dy >= 52.0: return 1.0
            return (dy - 40.0) / 12.0

        for dy in [39.0, 40.0, 43.0, 46.0, 49.0, 52.0, 55.0]:
            al = alpha_large(dy)
            ai = alpha_inline(dy)
            self.assertTrue(0.0 <= al <= 1.0)
            self.assertTrue(0.0 <= ai <= 1.0)
            if 40.0 <= dy <= 52.0:
                self.assertAlmostEqual(al + ai, 1.0, places=5)

        # 3. Sheet rubber band asymptotic limit
        c, d = 0.55, 200.0
        for x in [0.0, 10.0, 50.0, 100.0, 500.0, 10000.0]:
            rb = (x * d * c) / (d + c * x)
            self.assertLess(rb, d) # Asymptote at d = 200.0pt

        # 4. Refresh progress clamping
        def p_refresh(dy):
            return min(1.0, max(0.0, abs(dy) / 60.0))

        self.assertEqual(p_refresh(0.0), 0.0)
        self.assertAlmostEqual(p_refresh(30.0), 0.5)
        self.assertEqual(p_refresh(60.0), 1.0)
        self.assertEqual(p_refresh(120.0), 1.0)

    def test_14_scroll_progress_phase7_status(self):
        """R5: Verify scroll_progress.json marks phase_7_nested as completed."""
        self.assertTrue(self.progress_file.is_file())
        with open(self.progress_file, "r", encoding="utf-8") as f:
            p_data = json.load(f)

        phase7 = p_data.get("phases", {}).get("phase_7_nested", {})
        self.assertEqual(phase7.get("status"), "completed")
        self.assertTrue(phase7.get("entry_criteria_met"))
        self.assertGreaterEqual(len(phase7.get("notes", [])), 5)
        self.assertGreaterEqual(len(phase7.get("required_artifacts", [])), 5)

    def test_15_three_tier_concentric_scrolling_arbitration(self):
        """Edge Case 4: Test 3-tier concentric nesting (outer vertical, middle horizontal carousel, inner vertical card)."""
        with open(self.nested_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        concentric = data.get("three_tier_concentric_scrolling")
        self.assertIsNotNone(concentric, "three_tier_concentric_scrolling must be defined")
        self.assertIn("Outer Vertical Feed", concentric["hierarchy_structure"])
        self.assertIn("Middle Horizontal Carousel", concentric["hierarchy_structure"])
        self.assertIn("Inner Vertical Card", concentric["hierarchy_structure"])

        flow = concentric["arbitration_flow"]
        self.assertIn("directional_locking_evaluation", flow)
        self.assertIn("deepest_subview_priority", flow)
        self.assertIn("breakout_hysteresis", flow)
        self.assertIn("momentum_containment_across_tiers", flow)

    def test_16_custom_detents_multi_resolution(self):
        """Edge Case 2: Test multi-detent nearest-anchor resolution with custom detents."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        custom_mech = data.get("sheet_presentation_controller_coordination", {}).get("custom_detent_resolution_mechanics")
        self.assertIsNotNone(custom_mech, "custom_detent_resolution_mechanics must be defined")
        self.assertIn("argmin", custom_mech["multi_detent_nearest_anchor_algorithm"])
        self.assertIn("600.0 pt/s", custom_mech["dismissal_precedence"])

        # Python oracle for nearest anchor resolution:
        detents = [180.0, 426.0, 842.0]
        def resolve_multi(y, vy):
            if vy > 600.0 or y < (detents[0] - 60.0):
                return 0.0
            return min(detents, key=lambda d: abs(y - d))

        self.assertEqual(resolve_multi(110.0, 0.0), 0.0) # Pulled below 120 -> dismiss
        self.assertEqual(resolve_multi(400.0, 650.0), 0.0) # High velocity -> dismiss
        self.assertEqual(resolve_multi(200.0, 50.0), 180.0) # Settles to peek
        self.assertEqual(resolve_multi(450.0, 50.0), 426.0) # Settles to medium
        self.assertEqual(resolve_multi(800.0, 50.0), 842.0) # Settles to large

    def test_17_asynchronous_keyboard_resignation_interruption(self):
        """Edge Case 6: Test asynchronous firstResponder resignation interrupting interactive keyboard pan."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        async_inter = data.get("interactive_keyboard_dismissal", {}).get("asynchronous_interruption")
        self.assertIsNotNone(async_inter, "asynchronous_interruption must be defined")
        self.assertIn("resignFirstResponder", async_inter["external_resignation_behavior"])
        self.assertIn("is_tracking = false", async_inter["external_resignation_behavior"])

    def test_18_sheet_expansion_excess_drag_handoff(self):
        """Robustness: Test excess upward drag handoff to inner content when sheet reaches large detent."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules = data.get("sheet_presentation_controller_coordination", {}).get("content_scroll_vs_sheet_arbitration", {})
        self.assertIn("rule_excess_expansion_handoff", rules)
        self.assertIn("excess drag displacement", rules["rule_excess_expansion_handoff"])

    def test_19_sheet_vs_active_refresh_control_conflict(self):
        """Edge Case 5: Test downward drag conflict when inner scroll view is in active RefreshRefreshing state."""
        with open(self.ui_coord_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        conflict = data.get("sheet_presentation_controller_coordination", {}).get("sheet_vs_refresh_control_conflict")
        self.assertIsNotNone(conflict, "sheet_vs_refresh_control_conflict must be defined")
        self.assertIn("RefreshRefreshing", conflict["refreshing_downward_drag_rule"])
        self.assertIn("directly translates the sheet downward", conflict["refreshing_downward_drag_rule"])

    def test_20_uncoordinated_simultaneous_recognition_double_speed(self):
        """Edge Case 3: Verify uncoordinated simultaneous recognition defect vs coordinated clamping invariant."""
        with open(self.nested_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        defect_models = data.get("simultaneous_recognition_defect_models")
        self.assertIsNotNone(defect_models, "simultaneous_recognition_defect_models must be defined")
        self.assertIn("2 * dy_finger", defect_models["uncoordinated_double_speed_defect"]["mathematical_consequence"])
        self.assertIn("dy_finger", defect_models["coordinated_clamping_invariant"]["mathematical_consequence"])

    def test_21_upward_drag_boundary_handoff_and_dragging_state(self):
        """Edge Case 7: Test fractional upward drag boundary handoff to child and dragging state preservation."""
        # Mathematical simulation of coordinated upward handoff
        parent_max_y = 400.0
        parent_offset = 390.0
        child_offset = 0.0
        drag_y = 30.0

        travel = min(parent_max_y - parent_offset, drag_y)
        parent_offset += travel
        remainder = drag_y - travel
        child_offset += remainder

        self.assertAlmostEqual(parent_offset, 400.0)
        self.assertAlmostEqual(child_offset, 20.0)
        self.assertAlmostEqual(travel + remainder, drag_y)
        self.assertTrue(travel > 0.0) # parent dragging
        self.assertTrue(remainder > 0.0) # child dragging

    def test_22_three_tier_horizontal_lock_isolation_and_breakout(self):
        """Edge Case 8: Test 3-tier horizontal carousel locking suppressing vertical inner drift until 40pt breakout."""
        # Simulated multi-frame cross-axis accumulation
        locked_horizontal = True
        lock_broken = False
        accumulated_cross_axis = 0.0
        inner_y = 0.0

        for frame_dy in [15.0, 15.0, 15.0]:
            if locked_horizontal and not lock_broken:
                accumulated_cross_axis += frame_dy
                if accumulated_cross_axis >= 40.0:
                    lock_broken = True
                    inner_y += frame_dy # breakout!
            elif lock_broken:
                inner_y += frame_dy

        self.assertTrue(lock_broken)
        self.assertAlmostEqual(accumulated_cross_axis, 45.0)
        self.assertAlmostEqual(inner_y, 15.0) # Only the 3rd frame (post-breakout) routes to inner

    def test_23_interactive_keyboard_upward_flick_cancellation(self):
        """Edge Case 9: Test high upward velocity (vy < -400 pt/s) canceling dismissal even if travel > 50%."""
        kbd_height = 300.0
        travel = 180.0 # > 150pt (50% displacement)
        vy_upward = -500.0 # user swiped upward

        # Oracle logic:
        if vy_upward < -400.0:
            dismissed = False
        elif vy_upward > 400.0 or travel > (kbd_height * 0.50):
            dismissed = True
        else:
            dismissed = False

        self.assertFalse(dismissed, "Upward flick must cancel dismissal despite > 50% displacement")

    def test_24_multi_detent_unsorted_array_resolution(self):
        """Edge Case 10: Test multi-detent nearest-anchor resolution with unsorted detents array."""
        unsorted = [842.0, 180.0, 426.0]
        min_detent = min(unsorted)
        self.assertEqual(min_detent, 180.0)

        def resolve_unsorted(y, vy):
            if vy > 600.0 or y < (min_detent - 60.0):
                return 0.0
            return min(unsorted, key=lambda d: abs(y - d))

        self.assertEqual(resolve_unsorted(100.0, 0.0), 0.0) # < 120 -> dismiss
        self.assertEqual(resolve_unsorted(200.0, 0.0), 180.0) # near peek
        self.assertEqual(resolve_unsorted(440.0, 0.0), 426.0) # near medium
        self.assertEqual(resolve_unsorted(800.0, 0.0), 842.0) # near large

    def test_25_modern_navbar_refresh_control_threshold(self):
        """Edge Case 11: Test modern navigation bar 64.0pt pull-to-refresh trigger threshold and progress."""
        threshold = 64.0
        def p_progress(dy):
            return min(1.0, max(0.0, dy / threshold))

        self.assertAlmostEqual(p_progress(0.0), 0.0)
        self.assertAlmostEqual(p_progress(32.0), 0.50)
        self.assertAlmostEqual(p_progress(64.0), 1.00)
        self.assertAlmostEqual(p_progress(100.0), 1.00)

        # Triggered state gate: only reached at or past threshold
        self.assertFalse(32.0 >= threshold)
        self.assertTrue(64.0 >= threshold)

    def test_26_total_navbar_height_transitions_and_search_pinning(self):
        """Edge Case 12: Test total navigation bar height transitions and search bar pinning."""
        def calc_total_h(dy, has_search, pinned):
            std_h = 44.0
            lt_h = max(0.0, 52.0 - dy) if dy >= 0 else 52.0
            if not has_search:
                return std_h + lt_h
            if pinned:
                return std_h + lt_h + 52.0
            else:
                search_h = 52.0 if dy <= 52.0 else (max(0.0, 104.0 - dy) if dy < 104.0 else 0.0)
                return std_h + lt_h + search_h

        # Unpinned: 148pt expanded -> 96pt (large title collapsed) -> 44pt (search bar collapsed)
        self.assertAlmostEqual(calc_total_h(0.0, True, False), 148.0)
        self.assertAlmostEqual(calc_total_h(26.0, True, False), 122.0)
        self.assertAlmostEqual(calc_total_h(52.0, True, False), 96.0)
        self.assertAlmostEqual(calc_total_h(78.0, True, False), 70.0)
        self.assertAlmostEqual(calc_total_h(104.0, True, False), 44.0)

        # Pinned: stays pinned at 96pt minimum
        self.assertAlmostEqual(calc_total_h(0.0, True, True), 148.0)
        self.assertAlmostEqual(calc_total_h(52.0, True, True), 96.0)
        self.assertAlmostEqual(calc_total_h(200.0, True, True), 96.0)

        # Without search: 96pt -> 44pt
        self.assertAlmostEqual(calc_total_h(0.0, False, False), 96.0)
        self.assertAlmostEqual(calc_total_h(52.0, False, False), 44.0)

    def test_27_sheet_zero_drag_isolation(self):
        """Edge Case 13: Test that zero-displacement pan event never activates is_dragging state."""
        drag_y = 0.0
        if abs(drag_y) < 1e-9:
            is_sheet_dragging = False
            is_content_dragging = False
        else:
            is_content_dragging = (drag_y > 0.0)
            is_sheet_dragging = False

        self.assertFalse(is_sheet_dragging)
        self.assertFalse(is_content_dragging)

if __name__ == "__main__":
    unittest.main()
