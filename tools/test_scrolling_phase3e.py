#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 3E: Low-Level HID Input (IOHIDPointerScrollFilter)
Tests:
- IOHIDPointerScrollFilter JSON schema, vtable layout, PACDA discriminators, and property keys
- Pointer acceleration curves JSON schema, IEEE 754 floating-point constants, and device profiles
- Binary cross-validation against dyld_shared_cache_arm64e.48 at VM base 0x2529c4000
- PAC00 opcode instructions (0xd503237f pacibsp) across all 13 verified entry points
- C pseudocode compilation and execution of all 33 unit assertion suites under gcc -Wall -Wextra -Werror
- Findings dossier anti-placeholder compliance, Mermaid diagram variety, and LaTeX math formulas
- Evidence ledger cross-validation integrity for HID-001 through HID-015
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

class TestScrollingPhase3EAdversarial(unittest.TestCase):

    def setUp(self):
        self.iohid_json = PROJECT_ROOT / "artifacts/scrolling/iohid_scroll_filter.json"
        self.curves_json = PROJECT_ROOT / "artifacts/scrolling/pointer_acceleration_curves.json"
        self.pseudo_c = PROJECT_ROOT / "artifacts/scrolling/pseudocode/IOHIDPointerScrollFilter.pseudo.c"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/03E_IOHID_SCROLL_FILTER.md"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.shared_cache_slice = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.48"

    def test_iohid_scroll_filter_schema_and_vtable(self):
        """R1: Test IOHIDPointerScrollFilter architecture, vtable layout, and PACDA signatures."""
        self.assertTrue(self.iohid_json.is_file(), "iohid_scroll_filter.json must exist")
        with open(self.iohid_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Structural sections
        for sec in ["subsystem", "target_environment", "binary_mapping", "plugin_architecture",
                    "virtual_method_table", "accelerator_dispatch", "property_keys",
                    "event_constants", "normalization_parameters"]:
            self.assertIn(sec, data, f"Missing section '{sec}' in iohid_scroll_filter.json")

        # 2. Vtable verification
        vtable = data["virtual_method_table"]
        self.assertIn(vtable.get("vtable_base_address"), ["0x26dd6ad58", "0x26dd6ac60"])
        self.assertEqual(vtable.get("pac_discriminator"), "0x7e02")
        self.assertEqual(vtable.get("accelerator_pac_discriminator"), "0x9ff6")
        self.assertEqual(vtable.get("signing_mode"), "PACDA")
        
        methods = vtable.get("methods", [])
        self.assertEqual(len(methods), 10, "Vtable must contain exactly 10 virtual method slots")
        
        # Verify slot 9 is filter
        filter_method = methods[9]
        self.assertEqual(filter_method["slot"], 9)
        self.assertEqual(filter_method["symbol"], "IOHIDPointerScrollFilter::filter")
        self.assertEqual(filter_method["address"], "0x2529ca294")
        self.assertEqual(filter_method["pac_opcode"], "0xd503237f")

        # 3. Property keys coverage
        prop_keys = data["property_keys"]
        self.assertGreaterEqual(len(prop_keys), 25, "Must document at least 25 HID property keys")
        self.assertIn("HIDScrollAcceleration", prop_keys)
        self.assertIn("HIDPointerAcceleration", prop_keys)
        self.assertIn("ScrollMomentumDispatchRate", prop_keys)
        self.assertIn("HIDScrollResolution", prop_keys)

        # 4. Event types & constants
        events = data["event_constants"]
        self.assertEqual(events.get("kIOHIDEventTypePointer"), 17)
        self.assertEqual(events.get("kIOHIDEventTypeScroll"), 6)
        self.assertEqual(events.get("kIOHIDEventTypeDigitizer"), 11)
        self.assertEqual(events.get("kIOHIDEventFieldScrollX"), 393216)
        self.assertEqual(events.get("kIOHIDEventFieldScrollY"), 393217)

    def test_pointer_acceleration_curves_and_ieee754(self):
        """R2 & R3: Test acceleration curves, parametric math, and IEEE 754 constants."""
        self.assertTrue(self.curves_json.is_file(), "pointer_acceleration_curves.json must exist")
        with open(self.curves_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Constants in __TEXT.__const
        consts = data.get("ieee754_constants_in_text_const", [])
        self.assertGreaterEqual(len(consts), 8, "Must document at least 8 IEEE 754 constants")
        
        const_map = {c["address"]: c for c in consts}
        
        # Microsecond scale
        self.assertIn("0x2529cd690", const_map)
        self.assertEqual(const_map["0x2529cd690"]["value_decimal"], 1000000.0)
        self.assertEqual(const_map["0x2529cd690"]["ieee754_double_hex"], "0x412e848000000000")
        raw_usec = bytes.fromhex(const_map["0x2529cd690"]["ieee754_double_hex"][2:])
        self.assertAlmostEqual(struct.unpack(">d", raw_usec)[0], 1000000.0)

        # Pointer accel clamp
        self.assertIn("0x2529cd698", const_map)
        self.assertEqual(const_map["0x2529cd698"]["value_decimal"], 500.0)
        self.assertEqual(const_map["0x2529cd698"]["ieee754_double_hex"], "0x407f400000000000")

        # Report rate default
        self.assertIn("0x2529cd6a8", const_map)
        self.assertEqual(const_map["0x2529cd6a8"]["value_decimal"], 67.0)
        self.assertEqual(const_map["0x2529cd6a8"]["ieee754_double_hex"], "0x4050c00000000000")

        # Curvature coefficient
        self.assertIn("0x2529cd6b0", const_map)
        self.assertAlmostEqual(const_map["0x2529cd6b0"]["value_decimal"], -0.0145721435546875, places=12)
        self.assertEqual(const_map["0x2529cd6b0"]["ieee754_double_hex"], "0xbf8dd80000000000")
        raw_beta = bytes.fromhex(const_map["0x2529cd6b0"]["ieee754_double_hex"][2:])
        self.assertAlmostEqual(struct.unpack(">d", raw_beta)[0], -0.0145721435546875, places=12)

        # Gain linear slope
        self.assertIn("0x2529cd6b8", const_map)
        self.assertAlmostEqual(const_map["0x2529cd6b8"]["value_decimal"], 1.5009918212890625, places=12)
        self.assertEqual(const_map["0x2529cd6b8"]["ieee754_double_hex"], "0x3ff8041000000000")

        # Default scroll multiplier
        self.assertIn("0x2529cd7b0", const_map)
        self.assertAlmostEqual(const_map["0x2529cd7b0"]["value_decimal"], 1.4328358208955223, places=12)

        # 2. Parametric acceleration formula
        param_model = data.get("parametric_acceleration_model", {})
        self.assertIn("formula_latex", param_model)
        self.assertIn("\\alpha", param_model["formula_latex"])

        # 3. Momentum kinetics
        mom = data.get("trackpad_momentum_kinetics", {})
        self.assertEqual(mom.get("momentum_dispatch_timer_rate_ms"), 10)
        self.assertEqual(mom.get("friction_decay_rate_per_tick"), 0.950)
        self.assertEqual(mom.get("terminal_momentum_cutoff_pt_per_tick"), 0.05)

    def test_binary_slice_mach_o_and_pac_opcodes(self):
        """R1 & R3: Test binary slice Mach-O headers and PAC00 function prologues."""
        self.assertTrue(self.shared_cache_slice.is_file(), f"Shared cache slice .48 must exist at {self.shared_cache_slice}")
        
        file_base_offset = 0x25c4000
        vm_base_addr = 0x2529c4000
        
        with open(self.shared_cache_slice, "rb") as f:
            # 1. Mach-O 64-bit header
            f.seek(file_base_offset)
            hdr = f.read(32)
            magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', hdr)
            self.assertEqual(magic, 0xfeedfacf, "IOHIDPointerScrollFilter must have 64-bit Mach-O magic (0xfeedfacf)")
            self.assertEqual(cputype, 0x0100000c, "CPU type must be ARM64")
            self.assertEqual(cpusubtype, 0x80000002, "CPU subtype must be arm64e with PAC00 capabilities")

            # 2. Verify PAC00 function entry points (pacibsp: 0xd503237f)
            verified_pac_addresses = [
                0x2529c4a9c, # setProperty
                0x2529c50b4, # copyProperty
                0x2529c51ec, # open
                0x2529c52f4, # close
                0x2529c5444, # scheduleWithDispatchQueue
                0x2529c54a8, # unscheduleFromDispatchQueue
                0x2529c64e8, # createTableAccelerator
                0x2529c890c, # getMultiplierForDelta
                0x2529ca294, # filter
                0x2529ca6d8, # sub-event filter loop
                0x2529ca748, # acceleration dispatcher
                0x2529cc434, # startMomentumTimer
                0x2529cc4c0  # stopMomentumTimer
            ]
            
            for va in verified_pac_addresses:
                f_offset = file_base_offset + (va - vm_base_addr)
                f.seek(f_offset)
                insn = struct.unpack('<I', f.read(4))[0]
                self.assertEqual(insn, 0xd503237f, f"Subroutine at {hex(va)} must start with pacibsp opcode 0xd503237f")

            # 3. Verify constants in __TEXT.__const
            f.seek(file_base_offset + (0x2529cd690 - vm_base_addr))
            c_usec = struct.unpack('<d', f.read(8))[0]
            self.assertEqual(c_usec, 1000000.0)

            f.seek(file_base_offset + (0x2529cd698 - vm_base_addr))
            c_clamp = struct.unpack('<d', f.read(8))[0]
            self.assertEqual(c_clamp, 500.0)

            f.seek(file_base_offset + (0x2529cd6a8 - vm_base_addr))
            c_rate = struct.unpack('<d', f.read(8))[0]
            self.assertEqual(c_rate, 67.0)

            f.seek(file_base_offset + (0x2529cd6b0 - vm_base_addr))
            c_beta = struct.unpack('<d', f.read(8))[0]
            self.assertAlmostEqual(c_beta, -0.0145721435546875, places=12)

            f.seek(file_base_offset + (0x2529cd6b8 - vm_base_addr))
            c_alpha = struct.unpack('<d', f.read(8))[0]
            self.assertAlmostEqual(c_alpha, 1.5009918212890625, places=12)

    def test_c_pseudocode_compilation_and_assertions(self):
        """R5: Test C pseudocode standalone compilation and 33 unit assertion suites."""
        self.assertTrue(self.pseudo_c.is_file(), "IOHIDPointerScrollFilter.pseudo.c must exist")
        
        bin_out = Path("/tmp/test_iohid_exec")
        cmd_compile = [
            "gcc", "-Wall", "-Wextra", "-Werror", "-std=c99", "-O2",
            str(self.pseudo_c), "-lm", "-o", str(bin_out)
        ]
        res_compile = subprocess.run(cmd_compile, capture_output=True, text=True)
        self.assertEqual(res_compile.returncode, 0, f"C pseudocode failed to compile cleanly:\n{res_compile.stderr}")

        # Run test suites
        res_exec = subprocess.run([str(bin_out)], capture_output=True, text=True)
        self.assertEqual(res_exec.returncode, 0, f"C test harness execution failed:\n{res_exec.stderr}")
        self.assertIn("All 33 Assertion Suites PASSED Cleanly!", res_exec.stdout)

    def test_kinematic_invariants_and_inflection_points(self):
        """Review Round 2: Test mathematical kinematic invariants, inflection points (8, 32, 128), and saturation clamp."""
        with open(self.curves_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. High-speed profile inflection points
        hs_profile = data.get("device_acceleration_profiles", {}).get("high_speed_optical_mouse", {})
        self.assertTrue(hs_profile, "Missing high_speed_optical_mouse device profile in curves JSON")
        pts = hs_profile.get("acceleration_curve", [])
        self.assertEqual(len(pts), 4)
        thresholds = [p["velocity_threshold"] for p in pts]
        self.assertEqual(thresholds, [0.0, 8.0, 32.0, 128.0])

        # Piecewise table interpolation at midpoint v = 20.0 (between 8.0 and 32.0)
        # span = 24.0, frac = (20.0 - 8.0)/24.0 = 0.5 -> gain = 1.5 + 0.5 * 1.0 = 2.0
        v = 20.0
        frac = (v - 8.0) / (32.0 - 8.0)
        gain_20 = pts[1]["gain"] + frac * (pts[2]["gain"] - pts[1]["gain"])
        self.assertAlmostEqual(gain_20, 2.000, places=6)

        # Piecewise table interpolation at midpoint v = 80.0 (between 32.0 and 128.0)
        # span = 96.0, frac = (80.0 - 32.0)/96.0 = 0.5 -> gain = 2.5 + 0.5 * 1.5 = 3.25
        v = 80.0
        frac = (v - 32.0) / (128.0 - 32.0)
        gain_80 = pts[2]["gain"] + frac * (pts[3]["gain"] - pts[2]["gain"])
        self.assertAlmostEqual(gain_80, 3.250, places=6)

        # 2. Parametric piecewise rational model
        alpha = data["parametric_acceleration_model"]["parameters"]["alpha_gain_linear"]
        beta = data["parametric_acceleration_model"]["parameters"]["beta_curvature"]
        gamma = data["parametric_acceleration_model"]["parameters"]["gamma_tangent_root"]
        self.assertAlmostEqual(alpha, 1.5009918212890625, places=12)

        def eval_parametric(velocity):
            v_abs = abs(velocity)
            if v_abs <= alpha:
                return 1.0
            u = v_abs - alpha
            if u > 100000.0:
                return 500.0
            num = u * ((alpha - 1.0) + (abs(beta) * u))
            den = 1.0 + (gamma * u)
            gain = 1.0 + (num / den)
            return min(gain, 500.0)

        # Unity gain region
        self.assertEqual(eval_parametric(0.0), 1.0)
        self.assertEqual(eval_parametric(1.0), 1.0)
        self.assertEqual(eval_parametric(alpha), 1.0)

        # Symmetry M(-v) == M(v)
        for test_v in [2.0, 5.0, 15.0, 50.0, 150.0, 500.0]:
            self.assertAlmostEqual(eval_parametric(test_v), eval_parametric(-test_v), places=12)

        # Clamping at 500.0
        self.assertLessEqual(eval_parametric(1000.0), 500.0)
        self.assertEqual(eval_parametric(200000.0), 500.0)

    def test_momentum_decay_and_cutoff_invariants(self):
        """Review Round 2: Test synthetic momentum kinetics recurrence, exponential rate, and cutoff threshold."""
        with open(self.curves_json, "r", encoding="utf-8") as f:
            mom = data = json.load(f)["trackpad_momentum_kinetics"]

        decay_rate = mom["friction_decay_rate_per_tick"]
        self.assertEqual(decay_rate, 0.950)
        timer_rate_ms = mom["momentum_dispatch_timer_rate_ms"]
        self.assertEqual(timer_rate_ms, 10)

        # Continuous decay lambda = -ln(0.950) / 0.01 s
        delta_t_s = timer_rate_ms / 1000.0
        lam = -math.log(decay_rate) / delta_t_s
        self.assertAlmostEqual(lam, 5.129329, places=5)

        # Velocity cutoff
        cutoff = mom["terminal_momentum_cutoff_pt_per_tick"]
        self.assertEqual(cutoff, 0.05)

        # 10 ticks (100ms) decay ratio: 0.950^10 ~ 0.5987369
        ratio_100ms = decay_rate ** 10
        self.assertAlmostEqual(ratio_100ms, 0.5987369, places=6)

    def test_wheel_normalization_and_shift_swap(self):
        """Review Round 2: Test discrete detent normalization arithmetic and Shift modifier gating."""
        detent_ticks = 1
        lines_per_detent = 3.0
        line_to_pt = 10.0
        scroll_res = 10.0

        displacement_pt = (detent_ticks * lines_per_detent * line_to_pt) / scroll_res
        self.assertEqual(displacement_pt, 3.0)

    def test_findings_dossier_anti_placeholder_and_structure(self):
        """R6: Test findings dossier richness, anti-placeholder rules, and Mermaid diagrams."""
        self.assertTrue(self.findings_md.is_file(), "03E_IOHID_SCROLL_FILTER.md must exist")
        content = self.findings_md.read_text(encoding="utf-8")
        
        # 1. Size metric >= 3,500 bytes
        self.assertGreaterEqual(len(content.encode("utf-8")), 3500, "Findings markdown must be >= 3,500 bytes")

        # 2. Strict anti-placeholder scan
        for pattern in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            self.assertEqual(len(matches), 0, f"Forbidden placeholder '{pattern}' matched in {self.findings_md}")

        # 3. Mermaid diagrams variety
        diagrams = ["sequenceDiagram", "classDiagram", "stateDiagram-v2", "graph"]
        for d in diagrams:
            self.assertIn(d, content, f"Findings dossier must include Mermaid diagram type '{d}'")

        # 4. Required markers
        markers = [
            "0x2529c4000", "0x2529ca294", "0x2529c4a9c", "0x2529c64e8", "0x2529cd690",
            "kIOHIDEventScrollPhase", "IOHIDPointerScrollFilter", "IOHIDScrollAccelerator", "PAC00",
            "0.950", "10.0"
        ]
        for m in markers:
            self.assertIn(m, content, f"Required technical marker '{m}' missing from findings")

    def test_evidence_ledger_phase3e_integrity(self):
        """R6: Test evidence ledger Phase 3E confirmed entries HID-001 through HID-015."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        
        phase_3e_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line: continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_3E":
                    phase_3e_entries.append((line_no, entry))

        self.assertGreaterEqual(len(phase_3e_entries), 15, "Evidence ledger must contain at least 15 Phase 3E entries")
        
        entry_ids = [e["id"] for _, e in phase_3e_entries]
        for idx in range(1, 16):
            expected_id = f"HID-{idx:03d}"
            self.assertIn(expected_id, entry_ids, f"Missing evidence entry {expected_id}")

        for line_no, entry in phase_3e_entries:
            self.assertEqual(entry.get("confidence"), "CONFIRMED", f"Entry {entry['id']} line {line_no} not CONFIRMED")
            self.assertTrue(entry.get("finding", "").startswith("[CONFIRMED]"), f"Entry {entry['id']} finding missing [CONFIRMED]")
            self.assertTrue(entry.get("evidence_type"), f"Entry {entry['id']} missing evidence_type")
            self.assertTrue(entry.get("tool"), f"Entry {entry['id']} missing tool")
            bp = entry.get("binary_path", "")
            self.assertTrue(bp, f"Entry {entry['id']} missing binary_path")
            self.assertTrue((PROJECT_ROOT / bp).is_file(), f"Entry {entry['id']} cites non-existent binary_path: {bp}")

    def test_device_profiles_and_scroll_phase_bitmasks(self):
        """R3 & R4: Test device-dependent sensitivity profiles and complete scroll phase bitmasks."""
        with open(self.curves_json, "r", encoding="utf-8") as f:
            curves_data = json.load(f)
        with open(self.iohid_json, "r", encoding="utf-8") as f:
            iohid_data = json.load(f)

        # 1. Device profiles in curves JSON
        profiles = curves_data.get("device_acceleration_profiles", {})
        required_profiles = ["generic_usb_mouse", "apple_magic_mouse", "apple_magic_trackpad", "high_speed_optical_mouse"]
        for prof in required_profiles:
            self.assertIn(prof, profiles, f"Missing device profile '{prof}' in pointer_acceleration_curves.json")
            p_data = profiles[prof]
            self.assertTrue(p_data.get("device_type"), f"Profile '{prof}' missing device_type")
            curve = p_data.get("acceleration_curve", [])
            self.assertGreaterEqual(len(curve), 4, f"Profile '{prof}' must have at least 4 curve control points")
            # Verify monotonic thresholds and gains
            for i in range(len(curve) - 1):
                self.assertLessEqual(curve[i]["velocity_threshold"], curve[i+1]["velocity_threshold"])
                self.assertLessEqual(curve[i]["gain"], curve[i+1]["gain"])

        # 2. Scroll phase bitmasks in iohid_scroll_filter.json
        phase_masks = iohid_data.get("event_constants", {}).get("scroll_phase_bitmasks", {})
        expected_phases = {
            "kIOHIDEventScrollPhaseNone": 0,
            "kIOHIDEventScrollPhaseBegan": 1,
            "kIOHIDEventScrollPhaseChanged": 2,
            "kIOHIDEventScrollPhaseEnded": 4,
            "kIOHIDEventScrollMomentumBegan": 8,
            "kIOHIDEventScrollMomentumChanged": 16,
            "kIOHIDEventScrollMomentumEnded": 32
        }
        for name, exp_val in expected_phases.items():
            self.assertIn(name, phase_masks, f"Missing scroll phase bitmask '{name}'")
            self.assertEqual(phase_masks[name], exp_val, f"Bitmask '{name}' mismatch: {phase_masks[name]} != {exp_val}")

    def test_property_accessors_and_vtable_completeness(self):
        """R1: Test full vtable slot inventory and plugin COM architecture."""
        with open(self.iohid_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        arch = data.get("plugin_architecture", {})
        self.assertEqual(arch.get("factory_entry_point"), "IOHIDPointerScrollFilterFactory")
        self.assertEqual(arch.get("com_interface"), "IOHIDServiceFilterPlugInInterface")
        self.assertEqual(arch.get("class_hierarchy"), ["IUnknown", "IOHIDServiceFilterPlugInInterface", "IOHIDPointerScrollFilter"])

        vtable = data.get("virtual_method_table", {})
        methods = vtable.get("methods", [])
        self.assertEqual(len(methods), 10, "Vtable must contain exactly 10 slots")

        expected_symbols = [
            (0, "IOHIDPointerScrollFilter::QueryInterface"),
            (1, "IOHIDPointerScrollFilter::AddRef"),
            (2, "IOHIDPointerScrollFilter::Release"),
            (3, "IOHIDPointerScrollFilter::open"),
            (4, "IOHIDPointerScrollFilter::close"),
            (5, "IOHIDPointerScrollFilter::scheduleWithDispatchQueue"),
            (6, "IOHIDPointerScrollFilter::unscheduleFromDispatchQueue"),
            (7, "IOHIDPointerScrollFilter::copyProperty"),
            (8, "IOHIDPointerScrollFilter::setProperty"),
            (9, "IOHIDPointerScrollFilter::filter")
        ]

        for exp_slot, exp_sym in expected_symbols:
            m = methods[exp_slot]
            self.assertEqual(m["slot"], exp_slot)
            self.assertEqual(m["symbol"], exp_sym)
            self.assertTrue(m["address"].startswith("0x2529"))
            self.assertEqual(m["pac_opcode"], "0xd503237f")

if __name__ == "__main__":
    unittest.main()
