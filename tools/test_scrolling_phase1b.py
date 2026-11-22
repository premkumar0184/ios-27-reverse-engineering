#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 1B: Scrolling Symbol Discovery & Inventory
Tests quantitative discovery thresholds, complete metadata schemas, CSV alignment,
string table offsets, anti-placeholder compliance, and Phase 2 entry gate readiness.
"""

import unittest
import json
import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestScrollingPhase1BAdversarial(unittest.TestCase):

    def setUp(self):
        self.class_json = PROJECT_ROOT / "artifacts/scrolling/scroll_class_inventory.json"
        self.class_csv = PROJECT_ROOT / "artifacts/scrolling/scroll_class_inventory.csv"
        self.method_json = PROJECT_ROOT / "artifacts/scrolling/scroll_method_inventory.json"
        self.string_json = PROJECT_ROOT / "artifacts/scrolling/scroll_string_inventory.json"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/01B_SYMBOL_DISCOVERY.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"

    def test_class_inventory_quantitative_threshold(self):
        """R1 & Acceptance Criteria: At least 50 scrolling classes cataloged."""
        self.assertTrue(self.class_json.is_file(), "scroll_class_inventory.json must exist")
        with open(self.class_json, "r", encoding="utf-8") as f:
            classes = json.load(f)
        
        self.assertIsInstance(classes, list)
        self.assertGreaterEqual(len(classes), 50, f"Expected >= 50 classes, found {len(classes)}")

        # Validate required metadata schema on every single class
        required_keys = [
            "class_name", "framework", "subcache_slice", "vm_base_address",
            "superclass", "inheritance_chain", "category", "role",
            "protocols", "ivars", "methods"
        ]
        valid_categories = {
            "Core Kinematics", "Gesture Infrastructure",
            "Positioning/Paging", "Rendering/Display"
        }

        class_names = set()
        for idx, c in enumerate(classes):
            for k in required_keys:
                self.assertIn(k, c, f"Class {c.get('class_name', idx)} missing key '{k}'")
            self.assertIn(c["category"], valid_categories, f"Invalid category in {c['class_name']}: {c['category']}")
            self.assertTrue(c["vm_base_address"].startswith("0x"), f"Invalid vm_base_address: {c['vm_base_address']}")
            self.assertTrue(c["subcache_slice"].startswith("."), f"Invalid subcache_slice: {c['subcache_slice']}")
            self.assertIsInstance(c["inheritance_chain"], list)
            self.assertGreaterEqual(len(c["inheritance_chain"]), 1)
            class_names.add(c["class_name"])

        # Core anchor classes must exist
        expected_anchors = [
            "UIScrollView",
            "UIScrollViewPanGestureRecognizer",
            "UIScrollViewPagingController",
            "UIScrollViewScrollAnimation",
            "CADisplayLink",
            "CASpringAnimation",
            "SwiftUI.ScrollView",
            "IOHIDPointerScrollFilter",
            "WKScrollView",
            "AKSpring",
            "SBIconScrollView"
        ]
        for anchor in expected_anchors:
            self.assertIn(anchor, class_names, f"Expected anchor class '{anchor}' missing from class inventory")

        required_13 = [
            "UIKitCore.framework", "QuartzCore.framework", "SwiftUI.framework", "SwiftUICore.framework",
            "WebKit.framework", "WebKitLegacy.framework", "UIKit.framework", "Gestures.framework",
            "CoreText.framework", "IOHIDPointerScrollFilter.plugin", "AnimationKit.framework",
            "SystemUIAnimationKit.framework", "UIKitServices.framework"
        ]
        class_fws = set(c["framework"] for c in classes)
        for fw in required_13:
            self.assertIn(fw, class_fws, f"Candidate framework '{fw}' missing from class inventory")

        # Validate non-empty methods, ivars, and correct inheritance chains on every single class
        for c in classes:
            self.assertGreater(len(c["methods"]), 0, f"Class {c['class_name']} has empty methods list")
            self.assertGreater(len(c["ivars"]), 0, f"Class {c['class_name']} has empty ivars list")
            self.assertEqual(c["inheritance_chain"][0], c["class_name"], f"Class {c['class_name']} inheritance chain does not start with class name")
            if c.get("superclass") and len(c["inheritance_chain"]) > 1:
                self.assertEqual(c["inheritance_chain"][1], c["superclass"], f"Class {c['class_name']} inheritance chain second element != superclass")

    def test_class_csv_alignment(self):
        """R3: Tabular CSV inventory generated and perfectly aligned with JSON."""
        self.assertTrue(self.class_csv.is_file(), "scroll_class_inventory.csv must exist")
        with open(self.class_json, "r", encoding="utf-8") as f:
            classes_json = json.load(f)

        rows = []
        with open(self.class_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        self.assertEqual(len(rows), len(classes_json), f"CSV row count ({len(rows)}) must match JSON ({len(classes_json)})")
        
        # Verify columns and data integrity
        total_csv_methods = 0
        for i, row in enumerate(rows):
            c_json = classes_json[i]
            self.assertEqual(row["Class"], c_json["class_name"])
            self.assertEqual(row["Framework"], c_json["framework"])
            self.assertEqual(row["Subcache Slice"], c_json["subcache_slice"])
            self.assertEqual(int(row["Method Count"]), len(c_json["methods"]))
            self.assertEqual(int(row["Ivar Count"]), len(c_json["ivars"]))
            self.assertEqual(row["Superclass"], c_json["superclass"])
            self.assertEqual(row["Category"], c_json["category"])
            total_csv_methods += int(row["Method Count"])

        with open(self.method_json, "r", encoding="utf-8") as mf:
            methods_json = json.load(mf)
        self.assertEqual(total_csv_methods, len(methods_json), f"CSV total method count ({total_csv_methods}) must match method inventory ({len(methods_json)})")

    def test_method_inventory_quantitative_threshold(self):
        """R1 & Acceptance Criteria: At least 200 scrolling methods cataloged."""
        self.assertTrue(self.method_json.is_file(), "scroll_method_inventory.json must exist")
        with open(self.method_json, "r", encoding="utf-8") as f:
            methods = json.load(f)

        self.assertIsInstance(methods, list)
        self.assertGreaterEqual(len(methods), 200, f"Expected >= 200 methods, found {len(methods)}")

        # Verify all 13 candidate frameworks are represented in method inventory
        required_13 = [
            "UIKitCore.framework", "QuartzCore.framework", "SwiftUI.framework", "SwiftUICore.framework",
            "WebKit.framework", "WebKitLegacy.framework", "UIKit.framework", "Gestures.framework",
            "CoreText.framework", "IOHIDPointerScrollFilter.plugin", "AnimationKit.framework",
            "SystemUIAnimationKit.framework", "UIKitServices.framework"
        ]
        method_fws = set(m["framework"] for m in methods)
        for fw in required_13:
            self.assertIn(fw, method_fws, f"Candidate framework '{fw}' missing from method inventory")

        # Verify method schema on every single method
        required_keys = [
            "method_name", "class_name", "framework", "subcache_slice",
            "virtual_address", "signature", "category", "role", "is_kinematics_critical"
        ]
        method_names = set()
        for idx, m in enumerate(methods):
            for k in required_keys:
                self.assertIn(k, m, f"Method {m.get('method_name', idx)} missing key '{k}'")
            self.assertTrue(m["virtual_address"].startswith("0x"), f"Invalid virtual address: {m['virtual_address']}")
            self.assertIsInstance(m["is_kinematics_critical"], bool)
            method_names.add(m["method_name"])

        # Check critical kinematics methods
        critical_methods = [
            "-[UIScrollView setContentOffset:animated:]",
            "-[UIScrollView _rubberBandOffsetForOffset:maxOffset:minOffset:range:outside:legitimateOffset:]",
            "-[UIScrollView _scrollViewWillBeginDragging]",
            "-[UIScrollView decelerationRate]",
            "-[CADisplayLink setPreferredFrameRateRange:]",
            "-[CASpringAnimation setDamping:]",
            "-[UIScrollViewPanGestureRecognizer velocityInView:]"
        ]
        for cm in critical_methods:
            self.assertIn(cm, method_names, f"Expected critical method '{cm}' missing from method inventory")

        # Bidirectional 1:1 check with scroll_class_inventory.json
        with open(self.class_json, "r", encoding="utf-8") as cf:
            classes = json.load(cf)
        c_map = {c["class_name"]: set(m["name"] for m in c["methods"]) for c in classes}
        for m in methods:
            cn = m["class_name"]
            mn = m["method_name"]
            self.assertIn(cn, c_map, f"Class '{cn}' from method inventory missing from class inventory")
            self.assertIn(mn, c_map[cn], f"Method '{mn}' from method inventory missing from class '{cn}' methods array")

        total_class_methods = sum(len(c["methods"]) for c in classes)
        self.assertEqual(len(methods), total_class_methods, f"Total methods ({len(methods)}) must equal sum of class methods ({total_class_methods})")

    def test_string_inventory_kinematics_coverage(self):
        """R2: Comprehensive string extraction for physical tuning keywords with byte-level verification."""
        self.assertTrue(self.string_json.is_file(), "scroll_string_inventory.json must exist")
        with open(self.string_json, "r", encoding="utf-8") as f:
            strings = json.load(f)

        self.assertIsInstance(strings, list)
        self.assertGreaterEqual(len(strings), 50, f"Expected rich string inventory, found {len(strings)}")

        # Verify all 13 candidate frameworks are represented
        required_13 = [
            "UIKitCore.framework", "QuartzCore.framework", "SwiftUI.framework", "SwiftUICore.framework",
            "WebKit.framework", "WebKitLegacy.framework", "UIKit.framework", "Gestures.framework",
            "CoreText.framework", "IOHIDPointerScrollFilter.plugin", "AnimationKit.framework",
            "SystemUIAnimationKit.framework", "UIKitServices.framework"
        ]
        string_fws = set(s.get("framework") for s in strings)
        for fw in required_13:
            self.assertIn(fw, string_fws, f"Candidate framework '{fw}' missing from string inventory")

        required_keywords = [
            "deceleration", "rubber", "bounce", "friction",
            "damping", "spring", "velocityThreshold", "touchSlop"
        ]
        found_keywords = set(s.get("keyword") for s in strings)
        for kw in required_keywords:
            self.assertIn(kw, found_keywords, f"Required kinematics keyword '{kw}' missing from string inventory")

        # Deep verification: verify byte-accurate offsets for resident binaries
        uikit_text_file = PROJECT_ROOT / "artifacts/scrolling/UIKitCore_TEXT"
        uikit_data = uikit_text_file.read_bytes() if uikit_text_file.is_file() else None

        sc_01_file = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.01"
        sc_01_data = sc_01_file.read_bytes() if sc_01_file.is_file() else None

        sc_36_file = PROJECT_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.36"
        sc_36_data = sc_36_file.read_bytes() if sc_36_file.is_file() else None

        # Framework subcache VM bases for mathematical verification
        fw_inv_file = PROJECT_ROOT / "artifacts/scrolling/framework_inventory.json"
        fw_inv = {}
        if fw_inv_file.is_file():
            with open(fw_inv_file, "r", encoding="utf-8") as ff:
                fw_inv = {e["framework_query"]: e for e in json.load(ff)}

        for s in strings:
            self.assertIn("file_offset", s)
            self.assertIn("vm_address", s)
            self.assertTrue(s["file_offset"].startswith("0x"))
            self.assertTrue(s["vm_address"].startswith("0x"))

            # Byte-accuracy check on UIKitCore
            if uikit_data and s.get("framework") == "UIKitCore.framework":
                fo = int(s["file_offset"], 16) - 0x04352000
                target_bytes = s["string"].encode("utf-8")
                self.assertEqual(uikit_data[fo:fo+len(target_bytes)], target_bytes, f"Offset mismatch in UIKitCore string '{s['string']}'")

            # Byte-accuracy check on QuartzCore
            if sc_01_data and s.get("framework") == "QuartzCore.framework":
                fo = int(s["file_offset"], 16)
                target_bytes = s["string"].encode("utf-8")
                self.assertEqual(sc_01_data[fo:fo+len(target_bytes)], target_bytes, f"Offset mismatch in QuartzCore string '{s['string']}'")

            # Byte-accuracy check on SpringBoard
            if sc_36_data and s.get("framework") == "SpringBoard.framework":
                fo = int(s["file_offset"], 16)
                target_bytes = s["string"].encode("utf-8")
                self.assertEqual(sc_36_data[fo:fo+len(target_bytes)], target_bytes, f"Offset mismatch in SpringBoard string '{s['string']}'")

            # Mathematical exactness of VM address
            fw_name = s.get("framework")
            if fw_name in fw_inv:
                sub_vm = int(fw_inv[fw_name]["subcache_vm_base"], 16)
                fo = int(s["file_offset"], 16)
                vm = int(s["vm_address"], 16)
                self.assertEqual(vm, sub_vm + fo, f"VM address mismatch for {s['string']} in {fw_name}: {hex(vm)} != {hex(sub_vm + fo)}")

    def test_cryptex_cross_framework_strings_byte_accuracy(self):
        """Deep verification: verify non-resident candidate framework strings directly against cryptex shared cache slices."""
        cryptex_dmg = PROJECT_ROOT / "artifacts/crypto/141-09724-226_cryptex_systemos.dmg"
        if not cryptex_dmg.is_file():
            self.skipTest("Cryptex DMG not present")

        import subprocess
        # Sample test non-resident strings across slices .03, .07, .11, .46, .48, .69
        probe_strings = [
            (".48", 0x25cdabe, b"IOHIDScrollAccelerator", "IOHIDPointerScrollFilter.plugin"),
            (".48", 0x25cdce3, b"HIDScrollAcceleration", "IOHIDPointerScrollFilter.plugin"),
            (".03", 0x2359a97, b"friction", "Gestures.framework"),
            (".03", 0x236479b, b"deceleration", "Gestures.framework"),
            (".03", 0x1035d86, b"decelerating", "SwiftUICore.framework"),
            (".03", 0x3533d70, b"ScrollDecelerationRate", "SwiftUI.framework"),
            (".07", 0x5eec143, b"RubberBandingForSubScrollableRegionsEnabled", "WebKit.framework"),
            (".07", 0x6f671a0, b"SpringAnimationParameters", "AnimationKit.framework"),
            (".07", 0x21d458b, b"CTFontLineSpacingOverrideAttribute", "CoreText.framework"),
            (".11", 0x78ba000, b"WebKitMomentumScrollingAnimatorEnabled", "WebKitLegacy.framework"),
            (".46", 0x7ba6834, b"UNNotificationExtensionScrollsOwnContent", "UIKit.framework"),
            (".69", 0x5f4f980, b"Interactive Spring", "SystemUIAnimationKit.framework"),
        ]

        # Group by slice to minimize 7z invocations
        slices = set(p[0] for p in probe_strings)
        for sl in sorted(slices):
            slice_path = f"System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e{sl}"
            cmd = ["7z", "e", "-so", str(cryptex_dmg), slice_path]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            sl_probes = [p for p in probe_strings if p[0] == sl]
            max_off = max(p[1] + len(p[2]) for p in sl_probes)

            pos = 0
            data = b""
            while pos < max_off + 1024:
                chunk = proc.stdout.read(min(1024*1024, max_off + 1024 - pos))
                if not chunk:
                    break
                data += chunk
            if proc.stdout:
                proc.stdout.close()
            proc.terminate()
            proc.wait()

            for _, off, expected, fw in sl_probes:
                actual = data[off:off+len(expected)]
                self.assertEqual(actual, expected, f"Byte mismatch in slice {sl} offset {hex(off)} for {fw}")

    def test_anti_placeholder_across_all_artifacts(self):
        """Acceptance Criteria: Zero placeholder patterns in any artifact."""
        banned_patterns = [
            r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bLOREM IPSUM\b",
            r"\bINSERT HERE\b", r"\bCOMING SOON\b", r"\bOMITTED FOR BREVITY\b",
            r"\bNOT YET IMPLEMENTED\b", r"\[TBD\]", r"\[TODO\]"
        ]

        artifacts = [
            self.class_json,
            self.class_csv,
            self.method_json,
            self.string_json,
            self.findings_md
        ]
        for art in artifacts:
            content = art.read_text(encoding="utf-8")
            for pattern in banned_patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                self.assertEqual(len(matches), 0, f"Found banned pattern '{pattern}' in {art.name}")

    def test_findings_document_structure(self):
        """R4: Findings dossier size >= 2500 bytes with tables and code blocks."""
        self.assertTrue(self.findings_md.is_file())
        size = self.findings_md.stat().st_size
        self.assertGreaterEqual(size, 2500, f"Findings doc too small ({size} < 2500)")

        content = self.findings_md.read_text(encoding="utf-8")
        h2_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
        self.assertGreaterEqual(h2_count, 4, "Expected >= 4 '##' sections in findings")
        self.assertIn("|", content, "Markdown tables required in findings")
        self.assertIn("```", content, "Code evidence blocks required in findings")

        # Category tokens
        categories = ["Core Kinematics", "Gesture Infrastructure", "Positioning", "Rendering"]
        for cat in categories:
            self.assertIn(cat, content, f"Missing category '{cat}' in findings doc")

        # Table 2.1 sum check against method inventory
        table_rows = re.findall(r"\|\s*[*]+`?([A-Za-z0-9_.\s()]+?)`?[*]+\s*\|[^|]+\|[^|]+\|[^|]+\|\s*(\d+)\s*\|\s*(\d+)\s*\|", content)
        if table_rows:
            table_method_sum = sum(int(r[2]) for r in table_rows)
            with open(self.method_json, "r", encoding="utf-8") as mf:
                methods_count = len(json.load(mf))
            self.assertEqual(table_method_sum, methods_count, f"Table 2.1 method sum ({table_method_sum}) must equal method inventory ({methods_count})")

    def test_progress_gate_state(self):
        """Acceptance Criteria: scroll_progress.json updated for Phase 1B complete & Phase 2 entry."""
        self.assertTrue(self.progress_file.is_file())
        with open(self.progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)

        phases = progress.get("phases", {})
        p1b = phases.get("phase_1b_discovery", {})
        self.assertEqual(p1b.get("status"), "completed", "phase_1b_discovery.status must be 'completed'")

        p2 = phases.get("phase_2_architecture", {})
        self.assertTrue(p2.get("entry_criteria_met"), "phase_2_architecture.entry_criteria_met must be True")

        self.assertIn(progress.get("active_phase_id"), list(phases.keys()))
        v_log = progress.get("verification_log", [])
        p1b_entries = [e for e in v_log if e.get("phase_id") == "phase_1b_discovery"]
        self.assertEqual(len(p1b_entries), 1, "phase_1b_discovery must be logged in verification_log exactly once")
        self.assertEqual(p1b_entries[0].get("status"), "PASSED")

if __name__ == "__main__":
    unittest.main()
