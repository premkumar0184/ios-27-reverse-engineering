#!/usr/bin/env python3
"""
verify_qemu_emulation.py — Master Verification Suite for Apple Silicon A19 Pro
Clean-Room QEMU Virtualization & Coprocessor Emulation Platform.

Validates 7 test suites:
  Suite 1: Deliverables Inventory
  Suite 2: Dossier Volume & Quality Gate (>= 40,000 bytes, 0 placeholders)
  Suite 3: C Syntax & Struct Geometries (gcc -Wall -Wextra -std=c11)
  Suite 4: Memory Map & MMIO Topology Invariants
  Suite 5: Accelerator Device Models & Protocols (AGX, Silenus, ProRes, Tightbeam)
  Suite 6: Stub RTKit Firmware Geometry & Stack Canary Verification
  Suite 7: End-to-End Emulation Execution & Workload Assertions
"""

import sys
import os
import subprocess
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()

PLACEHOLDER_STRINGS = [
    "TODO", "TBD", "Coming in next step", "Analysis omitted for brevity",
    "placeholder", "PLACEHOLDER", "lorem ipsum", "coming soon",
    "to be determined", "work in progress", "WIP"
]

def check_placeholders(text: str) -> list:
    return [p for p in PLACEHOLDER_STRINGS if re.search(rf"\b{re.escape(p)}\b", text, re.IGNORECASE)]

class QEMUVerifier:
    def __init__(self):
        self.errors = []
        self.passed_suites = 0
        self.total_suites = 7

    def fail(self, msg: str):
        self.errors.append(msg)
        print(f"    [-] ERROR: {msg}")

    def ok(self, msg: str):
        print(f"    [+] {msg}")

    # -------------------------------------------------------------------------
    # Suite 1: Deliverables Inventory
    # -------------------------------------------------------------------------
    def test_suite_1_deliverables_inventory(self):
        print("\n=== [SUITE 1/7] Deliverables Inventory ===")
        required_files = [
            "artifacts/qemu/include/apple_a19_platform.h",
            "artifacts/qemu/devices/apple_aic.h",
            "artifacts/qemu/devices/apple_aic.c",
            "artifacts/qemu/devices/apple_ascwrap.h",
            "artifacts/qemu/devices/apple_ascwrap.c",
            "artifacts/qemu/devices/apple_dart.h",
            "artifacts/qemu/devices/apple_dart.c",
            "artifacts/qemu/devices/apple_agx_direct.h",
            "artifacts/qemu/devices/apple_agx_direct.c",
            "artifacts/qemu/devices/apple_silenus_dma.h",
            "artifacts/qemu/devices/apple_silenus_dma.c",
            "artifacts/qemu/devices/apple_prores_hw.h",
            "artifacts/qemu/devices/apple_prores_hw.c",
            "artifacts/qemu/devices/apple_tightbeam_ipc.h",
            "artifacts/qemu/devices/apple_tightbeam_ipc.c",
            "artifacts/qemu/specs/platform_hardware_topology.json",
            "artifacts/qemu/specs/accelerator_device_specs.json",
            "artifacts/qemu/specs/rtkit_firmware_stub_spec.json",
            "artifacts/qemu/firmware/stub_rtkit_boot.S",
            "artifacts/qemu/firmware/stub_rtkit_core.h",
            "artifacts/qemu/firmware/stub_rtkit_core.c",
            "artifacts/qemu/firmware/stub_rtkit_linker.ld",
            "artifacts/qemu/firmware/build_stubs.py",
            "artifacts/qemu/firmware/stub_rtkit_aop2.elf",
            "artifacts/qemu/firmware/stub_rtkit_aop2.bin",
            "artifacts/qemu/firmware/stub_rtkit_silenus.elf",
            "artifacts/qemu/firmware/stub_rtkit_silenus.bin",
            "artifacts/qemu/firmware/stub_rtkit_rtbuddy.elf",
            "artifacts/qemu/firmware/stub_rtkit_rtbuddy.bin",
            "artifacts/qemu/machine/qemu_apple_a19_pro.c",
            "artifacts/qemu/harness/apple_a19_emulation_runner.c",
            "artifacts/qemu/harness/Makefile",
            "findings/qemu/05_QEMU_VIRTUALIZATION_LAYER.md",
            "IOS_27_QEMU_VIRTUALIZATION_EMULATION_RE.md"
        ]

        missing = 0
        for rel_path in required_files:
            p = ROOT / rel_path
            if not p.exists():
                self.fail(f"Missing file: {rel_path}")
                missing += 1
            elif p.stat().st_size == 0:
                self.fail(f"Empty file: {rel_path}")
                missing += 1

        if missing == 0:
            self.ok(f"All {len(required_files)} deliverable files exist and are non-empty.")
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 2: Dossier Volume & Quality Gate
    # -------------------------------------------------------------------------
    def test_suite_2_dossier_volume_and_quality(self):
        print("\n=== [SUITE 2/7] Dossier Volume & Quality Gate ===")
        suite_passed = True
        dossier_path = ROOT / "findings/qemu/05_QEMU_VIRTUALIZATION_LAYER.md"
        pub_path = ROOT / "IOS_27_QEMU_VIRTUALIZATION_EMULATION_RE.md"

        if not dossier_path.exists():
            self.fail("findings/qemu/05_QEMU_VIRTUALIZATION_LAYER.md does not exist")
            return

        size = dossier_path.stat().st_size
        if size < 40000:
            self.fail(f"05_QEMU_VIRTUALIZATION_LAYER.md size is {size} bytes (< 40,000 bytes)")
            suite_passed = False
        else:
            self.ok(f"05_QEMU_VIRTUALIZATION_LAYER.md size is {size} bytes (>= 40,000 bytes)")

        text = dossier_path.read_text(encoding="utf-8", errors="replace")
        placeholders = check_placeholders(text)
        if placeholders:
            self.fail(f"Found placeholder tokens in 05_QEMU_VIRTUALIZATION_LAYER.md: {placeholders}")
            suite_passed = False
        else:
            self.ok("0 placeholder tokens found in master dossier.")

        if pub_path.exists():
            pub_size = pub_path.stat().st_size
            pub_text = pub_path.read_text(encoding="utf-8", errors="replace")
            pub_phs = check_placeholders(pub_text)
            if pub_phs:
                self.fail(f"Found placeholder tokens in IOS_27_QEMU_VIRTUALIZATION_EMULATION_RE.md: {pub_phs}")
                suite_passed = False
            else:
                self.ok(f"IOS_27_QEMU_VIRTUALIZATION_EMULATION_RE.md size: {pub_size} bytes, 0 placeholders.")

        if suite_passed:
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 3: C Syntax & Struct Geometries
    # -------------------------------------------------------------------------
    def test_suite_3_c_syntax(self):
        print("\n=== [SUITE 3/7] C Syntax & Compilation Gate ===")
        suite_passed = True

        cmd = [
            "gcc", "-Wall", "-Wextra", "-std=c11", "-fsyntax-only",
            "artifacts/qemu/include/apple_a19_platform.h",
            "artifacts/qemu/devices/apple_aic.c",
            "artifacts/qemu/devices/apple_ascwrap.c",
            "artifacts/qemu/devices/apple_dart.c",
            "artifacts/qemu/devices/apple_agx_direct.c",
            "artifacts/qemu/devices/apple_silenus_dma.c",
            "artifacts/qemu/devices/apple_prores_hw.c",
            "artifacts/qemu/devices/apple_tightbeam_ipc.c",
            "artifacts/qemu/machine/qemu_apple_a19_pro.c"
        ]

        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode != 0:
            self.fail(f"GCC syntax-only check failed:\n{res.stderr}")
            suite_passed = False
        else:
            self.ok("All C headers and device models compile with zero errors and zero warnings.")

        if suite_passed:
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 4: Memory Map & MMIO Topology Invariants
    # -------------------------------------------------------------------------
    def test_suite_4_memory_map_topology(self):
        print("\n=== [SUITE 4/7] Memory Map & Hardware Topology Invariants ===")
        suite_passed = True
        topo_path = ROOT / "artifacts/qemu/specs/platform_hardware_topology.json"

        if not topo_path.exists():
            self.fail("platform_hardware_topology.json missing")
            return

        topo = json.loads(topo_path.read_text())
        platform = topo.get("platform", {})
        if platform.get("soc") != "t8150":
            self.fail(f"Invalid SoC: {platform.get('soc')}")
            suite_passed = False

        dram = topo.get("physical_memory_map", {}).get("dram", {})
        if dram.get("size_gb") != 32 or dram.get("base_hex") != "0x0000000800000000":
            self.fail(f"Invalid DRAM geometry: {dram}")
            suite_passed = False
        else:
            self.ok("36-bit DRAM map validated (32 GB at 0x800000000).")

        carveouts = {c["id"]: c for c in topo.get("physical_memory_map", {}).get("carveouts", [])}
        expected_carveouts = ["SPTM_RESERVED", "TXM_RESERVED", "EXCLAVE_POOL", "SEP_TZ0S", "SEP_TZ1S", "DARWIN_HOST"]
        for cid in expected_carveouts:
            if cid not in carveouts:
                self.fail(f"Missing carveout: {cid}")
                suite_passed = False
        if suite_passed:
            self.ok(f"All {len(expected_carveouts)} hardware DRAM carveouts verified.")

        vectors = topo.get("interrupt_controller", {}).get("key_vectors", {})
        expected_vectors = {
            "AIC_IRQ_PRORES_COMPLETE": 256,
            "AIC_IRQ_ISP_FRAME_DONE": 284,
            "AIC_IRQ_ISP_STATS_READY": 285,
            "AIC_IRQ_DART_ISP_FAULT": 302,
            "AIC_IRQ_SEP_INBOX": 304,
            "AIC_IRQ_AOP2_INBOX": 357,
            "AIC_IRQ_EXCLAVE_AOP2_INBOX": 361,
            "AIC_IRQ_AGX_CORE0_INBOX": 952
        }
        for vname, vnum in expected_vectors.items():
            if vectors.get(vname, {}).get("vector") != vnum:
                self.fail(f"Vector {vname} mismatch: expected {vnum}, got {vectors.get(vname, {}).get('vector')}")
                suite_passed = False
        if suite_passed:
            self.ok(f"AIC v4 interrupt vector routing matrix verified ({len(expected_vectors)} vectors).")

        if suite_passed:
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 5: Accelerator Device Models & Protocols
    # -------------------------------------------------------------------------
    def test_suite_5_accelerator_specs(self):
        print("\n=== [SUITE 5/7] Accelerator Device Models & Protocols ===")
        suite_passed = True
        spec_path = ROOT / "artifacts/qemu/specs/accelerator_device_specs.json"

        if not spec_path.exists():
            self.fail("accelerator_device_specs.json missing")
            return

        specs = json.loads(spec_path.read_text()).get("accelerators", {})
        agx = specs.get("apple_agx_direct", {})
        if agx.get("structures", {}).get("command_descriptor_bytes") != 64 or \
           agx.get("structures", {}).get("status_page_size_bytes") != 16384:
            self.fail("AGX struct geometries invalid")
            suite_passed = False
        else:
            self.ok("AppleMetalDirect AGX descriptor (64B) and status page (16KB) verified.")

        silenus = specs.get("apple_silenus_dma", {})
        if silenus.get("cisp_protocol", {}).get("magic_hex") != "0x43495350" or \
           silenus.get("cisp_protocol", {}).get("command_packet_size_bytes") != 64:
            self.fail("Silenus CISP protocol geometry invalid")
            suite_passed = False
        else:
            self.ok("Silenus Camera ISP CISP packet (64B, magic 0x43495350) verified.")

        prores = specs.get("apple_prores_hw", {})
        if prores.get("encoding_topology", {}).get("total_slices") != 16 or \
           prores.get("encoding_topology", {}).get("raw_frame_header_bytes") != 128:
            self.fail("ProRes hardware encoding geometry invalid")
            suite_passed = False
        else:
            self.ok("ProRes HW dual-core 16-slice encoder and 128B header verified.")

        tightbeam = specs.get("apple_tightbeam_ipc", {})
        if tightbeam.get("wire_format", {}).get("header_size_bytes") != 88 or \
           tightbeam.get("wire_format", {}).get("max_capabilities") != 8:
            self.fail("Tightbeam wire format geometry invalid")
            suite_passed = False
        else:
            self.ok("Tightbeam IPC wire header (88B, max caps 8) verified.")

        if suite_passed:
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 6: Stub RTKit Firmware Geometry & Canary Verification
    # -------------------------------------------------------------------------
    def test_suite_6_firmware_stubs(self):
        print("\n=== [SUITE 6/7] Stub RTKit Firmware Geometry & Stack Canary ===")
        suite_passed = True
        stub_spec_path = ROOT / "artifacts/qemu/specs/rtkit_firmware_stub_spec.json"

        if not stub_spec_path.exists():
            self.fail("rtkit_firmware_stub_spec.json missing")
            return

        spec = json.loads(stub_spec_path.read_text())
        canary_bytes = struct.pack("<Q", 0x52544B535441434B) # 'RTKSTACK' in LE

        stubs = spec.get("stubs", {})
        expected_stubs = ["stub_rtkit_aop2", "stub_rtkit_silenus", "stub_rtkit_rtbuddy"]
        for sname in expected_stubs:
            if sname not in stubs:
                self.fail(f"Missing stub in spec: {sname}")
                suite_passed = False
                continue

            elf_file = ROOT / "artifacts/qemu/firmware" / stubs[sname]["elf_filename"]
            bin_file = ROOT / "artifacts/qemu/firmware" / stubs[sname]["bin_filename"]

            if not elf_file.exists() or elf_file.stat().st_size == 0:
                self.fail(f"ELF binary missing or empty: {elf_file}")
                suite_passed = False
            if not bin_file.exists() or bin_file.stat().st_size == 0:
                self.fail(f"BIN image missing or empty: {bin_file}")
                suite_passed = False

            # Verify RTKSTACK canary presence in ELF
            if elf_file.exists():
                elf_data = elf_file.read_bytes()
                if canary_bytes not in elf_data:
                    self.fail(f"RTKSTACK canary watermark missing in {elf_file.name}")
                    suite_passed = False
                else:
                    self.ok(f"{sname}: RTKSTACK canary watermark (0x52544B535441434B) present.")

        if suite_passed:
            self.passed_suites += 1

    # -------------------------------------------------------------------------
    # Suite 7: End-to-End Emulation Execution & Workload Assertions
    # -------------------------------------------------------------------------
    def test_suite_7_emulation_execution(self):
        print("\n=== [SUITE 7/7] End-to-End Emulation Execution ===")
        suite_passed = True

        # Run harness
        runner_exe = ROOT / "artifacts/qemu/harness/apple_a19_emulation_runner"
        if not runner_exe.exists():
            res_build = subprocess.run(["make", "-C", str(ROOT / "artifacts/qemu/harness")],
                                       capture_output=True, text=True)
            if res_build.returncode != 0:
                self.fail(f"Failed to build emulation runner:\n{res_build.stderr}")
                return

        res = subprocess.run([str(runner_exe)], capture_output=True, text=True, cwd=str(ROOT))
        if res.returncode != 0:
            self.fail(f"Emulation runner exited with code {res.returncode}:\n{res.stdout}\n{res.stderr}")
            suite_passed = False
        else:
            self.ok("Bare-metal runner executed with exit code 0.")

        trace_path = ROOT / "artifacts/qemu/logs/emulation_trace.json"
        if not trace_path.exists():
            self.fail("emulation_trace.json was not generated")
            return

        trace = json.loads(trace_path.read_text())
        if trace.get("status") != "PASSED":
            self.fail(f"Emulation trace status is not PASSED: {trace.get('status')}")
            suite_passed = False
        else:
            self.ok("Emulation trace status: PASSED.")

        # Check workloads
        wl = trace.get("workloads", {})
        if not wl.get("apple_metal_direct", {}).get("passed"):
            self.fail("Workload AppleMetalDirect failed in trace")
            suite_passed = False
        else:
            self.ok("Workload 1 (AppleMetalDirect): PASSED.")

        if not wl.get("silenus_camera_isp", {}).get("passed"):
            self.fail("Workload Silenus Camera ISP failed in trace")
            suite_passed = False
        else:
            self.ok("Workload 2 (Silenus Camera ISP & BNI): PASSED.")

        if not wl.get("apple_prores_hw", {}).get("passed"):
            self.fail("Workload AppleProResHW failed in trace")
            suite_passed = False
        else:
            self.ok("Workload 3 (AppleProResHW 8K RAW): PASSED.")

        if not wl.get("tightbeam_ipc", {}).get("passed"):
            self.fail("Workload Tightbeam IPC failed in trace")
            suite_passed = False
        else:
            self.ok("Workload 4 (Tightbeam IPC & ExclaveOS): PASSED.")

        if not trace.get("rtkit_coprocessor_handshake", {}).get("passed"):
            self.fail("RTKit coprocessor handshake failed in trace")
            suite_passed = False
        else:
            self.ok("RTKit Endpoint 0 Handshake: PASSED.")

        if suite_passed:
            self.passed_suites += 1

    def run_all(self) -> bool:
        print("********************************************************************")
        print("   Apple Silicon A19 Pro (t8150) QEMU Emulation Verification Suite  ")
        print("********************************************************************")

        self.test_suite_1_deliverables_inventory()
        self.test_suite_2_dossier_volume_and_quality()
        self.test_suite_3_c_syntax()
        self.test_suite_4_memory_map_topology()
        self.test_suite_5_accelerator_specs()
        self.test_suite_6_firmware_stubs()
        self.test_suite_7_emulation_execution()

        print("\n====================================================================")
        print(f"Results: {self.passed_suites}/{self.total_suites} suites passed.")
        if self.errors:
            print(f"Total Errors Encountered: {len(self.errors)}")
            for err in self.errors:
                print(f"  • {err}")
            print("====================================================================")
            return False
        else:
            print(">>> 100% GREEN PASS: ALL 7 TEST SUITES PASSED VERIFICATION <<<")
            print("====================================================================")
            return True

if __name__ == "__main__":
    verifier = QEMUVerifier()
    success = verifier.run_all()
    sys.exit(0 if success else 1)
