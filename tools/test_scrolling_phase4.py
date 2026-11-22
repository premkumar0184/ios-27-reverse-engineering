#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 4: Specialized Implementations
(SwiftUI, WebKit, TextKit, UICollectionView, UITableView, Accessibility, Keyboard)

Tests:
1. SwiftUI declarative scrolling JSON schema, _UIHostingScrollView subclassing, and ScrollGeometry layout.
2. WebKit multi-process scrolling JSON schema, WKScrollView split delegate, and CSS overscroll-behavior.
3. Specialized inventory JSON schema, kinematic constants, and mathematical models.
4. Numerical precision of selection drag quadratic velocity ramping and cell prefetch lookahead formulas.
5. Standalone compilation and execution of C pseudocode test harness (all 38 unit assertion suites).
6. Findings dossier anti-placeholder compliance, byte size (>= 30,000 bytes), Mermaid diagrams, and LaTeX math.
7. Evidence ledger cross-validation integrity for SPEC-001 through SPEC-020.
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

class TestScrollingPhase4Adversarial(unittest.TestCase):

    def setUp(self):
        self.swiftui_json = PROJECT_ROOT / "artifacts/scrolling/swiftui_scroll.json"
        self.webkit_json = PROJECT_ROOT / "artifacts/scrolling/webkit_scroll.json"
        self.specialized_json = PROJECT_ROOT / "artifacts/scrolling/specialized_inventory.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/specialized_scroll.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/04_SPECIALIZED_IMPLEMENTATIONS.md"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

    def test_swiftui_scroll_schema_and_types(self):
        """R1: Test SwiftUI declarative scrolling JSON schema and bridge definitions."""
        self.assertTrue(self.swiftui_json.is_file(), "swiftui_scroll.json must exist")
        with open(self.swiftui_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sec in ["subsystem", "target_environment", "frameworks", "_UIHostingScrollView",
                    "_SwiftUIScrollViewBridge", "ScrollPosition", "ScrollGeometry",
                    "ScrollPhase", "declarative_modifiers", "gesture_arbitration"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in swiftui_scroll.json")

        hosting = data["_UIHostingScrollView"]
        self.assertEqual(hosting.get("superclass"), "UIScrollView")
        self.assertIn("UIScrollView", hosting.get("inheritance_chain", []))

        # Ivars check
        ivar_names = [iv["name"] for iv in hosting.get("ivars", [])]
        self.assertIn("_bridge", ivar_names)
        self.assertIn("_isProgrammaticUpdate", ivar_names)
        self.assertIn("_targetBehavior", ivar_names)

        # ScrollGeometry check
        geom = data["ScrollGeometry"]
        self.assertEqual(geom.get("struct_size_bytes"), 80)
        field_names = [fld["name"] for fld in geom.get("fields", [])]
        self.assertEqual(field_names, ["contentOffset", "contentSize", "contentInsets", "boundsSize"])

        # ScrollPhase check
        phase_cases = [c["name"] for c in data["ScrollPhase"].get("cases", [])]
        self.assertEqual(phase_cases, ["idle", "interacting", "decelerating", "animating"])

    def test_webkit_scroll_schema_and_cross_process(self):
        """R2: Test WebKit multi-process scrolling JSON schema and split delegate."""
        self.assertTrue(self.webkit_json.is_file(), "webkit_scroll.json must exist")
        with open(self.webkit_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sec in ["subsystem", "target_environment", "frameworks", "process_model",
                    "WKScrollView", "remote_scrolling_coordinator", "scrolling_tree",
                    "overscroll_behavior", "wheel_event_throttling"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in webkit_scroll.json")

        wk_scroll = data["WKScrollView"]
        self.assertEqual(wk_scroll.get("superclass"), "UIScrollView")

        ivar_names = [iv["name"] for iv in wk_scroll.get("ivars", [])]
        self.assertIn("_internalDelegate", ivar_names)
        self.assertIn("_externalDelegate", ivar_names)
        self.assertIn("_scrollingTreeScrollingNode", ivar_names)
        self.assertIn("_overscrollBehaviorX", ivar_names)
        self.assertIn("_overscrollBehaviorY", ivar_names)

        # Overscroll behavior mapping
        overscroll = data["overscroll_behavior"]
        self.assertEqual(overscroll.get("enum_mapping", {}).get("none"), 2)
        self.assertEqual(overscroll.get("enum_mapping", {}).get("contain"), 1)
        self.assertEqual(overscroll.get("enum_mapping", {}).get("auto"), 0)

        # Wheel throttling timeout
        wheel = data["wheel_event_throttling"]
        self.assertEqual(wheel.get("active_listeners", {}).get("timeout_fallback_ms"), 100.0)

        # Tile cache memory pressure
        self.assertIn("tile_cache_memory_pressure", data)
        self.assertEqual(data["tile_cache_memory_pressure"].get("allocator"), "WebCore::TileController")

    def test_specialized_inventory_schema_and_constants(self):
        """R3 & R4 & R5: Test specialized inventory schema, TextKit, and CollectionView constants."""
        self.assertTrue(self.specialized_json.is_file(), "specialized_inventory.json must exist")
        with open(self.specialized_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        subsys = data.get("subsystems", {})
        for k in ["swiftui_declarative", "webkit_asynchronous", "uitextview_textkit",
                  "uicollectionview_prefetching", "accessibility_and_keyboard"]:
            self.assertIn(k, subsys, f"Missing subsystem '{k}' in specialized_inventory.json")

        # TextKit auto-scroll ramping formula and multi-container geometry
        text_params = subsys["uitextview_textkit"]["kinetic_parameters"]["auto_scroll_ramping_formula"]["parameters"]
        self.assertEqual(text_params["v_max"]["value_pt_per_sec"], 1400.0)
        self.assertEqual(text_params["d_edge"]["value_pt"], 44.0)
        self.assertEqual(text_params["p"]["value"], 2.0)
        self.assertEqual(text_params["caret_padding"]["value_pt"], 8.0)
        self.assertIn("multi_container_geometry", subsys["uitextview_textkit"]["kinetic_parameters"])
        self.assertIn("narrow_viewport_normalization", subsys["uitextview_textkit"]["kinetic_parameters"]["auto_scroll_ramping_formula"])
        self.assertIn("selection_drag_velocity_2d", subsys["uitextview_textkit"]["kinetic_parameters"]["auto_scroll_ramping_formula"])
        self.assertIn("exclusion_path_slicing", subsys["uitextview_textkit"]["kinetic_parameters"]["multi_container_geometry"])
        self.assertIn("multi_obstacle_boolean_slicing", subsys["uitextview_textkit"]["kinetic_parameters"]["multi_container_geometry"])

        # UICollectionView prefetching formula and orthogonal locking
        prefetch_params = subsys["uicollectionview_prefetching"]["prefetch_parameters"]["lookahead_window_formula"]["parameters"]
        self.assertEqual(prefetch_params["W_min_ratio"]["value"], 1.5)
        self.assertEqual(prefetch_params["delta_t_lead"]["value_sec"], 0.25)
        self.assertEqual(prefetch_params["W_max_ratio"]["value"], 4.0)
        self.assertEqual(prefetch_params["ballistic_cancellation_velocity"]["value_pt_per_sec"], 3000.0)
        self.assertIn("directional_lookahead_interval", subsys["uicollectionview_prefetching"]["prefetch_parameters"])
        ortho_lock = subsys["uicollectionview_prefetching"]["prefetch_parameters"]["orthogonal_directional_locking"]
        self.assertEqual(ortho_lock["vertical_lock_angle_deg"], 60.0)
        self.assertEqual(ortho_lock["horizontal_lock_angle_deg"], 30.0)

        # Accessibility directions
        a11y_dirs = subsys["accessibility_and_keyboard"]["accessibility_scroll_directions"]
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionRight"], 1)
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionLeft"], 2)
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionUp"], 3)
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionDown"], 4)
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionNext"], 5)
        self.assertEqual(a11y_dirs["UIAccessibilityScrollDirectionPrevious"], 6)

        # Navigation heuristics
        heuristics = subsys["accessibility_and_keyboard"]["navigation_heuristics"]
        self.assertEqual(heuristics["page_turn_overlap_pt"], 44.0)
        self.assertEqual(heuristics["keyboard_discrete_step_pt"], 40.0)
        self.assertIn("detent_status_formula", heuristics)
        self.assertIn("boundary_feedback_alert", heuristics)
        self.assertIn("keyboard_repeat_state_machine", heuristics)

    def test_numerical_precision_of_kinetic_formulas(self):
        """Mathematical verification of velocity ramping, lookahead formulas, and orthogonal angles."""
        # 1. Selection drag quadratic ramping: v(d) = v_max * ((d_edge - d)/d_edge)^2
        v_max = 1400.0
        d_edge = 44.0
        
        # d = 0 (edge): v = 1400
        v_edge = v_max * pow((d_edge - 0.0) / d_edge, 2.0)
        self.assertAlmostEqual(v_edge, 1400.0, places=6)

        # d = 22 (midway): v = 1400 * 0.25 = 350.0
        v_mid = v_max * pow((d_edge - 22.0) / d_edge, 2.0)
        self.assertAlmostEqual(v_mid, 350.0, places=6)

        # d = 44 (boundary limit): v = 0.0
        v_lim = v_max * pow((d_edge - 44.0) / d_edge, 2.0)
        self.assertAlmostEqual(v_lim, 0.0, places=6)

        # 1b. Narrow viewport dynamic normalization: H = 60.0 -> d_edge_eff = 30.0
        H_compact = 60.0
        d_eff = min(d_edge, H_compact / 2.0)
        self.assertEqual(d_eff, 30.0)
        # Touch at y = 35.0 (dist to bottom = 25.0) -> v = 1400 * ((30 - 25)/30)^2 = 1400 / 36
        v_compact = v_max * pow((d_eff - 25.0) / d_eff, 2.0)
        self.assertAlmostEqual(v_compact, 1400.0 / 36.0, places=4)

        # 1c. Multi-obstacle boolean interval union: [90, 210] union [140, 240] = [90, 240]
        # Valid text line fragment slices for container width 400: [0, 90] and [240, 400]
        self.assertEqual((0.0, 90.0), (0.0, min(90.0, 140.0)))
        self.assertEqual((240.0, 400.0), (max(210.0, 240.0), 400.0))

        # 1d. Hardware keyboard repeat timing and continuous velocity ramping
        # Initial delay = 0.40s. At t = 0.50s (active = 0.10s) at 30Hz: 3 repeats
        active_t = 0.50 - 0.40
        repeat_ticks = int(round(active_t / (1.0 / 30.0)))
        self.assertEqual(repeat_ticks, 3)
        # Ramped velocity at active_t = 1.1s: min(2400, 1200 + 1600 * 1.1) = 2400
        v_ramped = min(2400.0, 1200.0 + 1600.0 * 1.1)
        self.assertEqual(v_ramped, 2400.0)

        # 2. Prefetching lookahead window: W = min(4.0*H, max(1.5*H, |v| * 0.25))
        H = 800.0
        w_slow = min(4.0 * H, max(1.5 * H, 100.0 * 0.25))
        self.assertEqual(w_slow, 1200.0) # clamped to 1.5 * 800

        w_mid = min(4.0 * H, max(1.5 * H, 6000.0 * 0.25))
        self.assertEqual(w_mid, 1500.0) # velocity proportional

        w_fast = min(4.0 * H, max(1.5 * H, 20000.0 * 0.25))
        self.assertEqual(w_fast, 3200.0) # clamped to 4.0 * 800

        # 2b. Directional lookahead interval evaluation: offset = 1000, H = 800, W = 1200
        # Forward scroll (v > 0): [y + H, y + H + W] -> [1800, 3000]
        y_offset = 1000.0
        self.assertEqual((y_offset + H, y_offset + H + w_slow), (1800.0, 3000.0))
        # Backward scroll (v < 0): [y - W, y] -> [-200, 1000]
        self.assertEqual((y_offset - w_slow, y_offset), (-200.0, 1000.0))

        # 3. Orthogonal directional locking angles
        tan_60 = math.tan(math.radians(60.0))
        self.assertAlmostEqual(tan_60, math.sqrt(3.0), places=6)
        tan_30 = math.tan(math.radians(30.0))
        self.assertAlmostEqual(tan_30, 1.0 / math.sqrt(3.0), places=6)

    def test_standalone_pseudocode_compilation_and_execution(self):
        """R6: Compile and execute specialized_scroll.pseudo.c under gcc -Wall -Wextra -Werror."""
        self.assertTrue(self.pseudo_c.is_file(), "specialized_scroll.pseudo.c must exist")
        bin_path = Path("/tmp/test_specialized_scroll_bin")
        compile_cmd = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            str(self.pseudo_c), "-lm", "-o", str(bin_path)
        ]
        comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
        self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}")

        run_res = subprocess.run([str(bin_path)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0, f"Execution failed:\n{run_res.stderr}")
        self.assertIn("All 38 Specialized Scrolling unit test suites PASSED", run_res.stdout)

    def test_findings_dossier_structure_and_invariants(self):
        """R6: Verify findings document byte size, anti-placeholder compliance, and structure."""
        self.assertTrue(self.findings_md.is_file(), "04_SPECIALIZED_IMPLEMENTATIONS.md must exist")
        size = self.findings_md.stat().st_size
        self.assertGreaterEqual(size, 30000, f"Findings document size ({size}) < 30,000 bytes minimum")

        content = self.findings_md.read_text(encoding="utf-8")

        # Zero-placeholder scan
        for pat in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pat, content, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Banned placeholder '{matches[0].group() if matches else ''}' found in findings")

        # Structural sections
        for sec in ["SwiftUI Declarative Scrolling Architecture",
                    "WebKit Multi-Process Viewports",
                    "UITextView & TextKit 2 Kinetic Coordination",
                    "UICollectionView / UITableView Prefetching",
                    "Accessibility & Hardware Keyboard Scrolling",
                    "Mathematical Models & Closed-Form Recurrences",
                    "Master Architectural & PAC00 Method Table",
                    "Empirical Evidence Ledger Entries"]:
            self.assertIn(sec.lower(), content.lower(), f"Missing required section '{sec}' in findings document")

        # Mermaid diagrams variety
        for diag in ["classDiagram", "sequenceDiagram", "stateDiagram-v2", "graph"]:
            self.assertIn(diag, content, f"Missing Mermaid diagram '{diag}' in findings document")

        # LaTeX formulas
        self.assertIn("$$", content, "Missing LaTeX display formulas ($$) in findings document")

    def test_evidence_ledger_phase4_integrity(self):
        """R6: Verify evidence_ledger.jsonl contains SPEC-001 through SPEC-020 entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        phase4_entries = [e for e in lines if e.get("phase") == "PHASE_4"]
        self.assertGreaterEqual(len(phase4_entries), 20, f"Found {len(phase4_entries)} Phase 4 entries, expected >= 20")

        spec_ids = [e.get("id") for e in phase4_entries]
        for i in range(1, 21):
            expected_id = f"SPEC-{i:03d}"
            self.assertIn(expected_id, spec_ids, f"Missing evidence entry {expected_id}")

        for entry in phase4_entries:
            self.assertTrue(entry.get("id").startswith("SPEC-"))
            self.assertIn("[CONFIRMED]", entry.get("finding", ""))
            self.assertEqual(entry.get("confidence"), "CONFIRMED")
            self.assertTrue(entry.get("address", "").startswith("0x1"))
            self.assertTrue(entry.get("binary_path"))
            # Binary path must exist on disk
            full_bin = PROJECT_ROOT / entry.get("binary_path")
            self.assertTrue(full_bin.is_file(), f"Cited binary_path does not exist: {entry.get('binary_path')}")
            self.assertTrue(entry.get("opcode_instructions"))
            self.assertTrue(entry.get("evidence_type"))
            self.assertTrue(entry.get("tool"))

if __name__ == "__main__":
    unittest.main()
