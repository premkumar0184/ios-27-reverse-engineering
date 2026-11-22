#!/usr/bin/env python3
"""
tools/test_phase8_m3_adversarial.py
Adversarial empirical test harness targeting progress.json invariants,
Phase 8 requirements (notes count >= 4, verified_by, completed_at),
schema depth, and regression testing across all 8 phases via tools/verify_phase.py.

Author: Challenger M3-1 (Phase 8 Milestone 3)
"""

import sys
import os
import json
import re
import copy
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_PATH = PROJECT_ROOT / "progress.json"
VERIFY_PHASE_SCRIPT = PROJECT_ROOT / "tools" / "verify_phase.py"

BANNED_PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bLOREM IPSUM\b",
    r"\bINSERT HERE\b",
    r"\bCOMING SOON\b",
    r"\bOMITTED FOR BREVITY\b",
    r"\bNOT YET IMPLEMENTED\b",
    r"\[TBD\]",
    r"\[TODO\]",
    r"\[PLACEHOLDER\]"
]

EXPECTED_PHASE_IDS = [
    "phase_01_recon_and_inventory",
    "phase_02_crypto_and_extraction",
    "phase_03_kernel_sptm_txm",
    "phase_04_firmware_coprocessors",
    "phase_05_rootfs_dyld_frameworks",
    "phase_06_ui_and_applications",
    "phase_07_security_trust_architecture",
    "phase_08_graphify_synthesis"
]

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, condition: bool, test_name: str, details: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {test_name}: {details}"
            print(msg)
            self.errors.append(msg)

    def print_summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"Adversarial Challenge Test Results: {self.passed}/{total} Passed")
        print("=" * 60)
        if self.failed > 0:
            print("\nFailures:")
            for e in self.errors:
                print(e)
            return False
        else:
            print("\nALL ADVERSARIAL CHECKS PASSED.")
            return True


def test_file_and_utf8(runner: TestRunner):
    print("\n--- Suite 1: progress.json Raw File & UTF-8 Invariants ---")
    
    # 1.1 Exists and is file
    runner.check(PROGRESS_PATH.is_file(), "progress_json_exists", f"File not found at {PROGRESS_PATH}")
    if not PROGRESS_PATH.is_file():
        return None, None

    # 1.2 File size check (> 1KB, not excessively large)
    size = PROGRESS_PATH.stat().st_size
    runner.check(size > 1024, "progress_json_non_empty_substantial", f"File size is {size} bytes")

    # 1.3 Strict UTF-8 decoding without BOM
    raw_bytes = PROGRESS_PATH.read_bytes()
    runner.check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "progress_json_no_utf8_bom", "Found UTF-8 BOM prefix")

    try:
        raw_text = raw_bytes.decode("utf-8")
        runner.check(True, "progress_json_valid_utf8", "Successfully decoded UTF-8")
    except UnicodeDecodeError as ue:
        runner.check(False, "progress_json_valid_utf8", f"UTF-8 decode failed: {ue}")
        return None, None

    # 1.4 Strict JSON parsing
    try:
        data = json.loads(raw_text)
        runner.check(isinstance(data, dict), "progress_json_is_json_object", f"Top level type: {type(data)}")
    except json.JSONDecodeError as je:
        runner.check(False, "progress_json_strict_parse", f"JSON decode failed: {je}")
        return None, None

    # 1.5 Scan raw file for banned unfulfilled placeholders
    found_placeholders = []
    for pattern in BANNED_PLACEHOLDER_PATTERNS:
        matches = list(re.finditer(pattern, raw_text, re.IGNORECASE))
        if matches:
            found_placeholders.append(f"{pattern} ({len(matches)} occurrences)")
    runner.check(len(found_placeholders) == 0, "progress_json_no_banned_tokens", f"Found: {found_placeholders}")

    # 1.6 Case-sensitive uppercase PLACEHOLDER token check
    uc_placeholder = list(re.finditer(r"\bPLACEHOLDER\b", raw_text))
    runner.check(len(uc_placeholder) == 0, "progress_json_no_uppercase_placeholder", f"Found: {len(uc_placeholder)} uppercase PLACEHOLDER")

    # 1.7 Deep value inspection: verify that no string value in JSON is placeholder-like
    def inspect_values(val, path="root"):
        errs = []
        if isinstance(val, str):
            clean = val.strip().lower()
            if clean in ["placeholder", "todo", "tbd", "n/a", "none"]:
                errs.append(f"{path} has placeholder-like value '{val}'")
            if clean.startswith("placeholder:") or clean.startswith("todo:"):
                errs.append(f"{path} has prefix placeholder '{val}'")
        elif isinstance(val, list):
            for i, item in enumerate(val):
                errs.extend(inspect_values(item, f"{path}[{i}]"))
        elif isinstance(val, dict):
            for k, v in val.items():
                errs.extend(inspect_values(v, f"{path}.{k}"))
        return errs

    val_errors = inspect_values(data)
    runner.check(len(val_errors) == 0, "progress_json_values_no_placeholder_literals", f"Errors: {val_errors}")

    return raw_text, data


def test_schema_and_metadata(runner: TestRunner, data: dict):
    print("\n--- Suite 2: Schema & Metadata Invariants ---")
    if not data:
        return

    # 2.1 Top-level keys
    required_top_keys = ["$schema", "project", "execution_policy", "active_phase_id", "overall_status", "phases", "verification_log", "last_updated"]
    for k in required_top_keys:
        runner.check(k in data, f"top_key_{k}_present", f"Missing key '{k}' in progress.json")

    # 2.2 Project metadata
    proj = data.get("project", {})
    runner.check(proj.get("name") == "iOS 27.2 Full-Stack Reverse Engineering Pipeline", "project_name_exact", f"Got: {proj.get('name')}")
    runner.check(proj.get("version") == "27.2", "project_version_27.2", f"Got: {proj.get('version')}")
    runner.check(proj.get("build") == "24B119", "project_build_24B119", f"Got: {proj.get('build')}")
    runner.check(proj.get("target_hardware") == "iPhone18,3", "project_hw_iphone18_3", f"Got: {proj.get('target_hardware')}")
    runner.check(proj.get("soc") == "t8150", "project_soc_t8150", f"Got: {proj.get('soc')}")

    # 2.3 Execution policy booleans
    ep = data.get("execution_policy", {})
    runner.check(ep.get("step_by_step_enforcement") is True, "policy_step_by_step_enforcement", f"Got {ep.get('step_by_step_enforcement')}")
    runner.check(ep.get("active_phase_must_be_single") is True, "policy_active_phase_must_be_single", f"Got {ep.get('active_phase_must_be_single')}")
    runner.check(ep.get("disallow_placeholder_documentation") is True, "policy_disallow_placeholder_doc", f"Got {ep.get('disallow_placeholder_documentation')}")
    runner.check(ep.get("require_disk_artifact_verification") is True, "policy_require_disk_artifact", f"Got {ep.get('require_disk_artifact_verification')}")

    # 2.4 Overall status and active phase id invariants
    overall_status = data.get("overall_status")
    runner.check(overall_status == "completed", "overall_status_is_completed", f"Got: '{overall_status}'")

    active_phase_id = data.get("active_phase_id")
    runner.check(active_phase_id is None, "active_phase_id_is_strictly_none", f"Got: '{active_phase_id}'")

    # 2.5 last_updated timestamp ISO 8601 validity
    last_updated = data.get("last_updated")
    iso_valid = False
    try:
        datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        iso_valid = True
    except Exception as e:
        iso_valid = False
    runner.check(iso_valid, "last_updated_iso8601_valid", f"Got: '{last_updated}'")


def test_phases_collection(runner: TestRunner, data: dict):
    print("\n--- Suite 3: All 8 Phases Collection Invariants ---")
    if not data:
        return

    phases = data.get("phases", [])
    runner.check(len(phases) == 8, "phases_count_exactly_8", f"Got {len(phases)} phases")

    seen_ids = []
    seen_numbers = []

    for idx, p in enumerate(phases):
        p_id = p.get("id")
        p_num = p.get("number")
        seen_ids.append(p_id)
        seen_numbers.append(p_num)

        # Monotonic sequential ordering
        runner.check(p_num == idx + 1, f"phase_{idx+1}_number_monotonic", f"Expected {idx+1}, got {p_num}")
        runner.check(p_id == EXPECTED_PHASE_IDS[idx], f"phase_{idx+1}_id_matches_expected", f"Expected {EXPECTED_PHASE_IDS[idx]}, got {p_id}")

        # Completion status
        status = p.get("status")
        runner.check(status == "completed", f"{p_id}_status_completed", f"Status is '{status}'")

        # completed_at ISO 8601
        completed_at = p.get("completed_at")
        cat_valid = False
        try:
            if completed_at:
                datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                cat_valid = True
        except Exception:
            cat_valid = False
        runner.check(cat_valid, f"{p_id}_completed_at_valid_iso", f"Got: {completed_at}")

        # verified_by
        vby = p.get("verified_by")
        runner.check(vby == "tools/verify_phase.py", f"{p_id}_verified_by_tool", f"Got: {vby}")

        # Notes count >= 4
        notes = p.get("notes", [])
        runner.check(isinstance(notes, list) and len(notes) >= 4, f"{p_id}_notes_count_ge_4", f"Notes count: {len(notes)}")

        # Notes content non-trivial
        all_notes_solid = all(isinstance(n, str) and len(n.strip()) >= 20 for n in notes)
        runner.check(all_notes_solid, f"{p_id}_notes_substantive", "Found trivial or non-string notes")

        # Required disk artifacts exist and non-empty
        req_arts = p.get("required_disk_artifacts", [])
        runner.check(len(req_arts) > 0, f"{p_id}_has_required_disk_artifacts", f"Count: {len(req_arts)}")
        for art in req_arts:
            art_path = PROJECT_ROOT / art
            runner.check(art_path.exists() and (art_path.is_file() and art_path.stat().st_size > 0 or art_path.is_dir()),
                         f"{p_id}_artifact_{Path(art).name}_exists_non_empty", f"Missing or empty: {art}")

        # Findings document exists and non-empty
        f_doc = p.get("findings_document")
        if f_doc:
            f_path = PROJECT_ROOT / f_doc
            runner.check(f_path.is_file() and f_path.stat().st_size >= 2500,
                         f"{p_id}_findings_doc_ge_2500_bytes", f"Missing or too small: {f_doc} ({f_path.stat().st_size if f_path.is_file() else 'missing'})")

    runner.check(seen_ids == EXPECTED_PHASE_IDS, "all_phase_ids_unique_and_ordered", f"Got: {seen_ids}")
    runner.check(seen_numbers == [1, 2, 3, 4, 5, 6, 7, 8], "all_phase_numbers_1_to_8", f"Got: {seen_numbers}")


def test_phase_8_deep_inspection(runner: TestRunner, data: dict):
    print("\n--- Suite 4: Phase 8 Deep Specification & Artifact Inspection ---")
    if not data:
        return

    p8 = None
    for p in data.get("phases", []):
        if p.get("id") == "phase_08_graphify_synthesis":
            p8 = p
            break

    runner.check(p8 is not None, "phase_8_record_exists", "Phase 8 not found in progress.json")
    if not p8:
        return

    # Check prerequisites contain all 7 prior phases
    prereqs = p8.get("prerequisites", [])
    expected_prereqs = EXPECTED_PHASE_IDS[:7]
    runner.check(prereqs == expected_prereqs, "phase_8_prerequisites_all_7_phases", f"Prereqs: {prereqs}")

    # Check Phase 8 notes specifically
    notes = p8.get("notes", [])
    runner.check(len(notes) >= 4, "phase_8_notes_length_ge_4", f"Actual: {len(notes)}")

    # Check note content mentions required deliverables
    notes_joined = " ".join(notes)
    runner.check("graphify-out/graph.json" in notes_joined or "NetworkX" in notes_joined, "phase_8_notes_mention_graph", "Notes do not mention graph")
    runner.check("traversal" in notes_joined or "path" in notes_joined or "hops" in notes_joined, "phase_8_notes_mention_traversals", "Notes do not mention traversals")
    runner.check("08_SYNTHESIS_AND_GRAPH.md" in notes_joined or "Master Architectural" in notes_joined, "phase_8_notes_mention_dossier", "Notes do not mention dossier")
    runner.check("verify_phase.py" in notes_joined or "verification" in notes_joined, "phase_8_notes_mention_verification", "Notes do not mention verification")

    # Check required disk artifacts
    expected_p8_arts = [
        "graphify-out/graph.json",
        "graphify-out/GRAPH_REPORT.md",
        "findings/08_SYNTHESIS_AND_GRAPH.md"
    ]
    p8_arts = p8.get("required_disk_artifacts", [])
    runner.check(p8_arts == expected_p8_arts, "phase_8_required_artifacts_match_spec", f"Got: {p8_arts}")

    # Deep check graphify-out/graph.json
    graph_path = PROJECT_ROOT / "graphify-out" / "graph.json"
    runner.check(graph_path.is_file(), "phase_8_graph_json_exists", f"File missing at {graph_path}")
    if graph_path.is_file():
        try:
            with open(graph_path, "r", encoding="utf-8") as gf:
                gdata = json.load(gf)
            nodes = gdata.get("nodes", [])
            links = gdata.get("links", [])
            runner.check(len(nodes) >= 500, "phase_8_graph_nodes_ge_500", f"Found {len(nodes)} nodes (spec >= 500)")
            runner.check(len(links) >= 1000, "phase_8_graph_links_ge_1000", f"Found {len(links)} edges (spec >= 1000)")
            runner.check("directed" in gdata and gdata["directed"] is False, "phase_8_graph_undirected", f"directed: {gdata.get('directed')}")
            runner.check("multigraph" in gdata and gdata["multigraph"] is False, "phase_8_graph_simple", f"multigraph: {gdata.get('multigraph')}")
        except Exception as e:
            runner.check(False, "phase_8_graph_json_parseable", f"Error: {e}")

    # Deep check graphify-out/GRAPH_REPORT.md
    report_path = PROJECT_ROOT / "graphify-out" / "GRAPH_REPORT.md"
    runner.check(report_path.is_file() and report_path.stat().st_size > 500, "phase_8_graph_report_exists_and_substantial",
                 f"Report size: {report_path.stat().st_size if report_path.is_file() else 'missing'}")

    # Deep check findings/08_SYNTHESIS_AND_GRAPH.md
    dossier_path = PROJECT_ROOT / "findings" / "08_SYNTHESIS_AND_GRAPH.md"
    runner.check(dossier_path.is_file(), "phase_8_dossier_exists", f"Missing at {dossier_path}")
    if dossier_path.is_file():
        d_size = dossier_path.stat().st_size
        runner.check(d_size >= 3500, "phase_8_dossier_size_ge_3500", f"Dossier size: {d_size} bytes (minimum 3500)")
        d_text = dossier_path.read_text(encoding="utf-8")
        # Check Mermaid diagrams
        mermaid_blocks = re.findall(r"```mermaid", d_text)
        runner.check(len(mermaid_blocks) >= 5, "phase_8_dossier_has_5_mermaid_diagrams", f"Found {len(mermaid_blocks)} mermaid blocks (expected >= 5)")
        # Check markdown tables
        table_matches = re.findall(r"\|.+\|.+\|", d_text)
        runner.check(len(table_matches) >= 10, "phase_8_dossier_has_markdown_tables", f"Found {len(table_matches)} table lines")
        # Check for placeholders
        ph_found = [p for p in BANNED_PLACEHOLDER_PATTERNS if re.search(p, d_text, re.IGNORECASE)]
        runner.check(len(ph_found) == 0, "phase_8_dossier_zero_placeholders", f"Found banned: {ph_found}")


def test_execution_all_8_phases(runner: TestRunner):
    print("\n--- Suite 5: Empirical Subprocess Execution across All 8 Phases ---")
    
    for phase_id in EXPECTED_PHASE_IDS:
        cmd = [sys.executable, str(VERIFY_PHASE_SCRIPT), phase_id]
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        
        stdout_clean = proc.stdout.strip()
        stderr_clean = proc.stderr.strip()
        
        has_pass = "[PASS]" in stdout_clean
        exit_code_zero = proc.returncode == 0
        
        runner.check(exit_code_zero and has_pass,
                     f"verify_phase_execution_{phase_id}",
                     f"Exit code: {proc.returncode}, Stdout: {stdout_clean[:200]}, Stderr: {stderr_clean[:200]}")


def test_adversarial_oracle_and_mutation(runner: TestRunner, raw_text: str, data: dict):
    print("\n--- Suite 6: Adversarial Mutation & Negative Test Scenarios ---")
    if not data or not raw_text:
        return

    # 6.1 Negative verification: Non-existent phase ID
    proc_bogus = subprocess.run([sys.executable, str(VERIFY_PHASE_SCRIPT), "phase_99_nonexistent"],
                                cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    runner.check(proc_bogus.returncode != 0, "verify_phase_rejects_bogus_phase", f"Exit code was {proc_bogus.returncode}")

    # 6.2 Negative verification: No arguments
    proc_noargs = subprocess.run([sys.executable, str(VERIFY_PHASE_SCRIPT)],
                                 cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    runner.check(proc_noargs.returncode != 0, "verify_phase_rejects_no_args", f"Exit code was {proc_noargs.returncode}")

    # 6.3 Oracle Mutation: Test that an oracle validator catches illegal mutations
    def oracle_validate_progress(test_dict: dict) -> list:
        errs = []
        if test_dict.get("overall_status") != "completed":
            errs.append("overall_status_not_completed")
        if test_dict.get("active_phase_id") is not None:
            errs.append("active_phase_id_not_none")
        phases = test_dict.get("phases", [])
        if len(phases) != 8:
            errs.append(f"phase_count_{len(phases)}_not_8")
        for p in phases:
            pid = p.get("id")
            if p.get("status") != "completed":
                errs.append(f"{pid}_not_completed")
            if pid == "phase_08_graphify_synthesis":
                if len(p.get("notes", [])) < 4:
                    errs.append("phase_8_notes_lt_4")
                if p.get("verified_by") != "tools/verify_phase.py":
                    errs.append("phase_8_verified_by_mismatch")
                if not p.get("completed_at"):
                    errs.append("phase_8_completed_at_empty")
        return errs

    # Baseline oracle check
    baseline_errs = oracle_validate_progress(data)
    runner.check(len(baseline_errs) == 0, "oracle_baseline_clean", f"Baseline errors: {baseline_errs}")

    # Mutation 1: overall_status = "in_progress"
    mut1 = copy.deepcopy(data)
    mut1["overall_status"] = "in_progress"
    runner.check("overall_status_not_completed" in oracle_validate_progress(mut1),
                 "oracle_catches_mutated_overall_status", "Failed to catch overall_status mutation")

    # Mutation 2: active_phase_id = "phase_08_graphify_synthesis"
    mut2 = copy.deepcopy(data)
    mut2["active_phase_id"] = "phase_08_graphify_synthesis"
    runner.check("active_phase_id_not_none" in oracle_validate_progress(mut2),
                 "oracle_catches_mutated_active_phase_id", "Failed to catch active_phase_id mutation")

    # Mutation 3: Phase 8 notes truncated to 3 items (< 4)
    mut3 = copy.deepcopy(data)
    for p in mut3["phases"]:
        if p["id"] == "phase_08_graphify_synthesis":
            p["notes"] = p["notes"][:3]
    runner.check("phase_8_notes_lt_4" in oracle_validate_progress(mut3),
                 "oracle_catches_phase_8_notes_lt_4", "Failed to catch notes < 4 mutation")

    # Mutation 4: Phase 8 status reverted to "pending"
    mut4 = copy.deepcopy(data)
    for p in mut4["phases"]:
        if p["id"] == "phase_08_graphify_synthesis":
            p["status"] = "pending"
    runner.check("phase_08_graphify_synthesis_not_completed" in oracle_validate_progress(mut4),
                 "oracle_catches_phase_8_pending", "Failed to catch Phase 8 pending mutation")

    # Mutation 5: Phase 8 verified_by set to wrong tool
    mut5 = copy.deepcopy(data)
    for p in mut5["phases"]:
        if p["id"] == "phase_08_graphify_synthesis":
            p["verified_by"] = "manual_check"
    runner.check("phase_8_verified_by_mismatch" in oracle_validate_progress(mut5),
                 "oracle_catches_phase_8_verified_by_mismatch", "Failed to catch verified_by mutation")

    # Mutation 6: Phase 8 completed_at removed
    mut6 = copy.deepcopy(data)
    for p in mut6["phases"]:
        if p["id"] == "phase_08_graphify_synthesis":
            p["completed_at"] = None
    runner.check("phase_8_completed_at_empty" in oracle_validate_progress(mut6),
                 "oracle_catches_phase_8_completed_at_empty", "Failed to catch missing completed_at")


def main():
    print("=" * 60)
    print("CHALLENGER M3-1 ADVERSARIAL TEST HARNESS")
    print("Target: progress.json, verify_phase.py, Phase 8 Completion")
    print("=" * 60)

    runner = TestRunner()

    raw_text, data = test_file_and_utf8(runner)
    if data:
        test_schema_and_metadata(runner, data)
        test_phases_collection(runner, data)
        test_phase_8_deep_inspection(runner, data)
        test_execution_all_8_phases(runner)
        test_adversarial_oracle_and_mutation(runner, raw_text, data)

    success = runner.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
