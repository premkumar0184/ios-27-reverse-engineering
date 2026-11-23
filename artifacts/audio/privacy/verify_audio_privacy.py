#!/usr/bin/env python3
"""
verify_audio_privacy.py — Comprehensive Automated Verification Suite for
Track 4: Always-On Audio (AOPAudio2), VoiceTrigger & ExclaveOS Tightbeam Privacy Isolation
Apple Silicon A19 Pro (t8150) — iOS 27.2 (Darwin 24.2.0, Build 24B119)

Verifies:
1. Existence and integrity of all Track 4 artifacts, specs, C headers, and runtime clients.
2. Markdown documentation length (>= 35,000 bytes) and zero placeholder token guarantee.
3. AOP2 Always-On Audio numerical invariants (16 kHz, 3.0s, 96,000 bytes, 5.34 MB SRAM, 1.85 mW).
4. VoiceTrigger wake mechanics (AIC IRQ vector 357, Everest P-core wake, ASCwrap mailbox).
5. ExclaveOS Tightbeam wire specifications (endpoints 0x53, 0x61, 0x62, DART SID 0x11, SIL 80 nits).
6. LEAP haptic engine co-scheduling parameters (175 Hz LRA, < 100 us phase latency, 16 wave table assets).
7. Clean GCC C99 compilation of audio_host_interface.h and audio_direct_submit.c.
8. Execution and 100% pass of audio_direct_submit runtime test harness.
"""

import os
import sys
import json
import re
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

def run_all_verifications() -> bool:
    print("=======================================================================")
    print(" Apple Silicon A19 Pro (t8150 / iOS 27.2) Track 4 Verification Suite   ")
    print(" Always-On Audio, VoiceTrigger & Exclave Tightbeam Privacy Isolation   ")
    print("=======================================================================\n")

    all_ok = True

    privacy_dir = ROOT / "artifacts/audio/privacy"
    runtime_dir = ROOT / "artifacts/audio/runtime"
    findings_dir = ROOT / "findings/audio"

    # -------------------------------------------------------------------------
    # Suite 1: File Existence & Completeness
    # -------------------------------------------------------------------------
    print("--- Suite 1: Artifact Existence & Manifest Integrity ---")
    required_files = [
        runtime_dir / "audio_host_interface.h",
        runtime_dir / "audio_direct_submit.c",
        privacy_dir / "aop_audio_acoustic_buffer_spec.json",
        privacy_dir / "exclave_audio_tightbeam_wire_spec.json",
        privacy_dir / "leap_haptic_audio_sync_spec.json",
        findings_dir / "04_AOP_AUDIO_VOICETRIGGER_AND_EXCLAVE_PRIVACY.md"
    ]

    for rf in required_files:
        exists = rf.is_file()
        all_ok &= verify_assertion(f"Artifact exists: {rf.name}", exists, str(rf.relative_to(ROOT)))
        if not exists:
            print(f"FATAL: Missing required artifact {rf}")
            return False

    # -------------------------------------------------------------------------
    # Suite 2: Findings Quality & Size Invariants
    # -------------------------------------------------------------------------
    print("\n--- Suite 2: Authoritative Findings Document Integrity ---")
    doc_path = findings_dir / "04_AOP_AUDIO_VOICETRIGGER_AND_EXCLAVE_PRIVACY.md"
    doc_size = os.path.getsize(doc_path)
    all_ok &= verify_assertion(
        "Document size >= 35,000 bytes",
        doc_size >= 35000,
        f"{doc_size} bytes (minimum: 35,000 bytes)"
    )

    doc_text = doc_path.read_text(encoding="utf-8")
    placeholders = ["TODO", "TBD", "placeholder", "WIP", "FIXME"]
    for ph in placeholders:
        matches = list(re.finditer(r"\b" + ph + r"\b", doc_text, re.IGNORECASE))
        all_ok &= verify_assertion(
            f"Zero occurrence of placeholder '{ph}'",
            len(matches) == 0,
            f"Found {len(matches)}"
        )

    # -------------------------------------------------------------------------
    # Suite 3: AOP2 Always-On Audio Specification Invariants
    # -------------------------------------------------------------------------
    print("\n--- Suite 3: AOP2 Acoustic Buffer & SRAM Hardware Geometry ---")
    aop_spec_file = privacy_dir / "aop_audio_acoustic_buffer_spec.json"
    aop_spec = json.loads(aop_spec_file.read_text())

    # Memory
    sram = aop_spec.get("memory_architecture", {}).get("sram_aperture", {})
    all_ok &= verify_assertion(
        "SRAM Base == 0x0000000101000000",
        sram.get("base_physical_address") == "0x0000000101000000"
    )
    all_ok &= verify_assertion(
        "SRAM Size == 5.34 MB (5,599,232 bytes / 0x00557000)",
        sram.get("size_bytes") == 5599232 and sram.get("size_hex") == "0x00557000"
    )

    # Hotword Sub-binary
    sub_bin = aop_spec.get("firmware_sub_binary", {})
    all_ok &= verify_assertion(
        "Binary #3 is 03_audio_hotword_app.macho (offset: 434201, size: 753976)",
        sub_bin.get("index") == 3 and
        sub_bin.get("file_offset_bytes") == 434201 and
        sub_bin.get("size_bytes") == 753976 and
        sub_bin.get("uuid") == "46699d8af0e633b595d262b5cce92e9c"
    )

    # Acoustic Parameters
    acoustics = aop_spec.get("acoustic_parameters", {})
    all_ok &= verify_assertion(
        "Sampling Rate == 16,000 Hz",
        acoustics.get("sampling_rate_hz") == 16000
    )
    all_ok &= verify_assertion(
        "Bit Depth == 16 bits (Signed LPCM Mono)",
        acoustics.get("bit_depth") == 16 and acoustics.get("channel_count") == 1
    )
    all_ok &= verify_assertion(
        "History Buffer Duration == 3.0 seconds (48,000 frames)",
        acoustics.get("buffer_duration_seconds") == 3.0 and
        acoustics.get("total_buffer_frames") == 48000
    )
    all_ok &= verify_assertion(
        "History Buffer Allocation == 96,000 bytes",
        acoustics.get("total_buffer_bytes") == 96000
    )
    all_ok &= verify_assertion(
        "Acoustic Front-End Power Consumption <= 1.85 mW",
        acoustics.get("power_consumption_mw") <= 1.85
    )

    # Wake Invariants
    wake = aop_spec.get("wake_trigger_mechanics", {})
    all_ok &= verify_assertion(
        "AIC Interrupt Vector == 357 (0x0165, /device-tree/arm-io/aop2)",
        wake.get("interrupt_vector") == 357 and wake.get("aic_vector_hex") == "0x0165"
    )
    all_ok &= verify_assertion(
        "Wake Target Core Cluster == Everest P-cores",
        "Everest" in wake.get("target_core_cluster", "")
    )
    all_ok &= verify_assertion(
        "Typical Wake Latency <= 20 ms",
        wake.get("wake_latency_typical_ms") <= 20.0,
        f"{wake.get('wake_latency_typical_ms')} ms"
    )

    # -------------------------------------------------------------------------
    # Suite 4: ExclaveOS Tightbeam Audio Stream Wire Specification
    # -------------------------------------------------------------------------
    print("\n--- Suite 4: ExclaveOS Tightbeam Wire Formats & SIL Enforcement ---")
    tb_spec_file = privacy_dir / "exclave_audio_tightbeam_wire_spec.json"
    tb_spec = json.loads(tb_spec_file.read_text())

    endpoints = tb_spec.get("tightbeam_endpoints", {})
    all_ok &= verify_assertion(
        "Endpoint 0x53 defined as AOP2 Exclave bridge",
        "0x53" in endpoints and "sharedmem_xcoproc_AOP2_EP53_in" in endpoints["0x53"]["service_name"]
    )
    all_ok &= verify_assertion(
        "Endpoints 0x61 and 0x62 defined for isolated audio streams",
        "0x61" in endpoints and "0x62" in endpoints
    )
    all_ok &= verify_assertion(
        "DART Stream ID 0x11 mapped to mapper-exclave-aop2",
        "0x11" in endpoints.get("0x53", {}).get("dart_stream_id", "")
    )

    # Struct geometries
    structs = tb_spec.get("wire_struct_geometries", {})
    all_ok &= verify_assertion(
        "exad_stream_description size == 16 bytes ({IIISCC})",
        structs.get("exad_stream_description_t", {}).get("size_bytes") == 16 and
        structs.get("exad_stream_description_t", {}).get("wire_encoding") == "{IIISCC}"
    )
    all_ok &= verify_assertion(
        "voicetriggernonsecure_data size == 16 bytes ({QQ})",
        structs.get("voicetriggernonsecure_data_t", {}).get("size_bytes") == 16 and
        structs.get("voicetriggernonsecure_data_t", {}).get("wire_encoding") == "{QQ}"
    )
    all_ok &= verify_assertion(
        "voicetrigger_secure_data size == 156 bytes ({QQQI[128C]})",
        structs.get("voicetrigger_secure_data_t", {}).get("size_bytes") == 156 and
        structs.get("voicetrigger_secure_data_t", {}).get("wire_encoding") == "{QQQI[128C]}"
    )

    # SIL Enforcement
    sil = tb_spec.get("privacy_and_sil_enforcement", {}).get("secure_indicator_light", {})
    all_ok &= verify_assertion(
        "SIL Controller Service == com.apple.service.ExclaveIndicatorController",
        sil.get("hardware_controller_service") == "com.apple.service.ExclaveIndicatorController"
    )
    all_ok &= verify_assertion(
        "SIL Nominal Luminance Cap == 80 nits",
        sil.get("nominal_luminance_nits") == 80
    )

    # -------------------------------------------------------------------------
    # Suite 5: LEAP Haptic Engine Audio Sync Specification
    # -------------------------------------------------------------------------
    print("\n--- Suite 5: LEAP Haptic Engine Co-Scheduler Specification ---")
    leap_spec_file = privacy_dir / "leap_haptic_audio_sync_spec.json"
    leap_spec = json.loads(leap_spec_file.read_text())

    actuator = leap_spec.get("hardware_actuator_parameters", {})
    all_ok &= verify_assertion(
        "Actuator Type == Linear Resonant Actuator (LRA) / High-Force Driver (HFD)",
        "LRA" in actuator.get("motor_type", "")
    )
    all_ok &= verify_assertion(
        "LRA Resonant Frequency == 175.0 Hz",
        actuator.get("nominal_resonant_frequency_hz") == 175.0
    )
    all_ok &= verify_assertion(
        "Audio-to-Haptic Phase Latency Ceiling < 100 us",
        actuator.get("audio_to_haptic_phase_latency_max_us") <= 100,
        f"{actuator.get('audio_to_haptic_phase_latency_typical_us')} us typical"
    )
    all_ok &= verify_assertion(
        "Maximum Wave Table Assets == 16",
        actuator.get("max_assets") == 16
    )

    asset_geom = leap_spec.get("waveform_asset_geometry", {})
    all_ok &= verify_assertion(
        "leap_waveform_asset_t size == 30 bytes",
        asset_geom.get("size_bytes") == 30
    )
    all_ok &= verify_assertion(
        "AppleAOPButtonHaptics entitlement == com.apple.private.aea.haptics.user-access",
        any(d.get("user_client_entitlement") == "com.apple.private.aea.haptics.user-access" for d in leap_spec.get("driver_components", []))
    )

    # -------------------------------------------------------------------------
    # Suite 6: Clean-Room C99 Compilation & Verification Harness
    # -------------------------------------------------------------------------
    print("\n--- Suite 6: Clean-Room C99 Compilation & Binary Execution ---")
    c_header = runtime_dir / "audio_host_interface.h"
    c_source = runtime_dir / "audio_direct_submit.c"
    c_binary = runtime_dir / "audio_direct_submit"

    # Header syntax validation
    res_hdr = subprocess.run(
        ["gcc", "-fsyntax-only", "-Wall", "-Wextra", "-std=c99", "-pedantic", str(c_header)],
        capture_output=True,
        text=True
    )
    all_ok &= verify_assertion(
        "gcc -fsyntax-only -Wall -Wextra -std=c99 -pedantic audio_host_interface.h passes",
        res_hdr.returncode == 0,
        res_hdr.stderr.strip() if res_hdr.stderr else "Clean compilation"
    )

    # Runtime binary build
    res_build = subprocess.run(
        ["gcc", "-Wall", "-Wextra", "-std=c99", "-O2", "-pedantic", str(c_source), "-o", str(c_binary)],
        capture_output=True,
        text=True
    )
    all_ok &= verify_assertion(
        "gcc -Wall -Wextra -std=c99 -O2 -pedantic audio_direct_submit.c builds cleanly",
        res_build.returncode == 0,
        res_build.stderr.strip() if res_build.stderr else "Clean compilation"
    )

    # Binary execution
    if c_binary.is_file():
        res_run = subprocess.run(
            [str(c_binary)],
            capture_output=True,
            text=True
        )
        passed_test_msg = "ALL 11/11 TESTS PASSED" in res_run.stdout
        all_ok &= verify_assertion(
            "./audio_direct_submit executed with exit code 0",
            res_run.returncode == 0,
            f"Return code: {res_run.returncode}"
        )
        all_ok &= verify_assertion(
            "audio_direct_submit reports 11/11 tests passed",
            passed_test_msg,
            "100% Clean-Room Architecture Conformance"
        )
    else:
        all_ok &= verify_assertion("audio_direct_submit binary exists", False)

    # -------------------------------------------------------------------------
    # Final Verdict
    # -------------------------------------------------------------------------
    print("\n" + ("=" * 71))
    if all_ok:
        print("✅ ALL TRACK 4 AUDIO PRIVACY & VOICETRIGGER INVARIANTS VERIFIED (100% PASS)")
    else:
        print("❌ ONE OR MORE VERIFICATION ASSERTIONS FAILED")
    print("=" * 71 + "\n")

    return all_ok

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
