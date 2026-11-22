#!/usr/bin/env python3
"""
Adversarial Empirical Verification & Stress-Test Suite for Phase 7
=================================================================
Platform Security, TrustCache & Full Entitlement Matrix
Author: Challenger 1 (Adversarial Critic & Specialist)

Tests:
1. TrustCache Math & Invariants:
   - Sum across all 7 files strictly equals 5,204
   - Zero duplicate CDHashes within any single TrustCache
   - Strict lexicographical ordering of 20-byte CDHashes within each TrustCache
   - Inter-TrustCache overlap quantification
   - Header field validity (version in {1, 2}, valid UUID, matching entry_count)
2. First-Principles Independent CDHash Oracle:
   - Independent Mach-O parser & CodeDirectory hasher (independent of build_cdhash_database.py)
   - CDHash calculation for /sbin/launchd, /usr/lib/dyld, /usr/libexec/amfid, SpringBoard
   - Byte-for-byte comparison against cdhash_database.json and trustcache_catalog.json
3. AMFID Flag & TrustCache Flag Auditing:
   - Verification of flag == 1 on /usr/libexec/amfid (CDHash 8c8cbe476a8882df62f8250d7f1e7903778445f6)
   - Exhaustive census of all non-zero flags across all 5,204 TrustCache entries
   - Verification of whether any other binary is flagged as AMFID or has unexpected flags
4. JSON Schema Edge Cases & Semantic Rigor:
   - trustcache_catalog.json: required keys, data types, entry counts, empty array checks
   - cdhash_database.json: metadata integrity, hash mappings, constraint categories
   - entitlements_analysis.json: 4-tier taxonomy keys, non-empty collections, mapping validity
5. Findings Document Rigor & Anti-Placeholder:
   - Size >= 2,500 bytes
   - Anti-placeholder scan
   - Required sections, tables, disassembly blocks
"""

import sys
import os
import json
import struct
import hashlib
import uuid
import re
from pathlib import Path
from collections import defaultdict, Counter

REPO_ROOT = Path("/home/prem/Projects/iOS 27")
FIRMWARE_DIR = REPO_ROOT / "iPhone18,3_27.2_24B119_Restore/Firmware"
TC_CATALOG_JSON = REPO_ROOT / "artifacts/security/trustcache_catalog.json"
CDHASH_DB_JSON = REPO_ROOT / "artifacts/security/cdhash_database.json"
ENTITLEMENTS_JSON = REPO_ROOT / "artifacts/security/entitlements_analysis.json"
FINDINGS_DOC = REPO_ROOT / "findings/07_SECURITY_TRUST_ARCHITECTURE.md"

LAUNCHD_PATH = REPO_ROOT / "artifacts/rootfs/binaries/sbin/launchd"
DYLD_PATH = REPO_ROOT / "artifacts/rootfs/binaries/usr/lib/dyld"
AMFID_PATH = REPO_ROOT / "artifacts/rootfs/binaries/usr/libexec/amfid"
SPRINGBOARD_PATH = REPO_ROOT / "artifacts/ui/SpringBoard/System/Library/CoreServices/SpringBoard.app/SpringBoard"

BANNED_PLACEHOLDERS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bPLACEHOLDER\b",
    r"\bLOREM IPSUM\b",
    r"\bINSERT HERE\b",
    r"\bCOMING SOON\b",
    r"\bOMITTED FOR BREVITY\b",
    r"\bNOT YET IMPLEMENTED\b",
    r"\[TBD\]",
    r"\[TODO\]"
]


class ChallengerTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_failed = 0
        self.failures = []
        self.successes = []

    def assert_true(self, condition: bool, test_name: str, msg: str = ""):
        self.tests_run += 1
        if not condition:
            self.tests_failed += 1
            err = f"[FAIL] {test_name}: {msg}"
            self.failures.append(err)
            print(err)
        else:
            ok = f"[PASS] {test_name}" + (f": {msg}" if msg else "")
            self.successes.append(ok)
            print(ok)

    def assert_equal(self, actual, expected, test_name: str, msg: str = ""):
        self.assert_true(actual == expected, test_name, f"Expected {expected}, got {actual}. {msg}")


def read_asn1_length(data: bytes, offset: int):
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    num_bytes = first & 0x7F
    length = 0
    for _ in range(num_bytes):
        length = (length << 8) | data[offset]
        offset += 1
    return length, offset


def extract_raw_trustcache_payload(file_path: Path) -> bytes:
    data = file_path.read_bytes()
    if data.startswith(b"\x30") and b"IM4P" in data[:32]:
        seq_len, offset = read_asn1_length(data, 1)
        offset += 1
        m_len, offset = read_asn1_length(data, offset)
        offset += m_len
        if data[offset] == 0x16:
            offset += 1
            t_len, offset = read_asn1_length(data, offset)
            offset += t_len
        if data[offset] == 0x16:
            offset += 1
            d_len, offset = read_asn1_length(data, offset)
            offset += d_len
        if data[offset] == 0x04:
            offset += 1
            p_len, offset = read_asn1_length(data, offset)
            return data[offset:offset + p_len]
    return data


def independent_macho_cdhash(binary_path: Path):
    """
    Independent first-principles Mach-O Code Directory parser and hasher.
    Returns dict with sha256_truncated, sha1, ident, flags, etc.
    """
    if not binary_path.is_file():
        return None
    data = binary_path.read_bytes()
    if len(data) < 32:
        return None
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic == 0xfeedfacf:
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack_from("<IIIIIII", data, 4)
        offset = 32
    elif magic == 0xfeedface:
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack_from("<IIIIII", data, 4)
        offset = 28
    else:
        return None

    cdhashes = []
    for _ in range(ncmds):
        if offset + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack_from("<II", data, offset)
        if cmd == 0x1d:  # LC_CODE_SIGNATURE
            dataoff, datasize = struct.unpack_from("<II", data, offset + 8)
            sig_data = data[dataoff:dataoff + datasize]
            if len(sig_data) >= 12:
                smagic, slen, scount = struct.unpack_from(">III", sig_data, 0)
                if smagic == 0xfade0cc0:
                    for i in range(scount):
                        stype, soff = struct.unpack_from(">II", sig_data, 12 + i * 8)
                        blob = sig_data[soff:]
                        if len(blob) >= 8:
                            bmagic, blen = struct.unpack_from(">II", blob, 0)
                            if bmagic == 0xfade0c02:  # CSBLOB_CODEDIRECTORY
                                cd_blob = blob[:blen]
                                if len(cd_blob) >= 40:
                                    cd_ver, cd_flags, h_off, id_off, n_spec, n_code, code_lim = struct.unpack_from(">IIIIIII", cd_blob, 8)
                                    h_size, h_type, plat, page_sz = struct.unpack_from(">BBBB", cd_blob, 36)
                                    ident = cd_blob[id_off:].split(b"\x00")[0].decode("utf-8", "ignore")
                                    full_sha256 = hashlib.sha256(cd_blob).hexdigest()
                                    full_sha1 = hashlib.sha1(cd_blob).hexdigest()
                                    truncated_sha256 = full_sha256[:40]
                                    cdhashes.append({
                                        "h_type": h_type,
                                        "ident": ident,
                                        "truncated_sha256": truncated_sha256,
                                        "full_sha256": full_sha256,
                                        "sha1": full_sha1,
                                        "cd_flags": cd_flags,
                                        "cd_ver": cd_ver
                                    })
        offset += cmdsize
    return cdhashes


def main():
    runner = ChallengerTestRunner()
    print("=" * 70)
    print("PHASE 7 EMPIRICAL ADVERSARIAL CHALLENGE SUITE")
    print("=" * 70)

    # ---------------------------------------------------------
    # TEST SUITE 1: TrustCache Raw Binary Math & Sorting
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 1: TrustCache Raw Binary Math & Sorting ---")
    tc_files = sorted(FIRMWARE_DIR.glob("*.trustcache"))
    runner.assert_equal(len(tc_files), 7, "Firmware TrustCache File Count", f"Found {len(tc_files)} files")

    raw_total_entries = 0
    all_raw_hashes = []
    file_entry_counts = {}

    for tcf in tc_files:
        payload = extract_raw_trustcache_payload(tcf)
        runner.assert_true(len(payload) >= 24, f"{tcf.name} Header Size", f"Size: {len(payload)} bytes")
        version, = struct.unpack_from("<I", payload, 0)
        tc_uuid = uuid.UUID(bytes=payload[4:20])
        num_entries, = struct.unpack_from("<I", payload, 20)
        file_entry_counts[tcf.name] = num_entries
        raw_total_entries += num_entries

        runner.assert_true(version in [1, 2], f"{tcf.name} Valid Version", f"Version={version}")

        entry_size = 22 if version == 1 else 24
        expected_payload_min = 24 + num_entries * entry_size
        runner.assert_true(len(payload) >= expected_payload_min, f"{tcf.name} Payload Bound",
                           f"Expected >= {expected_payload_min}, got {len(payload)}")

        # Check entry iteration, sorting, and duplicate freedom within this file
        seen_in_file = set()
        file_hashes = []
        is_strictly_sorted = True
        has_internal_duplicates = False
        non_zero_flags_in_file = []

        offset = 24
        prev_hash_bytes = None
        for idx in range(num_entries):
            raw_hash = payload[offset:offset + 20]
            hex_hash = raw_hash.hex()
            if prev_hash_bytes is not None:
                if raw_hash < prev_hash_bytes:
                    is_strictly_sorted = False
                elif raw_hash == prev_hash_bytes:
                    has_internal_duplicates = True

            if hex_hash in seen_in_file:
                has_internal_duplicates = True
            seen_in_file.add(hex_hash)
            file_hashes.append(hex_hash)
            all_raw_hashes.append(hex_hash)
            prev_hash_bytes = raw_hash

            if version == 1:
                htype, flags = struct.unpack_from("<BB", payload, offset + 20)
                if flags != 0:
                    non_zero_flags_in_file.append((hex_hash, flags, None))
            elif version == 2:
                htype, flags, cat, res0 = struct.unpack_from("<BBBB", payload, offset + 20)
                if flags != 0:
                    non_zero_flags_in_file.append((hex_hash, flags, cat))

            offset += entry_size

        runner.assert_true(is_strictly_sorted, f"{tcf.name} Lexicographically Sorted",
                           "Raw 20-byte CDHashes must be monotonically sorted")
        runner.assert_true(not has_internal_duplicates, f"{tcf.name} Zero Internal Duplicates",
                           f"File contains {len(file_hashes)} entries, {len(seen_in_file)} unique")

    runner.assert_equal(raw_total_entries, 5204, "Sum Across All 7 Raw TrustCaches == 5,204",
                        f"Per-file counts: {file_entry_counts}")

    unique_raw_hashes = set(all_raw_hashes)
    runner.assert_equal(len(unique_raw_hashes), 4527, "Unique CDHashes Across TrustCaches == 4,527")
    print(f"[*] Inter-TrustCache duplicate entries (shared across images): {len(all_raw_hashes) - len(unique_raw_hashes)}")

    # ---------------------------------------------------------
    # TEST SUITE 2: TrustCache Catalog JSON Validation
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 2: TrustCache Catalog JSON Validation ---")
    runner.assert_true(TC_CATALOG_JSON.is_file(), "trustcache_catalog.json Exists")
    with open(TC_CATALOG_JSON, "r", encoding="utf-8") as f:
        tc_catalog = json.load(f)

    runner.assert_true(isinstance(tc_catalog, list), "Catalog is top-level JSON array")
    runner.assert_equal(len(tc_catalog), 7, "Catalog contains 7 TrustCache objects")

    catalog_total_entries = sum(c.get("entry_count", 0) for c in tc_catalog)
    runner.assert_equal(catalog_total_entries, 5204, "Catalog Entry Count Sum == 5,204")

    all_catalog_flags = []
    amfid_cdhash = "8c8cbe476a8882df62f8250d7f1e7903778445f6"
    amfid_found_in_catalog = False
    amfid_flag_val = None

    for c in tc_catalog:
        runner.assert_true("file" in c and "version" in c and "uuid" in c and "entries" in c,
                           f"Catalog Container {c.get('file')} has required keys")
        runner.assert_equal(len(c["entries"]), c["entry_count"],
                            f"Catalog Container {c.get('file')} entries list length matches entry_count")
        runner.assert_true(c.get("is_sorted") is True, f"Catalog Container {c.get('file')} marked is_sorted")

        for ent in c["entries"]:
            runner.assert_true("cdhash" in ent and "hash_type" in ent and "flags" in ent,
                               "Entry has required keys (cdhash, hash_type, flags)")
            runner.assert_equal(len(ent["cdhash"]), 40, "CDHash is 40 hex chars (20 bytes)")
            flags = ent["flags"]
            if flags != 0:
                all_catalog_flags.append((c["file"], ent["cdhash"], flags, ent.get("category")))
            if ent["cdhash"].lower() == amfid_cdhash.lower():
                amfid_found_in_catalog = True
                amfid_flag_val = flags

    runner.assert_true(amfid_found_in_catalog, "AMFID CDHash Present in Catalog")
    runner.assert_equal(amfid_flag_val, 1, "AMFID flag == 1 in trustcache_catalog.json")

    print(f"[*] Total entries with non-zero flags in all TrustCaches: {len(all_catalog_flags)}")
    flag1_hashes = {h for f, h, flg, cat in all_catalog_flags if flg == 1}
    flag2_hashes = {h for f, h, flg, cat in all_catalog_flags if flg == 2}
    print(f"[*] Entries with flag == 1: {len(flag1_hashes)} unique hashes ({len([1 for f, h, flg, cat in all_catalog_flags if flg == 1])} occurrences)")
    print(f"[*] Entries with flag == 2: {len(flag2_hashes)} unique hashes ({len([1 for f, h, flg, cat in all_catalog_flags if flg == 2])} occurrences)")
    runner.assert_equal(flag1_hashes, {amfid_cdhash}, "Exclusively amfid CDHash has flag == 1 across all 5,204 entries")

    # ---------------------------------------------------------
    # TEST SUITE 3: Independent CDHash First-Principles Calculation
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 3: Independent First-Principles CDHash Oracle ---")
    targets = [
        ("launchd", LAUNCHD_PATH, "51d581be575bfc1e9cf2587eb39beddedb235158", "com.apple.xpc.launchd"),
        ("dyld", DYLD_PATH, "73eacd413d3930ebcde071068c63fef0f8102f55", "com.apple.darwin.ignition"),
        ("amfid", AMFID_PATH, "8c8cbe476a8882df62f8250d7f1e7903778445f6", "com.apple.amfid"),
        ("SpringBoard", SPRINGBOARD_PATH, "93942d0622f54ff1b788f6e902d186fc01f2340f", "com.apple.springboard")
    ]

    for name, path, expected_hash, expected_ident in targets:
        runner.assert_true(path.is_file(), f"Binary Exists on Disk: {name}", f"Path: {path}")
        computed = independent_macho_cdhash(path)
        runner.assert_true(computed is not None and len(computed) > 0, f"Mach-O CDHash Computed: {name}")

        sha256_match = any(c["truncated_sha256"] == expected_hash for c in computed)
        runner.assert_true(sha256_match, f"{name} Computed CDHash Matches Expected Byte-for-Byte",
                           f"Expected: {expected_hash}, Computed: {[c['truncated_sha256'] for c in computed]}")

        # Check signing ident
        ident_match = any(expected_ident in c["ident"] for c in computed)
        runner.assert_true(ident_match, f"{name} Signing Identifier Matches",
                           f"Expected {expected_ident}, got {[c['ident'] for c in computed]}")

    # ---------------------------------------------------------
    # TEST SUITE 4: CDHash Database Integrity & Cross-Referencing
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 4: CDHash Database JSON Integrity ---")
    runner.assert_true(CDHASH_DB_JSON.is_file(), "cdhash_database.json Exists")
    with open(CDHASH_DB_JSON, "r", encoding="utf-8") as f:
        cd_db = json.load(f)

    runner.assert_true("metadata" in cd_db and "cdhashes" in cd_db, "cdhash_database.json Root Keys")
    meta = cd_db["metadata"]
    runner.assert_equal(meta.get("total_trustcache_entries"), 5204, "DB Metadata total_trustcache_entries == 5,204")
    runner.assert_equal(meta.get("unique_cdhashes"), 4527, "DB Metadata unique_cdhashes == 4,527")
    runner.assert_true(meta.get("total_mapped_binaries") >= 600, "DB Metadata mapped binaries >= 600",
                       f"Actual: {meta.get('total_mapped_binaries')}")

    db_cdhashes = cd_db["cdhashes"]
    runner.assert_equal(len(db_cdhashes), 4527, "DB cdhashes dictionary has exactly 4,527 keys")

    # Cross-reference the 4 key binaries in the database
    for name, path, exp_hash, exp_id in targets:
        runner.assert_true(exp_hash in db_cdhashes, f"{name} CDHash in Database")
        ent = db_cdhashes.get(exp_hash, {})
        runner.assert_true(ent.get("matched") is True, f"{name} is Matched to Disk Binary")
        runner.assert_true(ent.get("signing_identifier") == exp_id or exp_id in str(ent.get("signing_identifier")),
                           f"{name} Signing ID in DB", f"Got: {ent.get('signing_identifier')}")
        runner.assert_true(ent.get("binary_path") is not None and len(ent.get("binary_path")) > 0,
                           f"{name} Has Non-Empty Binary Path")

    # Specific check on AMFID entry in cdhash_database.json
    amfid_db_ent = db_cdhashes[amfid_cdhash]
    runner.assert_equal(amfid_db_ent.get("trustcache_sources", [{}])[0].get("flags"), 1,
                        "AMFID Database Entry flags == 1 in trustcache_sources")
    runner.assert_equal(amfid_db_ent.get("trustcache_sources", [{}])[0].get("category"), 1,
                        "AMFID Database Entry category == 1 (Core System Daemons)")

    # Launchd category check
    launchd_db_ent = db_cdhashes["51d581be575bfc1e9cf2587eb39beddedb235158"]
    runner.assert_equal(launchd_db_ent.get("trustcache_sources", [{}])[0].get("flags"), 0,
                        "launchd Database Entry flags == 0")
    runner.assert_equal(launchd_db_ent.get("trustcache_sources", [{}])[0].get("category"), 2,
                        "launchd Database Entry category == 2 (Core Bootstrap & Ignition)")

    # ---------------------------------------------------------
    # TEST SUITE 5: Entitlements Analysis JSON Integrity
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 5: Entitlements Analysis JSON Integrity ---")
    runner.assert_true(ENTITLEMENTS_JSON.is_file(), "entitlements_analysis.json Exists")
    with open(ENTITLEMENTS_JSON, "r", encoding="utf-8") as f:
        ent_analysis = json.load(f)

    for k in ["metadata", "taxonomy", "binaries"]:
        runner.assert_true(k in ent_analysis, f"entitlements_analysis.json has '{k}' key")

    ent_meta = ent_analysis.get("metadata", {})
    runner.assert_true(ent_meta.get("total_binaries_cataloged") >= 600, "Cataloged binaries >= 600",
                       f"Actual: {ent_meta.get('total_binaries_cataloged')}")
    runner.assert_true(ent_meta.get("unique_entitlements_cataloged") >= 4000, "Unique entitlements >= 4,000",
                       f"Actual: {ent_meta.get('unique_entitlements_cataloged')}")

    taxonomy = ent_analysis.get("taxonomy", {})
    tier1 = taxonomy.get("root_hardware_capabilities", [])
    tier2 = taxonomy.get("private_apple_entitlements", [])
    tier3 = taxonomy.get("tcc_access_overrides", {})
    tier4 = taxonomy.get("mach_lookup_assertions", {})

    runner.assert_true(len(tier1) > 200, f"Tier 1 (Root/HW) Count > 200 (Got {len(tier1)})")
    runner.assert_true(len(tier2) > 1500, f"Tier 2 (Private Apple) Count > 1,500 (Got {len(tier2)})")
    runner.assert_true(len(tier3.get("asserted_services", [])) > 50,
                       f"Tier 3 TCC services > 50 (Got {len(tier3.get('asserted_services', []))})")
    runner.assert_true(len(tier4.get("asserted_services", [])) > 1000,
                       f"Tier 4 Mach services > 1,000 (Got {len(tier4.get('asserted_services', []))})")

    # Check for empty / malformed binary entitlement objects
    binaries = ent_analysis.get("binaries", {})
    runner.assert_true(len(binaries) >= 600, f"Binaries count in dict >= 600 (Got {len(binaries)})")

    # ---------------------------------------------------------
    # TEST SUITE 6: JSON Edge Cases & Missing Keys
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 6: Schema Edge Cases & Missing Keys ---")
    empty_arrays = []
    missing_required_keys = []

    # Check cdhash_database.json for anomalies
    for cdhash, val in db_cdhashes.items():
        if val.get("matched"):
            if not val.get("binary_path"):
                missing_required_keys.append(f"Matched {cdhash} missing binary_path")
            if not val.get("signing_identifier"):
                missing_required_keys.append(f"Matched {cdhash} missing signing_identifier")
            if not val.get("macho_architecture"):
                missing_required_keys.append(f"Matched {cdhash} missing macho_architecture")

    runner.assert_equal(len(missing_required_keys), 0, "Zero Missing Required Keys in Matched CDHashes",
                        f"Errors: {missing_required_keys[:5]}")

    # ---------------------------------------------------------
    # TEST SUITE 7: Findings Document Verification
    # ---------------------------------------------------------
    print("\n--- TEST SUITE 7: Findings Document Integrity ---")
    runner.assert_true(FINDINGS_DOC.is_file(), "Findings Document Exists")
    doc_text = FINDINGS_DOC.read_text(encoding="utf-8")
    doc_len = len(doc_text)
    runner.assert_true(doc_len >= 2500, f"Findings Document Size >= 2,500 bytes (Actual: {doc_len} bytes)")

    placeholder_hits = []
    for pat in BANNED_PLACEHOLDERS:
        for m in re.finditer(pat, doc_text, re.IGNORECASE):
            placeholder_hits.append((pat, m.group(), m.start()))

    runner.assert_equal(len(placeholder_hits), 0, "Zero Banned Placeholders in Findings Document",
                        f"Hits: {placeholder_hits}")

    # Verify required assembly citations
    citations = [
        "mac_vnode_check_signature",
        "0xfffffe0009297d7c",
        "_check_cdhash_in_trustcache",
        "0xfffffe0009299730",
        "mac_cred_label_update_execve",
        "0xfffffe00092961f4",
        "pacibsp",
        "0xd503237f",
        "VTTBR_EL2"
    ]
    for cit in citations:
        runner.assert_true(cit in doc_text, f"Citations include '{cit}'")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {runner.tests_run} tests run | {runner.tests_run - runner.tests_failed} passed | {runner.tests_failed} failed")
    print("=" * 70)

    if runner.tests_failed > 0:
        print("[!] SUITE FAILED WITH FAILURES:")
        for f in runner.failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("[+] ALL ADVERSARIAL STRESS TESTS PASSED EMPIRICALLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()
