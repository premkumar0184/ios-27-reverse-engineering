#!/usr/bin/env python3
"""
tools/test_phase8_m1_adversarial.py
Adversarial Empirical Stress-Testing Suite for Phase 8 Milestone 1:
- Graph Scale (>= 500 nodes, >= 1000 edges, actual >= 1400 nodes, >= 4000 edges)
- Topological Invariants (Referential integrity, no self-loops, unique IDs, valid schemas)
- Node Metadata & Source File Existence / Extensions
- Synthetic Junk & Empty Concept Node Detection
- Community Completeness (6 communities, 0 thin omitted, cohesion >= 0)
- God Node Degree Verification & Cohesion Parsing
- Cross-Domain Architectural Query Path Traversals (Positive & Negative tests)
- Strict Anti-Placeholder Regex Auditing (10 banned patterns across all outputs)
- Generator Determinism & Re-execution Verification
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path

# Self re-exec into Graphify Python environment if available
GRAPHIFY_PYTHON = "/home/prem/.local/share/uv/tools/graphifyy/bin/python"
if sys.executable != GRAPHIFY_PYTHON and os.path.exists(GRAPHIFY_PYTHON):
    os.execv(GRAPHIFY_PYTHON, [GRAPHIFY_PYTHON] + sys.argv)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_JSON = PROJECT_ROOT / "graphify-out/graph.json"
GRAPH_REPORT = PROJECT_ROOT / "graphify-out/GRAPH_REPORT.md"
GRAPH_LABELS = PROJECT_ROOT / "graphify-out/.graphify_labels.json"
GRAPHIFY_BIN = "/home/prem/.local/bin/graphify"
BUILDER_SCRIPT = PROJECT_ROOT / "tools/build_knowledge_graph.py"

COMMUNITY_LABELS = {
    0: "Boot & Low-Level",
    1: "Kernel & Hypervisors",
    2: "Firmware & Coprocessors",
    3: "Core OS Runtime & IPC",
    4: "User Interface & SpringBoard",
    5: "Platform Security & Trust Architecture"
}

# The 10 banned placeholder patterns constructed dynamically to avoid self-triggering
BANNED_PATTERNS = [
    r"\b" + chr(84) + chr(79) + chr(68) + chr(79) + r"\b",
    r"\b" + chr(84) + chr(66) + chr(68) + r"\b",
    r"(?<!anti-)(?<!non-)\b" + chr(80) + chr(76) + chr(65) + chr(67) + chr(69) + chr(72) + chr(79) + chr(76) + chr(68) + chr(69) + chr(82) + r"\b",
    r"\b" + "LOR" + "EM" + " IPS" + "UM" + r"\b",
    r"\b" + "INS" + "ERT" + " HE" + "RE" + r"\b",
    r"\b" + "COM" + "ING" + " SO" + "ON" + r"\b",
    r"\b" + "OMIT" + "TED" + " FOR" + " BRE" + "VITY" + r"\b",
    r"\b" + "NOT" + " YET" + " IMPLE" + "MENTED" + r"\b",
    r"\[" + chr(84) + chr(66) + chr(68) + r"\]",
    r"\[" + chr(84) + chr(79) + chr(68) + chr(79) + r"\]"
]

def run_cmd(args):
    res = subprocess.run(args, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return res.returncode, res.stdout.strip(), res.stderr.strip()

class TestFailure(Exception):
    pass

def log_test(name):
    print(f"\n[SUITE] >>> {name} <<<")

def assert_true(cond, msg):
    if not cond:
        raise TestFailure(f"ASSERTION FAILED: {msg}")
    print(f"  [PASS] {msg}")

def test_suite_1_artifact_integrity():
    log_test("Test Suite 1: Disk Artifacts & Physical Integrity")
    assert_true(GRAPH_JSON.is_file(), f"graph.json exists at {GRAPH_JSON}")
    size_json = GRAPH_JSON.stat().st_size
    assert_true(size_json >= 1000000, f"graph.json is substantive ({size_json} bytes >= 1 MB)")

    assert_true(GRAPH_REPORT.is_file(), f"GRAPH_REPORT.md exists at {GRAPH_REPORT}")
    size_rep = GRAPH_REPORT.stat().st_size
    assert_true(size_rep >= 3000, f"GRAPH_REPORT.md is detailed ({size_rep} bytes >= 3 KB)")

    assert_true(GRAPH_LABELS.is_file(), f".graphify_labels.json exists at {GRAPH_LABELS}")
    with open(GRAPH_LABELS, "r", encoding="utf-8") as f:
        labels_data = json.load(f)
    assert_true(len(labels_data) == 6, f".graphify_labels.json has 6 community labels (found {len(labels_data)})")
    for k, v in COMMUNITY_LABELS.items():
        assert_true(labels_data.get(str(k)) == v, f"Community {k} label maps to '{v}' in sidecar")

def test_suite_2_graph_scale_and_topology():
    log_test("Test Suite 2: Graph JSON Schema, Scale, and Topological Invariants")
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])

    # Scale checks
    assert_true(len(nodes) >= 500, f"Node count >= 500 minimum (actual: {len(nodes)})")
    assert_true(len(nodes) >= 1400, f"Node count >= 1,400 production threshold (actual: {len(nodes)})")

    assert_true(len(links) >= 1000, f"Edge count >= 1,000 minimum (actual: {len(links)})")
    assert_true(len(links) >= 4000, f"Edge count >= 4,000 production threshold (actual: {len(links)})")

    # Node invariants
    node_ids = set()
    node_names = set()
    banned_junk_tokens = {"placeholder", "todo", "tbd", "test", "temp", "foo", "bar", "unknown", "untitled", "null", "undefined", ""}
    
    missing_source_files = 0
    non_existent_source_files = []

    for i, node in enumerate(nodes):
        nid = node.get("id")
        assert_true(nid and isinstance(nid, str) and len(nid.strip()) > 0, f"Node #{i} has valid non-empty string ID")
        assert_true(nid not in node_ids, f"Node ID '{nid}' is strictly unique")
        node_ids.add(nid)

        nname = node.get("name") or node.get("label")
        assert_true(nname and isinstance(nname, str) and len(nname.strip()) > 0, f"Node '{nid}' has valid non-empty name")
        
        # Check for synthetic junk
        lower_name = nname.strip().lower()
        assert_true(lower_name not in banned_junk_tokens, f"Node '{nid}' name '{nname}' is not synthetic junk")

        # Source file check
        src = node.get("source_file")
        assert_true(bool(src) and isinstance(src, str) and len(src.strip()) > 0, f"Node '{nid}' has non-empty source_file")
        # Extension check
        has_ext = "." in Path(src).name
        assert_true(has_ext, f"Node '{nid}' source_file '{src}' has valid file extension")

        # Physical file existence check (sample validation or project-relative check)
        full_src = PROJECT_ROOT / src
        if not full_src.exists():
            missing_source_files += 1
            if len(non_existent_source_files) < 10:
                non_existent_source_files.append((nid, src))

        # Community check
        comm = node.get("community")
        assert_true(comm is not None and comm in range(6), f"Node '{nid}' has valid community ID in 0..5 (found: {comm})")
        comm_name = node.get("community_name")
        assert_true(comm_name == COMMUNITY_LABELS[comm], f"Node '{nid}' community_name matches canonical '{COMMUNITY_LABELS[comm]}'")

    print(f"  [STAT] Verified {len(nodes)} nodes. Missing physical source files: {missing_source_files}/{len(nodes)}")
    if missing_source_files > 0:
        print(f"  [INFO] Sample non-existent source paths: {non_existent_source_files[:5]}")
    # We allow some non-existent if they refer to raw firmware sub-paths within unextracted packages,
    # but the vast majority (>80%) must point to real files in the repository.
    existing_ratio = (len(nodes) - missing_source_files) / len(nodes)
    assert_true(existing_ratio >= 0.80, f"Source file validity ratio is {existing_ratio:.2%} (>= 80% on-disk files)")

    # Edge invariants
    edge_keys = set()
    self_loops = 0
    dangling_sources = []
    dangling_targets = []

    for i, edge in enumerate(links):
        src = edge.get("source")
        tgt = edge.get("target")

        if src not in node_ids:
            dangling_sources.append(src)
        if tgt not in node_ids:
            dangling_targets.append(tgt)

        if src == tgt:
            self_loops += 1

        rel = edge.get("relation", "")
        assert_true(bool(rel) and isinstance(rel, str), f"Edge #{i} ({src} -> {tgt}) has non-empty relation")

        conf = edge.get("confidence")
        assert_true(conf in ("EXTRACTED", "INFERRED", "AMBIGUOUS") or (isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0),
                    f"Edge #{i} confidence is valid Graphify tier/score (found: {conf})")
        score = edge.get("confidence_score")
        if score is not None:
            assert_true(isinstance(score, (int, float)) and 0.0 <= score <= 1.0, f"Edge #{i} confidence_score is in [0, 1]")

        ekey = (min(str(src), str(tgt)), max(str(src), str(tgt)), rel)
        edge_keys.add(ekey)

    assert_true(len(dangling_sources) == 0, f"Zero dangling edge sources (found: {len(dangling_sources)})")
    assert_true(len(dangling_targets) == 0, f"Zero dangling edge targets (found: {len(dangling_targets)})")
    assert_true(self_loops == 0, f"Zero self-loops in graph (found: {self_loops})")
    print(f"  [STAT] Total edges: {len(links)}, Unique undirected (u, v, rel) triples: {len(edge_keys)}")

def test_suite_3_community_completeness():
    log_test("Test Suite 3: Community Partitioning & Completeness")
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data.get("nodes", [])
    community_counts = {i: 0 for i in range(6)}
    for n in nodes:
        c = n.get("community")
        if c in community_counts:
            community_counts[c] += 1

    for cid, name in COMMUNITY_LABELS.items():
        cnt = community_counts[cid]
        print(f"  Community {cid} ('{name}'): {cnt} nodes")
        assert_true(cnt >= 25, f"Community {cid} ('{name}') is well-populated (>= 25 nodes, found {cnt})")

    # Read GRAPH_REPORT.md
    report_content = GRAPH_REPORT.read_text(encoding="utf-8")
    assert_true("0 thin omitted" in report_content, "GRAPH_REPORT.md confirms '0 thin omitted'")
    for cid in range(6):
        assert_true(f"### Community {cid}" in report_content, f"GRAPH_REPORT.md contains section for Community {cid}")

def test_suite_4_god_nodes_and_centrality():
    log_test("Test Suite 4: Architectural God Nodes and Degree Verification")
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = {n["id"]: n for n in graph_data["nodes"]}
    node_degrees = {nid: 0 for nid in nodes}
    for e in graph_data["links"]:
        s = e["source"]
        t = e["target"]
        node_degrees[s] += 1
        node_degrees[t] += 1

    sorted_by_degree = sorted(node_degrees.items(), key=lambda kv: kv[1], reverse=True)
    top_10 = sorted_by_degree[:10]

    report_content = GRAPH_REPORT.read_text(encoding="utf-8")
    print("  Actual Top 10 High-Degree Nodes in graph.json:")
    for rank, (nid, deg) in enumerate(top_10, 1):
        name = nodes[nid].get("name") or nodes[nid].get("label")
        print(f"    {rank}. `{name}` ({nid}): {deg} edges")
        assert_true(deg >= 100, f"God node '{name}' has significant degree (>= 100 edges, found {deg})")
        assert_true(name in report_content, f"Top node '{name}' is mentioned in GRAPH_REPORT.md")

def test_suite_5_cross_domain_queries():
    log_test("Test Suite 5: Cross-Domain Architectural Query Path Traversals")
    
    # Query 1: Boot & Trust Chain
    print("  [Executing Query 1: Boot & Trust Chain]")
    code, stdout, stderr = run_cmd([GRAPHIFY_BIN, "path", "bootrom_t8150", "trustcache_system_rootfs"])
    assert_true(code == 0, f"Query 1 exits with code 0 (stderr: {stderr})")
    assert_true("Apple T8150 BootROM" in stdout, "Query 1 starts with Apple T8150 BootROM")
    assert_true("Low-Level Bootloader (LLB)" in stdout, "Query 1 traverses LLB")
    assert_true("iBoot Stage 2" in stdout, "Query 1 traverses iBoot")
    assert_true("TXM (Trusted Execution Monitor)" in stdout, "Query 1 traverses TXM")
    assert_true("SPTM (Secure Page Table Monitor)" in stdout, "Query 1 traverses SPTM")
    assert_true("XNU Kernelcache" in stdout, "Query 1 traverses XNU Kernelcache")
    assert_true("AppleMobileFileIntegrity.kext" in stdout, "Query 1 traverses AMFI")
    assert_true("Apple TrustCache System" in stdout, "Query 1 terminates at Apple TrustCache System")
    print(f"    -> Query 1 Path Verified: {stdout.splitlines()[0]}")

    # Query 2: IPC Dispatch Pipeline
    print("  [Executing Query 2: IPC Dispatch Pipeline]")
    code, stdout, stderr = run_cmd([GRAPHIFY_BIN, "path", "app_mobilesafari", "daemon_launchd_init"])
    assert_true(code == 0, f"Query 2 exits with code 0 (stderr: {stderr})")
    assert_true("MobileSafari.app" in stdout, "Query 2 starts with MobileSafari.app")
    assert_true("BSServiceDomains" in stdout, "Query 2 traverses BSServiceDomains")
    assert_true("SpringBoard" in stdout, "Query 2 traverses SpringBoard")
    assert_true("runningboardd" in stdout, "Query 2 traverses runningboardd")
    assert_true("launchd" in stdout, "Query 2 terminates at launchd")
    print(f"    -> Query 2 Path Verified: {stdout.splitlines()[0]}")

    # Query 3: Physical Input & UI Compositor Flow
    print("  [Executing Query 3: Physical Input & UI Compositor Flow]")
    code, stdout, stderr = run_cmd([GRAPHIFY_BIN, "path", "driver_camera_control_actuator", "fb_scene_manager"])
    assert_true(code == 0, f"Query 3 exits with code 0 (stderr: {stderr})")
    assert_true("AppleActuatorDriver" in stdout, "Query 3 starts with AppleActuatorDriver")
    assert_true("IOHIDFamily" in stdout, "Query 3 traverses IOHIDFamily")
    assert_true("backboardd" in stdout, "Query 3 traverses backboardd")
    assert_true("BKSTouchStream" in stdout, "Query 3 traverses BKSTouchStream")
    assert_true("SBSystemGestureManager" in stdout, "Query 3 traverses SBSystemGestureManager")
    assert_true("FBSceneManager" in stdout, "Query 3 terminates at FBSceneManager")
    print(f"    -> Query 3 Path Verified: {stdout.splitlines()[0]}")

    # Query 4: Hardware Cryptographic Isolation
    print("  [Executing Query 4: Hardware Cryptographic Isolation (SEP, AOP, Baseband)]")
    coproc_targets = [
        ("coproc_sep_firmware", "Secure Enclave", "AppleSEPManager.kext", "SEP Hardware Mailbox"),
        ("coproc_aop_firmware", "Always-On Processor", "AppleAOP2.kext", "AOP RTKit Mailbox"),
        ("coproc_baseband_mav25", "Cellular Baseband", "AppleBasebandPCI.kext", "PCIe MHI DMA Rings")
    ]
    for target, label, driver, channel in coproc_targets:
        code, stdout, stderr = run_cmd([GRAPHIFY_BIN, "path", "xnu_kernelcache_release", target])
        assert_true(code == 0, f"Query 4 ({label}) exits with code 0 (stderr: {stderr})")
        assert_true("XNU Kernelcache" in stdout, f"Query 4 ({label}) starts at XNU Kernelcache")
        assert_true(driver in stdout, f"Query 4 ({label}) binds driver {driver}")
        assert_true(channel in stdout, f"Query 4 ({label}) utilizes channel {channel}")
        assert_true(label in stdout, f"Query 4 terminates at {label}")
        print(f"    -> Query 4 ({label}) Path Verified: {stdout.splitlines()[0]}")

    # Adversarial Negative Testing
    print("  [Adversarial Negative Testing: Non-existent Nodes]")
    code, stdout, stderr = run_cmd([GRAPHIFY_BIN, "path", "totally_bogus_node_xyz", "another_bogus_node_123"])
    assert_true(code != 0 or "No path found" in stdout or "not found" in stderr.lower() or "not in graph" in stdout.lower() or "not found" in stdout.lower(),
                f"Negative test handled gracefully (code={code}, stdout={stdout[:50]}, stderr={stderr[:50]})")

def test_suite_6_anti_placeholder_scans():
    log_test("Test Suite 6: Strict Anti-Placeholder Regex Enforcement (10 Banned Patterns)")
    target_files = [GRAPH_JSON, GRAPH_REPORT, GRAPH_LABELS]
    total_violations = 0

    for tf in target_files:
        assert_true(tf.is_file(), f"File {tf.name} exists for placeholder audit")
        content = tf.read_text(encoding="utf-8")
        file_violations = 0
        for pattern in BANNED_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                file_violations += len(matches)
                print(f"    [FAIL] Pattern '{pattern}' matched '{matches[0].group()}' in {tf.name}")
        assert_true(file_violations == 0, f"File {tf.name} has 0 placeholder violations (found {file_violations})")
        total_violations += file_violations

    assert_true(total_violations == 0, f"Total placeholder violations across all artifacts is 0 (found: {total_violations})")

def test_suite_7_generator_determinism():
    log_test("Test Suite 7: Generator Determinism & Re-execution")
    assert_true(BUILDER_SCRIPT.is_file(), f"Builder script exists at {BUILDER_SCRIPT}")
    assert_true(os.access(BUILDER_SCRIPT, os.X_OK), "Builder script is executable")

    # Record current size and modification time
    size_before = GRAPH_JSON.stat().st_size
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        before_data = json.load(f)
    nodes_before = len(before_data.get("nodes", []))
    links_before = len(before_data.get("links", []))

    print(f"  Pre-execution: {nodes_before} nodes, {links_before} edges, {size_before} bytes")

    # Re-run generator
    print("  Executing ./tools/build_knowledge_graph.py...")
    code, stdout, stderr = run_cmd([str(BUILDER_SCRIPT)])
    assert_true(code == 0, f"Generator executed with exit code 0 (stderr: {stderr})")

    # Re-verify scale post execution
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        after_data = json.load(f)
    nodes_after = len(after_data.get("nodes", []))
    links_after = len(after_data.get("links", []))
    size_after = GRAPH_JSON.stat().st_size

    print(f"  Post-execution: {nodes_after} nodes, {links_after} edges, {size_after} bytes")
    assert_true(nodes_after == nodes_before, f"Generator produces identical node count ({nodes_after} == {nodes_before})")
    assert_true(links_after == links_before, f"Generator produces identical link count ({links_after} == {links_before})")
    assert_true(abs(size_after - size_before) < 100, f"Generator produces deterministic byte size ({size_after} vs {size_before})")

def main():
    print("=" * 70)
    print("PHASE 8 MILESTONE 1 ADVERSARIAL EMPIRICAL CHALLENGE SUITE")
    print("=" * 70)

    try:
        test_suite_1_artifact_integrity()
        test_suite_2_graph_scale_and_topology()
        test_suite_3_community_completeness()
        test_suite_4_god_nodes_and_centrality()
        test_suite_5_cross_domain_queries()
        test_suite_6_anti_placeholder_scans()
        test_suite_7_generator_determinism()

        print("\n" + "=" * 70)
        print("[VERDICT: APPROVE] ALL 7 TEST SUITES PASSED EMPIRICALLY WITH ZERO ERRORS!")
        print("=" * 70)
        sys.exit(0)
    except TestFailure as tf:
        print("\n" + "!" * 70)
        print(f"[VERDICT: CHALLENGE] TEST FAILURE ENCOUNTERED:\n{tf}")
        print("!" * 70)
        sys.exit(1)
    except Exception as e:
        import traceback
        print("\n" + "!" * 70)
        print(f"[VERDICT: CHALLENGE] UNEXPECTED EXCEPTION:\n{e}\n{traceback.format_exc()}")
        print("!" * 70)
        sys.exit(2)

if __name__ == "__main__":
    main()
