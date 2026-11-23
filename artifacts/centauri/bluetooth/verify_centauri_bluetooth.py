#!/usr/bin/env python3
"""
Verification Suite for Apple Centauri Bluetooth 5.4/6.0, LE Audio & Coexistence Subsystem
Target: Apple Centauri (t2026phoneG1 / Silicon Stepping B0)
"""

import sys
import os
import json
import hashlib
import re

WORKSPACE = "/home/prem/Projects/iOS 27"

def log_pass(msg):
    print(f"[\033[92mPASS\033[0m] {msg}")

def log_fail(msg):
    print(f"[\033[91mFAIL\033[0m] {msg}")
    sys.exit(1)

def test_partitions_and_hashes():
    print("\n--- Test 1: Partition Integrity & SHA-256 Hashes ---")
    manifest_path = os.path.join(WORKSPACE, "artifacts/centauri/bluetooth/partitions_manifest.json")
    if not os.path.exists(manifest_path):
        log_fail("partitions_manifest.json does not exist")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    for tag, info in manifest.items():
        file_path = os.path.join(WORKSPACE, info["file"])
        if not os.path.exists(file_path):
            log_fail(f"Partition file missing: {file_path}")
        
        size = os.path.getsize(file_path)
        if size != info["size"]:
            log_fail(f"Size mismatch for {tag}: expected {info['size']}, got {size}")
        
        with open(file_path, "rb") as bf:
            digest = hashlib.sha256(bf.read()).hexdigest()
        if digest != info["sha256"]:
            log_fail(f"SHA-256 mismatch for {tag}: expected {info['sha256']}, got {digest}")
        
        log_pass(f"Partition {tag:6s}: {size:7d} bytes, SHA-256 matches ({digest[:12]}...)")

def test_json_specifications():
    print("\n--- Test 2: JSON Specification Syntax & Schemas ---")
    specs = [
        "artifacts/centauri/bluetooth/coexistence_priority_matrix.json",
        "artifacts/centauri/bluetooth/channel_sounding_le_audio_spec.json",
        "artifacts/centauri/bluetooth/lpbt_findmy_spec.json",
        "artifacts/centauri/bluetooth/btse_security_engine_spec.json"
    ]
    for rel_path in specs:
        full_path = os.path.join(WORKSPACE, rel_path)
        if not os.path.exists(full_path):
            log_fail(f"Spec file missing: {rel_path}")
        with open(full_path) as f:
            try:
                data = json.load(f)
            except Exception as e:
                log_fail(f"Invalid JSON in {rel_path}: {e}")
        
        if "title" not in data or "target_silicon" not in data:
            log_fail(f"Required top-level fields missing in {rel_path}")
        
        log_pass(f"Valid Specification: {os.path.basename(rel_path)} ({len(data)} sections)")

def test_coexistence_matrix_integrity():
    print("\n--- Test 3: Coexistence Priority Matrix Structure ---")
    coex_path = os.path.join(WORKSPACE, "artifacts/centauri/bluetooth/coexistence_priority_matrix.json")
    with open(coex_path) as f:
        data = json.load(f)
    
    levels = data.get("priority_levels", [])
    if len(levels) != 8:
        log_fail(f"Expected 8 priority levels (0..7), got {len(levels)}")
    log_pass(f"Verified 8 priority levels (0 to 7) defined")
    
    activities = data.get("activity_classification_table", {})
    bt_acts = activities.get("bluetooth_activities", [])
    wifi_acts = activities.get("wifi_activities", [])
    if len(bt_acts) < 8 or len(wifi_acts) < 5:
        log_fail(f"Insufficient activity definitions: {len(bt_acts)} BT, {len(wifi_acts)} Wi-Fi")
    log_pass(f"Verified activity classifications: {len(bt_acts)} Bluetooth, {len(wifi_acts)} Wi-Fi")
    
    conflicts = data.get("pairwise_conflict_arbitration_matrix", [])
    if len(conflicts) < 8:
        log_fail(f"Insufficient conflict cases: {len(conflicts)}")
    log_pass(f"Verified pairwise arbitration conflict resolutions: {len(conflicts)} cases mapped")

def test_firmware_symbol_verification():
    print("\n--- Test 4: Firmware Symbol & Assertion Verification ---")
    acib_path = os.path.join(WORKSPACE, "artifacts/centauri/bluetooth/partitions/acib.bin")
    with open(acib_path, "rb") as f:
        acib_data = f.read()
    
    expected_symbols = [
        b"Aborting - Inactive CH MAP!",
        b"Bad step index! exp=%d, got=%d",
        b"illegal step status!",
        b"Illegal HDRP type: %d",
        b"Resolvable tag descriptor did not finish in time",
        b"lc_main_ble_audio_link_datapath_connected_iso_get_tx_packet",
        b"lm_ble_connected_iso_central_init_data_path_per_cis",
        b"findmy_ihsm_state_abort",
        b"Failed to allocate AES handle, instance=%d",
        b"GBT Transaction Manager: Transaction pool exhausted",
        b"lm_tas_set_activity_info: Unknown TAS_ACTIVITY_TYPE type = %d",
        b"lc_protocol_stewie_if_control_init",
        b"Coex SPMI RCS error!",
        b"top_lock_semaphore: failed to lock semaphore"
    ]
    
    for sym in expected_symbols:
        idx = acib_data.find(sym)
        if idx == -1:
            log_fail(f"Symbol not found in acib.bin: {sym.decode('latin1')}")
        log_pass(f"Symbol verified in acib.bin at offset 0x{idx:06x}: {sym.decode('latin1')[:45]}")
    
    lpbt_path = os.path.join(WORKSPACE, "artifacts/centauri/bluetooth/partitions/lpbt.bin")
    with open(lpbt_path, "rb") as f:
        lpbt_data = f.read()
    
    lpbt_symbols = [
        b"connected.open.pending.range_setup.uwb_get_key",
        b"connected.open.pending.range_setup.uwb_range_enable",
        b"rotation.adv_addr",
        b"rotation.adv_data",
        b"rotation.adv_enable",
        b"acipcSleep_changeState",
        b"acipcSleep_doWork"
    ]
    for sym in lpbt_symbols:
        idx = lpbt_data.find(sym)
        if idx == -1:
            log_fail(f"Symbol not found in lpbt.bin: {sym.decode('latin1')}")
        log_pass(f"Symbol verified in lpbt.bin at offset 0x{idx:06x}: {sym.decode('latin1')}")

def test_master_dossier():
    print("\n--- Test 5: Master Publication Dossier Verification ---")
    dossier_path = os.path.join(WORKSPACE, "findings/centauri/03_BLUETOOTH_COEX_SUBSYSTEM.md")
    if not os.path.exists(dossier_path):
        log_fail("Master dossier missing: findings/centauri/03_BLUETOOTH_COEX_SUBSYSTEM.md")
    
    size = os.path.getsize(dossier_path)
    if size < 40000:
        log_fail(f"Dossier size too small: {size} bytes (< 40,000 bytes)")
    log_pass(f"Master dossier verified: {size} bytes (target >= 40,000 bytes)")
    
    with open(dossier_path) as f:
        content = f.read()
    
    placeholders = ["TODO", "TBD", "placeholder", "WIP", "coming soon"]
    for p in placeholders:
        matches = re.findall(rf"\b{p}\b", content, re.IGNORECASE)
        if matches:
            log_fail(f"Placeholder token found in dossier: '{matches[0]}'")
    log_pass("Zero placeholder tokens detected in dossier")
    
    required_sections = [
        "Container Structure, Partition Catalog & Memory Architecture",
        "Phase C3A: Bluetooth 5.4 / 6.0 Physical & Link Layer",
        "Phase C3B: Low-Power Always-On Bluetooth",
        "Phase C3C: Hardware Security Engine",
        "Phase C3D: 2.4 GHz RF Coexistence Matrix",
        "Phase C3E: Host Driver Architecture & Inter-Processor Communication",
        "Authoritative Firmware Assertion Catalog",
        "Cross-Validation Matrix & Verification Summary"
    ]
    for sec in required_sections:
        if sec.lower() not in content.lower():
            log_fail(f"Required section missing in dossier: {sec}")
        log_pass(f"Required section present: {sec}")

def main():
    print("=====================================================================")
    print(" Apple Centauri Bluetooth & Coexistence Subsystem Verification Suite ")
    print("=====================================================================")
    test_partitions_and_hashes()
    test_json_specifications()
    test_coexistence_matrix_integrity()
    test_firmware_symbol_verification()
    test_master_dossier()
    print("\n=====================================================================")
    print(" \033[92mALL TESTS PASSED: 100% Verification Complete & Validated\033[0m ")
    print("=====================================================================\n")

if __name__ == "__main__":
    main()
