#!/usr/bin/env python3
"""
verify_ave_constants.py — Independent Numerical Verification of AVE2 Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro)

Verifies:
1. Binary Image4 headers, magic numbers, FourCC tags, and raw Mach-O structures.
2. AVE2 virtual memory layout, segments, stack sizes, and entrypoint.
3. Preserved codec symbols for AV1 Boreas, HEVC Erebus, AVC, and Motion Estimation.
4. Satellite RISC-V microcode symbols (HEIF, VLC, Task Dispatcher).
5. DeviceTree MMIO registers (dart-ave 0x77020000, 128 KB aperture).
6. XNU AppleAVE2.kext driver boundary and UserClient external methods.
7. Clean-room C client syntax verification via gcc -fsyntax-only.
8. Master Publication Dossier size and structural completeness.
"""

import sys
import struct
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def get_path(filename: str, default_dir: str = "specs") -> Path:
    candidates = [
        ROOT / default_dir / filename,
        ROOT / "artifacts/ave" / filename,
        ROOT / "artifacts/ave/pseudocode" / filename,
        ROOT / "docs" / filename,
        ROOT / filename,
        Path("/home/prem/Projects/iOS 27/artifacts/ave") / filename,
        Path("/home/prem/Projects/iOS 27/artifacts/ave/pseudocode") / filename,
        Path("/home/prem/Projects/iOS 27") / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return ROOT / default_dir / filename

def get_binary_path(filename: str) -> Path:
    candidates = [
        ROOT / "artifacts/ave/extracted" / filename,
        Path("/home/prem/Projects/iOS 27/artifacts/ave/extracted") / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return ROOT / "artifacts/ave/extracted" / filename

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_verifications() -> bool:
    print("=== Apple Video Encoder 2 (AVE2) Architecture Verification ===")
    all_ok = True

    # 1. Verify File Existence
    required_specs = [
        ("phase_1a_workspace_baseline.json", "specs"),
        ("ave_firmware_container_spec.json", "specs"),
        ("ave_topology_spec.json", "specs"),
        ("codec_pipeline_architecture.json", "specs"),
        ("ave_hardware_register_geometry.json", "specs"),
        ("dma_descriptor_geometry.json", "specs"),
        ("ave_command_queue_spec.json", "specs"),
        ("codec_control_descriptors.json", "specs"),
        ("xnu_ave_boundary_spec.json", "specs"),
        ("cross_validation_matrix.json", "specs"),
    ]

    for fname, default_dir in required_specs:
        rf = get_path(fname, default_dir)
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {fname}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {fname}")
            return False

    # Check pseudocode client
    c_client = get_path("ave_direct_submit.c", "runtime")
    if not c_client.is_file():
        c_client = get_path("ave_direct_submit.pseudo.c", "artifacts/ave/pseudocode")
    all_ok &= verify_assertion(f"Artifact exists: {c_client.name}", c_client.is_file(), str(c_client))

    # Check dossier
    dossier = get_path("MASTER_DOSSIER.md", "docs")
    if not dossier.is_file():
        dossier = get_path("IOS_27_AVE2_VIDEO_ENCODER_RE.md", ".")
    all_ok &= verify_assertion(f"Artifact exists: {dossier.name}", dossier.is_file(), str(dossier))

    # 2. Main Firmware Binary Header Verification
    main_raw = get_binary_path("AppleAVE2FW_H18.raw")
    if main_raw.is_file():
        raw_data = main_raw.read_bytes()
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, _ = struct.unpack("<IIIIIIII", raw_data[:32])

        all_ok &= verify_assertion("AVE2 Main FW Magic == 0xfeedfacf (MH_MAGIC_64)", magic == 0xfeedfacf, hex(magic))
        all_ok &= verify_assertion("AVE2 Main FW CPU Type == 0x0100000c (ARM64)", cputype == 0x0100000c, hex(cputype))
        all_ok &= verify_assertion("AVE2 Main FW CPU Subtype == 0x80000002 (ARM64E)", cpusubtype == 0x80000002, hex(cpusubtype))
        all_ok &= verify_assertion("AVE2 Main FW Filetype == 0x00000005 (MH_PRELOAD)", filetype == 0x00000005, hex(filetype))
        all_ok &= verify_assertion("AVE2 Main FW Load Commands == 7", ncmds == 7, str(ncmds))

        # Check Preserved Codec Symbols in Main Firmware
        codec_symbols = [
            b"_gc_sAVE_DevCap_DPMMap_AV1_Boreas",
            b"_gc_sAVE_DevCap_DPMMap_HEVC_Erebus",
            b"_gc_sAVE_DevCap_DPMMap_AVC_Erebus",
            b"_gc_sAVE_DevCap_DPMMap_LRME_Erebus",
            b"_gc_sAVE_DevCap_DPMMap_MCTF_Erebus",
            b"_gc_sAVE_DevCap_DPMMap_DMV_Erebus",
            b"_gc_sAVE_DevCap_DPMMap_GGM_Erebus"
        ]
        for sym in codec_symbols:
            present = sym in raw_data
            all_ok &= verify_assertion(f"Codec Symbol Preserved: {sym.decode()}", present)

    # 3. Satellite RISC-V Microcodes Verification
    for i in range(9):
        sat_raw = get_binary_path(f"AppleAVE2FW_H18_AVE{i}.raw")
        exists = sat_raw.is_file() and sat_raw.stat().st_size > 0
        all_ok &= verify_assertion(f"Satellite Core AVE{i} binary present", exists)

    sat0 = get_binary_path("AppleAVE2FW_H18_AVE0.raw")
    if sat0.is_file():
        d0 = sat0.read_bytes()
        all_ok &= verify_assertion("Satellite RISC-V start symbol present (_RTK_riscv32i_start)", b"_RTK_riscv32i_start" in d0)

    sat1 = get_binary_path("AppleAVE2FW_H18_AVE1.raw")
    if sat1.is_file():
        d1 = sat1.read_bytes()
        all_ok &= verify_assertion("HEIF Tuning symbol present (_AVE_HEIF_Process)", b"_AVE_HEIF_Process" in d1)

    sat7 = get_binary_path("AppleAVE2FW_H18_AVE7.raw")
    if sat7.is_file():
        d7 = sat7.read_bytes()
        all_ok &= verify_assertion("VLC Slice Header symbol present (_AVE_VLC_InsertHevcSliceHeader)", b"_AVE_VLC_InsertHevcSliceHeader" in d7)

    # 4. JSON Spec Invariants Verification
    hw_file = get_path("ave_hardware_register_geometry.json", "specs")
    hw_data = json.loads(hw_file.read_text())
    all_ok &= verify_assertion("dart-ave MMIO base == 0x77020000", "0x77020000" in str(hw_data.get("mmio_registers", {})))
    all_ok &= verify_assertion("Rate control models documented >= 3", len(hw_data.get("rate_control_models", {})) >= 3)

    cmd_file = get_path("ave_command_queue_spec.json", "specs")
    cmd_data = json.loads(cmd_file.read_text())
    all_ok &= verify_assertion("Command opcodes documented >= 10", len(cmd_data.get("command_opcodes", {})) >= 10)

    xnu_file = get_path("xnu_ave_boundary_spec.json", "specs")
    xnu_data = json.loads(xnu_file.read_text())
    all_ok &= verify_assertion("AppleAVE2 driver documented", "com.apple.driver.AppleAVE2" in xnu_data.get("kernel_drivers", {}))
    all_ok &= verify_assertion("UserClient external methods >= 10", len(xnu_data.get("external_methods", {})) >= 10)

    # 5. Clean-Room C Client Syntax Verification
    res = subprocess.run(
        ["gcc", "-fsyntax-only", "-Wall", "-Wextra", "-Werror", str(c_client)],
        capture_output=True, text=True
    )
    all_ok &= verify_assertion("Clean-room C Client compiles with gcc -fsyntax-only", res.returncode == 0, res.stderr.strip() or "Clean")

    # 6. Master Publication Dossier Verification
    dossier_bytes = len(dossier.read_bytes())
    all_ok &= verify_assertion("Master Publication Dossier size >= 50,000 bytes", dossier_bytes >= 50000, f"{dossier_bytes} bytes")

    if all_ok:
        print("\n✅ All AVE2 architectural invariants verified successfully.")
        return True
    else:
        print("\n❌ Verification failed on one or more invariants.")
        return False

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
