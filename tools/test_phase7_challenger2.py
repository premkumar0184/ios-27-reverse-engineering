#!/usr/bin/env python3
"""
Adversarial Empirical Verification Suite — Challenger 2 (Phase 7)
==================================================================
Milestone: Phase 7 (Platform Security, TrustCache & Full Entitlement Matrix)
Author: Empirical Challenger 2 (Critic & Specialist)

Validates:
1. Soundness and mutual exclusivity of 4-Tier Entitlement Taxonomy.
2. Ground-truth physical verification of >= 10 high-profile entitlements
   directly against raw Mach-O LC_CODE_SIGNATURE SuperBlobs on disk.
3. Verification of findings/07_SECURITY_TRUST_ARCHITECTURE.md metrics,
   tables, assembly blocks, and anti-placeholder compliance.
4. Exact byte-level assembly verification of cited opcodes, PAC instructions,
   and strings against artifacts/kernel/kernelcache.release.raw.
5. TrustCache catalog invariants (7 containers, 5,204 entries, SHA-256, sorted).
6. CDHash database ground truth (AMFID flag 1, launchd, 680 mapped binaries).
7. progress.json schema, timestamps, and active phase advancement.
"""

import sys
import json
import struct
import plistlib
import re
from pathlib import Path

REPO_ROOT = Path("/home/prem/Projects/iOS 27")
ENTITLEMENTS_JSON = REPO_ROOT / "artifacts/security/entitlements_analysis.json"
TC_CATALOG_JSON = REPO_ROOT / "artifacts/security/trustcache_catalog.json"
CDHASH_DB_JSON = REPO_ROOT / "artifacts/security/cdhash_database.json"
FINDINGS_MD = REPO_ROOT / "findings/07_SECURITY_TRUST_ARCHITECTURE.md"
KERNELCACHE_RAW = REPO_ROOT / "artifacts/kernel/kernelcache.release.raw"
KEXT_CATALOG_RELEASE = REPO_ROOT / "artifacts/kernel/kext_catalog_release.json"
PROGRESS_JSON = REPO_ROOT / "progress.json"

SEARCH_DIRS = [
    REPO_ROOT / "artifacts/rootfs/extracted_daemons",
    REPO_ROOT / "artifacts/rootfs/binaries",
    REPO_ROOT / "artifacts/ui/Applications",
    REPO_ROOT / "artifacts/ui/SpringBoard",
    REPO_ROOT / "artifacts/rootfs"
]

class TestHarness:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, condition: bool, name: str, detail: str = ""):
        self.total += 1
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}" + (f" ({detail})" if detail else ""))
        else:
            self.failed += 1
            err = f"  [FAIL] {name}: {detail}"
            self.failures.append(err)
            print(err)

def find_binary_on_disk(sys_path: str) -> Path:
    rel = sys_path.lstrip("/")
    for sdir in SEARCH_DIRS:
        cand = sdir / rel
        if cand.is_file():
            return cand
    fname = Path(sys_path).name
    for sdir in SEARCH_DIRS:
        for m in sdir.rglob(fname):
            if m.is_file() and m.stat().st_size > 0:
                return m
    return None

def extract_raw_macho_entitlements(file_path: Path):
    with open(file_path, "rb") as f:
        data = f.read()
    if len(data) < 32:
        return None
    magic_le = struct.unpack("<I", data[:4])[0]
    if magic_le != 0xfeedfacf:
        return None
    cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIII", data[4:32])
    offset = 32
    cs_offset, cs_size = 0, 0
    for _ in range(ncmds):
        if offset + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack("<II", data[offset:offset+8])
        if cmd == 0x1d:
            cs_offset, cs_size = struct.unpack("<II", data[offset+8:offset+16])
            break
        offset += cmdsize
    if cs_offset == 0 or cs_offset + cs_size > len(data):
        return None
    cs_data = data[cs_offset:cs_offset+cs_size]
    if len(cs_data) < 12:
        return None
    sb_magic, sb_len, sb_count = struct.unpack(">III", cs_data[:12])
    if sb_magic != 0xfade0cc0:
        return None
    idx_off = 12
    for _ in range(sb_count):
        if idx_off + 8 > len(cs_data):
            break
        slot_type, blob_offset = struct.unpack(">II", cs_data[idx_off:idx_off+8])
        idx_off += 8
        if blob_offset + 8 <= len(cs_data):
            blob_magic, blob_len = struct.unpack(">II", cs_data[blob_offset:blob_offset+8])
            if blob_magic == 0xfade7171 or slot_type == 5:
                xml_bytes = cs_data[blob_offset+8:blob_offset+blob_len]
                try:
                    return plistlib.loads(xml_bytes)
                except:
                    pass
    return None

def run_all_tests():
    harness = TestHarness()
    print("=" * 70)
    print("CHALLENGER 2: ADVERSARIAL STRESS TEST & BOUNDARY ANALYSIS")
    print("=" * 70)

    # -------------------------------------------------------------
    # Test Suite 1: Entitlement Taxonomy Soundness & Partition Math
    # -------------------------------------------------------------
    print("\n[*] Suite 1: Entitlement Taxonomy Soundness & Partition Math")
    harness.check(ENTITLEMENTS_JSON.is_file(), "entitlements_analysis.json exists")
    with open(ENTITLEMENTS_JSON, "r", encoding="utf-8") as f:
        ent_data = json.load(f)

    meta = ent_data.get("metadata", {})
    tax = ent_data.get("taxonomy", {})
    bins = ent_data.get("binaries", {})

    harness.check(meta.get("total_binaries_cataloged") == 680, "Metadata total binaries == 680", f"got {meta.get('total_binaries_cataloged')}")
    harness.check(meta.get("unique_entitlements_cataloged") == 4463, "Metadata unique entitlements == 4463", f"got {meta.get('unique_entitlements_cataloged')}")

    tier1 = set(tax.get("root_hardware_capabilities", []))
    tier2 = set(tax.get("private_apple_entitlements", []))
    tier3 = set(tax.get("tcc_access_overrides", {}).get("entitlement_keys", []))
    tier4 = set(tax.get("mach_lookup_assertions", {}).get("entitlement_keys", []))
    tier_std = set(tax.get("standard_capabilities", []))

    harness.check(len(tier1) == 238, "Tier 1 (Root/HW) count == 238", f"got {len(tier1)}")
    harness.check(len(tier2) == 1620, "Tier 2 (Private Apple) count == 1620", f"got {len(tier2)}")
    harness.check(len(tier3) == 24, "Tier 3 (TCC) count == 24", f"got {len(tier3)}")
    harness.check(len(tier4) == 8, "Tier 4 (Mach lookup) count == 8", f"got {len(tier4)}")
    harness.check(len(tier_std) == 2573, "Standard Capabilities count == 2573", f"got {len(tier_std)}")

    # Check partition disjointness
    tiers = {
        "Tier 1": tier1,
        "Tier 2": tier2,
        "Tier 3": tier3,
        "Tier 4": tier4,
        "Standard": tier_std
    }
    tier_names = list(tiers.keys())
    overlaps = []
    for i in range(len(tier_names)):
        for j in range(i+1, len(tier_names)):
            t1, t2 = tier_names[i], tier_names[j]
            overlap = tiers[t1] & tiers[t2]
            if overlap:
                overlaps.append((t1, t2, overlap))
    harness.check(len(overlaps) == 0, "All 5 taxonomy partitions are 100% mutually disjoint", f"Overlaps: {overlaps}")
    union_size = len(set.union(*tiers.values()))
    harness.check(union_size == 4463, "Partitions exactly cover the 4,463 cataloged keys", f"Union size: {union_size}")

    # -------------------------------------------------------------
    # Test Suite 2: Ground-Truth Binary Sampling (>= 10 Entitlements)
    # -------------------------------------------------------------
    print("\n[*] Suite 2: Ground-Truth Physical Binary Sampling (12 Sample Pairs)")
    sample_pairs = [
        ("com.apple.private.pmap.load-trust-cache", "/sbin/launchd"),
        ("com.apple.private.pmap.load-trust-cache", "/usr/libexec/cryptexd"),
        ("com.apple.private.amfi.can-allow-non-platform", "/sbin/launchd"),
        ("com.apple.private.kernel.system-override", "/sbin/launchd"),
        ("com.apple.private.kernel.system-override", "/usr/libexec/cameracaptured"),
        ("platform-application", "/Applications/private/var/staged_system_apps/MobileSMS.app/MobileSMS"),
        ("com.apple.private.security.no-sandbox", "/usr/libexec/lskdd"),
        ("com.apple.private.security.storage.AppDataContainers", "/usr/libexec/amfid"),
        ("com.apple.private.tcc.allow", "/usr/sbin/bluetoothd"),
        ("com.apple.private.tcc.allow", "/Applications/private/var/staged_system_apps/Reminders.app/Reminders"),
        ("com.apple.security.exception.mach-lookup.global-name", "/Applications/private/var/staged_system_apps/Reminders.app/Reminders"),
        ("com.apple.private.memorystatus", "/usr/libexec/containermanagerd")
    ]

    for ent_key, bin_path in sample_pairs:
        disk_path = find_binary_on_disk(bin_path)
        harness.check(disk_path is not None and disk_path.is_file(), f"Binary exists on disk: {bin_path}", str(disk_path))
        if disk_path:
            raw_ents = extract_raw_macho_entitlements(disk_path)
            harness.check(raw_ents is not None, f"Extracted raw Mach-O entitlements from {bin_path}")
            if raw_ents:
                harness.check(ent_key in raw_ents, f"Raw binary on disk contains {ent_key}")
                json_val = bins.get(bin_path, {}).get("entitlements", {}).get(ent_key)
                disk_val = raw_ents.get(ent_key)
                harness.check(json_val == disk_val, f"Value equality for {bin_path} -> {ent_key}")

    print("\n[*] Suite 2b: kTCCServiceCamera Ground-Truth Assertion Verification")
    camera_binaries = [
        "/System/Library/Frameworks/CoreTelephony.framework/Support/CommCenter",
        "/Applications/private/var/staged_system_apps/Reminders.app/Reminders",
        "/Applications/private/var/staged_system_apps/MobileSMS.app/MobileSMS",
        "/Applications/private/var/staged_system_apps/MobileSafari.app/MobileSafari"
    ]
    for cb in camera_binaries:
        disk_p = find_binary_on_disk(cb)
        harness.check(disk_p is not None, f"Camera holder binary exists: {cb}")
        if disk_p:
            raw_e = extract_raw_macho_entitlements(disk_p)
            allow_list = raw_e.get("com.apple.private.tcc.allow", []) if raw_e else []
            over_list = raw_e.get("com.apple.private.tcc.allow.overridable", []) if raw_e else []
            has_cam = ("kTCCServiceCamera" in allow_list) or ("kTCCServiceCamera" in over_list)
            harness.check(has_cam, f"{cb} holds kTCCServiceCamera in raw code signature")

    # -------------------------------------------------------------
    # Test Suite 3: Findings Document Metrics & Anti-Placeholder
    # -------------------------------------------------------------
    print("\n[*] Suite 3: Findings Document Metrics & Anti-Placeholder Scan")
    harness.check(FINDINGS_MD.is_file(), "07_SECURITY_TRUST_ARCHITECTURE.md exists")
    content = FINDINGS_MD.read_text(encoding="utf-8")
    doc_size = len(content.encode("utf-8"))
    harness.check(doc_size >= 2500, f"Document size >= 2500 bytes", f"actual: {doc_size} bytes")

    banned_patterns = [
        r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b", r"\bLOREM IPSUM\b",
        r"\bINSERT HERE\b", r"\bCOMING SOON\b", r"\bOMITTED FOR BREVITY\b",
        r"\bNOT YET IMPLEMENTED\b", r"\[TBD\]", r"\[TODO\]", r"\bFIXME\b", r"\bXXX\b"
    ]
    banned_hits = []
    for pat in banned_patterns:
        m = list(re.finditer(pat, content, re.IGNORECASE))
        if m:
            banned_hits.append((pat, [match.group() for match in m]))
    harness.check(len(banned_hits) == 0, "Zero banned placeholder tokens in findings", f"Hits: {banned_hits}")

    h2_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s+", content, re.MULTILINE))
    harness.check(h2_count >= 5, f"Markdown H2 sections >= 5", f"actual: {h2_count}")
    harness.check(h3_count >= 10, f"Markdown H3 sections >= 10", f"actual: {h3_count}")

    table_rows = len(re.findall(r"\|.*\|.*\|", content))
    harness.check(table_rows >= 20, f"Markdown table rows >= 20", f"actual: {table_rows}")

    asm_blocks = len(re.findall(r"```(?:assembly|arm64|asm)", content))
    harness.check(asm_blocks >= 3, f"Verbatim assembly blocks >= 3", f"actual: {asm_blocks}")

    # -------------------------------------------------------------
    # Test Suite 4: Verbatim Assembly Verification vs Kernelcache
    # -------------------------------------------------------------
    print("\n[*] Suite 4: Verbatim Assembly Verification vs Raw Kernelcache")
    harness.check(KERNELCACHE_RAW.is_file(), "kernelcache.release.raw exists")
    with open(KERNELCACHE_RAW, "rb") as kf:
        # Base VA: 0xfffffe0007004000
        # 1. mac_vnode_check_signature at 0xfffffe0009297d7c -> offset 0x2293d7c
        kf.seek(0x2293d7c)
        vnode_code = kf.read(48)
        # pacibsp: 7f 23 03 d5
        harness.check(vnode_code[:4] == bytes.fromhex("7f 23 03 d5"), "mac_vnode_check_signature prologue is pacibsp (0xd503237f)")
        # stp x28, x27, [sp, #-0x60]!: fc 6f ba a9
        harness.check(vnode_code[4:8] == bytes.fromhex("fc 6f ba a9"), "mac_vnode_check_signature spills x28, x27")
        # sub sp, sp, #0x330: ff c3 0c d1 at +0x20
        harness.check(vnode_code[0x20:0x24] == bytes.fromhex("ff c3 0c d1"), "mac_vnode_check_signature reserves 816-byte frame (sub sp, sp, #0x330)")

        # pacda x16, x1 at 0x2293e24: 30 0a c1 da
        kf.seek(0x2293e24)
        harness.check(kf.read(4) == bytes.fromhex("30 0a c1 da"), "mac_vnode_check_signature executes pacda x16, x1 at 0xfffffe0009297e24")

        # autda x16, x27 at 0x2293e70: 90 1b c1 da
        kf.seek(0x2293e70)
        harness.check(kf.read(4) == bytes.fromhex("90 1b c1 da"), "mac_vnode_check_signature executes autda x16, x27 at 0xfffffe0009297e70")

        # AMFI string at 0xfffffe000766c6c4 -> offset 0x6686c4
        kf.seek(0x6686c4)
        str_amfi = kf.read(51)
        harness.check(str_amfi == b"AMFI: vnode_check_signature called with platform %d", "AMFI vnode_check_signature format string exists at 0xfffffe000766c6c4")

        # 2. _check_cdhash_in_trustcache at 0xfffffe0009299730 -> offset 0x2295730
        kf.seek(0x2295730)
        tc_code = kf.read(48)
        harness.check(tc_code[:4] == bytes.fromhex("7f 23 03 d5"), "_check_cdhash_in_trustcache prologue is pacibsp")
        harness.check(tc_code[4:8] == bytes.fromhex("ff c3 04 d1"), "_check_cdhash_in_trustcache allocates 304-byte frame (sub sp, sp, #0x130)")
        harness.check(tc_code[0x20:0x24] == bytes.fromhex("a8 75 ff d0"), "_check_cdhash_in_trustcache references master in-kernel trustcache head (adrp x8)")

        # 3. mac_cred_label_update_execve at 0xfffffe00092961f4 -> offset 0x22921f4
        kf.seek(0x22921f4)
        cred_code = kf.read(40)
        harness.check(cred_code[:4] == bytes.fromhex("7f 23 03 d5"), "mac_cred_label_update_execve prologue is pacibsp")
        harness.check(cred_code[4:8] == bytes.fromhex("ff 43 02 d1"), "mac_cred_label_update_execve allocates 144-byte frame (sub sp, sp, #0x90)")

        # 4. Sandbox pre-compiled bytecode at 0xfffffe0007b79330 -> offset 0xb75330
        kf.seek(0xb75330)
        sb_head = kf.read(16)
        harness.check(len(sb_head) == 16, "Sandbox bytecode container accessible at 0xfffffe0007b79330")

    # -------------------------------------------------------------
    # Test Suite 5: TrustCache & CDHash Database Invariants
    # -------------------------------------------------------------
    print("\n[*] Suite 5: TrustCache & CDHash Database Invariants")
    with open(TC_CATALOG_JSON, "r", encoding="utf-8") as f:
        tc_list = json.load(f)
    harness.check(len(tc_list) == 7, "TrustCache catalog contains exactly 7 containers", f"got {len(tc_list)}")
    total_tc_entries = sum(c.get("entry_count", 0) for c in tc_list)
    harness.check(total_tc_entries == 5204, "Total TrustCache entries == 5,204", f"got {total_tc_entries}")
    all_sha256 = all(c.get("hash_type") == "SHA-256 (type 2)" for c in tc_list) and all(e.get("hash_type") == 2 for c in tc_list for e in c.get("entries", []))
    harness.check(all_sha256, "All 7 TrustCache containers declare SHA-256 (hash_type == 2 across all 5,204 entries)")
    all_sorted = all(c.get("is_sorted") is True for c in tc_list)
    harness.check(all_sorted, "All 7 TrustCache containers have is_sorted == True")

    with open(CDHASH_DB_JSON, "r", encoding="utf-8") as f:
        cd_db = json.load(f)
    cd_meta = cd_db.get("metadata", {})
    harness.check(cd_meta.get("total_trustcache_entries") == 5204, "CDHash DB total entries == 5204")
    harness.check(cd_meta.get("unique_cdhashes") == 4527, "CDHash DB unique hashes == 4527")
    harness.check(cd_meta.get("total_mapped_binaries") == 680, "CDHash DB mapped binaries == 680")

    amfid_hash = "8c8cbe476a8882df62f8250d7f1e7903778445f6"
    harness.check(amfid_hash in cd_db["cdhashes"], "AMFID CDHash exists in database")
    amfid_entry = cd_db["cdhashes"].get(amfid_hash, {})
    harness.check(amfid_entry.get("matched") is True, "AMFID is matched to disk binary")
    harness.check(amfid_entry.get("trustcache_sources", [{}])[0].get("flags") == 1, "AMFID declares flag == 1 (AMFID bootstrap gate)")

    # -------------------------------------------------------------
    # Test Suite 6: progress.json Rigor & State Machine
    # -------------------------------------------------------------
    print("\n[*] Suite 6: progress.json Rigor & Active Phase Advancement")
    with open(PROGRESS_JSON, "r", encoding="utf-8") as f:
        prog = json.load(f)
    harness.check(prog.get("active_phase_id") == "phase_08_graphify_synthesis", "active_phase_id advanced to phase_08_graphify_synthesis")
    phases = {p["id"]: p for p in prog.get("phases", [])}
    p7 = phases.get("phase_07_security_trust_architecture")
    harness.check(p7 is not None, "Phase 7 exists in progress.json")
    if p7:
        harness.check(p7.get("status") == "completed", "Phase 7 status is 'completed'")
        harness.check(p7.get("verified_by") == "tools/verify_phase.py", "Phase 7 verified_by == 'tools/verify_phase.py'")
        ts = p7.get("completed_at", "")
        harness.check(bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts)), "Phase 7 completed_at is valid ISO 8601 timestamp", ts)
        notes = p7.get("notes", [])
        harness.check(len(notes) >= 4, f"Phase 7 notes comprehensive (>= 4 paragraphs)", f"got {len(notes)}")

    # -------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"EMPIRICAL AUDIT RESULTS: {harness.passed}/{harness.total} checks PASSED, {harness.failed} FAILED")
    print("=" * 70)
    if harness.failed > 0:
        print("[!] FAILURES:")
        for fail in harness.failures:
            print(fail)
        sys.exit(1)
    else:
        print("[+] ALL ADVERSARIAL CHECKS PASSED EMPIRICALLY WITH ZERO DEFECTS.")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()
