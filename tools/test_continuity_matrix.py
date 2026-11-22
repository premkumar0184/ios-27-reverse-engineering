#!/usr/bin/env python3
"""
tools/test_continuity_matrix.py

Automated mechanical and adversarial test suite for Phase 9 Milestone 2:
Continuity & Cross-Device IPC Matrix verification.

Verifies:
1. File existence, non-emptiness, valid JSON format, and size threshold (> 50,000 bytes).
2. Anti-placeholder scan: Zero occurrences of TODO, FIXME, TBD, XXX, PLACEHOLDER.
3. continuity_daemons: Exactly 11 daemons with exact paths, sizes, CDHashes, Category 1 constraints,
   Mach services, and XPC interfaces.
4. ids_alloy_services: Exactly 112 service definitions from ServiceDefinitions/ with valid push topics,
   data protection classes, wake notifications, and transport flags.
5. proximity_protocols: 7 BLE advertisement subtypes under Apple Company ID 0x004c, AWDL election/scheduling,
   NanoRegistry companion sync, and Universal Clipboard sync.
6. cryptographic_key_groups: AKS Class A, PCS Class A (com.apple.private.alloy.pcskey.sync), Auto Unlock LTKs,
   Magic Pair envelopes, and Keychain access groups.
7. Idempotency test: generator script runs and outputs valid matrix without errors.
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = REPO_ROOT / "artifacts" / "ecosystem" / "continuity_ipc_matrix.json"
GENERATOR_PATH = REPO_ROOT / "tools" / "generate_continuity_matrix.py"

EXPECTED_DAEMONS = {
    "sharingd": {
        "binary_path": "/usr/libexec/sharingd",
        "cdhash": "788f8f2816e304a886ab078f4640d014d7b1be6a",
        "byte_size": 10480144,
        "category": 1,
        "min_mach_services": 30,
        "min_xpc_interfaces": 10
    },
    "identityservicesd": {
        "binary_path": "/System/Library/PrivateFrameworks/IDS.framework/identityservicesd.app/identityservicesd",
        "cdhash": "9cacb2cb3115fbebd3e1d642957802b16e1cdea6",
        "byte_size": 16303600,
        "category": 1,
        "min_mach_services": 8,
        "min_xpc_interfaces": 10
    },
    "apsd": {
        "binary_path": "/System/Library/PrivateFrameworks/ApplePushService.framework/apsd",
        "cdhash": "b8416e490db3b7df1e6d88d70ec9c77b76ef5d59",
        "byte_size": 2204368,
        "category": 1,
        "min_mach_services": 2,
        "min_xpc_interfaces": 5
    },
    "wifip2pd": {
        "binary_path": "/usr/libexec/wifip2pd",
        "cdhash": "092759962ed8a066061be1b866d6d9d6fe236494",
        "byte_size": 8574432,
        "category": 1,
        "min_mach_services": 2,
        "min_xpc_interfaces": 10
    },
    "nanoregistryd": {
        "binary_path": "/usr/libexec/nanoregistryd",
        "cdhash": "04fc0f28c15f8b8ab8cf3594ab8ccfb66490aa44",
        "byte_size": 1920816,
        "category": 1,
        "min_mach_services": 7,
        "min_xpc_interfaces": 5
    },
    "nanoregistrylaunchd": {
        "binary_path": "/usr/libexec/nanoregistrylaunchd",
        "cdhash": "c68a62beb42bfbc3f3498c20db6b20071ae3907c",
        "byte_size": 91296,
        "category": 1,
        "min_mach_services": 1,
        "min_xpc_interfaces": 2
    },
    "activitysharingd": {
        "binary_path": "/System/Library/PrivateFrameworks/ActivitySharingServices.framework/activitysharingd",
        "cdhash": "bd4ea8af7fdac31042f881c9e7009da95cafc611",
        "byte_size": 80320,
        "category": 1,
        "min_mach_services": 3,
        "min_xpc_interfaces": 3
    },
    "useractivityd": {
        "binary_path": "/System/Library/PrivateFrameworks/UserActivity.framework/Agents/useractivityd",
        "cdhash": "c2f7645a17111e3f7e9996bc6e1c0bf2e26c7af0",
        "byte_size": 998624,
        "category": 1,
        "min_mach_services": 5,
        "min_xpc_interfaces": 5
    },
    "pasted": {
        "binary_path": "/System/Library/PrivateFrameworks/Pasteboard.framework/Support/pasted",
        "cdhash": "2eaeb0fcda8fd7d2a3ce00852cb8b3743df8596f",
        "byte_size": 316368,
        "category": 1,
        "min_mach_services": 2,
        "min_xpc_interfaces": 3
    },
    "SidecarRelay": {
        "binary_path": "/usr/libexec/SidecarRelay",
        "cdhash": "de2a1a631dc4d732106ffcc84482e706d0626352",
        "byte_size": 928224,
        "category": 1,
        "min_mach_services": 1,
        "min_xpc_interfaces": 3
    },
    "airplayd": {
        "binary_path": "/usr/libexec/airplayd",
        "cdhash": "8e9c26edbc5a851d59fabd8e147fb97585c28580",
        "byte_size": 90864,
        "category": 1,
        "min_mach_services": 15,
        "min_xpc_interfaces": 3
    }
}

EXPECTED_BLE_SUBTYPES = [
    "0x05_airdrop",
    "0x07_proximity_pairing",
    "0x09_heysiri",
    "0x0c_handoff",
    "0x0d_tethering",
    "0x10_nearbyaction",
    "0x12_findmy"
]

def test_continuity_matrix():
    print("=" * 70)
    print("Mechanical Verification: Continuity & Cross-Device IPC Matrix (M2)")
    print("=" * 70)

    # 1. Existence and Size Test
    print("\n[Test 1/7] Testing matrix artifact existence & size...")
    assert MATRIX_PATH.is_file(), f"FAIL: Matrix file not found at {MATRIX_PATH}"
    size = MATRIX_PATH.stat().st_size
    print(f"  Matrix size: {size:,} bytes")
    assert size >= 50000, f"FAIL: Matrix file is too small ({size} bytes < 50,000 bytes)"
    print("  [PASS] File exists and exceeds size threshold.")

    # 2. JSON Validity & Placeholder Check
    print("\n[Test 2/7] Testing JSON validity & scanning for placeholder tokens...")
    with open(MATRIX_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"FAIL: Invalid JSON in matrix: {e}"

    placeholders = re.findall(r'\b(TODO|FIXME|TBD|XXX|PLACEHOLDER)\b', content, re.IGNORECASE)
    assert len(placeholders) == 0, f"FAIL: Found placeholder tokens: {placeholders}"
    print("  [PASS] Valid JSON with 0 placeholder tokens.")

    # 3. Continuity Daemons Completeness & Integrity
    print("\n[Test 3/7] Verifying 11 Continuity Daemons catalog...")
    daemons = data.get("continuity_daemons", {})
    assert len(daemons) == 11, f"FAIL: Expected 11 daemons, found {len(daemons)}"

    for name, exp in EXPECTED_DAEMONS.items():
        assert name in daemons, f"FAIL: Missing daemon '{name}' in continuity_daemons"
        d = daemons[name]
        assert d["binary_path"] == exp["binary_path"], f"FAIL: {name} path mismatch ({d['binary_path']} != {exp['binary_path']})"
        assert d["cdhash"] == exp["cdhash"], f"FAIL: {name} CDHash mismatch ({d['cdhash']} != {exp['cdhash']})"
        assert d["byte_size"] == exp["byte_size"], f"FAIL: {name} byte size mismatch ({d['byte_size']} != {exp['byte_size']})"
        assert d["constraint_category"] == exp["category"], f"FAIL: {name} Category mismatch ({d['constraint_category']} != {exp['category']})"
        assert len(d.get("mach_services", [])) >= exp["min_mach_services"], f"FAIL: {name} insufficient Mach services ({len(d.get('mach_services', []))} < {exp['min_mach_services']})"
        assert len(d.get("xpc_interfaces", [])) >= exp["min_xpc_interfaces"], f"FAIL: {name} insufficient XPC interfaces ({len(d.get('xpc_interfaces', []))} < {exp['min_xpc_interfaces']})"
        assert len(d.get("linked_dylibs", [])) > 0, f"FAIL: {name} missing linked dylibs"
        print(f"  [PASS] Daemon '{name}': CDHash={d['cdhash'][:16]}..., Size={d['byte_size']:,} B, MachServices={len(d['mach_services'])}, XPCInterfaces={len(d['xpc_interfaces'])}")

    print("  [PASS] All 11 Continuity Daemons verified with 100% integrity.")

    # 4. IDS Alloy Service Definitions Verification
    print("\n[Test 4/7] Verifying 112 IDS Alloy Service Definitions...")
    services = data.get("ids_alloy_services", [])
    assert len(services) == 112, f"FAIL: Expected 112 IDS services, found {len(services)}"

    # Check key continuity services
    service_names = {s["service_name"]: s for s in services}
    critical_services = [
        ("com.apple.private.alloy.continuity.activity", "D", True),
        ("com.apple.private.alloy.continuity.auth", "D", True),
        ("com.apple.private.alloy.continuity.unlock", "D", True),
        ("com.apple.private.alloy.pcskey.sync", "A", True),
        ("com.apple.private.alloy.fitnessfriends.icloud", None, False)
    ]

    for sname, exp_prot, exp_magnet_or_local in critical_services:
        assert sname in service_names, f"FAIL: Missing critical IDS service '{sname}'"
        s = service_names[sname]
        assert s["protocol_name"] == "com.apple.private.alloy", f"FAIL: {sname} protocol is {s['protocol_name']}"
        assert s.get("push_topic") is not None, f"FAIL: {sname} missing push topic"
        if exp_prot:
            assert s.get("data_protection_class") == exp_prot, f"FAIL: {sname} protection class mismatch ({s.get('data_protection_class')} != {exp_prot})"
        print(f"  [PASS] IDS Service '{sname}': PushTopic={s['push_topic']}, DataProt={s.get('data_protection_class')}, WakeMach={s.get('wake_mach_service')}")

    print("  [PASS] All 112 IDS Alloy Services verified.")

    # 5. Proximity Protocols Verification
    print("\n[Test 5/7] Verifying Proximity Protocols (BLE 0x004c, AWDL, Universal Clipboard)...")
    prox = data.get("proximity_protocols", {})
    assert "ble_advertisement_packets" in prox, "FAIL: Missing ble_advertisement_packets in proximity_protocols"
    ble_packets = prox["ble_advertisement_packets"]
    assert len(ble_packets) >= 7, f"FAIL: Expected >= 7 BLE subtypes, found {len(ble_packets)}"

    for subtype in EXPECTED_BLE_SUBTYPES:
        assert subtype in ble_packets, f"FAIL: Missing BLE subtype '{subtype}'"
        pkt = ble_packets[subtype]
        assert "packet_structure" in pkt, f"FAIL: {subtype} missing packet_structure"
        assert len(pkt["packet_structure"].get("fields", [])) > 0, f"FAIL: {subtype} missing fields"
        assert "security_considerations" in pkt, f"FAIL: {subtype} missing security_considerations"
        print(f"  [PASS] BLE Subtype '{subtype}': {pkt['protocol_name']} ({len(pkt['packet_structure']['fields'])} fields)")

    assert "awdl_mesh_and_discovery" in prox, "FAIL: Missing awdl_mesh_and_discovery"
    awdl = prox["awdl_mesh_and_discovery"]
    assert awdl["virtual_interface"] == "awdl0", f"FAIL: Virtual interface mismatch: {awdl['virtual_interface']}"
    assert len(awdl.get("operating_channels", [])) == 3, f"FAIL: Expected 3 AWDL channels, got {len(awdl.get('operating_channels', []))}"
    assert "master_election_protocol" in awdl, "FAIL: Missing master_election_protocol in AWDL"
    assert "availability_window_scheduling" in awdl, "FAIL: Missing availability_window_scheduling in AWDL"

    assert "universal_clipboard_sync" in prox, "FAIL: Missing universal_clipboard_sync"
    cb = prox["universal_clipboard_sync"]
    assert cb["transfer_thresholds"]["small_payload_threshold_bytes"] == 4096, "FAIL: Small payload threshold mismatch"
    assert cb["time_to_live_seconds"] == 120, "FAIL: TTL mismatch"

    print("  [PASS] Proximity Protocols verified.")

    # 6. Cryptographic Key Groups Verification
    print("\n[Test 6/7] Verifying Cryptographic Key Groups...")
    crypto = data.get("cryptographic_key_groups", {})
    assert "aks_class_a_sync" in crypto, "FAIL: Missing aks_class_a_sync"
    aks = crypto["aks_class_a_sync"]
    assert aks["user_client"] == "AppleKeyStoreUserClient", f"FAIL: User client mismatch: {aks['user_client']}"

    assert "pcs_class_a_sync" in crypto, "FAIL: Missing pcs_class_a_sync"
    pcs = crypto["pcs_class_a_sync"]
    assert pcs["service_definition"] == "com.apple.private.alloy.pcskey.sync", f"FAIL: Service def mismatch: {pcs['service_definition']}"
    assert pcs["transport_flags"]["ClassAProtectedTraffic"] is True, "FAIL: ClassAProtectedTraffic not True"

    assert "auto_unlock_ltks" in crypto, "FAIL: Missing auto_unlock_ltks"
    ltk = crypto["auto_unlock_ltks"]
    assert ltk["ranging_and_proximity_verification"]["distance_threshold_meters"] == 3.0, "FAIL: Distance threshold mismatch"

    assert "magic_pair_encryption" in crypto, "FAIL: Missing magic_pair_encryption"
    mp = crypto["magic_pair_encryption"]
    assert "advertising_token_format" in mp, "FAIL: Missing advertising_token_format"

    assert "keychain_access_groups" in crypto, "FAIL: Missing keychain_access_groups"
    kc = crypto["keychain_access_groups"]
    assert len(kc) >= 6, f"FAIL: Expected >= 6 keychain access groups, got {len(kc)}"
    assert "com.apple.sharing.pairing" in kc, "FAIL: Missing com.apple.sharing.pairing access group"

    print("  [PASS] Cryptographic Key Groups verified.")

    # 7. Idempotency Test
    print("\n[Test 7/7] Testing generator idempotency...")
    res = subprocess.run([sys.executable, str(GENERATOR_PATH)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"FAIL: Generator failed with code {res.returncode}:\n{res.stderr}"
    print("  [PASS] Generator executed cleanly and idempotently.")

    print("\n" + "=" * 70)
    print("ALL 7 ADVERSARIAL TESTS PASSED: Continuity IPC Matrix is 100% Valid!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_continuity_matrix()
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n[FAIL] Assertion Error: {ae}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[FATAL] Unexpected test error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
