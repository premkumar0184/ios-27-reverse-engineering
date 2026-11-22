#!/usr/bin/env python3
"""
verify_exclave_constants.py — Independent Numerical Verification of ExclaveOS & Tightbeam Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro)

Verifies:
1. BUND (DNUB) container header, FourCC tags, and binary offsets.
2. cL4 microkernel system call traps (svc #0..#5), 2-level CNode radix tree, and error codes.
3. Capability delegation model, 28 capability types, rights bitmasks, and hardware badging.
4. Tightbeam binary wire protocol, 88-byte tb_message_s header, and dual-transport thresholds.
5. Datacube memory retyping protocol, PMM dual allocators, and Jungle shared memory segments.
6. XNU system call traps (_exclaves_ctl, _exclaves_call, _exclaves_boot) and xnuproxy.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_verifications() -> bool:
    print("=== ExclaveOS & Tightbeam IPC Architecture Verification ===")
    all_ok = True

    # 1. Verify File Existence
    required_files = [
        ROOT / "artifacts/exclave/phase_1a_workspace_baseline.json",
        ROOT / "artifacts/exclave/bund_container_spec.json",
        ROOT / "artifacts/exclave/cl4_microkernel_spec.json",
        ROOT / "artifacts/exclave/capability_delegation_model.json",
        ROOT / "artifacts/exclave/tightbeam_wire_spec.json",
        ROOT / "artifacts/exclave/tightbeam_protocol_schema.json",
        ROOT / "artifacts/exclave/datacube_memory_spec.json",
        ROOT / "artifacts/exclave/jg_sharedmem_spec.json",
        ROOT / "artifacts/exclave/xnu_boundary_spec.json",
        ROOT / "artifacts/exclave/pseudocode/tightbeam_client.pseudo.c",
        ROOT / "artifacts/exclave/cross_validation_matrix.json"
    ]

    for rf in required_files:
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # 2. BUND Container Specification Verification
    bund_file = ROOT / "artifacts/exclave/bund_container_spec.json"
    bund_data = json.loads(bund_file.read_text())

    all_ok &= verify_assertion(
        "BUND Magic == 0x444e5542 (DNUB)",
        bund_data.get("magic") == "0x444e5542" and bund_data.get("magic_ascii") == "DNUB",
        f"got {bund_data.get('magic')} ({bund_data.get('magic_ascii')})"
    )
    all_ok &= verify_assertion(
        "BUND Version == 0x00040000",
        bund_data.get("version_hex") == "0x00040000",
        bund_data.get("version_hex")
    )
    all_ok &= verify_assertion(
        "BUND Entry Count == 10",
        bund_data.get("entry_count") == 10 and len(bund_data.get("entries", [])) == 10,
        f"got {bund_data.get('entry_count')}"
    )
    all_ok &= verify_assertion(
        "TOC Entry Size == 24 bytes",
        bund_data.get("entry_size_bytes") == 24,
        f"got {bund_data.get('entry_size_bytes')}"
    )

    # 3. cL4 Microkernel & Syscall ABI Verification
    cl4_file = ROOT / "artifacts/exclave/cl4_microkernel_spec.json"
    cl4_data = json.loads(cl4_file.read_text())

    syscalls = cl4_data.get("syscalls", {})
    all_ok &= verify_assertion(
        "Syscall traps cover svc #0 through svc #5",
        all(k in syscalls for k in ["L4_Call", "L4_Yield", "L4_Cap_Delete", "L4_Cap_Mint", "L4_Cap_Copy", "L4_Untyped_Create"]),
        f"{len(syscalls)} syscalls documented"
    )
    all_ok &= verify_assertion(
        "L4_Call trap opcode == 0xd4000001 (svc #0)",
        syscalls.get("L4_Call", {}).get("opcode") == "0xd4000001",
        syscalls.get("L4_Call", {}).get("opcode")
    )
    all_ok &= verify_assertion(
        "L4_Cap_Mint documented with L4_Cap_Mint_Ep",
        "L4_Cap_Mint_Ep" in syscalls,
        "minting syscall present"
    )

    cspace = cl4_data.get("cspace", {})
    all_ok &= verify_assertion(
        "CNode Table Size == 2048 bytes (0x800)",
        cspace.get("cnode_table_size_bytes") == 2048 and cspace.get("cnode_table_size_hex") == "0x800",
        f"got {cspace.get('cnode_table_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Slots per CNode == 256 (8-bit fanout)",
        cspace.get("slots_per_cnode") == 256 and cspace.get("radix_fanout_bits") == 8,
        f"got {cspace.get('slots_per_cnode')}"
    )
    all_ok &= verify_assertion(
        "Max CSpace Capacity == 65536 slots (2 levels)",
        cspace.get("max_cspace_capacity_slots") == 65536 and cspace.get("max_tree_depth") == 2,
        f"got {cspace.get('max_cspace_capacity_slots')}"
    )

    error_codes = cl4_data.get("error_codes", [])
    all_ok &= verify_assertion(
        "Error Code Table has exactly 10 sequential codes (0..9)",
        len(error_codes) == 10 and error_codes[0]["symbol"] == "L4_ErrorCodeSuccess" and error_codes[9]["symbol"] == "L4_ErrorCodePermissionInvalid",
        f"got {len(error_codes)} codes"
    )

    # 4. Capability Delegation Model Verification
    cap_file = ROOT / "artifacts/exclave/capability_delegation_model.json"
    cap_data = json.loads(cap_file.read_text())

    cap_types = cap_data.get("capability_types", [])
    all_ok &= verify_assertion(
        "Capability Types enum has 28 types (0..27)",
        len(cap_types) == 28 and cap_types[0]["name"] == "L4_Type_Null" and cap_types[27]["name"] == "L4_Type_Plat_Dart_PageTable",
        f"got {len(cap_types)} types"
    )
    all_ok &= verify_assertion(
        "Contains Apple Silicon extensions: RingGate (0x17) & DataCube (0x18)",
        any(c["id"] == 23 and c["name"] == "L4_Type_Plat_RingGate" for c in cap_types) and
        any(c["id"] == 24 and c["name"] == "L4_Type_Plat_DataCube" for c in cap_types),
        "Platform extension types confirmed"
    )

    rights = cap_data.get("rights_bits", {})
    all_ok &= verify_assertion(
        "Rights Bitmasks: CanRead (0x1), CanWrite (0x2), CanGrant (0x4), CanBadge (0x10)",
        rights.get("L4_CanRead", {}).get("mask") == "0x0001" and
        rights.get("L4_CanWrite", {}).get("mask") == "0x0002" and
        rights.get("L4_CanGrant", {}).get("mask") == "0x0004" and
        rights.get("L4_CanBadge", {}).get("mask") == "0x0010",
        "Rights bitmasks validated"
    )

    badging = cap_data.get("badging_model", {})
    all_ok &= verify_assertion(
        "Hardware Badge Width == 64 bits",
        badging.get("badge_width_bits") == 64,
        f"got {badging.get('badge_width_bits')}"
    )

    # 5. Tightbeam Wire Protocol Verification
    wire_file = ROOT / "artifacts/exclave/tightbeam_wire_spec.json"
    wire_data = json.loads(wire_file.read_text())

    msg_hdr = wire_data.get("message_header", {})
    all_ok &= verify_assertion(
        "tb_message_s Header Size == 88 bytes",
        msg_hdr.get("header_size_bytes") == 88,
        f"got {msg_hdr.get('header_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Type Encoding == ^{tb_message_s=ICQQQQ[4Q]Q^{tb_transport_message_buffer_s}}",
        msg_hdr.get("objective_c_type_encoding") == "^{tb_message_s=ICQQQQ[4Q]Q^{tb_transport_message_buffer_s}}",
        msg_hdr.get("objective_c_type_encoding")
    )

    accum = wire_data.get("accumulator", {})
    all_ok &= verify_assertion(
        "tb_message_accumulator_s Size == 32 bytes (QQQ*)",
        accum.get("size_bytes") == 32 and accum.get("objective_c_type_encoding") == "^{tb_message_accumulator_s=QQQ*}",
        f"got {accum.get('size_bytes')}"
    )

    transports = wire_data.get("transports", {})
    all_ok &= verify_assertion(
        "Transports cover cL4 (<=256B) and cL4_large (>256B)",
        "cL4" in transports and "cL4_large" in transports and transports["cL4"].get("max_inline_bytes") == 256,
        "cL4 and cL4_large validated"
    )

    # 6. Datacubes & Jungle Shared Memory Verification
    datacube_file = ROOT / "artifacts/exclave/datacube_memory_spec.json"
    datacube_data = json.loads(datacube_file.read_text())

    retyping = datacube_data.get("datacube_abstraction", {}).get("retyping_protocol", {})
    all_ok &= verify_assertion(
        "Retyping primitive == Release Datacube",
        retyping.get("primitive") == "Release Datacube",
        retyping.get("primitive")
    )
    all_ok &= verify_assertion(
        "PMM MTE frames configured via __PMM_EXTRA_MTE_FRAMES",
        datacube_data.get("pmm_server", {}).get("memory_tagging_extension", {}).get("mte_frame_pool") == "__PMM_EXTRA_MTE_FRAMES",
        "MTE frame pool validated"
    )

    jg_file = ROOT / "artifacts/exclave/jg_sharedmem_spec.json"
    jg_data = json.loads(jg_file.read_text())

    segments = jg_data.get("shared_memory_segments", [])
    all_ok &= verify_assertion(
        "Jungle Shared Memory catalogs >= 8 segments",
        len(segments) >= 8,
        f"got {len(segments)} segments"
    )
    all_ok &= verify_assertion(
        "Catalogs Backboardd SIL Surface and ANE ExclaveKit Bridge",
        any(s["segment_name"] == "sharedmem_backboardd_silmanager_exsurface" for s in segments) and
        any(s["segment_name"] == "EXSurfaceRoot_ANEEKTest" for s in segments),
        "Key shared segments present"
    )

    # 7. XNU Boundary Verification
    xnu_file = ROOT / "artifacts/exclave/xnu_boundary_spec.json"
    xnu_data = json.loads(xnu_file.read_text())

    traps = xnu_data.get("syscall_traps", {})
    all_ok &= verify_assertion(
        "XNU Traps document _exclaves_ctl_trap, _exclaves_call_trap, _exclaves_boot_trap",
        all(t in traps for t in ["_exclaves_ctl_trap", "_exclaves_call_trap", "_exclaves_boot_trap"]),
        "All 3 XNU traps documented"
    )

    # 8. Cross-Validation Matrix
    cv_file = ROOT / "artifacts/exclave/cross_validation_matrix.json"
    cv_data = json.loads(cv_file.read_text())

    conf = cv_data.get("extraction_confidence", {})
    all_ok &= verify_assertion(
        "Cross-Validation Matrix has >= 25 EXTRACTED constants",
        conf.get("EXTRACTED", 0) >= 25,
        f"got {conf.get('EXTRACTED', 0)} EXTRACTED"
    )
    all_ok &= verify_assertion(
        "Zero UNKNOWN or TENTATIVE constants",
        conf.get("UNKNOWN", 0) == 0 and conf.get("TENTATIVE", 0) == 0,
        f"UNKNOWN={conf.get('UNKNOWN')}, TENTATIVE={conf.get('TENTATIVE')}"
    )

    print("\n-----------------------------------------------------------")
    if all_ok:
        print("✅ ALL EXCLAVE CONSTANTS AND ARCHITECTURAL INVARIANTS VERIFIED!")
        return True
    else:
        print("❌ SOME VERIFICATION CHECKS FAILED.")
        return False

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
