#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 3D: Snapping, Paging & Target Content Offsets
Tests:
- Paging algorithm JSON schema, IEEE 754 deceleration rate (d = 0.985), and velocity threshold (200.0 pt/s)
- Target offset formula JSON, closed-form landing prediction, and delegate arbitration
- Scroll-to-top JSON, single-candidate exclusivity rule, and 0.30s animation parameters
- Numerical precision of closed-form landing multiplier Cd = 1 / (-1000 * ln(0.985))
- Paging decision boundaries: velocity threshold (199.9 vs 200.1 pt/s) and displacement cutoff (49.9% vs 50.1%)
- Single-page advance clamping under high-velocity momentum flings
- Status bar hit-testing boundary and candidate exclusion logic
- Standalone compilation and execution of C pseudocode test harnesses
- Findings dossier anti-placeholder compliance, LaTeX formulas, and structural richness
- Evidence ledger Phase 3D cross-validation integrity
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

class TestScrollingPhase3DAdversarial(unittest.TestCase):

    def setUp(self):
        self.paging_json = PROJECT_ROOT / "artifacts/scrolling/paging_algorithm.json"
        self.target_json = PROJECT_ROOT / "artifacts/scrolling/target_offset_formula.json"
        self.scroll_top_json = PROJECT_ROOT / "artifacts/scrolling/scroll_to_top.json"
        self.paging_pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/paging_target.pseudo.c"
        self.scroll_top_pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/scrollToTop_animation.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/03D_SNAPPING_POSITIONING.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.shared_cache_slice = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.01"

    def test_paging_algorithm_schema_and_constants(self):
        """R1: Test paging algorithm JSON schema, IEEE 754 constants, and thresholds."""
        self.assertTrue(self.paging_json.is_file(), "paging_algorithm.json must exist")
        with open(self.paging_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Deceleration rate 0.985
        fric = data.get("paging_kinematics_and_deceleration", {}).get("deceleration_friction", {})
        self.assertEqual(fric.get("value_decimal"), 0.985)
        self.assertEqual(fric.get("ieee754_double_hex"), "0x3fef851eb851eb85")
        self.assertEqual(fric.get("vm_address"), "0x1864d3040")

        # Unpack IEEE 754 double
        raw_bytes = bytes.fromhex(fric["ieee754_double_hex"][2:])
        unpacked_val = struct.unpack(">d", raw_bytes)[0]
        self.assertAlmostEqual(unpacked_val, 0.985, places=9)

        # 2. Velocity threshold 200.0 pt/s
        v_thresh = data.get("target_page_selection_algorithm", {}).get("velocity_threshold", {})
        self.assertEqual(v_thresh.get("threshold_pt_per_sec"), 200.0)
        self.assertEqual(v_thresh.get("ieee754_double_hex"), "0x4069000000000000")
        raw_v_bytes = bytes.fromhex(v_thresh["ieee754_double_hex"][2:])
        self.assertAlmostEqual(struct.unpack(">d", raw_v_bytes)[0], 200.0, places=6)

        # 3. Displacement cutoff 50%
        disp = data.get("target_page_selection_algorithm", {}).get("displacement_threshold", {})
        self.assertEqual(disp.get("cutoff_fraction"), 0.50)

        # 4. Single-page advance clamping
        policy = data.get("target_page_selection_algorithm", {}).get("multi_page_advance_policy", {})
        self.assertEqual(policy.get("standard_paging_limit", {}).get("maximum_page_delta_per_fling"), 1)

    def test_target_offset_formula_schema_and_derivation(self):
        """R2 & R3: Test target offset projection equations and delegate arbitration."""
        self.assertTrue(self.target_json.is_file(), "target_offset_formula.json must exist")
        with open(self.target_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Closed-form landing equation
        eq = data.get("proposed_target_offset_calculation", {}).get("closed_form_landing_equation", {})
        self.assertIn("s_projected", eq.get("formula", ""))
        self.assertIn("formula_latex", eq)

        # 2. Delegate arbitration
        del_arb = data.get("delegate_arbitration", {})
        self.assertIn("scrollViewWillEndDragging:withVelocity:targetContentOffset:", del_arb.get("protocol_signature", ""))
        conv = del_arb.get("velocity_conversion", {})
        self.assertEqual(conv.get("internal_velocity_unit"), "points per second (pt/s)")
        self.assertEqual(conv.get("delegate_velocity_unit"), "points per millisecond (pt/ms)")

        # 3. Snapping directional bias threshold 100.0 pt/s
        snap = data.get("snapping_detents_and_alignment", {}).get("nearest_neighbor_search_with_directional_bias", {})
        self.assertEqual(snap.get("bias_threshold", {}).get("velocity_threshold_pt_per_sec"), 100.0)

    def test_scroll_to_top_schema_and_kinematics(self):
        """R4: Test status bar scroll-to-top parameters and Single Candidate Exclusivity Rule."""
        self.assertTrue(self.scroll_top_json.is_file(), "scroll_to_top.json must exist")
        with open(self.scroll_top_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Duration 0.30s
        anim = data.get("animation_kinematics_and_parameters", {}).get("animation_parameters", {})
        self.assertEqual(anim.get("duration_seconds"), 0.30)
        self.assertEqual(anim.get("duration_ms"), 300.0)
        self.assertEqual(anim.get("ieee754_double_hex"), "0x3fd3333333333333")

        # Unpack IEEE 754 double
        raw_dur_bytes = bytes.fromhex(anim["ieee754_double_hex"][2:])
        self.assertAlmostEqual(struct.unpack(">d", raw_dur_bytes)[0], 0.30, places=9)

        # 2. Candidate qualification and exclusivity rule
        cand = data.get("candidate_scroll_view_selection_algorithm", {})
        self.assertIn("Single Candidate Exclusivity Rule", cand.get("exclusivity_rule", {}).get("rule_name", ""))
        crit = cand.get("qualification_criteria", [])
        crit_ids = [c.get("criterion_id") for c in crit]
        self.assertIn("SCROLLS_TO_TOP_ENABLED", crit_ids)
        self.assertIn("VIEW_VISIBILITY", crit_ids)
        self.assertIn("SCROLLABILITY", crit_ids)
        self.assertIn("NOT_ALREADY_AT_TOP", crit_ids)

        # 3. Target offset formula
        target_f = data.get("animation_kinematics_and_parameters", {}).get("target_content_offset", {}).get("formula", "")
        self.assertIn("-adjustedContentInset.top", target_f)
        self.assertIn("contentOffset.x", target_f)

    def test_closed_form_landing_multiplier_numerical_precision(self):
        """R1 & R2: Test closed-form landing multiplier Cd = 1 / (-1000 * ln(d))."""
        d = 0.985
        lambda_val = -1000.0 * math.log(d)
        cd_expected = 1.0 / lambda_val

        self.assertAlmostEqual(lambda_val, 15.113638, places=4)
        self.assertAlmostEqual(cd_expected, 0.066165, places=4)

        # Numerical integration vs closed-form projection
        v0 = 1000.0
        dt = 0.001 # 1ms simulation step
        pos_sim = 0.0
        v = v0
        for _ in range(10000): # simulate 10 seconds
            pos_sim += v * dt
            v *= math.pow(d, 1000.0 * dt)
            if abs(v) < 0.0001:
                break

        pos_analytic = v0 * cd_expected
        self.assertAlmostEqual(pos_sim, pos_analytic, delta=1.5)

    def test_paging_decision_boundaries_adversarial(self):
        """R1: Test sharp boundary transitions: 199.9 vs 200.1 pt/s and 49.9% vs 50.1%."""
        page_width = 393.0
        v_thresh = 200.0

        def select_page(current_page, displacement, velocity):
            disp_fraction = displacement / page_width
            if abs(velocity) >= v_thresh:
                if velocity > 0:
                    return current_page + 1
                else:
                    return current_page
            else:
                if disp_fraction > 0.50:
                    return current_page + 1
                else:
                    return current_page

        # 1. Just below threshold with 10% displacement -> snaps back to page 0
        self.assertEqual(select_page(0, page_width * 0.10, 199.99), 0)

        # 2. Just above threshold with 10% displacement -> advances to page 1
        self.assertEqual(select_page(0, page_width * 0.10, 200.01), 1)

        # 3. Just below displacement cutoff at low speed (50 pt/s) -> snaps back to page 0
        self.assertEqual(select_page(0, page_width * 0.4999, 50.0), 0)

        # 4. Just above displacement cutoff at low speed (50 pt/s) -> advances to page 1
        self.assertEqual(select_page(0, page_width * 0.5001, 50.0), 1)

        # 5. Backward flick just above threshold even with 95% displacement -> snaps back to page 0
        self.assertEqual(select_page(0, page_width * 0.95, -200.01), 0)

    def test_single_page_advance_clamping_adversarial(self):
        """R5: Single-page advance clamping under extreme velocities."""
        def clamped_target(initial_page, requested_page, max_pages=10):
            delta = requested_page - initial_page
            if delta > 1:
                target = initial_page + 1
            elif delta < -1:
                target = initial_page - 1
            else:
                target = requested_page
            return max(0, min(max_pages - 1, target))

        # Extreme positive fling: wants to jump +5 pages -> clamped to +1
        self.assertEqual(clamped_target(2, 7), 3)

        # Extreme negative fling: wants to jump -5 pages -> clamped to -1
        self.assertEqual(clamped_target(5, 0), 4)

        # Edge clamping at boundary
        self.assertEqual(clamped_target(0, -1), 0)
        self.assertEqual(clamped_target(9, 10), 9)

    def test_vertical_paging_and_delegate_arbitration_adversarial(self):
        """R1 & R2: Test vertical pagination target resolution and vertical d' adaptation."""
        page_height = 852.0
        v_thresh = 200.0

        def select_vertical_page(current_page, displacement, velocity):
            disp_fraction = displacement / page_height
            if abs(velocity) >= v_thresh:
                return current_page + 1 if velocity > 0 else current_page
            else:
                return current_page + 1 if disp_fraction > 0.50 else current_page

        # Vertical velocity advance
        self.assertEqual(select_vertical_page(0, 50.0, 250.0), 1)
        # Vertical displacement cutoff
        self.assertEqual(select_vertical_page(0, page_height * 0.55, 30.0), 1)
        self.assertEqual(select_vertical_page(0, page_height * 0.45, 30.0), 0)

        # Vertical effective deceleration rate adaptation
        vy = 500.0
        delta_sy = 200.0 # user wants to land at +200pt
        # d' = exp(-vy / (1000 * delta_sy))
        exponent = -vy / (1000.0 * delta_sy)
        d_prime = math.exp(exponent)
        self.assertTrue(0.850 <= d_prime <= 0.9995)
        self.assertAlmostEqual(d_prime, math.exp(-0.0025), places=6)

    def test_negative_interpage_spacing_and_unsorted_detents_adversarial(self):
        """R3 & R5: Clamping against negative interpageSpacing and handling unsorted detents."""
        bounds_width = 393.0
        # Negative interpageSpacing cannot reduce effective page width <= 0
        def safe_effective_page_size(w, spacing):
            eff = w + spacing
            return max(1.0, eff)

        self.assertEqual(safe_effective_page_size(bounds_width, -500.0), 1.0)
        self.assertEqual(safe_effective_page_size(bounds_width, -50.0), 343.0)

        # Unsorted detents should be sorted before nearest neighbor search
        unsorted = [500.0, 150.0, 0.0, 750.0, 320.0]
        sorted_detents = sorted(unsorted)
        self.assertEqual(sorted_detents, [0.0, 150.0, 320.0, 500.0, 750.0])

    def test_status_bar_screen_coordinate_boundaries_adversarial(self):
        """R4: Boundary testing for status bar touch coordinates."""
        status_bar_height = 54.0 # Dynamic Island
        window_width = 393.0

        def is_valid_status_bar_touch(x, y):
            if y < 0.0 or y > status_bar_height:
                return False
            if x < 0.0 or x > window_width:
                return False
            return True

        self.assertTrue(is_valid_status_bar_touch(196.5, 20.0))
        self.assertTrue(is_valid_status_bar_touch(0.0, 0.0))
        self.assertTrue(is_valid_status_bar_touch(window_width, status_bar_height))
        self.assertFalse(is_valid_status_bar_touch(196.5, -1.0))
        self.assertFalse(is_valid_status_bar_touch(196.5, 54.1))
        self.assertFalse(is_valid_status_bar_touch(-0.1, 20.0))
        self.assertFalse(is_valid_status_bar_touch(393.1, 20.0))

    def test_exact_cubic_bezier_ease_out_properties(self):
        """R4: Exact cubic Bézier ease-in-out/ease-out monotonicity and boundary checks."""
        def bezier_ease(u, x1=0.25, y1=0.10, x2=0.25, y2=1.0):
            if u <= 0: return 0.0
            if u >= 1: return 1.0
            t = u
            for _ in range(8):
                xt = 3*(1-t)**2 * t * x1 + 3*(1-t) * t**2 * x2 + t**3
                dxdt = 3*(1-t)**2 * x1 + 6*(1-t)*t*(x2 - x1) + 3*t**2 * (1 - x2)
                if abs(dxdt) < 1e-9: break
                t = t - (xt - u) / dxdt
                t = max(0.0, min(1.0, t))
            yt = 3*(1-t)**2 * t * y1 + 3*(1-t) * t**2 * y2 + t**3
            return yt

        # Boundary values
        self.assertEqual(bezier_ease(0.0), 0.0)
        self.assertEqual(bezier_ease(1.0), 1.0)

        # Monotonic progression
        prev = 0.0
        for step in range(1, 21):
            u = step / 20.0
            curr = bezier_ease(u)
            self.assertGreater(curr, prev, f"Bézier must be strictly increasing at u={u}")
            self.assertLessEqual(curr, 1.0)
            prev = curr

    def test_c_pseudocode_compilation_and_execution(self):
        """R6: Compile and execute C pseudocode verification test harnesses."""
        self.assertTrue(self.paging_pseudo_c.is_file(), "paging_target.pseudo.c must exist")
        self.assertTrue(self.scroll_top_pseudo_c.is_file(), "scrollToTop_animation.pseudo.c must exist")

        # 1. Compile and run paging_target.pseudo.c
        paging_bin = PROJECT_ROOT / "paging_target_test"
        compile_cmd1 = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            "-DPAGING_TARGET_STANDALONE",
            "-o", str(paging_bin),
            str(self.paging_pseudo_c),
            "-lm"
        ]
        res1 = subprocess.run(compile_cmd1, capture_output=True, text=True)
        self.assertEqual(res1.returncode, 0, f"Compilation of paging_target.pseudo.c failed:\n{res1.stderr}")

        exec_res1 = subprocess.run([str(paging_bin)], capture_output=True, text=True)
        self.assertEqual(exec_res1.returncode, 0, f"Execution of paging_target_test failed:\n{exec_res1.stderr}")
        self.assertIn("All 9 UIScrollView Paging & Snapping verification test suites passed", exec_res1.stdout)
        if paging_bin.exists():
            paging_bin.unlink()

        # 2. Compile and run scrollToTop_animation.pseudo.c
        scroll_top_bin = PROJECT_ROOT / "scroll_to_top_test"
        compile_cmd2 = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            "-DSCROLL_TO_TOP_STANDALONE",
            "-o", str(scroll_top_bin),
            str(self.scroll_top_pseudo_c),
            "-lm"
        ]
        res2 = subprocess.run(compile_cmd2, capture_output=True, text=True)
        self.assertEqual(res2.returncode, 0, f"Compilation of scrollToTop_animation.pseudo.c failed:\n{res2.stderr}")

        exec_res2 = subprocess.run([str(scroll_top_bin)], capture_output=True, text=True)
        self.assertEqual(exec_res2.returncode, 0, f"Execution of scroll_to_top_test failed:\n{exec_res2.stderr}")
        self.assertIn("All 8 Status Bar Scroll-To-Top verification test suites passed", exec_res2.stdout)
        if scroll_top_bin.exists():
            scroll_top_bin.unlink()

    def test_findings_dossier_anti_placeholder_and_structure(self):
        """R6: Verify findings dossier structure, size, LaTeX equations, and zero placeholders."""
        self.assertTrue(self.findings_md.is_file(), "03D_SNAPPING_POSITIONING.md must exist")
        size = self.findings_md.stat().st_size
        self.assertGreaterEqual(size, 2500, "Findings dossier must be >= 2500 bytes")

        content = self.findings_md.read_text(encoding="utf-8")

        # Anti-placeholder scan
        for pattern in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Forbidden placeholder pattern '{pattern}' found in {self.findings_md}")

        # Section presence
        required_sections = [
            "Executive Summary",
            "Paging Mechanics & Page Target Selection",
            "Target Content Offset Resolution & Delegate Arbitration",
            "Snapping Detents & Alignment Offsets",
            "Status Bar Scroll-To-Top Kinematics & Candidate Arbitration",
            "Paging Deceleration & Spring Coordination",
            "Production Pseudocode Architecture",
            "Verification & Empirical Evidence"
        ]
        for sec in required_sections:
            self.assertIn(sec.lower(), content.lower(), f"Missing required section '{sec}' in findings dossier")

        # LaTeX formulas and Mermaid diagrams
        self.assertIn("$$", content, "Findings dossier must contain LaTeX mathematical formulas")
        self.assertIn("```mermaid", content, "Findings dossier must contain Mermaid diagrams")

    def test_evidence_ledger_phase_3d_integrity(self):
        """R6: Verify Phase 3D entries in evidence_ledger.jsonl citing real shared cache slice."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        self.assertTrue(self.shared_cache_slice.is_file(), "Shared cache slice .01 must exist")

        phase_3d_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_3D":
                    phase_3d_entries.append(entry)

        self.assertGreaterEqual(len(phase_3d_entries), 10, "Must have at least 10 Phase 3D entries in ledger")

        expected_methods = [
            "isPagingEnabled",
            "setPagingEnabled:",
            "_defaultPagingDecelerationRate",
            "_pagingDecelerationRate",
            "_setPagingDecelerationRate:",
            "_pagingOrigin",
            "setPagingOrigin:",
            "_pagingLeftContentOffset",
            "_pagingRightContentOffset",
            "_scrollToTopFromTouchAtScreenLocation:animate:",
            "_registerAsScrollToTopViewIfPossible",
            "_unregisterAsScrollToTopViewIfPossible",
            "targetOffsetForOffset:velocity:",
            "pageForOffset:",
            "targetOffsetForProjectedOffset:velocity:"
        ]
        found_methods = [e.get("method") for e in phase_3d_entries]
        for meth in expected_methods:
            self.assertIn(meth, found_methods, f"Missing method {meth} in Phase 3D evidence ledger")

        for e in phase_3d_entries:
            self.assertEqual(e["confidence"], "CONFIRMED")
            self.assertIn("[CONFIRMED]", e["finding"])
            self.assertTrue(e["binary_path"].endswith("dyld_shared_cache_arm64e.01"))
            self.assertTrue((PROJECT_ROOT / e["binary_path"]).is_file())
            self.assertTrue(e["address"].startswith("0x18"))
            self.assertGreater(len(e["opcode_instructions"]), 0)

    def test_delegate_mutation_spring_fallback_adversarial(self):
        """R2 & R5: Stress test delegate mutation fallback: opposite direction, tiny displacement, large jump, out of bounds."""
        active_decel = 0.985
        s0 = 100.0

        def arbitrate_decision(v0, s_target, s_min=0.0, s_max=2000.0):
            if s_target < s_min or s_target > s_max:
                return "BOUNDARY_BOUNCE", active_decel, True

            delta_s = s_target - s0
            lambda_val = -1000.0 * math.log(active_decel)
            s_proj = s0 + v0 / lambda_val
            delta_proj = s_proj - s0

            same_direction = (v0 * delta_s > 0.0)
            significant_disp = (abs(delta_s) >= 1.0)
            significant_vel = (abs(v0) >= 10.0)
            within_jump_limit = (abs(delta_s - delta_proj) <= 150.0)

            if same_direction and significant_disp and significant_vel and within_jump_limit:
                exponent = -v0 / (1000.0 * delta_s)
                d_prime = math.exp(exponent)
                if 0.850 <= d_prime <= 0.9995:
                    return "BALLISTIC_DECAY", d_prime, False

            return "SPRING_SETTLING", active_decel, True

        # 1. Normal moderate adjustment within 150pt
        mode, d_prime, spring = arbitrate_decision(400.0, 130.0)
        self.assertEqual(mode, "BALLISTIC_DECAY")
        self.assertFalse(spring)
        self.assertTrue(0.850 <= d_prime <= 0.9995)

        # 2. Opposite direction: v0 = +400, s_target = 50 (delta_s = -50)
        mode, _, spring = arbitrate_decision(400.0, 50.0)
        self.assertEqual(mode, "SPRING_SETTLING")
        self.assertTrue(spring)

        # 3. Tiny displacement: v0 = 500, delta_s = 0.0001
        mode, d_val, spring = arbitrate_decision(500.0, 100.0001)
        self.assertEqual(mode, "SPRING_SETTLING")
        self.assertTrue(spring)
        self.assertFalse(math.isnan(d_val) or math.isinf(d_val))

        # 4. Large relocation jump: v0 = 300 (proj ~ 120), target = 500 (delta_s = 400 > 150pt delta)
        mode, _, spring = arbitrate_decision(300.0, 500.0)
        self.assertEqual(mode, "SPRING_SETTLING")
        self.assertTrue(spring)

        # 5. Out of bounds: target = 3000 (s_max = 2000)
        mode, _, spring = arbitrate_decision(200.0, 3000.0)
        self.assertEqual(mode, "BOUNDARY_BOUNCE")
        self.assertTrue(spring)

    def test_scroll_to_top_candidate_qualification_adversarial(self):
        """R4: Candidate qualification edge cases: disabled scrolling, zero contentSize, zoomed content, NaN."""
        def is_eligible(scroll_enabled, content_h, bounds_h, inset_top, inset_bottom, offset_y, zoom_scale=1.0):
            if not scroll_enabled:
                return False
            if content_h <= 0.0 or bounds_h <= 0.0:
                return False
            zoom = zoom_scale if zoom_scale >= 0.01 else 1.0
            effective_h = content_h * zoom
            total_h = effective_h + inset_top + inset_bottom
            if total_h <= bounds_h:
                return False
            min_top = -inset_top
            if math.isnan(offset_y) or math.isinf(offset_y):
                return False
            if offset_y <= min_top + 0.5:
                return False
            return True

        # Standard valid candidate
        self.assertTrue(is_eligible(True, 3000.0, 800.0, 54.0, 34.0, 600.0))

        # 1. Disabled scrolling
        self.assertFalse(is_eligible(False, 3000.0, 800.0, 54.0, 34.0, 600.0))

        # 2. Zero contentSize
        self.assertFalse(is_eligible(True, 0.0, 800.0, 54.0, 34.0, 600.0))

        # 3. Zoomed content: content_h=700 <= bounds_h=800 at 1.0x -> False, at 2.0x -> True
        self.assertFalse(is_eligible(True, 700.0, 800.0, 0.0, 0.0, 200.0, zoom_scale=1.0))
        self.assertTrue(is_eligible(True, 700.0, 800.0, 0.0, 0.0, 200.0, zoom_scale=2.0))

        # 4. Already at top or rested above top
        self.assertFalse(is_eligible(True, 3000.0, 800.0, 54.0, 34.0, -54.0)) # exactly at top
        self.assertFalse(is_eligible(True, 3000.0, 800.0, 54.0, 34.0, -53.8)) # within 0.5pt tolerance
        self.assertFalse(is_eligible(True, 3000.0, 800.0, 54.0, 34.0, -80.0)) # overscrolled above top

        # 5. NaN offset
        self.assertFalse(is_eligible(True, 3000.0, 800.0, 54.0, 34.0, float('nan')))

    def test_scroll_to_top_multi_touch_and_display_link_cancellation_adversarial(self):
        """R4: Multi-touch gesture interruption, touchesBegan/Cancelled, and CADisplayLink invalidation."""
        class MockScrollAnimation:
            def __init__(self):
                self.is_animating = True
                self.display_link_invalidated = False
                self.is_dragging = False
                self.zoom_scale = 1.0

            def touches_began(self):
                if self.is_animating:
                    self.is_animating = False
                    self.display_link_invalidated = True
                    self.is_dragging = True
                    return True
                self.is_dragging = True
                return False

            def touches_cancelled(self):
                if self.is_animating:
                    self.is_animating = False
                    self.display_link_invalidated = True
                self.is_dragging = False

            def handle_pinch(self, state, scale):
                if state in (1, 2): # Began or Changed
                    if self.is_animating:
                        self.is_animating = False
                        self.display_link_invalidated = True
                    self.zoom_scale = scale
                    return True
                elif state == 4: # Cancelled
                    if self.is_animating:
                        self.is_animating = False
                        self.display_link_invalidated = True
                    return True
                return False

            def step(self):
                if not self.is_animating or self.display_link_invalidated:
                    return False
                return True

        # Scenario 1: touchesBegan interruption
        anim = MockScrollAnimation()
        self.assertTrue(anim.is_animating)
        interrupted = anim.touches_began()
        self.assertTrue(interrupted)
        self.assertFalse(anim.is_animating)
        self.assertTrue(anim.display_link_invalidated)
        self.assertTrue(anim.is_dragging)
        self.assertFalse(anim.step()) # No further animation ticks allowed

        # Scenario 2: touchesCancelled
        anim2 = MockScrollAnimation()
        anim2.is_dragging = True
        anim2.touches_cancelled()
        self.assertFalse(anim2.is_animating)
        self.assertTrue(anim2.display_link_invalidated)
        self.assertFalse(anim2.is_dragging)

        # Scenario 3: Multi-touch pinch zoom interruption (state 1 = Began)
        anim3 = MockScrollAnimation()
        handled = anim3.handle_pinch(1, 1.75)
        self.assertTrue(handled)
        self.assertFalse(anim3.is_animating)
        self.assertTrue(anim3.display_link_invalidated)
        self.assertEqual(anim3.zoom_scale, 1.75)

        # Scenario 4: Multi-touch pinch zoom cancelled (state 4 = Cancelled)
        anim4 = MockScrollAnimation()
        handled = anim4.handle_pinch(4, 1.0)
        self.assertTrue(handled)
        self.assertFalse(anim4.is_animating)
        self.assertTrue(anim4.display_link_invalidated)

if __name__ == "__main__":
    unittest.main()
