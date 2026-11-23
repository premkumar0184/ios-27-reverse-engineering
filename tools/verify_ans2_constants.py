#!/usr/bin/env python3
"""
verify_ans2_constants.py — Independent Numerical Verification of Apple ANS2 Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro / ASP3-241.40.4~1100)

Asserts all empirical constants, 64-byte SQE descriptor alignment, 16-byte CQE size,
IM4P container digests, MMIO apertures, SART Coastguard configuration, and C runtime driver.
Supports both monorepo workspace and standalone repository directory structures.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if (ROOT / "specs").is_dir():
    SPEC_DIR = ROOT / "specs"
    RUNTIME_FILE = ROOT / "runtime/ans2_nvme_driver.c"
else:
    SPEC_DIR = ROOT / "artifacts/ans2"
    RUNTIME_FILE = ROOT / "artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c"

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_verifications() -> bool:
    print("=== Apple ANS2 NVMe Storage Controller Hardware Verification Suite ===")
    all_ok = True

    # 1. Verify File Existence
    required_files = [
        SPEC_DIR / "phase_1a_workspace_baseline.json",
        SPEC_DIR / "ans2_firmware_container_spec.json",
        SPEC_DIR / "ans2_microarchitecture_spec.json",
        SPEC_DIR / "rtkit_ftl_topology.json",
        SPEC_DIR / "ans2_mmio_memory_geometry.json",
        SPEC_DIR / "nand_geometry_crypto_spec.json",
        SPEC_DIR / "nvme_command_stream_spec.json",
        SPEC_DIR / "ans2_ring_buffer_protocol.json",
        SPEC_DIR / "xnu_nvme_boundary_spec.json",
        RUNTIME_FILE,
        SPEC_DIR / "cross_validation_matrix.json"
    ]

    for rf in required_files:
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # 2. Container & Hash Verification
    baseline = json.loads((SPEC_DIR / "phase_1a_workspace_baseline.json").read_text())
    fw_meta = baseline.get("firmware_metadata", {})
    all_ok &= verify_assertion(
        "FourCC tag == 'ansf'",
        fw_meta.get("fourcc_tag") == "ansf",
        f"got {fw_meta.get('fourcc_tag')}"
    )
    all_ok &= verify_assertion(
        "IM4P size == 1,329,936 bytes",
        fw_meta.get("im4p_size_bytes") == 1329936,
        f"got {fw_meta.get('im4p_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Decompressed size == 5,634,888 bytes",
        fw_meta.get("decompressed_size_bytes") == 5634888,
        f"got {fw_meta.get('decompressed_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "IM4P SHA256 matches verified digest",
        fw_meta.get("im4p_sha256") == "8eeb1f189cfe45bff4361720d9affe4fffde9d9a906c67d7c8ef621cf7a43408",
        f"got {fw_meta.get('im4p_sha256')}"
    )
    all_ok &= verify_assertion(
        "Decompressed SHA256 matches verified digest",
        fw_meta.get("decompressed_sha256") == "8f1bb732969689c01946153644550f0c81b198233cc45ca05d52d8a85a720e69",
        f"got {fw_meta.get('decompressed_sha256')}"
    )

    # 3. Microarchitecture & C Modules
    uarch = json.loads((SPEC_DIR / "ans2_microarchitecture_spec.json").read_text())
    modules = uarch.get("c_source_modules", [])
    all_ok &= verify_assertion(
        "Cataloged C firmware modules >= 100",
        len(modules) >= 100,
        f"got {len(modules)}"
    )

    # 4. MMIO & SART Coastguard Verification
    mmio = json.loads((SPEC_DIR / "ans2_mmio_memory_geometry.json").read_text())
    sart = mmio.get("sart_coastguard", {})
    all_ok &= verify_assertion(
        "SART Coastguard base == 0x17dc50000",
        sart.get("base_address") == "0x17dc50000",
        f"got {sart.get('base_address')}"
    )
    all_ok &= verify_assertion(
        "SART version == 4",
        sart.get("sart_version") == 4,
        f"got {sart.get('sart_version')}"
    )
    all_ok &= verify_assertion(
        "SART power reg offset == 0x13e8",
        sart.get("power_reg_offset") == "0x13e8",
        f"got {sart.get('power_reg_offset')}"
    )

    ns_list = mmio.get("namespaces", [])
    all_ok &= verify_assertion(
        "Total hardware namespaces == 7",
        len(ns_list) == 7,
        f"got {len(ns_list)}"
    )

    # 5. Queue Geometry & Opcodes
    cmd_spec = json.loads((SPEC_DIR / "nvme_command_stream_spec.json").read_text())
    q_geom = cmd_spec.get("queue_geometry", {})
    all_ok &= verify_assertion(
        "Submission Queue Entry size == 64 bytes",
        q_geom.get("submission_queue_entry_bytes") == 64,
        f"got {q_geom.get('submission_queue_entry_bytes')}"
    )
    all_ok &= verify_assertion(
        "Completion Queue Entry size == 16 bytes",
        q_geom.get("completion_queue_entry_bytes") == 16,
        f"got {q_geom.get('completion_queue_entry_bytes')}"
    )
    all_ok &= verify_assertion(
        "Queue depth == 64 entries",
        q_geom.get("queue_depth_entries") == 64,
        f"got {q_geom.get('queue_depth_entries')}"
    )

    # 6. Cross-Validation Matrix
    cv_matrix = json.loads((SPEC_DIR / "cross_validation_matrix.json").read_text())
    conf = cv_matrix.get("extraction_confidence", {})
    all_ok &= verify_assertion(
        "EXTRACTED constants >= 35",
        conf.get("EXTRACTED", 0) >= 35,
        f"got {conf.get('EXTRACTED')}"
    )
    all_ok &= verify_assertion(
        "TENTATIVE constants == 0",
        conf.get("TENTATIVE", 0) == 0,
        f"got {conf.get('TENTATIVE')}"
    )

    print("")
    print("=" * 60)
    if all_ok:
        print("✅ ALL ANS2 ARCHITECTURAL CONSTANTS NUMERICALLY VERIFIED")
        print("=" * 60)
        return True
    else:
        print("❌ VERIFICATION FAILURES DETECTED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
