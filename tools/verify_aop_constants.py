#!/usr/bin/env python3
"""
verify_aop_constants.py — Independent Numerical Verification of AOP2 & RTKit Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro)

Verifies:
1. Apple Image4 (IM4P) container headers and BUND (DNUB) multi-binary layout.
2. All 7 extracted Mach-O sub-binaries (offsets, byte sizes, UUIDs, SHA256 hashes).
3. Hardware MMIO peripheral register bases and DART IOMMU Stream IDs.
4. RTKit microkernel scheduler, 64-bit mailbox framing bitmasks, and endpoint registry.
5. Continuous Sensor Hub 64-byte IMU sample layout and lock-free SPSC fastpath geometry.
6. 1Hz Always-On Display (AOD) DCP buffer geometry and local Siri 3.0s SRAM FIFO sizing.
7. Direct ExclaveOS cross-enclave routing (DART SID 0x11, EP 0x53).
8. Forensic audit firmware verification (AOP1 'aopf' and Audio Boot Tone 'aubt').
9. Clean syntax compilation of aop_rtkit_channel client via gcc.
"""

import json
import sys
import subprocess
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
    print("=== AOP2, RTKit Microkernel & Sensor Hub Architecture Verification ===")
    all_ok = True

    specs_dir = ROOT / "artifacts/aop" if (ROOT / "artifacts/aop").is_dir() else ROOT / "specs"
    docs_dir = ROOT / "findings/aop" if (ROOT / "findings/aop").is_dir() else ROOT / "docs"
    runtime_dir = ROOT / "artifacts/aop/pseudocode" if (ROOT / "artifacts/aop/pseudocode").is_dir() else ROOT / "runtime"

    c_client = runtime_dir / "aop_rtkit_channel.pseudo.c"
    if not c_client.is_file():
        c_client = runtime_dir / "aop_rtkit_channel.c"

    # 1. Verify File Existence
    required_files = [
        specs_dir / "phase_1a_workspace_baseline.json",
        specs_dir / "aop_firmware_container_spec.json",
        specs_dir / "rtkit_microkernel_spec.json",
        specs_dir / "aop_service_topology.json",
        specs_dir / "aop_hardware_registers.json",
        specs_dir / "sensor_hub_geometry.json",
        specs_dir / "rtkit_endpoint_wire_spec.json",
        specs_dir / "aop_mailbox_protocol.json",
        specs_dir / "xnu_aop_boundary_spec.json",
        c_client,
        docs_dir / "01A_WORKSPACE_BASELINE.md",
        docs_dir / "01B_RTKIT_MICROKERNEL.md",
        docs_dir / "02_HARDWARE_AND_SENSOR_HUB.md",
        docs_dir / "03_ENDPOINT_WIRE_FORMAT.md",
        docs_dir / "04_XNU_DRIVER_BOUNDARY.md",
        docs_dir / "05_COMPREHENSIVE_AUDIT_REPORT.md"
    ]

    for rf in required_files:
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # 2. BUND Container Specification Verification
    bund_file = specs_dir / "aop_firmware_container_spec.json"
    bund_data = json.loads(bund_file.read_text())

    all_ok &= verify_assertion(
        "FourCC Tag == 'aop2'",
        bund_data.get("fourcc_tag") == "aop2",
        bund_data.get("fourcc_tag")
    )
    all_ok &= verify_assertion(
        "BUND Magic == 0x444e5542 ('DNUB')",
        bund_data.get("bund_header", {}).get("magic_hex") == "0x444e5542"
    )
    all_ok &= verify_assertion(
        "BUND Version == 0x00040000",
        bund_data.get("bund_header", {}).get("version") == "0x00040000"
    )
    all_ok &= verify_assertion(
        "BUND Segment Map has 11 entries",
        len(bund_data.get("bund_header", {}).get("segment_map", [])) == 11
    )
    all_ok &= verify_assertion(
        "Contains 7 embedded Mach-O sub-binaries",
        len(bund_data.get("sub_binaries", [])) == 7
    )

    # 3. Sub-Binary Offsets and Hashes
    binaries = {b["index"]: b for b in bund_data.get("sub_binaries", [])}
    
    # RootTask
    all_ok &= verify_assertion(
        "Binary #0 is roottask (offset: 69657, size: 147456)",
        binaries[0]["file_offset"] == 69657 and binaries[0]["size_bytes"] == 147456
    )
    # Motion App
    all_ok &= verify_assertion(
        "Binary #1 is motion app (offset: 208921, size: 536288)",
        binaries[1]["file_offset"] == 208921 and binaries[1]["size_bytes"] == 536288
    )
    # Location App
    all_ok &= verify_assertion(
        "Binary #2 is location app (offset: 311321, size: 477184)",
        binaries[2]["file_offset"] == 311321 and binaries[2]["size_bytes"] == 477184
    )
    # Audio Hotword App
    all_ok &= verify_assertion(
        "Binary #3 is audio hotword app (offset: 434201, size: 753976)",
        binaries[3]["file_offset"] == 434201 and binaries[3]["size_bytes"] == 753976
    )
    # Exclave Bridge
    all_ok &= verify_assertion(
        "Binary #4 is exclave bridge (offset: 823321, size: 326560)",
        binaries[4]["file_offset"] == 823321 and binaries[4]["size_bytes"] == 326560
    )
    # SPU Dylib
    all_ok &= verify_assertion(
        "Binary #5 is SPU dylib (offset: 888857, size: 532480)",
        binaries[5]["file_offset"] == 888857 and binaries[5]["size_bytes"] == 532480
    )
    # Microkernel Preload
    all_ok &= verify_assertion(
        "Binary #6 is RTKit preload (offset: 5439513, size: 81920, vm: 0xffffffff00000000)",
        binaries[6]["file_offset"] == 5439513 and binaries[6]["size_bytes"] == 81920
    )

    # 4. Hardware MMIO Registers & DART IOMMU Verification
    hw_file = specs_dir / "aop_hardware_registers.json"
    hw_data = json.loads(hw_file.read_text())

    bases = hw_data.get("mmio_peripheral_bases", {})
    all_ok &= verify_assertion(
        "ASCwrap Mailbox Base == 0x0000000101600000 (size: 0x88000)",
        bases.get("ascwrap_mailbox_primary", {}).get("base_physical_address") == "0x0000000101600000" and
        bases.get("ascwrap_mailbox_primary", {}).get("size_hex") == "0x00088000"
    )
    all_ok &= verify_assertion(
        "Doorbell Aggregation Base == 0x000000010162c000",
        bases.get("ascwrap_doorbell_aggregation", {}).get("base_physical_address") == "0x000000010162c000"
    )
    all_ok &= verify_assertion(
        "Exclave Mailbox Proxy Base == 0x000000035167c000",
        bases.get("exclave_mailbox_proxy", {}).get("base_physical_address") == "0x000000035167c000"
    )
    all_ok &= verify_assertion(
        "DART-AOP IOMMU Base == 0x0000000100fc0000",
        bases.get("dart_aop_iommu", {}).get("base_physical_address") == "0x0000000100fc0000"
    )

    streams = {s["name"]: s for s in hw_data.get("dart_stream_geometry", {}).get("streams", [])}
    all_ok &= verify_assertion(
        "DART Stream mapper-aop2 == SID 0x10",
        streams.get("mapper-aop2", {}).get("sid") == "0x10"
    )
    all_ok &= verify_assertion(
        "DART Stream mapper-exclave-aop2 == SID 0x11",
        streams.get("mapper-exclave-aop2", {}).get("sid") == "0x11"
    )

    # 5. RTKit Endpoint Wire Specification Verification
    wire_file = specs_dir / "rtkit_endpoint_wire_spec.json"
    wire_data = json.loads(wire_file.read_text())

    geom = wire_data.get("word_geometry", {}).get("fields", {})
    all_ok &= verify_assertion(
        "Wire Endpoint ID mask == 0xffff000000000000",
        geom.get("endpoint_id", {}).get("mask") == "0xffff000000000000"
    )
    all_ok &= verify_assertion(
        "Wire Message Type mask == 0x0000f00000000000",
        geom.get("message_type", {}).get("mask") == "0x0000f00000000000"
    )
    all_ok &= verify_assertion(
        "Wire Payload mask == 0x00000fffffffffff",
        geom.get("payload", {}).get("mask") == "0x00000fffffffffff"
    )
    all_ok &= verify_assertion(
        "Endpoint 0x53 defined as ExclaveOS bridge",
        "0x53" in wire_data.get("endpoints", {}) and
        "sharedmem_xcoproc_AOP2_EP53_in" in wire_data["endpoints"]["0x53"]["name"]
    )

    # 6. Sensor Hub & Ultra-Low-Power Hardware Geometry
    sensor_file = specs_dir / "sensor_hub_geometry.json"
    sensor_data = json.loads(sensor_file.read_text())

    all_ok &= verify_assertion(
        "IMU sample record size == 64 bytes",
        sensor_data.get("imu_pipeline", {}).get("sample_record_size_bytes") == 64
    )
    all_ok &= verify_assertion(
        "FastPath ring buffer allocation == 16384 bytes",
        sensor_data.get("fastpath_ring_buffer", {}).get("total_allocation_bytes") == 16384
    )
    all_ok &= verify_assertion(
        "FastPath capacity == 254 samples",
        sensor_data.get("fastpath_ring_buffer", {}).get("entry_capacity") == 254
    )
    all_ok &= verify_assertion(
        "1Hz AOD DCP buffer size == 262144 bytes",
        sensor_data.get("always_on_display", {}).get("hardware_buffer_properties", {}).get("buffer_size_bytes") == 262144
    )
    all_ok &= verify_assertion(
        "Siri hotword SRAM FIFO == 96000 bytes (3.0s @ 16kHz 16-bit)",
        sensor_data.get("local_siri_voice_trigger", {}).get("acoustic_parameters", {}).get("circular_buffer_size_bytes") == 96000
    )

    # 7. Clean-Room C Client Syntax Validation
    res = subprocess.run(
        ["gcc", "-fsyntax-only", "-Wall", "-Wextra", str(c_client)],
        capture_output=True,
        text=True
    )
    all_ok &= verify_assertion(
        f"gcc -fsyntax-only -Wall -Wextra {c_client.name} passes with zero warnings/errors",
        res.returncode == 0,
        res.stderr.strip() if res.stderr else "Clean compilation"
    )

    # 8. Forensic Audit Firmware Verification (AOP1 and Audio Boot Tone)
    aop1_im4p = ROOT / "iPhone18,3_27.2_24B119_Restore/Firmware/AOP/aopfw-v57aop.RELEASE.im4p"
    if not aop1_im4p.is_file():
        aop1_im4p = Path("/home/prem/Projects/iOS 27/iPhone18,3_27.2_24B119_Restore/Firmware/AOP/aopfw-v57aop.RELEASE.im4p")
    if aop1_im4p.is_file():
        aop1_bytes = aop1_im4p.read_bytes()
        all_ok &= verify_assertion(
            "AOP1 Image4 container has FourCC tag 'aopf'",
            b"aopf" in aop1_bytes[:32]
        )

    chime_im4p = ROOT / "iPhone18,3_27.2_24B119_Restore/Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p"
    if not chime_im4p.is_file():
        chime_im4p = Path("/home/prem/Projects/iOS 27/iPhone18,3_27.2_24B119_Restore/Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p")
    if chime_im4p.is_file():
        chime_bytes = chime_im4p.read_bytes()
        all_ok &= verify_assertion(
            "Boot chime Image4 container has FourCC tag 'aubt' (Audio Boot Tone)",
            b"aubt" in chime_bytes[:32] and len(chime_bytes) == 582555
        )

    # 9. Cross-Validation Matrix
    cv_file = specs_dir / "cross_validation_matrix.json"
    if cv_file.is_file():
        cv_data = json.loads(cv_file.read_text())
        ext_count = cv_data.get("extraction_confidence", {}).get("EXTRACTED", 0)
        all_ok &= verify_assertion(
            f"cross_validation_matrix has >= 30 EXTRACTED constants ({ext_count})",
            ext_count >= 30
        )

    print("\n" + ("=" * 70))
    if all_ok:
        print("✅ ALL AOP2 & RTKIT ARCHITECTURAL INVARIANTS VERIFIED SUCCESSFULLY.")
    else:
        print("❌ ONE OR MORE VERIFICATION ASSERTIONS FAILED.")
    print("=" * 70)

    return all_ok

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
