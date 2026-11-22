#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 2: Architecture Mapping & Execution Flow
Tests class hierarchy trees, Mach-O load command dependencies, 4-phase execution flow,
UIScrollView ivar offsets, SwiftUI bridge mechanics, anti-placeholder compliance, and gate state.
"""

import unittest
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestScrollingPhase2Adversarial(unittest.TestCase):

    def setUp(self):
        self.class_hierarchy_json = PROJECT_ROOT / "artifacts/scrolling/class_hierarchy.json"
        self.dependencies_json = PROJECT_ROOT / "artifacts/scrolling/framework_dependencies.json"
        self.execution_flow_json = PROJECT_ROOT / "artifacts/scrolling/execution_flow_preliminary.json"
        self.class_inventory_json = PROJECT_ROOT / "artifacts/scrolling/scroll_class_inventory.json"
        self.findings_md = PROJECT_ROOT / "findings/scrolling/02_ARCHITECTURE_MAP.md"
        self.progress_file = PROJECT_ROOT / "artifacts/scrolling/scroll_progress.json"
        self.ledger_file = PROJECT_ROOT / "artifacts/scrolling/evidence_ledger.jsonl"

    def test_class_hierarchy_reconstruction(self):
        """R1: Verify full class hierarchy reconstruction and concordance with 86 cataloged classes."""
        self.assertTrue(self.class_hierarchy_json.is_file(), "class_hierarchy.json must exist")
        with open(self.class_hierarchy_json, "r", encoding="utf-8") as f:
            hierarchy = json.load(f)

        self.assertIn("target_metadata", hierarchy)
        self.assertIn("uiscrollview_subsystem", hierarchy)
        self.assertIn("gesture_subsystem", hierarchy)
        self.assertIn("animation_subsystem", hierarchy)
        self.assertIn("class_index", hierarchy)

        class_index = hierarchy["class_index"]
        # Verify all 86 classes from Phase 1B exist in class_index
        with open(self.class_inventory_json, "r", encoding="utf-8") as f:
            inv_classes = json.load(f)
        self.assertEqual(len(inv_classes), 86)
        for c in inv_classes:
            cn = c["class_name"]
            self.assertIn(cn, class_index, f"Class '{cn}' from inventory missing from class_hierarchy.json")
            # Verify superclass chain consistency
            self.assertEqual(class_index[cn]["inheritance_chain"], c["inheritance_chain"])

        # Verify UIScrollView specific chain
        uisk_info = hierarchy["uiscrollview_subsystem"]
        self.assertEqual(uisk_info["root_class"], "UIScrollView")
        self.assertEqual(uisk_info["full_inheritance_chain"], ["UIScrollView", "UIView", "UIResponder", "NSObject"])

        # Verify specialized subclasses
        direct_subclasses = set(s["class_name"] for s in uisk_info["direct_subclasses"])
        expected_direct = [
            "_UIQueuingScrollView", "UIWebOverflowScrollView", "_UIHostingScrollView",
            "WKScrollView", "WebActionDisablingScrollView", "BSUIScrollView",
            "UITableView", "UICollectionView", "UITextView"
        ]
        for ed in expected_direct:
            self.assertIn(ed, direct_subclasses, f"Expected direct subclass '{ed}' missing from UIScrollView subsystem")

        # Verify indirect subclasses
        indirect_subclasses = set(s["class_name"] for s in uisk_info["indirect_subclasses"])
        self.assertIn("SBIconScrollView", indirect_subclasses)
        self.assertIn("SBAppSwitcherScrollView", indirect_subclasses)

        # Verify internal helper classes
        helper_classes = set(h["class_name"] for h in uisk_info["internal_helper_classes"])
        expected_helpers = [
            "_UIScrollViewDecelerationAnimation", "_UIScrollViewSpringAnimation",
            "_UIScrollViewScrollObserver", "_UIScrollViewScrollIndicator",
            "_UIScrollViewDimensions", "_UIScrollViewVelocity", "_UIScrollViewFrictionEstimator",
            "_UIScrollViewRubberBandPolicy", "_UIScrollViewSnappingBehavior",
            "_UIScrollViewDirectionalLock", "_UIScrollViewScrollingSpeedMonitor",
            "_UIScrollViewVFDTable", "_UIScrollViewAsyncScrollDeceleration"
        ]
        for eh in expected_helpers:
            self.assertIn(eh, helper_classes, f"Expected internal helper '{eh}' missing from UIScrollView subsystem")

    def test_framework_dependencies_graph(self):
        """R3: Verify framework dependency mapping across all 13 candidate frameworks."""
        self.assertTrue(self.dependencies_json.is_file(), "framework_dependencies.json must exist")
        with open(self.dependencies_json, "r", encoding="utf-8") as f:
            deps_data = json.load(f)

        self.assertIn("frameworks", deps_data)
        self.assertIn("circular_and_inverted_dependencies", deps_data)
        self.assertIn("architectural_layers", deps_data)

        frameworks = deps_data["frameworks"]
        required_13 = [
            "UIKitCore.framework", "QuartzCore.framework", "SwiftUI.framework", "SwiftUICore.framework",
            "WebKit.framework", "WebKitLegacy.framework", "UIKit.framework", "Gestures.framework",
            "CoreText.framework", "IOHIDPointerScrollFilter.plugin", "AnimationKit.framework",
            "SystemUIAnimationKit.framework", "UIKitServices.framework"
        ]
        for fw in required_13:
            self.assertIn(fw, frameworks, f"Required candidate framework '{fw}' missing from dependency graph")
            f_info = frameworks[fw]
            self.assertTrue(f_info["vm_base_address"].startswith("0x"))
            self.assertTrue(f_info["subcache_slice"].startswith("."))
            self.assertIsInstance(f_info["mach_o_load_commands"], list)
            self.assertIsInstance(f_info["outbound_dependencies"], list)
            self.assertIsInstance(f_info["inbound_dependents"], list)

        # Verify circular and inverted dependencies
        circs = deps_data["circular_and_inverted_dependencies"]
        self.assertGreaterEqual(len(circs), 2, "Expected at least 2 circular or inverted dependencies documented")
        pairs = [c["pair"] for c in circs]
        self.assertTrue(any("UIKitCore.framework" in p and "WebKitLegacy.framework" in p for p in pairs))
        self.assertTrue(any("UIKitCore.framework" in p and "SwiftUICore.framework" in p for p in pairs))

        # Verify architectural layering
        layers = deps_data["architectural_layers"]
        self.assertEqual(len(layers), 5, "Expected 5 architectural layer tiers")

    def test_execution_flow_preliminary(self):
        """R4: Verify 4-phase macro execution flow tracing from touch to render."""
        self.assertTrue(self.execution_flow_json.is_file(), "execution_flow_preliminary.json must exist")
        with open(self.execution_flow_json, "r", encoding="utf-8") as f:
            flow_data = json.load(f)

        self.assertIn("macro_pipeline", flow_data)
        self.assertIn("phases", flow_data)

        phases = flow_data["phases"]
        expected_phases = [
            "phase_1_input_and_gesture",
            "phase_2_drag_and_tracking",
            "phase_3_ballistic_kinematics",
            "phase_4_compositor_and_render"
        ]
        for ep in expected_phases:
            self.assertIn(ep, phases, f"Expected execution phase '{ep}' missing from execution flow")
            p_info = phases[ep]
            self.assertIn("phase_name", p_info)
            self.assertIn("trigger", p_info)
            self.assertIn("steps", p_info)
            self.assertGreater(len(p_info["steps"]), 0, f"Phase {ep} has no execution steps")
            for step in p_info["steps"]:
                self.assertIn("step_id", step)
                self.assertIn("component", step)
                self.assertIn("method", step)
                self.assertTrue(step["address"].startswith("0x"), f"Step {step['step_id']} address not hex: {step['address']}")
                self.assertIn("operation", step)

        # Verify equations
        p2 = phases["phase_2_drag_and_tracking"]
        self.assertIn("governing_equations", p2)
        self.assertIn("rubber_band_formula", p2["governing_equations"])

        p3 = phases["phase_3_ballistic_kinematics"]
        self.assertIn("governing_equations", p3)
        self.assertIn("velocity_decay", p3["governing_equations"])
        self.assertEqual(p3["governing_equations"]["normal_deceleration_rate"], 0.998)

        p4 = phases["phase_4_compositor_and_render"]
        self.assertIn("display_timing", p4)
        vfd = p4["display_timing"]["vfd_promotion_range"]
        self.assertEqual(vfd["preferred_hz"], 120.0)

    def test_anti_placeholder_across_all_artifacts(self):
        """Acceptance Criteria: Zero placeholder patterns in any Phase 2 artifact."""
        banned_patterns = [
            r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bLOREM IPSUM\b",
            r"\bINSERT HERE\b", r"\bCOMING SOON\b", r"\bOMITTED FOR BREVITY\b",
            r"\bNOT YET IMPLEMENTED\b", r"\[TBD\]", r"\[TODO\]"
        ]

        artifacts = [
            self.class_hierarchy_json,
            self.dependencies_json,
            self.execution_flow_json,
            self.findings_md
        ]
        for art in artifacts:
            content = art.read_text(encoding="utf-8")
            for pattern in banned_patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                self.assertEqual(len(matches), 0, f"Found banned pattern '{pattern}' in {art.name}")

    def test_findings_document_structure_and_depth(self):
        """R6: Findings dossier size >= 2500 bytes, Mermaid diagrams, tables, and ivar offsets."""
        self.assertTrue(self.findings_md.is_file(), "02_ARCHITECTURE_MAP.md must exist")
        size = self.findings_md.stat().st_size
        self.assertGreaterEqual(size, 2500, f"Findings doc too small ({size} < 2500)")

        content = self.findings_md.read_text(encoding="utf-8")
        h2_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
        self.assertGreaterEqual(h2_count, 6, f"Expected >= 6 '##' sections in findings (found {h2_count})")
        self.assertIn("|", content, "Markdown tables required in findings")
        self.assertIn("```", content, "Code blocks required in findings")
        self.assertIn("```mermaid", content, "Mermaid diagrams required in findings")

        # Verify Mermaid diagram types
        self.assertIn("classDiagram", content, "Mermaid classDiagram required")
        self.assertIn("sequenceDiagram", content, "Mermaid sequenceDiagram required")

        # Verify exact ivar offsets documented
        required_offsets = ["+0x100", "+0x110", "+0x120", "+0x118", "+0xd0"]
        for off in required_offsets:
            self.assertIn(off, content, f"Required ivar offset '{off}' missing from findings")

        # Verify bitfield flags documented
        bitfield_flags = ["isDragging", "isDecelerating", "delegateScrollViewDidScroll", "delegateScrollViewWillBeginDragging"]
        for bf in bitfield_flags:
            self.assertIn(bf, content, f"Required bitfield flag '{bf}' missing from findings")

        # Verify SwiftUI bridge mechanics
        swiftui_markers = ["_UIHostingScrollView", "_SwiftUIScrollViewBridge", "ScrollPosition", "ScrollGeometry"]
        for sm in swiftui_markers:
            self.assertIn(sm, content, f"SwiftUI marker '{sm}' missing from findings")

        # Verify ProMotion 120Hz VFD boosting
        vfd_markers = ["CADisplayLink", "CAFrameRateRange", "120Hz", "ProMotion"]
        for vm in vfd_markers:
            self.assertIn(vm, content, f"VFD marker '{vm}' missing from findings")

    def test_progress_gate_state(self):
        """Acceptance Criteria: scroll_progress.json updated for Phase 2 complete & Phase 3A entry."""
        self.assertTrue(self.progress_file.is_file())
        with open(self.progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)

        phases = progress.get("phases", {})
        p2 = phases.get("phase_2_architecture", {})
        self.assertEqual(p2.get("status"), "completed", "phase_2_architecture.status must be 'completed'")

        p3a = phases.get("phase_3a_input_gesture", {})
        self.assertTrue(p3a.get("entry_criteria_met"), "phase_3a_input_gesture.entry_criteria_met must be True")

        v_log = progress.get("verification_log", [])
        p2_entries = [e for e in v_log if e.get("phase_id") == "phase_2_architecture"]
        self.assertEqual(len(p2_entries), 1, "phase_2_architecture must be logged in verification_log exactly once")
        self.assertEqual(p2_entries[0].get("status"), "PASSED")

        # Verify active_phase_id maintains valid progression state
        self.assertIn(progress.get("active_phase_id"), list(progress.get("phases", {}).keys()),
                         "active_phase_id must be a valid registered phase in scroll_progress.json")
        expected_artifacts = [
            "findings/scrolling/02_ARCHITECTURE_MAP.md",
            "artifacts/scrolling/class_hierarchy.json",
            "artifacts/scrolling/framework_dependencies.json",
            "artifacts/scrolling/execution_flow_preliminary.json",
            "artifacts/scrolling/evidence_ledger.jsonl"
        ]
        self.assertEqual(p2.get("required_artifacts"), expected_artifacts,
                         "phase_2_architecture.required_artifacts must match the authoritative 5 required artifacts")

    def test_protocol_matrix_and_delegate_matrix(self):
        """R2: Verify structured protocol matrix and delegate invocation mapping in class_hierarchy.json."""
        with open(self.class_hierarchy_json, "r", encoding="utf-8") as f:
            hierarchy = json.load(f)

        self.assertIn("protocol_matrix", hierarchy)
        self.assertIn("delegate_matrix", hierarchy)

        protocols = hierarchy["protocol_matrix"]
        required_protocols = [
            "UIScrollViewDelegate",
            "UIGestureRecognizerDelegate",
            "_UIScrollViewScrollObserver",
            "UICollectionViewDelegateFlowLayout",
            "_UIGestureRecognizerDelegateInternal",
            "UIFocusItemScrollableContainer"
        ]
        for rp in required_protocols:
            self.assertIn(rp, protocols, f"Required protocol '{rp}' missing from protocol_matrix")
            p_info = protocols[rp]
            self.assertIn("visibility", p_info)
            self.assertIn("conforming_components", p_info)
            self.assertIn("methods_cataloged", p_info)
            self.assertGreater(len(p_info["methods_cataloged"]), 0)

        delegates = hierarchy["delegate_matrix"]
        self.assertGreaterEqual(len(delegates), 9)
        required_delegate_methods = [
            "scrollViewDidScroll:",
            "scrollViewWillBeginDragging:",
            "scrollViewWillEndDragging:withVelocity:targetContentOffset:",
            "scrollViewDidEndDragging:willDecelerate:",
            "scrollViewWillBeginDecelerating:",
            "scrollViewDidEndDecelerating:"
        ]
        found_methods = set(d["delegate_method"] for d in delegates)
        for rdm in required_delegate_methods:
            self.assertIn(rdm, found_methods, f"Required delegate method '{rdm}' missing from delegate_matrix")
        for d in delegates:
            self.assertTrue(d["address"].startswith("0x"))
            self.assertTrue(d["bitfield_offset"].startswith("+0x"))
            self.assertIn("bitfield_cache_flag", d)
            self.assertIn("telemetry_payload", d)
            self.assertIn("conditional_check", d)

    def test_execution_flow_all_steps_integrity(self):
        """R4: Verify comprehensive step integrity (26 steps, valid PAC00 hex addresses) across execution flow."""
        with open(self.execution_flow_json, "r", encoding="utf-8") as f:
            flow_data = json.load(f)

        phases = flow_data["phases"]
        total_steps = 0
        for p_name, p_info in phases.items():
            steps = p_info.get("steps", [])
            total_steps += len(steps)
            for s in steps:
                self.assertIsInstance(s["step_id"], int)
                self.assertGreater(len(s["component"]), 0)
                self.assertGreater(len(s["method"]), 0)
                self.assertTrue(s["address"].startswith("0x"), f"Invalid hex address: {s['address']}")
                self.assertGreater(len(s["operation"]), 10)
        self.assertEqual(total_steps, 26, f"Expected exactly 26 end-to-end execution steps (found {total_steps})")

    def test_verify_phase_script_phase2_enforcement(self):
        """Integrity: Ensure verify_phase.py contains active domain-specific assertions for Phase 2."""
        verify_py = PROJECT_ROOT / "tools/verify_phase.py"
        self.assertTrue(verify_py.is_file())
        content = verify_py.read_text(encoding="utf-8")
        self.assertIn("class_hierarchy.json", content)
        self.assertIn("framework_dependencies.json", content)
        self.assertIn("execution_flow_preliminary.json", content)
        self.assertIn("02_ARCHITECTURE_MAP.md", content)
        self.assertIn("phase_2_confirmed", content)
        self.assertIn("26-Step Macro Execution Flow Matrix", content)

    def test_ivar_layout_structural_integrity(self):
        """R5: Ensure Table 6.1 ivar memory layout is strictly contiguous with zero collisions."""
        content = self.findings_md.read_text(encoding="utf-8")
        # Ensure the 32-byte collision is resolved
        self.assertNotIn("| `+0x120` | `_contentInset` | `UIEdgeInsets` (`dddd`)| 32 |", content,
                         "_contentInset must not have size 32 colliding with _panGestureRecognizer at +0x130")
        self.assertIn("| **`+0x120`** | **`_contentInset`** | `UIEdgeInsets` Slot | 16 | 8 |", content,
                      "_contentInset slot at +0x120 must have size 16 (spanning +0x120 to +0x130)")
        self.assertIn("| `+0x130` | `_panGestureRecognizer` | `UIPanGestureRecognizer*` | 8 | 8 |", content)
        self.assertIn("| `+0x138` | `_pinchGestureRecognizer`| `UIPinchGestureRecognizer*`| 8 | 8 |", content)

    def test_evidence_ledger_binary_path_validity(self):
        """Integrity: Ensure Phase 2 evidence ledger entries cite true Mach-O binaries that physically exist."""
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("phase") == "PHASE_2":
                    bp = entry.get("binary_path", "")
                    self.assertTrue(len(bp) > 0, f"Entry {entry.get('id')} missing binary_path")
                    self.assertFalse(bp.endswith(".json"), f"Entry {entry.get('id')} cites JSON file as binary_path: {bp}")
                    self.assertFalse(bp.endswith(".plist"), f"Entry {entry.get('id')} cites plist file as binary_path: {bp}")
                    self.assertTrue((PROJECT_ROOT / bp).is_file(),
                                    f"Entry {entry.get('id')} binary_path does not exist on disk: {bp}")
                    self.assertEqual(entry.get("confidence"), "CONFIRMED")

    def test_findings_dossier_deliverable_matrix_parity(self):
        """R6: Ensure 02_ARCHITECTURE_MAP.md Table 1.1 includes all 5 required artifacts."""
        content = self.findings_md.read_text(encoding="utf-8")
        self.assertIn("### 1.1 Authoritative Phase 2 Deliverable Matrix", content)
        expected_artifacts = [
            "artifacts/scrolling/class_hierarchy.json",
            "artifacts/scrolling/framework_dependencies.json",
            "artifacts/scrolling/execution_flow_preliminary.json",
            "artifacts/scrolling/evidence_ledger.jsonl",
            "findings/scrolling/02_ARCHITECTURE_MAP.md"
        ]
        for art in expected_artifacts:
            self.assertIn(art, content, f"Required artifact '{art}' missing from Table 1.1 in 02_ARCHITECTURE_MAP.md")

    def test_findings_dossier_26_steps_parity(self):
        """R4 & R6: Ensure 02_ARCHITECTURE_MAP.md catalogs all 26 execution steps in Section 5.5."""
        content = self.findings_md.read_text(encoding="utf-8")
        self.assertIn("### 5.5 Authoritative 26-Step Macro Execution Flow Matrix", content)
        with open(self.execution_flow_json, "r", encoding="utf-8") as f:
            flow_data = json.load(f)
        phases = flow_data["phases"]
        for p_name, p_info in phases.items():
            for s in p_info.get("steps", []):
                step_marker = f"| **{s['step_id']}** |"
                self.assertIn(step_marker, content, f"Step {s['step_id']} missing from 02_ARCHITECTURE_MAP.md Section 5.5 table")
                self.assertIn(s["address"], content, f"Step {s['step_id']} address {s['address']} missing from findings dossier")

    def test_framework_metadata_consistency(self):
        """R3: Ensure framework_dependencies.json has consistent metadata counts and non-empty load commands."""
        with open(self.dependencies_json, "r", encoding="utf-8") as f:
            deps_data = json.load(f)
        tm = deps_data.get("target_metadata", {})
        self.assertEqual(tm.get("candidate_frameworks_count"), 13)
        self.assertEqual(tm.get("system_shell_frameworks_count"), 1)
        self.assertEqual(tm.get("total_frameworks_mapped"), 14)
        self.assertEqual(len(deps_data.get("frameworks", {})), 14)

if __name__ == "__main__":
    unittest.main()
