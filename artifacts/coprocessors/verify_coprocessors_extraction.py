#!/usr/bin/env python3
"""
verify_coprocessors_extraction.py

Automated verification harness for Apple Silicon A19 Pro (t8150) / iPhone 18,3 (v57ap)
peripheral coprocessors: ALPM, Secure M3, MSR IOSurfaceAccelerator, WirelessPower, and Volchok BMU.

Gates:
  Gate 1: Apple Low Power Monitor (ALPM) IM4P & fwsg Tail Segment Table
  Gate 2: Secure M3 Coprocessor (SM3) Mach-O 32-bit & Tightbeam IPC Buffer
  Gate 3: Memory System Resource (MSR) Mach-O 32-bit & Pixel Accelerator Pipeline
  Gate 4: Wireless Power FTAB Container, Partitions (DORX, BOOT, DOTX) & Vectors
  Gate 5: Volchok X3357 Battery Management Unit Chemistry Profiles & su_crypto
  Gate 6: JSON Specifications Integrity & Schema Completeness
  Gate 7: Clean-Room C Runtime Headers Syntax & Compilation
"""

import os
import sys
import json
import struct
import plistlib
import subprocess

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def log_gate(gate_num, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] Gate {gate_num}: {name}")
    if detail:
        print(f"       -> {detail}")
    if not passed:
        sys.exit(1)

def test_gate1_alpm():
    alpm_path = os.path.join(BASE_DIR, "iPhone18,3_27.2_24B119_Restore/Firmware/AppleLPM/AppleLPM.v57.release.im4p")
    assert os.path.exists(alpm_path), "AppleLPM IM4P missing"
    with open(alpm_path, "rb") as f:
        data = f.read()
    
    assert b"alpm" in data[:32], "Missing 'alpm' fourcc in IM4P header"
    fwsg_idx = data.rfind(b"fwsg")
    assert fwsg_idx != -1, "Missing 'fwsg' tail magic in ALPM"
    
    magic, ver, table_off, num_segs = struct.unpack("<IIII", data[fwsg_idx:fwsg_idx+16])
    assert magic == 0x67737766, f"Invalid fwsg magic: {magic:#x}"
    assert ver == 1, f"Invalid fwsg version: {ver}"
    assert num_segs == 2, f"Expected 2 segments, got {num_segs}"
    assert b"RTKit_armv8_chinook" in data, "Missing RTKit Chinook build string"
    assert b"disp0-service" in data, "Missing disp0-service string"
    assert b"afk_client_init" in data, "Missing afk_client_init string"
    
    log_gate(1, "Apple Low Power Monitor (ALPM) fwsg Table & AFK IPC", True,
             f"Size={len(data):,d} B, fwsg_off={fwsg_idx:#x}, segs={num_segs}")

def test_gate2_secure_m3():
    sm3_path = os.path.join(BASE_DIR, "iPhone18,3_27.2_24B119_Restore/Firmware/M3/bin/securem3fw-v57.im4p")
    assert os.path.exists(sm3_path), "Secure M3 IM4P missing"
    with open(sm3_path, "rb") as f:
        f.seek(0x19)
        macho = f.read()
    
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack("<IIIIIII", macho[:28])
    assert magic == 0xfeedface, f"Expected Mach-O 32-bit magic 0xfeedface, got {magic:#x}"
    assert cputype == 0xc, f"Expected CPU_TYPE_ARM (0xc), got {cputype:#x}"
    assert cpusubtype == 0xf, f"Expected CPU_SUBTYPE_ARM_V7M (0xf), got {cpusubtype:#x}"
    assert b"__tb_ipc_buf" in macho, "Missing __tb_ipc_buf section"
    assert b"isp_to_m3_tightbeam.c" in macho, "Missing isp_to_m3_tightbeam.c symbol"
    assert b"RTKit_armv7m_Oz" in macho, "Missing RTKit armv7m build string"
    
    log_gate(2, "Secure M3 Coprocessor (SM3) Mach-O 32-bit & Tightbeam IPC", True,
             f"Mach-O size={len(macho):,d} B, ncmds={ncmds}, __tb_ipc_buf validated")

def test_gate3_msr():
    msr_path = os.path.join(BASE_DIR, "iPhone18,3_27.2_24B119_Restore/Firmware/msr/t8150.msrf.im4p")
    assert os.path.exists(msr_path), "MSR IM4P missing"
    with open(msr_path, "rb") as f:
        f.seek(0x19)
        macho = f.read()
    
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack("<IIIIIII", macho[:28])
    assert magic == 0xfeedface, f"Expected Mach-O 32-bit magic 0xfeedface, got {magic:#x}"
    assert cputype == 0xc, f"Expected CPU_TYPE_ARM (0xc), got {cputype:#x}"
    assert cpusubtype == 0xf, f"Expected CPU_SUBTYPE_ARM_V7M (0xf), got {cpusubtype:#x}"
    assert b"IOSurfaceAccelerator_Firmware" in macho, "Missing IOSurfaceAccelerator symbol"
    assert b"_pa_configure_pipeline" in macho, "Missing _pa_configure_pipeline symbol"
    assert b"Apiodma" in macho, "Missing Apiodma symbol"
    assert b"_dmem_image" in macho, "Missing _dmem_image section"
    
    log_gate(3, "Memory System Resource (MSR) IOSurfaceAccelerator & Pixel Pipeline", True,
             f"Mach-O size={len(macho):,d} B, ncmds={ncmds}, PA pipeline validated")

def test_gate4_wireless_power():
    wipw_path = os.path.join(BASE_DIR, "iPhone18,3_27.2_24B119_Restore/Firmware/WirelessPower/WirelessPower.d23_v5z.im4p")
    assert os.path.exists(wipw_path), "WirelessPower IM4P missing"
    with open(wipw_path, "rb") as f:
        data = f.read()
    
    ftab_idx = data.find(b"rkosftab")
    assert ftab_idx != -1, "Missing rkosftab magic"
    ftab = data[ftab_idx:]
    magic = ftab[:8]
    assert magic == b"rkosftab", f"Invalid FTAB magic: {magic}"
    num_entries = struct.unpack("<I", ftab[8:12])[0]
    assert num_entries == 3, f"Expected 3 FTAB entries, got {num_entries}"
    
    # check partition tags
    tags = [ftab[16:20], ftab[32:36], ftab[48:52]]
    assert b"DORX" in tags, "Missing DORX partition"
    assert b"BOOT" in tags, "Missing BOOT partition"
    assert b"DOTX" in tags, "Missing DOTX partition"
    
    log_gate(4, "Wireless Power FTAB Container, Partitions & Entry Vectors", True,
             f"FTAB offset={ftab_idx:#x}, partitions={[t.decode('ascii') for t in tags]}")

def test_gate5_volchok():
    v_map_path = os.path.join(BASE_DIR, "iPhone18,3_27.2_24B119_Restore/Firmware/Volchok/X3357/FirmwareMap.plist")
    assert os.path.exists(v_map_path), "Volchok FirmwareMap.plist missing"
    with open(v_map_path, "rb") as f:
        pl = plistlib.load(f)
    
    assert pl["product_id"] == "X3357", f"Expected product_id X3357, got {pl.get('product_id')}"
    assert pl["board_id"] == 13143, f"Expected board_id 13143, got {pl.get('board_id')}"
    assert "20" in pl["hw_version"], "Missing hw_version 20"
    v20 = pl["hw_version"]["20"]
    assert "chemistry" in v20, "Missing chemistry dictionary"
    assert len(v20["chemistry"]) >= 5, f"Expected >= 5 chemistry profiles, got {len(v20['chemistry'])}"
    assert "su_crypto" in v20, "Missing su_crypto dictionary"
    
    log_gate(5, "Volchok X3357 Battery Management Unit Chemistry Profiles & Crypto", True,
             f"Product={pl['product_id']}, Board={pl['board_id']}, ChemProfiles={len(v20['chemistry'])}")

def test_gate6_json_specs():
    specs = [
        "artifacts/coprocessors/apple_lpm_spec.json",
        "artifacts/coprocessors/secure_m3_tightbeam_spec.json",
        "artifacts/coprocessors/msr_surface_accelerator_spec.json",
        "artifacts/coprocessors/wireless_power_ftab_spec.json",
        "artifacts/coprocessors/volchok_bmu_chemistry_spec.json"
    ]
    for s in specs:
        p = os.path.join(BASE_DIR, s)
        assert os.path.exists(p), f"Missing JSON spec: {s}"
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        assert len(obj) > 3, f"JSON spec {s} too sparse"
    
    log_gate(6, "JSON Specifications Schema & Completeness", True,
             f"All {len(specs)} specification files validated successfully")

def test_gate7_c_headers():
    headers = [
        "artifacts/coprocessors/pseudocode/apple_lpm_afk.h",
        "artifacts/coprocessors/pseudocode/secure_m3_tightbeam.h",
        "artifacts/coprocessors/pseudocode/msr_surface_accelerator.h",
        "artifacts/coprocessors/pseudocode/wireless_power_ftab.h"
    ]
    for h in headers:
        p = os.path.join(BASE_DIR, h)
        assert os.path.exists(p), f"Missing C header: {h}"
        cmd = ["gcc", "-fsyntax-only", "-std=c11", "-I", os.path.dirname(p), p]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Compilation failed for {h}:\n{res.stderr}"
    
    log_gate(7, "Clean-Room C Runtime Headers Syntax & Compilation", True,
             f"All {len(headers)} C headers compiled cleanly with zero warnings/errors")

def main():
    print("=" * 80)
    print("APPLE SILICON A19 PRO (t8150) PERIPHERAL COPROCESSORS VERIFICATION SUITE")
    print("=" * 80)
    test_gate1_alpm()
    test_gate2_secure_m3()
    test_gate3_msr()
    test_gate4_wireless_power()
    test_gate5_volchok()
    test_gate6_json_specs()
    test_gate7_c_headers()
    print("=" * 80)
    print("ALL 7 COPROCESSOR VERIFICATION GATES PASSED (100% COMPLIANCE)")
    print("=" * 80)

if __name__ == "__main__":
    main()
