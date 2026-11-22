#!/usr/bin/env python3
"""
tools/test_phase8_m2_adversarial.py
Adversarial Empirical Stress-Testing Suite for Phase 8 Milestone 2:
Master Architectural Synthesis Dossier (findings/08_SYNTHESIS_AND_GRAPH.md).

Author: Challenger M2-1 (Adversarial Dossier Challenger)
Target: findings/08_SYNTHESIS_AND_GRAPH.md

Validation Dimensions:
1. Physical Integrity, Size Thresholds (>= 3,500 bytes and >= 40,000 bytes), & UTF-8 Invariants
2. Structural Richness, Heading Hierarchies, & Markdown Table Delimiter Consistency
3. Comprehensive Mermaid AST, Bracket Balance, Subgraph Parity, & Transition Syntax (5 diagrams)
4. Empirical Coverage of all 8 Privilege Rings & Hardware Monitor Domains
5. Live Cross-Domain Graph Query Path Traversals (7-hop, 5-hop, 5-hop, 3-hop) & Adversarial Negatives
6. Strict Anti-Placeholder Regex Scanning (10 Banned Patterns + Adversarial Stubs)
7. Mechanical Phase Verification Execution (tools/verify_phase.py phase_08_graphify_synthesis)
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOSSIER_PATH = PROJECT_ROOT / "findings/08_SYNTHESIS_AND_GRAPH.md"
GRAPHIFY_BIN = "/home/prem/.local/bin/graphify"
GRAPH_JSON = PROJECT_ROOT / "graphify-out/graph.json"

# The 10 banned placeholder patterns dynamically assembled to avoid self-matching
BANNED_PATTERNS = [
    r"\b" + chr(84) + chr(79) + chr(68) + chr(79) + r"\b",
    r"\b" + chr(84) + chr(66) + chr(68) + r"\b",
    r"(?<!anti-)(?<!non-)\b" + chr(80) + chr(76) + chr(65) + chr(67) + chr(69) + chr(72) + chr(79) + chr(76) + chr(68) + chr(69) + chr(72) + r"\b",
    r"\b" + "LOR" + "EM" + " IPS" + "UM" + r"\b",
    r"\b" + "INS" + "ERT" + " HE" + "RE" + r"\b",
    r"\b" + "COM" + "ING" + " SO" + "ON" + r"\b",
    r"\b" + "OMIT" + "TED" + " FOR" + " BRE" + "VITY" + r"\b",
    r"\b" + "NOT" + " YET" + " IMPLE" + "MENTED" + r"\b",
    r"\[" + chr(84) + chr(66) + chr(68) + r"\]",
    r"\[" + chr(84) + chr(79) + chr(68) + chr(79) + r"\]"
]

ADVERSARIAL_STUB_PATTERNS = [
    r"\b" + chr(70) + chr(73) + chr(88) + chr(77) + chr(69) + r"\b", # FIXME
    r"\b" + chr(88) + chr(88) + chr(88) + r"\b",                     # XXX
    r"\b" + "REPLACE" + "_ME" + r"\b",
    r"\b" + "FILL" + "ME" + r"\b",
    r"\b" + "STUB" + "_ONLY" + r"\b"
]

class TestFailure(Exception):
    pass

def log_suite(title):
    print(f"\n[SUITE] >>> {title} <<<")

def assert_true(condition, message):
    if not condition:
        raise TestFailure(f"ASSERTION FAILED: {message}")
    print(f"  [PASS] {message}")

def run_cmd(args):
    res = subprocess.run(args, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return res.returncode, res.stdout.strip(), res.stderr.strip()

# ==============================================================================
# SUITE 1: Size, Encoding, Physical Byte Invariants
# ==============================================================================
def test_suite_1_size_and_encoding():
    log_suite("Suite 1: Physical File Integrity, Byte Size Thresholds, & Encoding")
    assert_true(DOSSIER_PATH.is_file(), f"Dossier exists at {DOSSIER_PATH}")
    
    stat = DOSSIER_PATH.stat()
    size = stat.st_size
    print(f"  [INFO] File byte size: {size:,} bytes")
    
    # Assert size bounds
    assert_true(size >= 3500, f"Byte size >= 3,500 minimum mandate (found {size} bytes)")
    assert_true(size >= 40000, f"Byte size >= 40,000 adversarial threshold (found {size} bytes)")
    assert_true(size <= 150000, f"Byte size <= 150,000 anti-bloat bound (found {size} bytes)")
    
    # Read raw bytes to verify encoding invariants
    raw_bytes = DOSSIER_PATH.read_bytes()
    assert_true(not raw_bytes.startswith(b"\xef\xbb\xbf"), "File does not contain UTF-8 BOM")
    assert_true(b"\x00" not in raw_bytes, "File contains zero null bytes (no binary corruption)")
    
    # Verify strict UTF-8 decode without errors
    try:
        content = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as ude:
        raise TestFailure(f"Strict UTF-8 decode failed: {ude}")
    assert_true("\ufffd" not in content, "Decoded text contains zero unicode replacement characters")
    
    # Line count check
    lines = content.splitlines()
    print(f"  [INFO] Total line count: {len(lines)}")
    assert_true(len(lines) >= 450, f"Dossier has >= 450 lines (found {len(lines)})")

# ==============================================================================
# SUITE 2: Structural Richness & Markdown Table Invariants
# ==============================================================================
def test_suite_2_structure_and_tables():
    log_suite("Suite 2: Markdown AST Structure, Headings, & Table Delimiter Consistency")
    content = DOSSIER_PATH.read_text(encoding="utf-8")
    
    # 1. Heading verification
    h1_matches = re.findall(r"^#\s+(.+)$", content, re.MULTILINE)
    assert_true(len(h1_matches) == 1, f"Exactly 1 H1 document title (found {len(h1_matches)})")
    
    h2_matches = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    print(f"  [INFO] H2 sections found: {len(h2_matches)}")
    assert_true(len(h2_matches) >= 7, f"At least 7 major H2 sections (found {len(h2_matches)})")
    
    h3_matches = re.findall(r"^###\s+(.+)$", content, re.MULTILINE)
    print(f"  [INFO] H3 sub-sections found: {len(h3_matches)}")
    assert_true(len(h3_matches) >= 15, f"At least 15 technical H3 sub-sections (found {len(h3_matches)})")
    
    # Check for invalid heading formatting (e.g., '##Heading' missing space)
    invalid_headers = re.findall(r"^#{1,6}[^#\s]", content, re.MULTILINE)
    assert_true(len(invalid_headers) == 0, f"Zero malformed headers missing space (found {len(invalid_headers)})")

    # 2. Markdown tables validation (ignoring ASCII art inside code blocks)
    lines = content.splitlines()
    table_blocks = []
    current_table = []
    in_table = False
    in_code = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if not in_code and stripped.startswith("|") and stripped.endswith("|"):
            current_table.append(stripped)
            in_table = True
        else:
            if in_table and len(current_table) > 0:
                table_blocks.append(current_table)
                current_table = []
            in_table = False
    if in_table and len(current_table) > 0:
        table_blocks.append(current_table)

    print(f"  [INFO] Markdown tables detected: {len(table_blocks)}")
    assert_true(len(table_blocks) >= 8, f"At least 8 markdown tables present (found {len(table_blocks)})")

    total_table_rows = 0
    for t_idx, table in enumerate(table_blocks, 1):
        assert_true(len(table) >= 3, f"Table #{t_idx} has header, separator, and at least 1 data row (found {len(table)} lines)")
        header_cols = [c.strip() for c in table[0].strip("|").split("|")]
        col_count = len(header_cols)
        assert_true(col_count >= 2, f"Table #{t_idx} has at least 2 columns (found {col_count})")
        
        # Check delimiter row
        delim_cols = [c.strip() for c in table[1].strip("|").split("|")]
        assert_true(len(delim_cols) == col_count, f"Table #{t_idx} delimiter column count matches header ({len(delim_cols)} == {col_count})")
        for dc in delim_cols:
            assert_true(bool(re.match(r"^:?-+:?$", dc)), f"Table #{t_idx} delimiter cell '{dc}' is valid markdown separator")
            
        # Check all data rows
        for r_idx, row_str in enumerate(table[2:], 3):
            total_table_rows += 1
            row_cols = [c.strip() for c in row_str.strip("|").split("|")]
            assert_true(len(row_cols) == col_count,
                        f"Table #{t_idx} row #{r_idx} column count matches header ({len(row_cols)} == {col_count})")
            # Ensure cells are not empty
            for c_idx, cell in enumerate(row_cols):
                assert_true(len(cell) > 0, f"Table #{t_idx} row #{r_idx} col #{c_idx} is non-empty")

    print(f"  [INFO] Total validated table data rows: {total_table_rows}")
    assert_true(total_table_rows >= 50, f"At least 50 total table data rows (found {total_table_rows})")

    # 3. Code fence parity
    delimiter_count = content.count("```")
    assert_true(delimiter_count % 2 == 0, f"Code delimiters (```) are strictly balanced ({delimiter_count} is even)")
    print(f"  [INFO] Code blocks found: {delimiter_count // 2} (delimiters: {delimiter_count})")
    assert_true(delimiter_count // 2 >= 10, f"At least 10 code blocks present (found {delimiter_count // 2})")

# ==============================================================================
# SUITE 3: Comprehensive Mermaid AST & Syntax Stress Testing
# ==============================================================================
def test_suite_3_mermaid_diagrams():
    log_suite("Suite 3: Comprehensive Mermaid AST, Bracket Balance, & Transition Syntax")
    content = DOSSIER_PATH.read_text(encoding="utf-8")
    
    mermaid_blocks = re.findall(r"```mermaid\n([\s\S]*?)\n```", content)
    print(f"  [INFO] Mermaid diagrams extracted: {len(mermaid_blocks)}")
    assert_true(len(mermaid_blocks) == 5, f"Exactly 5 Mermaid diagrams authored (found {len(mermaid_blocks)})")

    expected_diagram_types = [
        ("flowchart TD", "Diagram 1: Boot Sequence & EL Translation"),
        ("flowchart LR", "Diagram 2: Dual Kernelcache & KEXT Topology"),
        ("flowchart BT", "Diagram 3: Window Level Compositor Hierarchy"),
        ("stateDiagram-v2", "Diagram 4: Dynamic Island Presentation States"),
        ("flowchart TD", "Diagram 5: Coprocessor Interconnect Bus Topology")
    ]

    for d_idx, (block, (expected_type, desc)) in enumerate(zip(mermaid_blocks, expected_diagram_types), 1):
        print(f"\n  [ANALYSIS] Validating {desc} (Diagram #{d_idx})...")
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        assert_true(len(lines) >= 10, f"Diagram #{d_idx} has substantive definition (>= 10 lines, found {len(lines)})")
        
        # Check directive
        first_line = lines[0]
        assert_true(first_line == expected_type, f"Diagram #{d_idx} starts with '{expected_type}' (found '{first_line}')")
        
        # Lexical bracket balance check
        paren_stack = 0
        bracket_stack = 0
        brace_stack = 0
        quote_count = 0
        
        for l_num, line in enumerate(lines, 1):
            for ch in line:
                if ch == '(':
                    paren_stack += 1
                elif ch == ')':
                    paren_stack -= 1
                    assert_true(paren_stack >= 0, f"Diagram #{d_idx} line {l_num} has unexpected closing parenthesis ')'")
                elif ch == '[':
                    bracket_stack += 1
                elif ch == ']':
                    bracket_stack -= 1
                    assert_true(bracket_stack >= 0, f"Diagram #{d_idx} line {l_num} has unexpected closing bracket ']'")
                elif ch == '{':
                    brace_stack += 1
                elif ch == '}':
                    brace_stack -= 1
                    assert_true(brace_stack >= 0, f"Diagram #{d_idx} line {l_num} has unexpected closing brace '}}'")
                elif ch == '"':
                    quote_count += 1

        assert_true(paren_stack == 0, f"Diagram #{d_idx} parentheses balanced (net: {paren_stack})")
        assert_true(bracket_stack == 0, f"Diagram #{d_idx} square brackets balanced (net: {bracket_stack})")
        assert_true(brace_stack == 0, f"Diagram #{d_idx} curly braces balanced (net: {brace_stack})")
        assert_true(quote_count % 2 == 0, f"Diagram #{d_idx} double quotes balanced ({quote_count} even)")

        # Subgraph balance check for flowcharts
        if "flowchart" in first_line:
            subgraph_starts = len(re.findall(r"^\s*subgraph\s+", block, re.MULTILINE))
            subgraph_ends = len(re.findall(r"^\s*end\s*$", block, re.MULTILINE))
            assert_true(subgraph_starts >= 2, f"Diagram #{d_idx} contains modular subgraphs (found {subgraph_starts})")
            assert_true(subgraph_starts == subgraph_ends,
                        f"Diagram #{d_idx} subgraphs balanced (starts: {subgraph_starts}, ends: {subgraph_ends})")

            # Check for dangling arrow syntax
            for l_num, line in enumerate(lines, 1):
                if line.startswith("subgraph") or line == "end" or line == first_line or line.startswith("%%"):
                    continue
                # If line contains arrow, check it doesn't end with arrow or pipe
                if "-->" in line:
                    stripped_arrow = line.rstrip()
                    assert_true(not stripped_arrow.endswith("-->"), f"Diagram #{d_idx} line {l_num} has dangling arrow: '{line}'")
                    assert_true(not stripped_arrow.endswith("|"), f"Diagram #{d_idx} line {l_num} has unterminated edge label: '{line}'")

        # Specific diagram checks
        if d_idx == 1:
            assert_true("BootROM" in block and "SPTM" in block and "TXM" in block and "XNU" in block,
                        "Diagram 1 explicitly connects BootROM, SPTM, TXM, and XNU")
            assert_true("VTTBR_EL2" in block, "Diagram 1 references VTTBR_EL2 Stage-2 ownership")
        elif d_idx == 2:
            assert_true("KC_REL" in block and "KC_RES" in block, "Diagram 2 maps release and research kernelcaches")
            assert_true("08 00 80 52" in block and "28 00 80 52" in block, "Diagram 2 depicts exact 1-byte opcode research gate")
        elif d_idx == 3:
            assert_true("SBHomeScreenWindow" in block and "SBAppResizingShieldWindow" in block,
                        "Diagram 3 covers full spectrum from Level 0.0 to 11000.0")
            assert_true("Level: 0.0" in block and "Level: 11000.0" in block, "Diagram 3 displays exact float levels")
        elif d_idx == 4:
            assert_true("[*] --> STATE_SA_NONE" in block, "Diagram 4 initializes from [*]")
            assert_true("STATE_SA_COMPACT_DUAL" in block and "STATE_SA_EXPANDED_HUD" in block,
                        "Diagram 4 covers Dynamic Island presentation states")
        elif d_idx == 5:
            assert_true("HOST_AP" in block and "BB_MODEM" in block and "SEP_PROC" in block and "AOP_PROC" in block,
                        "Diagram 5 connects Host AP to Baseband, SEP, and AOP")
            assert_true("PCIe Gen3/4 MHI DMA" in block, "Diagram 5 labels PCIe MHI transport")

# ==============================================================================
# SUITE 4: 8 Privilege Rings & Hardware Monitors Verification
# ==============================================================================
def test_suite_4_privilege_rings():
    log_suite("Suite 4: All 8 Privilege Rings & Hardware Monitor Domains Empirical Coverage")
    content = DOSSIER_PATH.read_text(encoding="utf-8")
    
    rings_spec = [
        (1, "Ring 1: EL3 Secure Monitor", ["TXM", "0xfffffff017004000", "0xfffffff017084000", "1eb0eb97-f667-3470-97b9-1cd95d26246f", "braaz x0"]),
        (2, "Ring 2: GL2 / EL2 Hypervisor Monitor", ["SPTM", "0xfffffff027004000", "0xfffffff0270bc388", "6fb95ed6-be8a-39cf-862b-250ba7efd5a5", "VTTBR_EL2", "42 unique Function IDs", "59 distinct frame types"]),
        (3, "Ring 3: Enclave Microkernel Domain", ["ExclaveCore", "DNUB", "00_tightbeam_runtime.macho", "01_pmm_server.macho", "02_vascore_platform.macho", "03_jg_sharedmem_preload.macho"]),
        (4, "Ring 4: EL1 Supervisor", ["XNU Kernel", "0xfffffe0007004000", "302 sub-binaries", "0xfffffe0009297454", "08 00 80 52", "28 00 80 52", "18,224 bytecode rules"]),
        (5, "Ring 5: EL0 Userspace", ["launchd", "0x100018574", "Category 2", "690 launch daemon", "2,414 unique Mach services", "dyld 4", "__TPRO_CONST", "SpringBoard.framework", "0x226a11000", "19-tier"]),
        (6, "Ring 6: Coprocessor Domain A", ["Always-On Processor", "aopfw-v57aop", "aop2fw-v57aop2", "RTKitOS", "0x00000000", "EP 0x01", "EP 0x08", "EP 0x09", "EP 0x12", "EP 0x24", "EP 0x35", "EP 0x53"]),
        (7, "Ring 7: Coprocessor Domain B", ["Secure Enclave Processor", "sep-firmware.v57.RELEASE.im4p", "UID0", "GID0", "SEP_BOOT_ROM", "SEP_PRIVATE_SRAM", "SEP_DRAM_TZ0", "SEP_SHARED_MAILBOX"]),
        (8, "Ring 8: Coprocessor Domain C", ["Qualcomm Snapdragon X75", "Mav25-2.20.04.Release.bbfw", "27 partitions", "qdsp6sw.mbn", "Hexagon QDSP6 v73", "bbcfg.mbn", "MHI DMA", "MSI-X", "Stewie"])
    ]

    for ring_num, ring_title, required_tokens in rings_spec:
        print(f"\n  [ANALYSIS] Validating {ring_title}...")
        assert_true(ring_title in content, f"Section '{ring_title}' is present in dossier")
        for token in required_tokens:
            assert_true(token in content, f"{ring_title} contains verified token: '{token}'")

# ==============================================================================
# SUITE 5: Cross-Domain Queries & Live Graphify Path Verification
# ==============================================================================
def test_suite_5_query_traversals():
    log_suite("Suite 5: Cross-Domain Query Navigation & Live Graph Traversals")
    content = DOSSIER_PATH.read_text(encoding="utf-8")
    
    # 1. Document description checks
    assert_true("5.1 Query 1: Boot & Trust Chain Traversal" in content, "Query 1 section present")
    assert_true("5.2 Query 2: IPC Dispatch Pipeline Traversal" in content, "Query 2 section present")
    assert_true("5.3 Query 3: Physical Input & UI Compositor Flow Traversal" in content, "Query 3 section present")
    assert_true("5.4 Query 4: Hardware Cryptographic Isolation Traversal" in content, "Query 4 section present")

    # 2. Live graph traversal execution using /home/prem/.local/bin/graphify path
    print("\n  [LIVE GRAPH QUERY 1: Boot & Trust Chain]")
    code, out, err = run_cmd([GRAPHIFY_BIN, "path", "bootrom_t8150", "trustcache_system_rootfs"])
    assert_true(code == 0, f"Query 1 exits cleanly (exit code 0, stderr: '{err}')")
    q1_expected_nodes = [
        "Apple T8150 BootROM",
        "Low-Level Bootloader (LLB)",
        "iBoot Stage 2",
        "TXM (Trusted Execution Monitor)",
        "SPTM (Secure Page Table Monitor)",
        "XNU Kernelcache",
        "AppleMobileFileIntegrity.kext",
        "Apple TrustCache System"
    ]
    for n in q1_expected_nodes:
        assert_true(n in out, f"Query 1 live output includes '{n}'")
    print(f"    -> Query 1 Shortest Path: {out.splitlines()[0]}")

    print("\n  [LIVE GRAPH QUERY 2: IPC Dispatch Pipeline]")
    code, out, err = run_cmd([GRAPHIFY_BIN, "path", "app_mobilesafari", "daemon_launchd_init"])
    assert_true(code == 0, f"Query 2 exits cleanly (exit code 0, stderr: '{err}')")
    q2_expected_nodes = [
        "MobileSafari.app",
        "BSServiceDomains",
        "SpringBoard",
        "runningboardd",
        "launchd"
    ]
    for n in q2_expected_nodes:
        assert_true(n in out, f"Query 2 live output includes '{n}'")
    print(f"    -> Query 2 Shortest Path: {out.splitlines()[0]}")

    print("\n  [LIVE GRAPH QUERY 3: Physical Input & UI Compositor Flow]")
    code, out, err = run_cmd([GRAPHIFY_BIN, "path", "driver_camera_control_actuator", "fb_scene_manager"])
    assert_true(code == 0, f"Query 3 exits cleanly (exit code 0, stderr: '{err}')")
    q3_expected_nodes = [
        "AppleActuatorDriver",
        "IOHIDFamily",
        "backboardd",
        "BKSTouchStream",
        "SBSystemGestureManager",
        "FBSceneManager"
    ]
    for n in q3_expected_nodes:
        assert_true(n in out, f"Query 3 live output includes '{n}'")
    print(f"    -> Query 3 Shortest Path: {out.splitlines()[0]}")

    print("\n  [LIVE GRAPH QUERY 4: Hardware Cryptographic Isolation Channels]")
    q4_targets = [
        ("coproc_sep_firmware", "Secure Enclave (SEP Firmware)", "AppleSEPManager.kext"),
        ("coproc_aop_firmware", "Always-On Processor (AOP2 RTKitOS)", "AppleAOP2.kext"),
        ("coproc_baseband_mav25", "Cellular Baseband (Mav25 Snapdragon X75)", "AppleBasebandPCI.kext")
    ]
    for target_id, label, kext in q4_targets:
        code, out, err = run_cmd([GRAPHIFY_BIN, "path", "xnu_kernelcache_release", target_id])
        assert_true(code == 0, f"Query 4 ({label}) exits cleanly with code 0")
        assert_true("XNU Kernelcache" in out, f"Query 4 ({label}) starts at XNU Kernelcache")
        assert_true(kext in out, f"Query 4 ({label}) binds driver '{kext}'")
        assert_true(label in out, f"Query 4 ({label}) terminates at '{label}'")
        print(f"    -> Query 4 ({label}) Shortest Path: {out.splitlines()[0]}")

    # 3. Adversarial Negative Query Tests
    print("\n  [ADVERSARIAL NEGATIVE TESTING: Non-Existent Nodes & Disconnected Paths]")
    # Negative test 1: Non-existent node (pure gibberish, no fuzzy match)
    code, out, err = run_cmd([GRAPHIFY_BIN, "path", "xyz999qwe_completely_unmatched_12345", "zzzyyyxxx_completely_unmatched_67890"])
    combined = (out + " " + err).lower()
    assert_true(code == 4 and "no node matching" in combined,
                f"Gibberish node correctly rejected with code 4 ('{out}')")

    # Negative test 2: Disconnected components (no directed path)
    code, out, err = run_cmd([GRAPHIFY_BIN, "path", "daemon_com_apple_analyticsd", "tools_analyze_app_ecosystem_main"])
    combined = (out + " " + err).lower()
    assert_true("no directed path found" in combined,
                f"Disconnected path correctly reports 'No directed path found' ('{out}')")

# ==============================================================================
# SUITE 6: Strict Anti-Placeholder Regex Scanning
# ==============================================================================
def test_suite_6_anti_placeholder():
    log_suite("Suite 6: Strict Anti-Placeholder Regex Enforcement (10 Banned + Adversarial Stubs)")
    content = DOSSIER_PATH.read_text(encoding="utf-8")
    
    violations = []
    
    # Check 10 standard banned patterns
    for pattern in BANNED_PATTERNS:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            for m in matches:
                violations.append((pattern, m.group(), m.start()))

    # Check adversarial stubs
    for pattern in ADVERSARIAL_STUB_PATTERNS:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            for m in matches:
                violations.append((pattern, m.group(), m.start()))

    if violations:
        print(f"  [FAIL] Detected {len(violations)} placeholder violations:")
        for pat, matched_text, offset in violations:
            print(f"    - Pattern '{pat}' matched '{matched_text}' at character offset {offset}")
        raise TestFailure(f"Total placeholder violations: {len(violations)}")
    
    assert_true(len(violations) == 0, "Zero banned placeholder patterns or adversarial stubs detected across dossier")

# ==============================================================================
# SUITE 7: Phase Verification Script Execution & Exit Code 0
# ==============================================================================
def test_suite_7_mechanical_verification():
    log_suite("Suite 7: Phase Verification Script (tools/verify_phase.py)")
    verify_script = PROJECT_ROOT / "tools/verify_phase.py"
    assert_true(verify_script.is_file(), f"verify_phase.py exists at {verify_script}")
    
    code, stdout, stderr = run_cmd([sys.executable, str(verify_script), "phase_08_graphify_synthesis"])
    print(f"  [OUTPUT]\n{stdout}")
    if stderr:
        print(f"  [STDERR]\n{stderr}")
        
    assert_true(code == 0, f"tools/verify_phase.py exited with code 0 (actual: {code})")
    assert_true("[PASS] All verification checks PASSED" in stdout, "verify_phase.py reports [PASS]")

# ==============================================================================
# MAIN TEST DISPATCHER
# ==============================================================================
def main():
    print("=" * 80)
    print("PHASE 8 MILESTONE 2: ADVERSARIAL EMPIRICAL STRESS TEST SUITE")
    print(f"Target Artifact: {DOSSIER_PATH}")
    print("=" * 80)

    try:
        test_suite_1_size_and_encoding()
        test_suite_2_structure_and_tables()
        test_suite_3_mermaid_diagrams()
        test_suite_4_privilege_rings()
        test_suite_5_query_traversals()
        test_suite_6_anti_placeholder()
        test_suite_7_mechanical_verification()

        print("\n" + "=" * 80)
        print("[VERDICT: APPROVE] ALL 7 ADVERSARIAL TEST SUITES PASSED EMPIRICALLY WITH ZERO DEFECTS!")
        print("=" * 80)
        sys.exit(0)
    except TestFailure as tf:
        print("\n" + "!" * 80)
        print(f"[VERDICT: CHALLENGE] ADVERSARIAL CHALLENGE TRIGGERED:\n{tf}")
        print("!" * 80)
        sys.exit(1)
    except Exception as e:
        import traceback
        print("\n" + "!" * 80)
        print(f"[VERDICT: CHALLENGE] UNEXPECTED EXCEPTION:\n{e}\n{traceback.format_exc()}")
        print("!" * 80)
        sys.exit(2)

if __name__ == "__main__":
    main()
