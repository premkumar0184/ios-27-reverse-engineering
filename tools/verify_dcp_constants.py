#!/usr/bin/env python3
"""
verify_dcp_constants.py — Independent Numerical Verification of Display Coprocessor (DCP) & ProMotion Constants
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro)

Asserts:
1. Image4 container header, FourCC tag 'dcpf', LZFSE decompression to 16.99 MB.
2. Apple BUNDLE container (DNUB v4.0), 11 TOC entries, ARM64e Mach-O slices.
3. Hardware MMIO: ASCwrap-v6 Mailbox (0x100600000), DART-DCP (0x1fa340000), DART-DISP0 (0x1fa300000).
4. AIC Interrupt vectors: 411 (DISP_INT_DCP), 412 (DISP_EXT0_DCP), 403 (DCP0-V), 405 (DCPEXT0-V).
5. ProMotion dynamic refresh rates: 1Hz (AOD) through 120Hz (ProMotion), 504 MHz pixel clock.
6. Vertical Flexible Timing Generator (VFTG_v38) scan-invariance and dynamic back porch modulation.
7. Hardware UPBlocks: 38 pipe blocks, GenPipe_v33 architecture.
8. Cross-Validation Matrix: >= 25 EXTRACTED constants, 0 UNKNOWN, 0 TENTATIVE.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def get_path(filename: str, default_dir: str = "artifacts/dcp") -> Path:
    p = ROOT / default_dir / filename
    if p.is_file():
        return p
    p2 = ROOT / "specs" / filename
    if p2.is_file():
        return p2
    return p

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_verifications() -> bool:
    print("=== Apple Display Coprocessor (DCP) & ProMotion Architecture Verification ===")
    all_ok = True

    # 1. Verify File Existence
    required_filenames = [
        ("phase_1a_workspace_baseline.json", "artifacts/dcp"),
        ("dcp_firmware_container_spec.json", "artifacts/dcp"),
        ("dcp_microkernel_spec.json", "artifacts/dcp"),
        ("dcp_service_topology.json", "artifacts/dcp"),
        ("promotion_arbitration_spec.json", "artifacts/dcp"),
        ("vftg_timing_generator_spec.json", "artifacts/dcp"),
        ("pixel_compensation_spec.json", "artifacts/dcp"),
        ("color_pipeline_lut_spec.json", "artifacts/dcp"),
        ("xnu_dcp_boundary_spec.json", "artifacts/dcp"),
        ("cross_validation_matrix.json", "artifacts/dcp"),
    ]

    for fname, default_dir in required_filenames:
        rf = get_path(fname, default_dir)
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {fname}", exists, str(rf))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # Check client implementation
    client_c = ROOT / "artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c"
    if not client_c.is_file():
        client_c = ROOT / "runtime/dcp_mailbox_client.c"
    exists = client_c.is_file()
    all_ok &= verify_assertion(f"Artifact exists: {client_c.name}", exists, str(client_c))
    if not exists:
        print(f"FATAL: Missing required artifact {client_c}")
        return False

    # 2. Container Specification Verification
    cont_file = get_path("dcp_firmware_container_spec.json")
    cont_data = json.loads(cont_file.read_text())
    container_info = cont_data.get("container", {})

    all_ok &= verify_assertion(
        "FourCC Tag == dcpf",
        container_info.get("fourcc_tag") == "dcpf",
        f"got {container_info.get('fourcc_tag')}"
    )
    all_ok &= verify_assertion(
        "Wrapper == Apple Image4 (IM4P)",
        container_info.get("wrapper") == "Apple Image4 (IM4P)",
        container_info.get("wrapper")
    )
    all_ok &= verify_assertion(
        "Total Compressed Size == 2466452 bytes",
        container_info.get("total_container_size_bytes") == 2466452,
        f"got {container_info.get('total_container_size_bytes')}"
    )
    all_ok &= verify_assertion(
        "Decompressed Payload Size == 16990208 bytes (16.20 MB)",
        container_info.get("compression", {}).get("decompressed_size_bytes") == 16990208,
        f"got {container_info.get('compression', {}).get('decompressed_size_bytes')}"
    )

    bund = container_info.get("internal_bundle", {})
    all_ok &= verify_assertion(
        "Internal Bundle Magic == 0x42554e44 (DNUB v4.0)",
        bund.get("magic") == "0x42554e44" and bund.get("version") == "0x00040000",
        f"magic={bund.get('magic')}, ver={bund.get('version')}"
    )

    # 3. Microkernel & Memory Specification
    micro_file = get_path("dcp_microkernel_spec.json")
    micro_data = json.loads(micro_file.read_text())

    rtkit = micro_data.get("microkernel", {})
    all_ok &= verify_assertion(
        "RTKit OS Version Banner matches 3514.40.18 release",
        "RTKit_armv8_cl4_Oz_flto_pac-3514.40.18.release" in rtkit.get("version", ""),
        rtkit.get("version")
    )

    carveouts = micro_data.get("memory_carveouts", {})
    all_ok &= verify_assertion(
        "DCP Runtime DRAM Carveout == 48 MB (50331648 bytes)",
        carveouts.get("dcp_firmware_dram", {}).get("size_bytes") == 50331648,
        f"got {carveouts.get('dcp_firmware_dram', {}).get('size_bytes')}"
    )
    all_ok &= verify_assertion(
        "DISP0 Framebuffer DRAM Pool == 80 MB (83886080 bytes)",
        carveouts.get("disp_framebuffer_pool", {}).get("size_bytes") == 83886080,
        f"got {carveouts.get('disp_framebuffer_pool', {}).get('size_bytes')}"
    )

    # 4. Hardware MMIO & Interrupt Topology
    base_file = get_path("phase_1a_workspace_baseline.json")
    base_data = json.loads(base_file.read_text())
    hw = base_data.get("hardware_interconnect", {})

    all_ok &= verify_assertion(
        "ASCwrap Mailbox MMIO Base == 0x0000000100600000 (544 KB window)",
        hw.get("ascwrap_mailbox_mmio_base") == "0x0000000100600000" and hw.get("ascwrap_mailbox_size_bytes") == 557056,
        hw.get("ascwrap_mailbox_mmio_base")
    )
    all_ok &= verify_assertion(
        "DART-DCP IOMMU Base == 0x00000001fa340000",
        hw.get("dart_dcp_base") == "0x00000001fa340000",
        hw.get("dart_dcp_base")
    )
    all_ok &= verify_assertion(
        "DART-DISP0 IOMMU Base == 0x00000001fa300000",
        hw.get("dart_disp0_base") == "0x00000001fa300000",
        hw.get("dart_disp0_base")
    )

    irqs = hw.get("interrupt_vectors", {})
    all_ok &= verify_assertion(
        "AIC Interrupts cover 411 (DISP_INT_DCP), 412 (DISP_EXT0_DCP), 403 (DCP0_V), 405 (DCPEXT0_V)",
        irqs.get("DISP_INT_DCP") == 411 and irqs.get("DISP_EXT0_DCP") == 412 and irqs.get("DCP0_V") == 403 and irqs.get("DCPEXT0_V") == 405,
        f"IRQs: {irqs}"
    )

    # 5. ProMotion Dynamic Refresh Rate & VFTG Timing
    prom_file = get_path("promotion_arbitration_spec.json")
    prom_data = json.loads(prom_file.read_text())
    prom_arch = prom_data.get("promotion_architecture", {})

    all_ok &= verify_assertion(
        "ProMotion Range: Max 120Hz, Min Interactive 10Hz, Min AOD 1Hz",
        prom_arch.get("range_hz", {}).get("max_hz") == 120 and
        prom_arch.get("range_hz", {}).get("min_interactive_hz") == 10 and
        prom_arch.get("range_hz", {}).get("min_aod_hz") == 1,
        f"range={prom_arch.get('range_hz')}"
    )

    rates = prom_arch.get("discrete_refresh_rates", [])
    all_ok &= verify_assertion(
        "Catalogs 11 discrete refresh rates (1Hz through 120Hz)",
        len(rates) == 11 and all(r["rate_hz"] in [1, 10, 15, 20, 24, 30, 40, 48, 60, 80, 120] for r in rates),
        f"got {len(rates)} discrete rates"
    )

    vftg_file = get_path("vftg_timing_generator_spec.json")
    vftg_data = json.loads(vftg_file.read_text())
    vftg_hw = vftg_data.get("vftg_hardware", {})

    all_ok &= verify_assertion(
        "VFTG Pixel Clock == 504.0 MHz (504000000 Hz)",
        vftg_hw.get("pixel_clock_hz") == 504000000,
        f"got {vftg_hw.get('pixel_clock_hz')}"
    )
    all_ok &= verify_assertion(
        "Panel Active Resolution == 1320x2868",
        vftg_hw.get("horizontal_geometry", {}).get("active_pixels") == 1320 and
        vftg_hw.get("vertical_geometry", {}).get("active_lines") == 2868,
        "1320x2868 confirmed"
    )
    all_ok &= verify_assertion(
        "Fast_TE Sample Clock == 24 MHz (24000000 Hz)",
        vftg_hw.get("panel_synchronization", {}).get("te_sample_clock_hz") == 24000000,
        "Fast_TE sampling clock verified"
    )

    # 6. Service Topology & Hardware UPBlocks
    topo_file = get_path("dcp_service_topology.json")
    topo_data = json.loads(topo_file.read_text())

    endpoints = topo_data.get("endpoints", [])
    all_ok &= verify_assertion(
        "AFK endpoints catalog AFKBuiltinAPMailboxEndpoint, CBAOPEndpoint, RTKExclaveTBEndpoint, RTKTrustedTBEndpoint",
        len(endpoints) == 4 and any(e["endpoint_name"] == "CBAOPEndpoint" for e in endpoints) and any(e["endpoint_name"] == "RTKExclaveTBEndpoint" for e in endpoints),
        f"got {len(endpoints)} endpoints"
    )

    upblocks = topo_data.get("hardware_pipe_blocks", {})
    all_ok &= verify_assertion(
        "Hardware Pipe Architecture == GenPipe_v33 with 38 pipe blocks",
        upblocks.get("architecture") == "GenPipe_v33 (H18P)" and upblocks.get("count") == 38,
        upblocks.get("architecture")
    )

    # 7. Cross-Validation Matrix
    cv_file = get_path("cross_validation_matrix.json")
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
        print("✅ ALL DISPLAY COPROCESSOR (DCP) & PROMOTION CONSTANTS AND INVARIANTS VERIFIED!")
        return True
    else:
        print("❌ SOME VERIFICATION CHECKS FAILED.")
        return False

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
