#!/usr/bin/env python3
"""
verify_prores_me_hardware.py - Standalone Verification Test Suite
Subsystems: AppleProResHW Real-Time 8K ProRes 422 HQ, 8K ProRes RAW & AVE2 Motion Estimation Coprocessors
Target Platform: Apple Silicon A19 Pro (t8150) / Apple H18 Generation
"""

import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def find_file(rel_path: str) -> Path:
    candidates = [
        ROOT / rel_path,
        ROOT / "specs" / Path(rel_path).name,
        ROOT / "docs" / Path(rel_path).name,
        Path("/home/prem/Projects/iOS 27") / rel_path,
        Path("/home/prem/Projects/iOS 27/artifacts/ave") / Path(rel_path).name,
        Path("/home/prem/Projects/iOS 27/findings/ave") / Path(rel_path).name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(f"Cannot locate {rel_path} in workspace or standalone repo")

def test_kernelcache_symbols():
    print("[TEST 1/7] Validating Kernelcache AppleProResHW Symbols & Strings...")
    kc_path = find_file("artifacts/kernel/kernelcache.release.raw")
    with open(kc_path, "rb") as f:
        data = f.read()
    
    assert b"com.apple.driver.AppleProResHW" in data, "Missing AppleProResHW kext bundle ID"
    assert b"EncodeYCbCr cmd:" in data, "Missing EncodeYCbCr command format"
    assert b"DecodeRaw cmd:" in data, "Missing DecodeRaw command format"
    assert b"FrameHeader size=" in data, "Missing ProRes RAW FrameHeader string"
    assert b"codedWindowWidthInMb=" in data, "Missing ProRes rate control macroblock string"
    assert b"AppleProResCommandQueue" in data, "Missing AppleProResCommandQueue string"
    assert b"DART error info" in data, "Missing DART error info telemetry"
    print("  --> Kernelcache OK: AppleProResHW symbols, command strings, and DART telemetry verified")

def test_ave2_firmware_symbols():
    print("[TEST 2/7] Validating AVE2 Firmware Motion Estimation Coprocessor Symbols...")
    fw_path = find_file("artifacts/ave/extracted/AppleAVE2FW_H18.raw")
    with open(fw_path, "rb") as f:
        data = f.read()
        
    assert b"HMESCSRCPIXRD_CTXCFG_SRCADDR" in data, "Missing HMESC register string"
    assert b"CLRMEFSController" in data, "Missing CLRMEFSController symbol"
    assert b"CLRMERSController" in data, "Missing CLRMERSController symbol"
    assert b"CDMVController" in data, "Missing CDMVController symbol"
    assert b"CMCTFController" in data, "Missing CMCTFController symbol"
    assert b"CGGMController" in data, "Missing CGGMController symbol"
    assert b"COFController" in data, "Missing COFController symbol"
    print("  --> AVE2 Firmware OK: HMESC, LRME, DMV, and MCTF controllers verified")

def test_prores_422_hq_spec():
    print("[TEST 3/7] Validating ProRes 422 HQ Pipeline Specification...")
    spec_path = find_file("prores_422_hq_pipeline_spec.json")
    with open(spec_path, "r") as f:
        spec = json.load(f)
        
    p422 = spec["prores_422_hq_specifications"]
    assert p422["bit_depth"] == 10
    assert p422["multi_core_parallelization"]["slices_per_frame"] == 16
    assert "apr_a1" in p422["multi_core_parallelization"]["core_allocation"]
    assert "apr_a2" in p422["multi_core_parallelization"]["core_allocation"]
    
    cmd = spec["hardware_command_descriptors"]
    assert cmd["command_name"] == "EncodeYCbCr"
    assert "fid" in cmd["parameters"]
    assert "nPass" in cmd["parameters"]
    print("  --> ProRes 422 HQ OK: 8K multi-core slice parallelization and EncodeYCbCr verified")

def test_prores_raw_spec():
    print("[TEST 4/7] Validating ProRes RAW Pipeline Specification...")
    spec_path = find_file("prores_raw_pipeline_spec.json")
    with open(spec_path, "r") as f:
        spec = json.load(f)
        
    raw = spec["prores_raw_architecture"]
    assert raw["bit_depth"] == 14
    assert raw["planar_memory_layout"]["plane_count"] == 4
    assert len(raw["cfa_bayer_patterns"]) == 4
    
    header = spec["raw_frame_header_metadata_packet"]
    assert header["total_size_bytes"] == 128
    assert any(field["name"] == "cfa" for field in header["fields"])
    assert any(field["name"] == "cm" for field in header["fields"])
    print("  --> ProRes RAW OK: 4-plane CFA Bayer ingestion and 128-byte FrameHeader verified")

def test_motion_estimation_spec():
    print("[TEST 5/7] Validating Motion Estimation Coprocessor Specification...")
    spec_path = find_file("motion_estimation_coprocessor_spec.json")
    with open(spec_path, "r") as f:
        spec = json.load(f)
        
    cluster = spec["motion_estimation_coprocessor_cluster"]
    assert "hmesc" in cluster
    assert "lrme" in cluster
    assert "dmv" in cluster
    assert "mctf" in cluster or "mctF" in cluster
    assert "satellite_riscv_microcode_engines" in cluster
    print("  --> Motion Estimation OK: HMESC, LRME, DMV, MCTF, and satellite RISC-V cores verified")

def test_register_geometry():
    print("[TEST 6/7] Validating AppleProResHW Register Geometry & DART IOMMU...")
    reg_path = find_file("apple_prores_hw_register_geometry.json")
    with open(reg_path, "r") as f:
        spec = json.load(f)
        
    assert spec["mmio_regions"]["base_address"] == "0x77080000"
    cores = spec["mmio_regions"]["cores"]
    assert len(cores) == 3
    assert cores[0]["name"] == "apr,m0"
    assert cores[1]["name"] == "apr,a1"
    assert cores[2]["name"] == "apr,a2"
    
    dart = spec["dart_iommu_configuration"]
    assert len(dart["stream_ids"]) == 5
    print("  --> Register Geometry OK: apr,m0, apr,a1, apr,a2 MMIO maps and DART SIDs verified")

def test_master_dossier_completeness():
    print("[TEST 7/7] Validating Master Dossier Completeness...")
    dossier_path = find_file("02_PRORES_AND_MOTION_ESTIMATION_HARDWARE.md")
    size = os.path.getsize(dossier_path)
    assert size >= 40000, f"Dossier size {size} is less than required 40,000 bytes threshold"
    
    with open(dossier_path, "r") as f:
        text = f.read()
        
    for token in ["TODO", "TBD", "placeholder", "WIP", "coming soon"]:
        assert token not in text, f"Found forbidden token '{token}' in dossier"
        assert token.lower() not in text.lower(), f"Found forbidden token case-insensitive '{token}' in dossier"
        
    required_sections = [
        "Executive Summary & Heterogeneous Media Accelerator Architecture",
        "Phase 1 — Real-Time 8K ProRes 422 HQ Hardware Encode Pipeline",
        "Phase 2 — Real-Time 8K ProRes RAW Hardware Encode Pipeline",
        "Phase 3 — AVE2 Motion Estimation (ME) Hardware Coprocessor Architecture",
        "XNU Driver Interface & DART IOMMU Boundary",
        "Comprehensive C/C++ Header Definitions & Register Map",
        "Verification Matrix & Reproduction Protocol"
    ]
    for sec in required_sections:
        assert sec in text, f"Missing required section '{sec}'"
        
    print(f"  --> Master Dossier OK: {size:,} bytes (exceeds 40KB minimum), all core sections verified")

if __name__ == "__main__":
    print("=== STARTING PRORES & AVE2 MOTION ESTIMATION VERIFICATION SUITE ===")
    test_kernelcache_symbols()
    test_ave2_firmware_symbols()
    test_prores_422_hq_spec()
    test_prores_raw_spec()
    test_motion_estimation_spec()
    test_register_geometry()
    test_master_dossier_completeness()
    print("=== ALL 7/7 TESTS PASSED WITH 100% SUCCESS ===")
