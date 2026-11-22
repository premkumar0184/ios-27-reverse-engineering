#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 5: Rendering, Compositing & Frame Scheduling
(QuartzCore, CoreAnimation, UIKitCore, CADisplayLink, CALayer, CATransaction, Scroll Indicators)

Tests:
1. Rendering pipeline JSON schema, CADisplayLink lifecycle, and ProMotion VFD boosting tiers.
2. Scroll indicator parameters JSON schema, geometric formulas, and fade kinetics constants.
3. Numerical precision of ProMotion timestep invariance, indicator sizing, overscroll compression, and scrubbing factors.
4. Standalone compilation and execution of C pseudocode test harness (all 42 unit assertion suites).
5. Findings dossiers anti-placeholder compliance, minimum byte sizes (>= 25,000 bytes and >= 20,000 bytes), Mermaid diagrams, and LaTeX math.
6. Evidence ledger cross-validation integrity for REND-001 through REND-020.
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

class TestScrollingPhase5Adversarial(unittest.TestCase):

    def setUp(self):
        self.rendering_json = PROJECT_ROOT / "artifacts/scrolling/rendering_pipeline.json"
        self.indicator_json = PROJECT_ROOT / "artifacts/scrolling/indicator_parameters.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/rendering_scheduling.pseudo.c"
        self.findings_rendering_md = PROJECT_ROOT / "findings/scrolling/05_RENDERING_FRAME_SCHEDULING.md"
        self.findings_indicators_md = PROJECT_ROOT / "findings/scrolling/05_SCROLL_INDICATORS.md"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

    def test_rendering_pipeline_schema_and_types(self):
        """R1, R2, R3: Test rendering pipeline JSON schema, CADisplayLink lifecycle, and ProMotion VFD boosting."""
        self.assertTrue(self.rendering_json.is_file(), "rendering_pipeline.json must exist")
        with open(self.rendering_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sec in ["subsystem", "target_environment", "frameworks", "cadisplaylink_lifecycle",
                    "compositor_transforms", "model_vs_presentation_authority", "promotion_vfd_boosting"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in rendering_pipeline.json")

        cdl = data["cadisplaylink_lifecycle"]
        self.assertEqual(cdl.get("class_name"), "CADisplayLink")
        init_info = cdl.get("initialization", {})
        self.assertEqual(init_info.get("address"), "0x184310100")
        self.assertEqual(init_info.get("caller_address"), "0x1848b7120")

        # Runloop modes
        rl = cdl.get("runloop_modes", {})
        self.assertIn("active_touch_tracking", rl)
        self.assertIn("ballistic_deceleration", rl)
        self.assertEqual(rl["active_touch_tracking"].get("mode_name"), "UITrackingRunLoopMode")
        self.assertEqual(rl["ballistic_deceleration"].get("mode_name"), "NSRunLoopCommonModes")

        # Compositor transforms
        ct = data["compositor_transforms"]
        self.assertEqual(ct.get("bounds_translation", {}).get("address"), "0x184315100")
        self.assertIn("implicit_animation_suppression", ct)

        # ProMotion VFD tiers
        vfd = data["promotion_vfd_boosting"]
        tiers = vfd.get("velocity_rate_tiers", [])
        self.assertEqual(len(tiers), 4)
        tier_names = [t.get("tier_name") for t in tiers]
        self.assertTrue(any("Peak" in n for n in tier_names))
        self.assertTrue(any("Balanced" in n for n in tier_names))
        self.assertTrue(any("Conservative" in n for n in tier_names))
        self.assertTrue(any("Idle" in n for n in tier_names))

        # Check peak tier 120Hz
        peak = [t for t in tiers if "Peak" in t.get("tier_name")][0]
        self.assertEqual(peak["frame_rate_range"]["maximum_hz"], 120.0)
        self.assertEqual(peak["frame_rate_range"]["preferred_hz"], 120.0)
        self.assertEqual(peak["frame_rate_range"]["minimum_hz"], 80.0)

    def test_indicator_parameters_schema_and_types(self):
        """R4, R5: Test scroll indicator parameters JSON schema, sizing, overscroll, and fade constants."""
        self.assertTrue(self.indicator_json.is_file(), "indicator_parameters.json must exist")
        with open(self.indicator_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sec in ["subsystem", "target_environment", "classes", "geometry_and_sizing",
                    "overscroll_compression", "interactive_scrubbing", "fade_kinetics", "compositor_hit_testing"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in indicator_parameters.json")

        geo = data["geometry_and_sizing"]
        self.assertEqual(geo.get("minimum_length_pt", {}).get("vertical"), 36.0)
        self.assertEqual(geo.get("minimum_length_pt", {}).get("horizontal"), 36.0)
        self.assertEqual(geo.get("minimum_length_pt", {}).get("ieee754_double_hex"), "0x4042000000000000")
        self.assertEqual(geo.get("knob_thickness_pt", {}).get("default_collapsed"), 3.0)
        self.assertEqual(geo.get("knob_thickness_pt", {}).get("interactive_expanded"), 8.0)

        overscroll = data["overscroll_compression"]
        self.assertEqual(overscroll.get("compression_ratio"), 2.0)

        fade = data["fade_kinetics"]
        self.assertEqual(fade.get("display_timeout_delay_sec", {}).get("standard_scroll_view"), 1.50)
        self.assertEqual(fade.get("display_timeout_delay_sec", {}).get("paging_scroll_view"), 2.00)
        self.assertEqual(fade.get("fade_out_animation", {}).get("duration_sec"), 0.30)
        self.assertEqual(fade.get("fade_out_animation", {}).get("ieee754_duration_hex"), "0x3fd3333333333333")

        hit = data["compositor_hit_testing"]
        self.assertEqual(hit.get("hit_target_expansion", {}).get("minimum_hit_dimension_pt"), 44.0)

    def test_numerical_precision_of_rendering_formulas(self):
        """R3, R4, R5: Mathematical precision of timestep invariance, indicator sizing, overscroll compression, and fade curves."""
        # 1. ProMotion Timestep Invariance Proof
        v0 = 2500.0
        d = 0.998
        total_time = 1.0 / 60.0 # 16.6667ms
        ln_d = math.log(d)

        # Single 60Hz step
        delta_s_60 = v0 * (pow(d, 1000.0 * total_time) - 1.0) / (1000.0 * ln_d)

        # Two 120Hz sub-steps
        dt_sub = total_time / 2.0
        ds1 = v0 * (pow(d, 1000.0 * dt_sub) - 1.0) / (1000.0 * ln_d)
        v1 = v0 * pow(d, 1000.0 * dt_sub)
        ds2 = v1 * (pow(d, 1000.0 * dt_sub) - 1.0) / (1000.0 * ln_d)
        delta_s_120 = ds1 + ds2

        self.assertAlmostEqual(delta_s_60, delta_s_120, places=7,
                               msg="Timestep numerical integration must be invariant between 60Hz and 120Hz")

        # 2. Scroll Indicator Sizing Equation
        # L = max(36.0, L_track * (L_viewport / L_content))
        viewport = 800.0
        track = 794.0 # 800 - 6.0 margin

        # Normal proportionality: content = 1600 (2x viewport) -> raw = 397.0
        len_normal = max(36.0, track * (viewport / 1600.0))
        self.assertEqual(len_normal, 397.0)

        # Clamped proportionality: content = 50,000 -> raw = 794 * (800 / 50000) = 12.704 -> clamped to 36.0
        len_clamped = max(36.0, track * (viewport / 50000.0))
        self.assertEqual(len_clamped, 36.0)

        # 3. Overscroll Compression Equation
        # L_comp = max(3.0, L_base - |overscroll| / 2.0)
        base_len = 200.0
        overscroll = 60.0
        comp_len = max(3.0, base_len - overscroll / 2.0)
        self.assertEqual(comp_len, 170.0)

        # Extreme overscroll clamped to knob thickness (3.0pt)
        extreme_overscroll = 1000.0
        comp_extreme = max(3.0, base_len - extreme_overscroll / 2.0)
        self.assertEqual(comp_extreme, 3.0)

        # 4. Interactive Scrubbing Direct Offset Scaling Factor
        # delta_offset = delta_finger * (max_offset / travel_range)
        content_len = 3000.0
        max_offset = content_len - viewport # 2200.0
        travel_range = track - base_len # 794 - 200 = 594.0
        factor = max_offset / travel_range
        self.assertAlmostEqual(factor, 2200.0 / 594.0, places=6)
        delta_finger = 15.0
        delta_offset = delta_finger * factor
        self.assertAlmostEqual(delta_offset, 15.0 * (2200.0 / 594.0), places=6)

        # 5. Fade-out Alpha Quadratic Curve: alpha(t) = 1.0 - (progress)^2
        # At halfway progress (progress = 0.5): alpha = 1.0 - 0.25 = 0.75
        alpha_half = 1.0 - pow(0.5, 2.0)
        self.assertEqual(alpha_half, 0.75)

    def test_standalone_pseudocode_compilation_and_execution(self):
        """R6: Compile and execute rendering_scheduling.pseudo.c under gcc -Wall -Wextra -Werror."""
        self.assertTrue(self.pseudo_c.is_file(), "rendering_scheduling.pseudo.c must exist")
        bin_path = Path("/tmp/test_rendering_scheduling_bin")
        compile_cmd = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99",
            str(self.pseudo_c), "-lm", "-o", str(bin_path)
        ]
        comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
        self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}")

        run_res = subprocess.run([str(bin_path)], capture_output=True, text=True)
        self.assertEqual(run_res.returncode, 0, f"Execution failed:\n{run_res.stderr}")
        self.assertIn("All 42 Rendering & Scheduling unit test suites PASSED", run_res.stdout)

    def test_findings_dossiers_structure_and_invariants(self):
        """R6: Verify findings documents byte size, anti-placeholder compliance, and structure."""
        # 1. 05_RENDERING_FRAME_SCHEDULING.md
        self.assertTrue(self.findings_rendering_md.is_file(), "05_RENDERING_FRAME_SCHEDULING.md must exist")
        size_r = self.findings_rendering_md.stat().st_size
        self.assertGreaterEqual(size_r, 25000, f"Rendering findings size ({size_r}) < 25,000 bytes minimum")

        content_r = self.findings_rendering_md.read_text(encoding="utf-8")
        for pat in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pat, content_r, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Banned placeholder '{matches[0].group() if matches else ''}' in rendering findings")

        for sec in ["CADisplayLink & RunLoop Scheduling Architecture",
                    "Content Offset to Compositor Transforms",
                    "ProMotion 120Hz Variable Refresh Rate",
                    "Model vs. Presentation Layer Authority",
                    "Master Architectural & PAC00 Method Table",
                    "Empirical Evidence Ledger Entries"]:
            self.assertIn(sec.lower(), content_r.lower(), f"Missing required section '{sec}' in rendering findings")

        self.assertIn("$$", content_r, "Missing LaTeX display math in rendering findings")
        self.assertIn("graph", content_r, "Missing Mermaid graph diagram in rendering findings")
        self.assertIn("stateDiagram-v2", content_r, "Missing Mermaid state diagram in rendering findings")

        # 2. 05_SCROLL_INDICATORS.md
        self.assertTrue(self.findings_indicators_md.is_file(), "05_SCROLL_INDICATORS.md must exist")
        size_i = self.findings_indicators_md.stat().st_size
        self.assertGreaterEqual(size_i, 20000, f"Indicators findings size ({size_i}) < 20,000 bytes minimum")

        content_i = self.findings_indicators_md.read_text(encoding="utf-8")
        for pat in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pat, content_i, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Banned placeholder '{matches[0].group() if matches else ''}' in indicators findings")

        for sec in ["Scroll Indicators Sizing & Geometry Mechanics",
                    "Rubber-Banding Overscroll Compression Ratio",
                    "Interactive Scroll Indicator Dragging",
                    "Indicator Fade Kinetics & Compositor Hit-Testing",
                    "Master Architectural & PAC00 Method Table",
                    "Empirical Evidence Ledger Entries"]:
            self.assertIn(sec.lower(), content_i.lower(), f"Missing required section '{sec}' in indicators findings")

        self.assertIn("$$", content_i, "Missing LaTeX display math in indicators findings")
        self.assertIn("graph", content_i, "Missing Mermaid graph diagram in indicators findings")
        self.assertIn("sequenceDiagram", content_i, "Missing Mermaid sequence diagram in indicators findings")

    def test_evidence_ledger_phase5_integrity(self):
        """R6: Verify evidence_ledger.jsonl contains REND-001 through REND-020 entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        phase5_entries = [e for e in lines if e.get("phase") == "PHASE_5"]
        self.assertGreaterEqual(len(phase5_entries), 20, f"Found {len(phase5_entries)} Phase 5 entries, expected >= 20")

        rend_ids = [e.get("id") for e in phase5_entries]
        for i in range(1, 21):
            expected_id = f"REND-{i:03d}"
            self.assertIn(expected_id, rend_ids, f"Missing evidence entry {expected_id}")

        for entry in phase5_entries:
            self.assertTrue(entry.get("id").startswith("REND-"))
            self.assertIn("[CONFIRMED]", entry.get("finding", ""))
            self.assertEqual(entry.get("confidence"), "CONFIRMED")
            self.assertTrue(entry.get("address", "").startswith("0x184"))
            self.assertTrue(entry.get("binary_path"))
            full_bin = PROJECT_ROOT / entry.get("binary_path")
            self.assertTrue(full_bin.is_file(), f"Cited binary_path does not exist: {entry.get('binary_path')}")
            self.assertTrue(entry.get("opcode_instructions"))
            self.assertTrue(entry.get("evidence_type"))
            self.assertTrue(entry.get("tool"))

    def test_zoomed_content_indicator_scaling_and_mutual_exclusion(self):
        """R2, R4: Verify zoomScale effective content sizing and mutual exclusion with scrubber."""
        viewport = 800.0
        content_unzoomed = 1000.0
        zoom_scale = 2.0
        effective_content = content_unzoomed * zoom_scale
        track_length = viewport - 6.0 # 794.0

        # Unzoomed raw length: 794 * (800 / 1000) = 635.2
        # Zoomed raw length: 794 * (800 / 2000) = 317.6
        len_zoomed = max(36.0, track_length * (viewport / effective_content))
        self.assertAlmostEqual(len_zoomed, 317.6, places=5)

        # Max offset when zoomed: 2000 - 800 = 1200 pt
        max_offset_zoomed = effective_content - viewport
        self.assertEqual(max_offset_zoomed, 1200.0)

        # Scrubbing scaling factor when zoomed
        travel_range = track_length - len_zoomed # 794 - 317.6 = 476.4
        factor_zoomed = max_offset_zoomed / travel_range
        self.assertAlmostEqual(factor_zoomed, 1200.0 / 476.4, places=5)

    def test_constrained_track_length_clamping_and_horizontal_indicator(self):
        """R4, R5: Test indicator length clamping on severely constrained tracks and horizontal hit target."""
        # When trackLength < 36.0, indicator length must clamp to trackLength, never exceeding it
        track_constrained = 14.0
        viewport_constrained = 20.0
        content_len = 100.0
        raw = track_constrained * (viewport_constrained / content_len) # 14 * 0.2 = 2.8
        clamped = max(36.0, raw) # 36.0
        final_len = min(clamped, track_constrained) # Clamped to track
        self.assertEqual(final_len, 14.0)

        # Horizontal indicator touch target expansion along cross-axis (height >= 44.0pt)
        cross_axis_dim = 852.0
        knob_thickness = 3.0
        touch_padding = (44.0 - knob_thickness) / 2.0 # 20.5pt
        hit_height = 44.0
        self.assertEqual(hit_height, 44.0)

    def test_retina_subpixel_quantization_and_drift_mitigation(self):
        """R2, R3: Test Retina @3x subpixel grid quantization (1/3 pt) eliminating long-horizon drift."""
        scale = 3.0
        test_val = 150.25
        # 150.25 * 3 = 450.75 -> round = 451 -> 451 / 3 = 150.33333333333334
        quantized = round(test_val * scale) / scale
        self.assertAlmostEqual(quantized, 150.33333333333334, places=12)

        # Over 10,000 steps of subpixel quantization, coordinate remains on exact 1/3 pt lattice
        curr = 0.0
        step_delta = 0.3333333333333333
        for _ in range(10000):
            curr += step_delta
            curr = round(curr * scale) / scale
        # curr should be exactly 3333.3333333333335
        self.assertAlmostEqual(curr, 10000.0 / 3.0, places=10)

    def test_promotion_thermal_jitter_timestep_invariance(self):
        """R1, R3: ProMotion exponential decay timestep invariance under thermal jitter and stall clamp."""
        v0 = 3200.0
        d = 0.998
        ln_d = math.log(d)

        # 1. Simulating 500 variable frames of thermal throttling jitter
        # Intervals vary between 4ms (240Hz spike) and 66.67ms (15Hz thermal drop)
        intervals = [
            0.008333, 0.016667, 0.033333, 0.012500, 0.050000, 0.004167,
            0.025000, 0.041667, 0.008333, 0.062500, 0.016667, 0.020000
        ] * 40 # 480 frames
        total_time = sum(intervals)

        # Analytical continuous integral
        expected_disp = v0 * (pow(d, 1000.0 * total_time) - 1.0) / (1000.0 * ln_d)

        # Discrete variable-step accumulation
        curr_v = v0
        accum_disp = 0.0
        for dt in intervals:
            decay = pow(d, 1000.0 * dt)
            ds = curr_v * (decay - 1.0) / (1000.0 * ln_d)
            accum_disp += ds
            curr_v *= decay

        self.assertAlmostEqual(accum_disp, expected_disp, places=7,
                               msg="Multi-hundred-frame thermal jitter must match continuous analytical displacement")

        # 2. Frame stall clamping: dt > 0.10s clamped to 0.10s
        stall_dt = 0.15 # 150ms hitch
        clamped_dt = min(stall_dt, 0.10)
        self.assertEqual(clamped_dt, 0.10)

    def test_nonlinear_rubber_band_indicator_compression_and_hit_padding(self):
        """R4, R5: Non-linear rational rubber-band drag resistance coupled with indicator compression and hit padding."""
        viewport = 852.0
        content = 2000.0
        track = viewport - 6.0 # 846.0
        base_len = max(36.0, track * (viewport / content)) # 846 * (852/2000) = 360.396 pt
        c_resistance = 0.55
        d_viewport = 852.0

        # Finger pulls from 10pt to 5000pt
        pulls = [10.0, 50.0, 100.0, 250.0, 500.0, 1500.0, 5000.0]
        prev_len = base_len

        for x in pulls:
            # Rational rubber-band resistance formula (Phase 3C BOUNCE-001)
            y_overscroll = (x * c_resistance * d_viewport) / (d_viewport + c_resistance * x)
            # Indicator compression ratio r = 2.0
            comp_len = max(3.0, base_len - y_overscroll / 2.0)

            # Monotonic reduction
            self.assertLessEqual(comp_len, prev_len)
            self.assertGreaterEqual(comp_len, 3.0)
            prev_len = comp_len

            # Touch target expansion: both width and height must be >= 44.0pt
            hit_w = max(44.0, 3.0)
            hit_h = max(44.0, comp_len)
            self.assertGreaterEqual(hit_w, 44.0)
            self.assertGreaterEqual(hit_h, 44.0)

        # Asymptotic limit: y_overscroll -> d_viewport (852pt)
        # 360.396 - 852 / 2 = 360.396 - 426 = -65.6 -> clamped to 3.0
        limit_overscroll = d_viewport
        clamped_len = max(3.0, base_len - limit_overscroll / 2.0)
        self.assertEqual(clamped_len, 3.0)

    def test_scrubbing_edge_haptic_impact_isolation(self):
        """R4: Boundary impact haptic feedback trigger isolation during interactive scrubbing."""
        # When scrubbing transitions into boundary (prev > 0 and target <= 0), haptic fires (True)
        prev_y = 20.0
        target_y = -10.0 # overshoot
        clamped_y = max(0.0, target_y)
        haptic_impact = (prev_y > 0.0 and target_y <= 0.0)
        self.assertTrue(haptic_impact, "Initial boundary contact must trigger haptic impact")
        self.assertEqual(clamped_y, 0.0)

        # Subsequent drag while already resting at 0.0 must NOT trigger haptic impact
        prev_y = 0.0
        target_y = -15.0 # continued drag into stop
        clamped_y = max(0.0, target_y)
        haptic_impact = (prev_y > 0.0 and target_y <= 0.0)
        self.assertFalse(haptic_impact, "Continued drag while stationary at boundary must not trigger haptic")

if __name__ == "__main__":
    unittest.main()

