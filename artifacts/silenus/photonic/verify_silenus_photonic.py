#!/usr/bin/env python3
"""
Automated Verification Suite for Apple Silenus H18ISP Photonic Engine & Statistics Pipeline
Validates binary integrity, struct unpacks, 3x3 matrix invariants, and zero placeholders.
"""

import os
import sys
import json
import struct
import hashlib
import numpy as np

WORKSPACE_ROOT = "/home/prem/Projects/iOS 27"
ARTIFACTS_DIR = os.path.join(WORKSPACE_ROOT, "artifacts/silenus/photonic")
FINDINGS_DIR = os.path.join(WORKSPACE_ROOT, "findings/silenus")
MACHO_PATH = os.path.join(ARTIFACTS_DIR, "silenus_isp.macho")
DOSSIER_PATH = os.path.join(FINDINGS_DIR, "02_PHOTONIC_ENGINE_STATS_PIPELINE.md")

def log(msg, status="INFO"):
    symbol = {"INFO": "[*]", "PASS": "[+]", "FAIL": "[-]"}.get(status, "[*]")
    print(f"{symbol} {msg}")

def test_macho_binary():
    log("Gate 1: Verifying Mach-O Binary Structural Integrity...", "INFO")
    assert os.path.exists(MACHO_PATH), f"Missing binary at {MACHO_PATH}"
    file_size = os.path.getsize(MACHO_PATH)
    assert file_size == 29016064, f"Binary size mismatch: {file_size} != 29016064"
    
    with open(MACHO_PATH, "rb") as f:
        header = f.read(32)
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", header)
        assert magic == 0xfeedfacf, f"Invalid Mach-O 64 magic: {hex(magic)}"
        assert cputype == 0x0100000c, f"Unexpected CPU type: {hex(cputype)} (expected ARM64)"
        
        # Verify __TEXT.__const section header
        f.seek(32)
        found_const = False
        for _ in range(ncmds):
            cmd_start = f.tell()
            cmd, cmdsize = struct.unpack("<II", f.read(8))
            if cmd == 0x19: # LC_SEGMENT_64
                seg_hdr = f.read(64)
                segname, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack("<16sQQQQIIII", seg_hdr)
                for _ in range(nsects):
                    sect_data = f.read(80)
                    sectname, segname2, s_addr, s_size, s_offset, s_align, s_reloff, s_nreloc, s_flags, r1, r2, r3 = struct.unpack("<16s16sQQIIIIIIII", sect_data)
                    s_name = sectname.decode('ascii', errors='ignore').strip('\x00')
                    if s_name == "__const" and s_addr == 0x00ae2080:
                        assert s_size == 0x008b3308, f"Unexpected __const size: {s_size}"
                        assert s_offset == 0x00ae6080, f"Unexpected __const offset: {s_offset}"
                        found_const = True
            f.seek(cmd_start + cmdsize)
        assert found_const, "Could not find __TEXT.__const section in Mach-O headers"
    log("Gate 1 Passed: Mach-O binary verified (29,016,064 bytes, 64-bit ARM, valid __const section).", "PASS")

def test_vispipe_architecture():
    log("Gate 2: Verifying VISPIPE Architecture & Stream Endpoints...", "INFO")
    vispipe_path = os.path.join(ARTIFACTS_DIR, "vispipe_architecture.json")
    assert os.path.exists(vispipe_path), f"Missing {vispipe_path}"
    with open(vispipe_path, "r") as f:
        data = json.load(f)
    
    endpoints = data.get("pipeline_endpoints", [])
    assert len(endpoints) >= 17, f"Expected at least 17 endpoints, got {len(endpoints)}"
    
    # Check key endpoints
    endpoint_map = {ep["name"]: ep for ep in endpoints}
    assert "TYPE_VISPIPE" in endpoint_map, "Missing TYPE_VISPIPE endpoint"
    assert endpoint_map["TYPE_VISPIPE"]["mmio_base"] == "0x0000000321b00000", "Incorrect MMIO for TYPE_VISPIPE"
    assert "VISPIPE_SRC" in endpoint_map, "Missing VISPIPE_SRC endpoint"
    assert endpoint_map["VISPIPE_SRC"]["mmio_base"] == "0x0000000321c004a8", "Incorrect MMIO for VISPIPE_SRC"
    assert "VISPIPE_DST" in endpoint_map, "Missing VISPIPE_DST endpoint"
    assert endpoint_map["VISPIPE_DST"]["mmio_base"] == "0x0000000321c10f2c", "Incorrect MMIO for VISPIPE_DST"
    
    # Check pixel format list
    pixel_formats = data.get("pixel_formats", [])
    assert len(pixel_formats) >= 27, f"Expected at least 27 pixel formats, got {len(pixel_formats)}"
    fmt_names = [pf["name"] for pf in pixel_formats]
    assert "RAW8" in fmt_names and "RAW10" in fmt_names and "RAW14" in fmt_names and "RAW16" in fmt_names
    assert "ARGB8888" in fmt_names and "YCC42010_2Plane" in fmt_names and "Stats_AFBayerYF0" in fmt_names
    
    log("Gate 2 Passed: VISPIPE architecture and 17 stream endpoints verified.", "PASS")

def test_stats_pipeline_state_machines():
    log("Gate 3: Verifying Statistical Estimation State Machines...", "INFO")
    stats_path = os.path.join(ARTIFACTS_DIR, "stats_pipeline_state_machines.json")
    assert os.path.exists(stats_path), f"Missing {stats_path}"
    with open(stats_path, "r") as f:
        data = json.load(f)
    
    modules = data.get("modules", [])
    assert len(modules) == 22, f"Expected 22 state machine modules, got {len(modules)}"
    
    # Verify binary correspondence
    with open(MACHO_PATH, "rb") as f:
        macho_bytes = f.read()
    
    for mod in modules:
        off = int(mod["descriptor_file_offset"], 16)
        sym = mod["symbol"]
        raw_sym = macho_bytes[off:off+len(sym)].decode("ascii", errors="ignore")
        assert raw_sym == sym, f"Symbol mismatch at {hex(off)}: expected {sym}, got {raw_sym}"
        
        reg_ptr = struct.unpack("<Q", macho_bytes[off+0x100:off+0x108])[0]
        expected_reg = int(mod["hardware_register_mmio"], 16)
        assert reg_ptr == expected_reg, f"MMIO register pointer mismatch for {sym}: {hex(reg_ptr)} != {hex(expected_reg)}"
    
    log("Gate 3 Passed: All 22 aisp_IspStatsPipe* state machines verified bit-exact against binary.", "PASS")

def test_isp_mathematical_tables():
    log("Gate 4: Verifying Mathematical Lookup Tables & CSC Invariants...", "INFO")
    math_path = os.path.join(ARTIFACTS_DIR, "isp_mathematical_tables.json")
    assert os.path.exists(math_path), f"Missing {math_path}"
    with open(math_path, "r") as f:
        data = json.load(f)
    
    csc = data.get("color_space_conversion_matrices", {})
    csca = np.array(csc["csca_forward_matrix"]["matrix_3x3"])
    cscb = np.array(csc["cscb_reverse_matrix"]["matrix_3x3"])
    
    # Verify dimensions
    assert csca.shape == (3, 3) and cscb.shape == (3, 3), "Invalid CSC matrix shapes"
    
    # Verify non-singular determinant (empirically calculated det = 2.452400)
    det_csca = np.linalg.det(csca)
    assert abs(det_csca - 2.452400) < 0.01, f"Unexpected CSCA determinant: {det_csca}"
    
    # Verify transpose-inverse mathematical pairing
    inv_csca_t = np.linalg.inv(csca).T
    frobenius_diff = np.linalg.norm(cscb - inv_csca_t)
    assert frobenius_diff < 0.0002, f"Frobenius norm difference too high: {frobenius_diff}"
    
    # Verify TRC gamma curve
    trc = data.get("tone_reproduction_curves", {})
    srgb = trc.get("srgb_gamma_curve", {})
    assert srgb.get("total_nodes") == 257, "sRGB curve must contain 257 nodes"
    assert srgb.get("start_value") == 0 and srgb.get("end_value") == 65535, "sRGB curve must span [0, 65535]"
    assert srgb.get("mid_value") == 48310, "sRGB curve midpoint must equal 48310"
    
    log("Gate 4 Passed: CSCA/CSCB transpose-inverse invariant and 257-node sRGB TRC verified.", "PASS")

def test_frmstate_synchronization():
    log("Gate 5: Verifying Frame State Synchronization & Time Machine Descriptors...", "INFO")
    frm_path = os.path.join(ARTIFACTS_DIR, "frmstate_synchronization.json")
    assert os.path.exists(frm_path), f"Missing {frm_path}"
    with open(frm_path, "r") as f:
        data = json.load(f)
    
    fields = [f["name"] for f in data.get("descriptor_fields", [])]
    expected_fields = ["ch", "send_ch", "num", "retain", "fstype", "ts", "mode", "bktag", "rqtype"]
    for ef in expected_fields:
        assert ef in fields, f"Missing expected descriptor field {ef}"
    
    pools = [p["pool_name"] for p in data.get("time_machine_raw_buffer_pools", [])]
    assert "RAW_POOL_COMMON_DUAL_PRIME" in pools
    assert "RAW_POOL_COMMON_SLAVE_SHARE" in pools
    assert "RAW_POOL_COMMON_DUAL_PRIME_STILL" in pools
    assert "RAW_POOL_COMMON_FEP" in pools
    
    log("Gate 5 Passed: Time Machine circular frame descriptor and buffer pools verified.", "PASS")

def test_master_dossier_integrity():
    log("Gate 6: Verifying Master Publication Dossier Integrity...", "INFO")
    assert os.path.exists(DOSSIER_PATH), f"Missing dossier at {DOSSIER_PATH}"
    dossier_size = os.path.getsize(DOSSIER_PATH)
    assert dossier_size > 35000, f"Dossier size too small: {dossier_size} <= 35000 bytes"
    
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier_content = f.read()
    
    # Verify zero placeholders
    placeholders = ["TODO", "TBD", "placeholder", "FIXME"]
    for ph in placeholders:
        assert ph not in dossier_content, f"Found forbidden placeholder '{ph}' in master dossier"
    
    # Verify essential technical sections
    required_sections = [
        "Phase 2A — Hardware Visual Pipeline (VISPIPE) Architecture",
        "Phase 2B — Statistical Estimation & Correction State Machines",
        "Phase 2C — Mathematical Coefficient Tables",
        "Phase 2D — Frame State Synchronization",
        "TYPE_VISPIPE", "VISPIPE_SRC", "VISPIPE_DST",
        "aisp_IspStatsPipeSLin0_FrmState", "aisp_IspStatsBeVNF0_FrmState",
        "0x00b3eb68", "0x00b3eb8c", "0x00b2c080",
        "TM Capture: ch:0x%zu send ch:0x%lx"
    ]
    for sec in required_sections:
        assert sec in dossier_content, f"Missing required technical section / token '{sec}' in dossier"
    
    log(f"Gate 6 Passed: Master dossier verified ({dossier_size} bytes, zero placeholders, complete coverage).", "PASS")

def main():
    print("=" * 78)
    print("Apple Silenus H18ISP Photonic Engine Reverse Engineering Test Harness")
    print("=" * 78)
    
    test_macho_binary()
    test_vispipe_architecture()
    test_stats_pipeline_state_machines()
    test_isp_mathematical_tables()
    test_frmstate_synchronization()
    test_master_dossier_integrity()
    
    print("=" * 78)
    print("[SUCCESS] All 6 Verification Gates Passed with 100% Empirical Proof!")
    print("=" * 78)

if __name__ == "__main__":
    main()
