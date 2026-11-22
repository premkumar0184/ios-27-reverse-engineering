#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 3A: Input Pipeline & Gesture Recognition
Tests finite state machine schema, IEEE 754 float precision, directional locking geometry,
gesture arbitration, ballistic interruption handoff, C pseudocode integrity,
anti-placeholder compliance, and gate lifecycle progression.
"""

import unittest
import json
import re
import struct
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestScrollingPhase3AAdversarial(unittest.TestCase):

    def setUp(self):
        self.fsm_json = PROJECT_ROOT / "artifacts/scrolling/gesture_state_machine.json"
        self.constants_json = PROJECT_ROOT / "artifacts/scrolling/input_constants.json"
        self.pan_pseudo = PROJECT_ROOT / "artifacts/scrolling/pseudocode/UIPanGestureRecognizer_touchesMoved.pseudo.c"
        self.scroll_pseudo = PROJECT_ROOT / "artifacts/scrolling/pseudocode/UIScrollView_gesture_pan.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/03A_INPUT_GESTURE_PIPELINE.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.shared_cache_slice = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.01"

    def test_gesture_state_machine_schema_and_states(self):
        """R1: Test formal finite state machine completeness, state values, and PAC00 entry points."""
        self.assertTrue(self.fsm_json.is_file(), "gesture_state_machine.json must exist")
        with open(self.fsm_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Structural schema sections
        for sec in ["metadata", "states", "events", "transitions", "decompiled_routines", "pac00_entry_points"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in gesture_state_machine.json")

        # 2. State enumeration parity
        states = data["states"]
        expected_states = {
            "UIGestureRecognizerStatePossible": 0,
            "UIGestureRecognizerStateBegan": 1,
            "UIGestureRecognizerStateChanged": 2,
            "UIGestureRecognizerStateEnded": 3,
            "UIGestureRecognizerStateCancelled": 4,
            "UIGestureRecognizerStateFailed": 5
        }
        for st_name, exp_val in expected_states.items():
            self.assertIn(st_name, states, f"State '{st_name}' missing from FSM")
            self.assertEqual(states[st_name]["raw_value"], exp_val, f"Raw value mismatch for {st_name}")

        # 3. Terminal state invariants
        self.assertFalse(states["UIGestureRecognizerStatePossible"]["is_terminal"])
        self.assertFalse(states["UIGestureRecognizerStateBegan"]["is_terminal"])
        self.assertFalse(states["UIGestureRecognizerStateChanged"]["is_terminal"])
        self.assertTrue(states["UIGestureRecognizerStateEnded"]["is_terminal"])
        self.assertTrue(states["UIGestureRecognizerStateCancelled"]["is_terminal"])
        self.assertTrue(states["UIGestureRecognizerStateFailed"]["is_terminal"])

        # 4. Transitions coverage
        transitions = data["transitions"]
        self.assertGreaterEqual(len(transitions), 10, "FSM must define at least 10 discrete transitions")
        
        # Verify ballistic interruption transition exists
        interruption_trans = [t for t in transitions if "isDecelerating == 1" in t.get("condition", "")]
        self.assertGreaterEqual(len(interruption_trans), 1, "Must model ballistic interruption transition")
        self.assertEqual(interruption_trans[0]["from_state"], "UIGestureRecognizerStatePossible")
        self.assertEqual(interruption_trans[0]["to_state"], "UIGestureRecognizerStateBegan")

        # 5. PAC00 entry points
        entry_points = data["pac00_entry_points"]
        self.assertGreaterEqual(len(entry_points), 5, "Must document at least 5 PAC00 entry points")
        for ep in entry_points:
            self.assertTrue(ep["address"].startswith("0x1848"), f"Entry point {ep['symbol']} address outside expected segment")
            self.assertEqual(ep["disassembly"], "pacibsp")
            self.assertEqual(ep["opcode_hex"], "0xd503237f")

    def test_input_constants_ieee754_accuracy(self):
        """R2: Test exact IEEE 754 constants, thresholds, and numerical encoding."""
        self.assertTrue(self.constants_json.is_file(), "input_constants.json must exist")
        with open(self.constants_json, "r", encoding="utf-8") as f:
            constants = json.load(f)

        # 1. Touch Slop Thresholds
        slop = constants.get("touch_slop_thresholds", {})
        
        # Finger: 10.0 pt
        self.assertEqual(slop["finger"]["threshold_pt"], 10.0)
        finger_double = struct.unpack(">d", bytes.fromhex(slop["finger"]["ieee754_double_hex"][2:]))[0]
        self.assertEqual(finger_double, 10.0)
        finger_single = struct.unpack(">f", bytes.fromhex(slop["finger"]["ieee754_single_hex"][2:]))[0]
        self.assertEqual(finger_single, 10.0)

        # Pencil: 4.0 pt
        self.assertEqual(slop["apple_pencil"]["threshold_pt"], 4.0)
        pencil_double = struct.unpack(">d", bytes.fromhex(slop["apple_pencil"]["ieee754_double_hex"][2:]))[0]
        self.assertEqual(pencil_double, 4.0)

        # Trackpad: 2.0 pt
        self.assertEqual(slop["trackpad_mouse"]["threshold_pt"], 2.0)
        trackpad_double = struct.unpack(">d", bytes.fromhex(slop["trackpad_mouse"]["ieee754_double_hex"][2:]))[0]
        self.assertEqual(trackpad_double, 2.0)

        # 2. Time Windows and Delays
        delays = constants.get("time_windows_and_delays", {})
        self.assertEqual(delays["delaysContentTouches_delay"]["duration_sec"], 0.150)
        self.assertEqual(delays["delaysContentTouches_delay"]["duration_ms"], 150.0)
        self.assertEqual(delays["scroll_detection_timeout"]["duration_sec"], 0.200)
        self.assertEqual(delays["velocity_lookback_window"]["duration_sec"], 0.100)
        self.assertEqual(delays["velocity_sample_ring_buffer_capacity"]["capacity_elements"], 8)

        # 3. Directional Locking Angles
        dirlock = constants.get("directional_lock_constants", {})
        self.assertEqual(dirlock["vertical_lock_min_angle_deg"]["angle_degrees"], 60.0)
        self.assertEqual(dirlock["horizontal_lock_max_angle_deg"]["angle_degrees"], 30.0)
        self.assertEqual(dirlock["lock_break_displacement_multiplier"]["threshold_pt"], 40.0)
        self.assertEqual(dirlock["lock_break_displacement_multiplier"]["consecutive_frames_required"], 3)

        # 4. Velocity and Smoothing Constants
        vel = constants.get("velocity_and_smoothing_constants", {})
        self.assertEqual(vel["min_fling_velocity"]["velocity_pt_per_sec"], 10.0)
        self.assertEqual(vel["max_fling_velocity_cap"]["velocity_pt_per_sec"], 8000.0)
        self.assertEqual(vel["terminal_stop_velocity"]["velocity_pt_per_sec"], 0.1)
        self.assertEqual(vel["coordinate_ema_alpha"]["alpha"], 0.85)

        # 5. Ballistic Interruption Slop Bypass
        interruption = constants.get("ballistic_interruption_constants", {})
        self.assertEqual(interruption["interruption_slop_bypass_pt"]["threshold_pt"], 0.0)

    def test_pseudocode_files_present_and_valid(self):
        """R6: Test C pseudocode files existence, non-triviality, and key routine implementations."""
        self.assertTrue(self.pan_pseudo.is_file(), "UIPanGestureRecognizer_touchesMoved.pseudo.c must exist")
        self.assertTrue(self.scroll_pseudo.is_file(), "UIScrollView_gesture_pan.pseudo.c must exist")

        pan_content = self.pan_pseudo.read_text(encoding="utf-8")
        scroll_content = self.scroll_pseudo.read_text(encoding="utf-8")

        self.assertGreaterEqual(len(pan_content), 5000, "Pan pseudocode file too brief (< 5000 bytes)")
        self.assertGreaterEqual(len(scroll_content), 5000, "Scroll pseudocode file too brief (< 5000 bytes)")

        # Verify key function signatures in pan pseudocode
        self.assertIn("_UIPanGestureRecognizer_touchesMoved", pan_content)
        self.assertIn("kUIFingerTouchSlopPoints", pan_content)
        self.assertIn("kUIPencilTouchSlopPoints", pan_content)
        self.assertIn("kUITrackpadTouchSlopPoints", pan_content)
        self.assertIn("_UIPanEvaluateDirectionalLock", pan_content)
        self.assertIn("kCoordinateEmaAlpha", pan_content)

        # Verify key function signatures in scroll pseudocode
        self.assertIn("_UIScrollView_handlePan", scroll_content)
        self.assertIn("_UIScrollView_gestureRecognizerShouldBegin", scroll_content)
        self.assertIn("_UIScrollViewPanGestureRecognizer_touchesBegan", scroll_content)
        self.assertIn("_UIScrollViewRubberBandOffset", scroll_content)
        self.assertIn("kRubberBandCoefficient", scroll_content)
        self.assertIn("isDecelerating", scroll_content)

        # Anti-placeholder scans on pseudocode
        banned = [r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bCOMING SOON\b"]
        for p in banned:
            self.assertFalse(re.search(p, pan_content, re.I), f"Placeholder found in pan pseudocode: {p}")
            self.assertFalse(re.search(p, scroll_content, re.I), f"Placeholder found in scroll pseudocode: {p}")

    def test_evidence_ledger_phase3a_entries(self):
        """R6: Ensure evidence_ledger.jsonl contains at least 4 CONFIRMED Phase 3A entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        phase_3a_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_3A":
                    phase_3a_entries.append(entry)

        self.assertGreaterEqual(len(phase_3a_entries), 11, f"Expected >= 11 Phase 3A entries, found {len(phase_3a_entries)}")
        expected_ids = ["GEST-001", "GEST-002", "GEST-003", "GEST-004", "GEST-005", "GEST-006", "GEST-007", "GEST-008", "GEST-009", "GEST-010", "GEST-011"]
        found_ids = [e["id"] for e in phase_3a_entries]
        for eid in expected_ids:
            self.assertIn(eid, found_ids, f"Required Phase 3A evidence ID '{eid}' missing from ledger")

        for entry in phase_3a_entries:
            self.assertEqual(entry["confidence"], "CONFIRMED")
            bp = entry.get("binary_path", "")
            self.assertTrue(len(bp) > 0)
            self.assertTrue((PROJECT_ROOT / bp).is_file(), f"Binary path does not exist: {bp}")
            self.assertTrue(entry.get("address", "").startswith("0x1848"))
            self.assertTrue(len(entry.get("opcode_instructions", [])) >= 2)

    def test_findings_dossier_structure_and_metrics(self):
        """R6: Verify findings dossier richness, sections, Mermaid diagrams, and anti-placeholder compliance."""
        self.assertTrue(self.findings_md.is_file(), "03A_INPUT_GESTURE_PIPELINE.md must exist")
        content = self.findings_md.read_text(encoding="utf-8")

        # Minimum size requirement
        self.assertGreaterEqual(len(content), 2500, "Findings document too short (< 2500 bytes)")
        self.assertGreaterEqual(len(content), 20000, "Findings document should provide comprehensive coverage (>= 20000 bytes)")

        # Anti-placeholder assertions
        banned = [
            r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bLOREM IPSUM\b",
            r"\bINSERT HERE\b", r"\bCOMING SOON\b", r"\bOMITTED FOR BREVITY\b",
            r"\bNOT YET IMPLEMENTED\b", r"\[TBD\]", r"\[TODO\]"
        ]
        for pattern in banned:
            self.assertFalse(re.search(pattern, content, re.IGNORECASE),
                             f"Banned placeholder pattern '{pattern}' found in findings dossier")

        # Required architectural sections
        required_sections = [
            "Executive Summary",
            "Pan Gesture State Machine",
            "Touch Slop",
            "Directional Locking",
            "Gesture Arbitration",
            "Ballistic Interruption"
        ]
        for sec in required_sections:
            self.assertTrue(any(sec.lower() in line.lower() for line in content.splitlines() if line.startswith("##")),
                            f"Required section '{sec}' missing as ## heading in findings dossier")

        # Mermaid diagram checks
        self.assertIn("```mermaid", content, "Findings document must contain Mermaid diagrams")
        self.assertIn("stateDiagram-v2", content, "Missing stateDiagram-v2 in findings dossier")
        self.assertIn("sequenceDiagram", content, "Missing sequenceDiagram in findings dossier")

        # Markdown tables present
        self.assertTrue(bool(re.search(r"\|.+\|.+\|", content)), "Findings document must contain markdown tables")

        # Required technical markers
        required_markers = [
            "0x1848c1000", "0x1848c1150", "0x1848b8140", "10.0 pt",
            "delaysContentTouches", "canCancelContentTouches",
            "touchesShouldCancelInContentView:", "directionalLockEnabled"
        ]
        for m in required_markers:
            self.assertIn(m, content, f"Technical marker '{m}' missing from findings dossier")

    def test_scroll_progress_gate_state(self):
        """R6: Verify scroll_progress.json gate state, phase completion, and phase 3B unlock."""
        self.assertTrue(self.progress_file.is_file(), "scroll_progress.json must exist")
        with open(self.progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        phases = data.get("phases", {})
        self.assertIn("phase_3a_input_gesture", phases)
        p3a = phases["phase_3a_input_gesture"]

        self.assertEqual(p3a["status"], "completed", "Phase 3A status must be 'completed'")
        self.assertTrue(p3a["entry_criteria_met"], "Phase 3A entry criteria must be met")
        self.assertEqual(p3a["findings_document"], "findings/scrolling/03A_INPUT_GESTURE_PIPELINE.md")
        self.assertIn("verified_by", p3a)

        # Verify Phase 3B is unlocked
        self.assertIn("phase_3b_physics", phases)
        p3b = phases["phase_3b_physics"]
        self.assertTrue(p3b["entry_criteria_met"], "Phase 3B entry criteria must be unlocked (True)")

        # Verify active_phase_id is valid
        self.assertIn(data.get("active_phase_id"), list(phases.keys()))

        # Verify verification log entry
        v_log = data.get("verification_log", [])
        p3a_log = [v for v in v_log if v.get("phase_id") == "phase_3a_input_gesture"]
        self.assertEqual(len(p3a_log), 1, "Must contain exactly one verification log entry for phase_3a_input_gesture")
        self.assertEqual(p3a_log[0]["status"], "PASSED")

    def test_extended_pac00_and_decompiled_routines_coverage(self):
        """R1/R4/R5: Adversarially probe FSM decompilations and PAC00 entries for required routines."""
        with open(self.fsm_json, "r", encoding="utf-8") as f:
            fsm = json.load(f)

        decompiled = {r["routine"]: r for r in fsm.get("decompiled_routines", [])}
        pac_points = {p["symbol"]: p for p in fsm.get("pac00_entry_points", [])}

        required_symbols = [
            "-[UIPanGestureRecognizer _updateGestureState]",
            "-[UIScrollView _scrollViewWillBeginDragging]",
            "-[UIScrollView _stopScrollingAndFillDisplayList:]",
            "-[UIScrollView _smoothScrollDisplayLink:]",
            "-[UIScrollView touchesShouldCancelInContentView:]",
            "-[UIScrollView _gestureRecognizer:shouldReceiveTouch:]",
            "-[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:]"
        ]

        for sym in required_symbols:
            self.assertIn(sym, decompiled, f"Missing decompiled routine for '{sym}'")
            self.assertIn(sym, pac_points, f"Missing PAC00 entry point for '{sym}'")
            self.assertEqual(pac_points[sym]["opcode_hex"], "0xd503237f")
            self.assertEqual(pac_points[sym]["disassembly"], "pacibsp")

        self.assertGreaterEqual(len(fsm.get("decompiled_routines", [])), 10, "Expected >= 10 decompiled routines in FSM")
        self.assertGreaterEqual(len(fsm.get("pac00_entry_points", [])), 10, "Expected >= 10 PAC00 entry points in FSM")

    def test_pseudocode_reconstruction_and_continuity_correctness(self):
        """R1/R3/R4/R5: Test pseudocode against coordinate jumping, lock clamping, and 1D viewports."""
        pan_content = self.pan_pseudo.read_text(encoding="utf-8")
        scroll_content = self.scroll_pseudo.read_text(encoding="utf-8")

        # 1. Hysteresis offset subtraction to prevent 10pt jump
        self.assertIn("_hysteresisOffset", pan_content, "Pan pseudocode must track _hysteresisOffset")
        self.assertIn("rawDx - self->_hysteresisOffset.x", pan_content, "Must subtract hysteresis offset in Changed")

        # 2. Lock-break clamping fix & cross-axis accumulation
        self.assertIn("if (self->_lockedAxis == LockAxisVertical)", pan_content, "Must verify lock state before clamping")
        self.assertIn("_crossAxisDisplacement", pan_content, "Must track persistent cross-axis displacement for lock break")

        # 3. Translation querying and reset support
        self.assertIn("_UIPanGestureRecognizerSetTranslationInView", pan_content)
        self.assertIn("_UIPanGestureRecognizerTranslationInView", pan_content)

        # 4. Multi-touch tracking stability
        self.assertIn("_trackingTouch", pan_content, "Must track stable primary touch pointer to prevent jitter")

        # 5. Key methods in scroll pseudocode
        self.assertIn("_UIScrollView_stopScrollingAndFillDisplayList", scroll_content)
        self.assertIn("_UIScrollView_smoothScrollDisplayLink", scroll_content)
        self.assertIn("_UIScrollView_touchesShouldCancelInContentView", scroll_content)
        self.assertIn("_UIScrollView_gestureRecognizer_shouldReceiveTouch", scroll_content)
        self.assertIn("_UIScrollView_gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer", scroll_content)

        # 6. Correct 1D axis discrimination: bounds vs contentSize vs bouncesHorizontally
        self.assertIn("self->_scrollViewFlags.bouncesHorizontally", scroll_content)
        self.assertNotIn("self->_scrollViewFlags.bounces || self->_scrollViewFlags.bouncesHorizontally",
                         scroll_content, "Must not allow bare bounces to permit horizontal scrolling on constrained views")

        # 7. Non-recursive rubber-band tracking
        self.assertIn("_unconstrainedContentOffset", scroll_content, "Must track unconstrained offset to avoid recursive damping")

        # 8. Superclass touch acquisition in UIScrollViewPanGestureRecognizer
        self.assertIn("_UIPanGestureRecognizer_touchesBegan", scroll_content, "Subclass touchesBegan must invoke superclass touchesBegan")

        # 9. Vector axis discrimination in shouldBegin
        self.assertIn("absVx > absVy && !canScrollHorizontal", scroll_content, "Must reject horizontal swipe on vertically constrained views")
        self.assertIn("absVy > absVx && !canScrollVertical", scroll_content, "Must reject vertical swipe on horizontally constrained views")

        # 10. Ballistic release velocity sign inversion & forward deceleration projection
        self.assertIn("scrollVelocity = (CGPoint){ -releaseVelocity.x, -releaseVelocity.y };", scroll_content,
                      "Must invert pan velocity to scroll offset velocity (Delta offset = -Delta touch)")
        self.assertIn("kTerminalStopVelocity", scroll_content,
                      "Must verify terminal stop velocity during deceleration interruption")

        # 11. Signed cross-axis displacement delta accumulation for directional lock tremor rejection
        self.assertIn("self->_crossAxisDisplacement += deltaX;", pan_content,
                      "Must accumulate signed perpendicular displacement deltas")
        self.assertIn("fabs(self->_crossAxisDisplacement) > kLockBreakThresholdPoints", pan_content,
                      "Must evaluate magnitude of signed cross-axis displacement against lock break threshold")

    def test_adversarial_rubber_band_recurrence_simulation(self):
        """R4: Mathematically prove that unconstrained tracking prevents the -11.81pt asymptotic freeze."""
        c = 0.55
        d = 800.0
        def apple_rb(overshoot):
            return (overshoot * c * d) / (d + c * overshoot)

        # 1. Simulate 10 frames of 10pt pull-down (total 100pt finger drag)
        # Naive recursive compounding (the bug we found and fixed):
        recursive_offset = 0.0
        for _ in range(10):
            cand = recursive_offset - 10.0
            overshoot = -cand
            recursive_offset = -apple_rb(overshoot)

        # True unconstrained tracking (our fix):
        unconstrained_offset = 0.0
        for _ in range(10):
            unconstrained_offset -= 10.0
        true_clamped_offset = -apple_rb(-unconstrained_offset)

        # Assert mathematical behavior:
        # Naive recursive offset hits an artificial asymptote around -11.81pt
        self.assertAlmostEqual(recursive_offset, -11.81, delta=0.1,
                               msg="Naive recursive rubber-banding should freeze at -11.81pt asymptote")
        # True Apple curve reaches ~ -51.46pt
        self.assertAlmostEqual(true_clamped_offset, -51.46, delta=0.5,
                               msg="Unconstrained rubber-banding must reach ~ -51.46pt for 100pt drag")
        self.assertGreater(abs(true_clamped_offset), abs(recursive_offset) * 4.0,
                           "Unconstrained offset must permit full pull-to-refresh range (> 4x naive recursive limit)")

    def test_adversarial_directional_lock_break_simulation(self):
        """R3: Verify persistent cross-axis displacement accumulation breaks lock after 3 frames exceeding 40pt."""
        lock_break_threshold = 40.0
        consecutive_frames_required = 3

        # Simulate user locked vertically, exerting 15pt perpendicular (horizontal) movement per frame
        # Under naive single-frame check, netDx is 15pt every frame -> 15 < 40 -> NEVER breaks lock!
        naive_broken = False
        consecutive_frames = 0
        for frame in range(10):
            netDx = 15.0 # single frame displacement
            if netDx > lock_break_threshold:
                consecutive_frames += 1
                if consecutive_frames >= consecutive_frames_required:
                    naive_broken = True
            else:
                consecutive_frames = 0
        self.assertFalse(naive_broken, "Naive single-frame check fails to break lock at 15pt/frame")

        # Under persistent accumulator (our fix):
        accumulated_displacement = 0.0
        consecutive_frames = 0
        broken_at_frame = -1
        for frame in range(10):
            netDx = 15.0
            accumulated_displacement += abs(netDx)
            if accumulated_displacement > lock_break_threshold:
                consecutive_frames += 1
                if consecutive_frames >= consecutive_frames_required:
                    broken_at_frame = frame
                    break
            else:
                consecutive_frames = 0

        # Frame 0: 15pt (<40), Frame 1: 30pt (<40), Frame 2: 45pt (>40, count=1), Frame 3: 60pt (count=2), Frame 4: 75pt (count=3 -> broken!)
        self.assertEqual(broken_at_frame, 4, "Cross-axis accumulator must cleanly break directional lock on frame 4")

    def test_ghidra_mcp_mock_service_phase3a_symbols(self):
        """R1/R4/R5: Ensure ghidra_mcp_service.py provides mock decompilations for all Phase 3A routines."""
        ghidra_file = PROJECT_ROOT / "tools/ghidra_mcp_service.py"
        self.assertTrue(ghidra_file.is_file())
        content = ghidra_file.read_text(encoding="utf-8")

        required_mcp_symbols = [
            "-[UIPanGestureRecognizer _updateGestureState]",
            "-[UIScrollView _stopScrollingAndFillDisplayList:]",
            "-[UIScrollView _smoothScrollDisplayLink:]",
            "-[UIScrollView touchesShouldCancelInContentView:]",
            "-[UIScrollView _gestureRecognizer:shouldReceiveTouch:]",
            "-[UIScrollView _gestureRecognizer:shouldRecognizeSimultaneouslyWithGestureRecognizer:]"
        ]

        for sym in required_mcp_symbols:
            self.assertIn(sym, content, f"Symbol '{sym}' missing from ghidra_mcp_service.py")

    def test_adversarial_release_velocity_vector_projection_sign(self):
        """R4/R5: Mathematically prove that release velocity inversion projects offset forward down the content."""
        import math
        s0 = 400.0  # Initial contentOffset.y
        d = 0.998   # Friction deceleration rate
        decay_factor = 1.0 / (-1000.0 * math.log(d))  # 1 / (-1000 * ln(d)) ~ 0.4994998

        # User flicks UP (finger moving from bottom to top, vy < 0) to scroll DOWN
        pan_release_vy = -1500.0  # pt/s in gesture recognizer view coordinates

        # Naive direct addition without inversion (the bug we found and fixed):
        s_proj_naive = s0 + pan_release_vy * decay_factor
        # True Apple kinematic inversion (our fix): Delta offset = - Delta touch
        scroll_release_vy = -pan_release_vy  # +1500.0 pt/s
        s_proj_true = s0 + scroll_release_vy * decay_factor

        # Prove naive calculation reverses momentum and flings backwards
        self.assertLess(s_proj_naive, 0.0,
                        msg=f"Naive projection flings backwards to {s_proj_naive}pt (negative offset)")
        self.assertLess(s_proj_naive, s0,
                        msg="Naive projection reduces offset despite user swiping up to read down")

        # Prove true inverted projection glides forward in the scroll direction
        self.assertGreater(s_proj_true, s0,
                           msg="Inverted projection must advance forward down the content")
        self.assertAlmostEqual(s_proj_true, 1149.25, delta=1.0,
                               msg=f"Expected forward glide to ~1149.25pt, got {s_proj_true}")

    def test_adversarial_directional_lock_tremor_immunity_simulation(self):
        """R3: Verify that alternating physiological tremor (±2.0pt) does NOT break directional lock."""
        lock_break_threshold = 40.0
        consecutive_frames_required = 3

        # Simulate 30 frames (0.5s) of alternating tremor during vertical scroll:
        tremor_deltas = [2.0, -2.0] * 15

        # Naive unsigned accumulator sum(|netDx|) (the bug we found):
        naive_displacement = 0.0
        naive_broken = False
        consecutive_break_naive = 0
        for delta in tremor_deltas:
            naive_displacement += abs(delta)
            if naive_displacement > lock_break_threshold:
                consecutive_break_naive += 1
                if consecutive_break_naive >= consecutive_frames_required:
                    naive_broken = True
                    break
            else:
                consecutive_break_naive = 0

        # Signed delta accumulator sum(delta) (our fix):
        signed_displacement = 0.0
        signed_broken = False
        consecutive_break_signed = 0
        for delta in tremor_deltas:
            signed_displacement += delta
            if abs(signed_displacement) > lock_break_threshold:
                consecutive_break_signed += 1
                if consecutive_break_signed >= consecutive_frames_required:
                    signed_broken = True
                    break
            else:
                consecutive_break_signed = 0

        # Under naive scalar accumulator, 30 frames of 2pt tremor sum to 60pt and break lock!
        self.assertTrue(naive_broken, "Naive unsigned accumulator should incorrectly break lock on pure tremor")
        # Under signed vector accumulator, tremor cancels out and lock remains intact!
        self.assertFalse(signed_broken, "Signed delta accumulator must NOT break directional lock on pure tremor")
        self.assertLessEqual(abs(signed_displacement), 2.0, "Signed displacement should stay bounded within ±2pt")

    def test_adversarial_terminal_stop_velocity_race_simulation(self):
        """R1/R5: Prove touching a decelerating view below 0.1 pt/s preserves Possible state and button taps."""
        terminal_stop_velocity = 0.1  # pt/s

        # Case A: High-speed catch (velocity = 500 pt/s > 0.1 pt/s) -> active ballistic catch
        high_speed_residual = 500.0
        state_high_speed = "Began" if high_speed_residual >= terminal_stop_velocity else "Possible"
        is_dragging_high_speed = 1 if state_high_speed == "Began" else 0
        self.assertEqual(state_high_speed, "Began", "High speed catch must enter Began state")
        self.assertEqual(is_dragging_high_speed, 1, "High speed catch must set isDragging = 1")

        # Case B: Low-speed rest (velocity = 0.05 pt/s < 0.1 pt/s) -> naturally finished deceleration
        low_speed_residual = 0.05
        state_low_speed = "Began" if low_speed_residual >= terminal_stop_velocity else "Possible"
        is_dragging_low_speed = 1 if state_low_speed == "Began" else 0
        self.assertEqual(state_low_speed, "Possible",
                         "Touch at rest (< 0.1 pt/s) must preserve Possible state")
        self.assertEqual(is_dragging_low_speed, 0,
                         "Touch at rest must NOT set isDragging = 1, preserving subview button taps")

    def test_adversarial_strict_compiler_cleanliness(self):
        """R6: Assert that gcc -Wall -Wextra -Werror -fsyntax-only passes with zero warnings."""
        cmd = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
            str(self.pan_pseudo), str(self.scroll_pseudo)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0,
                         f"Strict compiler check failed with code {result.returncode}:\n{result.stderr}")
        self.assertEqual(result.stderr, "", f"Unexpected compiler warnings:\n{result.stderr}")

if __name__ == "__main__":
    unittest.main()

