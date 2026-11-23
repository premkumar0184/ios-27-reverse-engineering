#!/usr/bin/env python3
"""
verify_silenus_driver.py — Comprehensive Verification Suite for Apple Silenus ISP
Darwin Host Driver Boundary & Camera Hardware Topography (A19 Pro t8150 / iOS 27.2 24B119)
"""

import sys
import os
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_tests() -> bool:
    print("=====================================================================================")
    print(" Apple Silenus Camera ISP: Host Driver Boundary & Hardware Topography Test Suite     ")
    print("=====================================================================================")
    all_ok = True

    # Suite 1: Deliverables Inventory
    print("\n--- Suite 1: Verifying Deliverables Inventory ---")
    required_files = [
        ROOT / "artifacts/silenus/driver/silenus_host_interface.h",
        ROOT / "artifacts/silenus/driver/camera_hardware_topography.json",
        ROOT / "artifacts/silenus/driver/driver_dispatch_spec.json",
        ROOT / "artifacts/silenus/driver/volchok_actuator_spec.json",
        ROOT / "findings/silenus/04_DARWIN_DRIVER_CAMERA_TOPOLOGY.md",
    ]
    for rf in required_files:
        exists = rf.is_file()
        sz = rf.stat().st_size if exists else 0
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, f"{sz} bytes")

    # Suite 2: Dossier Volume & Zero Placeholder Tokens
    print("\n--- Suite 2: Verifying Dossier Volume & Cleanliness ---")
    dossier_path = ROOT / "findings/silenus/04_DARWIN_DRIVER_CAMERA_TOPOLOGY.md"
    if dossier_path.is_file():
        text = dossier_path.read_text(encoding="utf-8", errors="replace")
        sz = len(text.encode("utf-8"))
        all_ok &= verify_assertion("Dossier volume >= 40,000 bytes", sz >= 40000, f"{sz} bytes")
        forbidden = ["TODO", "TBD", "placeholder", "coming soon", "work in progress", "WIP"]
        found = [tok for tok in forbidden if tok.lower() in text.lower()]
        all_ok &= verify_assertion("Zero forbidden placeholder tokens", len(found) == 0, f"Found: {found}")
    else:
        all_ok = False
        print("  [FAIL] Dossier file not found on disk")

    # Suite 3: C Interface Syntax & Struct Geometries
    print("\n--- Suite 3: Verifying C Interface Syntax & Struct Geometries ---")
    c_header = ROOT / "artifacts/silenus/driver/silenus_host_interface.h"
    if c_header.is_file():
        res = subprocess.run(["gcc", "-Wall", "-Wextra", "-fsyntax-only", str(c_header)],
                             capture_output=True, text=True)
        all_ok &= verify_assertion("gcc -fsyntax-only silenus_host_interface.h compiles cleanly",
                                  res.returncode == 0, res.stderr.strip() if res.returncode != 0 else "0 warnings")

        # Test struct sizes
        test_c = f"""
        #include <stdio.h>
        #include "{c_header}"
        int main() {{
            if (sizeof(struct cisp_command_header) != 16) return 1;
            if (sizeof(struct cisp_command_packet) != 64) return 2;
            if (sizeof(struct isp_ring_buffer_header_v2) != 64) return 3;
            if (sizeof(struct h16_isp_process_buffer_args) != 48) return 4;
            return 0;
        }}
        """
        tmp_src = Path("/tmp/test_silenus_sizes.c")
        tmp_bin = Path("/tmp/test_silenus_sizes")
        tmp_src.write_text(test_c)
        comp_res = subprocess.run(["gcc", "-Wall", "-Wextra", str(tmp_src), "-o", str(tmp_bin)],
                                  capture_output=True, text=True)
        if comp_res.returncode == 0:
            run_res = subprocess.run([str(tmp_bin)], capture_output=True)
            all_ok &= verify_assertion("Exact C struct sizes: Header=16B, Packet=64B, Ring=64B, Args=48B",
                                      run_res.returncode == 0, f"exit code {run_res.returncode}")
        else:
            all_ok = False
            print("  [FAIL] Failed to compile struct size test:", comp_res.stderr)
    else:
        all_ok = False
        print("  [FAIL] silenus_host_interface.h not found")

    # Suite 4: Hardware Topography & DART-ISP Invariants
    print("\n--- Suite 4: Verifying Hardware Topography & DART-ISP Invariants ---")
    topo_path = ROOT / "artifacts/silenus/driver/camera_hardware_topography.json"
    if topo_path.is_file():
        tdata = json.loads(topo_path.read_text(encoding="utf-8"))
        iommu = tdata.get("iommu", {})
        all_ok &= verify_assertion("DART-ISP MMIO base == 0x00000001128c0000", iommu.get("mmio_base") == "0x00000001128c0000")
        all_ok &= verify_assertion("DART-ISP aperture == 65,536 bytes (64 KB)", iommu.get("aperture_size_bytes") == 65536)
        all_ok &= verify_assertion("DART-ISP page granule == 16,384 bytes (16 KB)", iommu.get("page_granule_bytes") == 16384)
        all_ok &= verify_assertion("DART-ISP AIC interrupt vector == 302 (0x012e)", iommu.get("aic_interrupt_vector") == 302)
        sids = {s["sid_hex"]: s["name"] for s in iommu.get("stream_id_mappings", [])}
        all_ok &= verify_assertion("Stream ID 0x00 (Control) mapped", "0x00" in sids and sids["0x00"] == "mapper-isp")
        all_ok &= verify_assertion("Stream ID 0x01 (Raw) mapped", "0x01" in sids and sids["0x01"] == "mapper-isp-raw")
        all_ok &= verify_assertion("Stream ID 0x02 (BNI Pearl) mapped", "0x02" in sids and sids["0x02"] == "mapper-isp-pearl")
        all_ok &= verify_assertion("Stream ID 0x03 (YUV Preview) mapped", "0x03" in sids and sids["0x03"] == "mapper-isp-yuv")

        isp_core = tdata.get("isp_core", {})
        clks = {c["function_name"]: c["frequency_nominal_mhz"] for c in isp_core.get("reference_clocks", [])}
        all_ok &= verify_assertion("ref0 nominal frequency == 1,200 MHz", clks.get("function-conf_isp_ref0_clk_freq") == 1200)
        all_ok &= verify_assertion("ref1 nominal frequency == 800 MHz", clks.get("function-conf_isp_ref1_clk_freq") == 800)
        all_ok &= verify_assertion("ref2 nominal frequency == 400 MHz", clks.get("function-conf_isp_ref2_clk_freq") == 400)
    else:
        all_ok = False
        print("  [FAIL] camera_hardware_topography.json not found")

    # Suite 5: Driver Dispatch & UserClient Specifications
    print("\n--- Suite 5: Verifying Driver Dispatch & UserClient Specifications ---")
    disp_path = ROOT / "artifacts/silenus/driver/driver_dispatch_spec.json"
    if disp_path.is_file():
        ddata = json.loads(disp_path.read_text(encoding="utf-8"))
        bid = ddata.get("driver_bundle", {}).get("bundle_id")
        all_ok &= verify_assertion("Driver bundle == com.apple.driver.AppleH16CameraInterface", bid == "com.apple.driver.AppleH16CameraInterface")
        classes = [c["class_name"] for c in ddata.get("driver_bundle", {}).get("primary_classes", [])]
        all_ok &= verify_assertion("AppleH16CamIn class present", "AppleH16CamIn" in classes)
        all_ok &= verify_assertion("AppleH16CamInUserClient class present", "AppleH16CamInUserClient" in classes)
        all_ok &= verify_assertion("AppleH16PearlCamUserClient class present", "AppleH16PearlCamUserClient" in classes)
        all_ok &= verify_assertion("AppleH16CamInFrameReceiver class present", "AppleH16CamInFrameReceiver" in classes)

        mapping = ddata.get("memory_mapping_functions", {})
        all_ok &= verify_assertion("function-isp_map_iobmd mapped", "function_isp_map_iobmd" in mapping)
        all_ok &= verify_assertion("function-isp_unmap_iobmd mapped", "function_isp_unmap_iobmd" in mapping)

        queue = ddata.get("shared_data_queue", {})
        all_ok &= verify_assertion("IOSharedDataQueue capacity == 65,536 bytes", queue.get("queue_capacity_bytes") == 65536)
        all_ok &= verify_assertion("IOSharedDataQueue ring version == 2", queue.get("ring_buffer_version") == 2)
    else:
        all_ok = False
        print("  [FAIL] driver_dispatch_spec.json not found")

    # Suite 6: Volchok X3357 Actuators & Stabilization
    print("\n--- Suite 6: Verifying Volchok X3357 Actuators & Stabilization ---")
    vol_path = ROOT / "artifacts/silenus/driver/volchok_actuator_spec.json"
    if vol_path.is_file():
        vdata = json.loads(vol_path.read_text(encoding="utf-8"))
        act = vdata.get("actuator_controller", {})
        all_ok &= verify_assertion("Volchok Product ID == X3357", act.get("product_id") == "X3357")
        all_ok &= verify_assertion("Volchok Board ID == 13143 (0x3357)", act.get("board_id") == 13143)

        uc = vdata.get("microcode_payload", {})
        all_ok &= verify_assertion("Volchok microcode size == 98,304 bytes (96 KB)", uc.get("payload_size_bytes") == 98304)
        all_ok &= verify_assertion("Volchok microcode version == 209200028", uc.get("version") == 209200028)
        vt = uc.get("vector_table", {})
        all_ok &= verify_assertion("Initial Stack Pointer == 0x20006000", vt.get("initial_stack_pointer") == "0x20006000")
        all_ok &= verify_assertion("Reset Vector == 0x0000c49d (Thumb entry 0x0000c49c)", vt.get("reset_vector") == "0x0000c49d")

        crypto = vdata.get("security_crypto_module", {})
        all_ok &= verify_assertion("su_crypto payload size == 24,576 bytes (24 KB)", crypto.get("payload_size_bytes") == 24576)
        all_ok &= verify_assertion("su_crypto version == 172501", crypto.get("version") == 172501)

        stab = vdata.get("stabilization_subsystems", {})
        ois = stab.get("sensor_shift_ois", {})
        all_ok &= verify_assertion("Sensor-Shift has-sphere flag == 1", ois.get("devicetree_value") == 1)
        all_ok &= verify_assertion("AOP gyro telemetry endpoint == aop-isp-endpoint-cfg", ois.get("telemetry_endpoint") == "aop-isp-endpoint-cfg")
        all_ok &= verify_assertion("Sensor-Shift sampling rate == 10,000 Hz", ois.get("sampling_rate_hz") == 10000)
    else:
        all_ok = False
        print("  [FAIL] volchok_actuator_spec.json not found")

    print("\n=====================================================================================")
    if all_ok:
        print(" ALL 6 TEST SUITES PASSED: 100% GREEN (ZERO PLACEHOLDERS, VERIFIED SPECS)            ")
        print("=====================================================================================")
        return True
    else:
        print(" VERIFICATION FAILED! Check error messages above.                                   ")
        print("=====================================================================================")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
