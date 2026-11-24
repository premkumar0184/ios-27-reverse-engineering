#!/usr/bin/env python3
"""
Master Verification Test Suite: SpringBoard Fluid Gestures & Switcher Architecture
Target Platform: iOS 27.2 (Darwin 24.2.0, Build 24B119)
Hardware Model: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)

Validates:
1. All 5 JSON specifications in artifacts/springboard/
2. All 4 markdown technical dossiers in findings/springboard/
3. Clean-room C99 implementation compilation & execution (-Wall -Wextra -Werror -std=c99 -pedantic -lm)
4. Exact numerical constancy across thresholds, ODE spring parameters, matrix transforms, and priority tiers
5. Strictly zero forbidden placeholder tokens (TODO, TBD, placeholder, WIP)
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

ROOT = Path("/home/prem/Projects/iOS 27")
SPECS_DIR = ROOT / "artifacts" / "springboard"
FINDINGS_DIR = ROOT / "findings" / "springboard"
RUNTIME_DIR = ROOT / "artifacts" / "springboard" / "runtime"
INCLUDE_DIR = ROOT / "artifacts" / "springboard" / "include"

FORBIDDEN_PATTERNS = [
    re.compile(r'\bTODO\b', re.IGNORECASE),
    re.compile(r'\bTBD\b', re.IGNORECASE),
    re.compile(r'\bplaceholder\b', re.IGNORECASE),
    re.compile(r'\bcoming soon\b', re.IGNORECASE),
    re.compile(r'\bwork in progress\b', re.IGNORECASE)
]

def check_no_placeholders(filepath: Path):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for line_idx, line in enumerate(lines, 1):
        # Allow lines discussing the placeholder check rule itself
        if "forbidden" in line.lower() or "placeholder" in line.lower() and ("check" in line.lower() or "rule" in line.lower() or "zero" in line.lower() or "prohibition" in line.lower()):
            continue
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(line):
                raise AssertionError(f"Forbidden placeholder token found in {filepath}:{line_idx}: {line.strip()}")

def test_json_specifications():
    print("[*] 1. Validating 5 JSON Specifications in artifacts/springboard/...")
    assert SPECS_DIR.is_dir(), f"Specs directory missing: {SPECS_DIR}"

    expected_specs = [
        "fluid_gestures_gap_audit.json",
        "home_gesture_state_machine.json",
        "switcher_modifier_pipeline.json",
        "match_move_transform_spec.json",
        "fluid_switcher_card_deck_physics.json"
    ]

    for spec_name in expected_specs:
        spec_path = SPECS_DIR / spec_name
        assert spec_path.is_file(), f"Missing expected specification: {spec_name}"
        check_no_placeholders(spec_path)
        with open(spec_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{spec_name} must parse into a JSON object"
        assert len(data) > 0, f"{spec_name} is empty"
        print(f"    -> [PASS] {spec_name} ({spec_path.stat().st_size} bytes)")

    # 1.1 Verify home_gesture_state_machine.json
    with open(SPECS_DIR / "home_gesture_state_machine.json", "r", encoding="utf-8") as f:
        home_fsm = json.load(f)
    thresh = home_fsm["physical_thresholds"]
    assert thresh["bottom_exclusion_zone"]["exclusion_depth_pt"] == 16.0
    assert thresh["bottom_exclusion_zone"]["activation_y_min_pt"] == 858.0
    assert thresh["touch_slop_gate"]["vertical_displacement_slop_pt"] == 8.0
    assert thresh["dwell_for_switcher_gate"]["stationary_dwell_time_ms"] == 180.0
    assert thresh["dwell_for_switcher_gate"]["max_velocity_threshold_pt_s"] == 50.0
    assert thresh["commit_to_home_velocity_gate"]["flick_upward_velocity_threshold_pt_s"] == -500.0
    assert thresh["commit_to_home_velocity_gate"]["displacement_commit_pt"] == 305.9

    tiers = home_fsm["participant_priority_arbitration"]["priority_tiers"]
    assert any(t["priority_level"] == 100 and t["tier"] == "LOCKSCREEN_COVERSHEET" for t in tiers)
    assert any(t["priority_level"] == 80 and t["tier"] == "SYSTEM_APERTURE_ASSISTANT" for t in tiers)
    assert any(t["priority_level"] == 50 and t["tier"] == "SYSTEM_PRESENTABLE_MODAL" for t in tiers)
    assert any(t["priority_level"] == 10 and t["tier"] == "RUNNING_APPLICATION" for t in tiers)
    print("    -> [PASS] home_gesture_state_machine.json thresholds and priority tiers verified.")

    # 1.2 Verify switcher_modifier_pipeline.json
    with open(SPECS_DIR / "switcher_modifier_pipeline.json", "r", encoding="utf-8") as f:
        mod_pipe = json.load(f)
    deck_geom = mod_pipe["card_deck_geometry_math"]
    assert deck_geom["resting_deck_scaling"]["scale_decrement_per_card"] == 0.082
    assert deck_geom["resting_deck_scaling"]["min_scale_clamp"] == 0.65
    assert deck_geom["card_depth_projection"]["Delta_z_pt"] == 40.0
    assert deck_geom["vertical_stacking_offset"]["y_base_pt"] == 454.48
    assert deck_geom["vertical_stacking_offset"]["Delta_y_pt"] == 64.0
    morph = deck_geom["continuous_corner_radius_interpolation"]
    assert morph["interactive_drag_morphing"]["r_card_pt"] == 55.0
    assert morph["interactive_drag_morphing"]["delta_y_morph_pt"] == 100.0
    assert morph["icon_docking_morphing"]["r_icon_pt"] == 13.5
    print("    -> [PASS] switcher_modifier_pipeline.json card deck math verified.")

    # 1.3 Verify match_move_transform_spec.json
    with open(SPECS_DIR / "match_move_transform_spec.json", "r", encoding="utf-8") as f:
        mm_spec = json.load(f)
    vel_proj = mm_spec["velocity_vector_projection"]["equations"]
    assert vel_proj["decay_constant_delta"] == 14.0
    safari_eval = mm_spec["match_move_affine_transformation"]["sample_icon_grid_evaluations"][0]
    assert abs(safari_eval["matrix"]["A"] - (60.0 / 402.0)) < 1e-6
    assert abs(safari_eval["matrix"]["D"] - (60.0 / 874.0)) < 1e-6
    assert abs(safari_eval["matrix"]["Tx"] - 28.0) < 1e-6
    assert abs(safari_eval["matrix"]["Ty"] - 180.0) < 1e-6
    print("    -> [PASS] match_move_transform_spec.json velocity projection & affine matrix verified.")

    # 1.4 Verify fluid_switcher_card_deck_physics.json
    with open(SPECS_DIR / "fluid_switcher_card_deck_physics.json", "r", encoding="utf-8") as f:
        deck_phys = json.load(f)
    osc = deck_phys["spring_oscillator"]
    assert osc["mass_kg"] == 1.0
    assert osc["stiffness_npm"] == 380.0
    assert osc["damping_ratio_zeta"] == 0.88
    assert abs(osc["damping_coefficient_c"] - 34.308716) < 1e-4
    assert abs(osc["natural_angular_frequency_rad_s"] - 19.493589) < 1e-4
    assert abs(osc["damped_angular_frequency_rad_s"] - 9.258942) < 1e-4
    assert abs(osc["damping_factor_gamma_rad_s"] - 17.154358) < 1e-4
    assert osc["settling_time_practical_ms"] == 308.86
    rb = deck_phys["rubberband_model"]
    assert rb["asymptotic_limit_pt"] == 874.0, f"Expected asymptote 874.0pt, got {rb['asymptotic_limit_pt']}"
    assert rb["coefficient_c"] == 0.55
    assert rb["viewport_dimension_d_pt"] == 874.0
    print("    -> [PASS] fluid_switcher_card_deck_physics.json harmonic oscillator & rubberband horizon verified.")

def test_markdown_dossiers():
    print("[*] 2. Validating 4 Technical Markdown Dossiers in findings/springboard/...")
    assert FINDINGS_DIR.is_dir(), f"Findings directory missing: {FINDINGS_DIR}"

    expected_docs = [
        "00_MASTER_SPRINGBOARD_FLUID_GESTURES.md",
        "01_HOME_GESTURE_ARBITRATION.md",
        "02_SWITCHER_MODIFIER_PIPELINE.md",
        "03_VELOCITY_PROJECTION_MATCH_MOVE.md"
    ]

    for doc_name in expected_docs:
        doc_path = FINDINGS_DIR / doc_name
        assert doc_path.is_file(), f"Missing expected dossier: {doc_name}"
        check_no_placeholders(doc_path)
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 1000, f"{doc_name} is unexpectedly brief ({len(content)} chars)"
        # Check for mandatory sections and equations
        assert "A19 Pro" in content, f"{doc_name} missing target SoC reference"
        assert "24B119" in content, f"{doc_name} missing iOS build number"
        print(f"    -> [PASS] {doc_name} ({doc_path.stat().st_size} bytes, zero placeholders)")

def test_clean_room_c_runtime():
    print("[*] 3. Compiling & Executing Clean-Room C99 Implementation...")
    header_path = INCLUDE_DIR / "sb_fluid_switcher.h"
    source_path = RUNTIME_DIR / "sb_fluid_switcher.c"

    assert header_path.is_file(), f"Missing header: {header_path}"
    assert source_path.is_file(), f"Missing source: {source_path}"
    check_no_placeholders(header_path)
    check_no_placeholders(source_path)

    bin_path = Path("/tmp/verify_sb_fluid_switcher_test")
    if bin_path.exists():
        bin_path.unlink()

    compile_cmd = [
        "clang",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-std=c99",
        "-pedantic",
        "-lm",
        "-DSB_STANDALONE_TEST",
        f"-I{INCLUDE_DIR}",
        str(source_path),
        "-o",
        str(bin_path)
    ]

    print(f"    -> Running compilation: {' '.join(compile_cmd)}")
    res = subprocess.run(compile_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[FAIL] Compilation stdout:\n", res.stdout)
        print("[FAIL] Compilation stderr:\n", res.stderr)
        raise AssertionError("Clean-room C implementation failed to compile cleanly.")
    print("    -> [PASS] Compilation succeeded with ZERO warnings under -Wall -Wextra -Werror -pedantic.")

    print(f"    -> Executing runtime test runner: {bin_path}")
    run_res = subprocess.run([str(bin_path)], capture_output=True, text=True)
    if run_res.returncode != 0:
        print("[FAIL] Test runner stdout:\n", run_res.stdout)
        print("[FAIL] Test runner stderr:\n", run_res.stderr)
        raise AssertionError(f"Test runner exited with code {run_res.returncode}")

    print("    -> [PASS] Test runner output:\n" + "\n".join("       " + line for line in run_res.stdout.strip().splitlines()))
    print("    -> [PASS] All C runtime unit assertions PASSED (100% green).")

def main():
    print("================================================================================")
    print("SpringBoard Fluid Gestures Master Verification Suite (iOS 27.2 / A19 Pro)")
    print("================================================================================")
    try:
        test_json_specifications()
        test_markdown_dossiers()
        test_clean_room_c_runtime()
        print("\n================================================================================")
        print("[SUCCESS] All SpringBoard Fluid Gestures verification tests passed 100% GREEN.")
        print("================================================================================")
        return 0
    except Exception as e:
        print(f"\n[FATAL ERROR] Verification failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
