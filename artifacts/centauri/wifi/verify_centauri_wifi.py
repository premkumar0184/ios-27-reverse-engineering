#!/usr/bin/env python3
"""
Apple Centauri Wi-Fi 7 (802.11be) MAC & PHY Subsystem Verification Suite
Author: Antigravity Clean-Room Reverse Engineering Team
Target: Apple Centauri (Proxima si-b0) Wi-Fi 7 Subsystem
"""

import os
import sys
import json
import hashlib
import struct
import re

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

PASS_COUNT = 0
FAIL_COUNT = 0

def pass_test(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"{GREEN}[PASS]{RESET} {msg}")

def fail_test(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"{RED}[FAIL]{RESET} {msg}")

def check_file(path, min_size=1):
    if not os.path.exists(path):
        fail_test(f"File missing: {path}")
        return False
    size = os.path.getsize(path)
    if size < min_size:
        fail_test(f"File too small ({size} < {min_size}): {path}")
        return False
    return True

print("=" * 72)
print(" Apple Centauri Wi-Fi 7 (802.11be) MAC & PHY Subsystem Verification Suite")
print("=" * 72)

# 1. Deliverables existence & volume
print("\n--- Test 1: Deliverables Inventory & Sizing ---")
matrix_file = "artifacts/centauri/wifi/wifi7_feature_matrix.json"
dossier_file = "findings/centauri/02_WIFI7_MAC_PHY_SUBSYSTEM.md"

if check_file(matrix_file, 50000):
    pass_test(f"Feature matrix exists: {matrix_file} ({os.path.getsize(matrix_file)} bytes >= 50KB)")

if check_file(dossier_file, 30000):
    pass_test(f"Master dossier exists: {dossier_file} ({os.path.getsize(dossier_file)} bytes >= 30KB)")

# 2. Zero-placeholder scan
print("\n--- Test 2: Zero-Placeholder Quality Gate ---")
forbidden_patterns = [r"\bTODO\b", r"\bTBD\b", r"\bplaceholder\b", r"\bPLACEHOLDER\b", r"\bFIXME\b"]

for fpath in [matrix_file, dossier_file]:
    with open(fpath) as f:
        content = f.read()
    clean = True
    for pat in forbidden_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            fail_test(f"Found {len(matches)} placeholder tokens matching {pat} in {fpath}")
            clean = False
    if clean:
        pass_test(f"Zero placeholder tokens found in {fpath}")

# 3. Partition verification against ftab manifest
print("\n--- Test 3: Wi-Fi Firmware Partitions Integrity & Hashes ---")
manifest_path = "artifacts/centauri/firmware/ftab_manifest.json"
with open(manifest_path) as f:
    manifest = json.load(f)

partitions_by_tag = {p["tag"]: p for p in manifest["partitions"]}

wifi_tags = ["aciw", "w2lp", "wftp", "wfrp", "w5lp", "w5pp", "w2pp", "scaw", "w2lm", "w5lm", "w2pm", "w5pm", "w2pt", "w5pt"]

for tag in wifi_tags:
    pinfo = partitions_by_tag.get(tag)
    if not pinfo:
        fail_test(f"Partition {tag} not in manifest")
        continue
    fpath = os.path.join("artifacts/centauri/firmware/partitions", pinfo["filename"])
    if not os.path.exists(fpath):
        fail_test(f"Partition file missing: {fpath}")
        continue
    act_sz = os.path.getsize(fpath)
    exp_sz = pinfo["size_dec"]
    exp_sha = pinfo["sha256"]
    with open(fpath, "rb") as bf:
        act_sha = hashlib.sha256(bf.read()).hexdigest()
    if act_sz == exp_sz and act_sha == exp_sha:
        pass_test(f"Partition {tag:4s}: {act_sz:7d} B, SHA256 verified ({act_sha[:16]}...)")
    else:
        fail_test(f"Partition {tag} mismatch: sz={act_sz} (exp {exp_sz}), sha={act_sha} (exp {exp_sha})")

# 4. ARM Cortex-M Vector Tables & Reset Addresses
print("\n--- Test 4: ARM Cortex-M Vector Tables & Reset Handlers ---")
expected_vectors = {
    "w2lp": (0x1002fff0, 0x00100bd5),
    "w2lm": (0x1002fff0, 0x00100bd5),
    "w2pp": (0x10023ff0, 0x0010090d),
    "w2pm": (0x10023ff0, 0x0010090d),
    "w2pt": (0x10023ff0, 0x0010090d),
    "w5lp": (0x1002fff0, 0x00100bd5),
    "w5lm": (0x1002fff0, 0x00100bd5),
    "w5pp": (0x1002fff0, 0x0010090d),
    "w5pm": (0x1002fff0, 0x0010090d),
    "w5pt": (0x1002fff0, 0x0010090d),
}

for tag, (exp_sp, exp_reset) in expected_vectors.items():
    pinfo = partitions_by_tag[tag]
    fpath = os.path.join("artifacts/centauri/firmware/partitions", pinfo["filename"])
    with open(fpath, "rb") as bf:
        head = bf.read(16)
        sp, reset = struct.unpack("<II", head[:8])
    if sp == exp_sp and reset == exp_reset:
        pass_test(f"Vector Table {tag:4s}: Initial SP=0x{sp:08x}, Reset=0x{reset:08x} (Entry=0x{reset-1:08x})")
    else:
        fail_test(f"Vector Table {tag:4s}: SP=0x{sp:08x} (exp 0x{exp_sp:08x}), Reset=0x{reset:08x} (exp 0x{exp_reset:08x})")

# 5. Wi-Fi 7 Protocol Constants from Feature Matrix
print("\n--- Test 5: Wi-Fi 7 Feature Matrix Protocol Invariants ---")
with open(matrix_file) as f:
    matrix = json.load(f)

# MLO links
mlo = matrix["wifi7_features"]["multi_link_operation_mlo"]
sta1 = mlo["link_architecture"]["mld_sta_primary"]["id"]
sta2 = mlo["link_architecture"]["mld_sta_secondary"]["id"]
dyn_first = mlo["link_architecture"]["dynamic_mlo_links_range"]["first"]
dyn_last = mlo["link_architecture"]["dynamic_mlo_links_range"]["last"]

if sta1 == 2 and sta2 == 3 and dyn_first == 13 and dyn_last == 33:
    pass_test(f"MLD Link Architecture: Primary STA={sta1}, Secondary STA={sta2}, Dynamic Range=[{dyn_first}..{dyn_last}]")
else:
    fail_test(f"MLD Link mismatch: sta1={sta1}, sta2={sta2}, dyn=[{dyn_first}..{dyn_last}]")

# 4096-QAM
qam = matrix["wifi7_features"]["modulation_4096_qam"]
ppdu_eht = qam["ppdu_type_eht"]["rate_ppdu_enum"]["id"]
bits_sym = qam["constellation_parameters"]["bits_per_symbol"]
evm_floor = qam["constellation_parameters"]["evm_floor_requirement_db"]

if ppdu_eht == 6 and bits_sym == 12 and evm_floor == -38.0:
    pass_test(f"4096-QAM Modulation: RATE_PPDU_EHT_E={ppdu_eht}, Bits/Symbol={bits_sym}, EVM Floor={evm_floor} dB")
else:
    fail_test(f"4096-QAM mismatch: ppdu_eht={ppdu_eht}, bits={bits_sym}, evm={evm_floor}")

# 320 MHz Channelization
chan320 = matrix["wifi7_features"]["channelization_320mhz"]
sub_count = chan320["subchannel_count"]
p0 = chan320["primary_20mhz_channel_positions"]["subchannel_0"]["enum_id"]
p15 = chan320["primary_20mhz_channel_positions"]["subchannel_15"]["enum_id"]

if sub_count == 16 and p0 == 15 and p15 == 30:
    pass_test(f"320 MHz Channelization: 16 subchannels, primary_0={p0}, primary_15={p15}")
else:
    fail_test(f"320 MHz mismatch: count={sub_count}, p0={p0}, p15={p15}")

# 6. Regulatory Power Tables
print("\n--- Test 6: Regulatory Power Tables Magic & Version ---")
p_tables = ["41_P005.bin", "42_P006.bin", "43_P007.bin", "44_P008.bin", "45_P009.bin", "46_P014.bin", "47_P015.bin", "48_P032.bin"]
p_clean = True
for pt in p_tables:
    p_path = os.path.join("artifacts/centauri/firmware/partitions", pt)
    with open(p_path, "rb") as f:
        head = f.read(16)
    magic = head[:4].hex()
    ver = head[4:8].decode("ascii", errors="ignore")
    if magic != "fecafeca" or ver != "10.0":
        fail_test(f"Power table {pt} bad header: magic={magic}, ver={ver}")
        p_clean = False
if p_clean:
    pass_test("All 8 Regulatory Power Tables verified: Magic 0xCAFECAFE, Version 10.0")

# 7. Overall status
print("\n" + "=" * 72)
if FAIL_COUNT == 0:
    print(f"{GREEN}ALL {PASS_COUNT} WI-FI 7 TESTS PASSED: 100% VERIFICATION COMPLETE{RESET}")
    print("=" * 72)
    sys.exit(0)
else:
    print(f"{RED}{FAIL_COUNT} TESTS FAILED, {PASS_COUNT} PASSED{RESET}")
    print("=" * 72)
    sys.exit(1)
