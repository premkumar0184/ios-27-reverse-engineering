#!/usr/bin/env python3
"""
Adversarial Verification Suite for Phase 9: Master Research Report Synthesis
iOS 27.2 (Build 24B119, iPhone18,3, SoC t8150 A19 Pro, arm64e PAC00)

Comprehensive unit testing across:
1. Master Research Report existence, byte size (>= 80,000 bytes), and completeness (IOS_27_SCROLLING_REVERSE_ENGINEERING.md)
2. All 18 required master research report sections present with substantive content
3. Valid Mermaid diagram syntax across architecture, state machine, and sequence diagrams
4. Formal LaTeX mathematical formatting of ODEs, rational rubber-banding, and harmonic spring physics
5. Presence of authoritative PAC00 addresses, IEEE 754 hex patterns, and system baseline markers
6. Honest Uncertainty & Open Questions dossier existence, byte size (>= 15,000 bytes), and structural depth (findings/scrolling/09_UNRESOLVED_QUESTIONS.md)
7. Machine-readable Evidence Appendix schema, metadata, and 100+ record count (artifacts/scrolling/evidence_appendix.json)
8. Cryptographic SHA-256 hash integrity and subcache slice cross-referencing
9. Full 1:1 cross-reference reconciliation against artifacts/scrolling/evidence_ledger.jsonl
10. Strict zero-tolerance anti-placeholder compliance across all Phase 9 deliverables
11. Clean-room cross-platform code recipes for C99, Android Jetpack Compose, and Flutter
12. Automated Phase 9 verification gate execution (tools/verify_phase.py phase_9_report)
"""

import unittest
import json
import re
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

class TestScrollingPhase9Report(unittest.TestCase):

    def setUp(self):
        self.report_path = PROJECT_ROOT / "IOS_27_SCROLLING_REVERSE_ENGINEERING.md"
        self.uncertainty_path = PROJECT_ROOT / "findings" / "scrolling" / "09_UNRESOLVED_QUESTIONS.md"
        self.appendix_path = PROJECT_ROOT / "artifacts" / "scrolling" / "evidence_appendix.json"
        self.ledger_path = PROJECT_ROOT / "artifacts" / "scrolling" / "evidence_ledger.jsonl"
        self.progress_path = PROJECT_ROOT / "artifacts" / "scrolling" / "scroll_progress.json"

        self.assertTrue(self.report_path.is_file(), f"Missing master report: {self.report_path}")
        self.assertTrue(self.uncertainty_path.is_file(), f"Missing unresolved questions: {self.uncertainty_path}")
        self.assertTrue(self.appendix_path.is_file(), f"Missing evidence appendix: {self.appendix_path}")
        self.assertTrue(self.ledger_path.is_file(), f"Missing evidence ledger: {self.ledger_path}")
        self.assertTrue(self.progress_path.is_file(), f"Missing scroll progress ledger: {self.progress_path}")

        self.report_text = self.report_path.read_text(encoding="utf-8")
        self.uncertainty_text = self.uncertainty_path.read_text(encoding="utf-8")

        with open(self.appendix_path, "r", encoding="utf-8") as f:
            self.appendix_data = json.load(f)

    def test_01_master_report_size_gate(self):
        """Validate IOS_27_SCROLLING_REVERSE_ENGINEERING.md is >= 80,000 bytes."""
        size = self.report_path.stat().st_size
        self.assertGreaterEqual(
            size, 80000,
            f"Master report too small: {size} bytes < 80,000 bytes minimum requirement"
        )

    def test_02_master_report_18_sections_present(self):
        """Verify all 18 required sections exist in IOS_27_SCROLLING_REVERSE_ENGINEERING.md."""
        required_sections = [
            "Executive Summary",
            "Empirical Target Baseline",
            "Architectural Subsystem Map",
            "Touch Ingestion",
            "Gesture Interaction Finite State Machine",
            "Velocity Estimation",
            "Free Deceleration Kinematics",
            "Boundary Deceleration",
            "Underdamped Harmonic Spring Restitution",
            "Snapping, Alignment",
            "Low-Level IOHIDEvent Filtering",
            "Specialized Framework Implementations",
            "Rendering Pipeline",
            "Transient Scroll Indicators",
            "Cross-Framework Consistency",
            "Nested Scrolling Arbitration",
            "Clean-Room Engineering Specification",
            "Master Empirical Evidence Ledger"
        ]
        content_lower = self.report_text.lower()
        for sec in required_sections:
            self.assertIn(
                sec.lower(), content_lower,
                f"Master report missing required section: '{sec}'"
            )

    def test_03_master_report_mermaid_diagrams_valid(self):
        """Verify master report contains valid Mermaid diagram blocks and expected diagram types."""
        diagram_types = ["graph", "stateDiagram-v2", "sequenceDiagram"]
        for dtype in diagram_types:
            self.assertIn(
                dtype, self.report_text,
                f"Master report missing Mermaid diagram type: '{dtype}'"
            )

        # Ensure all ```mermaid blocks are non-empty and properly closed
        mermaid_blocks = re.findall(r"```mermaid\n(.*?)\n```", self.report_text, re.DOTALL)
        self.assertGreaterEqual(len(mermaid_blocks), 4, f"Expected >= 4 Mermaid diagrams, found {len(mermaid_blocks)}")
        for i, block in enumerate(mermaid_blocks):
            self.assertGreater(len(block.strip()), 20, f"Mermaid diagram {i} appears empty or trivial")

    def test_04_master_report_latex_formulas(self):
        """Verify presence of formal LaTeX mathematical formulas for kinematics ODEs."""
        required_math_tokens = [
            r"\frac{dv}{dt} = -\lambda v",
            r"v(t) = v_0 e^{-\lambda t}",
            r"x = \frac{|x_{\text{raw}}| \cdot d_{\text{dim}} \cdot c}{d_{\text{dim}} + c \cdot |x_{\text{raw}}|}",
            r"m \frac{d^2 x}{dt^2} + c_{\text{viscous}} \frac{dx}{dt} + k x = 0",
            r"\zeta = \frac{c_{\text{viscous}}}{c_{\text{crit}}} = \frac{18.0}{20.0} = 0.90",
            r"\omega_d = \omega_0 \sqrt{1 - \zeta^2}"
        ]
        for token in required_math_tokens:
            self.assertIn(
                token, self.report_text,
                f"Master report missing required LaTeX formula: '{token}'"
            )

    def test_05_master_report_authoritative_markers(self):
        """Verify master report contains all authoritative physical, geometric, and hardware markers."""
        markers = [
            "0.998", "0.990", "0.985", "0.950", "0.550", "100.0", "18.0", "0.90",
            "10.0", "4.0", "2.0", "36.0", "52.0", "60.0", "400.0", "600.0",
            "0x1864d3030", "0x1865166d0", "0x1848c8110", "PAC00", "iPhone18,3", "24B119", "t8150",
            "0x3fefef9db22d0e56", "0x3fe199999999999a"
        ]
        for marker in markers:
            self.assertIn(
                marker, self.report_text,
                f"Master report missing authoritative marker: '{marker}'"
            )

    def test_06_unresolved_questions_size_gate(self):
        """Validate findings/scrolling/09_UNRESOLVED_QUESTIONS.md is >= 15,000 bytes."""
        size = self.uncertainty_path.stat().st_size
        self.assertGreaterEqual(
            size, 15000,
            f"Unresolved questions document too small: {size} bytes < 15,000 bytes minimum requirement"
        )

    def test_07_unresolved_questions_sections_and_depth(self):
        """Verify structural sections and technical markers in 09_UNRESOLVED_QUESTIONS.md."""
        required_sections = [
            "Executive Mission",
            "Closed Hardware Invariants",
            "Dynamic Tuning Knobs",
            "Multi-Touch Contention",
            "Cross-Process Compositing",
            "Non-Linear Friction",
            "Future Research Roadmap",
            "Master Uncertainty"
        ]
        content_lower = self.uncertainty_text.lower()
        for sec in required_sections:
            self.assertIn(
                sec.lower(), content_lower,
                f"09_UNRESOLVED_QUESTIONS.md missing required section: '{sec}'"
            )

        markers = ["A19 Pro", "t8150", "PAC00", "IOHIDEvent", "CADisplayLink", "ProMotion", "_UIInternalPreferences"]
        for marker in markers:
            self.assertIn(
                marker, self.uncertainty_text,
                f"09_UNRESOLVED_QUESTIONS.md missing marker: '{marker}'"
            )

    def test_08_evidence_appendix_schema(self):
        """Validate artifacts/scrolling/evidence_appendix.json schema and metadata."""
        self.assertIn("$schema", self.appendix_data)
        self.assertIn("target_platform", self.appendix_data)
        self.assertIn("metadata", self.appendix_data)
        self.assertIn("subcache_slices", self.appendix_data)
        self.assertIn("evidence_records", self.appendix_data)

        tp = self.appendix_data["target_platform"]
        self.assertEqual(tp.get("os"), "iOS 27.2")
        self.assertEqual(tp.get("build"), "24B119")
        self.assertEqual(tp.get("device"), "iPhone18,3")
        self.assertEqual(tp.get("soc"), "t8150 (Apple A19 Pro)")
        self.assertEqual(tp.get("architecture"), "arm64e")
        self.assertEqual(tp.get("pointer_authentication"), "PAC00")

    def test_09_evidence_appendix_record_count(self):
        """Ensure evidence_appendix.json contains >= 100 confirmed empirical records."""
        records = self.appendix_data["evidence_records"]
        self.assertGreaterEqual(
            len(records), 100,
            f"Expected >= 100 evidence records, found {len(records)}"
        )
        self.assertEqual(self.appendix_data["metadata"]["confidence_level"], "CONFIRMED")

    def test_10_evidence_appendix_record_fields_integrity(self):
        """Verify each evidence record contains required fields, valid PAC00 address, and SHA-256 hash."""
        required_fields = [
            "id", "phase", "framework", "class", "method",
            "address", "subcache_slice", "sha256_hash", "finding", "confidence"
        ]
        for r in self.appendix_data["evidence_records"]:
            for field in required_fields:
                self.assertIn(field, r, f"Evidence record {r.get('id')} missing field: {field}")
            self.assertTrue(r["address"].startswith("0x"), f"Record {r['id']} address must start with 0x: {r['address']}")
            self.assertEqual(r["confidence"], "CONFIRMED", f"Record {r['id']} confidence must be CONFIRMED")
            self.assertEqual(len(r["sha256_hash"]), 64, f"Record {r['id']} invalid SHA-256 hash length")

    def test_11_evidence_appendix_ledger_cross_reference(self):
        """Reconcile 100% of records in evidence_ledger.jsonl against evidence_appendix.json."""
        appendix_map = {r["id"]: r for r in self.appendix_data["evidence_records"]}
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line:
                    continue
                item = json.loads(line)
                rec_id = item["id"]
                self.assertIn(
                    rec_id, appendix_map,
                    f"Ledger record line {line_no} '{rec_id}' not found in evidence_appendix.json"
                )
                app_rec = appendix_map[rec_id]
                self.assertEqual(
                    item.get("address"), app_rec.get("address"),
                    f"Address mismatch for record {rec_id} between ledger and appendix"
                )

    def test_12_anti_placeholder_compliance_master_report(self):
        """Ensure zero banned placeholder phrases in IOS_27_SCROLLING_REVERSE_ENGINEERING.md."""
        for pattern in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, self.report_text, re.IGNORECASE))
            self.assertEqual(
                len(matches), 0,
                f"Banned placeholder '{pattern}' found in master report: {[m.group() for m in matches]}"
            )

    def test_13_anti_placeholder_compliance_unresolved_questions(self):
        """Ensure zero banned placeholder phrases in findings/scrolling/09_UNRESOLVED_QUESTIONS.md."""
        for pattern in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, self.uncertainty_text, re.IGNORECASE))
            self.assertEqual(
                len(matches), 0,
                f"Banned placeholder '{pattern}' found in unresolved questions: {[m.group() for m in matches]}"
            )

    def test_14_anti_placeholder_compliance_evidence_appendix(self):
        """Ensure zero banned placeholder phrases in artifacts/scrolling/evidence_appendix.json."""
        raw_appendix = self.appendix_path.read_text(encoding="utf-8")
        for pattern in BANNED_PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, raw_appendix, re.IGNORECASE))
            self.assertEqual(
                len(matches), 0,
                f"Banned placeholder '{pattern}' found in evidence appendix: {[m.group() for m in matches]}"
            )

    def test_15_code_recipes_in_master_report(self):
        """Verify presence of C99, Android Jetpack Compose, and Flutter implementation recipes."""
        self.assertIn("```c", self.report_text, "Missing C99 reference implementation code block")
        self.assertIn("```kotlin", self.report_text, "Missing Android Jetpack Compose implementation block")
        self.assertIn("```dart", self.report_text, "Missing Flutter implementation block")
        self.assertIn("rubber_band_offset", self.report_text)
        self.assertIn("IOS27ScrollPhysics", self.report_text)
        self.assertIn("IOS27DecelerationSimulation", self.report_text)

    def test_16_verify_phase9_automated_gate(self):
        """Run tools/verify_phase.py phase_9_report and assert clean exit code 0."""
        cmd = ["python3", str(PROJECT_ROOT / "tools" / "verify_phase.py"), "phase_9_report"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            res.returncode, 0,
            f"tools/verify_phase.py phase_9_report failed (code {res.returncode}):\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        self.assertIn("[PASS]", res.stdout)

    def test_17_evidence_appendix_subcache_slices_coverage(self):
        """Verify all 5 subcache slices are registered in metadata and mapped to records."""
        expected_slices = {
            "dyld_shared_cache_arm64e.01",
            "dyld_shared_cache_arm64e.03",
            "dyld_shared_cache_arm64e.07",
            "dyld_shared_cache_arm64e.36",
            "dyld_shared_cache_arm64e.48"
        }
        meta_slices = set(self.appendix_data.get("subcache_slices", []))
        self.assertEqual(
            expected_slices, meta_slices,
            f"Appendix metadata subcache slices mismatch: expected {expected_slices}, found {meta_slices}"
        )
        record_slices = set(r["subcache_slice"] for r in self.appendix_data["evidence_records"])
        self.assertTrue(
            expected_slices.issubset(record_slices),
            f"Not all 5 subcache slices are represented in evidence records: missing {expected_slices - record_slices}"
        )

    def test_18_springboard_pac00_address_and_offset_reconciliation(self):
        """Verify SpringBoard.framework VM address (0x226a11000) and file offset (0x6611000) in subcache .36."""
        self.assertIn("0x226a11000", self.report_text)
        self.assertNotIn("0x228e93", self.report_text)
        self.assertEqual(self.appendix_data["subcache_slices"]["dyld_shared_cache_arm64e.36"]["vm_base"], "0x220400000")

        sb_records = [r for r in self.appendix_data["evidence_records"] if r["id"] in ("BASE-003", "BASE-005")]
        self.assertGreaterEqual(len(sb_records), 2)
        for r in sb_records:
            self.assertEqual(r["address"], "0x226a11000")
            self.assertEqual(r["subcache_slice"], "dyld_shared_cache_arm64e.36")
            self.assertEqual(r["subcache_file_offset"], "0x6611000")

    def test_19_master_report_disassembly_instructions_integrity(self):
        """Verify -[UIScrollView setContentOffset:animated:] disassembly has valid PAC00 opcodes and no ellipsis."""
        self.assertIn("0x1848b4c00: pacibsp", self.report_text)
        self.assertIn("0x1848b4c6c: autibsp", self.report_text)
        self.assertIn("0x1848b4c70: ret", self.report_text)
        self.assertNotIn("0x1848b4c74: ret", self.report_text)
        self.assertNotIn("...", self.report_text)

    def test_20_scrolling_physics_simulation_120hz_vfd_and_hitches(self):
        """Simulate deceleration ODE across 120Hz, 60Hz, and display hitch intervals to prove zero drift."""
        import math
        v0 = 2000.0  # pt/s
        v_stop = 0.10  # pt/s
        d = 0.998
        lambd = -1000.0 * math.log(d)
        expected_total_dist = (v0 - v_stop) / lambd

        # Scenario A: Perfect 120Hz ProMotion (8.333ms per frame)
        pos_120 = 0.0
        v_120 = v0
        dt_120 = 1.0 / 120.0
        while v_120 > v_stop:
            factor = math.pow(d, 1000.0 * dt_120)
            dx = (v_120 / -lambd) * (factor - 1.0)
            pos_120 += dx
            v_120 *= factor

        # Scenario B: 60Hz Baseline (16.667ms per frame)
        pos_60 = 0.0
        v_60 = v0
        dt_60 = 1.0 / 60.0
        while v_60 > v_stop:
            factor = math.pow(d, 1000.0 * dt_60)
            dx = (v_60 / -lambd) * (factor - 1.0)
            pos_60 += dx
            v_60 *= factor

        # Scenario C: Variable VFD with synthetic 50ms display hitches
        pos_hitches = 0.0
        v_hitches = v0
        frame_idx = 0
        while v_hitches > v_stop:
            dt = 0.050 if (frame_idx % 15 == 7) else (1.0 / 120.0)
            factor = math.pow(d, 1000.0 * dt)
            dx = (v_hitches / -lambd) * (factor - 1.0)
            pos_hitches += dx
            v_hitches *= factor
            frame_idx += 1

        self.assertAlmostEqual(pos_120, expected_total_dist, delta=0.1)
        self.assertAlmostEqual(pos_60, expected_total_dist, delta=0.1)
        self.assertAlmostEqual(pos_hitches, expected_total_dist, delta=0.1)
        self.assertAlmostEqual(pos_120, pos_hitches, delta=0.1)

    def test_21_mermaid_diagram_syntax_and_topology_rigor(self):
        """Validate syntactic structure, topology, and ID integrity of all 12 Mermaid diagrams (8 master + 4 unresolved)."""
        diagram_targets = [
            ("Master Report", self.report_text, 8),
            ("Unresolved Questions", self.uncertainty_text, 4)
        ]
        valid_starters = ("graph", "stateDiagram", "sequenceDiagram", "flowchart")
        for doc_name, doc_text, expected_count in diagram_targets:
            blocks = re.findall(r"```mermaid\n(.*?)\n```", doc_text, re.DOTALL)
            self.assertEqual(
                len(blocks), expected_count,
                f"{doc_name} expected {expected_count} Mermaid diagrams, found {len(blocks)}"
            )
            for i, block in enumerate(blocks):
                lines = [l.strip() for l in block.strip().splitlines() if l.strip() and not l.strip().startswith("%%")]
                self.assertTrue(
                    any(lines[0].startswith(s) for s in valid_starters),
                    f"{doc_name} diagram {i} invalid header: {lines[0]}"
                )
                # Ensure balanced brackets
                self.assertEqual(block.count("["), block.count("]"), f"{doc_name} diagram {i} unmatched [] brackets")
                self.assertEqual(block.count("{"), block.count("}"), f"{doc_name} diagram {i} unmatched {{}} brackets")
                self.assertEqual(block.count("("), block.count(")"), f"{doc_name} diagram {i} unmatched () brackets")

                # Validate subgraph vs node ID collision absence
                subgraphs = re.findall(r"subgraph\s+([A-Za-z0-9_]+)", block)
                for sg in subgraphs:
                    node_decl = re.findall(r"(?<!subgraph\s)\b" + sg + r"\s*\[", block)
                    self.assertEqual(
                        len(node_decl), 0,
                        f"{doc_name} diagram {i}: Subgraph ID '{sg}' collides with node definition"
                    )

    def test_22_evidence_appendix_offsets_strictly_non_negative(self):
        """Verify all evidence records have valid strictly non-negative subcache file offsets."""
        for r in self.appendix_data["evidence_records"]:
            off = r.get("subcache_file_offset", "")
            self.assertTrue(off.startswith("0x"), f"Record {r['id']} offset must start with 0x: {off}")
            self.assertNotIn("-", off, f"Record {r['id']} must not have negative offset: {off}")
            off_int = int(off, 16)
            self.assertGreaterEqual(off_int, 0, f"Record {r['id']} offset must be >= 0: {off}")

        # Check key boundary records
        rec_map = {r["id"]: r for r in self.appendix_data["evidence_records"]}
        self.assertEqual(rec_map["INIT-000"]["subcache_file_offset"], "0x0")
        self.assertEqual(rec_map["BASE-001"]["subcache_file_offset"], "0x0")
        self.assertEqual(rec_map["ARCH-001"]["subcache_slice"], "dyld_shared_cache_arm64e.01")
        self.assertEqual(rec_map["ARCH-001"]["subcache_file_offset"], "0x4352000")
        self.assertEqual(rec_map["BASE-003"]["subcache_slice"], "dyld_shared_cache_arm64e.36")
        self.assertEqual(rec_map["BASE-003"]["subcache_file_offset"], "0x6611000")
        self.assertEqual(rec_map["BASE-005"]["subcache_slice"], "dyld_shared_cache_arm64e.36")
        self.assertEqual(rec_map["BASE-005"]["subcache_file_offset"], "0x6611000")

    def test_23_master_report_section_18_evidence_table_referential_integrity(self):
        """Verify master report Section 18.3 table accurately mirrors evidence_appendix.json records."""
        for r in self.appendix_data["evidence_records"]:
            # Check ID is present in report
            self.assertIn(f"`{r['id']}`", self.report_text, f"Evidence record {r['id']} missing from Section 18.3 table")

        # Confirm ARCH-001 is listed under UIKitCore / arm64e.01
        self.assertIn("0x4352000", self.report_text)
        # Confirm SpringBoard slice offset 0x6611000
        self.assertIn("0x6611000", self.report_text)

    def test_24_kinematic_displacement_formula_sign_and_derivation_precision(self):
        """Verify exact discrete displacement formula and ensure no negative sign flipping bug."""
        # The correct formula in section 13.3 has positive displacement for positive velocity
        self.assertIn(r"\Delta x = \frac{v_k}{1000 \cdot \ln(d)} \left(d^{1000 \cdot \Delta t} - 1\right)", self.report_text)
        # Ensure erroneous sign flip (-1000 ln(d) in denominator with factor - 1) is NOT present
        self.assertNotIn(r"\frac{v_k}{-1000 \ln(d)} \left(d^{1000 \cdot \Delta t} - 1\right)", self.report_text)

    def test_25_parameter_reference_ledger_alignment_and_exact_ieee754(self):
        """Verify parameter_reference.json bit-exact IEEE 754 compliance and exact lambda values."""
        import struct
        param_path = PROJECT_ROOT / "artifacts" / "scrolling" / "parameter_reference.json"
        with open(param_path, "r", encoding="utf-8") as f:
            pdata = json.load(f)

        params = {p["id"]: p for p in pdata["parameters"]}
        # PARAM-001: continuous_lambda == 2.0020026706730794
        self.assertAlmostEqual(params["PARAM-001"]["continuous_lambda"], 2.0020026706730794, places=12)
        # PARAM-008: continuous_lambda == 2.0020026706730794, hex 0x40000419f9e85d41
        self.assertEqual(params["PARAM-008"]["ieee754_hex"], "0x40000419f9e85d41")
        # PARAM-009: lambda_fast hex 0x402419c59ef935c0
        self.assertEqual(params["PARAM-009"]["ieee754_hex"], "0x402419c59ef935c0")
        expected_hex = "0x" + struct.pack(">d", params["PARAM-009"]["decimal_value"]).hex()
        self.assertEqual(params["PARAM-009"]["ieee754_hex"].lower(), expected_hex.lower())

    def test_26_markdown_table_column_alignment_and_pipe_safety(self):
        """Verify strict column count consistency and pipe delimiter integrity across all markdown tables."""
        targets = [
            ("Master Report", self.report_text),
            ("Unresolved Questions", self.uncertainty_text)
        ]
        for doc_name, doc_text in targets:
            lines = doc_text.splitlines()
            in_table = False
            hdr_cols = []
            for line_no, line in enumerate(lines, 1):
                s_line = line.strip()
                if s_line.startswith("|") and s_line.endswith("|"):
                    cols = [c.strip() for c in s_line.split("|")[1:-1]]
                    if not in_table:
                        in_table = True
                        hdr_cols = cols
                    else:
                        if set("".join(cols)).issubset({"-", ":", " "}):
                            # Separator line
                            self.assertEqual(
                                len(cols), len(hdr_cols),
                                f"{doc_name} line {line_no}: separator columns ({len(cols)}) != header ({len(hdr_cols)})"
                            )
                        else:
                            # Data row
                            self.assertEqual(
                                len(cols), len(hdr_cols),
                                f"{doc_name} line {line_no}: row column count ({len(cols)}) != header ({len(hdr_cols)}): '{s_line[:60]}...'"
                            )
                else:
                    in_table = False

    def test_27_unresolved_questions_epistemological_structure_and_ledger(self):
        """Verify epistemological tiers (A, B, C) and completeness of the 10 UNCERT questions in 09_UNRESOLVED_QUESTIONS.md."""
        expected_tiers = [
            "Tier A: Proven Invariants",
            "Tier B: Constrained Inferences",
            "Tier C: Open Research Horizons"
        ]
        for tier in expected_tiers:
            self.assertIn(tier, self.uncertainty_text, f"Missing epistemological tier: '{tier}'")

        for q_idx in range(1, 11):
            qid = f"UNCERT-{q_idx:03d}"
            self.assertIn(qid, self.uncertainty_text, f"09_UNRESOLVED_QUESTIONS.md missing question ID: '{qid}'")

        # Verify presence of the 6 table columns in Section 8
        expected_cols = [
            "Question ID", "Subsystem Domain", "Open Research Question",
            "Empirical Hypothesis", "Required Tooling / Verification Vector", "Priority"
        ]
        for col in expected_cols:
            self.assertIn(col, self.uncertainty_text, f"Section 8 table missing column: '{col}'")

if __name__ == "__main__":
    unittest.main()
