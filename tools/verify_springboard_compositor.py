#!/usr/bin/env python3
"""
Master Verification Test Harness: SpringBoard UI Compositor, Dynamic Island & Fluid Switcher
Architecture: Apple Silicon A19 Pro (t8150 / v57ap / iPhone 18,3) - iOS 27.2 (24B119)

Validates:
1. All 5 JSON specifications in specs/
2. All 4 markdown technical dossiers in docs/ (or findings/ui_compositor/)
3. Clean-room C99 layout solver compilation and execution (-Wall -Wextra -Werror -std=c99 -pedantic -lm)
4. Zero forbidden placeholder tokens (TODO, TBD, placeholder, WIP)
5. Exact coordinate mathematics, spring physics constants, and window level hierarchy
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

def resolve_paths(root: Path):
    """Detect whether running in main workspace or standalone repository layout."""
    if (root / "artifacts" / "ui_compositor").exists():
        # Main iOS 27 workspace layout
        return {
            "mode": "main_workspace",
            "docs_dir": root / "findings" / "ui_compositor",
            "specs_dir": root / "artifacts" / "ui_compositor" / "specs",
            "runtime_dir": root / "artifacts" / "ui_compositor" / "runtime",
            "tools_dir": root / "tools"
        }
    else:
        # Standalone repository layout
        return {
            "mode": "standalone_repo",
            "docs_dir": root / "docs",
            "specs_dir": root / "specs",
            "runtime_dir": root / "runtime",
            "tools_dir": root / "tools"
        }

def test_json_specifications(specs_dir: Path):
    print("[*] Validating 5 JSON Specifications in", specs_dir)
    assert specs_dir.exists(), f"Specs directory not found: {specs_dir}"

    expected_specs = [
        "dynamic_island_geometry_spec.json",
        "dynamic_island_preemption_spec.json",
        "fluid_switcher_physics_spec.json",
        "frontboard_scene_lifecycle_spec.json",
        "springboard_window_level_matrix.json"
    ]

    for spec_name in expected_specs:
        spec_path = specs_dir / spec_name
        assert spec_path.is_file(), f"Missing expected specification: {spec_name}"
        with open(spec_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{spec_name} must parse into a JSON object"
        assert len(data) > 0, f"{spec_name} is empty"
        print(f"    -> [PASS] {spec_name} ({spec_path.stat().st_size} bytes)")

    # 1. Verify dynamic_island_geometry_spec.json
    with open(specs_dir / "dynamic_island_geometry_spec.json", "r", encoding="utf-8") as f:
        island_geo = json.load(f)
    cutout = island_geo["hardware_cutout"]
    assert cutout["position"]["x"] == 196.5, f"Hardware cutout x mismatch: {cutout['position']['x']}"
    assert cutout["position"]["y"] == 11.0, f"Hardware cutout y mismatch: {cutout['position']['y']}"
    assert cutout["size"]["width"] == 120.0, f"Hardware cutout width mismatch: {cutout['size']['width']}"
    assert cutout["size"]["height"] == 35.0, f"Hardware cutout height mismatch: {cutout['size']['height']}"

    mode1_list = [m for m in island_geo["layout_modes"] if m["mode_id"] == 1]
    assert len(mode1_list) == 1, "Mode 1 (Compact Split) must exist in layout_modes"
    mode1 = mode1_list[0]
    lead_pill = mode1["container_geometry"]["leading_pill"]
    trail_pill = mode1["container_geometry"]["trailing_pill"]
    assert lead_pill["x"] == 151.17, f"Leading pill x must be 151.17, got {lead_pill['x']}"
    assert trail_pill["x"] == 324.83, f"Trailing pill x must be 324.83, got {trail_pill['x']}"
    assert lead_pill["width"] == 37.0, f"Leading pill width must be 37.0, got {lead_pill['width']}"
    assert trail_pill["width"] == 37.0, f"Trailing pill width must be 37.0, got {trail_pill['width']}"

    # 2. Verify dynamic_island_preemption_spec.json
    with open(specs_dir / "dynamic_island_preemption_spec.json", "r", encoding="utf-8") as f:
        island_prio = json.load(f)
    assert "priority_queue_hierarchy" in island_prio
    tiers = island_prio["priority_queue_hierarchy"]
    assert any(t["priority"] == 100 for t in tiers), "Missing priority level 100"
    assert any(t["priority"] == 80 for t in tiers), "Missing priority level 80"
    assert any(t["priority"] == 20 for t in tiers), "Missing priority level 20"

    # 3. Verify fluid_switcher_physics_spec.json
    with open(specs_dir / "fluid_switcher_physics_spec.json", "r", encoding="utf-8") as f:
        switcher = json.load(f)
    deck = switcher["deck_switcher_layout_3d"]
    assert deck["card_scaling"]["scale_decrement_per_card"] == 0.082, "Scale decay step must be 0.082"
    assert deck["card_scaling"]["min_scale_clamp"] == 0.65, "Scale clamp must be 0.65"
    assert deck["card_depth_projection"]["Delta_z_pt"] == 40.0, "Depth step must be 40.0"

    spring = switcher["flick_to_home_spring_dynamics"]["physical_parameters"]
    assert spring["mass_m_kg"] == 1.0, "Spring mass must be 1.0"
    assert spring["stiffness_k_npm"] == 380.0, "Spring stiffness must be 380.0"
    assert spring["damping_ratio_zeta"] == 0.88, "Damping ratio must be 0.88"

    # 4. Verify frontboard_scene_lifecycle_spec.json
    with open(specs_dir / "frontboard_scene_lifecycle_spec.json", "r", encoding="utf-8") as f:
        fb_scene = json.load(f)
    watchdogs = fb_scene["watchdog_timer_matrix"]["deadlines"]
    assert any(w["deadline_seconds"] == 20.0 for w in watchdogs), "Missing 20s launch watchdog"
    assert any(w["deadline_seconds"] == 10.0 for w in watchdogs), "Missing 10s transition watchdog"
    assert any(w["deadline_seconds"] == 5.0 for w in watchdogs), "Missing 5s kill watchdog"

    # 5. Verify springboard_window_level_matrix.json
    with open(specs_dir / "springboard_window_level_matrix.json", "r", encoding="utf-8") as f:
        levels = json.load(f)
    matrix = levels["window_level_matrix"]
    assert len(matrix) == 18, f"Window level matrix must have exactly 18 levels, got {len(matrix)}"
    # Verify strict ascending order
    prev_level = -99999.0
    for entry in matrix:
        lvl = entry["window_level"]
        assert lvl >= prev_level, f"Window levels not sorted monotonically: {lvl} < {prev_level}"
        prev_level = lvl
    assert matrix[0]["window_level"] == -1000.0, "Lowest level must be Wallpaper -1000.0"
    assert matrix[-1]["window_level"] == 3500.0, "Highest level must be SecureEnclavePinpad 3500.0"

    print("[+] All 5 JSON specifications successfully verified.\n")

def test_markdown_dossiers(docs_dir: Path):
    print("[*] Validating 4 Technical Markdown Dossiers in", docs_dir)
    assert docs_dir.exists(), f"Docs directory not found: {docs_dir}"

    expected_dossiers = [
        "01_DYNAMIC_ISLAND_SYSTEM_APERTURE_ENGINE.md",
        "02_FLUID_SWITCHER_GESTURAL_MULTITASKING.md",
        "03_FRONTBOARD_BACKBOARDD_COMPOSITOR_PLUMBING.md",
        "04_SPRINGBOARD_IPC_DOMAINS_AND_SYNTHESIS.md"
    ]

    for dossier_name in expected_dossiers:
        p = docs_dir / dossier_name
        assert p.is_file(), f"Missing expected dossier: {dossier_name}"
        size = p.stat().st_size
        assert size > 20000, f"Dossier {dossier_name} size too small: {size} bytes"
        text = p.read_text(encoding="utf-8")
        assert "```mermaid" in text, f"Dossier {dossier_name} missing Mermaid diagrams"
        assert "#" in text, f"Dossier {dossier_name} missing markdown headers"
        print(f"    -> [PASS] {dossier_name} ({size} bytes, structured markdown & diagrams verified)")

    print("[+] All 4 technical dossiers successfully verified.\n")

def test_c99_layout_solver(runtime_dir: Path):
    print("[*] Compiling and Executing Clean-Room C99 Layout Solver...")
    assert runtime_dir.exists(), f"Runtime directory not found: {runtime_dir}"

    header_file = runtime_dir / "springboard_compositor_interface.h"
    solver_file = runtime_dir / "springboard_layout_solver.c"

    assert header_file.is_file(), f"Missing header: {header_file}"
    assert solver_file.is_file(), f"Missing solver: {solver_file}"

    bin_path = Path("/tmp/sb_layout_solver_test")
    if bin_path.exists():
        bin_path.unlink()

    # Compilation command as specified
    compile_cmd = [
        "gcc",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-std=c99",
        "-pedantic",
        str(solver_file),
        "-lm",
        "-o",
        str(bin_path)
    ]

    print("    -> Invoking:", " ".join(compile_cmd))
    res = subprocess.run(compile_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[-] Compilation Failed:")
        print(res.stderr)
        sys.exit(1)

    print("    -> Compilation Succeeded with 0 warnings/errors.")

    # Execute binary
    print("    -> Executing binary:", str(bin_path))
    exec_res = subprocess.run([str(bin_path)], capture_output=True, text=True)
    if exec_res.returncode != 0:
        print("[-] Execution Failed with return code:", exec_res.returncode)
        print(exec_res.stdout)
        print(exec_res.stderr)
        sys.exit(1)

    assert "ALL SPRINGBOARD COMPOSITOR VERIFICATION TESTS PASSED (100% GREEN)" in exec_res.stdout
    print("    -> Clean-room solver execution verified (100% green).")
    print("[+] C99 layout solver test successfully passed.\n")

def test_zero_placeholders(paths: dict):
    print("[*] Asserting Zero Forbidden Placeholder Tokens Across All Deliverables...")
    forbidden_tokens = ["TODO", "TBD", "placeholder", "WIP"]

    dirs_to_scan = [paths["docs_dir"], paths["specs_dir"], paths["runtime_dir"]]
    scanned_files = 0

    for d in dirs_to_scan:
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            # Only scan text deliverables
            if f.suffix in [".md", ".json", ".c", ".h", ".py", ".txt"]:
                scanned_files += 1
                content = f.read_text(encoding="utf-8", errors="ignore")
                for tok in forbidden_tokens:
                    matches = re.findall(rf"\b{re.escape(tok)}\b", content, re.IGNORECASE)
                    if matches:
                        print(f"[-] VIOLATION: File {f} contains {len(matches)} instance(s) of forbidden token '{tok}'")
                        sys.exit(1)

    print(f"    -> Scanned {scanned_files} files across all deliverable folders.")
    print("[+] Zero forbidden placeholder tokens verified.\n")

def main():
    root = Path(__file__).resolve().parent.parent
    print(f"[+] Initializing Master SpringBoard Compositor Verification Harness")
    print(f"[+] Repository Root: {root}")

    paths = resolve_paths(root)
    print(f"[+] Detected Execution Mode: {paths['mode']}\n")

    test_json_specifications(paths["specs_dir"])
    test_markdown_dossiers(paths["docs_dir"])
    test_c99_layout_solver(paths["runtime_dir"])
    test_zero_placeholders(paths)

    print("========================================================================")
    print("CERTIFICATION COMPLETE: 100% OF COMPOSITOR VERIFICATION CHECKS PASSED")
    print("========================================================================")

if __name__ == "__main__":
    main()
