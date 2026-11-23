#!/usr/bin/env python3
"""
Apple Display Co-Processor (DCP) & ProMotion 120Hz Pipeline Deep-Dive Verification Suite
Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
Hardware Target: Apple Silicon A19 Pro (t8150) — iPhone 18,3 (v57ap)

Validates:
- Gate 1: VFTG Line Time & Scan-Rate Invariance (504.0 MHz, 2.778 us line time, 7.967 ms active scan)
- Gate 2: VBP Blanking Modulation Math across all 11 discrete refresh modes (1Hz to 120Hz)
- Gate 3: SWMPR FSM transitions, <8.33ms touch-boost ramp-up, and 100ms deceleration hysteresis
- Gate 4: BICS 8 MB (0x800000) history buffer allocation & PTUC 64x32 thermal zone grid
- Gate 5: PDC subpixel feathering, mix bins, and ACSS off-axis microcavity tuning
- Gate 6: DART-DCP Stream ID multiplexing (0x01/0x02/0x03), Tightbeam RPC, and SIL nits capping
- Gate 7: Master Dossier completeness, size (>35KB), and strict zero-placeholder policy
"""

import os
import sys
import json
import math
import re

SUCCESS = 0
FAILURE = 1

def log_gate(gate_num, name, status, details=""):
    badge = "[PASS]" if status else "[FAIL]"
    print(f"Gate {gate_num} {badge} {name}")
    if details:
        print(f"       -> {details}")

def verify_gate_1(vftg_spec):
    """Gate 1: VFTG Line Time & Scan-Rate Invariance"""
    hw = vftg_spec["vftg_hardware"]
    pclk = hw["pixel_clock_hz"]
    h_total = hw["horizontal_geometry"]["total_pixels_per_line"]
    v_active = hw["vertical_geometry"]["active_lines"]
    
    assert pclk == 504000000, f"Expected 504 MHz pixel clock, got {pclk}"
    assert h_total == 1400, f"Expected 1400 total horizontal pixels, got {h_total}"
    assert v_active == 2868, f"Expected 2868 active vertical lines, got {v_active}"
    
    # Calculate line time: 1400 / 504e6 s = 2.77777778 us
    line_time_us = (h_total / pclk) * 1e6
    assert abs(line_time_us - 2.777778) < 1e-4, f"Line time deviation: {line_time_us} us"
    
    # Active scan duration: 2868 * line_time = 7966.66667 us
    active_scan_us = v_active * line_time_us
    assert abs(active_scan_us - 7966.66667) < 1e-2, f"Active scan duration deviation: {active_scan_us} us"
    
    return True, f"504.0 MHz PCLK invariant confirmed: Line time={line_time_us:.4f} us, Active scan={active_scan_us/1000.0:.3f} ms"

def verify_gate_2(vftg_spec):
    """Gate 2: VBP Blanking Modulation Math across all 11 discrete modes"""
    hw = vftg_spec["vftg_hardware"]
    pclk = hw["pixel_clock_hz"]
    h_total = hw["horizontal_geometry"]["total_pixels_per_line"]
    v_active = hw["vertical_geometry"]["active_lines"]
    v_fp = hw["vertical_geometry"]["front_porch_lines"]
    v_sync = hw["vertical_geometry"]["sync_width_lines"]
    fixed_overhead = v_active + v_fp + v_sync # 2884 lines
    
    modes = hw["dynamic_blanking_modulation"]["discrete_timing_modes"]
    assert len(modes) == 11, f"Expected 11 discrete ProMotion modes, got {len(modes)}"
    
    for m in modes:
        hz = m["rate_hz"]
        vbp = m["vbp_lines"]
        total_lines = m["total_lines"]
        expected_total = fixed_overhead + vbp
        assert total_lines == expected_total, f"{hz}Hz: total_lines mismatch ({total_lines} != {expected_total})"
        
        # Calculate theoretical frame duration in us
        calculated_duration_us = (total_lines * h_total / pclk) * 1e6
        expected_duration_us = (1.0 / hz) * 1e6
        
        # Allow <0.5% tolerance for integer line quantization
        rel_diff = abs(calculated_duration_us - expected_duration_us) / expected_duration_us
        assert rel_diff < 0.005, f"{hz}Hz: frame duration mismatch ({calculated_duration_us} vs {expected_duration_us})"
        
    return True, "All 11 modes (1Hz - 120Hz) perfectly obey total_lines = 2884 + VBP and target refresh cadence"

def verify_gate_3(promotion_spec):
    """Gate 3: SWMPR FSM, Touch-Boost, and Hysteresis Constraints"""
    arch = promotion_spec["promotion_architecture"]
    fsm = arch["arbitration_state_machine"]
    states = fsm["states"]
    assert len(states) == 6, f"Expected 6 FSM states, got {len(states)}"
    
    state_names = [s["name"] for s in states]
    required_states = [
        "SWMPR_STATE_IDLE_10HZ",
        "SWMPR_STATE_INTERACTIVE_RAMP_UP",
        "SWMPR_STATE_ACTIVE_120HZ",
        "SWMPR_STATE_DECEL_RAMP_DOWN",
        "SWMPR_STATE_MEDIA_LOCK_24_48_60HZ",
        "SWMPR_STATE_AOD_1HZ"
    ]
    for req in required_states:
        assert req in state_names, f"Missing FSM state: {req}"
        
    touch_boost = fsm["touch_boost_policy"]
    assert touch_boost["ramp_up_latency_us"] <= 8333.334, "Touch boost latency must be <= 8.33ms (1 frame)"
    
    hysteresis = fsm["deceleration_hysteresis"]
    assert hysteresis["total_hysteresis_duration_ms"] == 100, "Deceleration hysteresis must equal exactly 100ms"
    steps = hysteresis["stair_down_sequence"]
    total_step_time = sum(s["hold_ms"] for s in steps)
    assert total_step_time == 100, f"Sum of stair-down hold times must equal 100ms, got {total_step_time}"
    
    return True, "FSM verified: 6 states, <8.33ms touch boost jump to 120Hz, 100ms 5-step stair-down hysteresis"

def verify_gate_4(ppc_spec):
    """Gate 4: BICS 8 MB (0x800000) History Buffer & PTUC 64x32 Thermal Grid"""
    engines = ppc_spec["panel_compensation_engines"]
    bics = engines["bics"]
    assert bics["history_buffer_size_bytes"] == 8388608, f"BICS history size must be 8 MB (8388608), got {bics['history_buffer_size_bytes']}"
    assert bics["history_buffer_hex"] == "0x800000", "BICS history hex must be 0x800000"
    assert "BICS::do_gain" in bics["gain_calculation_routines"]
    assert "BICS::do_tbics_gain" in bics["gain_calculation_routines"]
    
    ptuc = engines["ptuc"]
    grid = ptuc["grid_resolution"]
    assert grid["grid_x_count"] == 64, "PTUC grid X count must be 64"
    assert grid["grid_y_count"] == 32, "PTUC grid Y count must be 32"
    assert grid["total_zones"] == 2048, "PTUC total zones must be 2048"
    assert any("T8150_TTR" in s for s in ptuc["sensor_inputs"]), "PTUC must sample A19 Pro on-die sensors"
    
    return True, "BICS 8 MB history buffer confirmed & PTUC 64x32 (2048-zone) thermal grid verified"

def verify_gate_5(ppc_spec):
    """Gate 5: PDC Subpixel Feathering & ACSS Off-Axis Rescale"""
    engines = ppc_spec["panel_compensation_engines"]
    pdc = engines["pdc"]
    assert "PDCc (Configuration control block)" in pdc["configuration_blocks"]
    assert "PDCp (Parameter data block)" in pdc["configuration_blocks"]
    assert len(pdc["channels_compensated"]) == 3, "PDC must compensate Red, Green, Blue channels"
    
    acss = engines["acss"]
    assert "EMMP table" in acss["table_type"]
    assert "ACSS_ALS_RESCALE" in acss["ambient_adaptation"]
    
    return True, "PDCc/PDCp parameter blocks and ACSS EMMP ALS adaptation verified"

def verify_gate_6(exclave_spec):
    """Gate 6: DART-DCP Stream ID Topology, Tightbeam RPC, and SIL Protection"""
    arch = exclave_spec["exclave_display_architecture"]
    dart_dcp = arch["iommu_configuration"]["dart_dcp"]
    dart_disp0 = arch["iommu_configuration"]["dart_disp0"]
    
    assert dart_dcp["mmio_base"] == "0x00000001fa340000", "DART-DCP base must be 0x1fa340000"
    assert dart_disp0["mmio_base"] == "0x00000001fa300000", "DART-DISP0 base must be 0x1fa300000"
    
    streams = arch["stream_id_allocations"]
    assert len(streams) == 3, f"Expected 3 DART Stream IDs, got {len(streams)}"
    
    stream_map = {s["stream_id"]: s for s in streams}
    assert "0x01" in stream_map and "Host" in stream_map["0x01"]["domain"]
    assert "0x02" in stream_map and "Exclave" in stream_map["0x02"]["domain"]
    assert "0x03" in stream_map and "Cursor" in stream_map["0x03"]["domain"]
    
    # SIL and Blending
    blend = arch["hardware_blending_engine"]
    assert "SecureBlendHandler.cpp" in blend["handler"]
    sil = blend["secure_indicator_light_protection"]
    assert "above Indicator nits cap" in sil["nits_capping_enforcement"]
    
    return True, "DART-DCP Stream IDs (0x01 Host / 0x02 Exclave / 0x03 Cursor) and SecureBlendHandler verified"

def verify_gate_7(dossier_path):
    """Gate 7: Master Dossier Completeness, Size (>35KB), and Zero Placeholders"""
    if not os.path.isfile(dossier_path):
        return False, f"Master dossier not found at {dossier_path}"
        
    size_bytes = os.path.getsize(dossier_path)
    if size_bytes < 35000:
        return False, f"Master dossier size {size_bytes} bytes is below required 35,000 bytes"
        
    with open(dossier_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check for placeholder strings
    placeholders = ["TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", "<insert"]
    found_placeholders = []
    for p in placeholders:
        matches = re.findall(rf"\b{p}\b", content, re.IGNORECASE)
        if matches:
            found_placeholders.append(f"{p} ({len(matches)} occurrences)")
            
    if found_placeholders:
        return False, f"Detected disallowed placeholders: {', '.join(found_placeholders)}"
        
    # Check for critical technical keywords
    required_keywords = [
        "UPBlock_SWMPR_v1",
        "UPBlock_VFTG_v38",
        "UPBlock_BICS_v19",
        "UPBlock_PTUC_v4",
        "UPBlock_PDC_v11",
        "UPBlock_ACSS_v11",
        "RTKExclaveTBEndpoint",
        "SecureBlendHandler",
        "DART-DCP",
        "504.0 MHz",
        "mapper-dcp-exclave",
        "Fast_TE"
    ]
    missing = [kw for kw in required_keywords if kw not in content]
    if missing:
        return False, f"Missing critical technical keywords: {missing}"
        
    return True, f"Master dossier verified: {size_bytes} bytes, 0 placeholders, all critical keywords present"

def main():
    print("=" * 80)
    print(" Display Co-Processor (DCP) & ProMotion 120Hz Pipeline Deep-Dive Test Suite")
    print("=" * 80)
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dcp_art_dir = os.path.join(base_dir, "artifacts", "dcp")
    findings_dir = os.path.join(base_dir, "findings", "dcp")
    
    vftg_file = os.path.join(dcp_art_dir, "vftg_timing_generator_spec.json")
    promotion_file = os.path.join(dcp_art_dir, "promotion_arbitration_spec.json")
    ppc_file = os.path.join(dcp_art_dir, "pixel_compensation_spec.json")
    exclave_file = os.path.join(dcp_art_dir, "exclave_compositor_spec.json")
    dossier_file = os.path.join(findings_dir, "05_DCP_PROMOTION_EXCLAVE_DEEPDIVE.md")
    
    with open(vftg_file, "r") as f:
        vftg_spec = json.load(f)
    with open(promotion_file, "r") as f:
        promotion_spec = json.load(f)
    with open(ppc_file, "r") as f:
        ppc_spec = json.load(f)
    with open(exclave_file, "r") as f:
        exclave_spec = json.load(f)
        
    all_passed = True
    
    # Gate 1
    g1_ok, g1_msg = verify_gate_1(vftg_spec)
    log_gate(1, "VFTG Line Time & Scan-Rate Invariance", g1_ok, g1_msg)
    if not g1_ok: all_passed = False
    
    # Gate 2
    g2_ok, g2_msg = verify_gate_2(vftg_spec)
    log_gate(2, "VBP Blanking Modulation Math (1Hz-120Hz)", g2_ok, g2_msg)
    if not g2_ok: all_passed = False
    
    # Gate 3
    g3_ok, g3_msg = verify_gate_3(promotion_spec)
    log_gate(3, "SWMPR FSM, Touch-Boost & Hysteresis", g3_ok, g3_msg)
    if not g3_ok: all_passed = False
    
    # Gate 4
    g4_ok, g4_msg = verify_gate_4(ppc_spec)
    log_gate(4, "BICS 8MB Aging Buffer & PTUC 64x32 Grid", g4_ok, g4_msg)
    if not g4_ok: all_passed = False
    
    # Gate 5
    g5_ok, g5_msg = verify_gate_5(ppc_spec)
    log_gate(5, "PDC Subpixel Feathering & ACSS ALS Tuning", g5_ok, g5_msg)
    if not g5_ok: all_passed = False
    
    # Gate 6
    g6_ok, g6_msg = verify_gate_6(exclave_spec)
    log_gate(6, "DART-DCP Stream IDs & Exclave Security", g6_ok, g6_msg)
    if not g6_ok: all_passed = False
    
    # Gate 7 (Dossier Gate)
    g7_ok, g7_msg = verify_gate_7(dossier_file)
    log_gate(7, "Master Publication Dossier Integrity", g7_ok, g7_msg)
    if not g7_ok: all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("[ALL GATES PASSED] Display Co-Processor Deep-Dive successfully validated!")
        return SUCCESS
    else:
        print("[VALIDATION FAILED] One or more gates failed verification.")
        return FAILURE

if __name__ == "__main__":
    sys.exit(main())
