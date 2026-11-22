#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 1A: Workspace Baseline & Framework Verification
Tests the 13 candidate scrolling frameworks, subcache cross-slice traversal,
pointer fixup alignment, tool non-clobber invariants, and baseline dossier completeness.
"""

import unittest
import json
import struct
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestScrollingPhase1AAdversarial(unittest.TestCase):

    def setUp(self):
        self.overview_file = PROJECT_ROOT / "artifacts/rootfs/shared_cache_overview.json"
        self.baseline_md = PROJECT_ROOT / "findings/scrolling/01A_WORKSPACE_BASELINE.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"
        self.uikitcore_res_file = PROJECT_ROOT / "artifacts/scrolling/uikitcore_offset_resolution.json"

        with open(self.overview_file, "r", encoding="utf-8") as f:
            self.overview = json.load(f)

    def test_system_baseline_metadata(self):
        """R1: Test that findings document and manifests establish exact platform baseline."""
        self.assertTrue(self.baseline_md.is_file(), "01A_WORKSPACE_BASELINE.md must exist")
        content = self.baseline_md.read_text(encoding="utf-8")
        
        required_tokens = [
            "iOS 27.2",
            "24B119",
            "RaveB",
            "Darwin 24.2.0",
            "iPhone18,3",
            "v57ap",
            "0x08",
            "t8150",
            "arm64e",
            "PAC00"
        ]
        for token in required_tokens:
            self.assertIn(token, content, f"Missing required platform baseline token: {token}")

    def test_13_candidate_frameworks_exact_resolution(self):
        """R2: Verify exact resolution of all 13 candidate scrolling frameworks."""
        from tools.analyze_dyld_cache import find_matching_image, resolve_framework_offsets

        expected_frameworks = {
            "UIKitCore.framework": ("/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore", ".01", 0x184752000, 0x04352000),
            "QuartzCore.framework": ("/System/Library/Frameworks/QuartzCore.framework/QuartzCore", ".01", 0x1842d4000, 0x03ed4000),
            "SwiftUI.framework": ("/System/Library/Frameworks/SwiftUI.framework/SwiftUI", ".03", 0x18a8a7000, 0x024a7000),
            "SwiftUICore.framework": ("/System/Library/Frameworks/SwiftUICore.framework/SwiftUICore", ".03", 0x188404000, 0x00004000),
            "WebKit.framework": ("/System/Library/Frameworks/WebKit.framework/WebKit", ".07", 0x19cbb9000, 0x047b9000),
            "WebKitLegacy.framework": ("/System/Library/PrivateFrameworks/WebKitLegacy.framework/WebKitLegacy", ".11", 0x1afb20000, 0x07720000),
            "UIKit.framework": ("/System/Library/Frameworks/UIKit.framework/UIKit", ".46", 0x24ff98000, 0x07b98000),
            "Gestures.framework": ("/System/Library/PrivateFrameworks/Gestures.framework/Gestures", ".03", 0x18a169000, 0x01d69000),
            "CoreText.framework": ("/System/Library/Frameworks/CoreText.framework/CoreText", ".07", 0x19a3d7000, 0x01fd7000),
            "IOHIDPointerScrollFilter.plugin": ("/System/Library/HIDPlugins/IOHIDPointerScrollFilter.plugin/IOHIDPointerScrollFilter", ".48", 0x2529c4000, 0x025c4000),
            "AnimationKit.framework": ("/System/Library/PrivateFrameworks/AnimationKit.framework/AnimationKit", ".07", 0x19f2b1000, 0x06eb1000),
            "SystemUIAnimationKit.framework": ("/System/Library/PrivateFrameworks/SystemUIAnimationKit.framework/SystemUIAnimationKit", ".69", 0x2b62f0000, 0x05ef0000),
            "UIKitServices.framework": ("/System/Library/PrivateFrameworks/UIKitServices.framework/UIKitServices", ".05", 0x197f2b000, 0x07b2b000)
        }

        cache_dir = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld"
        for fw_name, (exp_path, exp_slice, exp_vm, exp_off) in expected_frameworks.items():
            res = resolve_framework_offsets(self.overview, fw_name, cache_dir)
            self.assertEqual(res["matched_image_path"], exp_path, f"{fw_name} matched path mismatch")
            self.assertEqual(res["subcache_extension"], exp_slice, f"{fw_name} slice mismatch")
            self.assertEqual(res["vm_base_address_int"], exp_vm, f"{fw_name} VM address mismatch")
            self.assertEqual(res["subcache_file_offset_int"], exp_off, f"{fw_name} subcache file offset mismatch")
            self.assertEqual(res["segment_count"], 7, f"{fw_name} must adhere to 7-segment partition")

    def test_framework_short_name_matching_resilience(self):
        """Test that short framework queries do not accidentally match axbundles or prefix collisions."""
        from tools.analyze_dyld_cache import find_matching_image
        images = self.overview["all_images"]

        # 'UIKit' must match UIKit.framework, NOT UIKitCore
        uikit_match = find_matching_image(images, "UIKit")
        self.assertIsNotNone(uikit_match)
        self.assertEqual(uikit_match["path"], "/System/Library/Frameworks/UIKit.framework/UIKit")

        # 'SwiftUI' must match SwiftUI.framework, NOT SwiftUI.axbundle
        swiftui_match = find_matching_image(images, "SwiftUI")
        self.assertIsNotNone(swiftui_match)
        self.assertEqual(swiftui_match["path"], "/System/Library/Frameworks/SwiftUI.framework/SwiftUI")

        # 'SpringBoard' must match SpringBoard.framework, NOT SpringBoardHome.axbundle
        sb_match = find_matching_image(images, "SpringBoard")
        self.assertIsNotNone(sb_match)
        self.assertEqual(sb_match["path"], "/System/Library/PrivateFrameworks/SpringBoard.framework/SpringBoard")

    def test_case_insensitive_extension_matching(self):
        """Test case-insensitive extension stripping and path resilience."""
        from tools.analyze_dyld_cache import find_matching_image
        images = self.overview["all_images"]

        # 'UIKit.FRAMEWORK' must match UIKit.framework, NOT _AppIntents_UIKit
        uikit_match = find_matching_image(images, "UIKit.FRAMEWORK")
        self.assertIsNotNone(uikit_match)
        self.assertEqual(uikit_match["path"], "/System/Library/Frameworks/UIKit.framework/UIKit")

        # 'IOHIDPointerScrollFilter.PLUGIN' and 'iohidpointerscrollfilter.plugin'
        plugin_match = find_matching_image(images, "IOHIDPointerScrollFilter.PLUGIN")
        self.assertIsNotNone(plugin_match)
        self.assertEqual(plugin_match["path"], "/System/Library/HIDPlugins/IOHIDPointerScrollFilter.plugin/IOHIDPointerScrollFilter")

        plugin_lower = find_matching_image(images, "iohidpointerscrollfilter.plugin")
        self.assertIsNotNone(plugin_lower)
        self.assertEqual(plugin_lower["path"], "/System/Library/HIDPlugins/IOHIDPointerScrollFilter.plugin/IOHIDPointerScrollFilter")

        # Edge cases: None or empty query
        self.assertIsNone(find_matching_image(images, None))
        self.assertIsNone(find_matching_image(images, ""))
        self.assertIsNone(find_matching_image(images, "   "))

        # Full path query
        full_path_match = find_matching_image(images, "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore")
        self.assertIsNotNone(full_path_match)
        self.assertEqual(full_path_match["path"], "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore")

    def test_uikitcore_resolution_not_clobbered(self):
        """Test that resolving a non-UIKitCore framework does not clobber uikitcore_offset_resolution.json."""
        with open(self.uikitcore_res_file, "r", encoding="utf-8") as f:
            orig_data = json.load(f)

        # Run analyze_dyld_cache.py resolving QuartzCore
        cmd = [
            "python3", "tools/analyze_dyld_cache.py",
            "--framework", "QuartzCore"
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"analyze_dyld_cache.py failed: {res.stderr}")

        # Ensure uikitcore_offset_resolution.json was NOT modified
        with open(self.uikitcore_res_file, "r", encoding="utf-8") as f:
            curr_data = json.load(f)

        self.assertEqual(curr_data["vm_base_address"], "0x184752000")
        self.assertEqual(curr_data["matched_image_path"], "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore")
        self.assertEqual(curr_data, orig_data)

    def test_subcache_traversal_resident_slices(self):
        """R3: Test boundary traversal and Mach-O header integrity across subcaches .01 and .36."""
        cache_dir = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld"
        sc_01 = cache_dir / "dyld_shared_cache_arm64e.01"
        sc_36 = cache_dir / "dyld_shared_cache_arm64e.36"

        self.assertTrue(sc_01.is_file(), "Subcache .01 must be resident on disk")
        self.assertTrue(sc_36.is_file(), "Subcache .36 must be resident on disk")

        # Test subcache .01 targets
        with open(sc_01, "rb") as f:
            # UIKitCore at 0x4352000
            f.seek(0x04352000)
            magic, cputype, cpusubtype = struct.unpack("<III", f.read(12))
            self.assertEqual(magic, 0xfeedfacf, "UIKitCore Mach-O magic mismatch")
            self.assertEqual(cputype, 0x0100000c, "UIKitCore CPU type must be ARM64")
            self.assertEqual(cpusubtype, 0x80000002, "UIKitCore CPU subtype must be ARM64E")

            # QuartzCore at 0x3ed4000
            f.seek(0x03ed4000)
            magic, cputype, cpusubtype = struct.unpack("<III", f.read(12))
            self.assertEqual(magic, 0xfeedfacf, "QuartzCore Mach-O magic mismatch")

        # Test subcache .36 targets
        with open(sc_36, "rb") as f:
            # SpringBoard at 0x06611000
            f.seek(0x06611000)
            magic, cputype, cpusubtype = struct.unpack("<III", f.read(12))
            self.assertEqual(magic, 0xfeedfacf, "SpringBoard Mach-O magic mismatch")
            self.assertEqual(cputype, 0x0100000c, "SpringBoard CPU type must be ARM64")
            self.assertEqual(cpusubtype, 0x80000002, "SpringBoard CPU subtype must be ARM64E")

            # UserNotificationsUIKit at 0x05d24000
            f.seek(0x05d24000)
            magic, _, _ = struct.unpack("<III", f.read(12))
            self.assertEqual(magic, 0xfeedfacf, "UserNotificationsUIKit Mach-O magic mismatch")

            # ControlCenterUIKit at 0x0751d000
            f.seek(0x0751d000)
            magic, _, _ = struct.unpack("<III", f.read(12))
            self.assertEqual(magic, 0xfeedfacf, "ControlCenterUIKit Mach-O magic mismatch")

    def test_subcache_25_dylddata_coordinate_alignment(self):
        """R3: Verify mathematical coordinate alignment of Subcache .25.dylddata at 0x1e00f4000."""
        subcaches = self.overview["subcaches_summary"]["entries"]
        sc_25 = next((sc for sc in subcaches if sc["extension"] == ".25.dylddata"), None)
        self.assertIsNotNone(sc_25, "Subcache .25.dylddata must exist in subcaches table")
        
        vm_base_25 = 0x180000000 + sc_25["vm_offset_int"]
        self.assertEqual(vm_base_25, 0x1e00f4000, "Subcache .25.dylddata VM base must be 0x1e00f4000")

        # UIKitCore segments in Subcache .25
        uikitcore_data_const_vm = 0x1e05fafd0
        uikitcore_auth_const_vm = 0x1e229cef0

        self.assertEqual(uikitcore_data_const_vm - vm_base_25, 0x506fd0, "__DATA_CONST fileoff mismatch")
        self.assertEqual(uikitcore_auth_const_vm - vm_base_25, 0x21a8ef0, "__AUTH_CONST fileoff mismatch")

    def test_evidence_ledger_phase1a(self):
        """R5: Test that evidence_ledger.jsonl contains valid Phase 1A confirmed entries."""
        self.assertTrue(self.ledger_file.is_file(), "evidence_ledger.jsonl must exist")
        phase1a_entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_1A":
                    phase1a_entries.append(entry)

        self.assertGreaterEqual(len(phase1a_entries), 4, "Must have at least 4 Phase 1A evidence entries")
        for entry in phase1a_entries:
            self.assertEqual(entry["confidence"], "CONFIRMED")
            self.assertTrue(entry.get("finding", "").startswith("[CONFIRMED]"))

    def test_springboard_prior_findings_coverage(self):
        """R4: Test that SpringBoard prior findings are documented in 01A_WORKSPACE_BASELINE.md."""
        content = self.baseline_md.read_text(encoding="utf-8")
        sb_elements = [
            "BKSTouchStream",
            "SBSystemGestureManager",
            "SBHomeGesturePanGestureRecognizer",
            "SBDeckSwitcherPanGestureWorkspace",
            "SBFloatingDockView",
            "SBCoverSheet"
        ]
        for elem in sb_elements:
            self.assertIn(elem, content, f"Missing prior SpringBoard finding element: {elem}")

    def test_scroll_progress_phase1a_completed(self):
        """R5: Test that scroll_progress.json reflects phase_1a_workspace completion."""
        with open(self.progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)

        phase_1a = progress["phases"]["phase_1a_workspace"]
        self.assertEqual(phase_1a["status"], "completed")
        self.assertIn(progress["active_phase_id"], list(progress["phases"].keys()))

    def test_verify_phase_cli(self):
        """R5: Test that verify_phase.py passes for both phase_0_tooling and phase_1a_workspace."""
        for phase in ["phase_0_tooling", "phase_1a_workspace"]:
            cmd = ["python3", "tools/verify_phase.py", phase]
            res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"verify_phase.py {phase} failed: {res.stdout}\n{res.stderr}")

    def test_full_path_framework_resolution_routing(self):
        """Test that passing full framework path routes to uikitcore_offset_resolution.json without creating nested folders."""
        cmd = [
            "python3", "tools/analyze_dyld_cache.py",
            "--framework", "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore"
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"analyze_dyld_cache.py failed on full path: {res.stderr}")

        # Ensure no nested directory was created
        nested_dir = PROJECT_ROOT / "artifacts/scrolling/system"
        self.assertFalse(nested_dir.exists(), f"Unsanitized nested directory should not exist: {nested_dir}")

        with open(self.uikitcore_res_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["vm_base_address"], "0x184752000")
        self.assertEqual(data["matched_image_path"], "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore")

    def test_framework_inventory_structure_and_coverage(self):
        """R2: Test artifacts/scrolling/framework_inventory.json schema depth and coverage."""
        inv_file = PROJECT_ROOT / "artifacts/scrolling/framework_inventory.json"
        self.assertTrue(inv_file.is_file(), "framework_inventory.json must exist")
        with open(inv_file, "r", encoding="utf-8") as f:
            inv = json.load(f)

        self.assertIsInstance(inv, list)
        self.assertEqual(len(inv), 13, "Must have exactly 13 candidate framework entries")
        
        expected_slices = {
            "UIKitCore.framework": ".01",
            "QuartzCore.framework": ".01",
            "SwiftUI.framework": ".03",
            "SwiftUICore.framework": ".03",
            "WebKit.framework": ".07",
            "WebKitLegacy.framework": ".11",
            "UIKit.framework": ".46",
            "Gestures.framework": ".03",
            "CoreText.framework": ".07",
            "IOHIDPointerScrollFilter.plugin": ".48",
            "AnimationKit.framework": ".07",
            "SystemUIAnimationKit.framework": ".69",
            "UIKitServices.framework": ".05"
        }
        for entry in inv:
            query = entry["framework_query"]
            self.assertIn(query, expected_slices)
            self.assertEqual(entry["subcache_extension"], expected_slices[query])
            self.assertEqual(entry["segment_count"], 7)
            self.assertTrue(entry["vm_base_address"].startswith("0x"))
            self.assertTrue(entry["subcache_file_offset"].startswith("0x"))

    def test_rea_cross_slice_macho_slices(self):
        """R3: Test Mach-O header integrity and load command fileoff bounds of REA slices."""
        slice_01 = PROJECT_ROOT / "artifacts/scrolling/UIKitCore_UIScrollView_slice"
        slice_36 = PROJECT_ROOT / "artifacts/scrolling/SpringBoard_slice"

        self.assertTrue(slice_01.is_file(), "UIKitCore_UIScrollView_slice must exist")
        self.assertTrue(slice_36.is_file(), "SpringBoard_slice must exist")

        for s_file, exp_subtype in [(slice_01, 0x0), (slice_36, 0x80000002)]:
            file_len = s_file.stat().st_size
            with open(s_file, "rb") as f:
                data = f.read()
                magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", data[:32])
                self.assertEqual(magic, 0xfeedfacf, f"{s_file.name} must have 64-bit Mach-O magic")
                self.assertEqual(cputype, 0x0100000c, f"{s_file.name} CPU type must be ARM64")

                # Verify all segment load commands have fileoff + filesize <= file_len
                # This guarantees Ghidra MachoLoader will not throw IndexOutOfBoundsException
                off = 32
                for _ in range(ncmds):
                    cmd, cmdsize = struct.unpack("<II", data[off:off+8])
                    if cmd == 0x19: # LC_SEGMENT_64
                        seg_vmaddr, seg_vmsize, seg_fileoff, seg_filesize = struct.unpack("<QQQQ", data[off+24:off+56])
                        self.assertLessEqual(seg_fileoff + seg_filesize, file_len,
                                             f"{s_file.name} segment exceeds file boundary: {seg_fileoff} + {seg_filesize} > {file_len}")
                    off += cmdsize

    def test_subcache_36_scrollview_classes(self):
        """R4: Verify empirical presence of ScrollView classes inside dyld_shared_cache_arm64e.36."""
        cache_36 = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.36"
        self.assertTrue(cache_36.is_file())
        with open(cache_36, "rb") as f:
            data = f.read()

        required_symbols = [
            b"SBIconScrollView",
            b"SBAppSwitcherScrollView",
            b"SBFPagedScrollView",
            b"BSUIScrollView",
            b"CCUIIconScrollView"
        ]
        for sym in required_symbols:
            self.assertIn(sym, data, f"Subcache .36 missing empirical symbol: {sym.decode('ascii')}")

    def test_verify_phase_rejects_missing_phase1a_evidence(self):
        """Adversarial: Ensure verify_phase.py catches absence of confirmed Phase 1A evidence."""
        from tools.verify_phase import verify_artifact_content
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tf:
            # Ledger containing ONLY Phase 0 entry
            tf.write('{"id":"TOOL-001","phase":"PHASE_0","framework":"UIKitCore","binary_path":"artifacts/...","address":"0x1848b4c00","opcode_instructions":["0x1: pacibsp"],"finding":"[CONFIRMED]","confidence":"CONFIRMED"}\n')
            tf_path = Path(tf.name)

        try:
            errors = verify_artifact_content("evidence_ledger.jsonl", tf_path)
            self.assertTrue(any("Phase 1A entries" in err for err in errors),
                            f"verify_phase should fail when Phase 1A entries are missing, got: {errors}")
        finally:
            tf_path.unlink()

    def test_verify_phase_rejects_missing_subcache_file_offset(self):
        """Adversarial: Ensure verify_phase.py catches missing subcache_file_offset in framework inventory."""
        from tools.verify_phase import verify_artifact_content
        import tempfile

        with open(PROJECT_ROOT / "artifacts/scrolling/framework_inventory.json", "r") as f:
            inv_data = json.load(f)

        # Corrupt first entry: remove subcache_file_offset
        inv_data[0]["subcache_file_offset"] = ""

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(inv_data, tf)
            tf_path = Path(tf.name)

        try:
            errors = verify_artifact_content("framework_inventory.json", tf_path)
            self.assertTrue(any("subcache_file_offset" in err for err in errors),
                            f"verify_phase should fail when subcache_file_offset is missing, got: {errors}")
        finally:
            tf_path.unlink()

if __name__ == "__main__":
    unittest.main()

