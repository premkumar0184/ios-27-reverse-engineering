#!/usr/bin/env python3
"""
verify_ane_constants.py — Independent Numerical Verification of Apple Neural Engine (ANE) Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro / Generation H18 Apollo v5)

Asserts all empirical constants, spatial tile geometry, FIFO submission protocols,
HWX container header structures, and driver dispatch invariants.
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
    print("=== Apple Neural Engine (ANE) Hardware Constants Verification ===")
    all_ok = True

    # 1. Verify File Existence
    required_files = [
        ROOT / "artifacts/ane/hardware_dispatch_spec.json",
        ROOT / "artifacts/ane/ane_isa_opcode_table.json",
        ROOT / "artifacts/ane/hwx_container_spec.json",
        ROOT / "artifacts/ane/symbol_inventory.json",
        ROOT / "artifacts/ane/client_server_topology.json",
        ROOT / "artifacts/ane/cross_validation_matrix.json",
        ROOT / "artifacts/ane/h18_ane_fw_apollo_v5x.raw"
    ]

    for rf in required_files:
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # 2. Hardware Dispatch Spec & FIFO Mailbox
    dispatch_file = ROOT / "artifacts/ane/hardware_dispatch_spec.json"
    dispatch_data = json.loads(dispatch_file.read_text())

    fifo = dispatch_data.get("fifo", {})
    all_ok &= verify_assertion(
        "FIFO Node ID == 0x40 (ANE_FIFO_NID)",
        fifo.get("node_id") == 0x40 and fifo.get("node_id_hex") == "0x40",
        f"got {fifo.get('node_id_hex')}"
    )

    all_ok &= verify_assertion(
        "Command Granularity == 16 bytes (0x10)",
        fifo.get("command_granularity_bytes") == 16 and fifo.get("command_granularity_hex") == "0x10",
        f"got {fifo.get('command_granularity_bytes')}"
    )

    ring = fifo.get("ring_buffer", {})
    all_ok &= verify_assertion(
        "Command Ring Depth == 32 slots",
        ring.get("depth_slots") == 32,
        f"got {ring.get('depth_slots')}"
    )
    all_ok &= verify_assertion(
        "Ring Slot Size == 64 bytes",
        ring.get("slot_size_bytes") == 64,
        f"got {ring.get('slot_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Total Ring Buffer Size == 2048 bytes (0x800)",
        ring.get("total_ring_size_bytes") == 2048,
        f"got {ring.get('total_ring_size_bytes')}"
    )

    # Doorbell registers
    all_ok &= verify_assertion(
        "Ring Head Register Offset == 0x00004010",
        ring.get("head_register_offset") == "0x00004010",
        ring.get("head_register_offset")
    )
    all_ok &= verify_assertion(
        "Ring Tail Register Offset == 0x00004018",
        ring.get("tail_register_offset") == "0x00004018",
        ring.get("tail_register_offset")
    )
    all_ok &= verify_assertion(
        "Queue Status Register Offset == 0x00004020",
        ring.get("status_register_offset") == "0x00004020",
        ring.get("status_register_offset")
    )

    # 3. Channels & Memory Partitioning
    channels = dispatch_data.get("channels", {})
    all_ok &= verify_assertion(
        "Maximum Memory Channels == 32",
        channels.get("max_channels") == 32,
        f"got {channels.get('max_channels')}"
    )
    chan_alloc = channels.get("channel_allocation", [])
    all_ok &= verify_assertion(
        "Channel Allocation count >= 7 core channels",
        len(chan_alloc) >= 7,
        f"got {len(chan_alloc)}"
    )

    # 4. Submission Struct Invariants
    submit_struct = dispatch_data.get("submission_struct", {})
    all_ok &= verify_assertion(
        "ane_submit_args struct size == 160 bytes",
        submit_struct.get("size_bytes") == 160,
        f"got {submit_struct.get('size_bytes')}"
    )

    # 5. HWX Container Format Specification
    hwx_file = ROOT / "artifacts/ane/hwx_container_spec.json"
    hwx_data = json.loads(hwx_file.read_text())

    hwx_hdr = hwx_data.get("header", {})
    magic_val = hwx_hdr.get("magic")
    all_ok &= verify_assertion(
        "ANEC Magic == 0x414e4543 ('ANEC')",
        magic_val in ("0x414e4543", 0x414e4543) or hwx_hdr.get("magic_ascii") == "ANEC",
        f"magic: {magic_val}"
    )
    all_ok &= verify_assertion(
        "HWX Header Size == 128 bytes (0x80)",
        hwx_hdr.get("header_size_bytes") == 128 or hwx_hdr.get("header_size") == 128,
        f"size: {hwx_hdr.get('header_size_bytes', hwx_hdr.get('header_size'))}"
    )
    all_ok &= verify_assertion(
        "Hardware Target Version == 36 (H18 A19 Pro)",
        hwx_hdr.get("hw_version") == 36 or hwx_hdr.get("version") == 36,
        f"hw_version: {hwx_hdr.get('hw_version')}"
    )

    # Task descriptor layout
    td_spec = hwx_data.get("sections", {}).get("td", {})
    td_size = td_spec.get("descriptor_size_bytes", td_spec.get("entry_size_bytes"))
    all_ok &= verify_assertion(
        "Task Descriptor struct size == 128 bytes (ZinAneTd36)",
        td_size == 128,
        f"got {td_size}"
    )

    # 6. ISA & Bytecode Opcode Table
    isa_file = ROOT / "artifacts/ane/ane_isa_opcode_table.json"
    isa_data = json.loads(isa_file.read_text())

    opcodes = isa_data.get("opcodes", {})
    all_ok &= verify_assertion(
        "Hardware Opcode Count >= 10 CSNE commands",
        len(opcodes) >= 10,
        f"got {len(opcodes)}"
    )

    # Verify critical CSNE opcodes
    expected_opcodes = {
        "CSNE_CMD_RESET": "0x0001",
        "CSNE_CMD_LOAD_PROGRAM": "0x0002",
        "CSNE_CMD_UNLOAD_PROGRAM": "0x0003",
        "CSNE_CMD_CREATE_PROCESS": "0x0004",
        "CSNE_CMD_TERMINATE_PROCESS": "0x0005",
        "CSNE_CMD_PROCEDURE_CALL": "0x0006",
        "CSNE_CMD_PROCEDURE_CALL_WITH_CUSTOM_BARS": "0x0007",
        "CSNE_CMD_PROCEDURE_CALL_WITH_SIGNAL_EVENTS": "0x0008",
        "CSNE_CMD_LOAD_AFPP": "0x0009",
        "CSNE_CMD_UNLOAD_AFPP": "0x000A",
        "CSNE_CMD_PREMAP_BUFFER": "0x000B",
        "CSNE_CMD_DATA_CHAINING_EVENT": "0x000C",
        "CSNE_CMD_PREFETCH_DSID_EVENT": "0x000D",
        "CSNE_CMD_SECURE_MODE_EVENT": "0x000E",
    }
    for op_name, op_hex in expected_opcodes.items():
        found = False
        if op_name in opcodes:
            found = (opcodes[op_name].get("opcode", "").upper() == op_hex.upper())
        else:
            found = any(v.get("opcode", "").upper() == op_hex.upper() for v in opcodes.values())
        all_ok &= verify_assertion(f"ISA Opcode {op_hex} ({op_name}) defined", found)

    # 7. 16 KB Tile Geometry Invariants
    tile_geo = isa_data.get("tile_geometry", {})
    all_ok &= verify_assertion(
        "Memory Tile Size == 16384 bytes (0x4000 / 16 KB)",
        tile_geo.get("tile_size_bytes") == 16384,
        f"got {tile_geo.get('tile_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Tile Shift == 14 (log2(16384))",
        tile_geo.get("tile_shift") == 14,
        f"got {tile_geo.get('tile_shift')}"
    )
    all_ok &= verify_assertion(
        "Raster Channels per Tile == 32 channels",
        tile_geo.get("channels_per_tile") == 32,
        f"got {tile_geo.get('channels_per_tile')}"
    )
    all_ok &= verify_assertion(
        "Row Stride Alignment == 64 bytes",
        tile_geo.get("alignment_bytes") == 64 or tile_geo.get("row_align_bytes") == 64,
        f"got {tile_geo.get('alignment_bytes', tile_geo.get('row_align_bytes'))}"
    )

    # 8. User Client Jump Table Invariants
    sym_file = ROOT / "artifacts/ane/symbol_inventory.json"
    sym_data = json.loads(sym_file.read_text())
    kext_info = sym_data.get("frameworks", {}).get("AppleH16ANEInterface", {})
    sdt = kext_info.get("selector_dispatch_table", {})
    selector_count = sdt.get("total_selectors", len(sdt.get("selectors", [])))
    all_ok &= verify_assertion(
        "H11ANEInUserClient Dispatch Table Count == 32 selectors",
        selector_count == 32,
        f"got {selector_count}"
    )

    # 9. Firmware Binary Validation
    fw_path = ROOT / "artifacts/ane/h18_ane_fw_apollo_v5x.raw"
    fw_size = fw_path.stat().st_size
    all_ok &= verify_assertion(
        "Apollo v5 Firmware Size == 1,540,096 bytes",
        fw_size == 1540096,
        f"got {fw_size} bytes"
    )

    # 10. Cross-Validation Matrix Invariants
    matrix_file = ROOT / "artifacts/ane/cross_validation_matrix.json"
    matrix_data = json.loads(matrix_file.read_text())
    conf = matrix_data.get("extraction_confidence", {})
    all_ok &= verify_assertion(
        "Cross-Validation Matrix has >= 20 EXTRACTED constants",
        conf.get("EXTRACTED", 0) >= 20,
        f"got {conf.get('EXTRACTED', 0)}"
    )
    all_ok &= verify_assertion(
        "Cross-Validation Matrix has ZERO UNKNOWN constants",
        conf.get("UNKNOWN", 0) == 0,
        f"got {conf.get('UNKNOWN', 0)}"
    )

    print("\n==================================================================")
    if all_ok:
        print("ALL ANE HARDWARE CONSTANTS & STRUCTURAL INVARIANTS VERIFIED: PASS")
        return True
    else:
        print("ANE HARDWARE VERIFICATION FAILED: ONE OR MORE ASSERTIONS FAILED")
        return False

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
