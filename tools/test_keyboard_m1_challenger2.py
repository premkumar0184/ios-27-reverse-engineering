#!/usr/bin/env python3
"""
Adversarial Empirical Verification Suite — Challenger M1_2
===========================================================
Milestone: Milestone 1 (Component & Resource Inventories, Workspace Audit)
Project: iOS 27 Keyboard Ecosystem Reverse Engineering & Reconstruction
Target OS: iOS 27.2 (Build 24B119, iPhone18,3, SoC t8150 / A19 Pro)
Author: Empirical Challenger M1_2 (critic, specialist)

Verification Criteria:
1. Exact CSV DictReader parsing and strict column header validation.
2. Complete non-emptiness, whitespace trimming, and well-formedness of all row fields.
3. Ground-truth cross-referencing against dyld shared cache overview and filesystem.
4. Uniqueness, semantic validity, and cross-inventory bundle consistency.
5. Strict anti-placeholder regex audit across all deliverables.
6. UTF-8 byte integrity (zero replacement characters \ufffd or byte decoding errors).
7. Coverage of all 98 layout bundles and all 7 unresolved components.
8. Preservation of read-only baseline for original IPSW restore containers.
"""

import sys
import os
import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path("/home/prem/Projects/iOS 27")
DELIVERABLES_DIR = REPO_ROOT / "ios27-keyboard-reverse-engineering"
COMPONENT_CSV = DELIVERABLES_DIR / "02_COMPONENT_INVENTORY.csv"
RESOURCE_CSV = DELIVERABLES_DIR / "05_RESOURCE_INVENTORY.csv"
WORKSPACE_AUDIT = DELIVERABLES_DIR / "01_WORKSPACE_AUDIT.md"
UNRESOLVED_MD = DELIVERABLES_DIR / "08_UNRESOLVED_COMPONENTS.md"

SHARED_CACHE_OVERVIEW = REPO_ROOT / "artifacts/rootfs/shared_cache_overview.json"
SHARED_CACHE_DIR = REPO_ROOT / "artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld"
RESTORE_DIR = REPO_ROOT / "iPhone18,3_27.2_24B119_Restore"
CRYPTO_DIR = REPO_ROOT / "artifacts/crypto"

BANNED_PLACEHOLDER_REGEX = re.compile(r'(TODO|TBD|placeholder|<insert)', re.IGNORECASE)

class TestSuiteRunner:
    def __init__(self):
        self.total_assertions = 0
        self.passed_assertions = 0
        self.failed_assertions = 0
        self.failures = []

    def assert_true(self, condition: bool, description: str, context: str = ""):
        self.total_assertions += 1
        if condition:
            self.passed_assertions += 1
            print(f"  [PASS] {description}")
        else:
            self.failed_assertions += 1
            failure_msg = f"{description} | Context: {context}"
            self.failures.append(failure_msg)
            print(f"  [FAIL] {failure_msg}")

    def summarize(self):
        print("\n" + "=" * 70)
        print("EMPIRICAL TEST SUITE EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Total Assertions : {self.total_assertions}")
        print(f"Passed           : {self.passed_assertions}")
        print(f"Failed           : {self.failed_assertions}")
        if self.failed_assertions > 0:
            print("\nFAILURES ENCOUNTERED:")
            for f in self.failures:
                print(f"  - {f}")
            print("\nVERDICT: FAIL")
            return 1
        else:
            print("\nALL ASSERTIONS PASSED EMPIRICALLY.")
            print("VERDICT: APPROVE")
            return 0


def run_tests():
    runner = TestSuiteRunner()

    print("=" * 70)
    print("CHALLENGER M1_2: EMPIRICAL STRESS TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Suite 1: File Existence, Accessibility, and Non-Trivial Size
    # -------------------------------------------------------------------------
    print("\n[SUITE 1] Deliverable Files Physical Integrity")
    files_to_check = [
        (WORKSPACE_AUDIT, 10000, "01_WORKSPACE_AUDIT.md"),
        (COMPONENT_CSV, 20000, "02_COMPONENT_INVENTORY.csv"),
        (RESOURCE_CSV, 200000, "05_RESOURCE_INVENTORY.csv"),
        (UNRESOLVED_MD, 10000, "08_UNRESOLVED_COMPONENTS.md"),
    ]
    for path, min_size, name in files_to_check:
        runner.assert_true(path.is_file(), f"{name} exists as regular file", str(path))
        if path.is_file():
            size = path.stat().st_size
            runner.assert_true(size >= min_size, f"{name} exceeds minimum size ({size} >= {min_size} bytes)", str(path))

    # -------------------------------------------------------------------------
    # Suite 2: UTF-8 Encoding & Byte Cleanliness
    # -------------------------------------------------------------------------
    print("\n[SUITE 2] UTF-8 Encoding & Character Integrity")
    for path, _, name in files_to_check:
        try:
            with open(path, 'r', encoding='utf-8', errors='strict') as f:
                content = f.read()
            runner.assert_true('\ufffd' not in content, f"{name}: zero Unicode replacement chars (\\ufffd)")
            runner.assert_true('\x00' not in content, f"{name}: zero null bytes")
        except UnicodeDecodeError as e:
            runner.assert_true(False, f"{name}: failed strict UTF-8 decoding", str(e))

    # -------------------------------------------------------------------------
    # Suite 3: 02_COMPONENT_INVENTORY.csv Strict DictReader Parsing & Headers
    # -------------------------------------------------------------------------
    print("\n[SUITE 3] 02_COMPONENT_INVENTORY.csv Schema & DictReader Parsing")
    expected_comp_headers = [
        'Component', 'Path', 'Type', 'Architecture', 'Size',
        'Identifier', 'Purpose', 'Relationships', 'Status', 'Confidence'
    ]
    with open(COMPONENT_CSV, 'r', encoding='utf-8') as f:
        comp_reader = csv.DictReader(f)
        actual_headers = comp_reader.fieldnames
        runner.assert_true(
            actual_headers == expected_comp_headers,
            "02_COMPONENT_INVENTORY.csv exact column header sequence",
            f"Expected: {expected_comp_headers}, Got: {actual_headers}"
        )
        comp_rows = list(comp_reader)
        runner.assert_true(
            len(comp_rows) == 57,
            f"02_COMPONENT_INVENTORY.csv contains exactly 57 data rows (actual: {len(comp_rows)})",
            str(COMPONENT_CSV)
        )

    # -------------------------------------------------------------------------
    # Suite 4: 02_COMPONENT_INVENTORY.csv Field Completeness & Semantic Sanity
    # -------------------------------------------------------------------------
    print("\n[SUITE 4] 02_COMPONENT_INVENTORY.csv Field Non-Emptiness & Semantics")
    comp_names = set()
    comp_paths = set()
    comp_ids = set()
    embedded_count = 0
    separated_count = 0

    valid_types = {
        'Framework (Mach-O dylib)',
        'Bundle (Mach-O bundle)',
        'Daemon (Mach-O executable)',
        'Application (Mach-O executable)',
        'Extension (Mach-O executable)',
        'LaunchDaemon (Property List)',
    }

    for idx, row in enumerate(comp_rows):
        # 1. Non-empty fields and no untrimmed whitespace
        for col in expected_comp_headers:
            val = row.get(col)
            runner.assert_true(
                val is not None and val.strip() != '',
                f"Row {idx+1} ({row.get('Component')}): field '{col}' is non-empty",
                f"Value: {val!r}"
            )

        # 2. Unique Component and Path
        c_name = row.get('Component', '')
        c_path = row.get('Path', '')
        c_type = row.get('Type', '')
        c_arch = row.get('Architecture', '')
        c_id = row.get('Identifier', '')
        c_conf = row.get('Confidence', '')
        c_status = row.get('Status', '')
        c_purpose = row.get('Purpose', '')
        c_rel = row.get('Relationships', '')

        runner.assert_true(c_name not in comp_names, f"Row {idx+1}: Component '{c_name}' is unique")
        comp_names.add(c_name)

        runner.assert_true(c_path not in comp_paths, f"Row {idx+1}: Path '{c_path}' is unique")
        comp_paths.add(c_path)

        runner.assert_true(c_type in valid_types, f"Row {idx+1}: Type '{c_type}' belongs to recognized taxonomy")
        runner.assert_true(
            c_arch in {'arm64e (PAC00)', 'Binary Plist'},
            f"Row {idx+1}: Architecture '{c_arch}' is valid"
        )
        runner.assert_true(
            c_id.startswith('com.apple.'),
            f"Row {idx+1}: Identifier '{c_id}' is valid Apple bundle ID"
        )
        runner.assert_true(
            c_conf.startswith('1.0'),
            f"Row {idx+1}: Confidence score '{c_conf}' indicates high empirical certainty"
        )
        runner.assert_true(
            len(c_purpose) >= 30,
            f"Row {idx+1}: Purpose description is substantive (len={len(c_purpose)})"
        )
        runner.assert_true(
            len(c_rel) >= 30,
            f"Row {idx+1}: Relationships description is substantive (len={len(c_rel)})"
        )

        if 'Embedded in dyld_shared_cache' in c_status:
            embedded_count += 1
        elif 'Separated' in c_status:
            separated_count += 1

    runner.assert_true(
        embedded_count == 50,
        f"Exactly 50 components embedded in dyld shared cache (actual: {embedded_count})"
    )
    runner.assert_true(
        separated_count == 7,
        f"Exactly 7 components separated on RootFS (actual: {separated_count})"
    )

    # -------------------------------------------------------------------------
    # Suite 5: 05_RESOURCE_INVENTORY.csv Strict DictReader Parsing & Headers
    # -------------------------------------------------------------------------
    print("\n[SUITE 5] 05_RESOURCE_INVENTORY.csv Schema & DictReader Parsing")
    expected_res_headers = [
        'Path', 'Format', 'Locale', 'KeyboardRelationship', 'Size', 'Description'
    ]
    with open(RESOURCE_CSV, 'r', encoding='utf-8') as f:
        res_reader = csv.DictReader(f)
        actual_res_headers = res_reader.fieldnames
        runner.assert_true(
            actual_res_headers == expected_res_headers,
            "05_RESOURCE_INVENTORY.csv exact column header sequence",
            f"Expected: {expected_res_headers}, Got: {actual_res_headers}"
        )
        res_rows = list(res_reader)
        runner.assert_true(
            len(res_rows) == 2053,
            f"05_RESOURCE_INVENTORY.csv contains exactly 2053 data rows (actual: {len(res_rows)})",
            str(RESOURCE_CSV)
        )

    # -------------------------------------------------------------------------
    # Suite 6: 05_RESOURCE_INVENTORY.csv Field Completeness, Uniqueness & Sanity
    # -------------------------------------------------------------------------
    print("\n[SUITE 6] 05_RESOURCE_INVENTORY.csv Field Non-Emptiness & Formats")
    res_paths = set()
    res_duplicate_count = 0
    res_empty_field_count = 0
    res_invalid_size_count = 0
    res_short_description_count = 0
    res_layout_bundles = set()

    for idx, row in enumerate(res_rows):
        # 1. Non-emptiness
        for col in expected_res_headers:
            val = row.get(col)
            if val is None or val.strip() == '':
                res_empty_field_count += 1

        # 2. Path uniqueness
        p = row.get('Path', '')
        if p in res_paths:
            res_duplicate_count += 1
        res_paths.add(p)

        # 3. Numeric size
        sz = row.get('Size', '')
        if not sz.isdigit():
            res_invalid_size_count += 1

        # 4. Description substantive
        desc = row.get('Description', '')
        if len(desc.strip()) < 20:
            res_short_description_count += 1

        # 5. Extract layout bundles
        m = re.search(r'(TextInput_[a-zA-Z0-9_]+\.bundle)', p)
        if m:
            res_layout_bundles.add(m.group(1))

    runner.assert_true(res_empty_field_count == 0, f"05_RESOURCE_INVENTORY: zero empty fields (found: {res_empty_field_count})")
    runner.assert_true(res_duplicate_count == 0, f"05_RESOURCE_INVENTORY: zero duplicate paths (found: {res_duplicate_count})")
    runner.assert_true(res_invalid_size_count == 0, f"05_RESOURCE_INVENTORY: all sizes are valid non-negative integers (found: {res_invalid_size_count})")
    runner.assert_true(res_short_description_count == 0, f"05_RESOURCE_INVENTORY: all descriptions are substantive >= 20 chars (found: {res_short_description_count})")
    runner.assert_true(len(res_layout_bundles) == 98, f"05_RESOURCE_INVENTORY: indexes all 98 layout bundles (found: {len(res_layout_bundles)})")

    # Cross-reference bundles from 02_COMPONENT_INVENTORY are fully covered in 05
    comp_bundles = {r['Component'] for r in comp_rows if r['Component'].startswith('TextInput_')}
    runner.assert_true(
        comp_bundles.issubset(res_layout_bundles),
        f"All {len(comp_bundles)} bundles from 02_COMPONENT_INVENTORY are represented in 05_RESOURCE_INVENTORY"
    )

    # -------------------------------------------------------------------------
    # Suite 7: Physical Ground-Truth Cross-Referencing (dyld Cache & Filesystem)
    # -------------------------------------------------------------------------
    print("\n[SUITE 7] Physical Ground-Truth Cross-Referencing")
    # 1. Shared Cache Overview Check
    runner.assert_true(SHARED_CACHE_OVERVIEW.is_file(), "artifacts/rootfs/shared_cache_overview.json exists")
    with open(SHARED_CACHE_OVERVIEW, 'r', encoding='utf-8') as f:
        sc_data = json.load(f)
    sc_images = {img['path']: img for img in sc_data.get('all_images', [])}
    runner.assert_true(len(sc_images) == 4770, f"Shared cache overview indexes 4,770 images (actual: {len(sc_images)})")

    # Cross-reference all 50 embedded components
    embedded_verified_count = 0
    vmaddr_mismatches = 0
    for row in comp_rows:
        if 'Embedded in dyld_shared_cache' in row['Status']:
            c_path = row['Path']
            if c_path in sc_images:
                embedded_verified_count += 1
                img = sc_images[c_path]
                m = re.search(r'vmaddr:\s*(0x[0-9a-fA-F]+)', row['Status'])
                if m:
                    csv_addr = m.group(1).lower()
                    sc_addr = img['address'].lower()
                    if csv_addr != sc_addr:
                        vmaddr_mismatches += 1

    runner.assert_true(
        embedded_verified_count == 50,
        f"All 50 embedded components verified against dyld_shared_cache_overview.json (matched: {embedded_verified_count})"
    )
    runner.assert_true(
        vmaddr_mismatches == 0,
        f"All embedded components match exact dyld cache VM addresses (mismatches: {vmaddr_mismatches})"
    )

    # 2. Separated Binaries on RootFS Check
    separated_verified = 0
    expected_separated = [
        REPO_ROOT / "artifacts/rootfs/extracted_daemons/System/Library/TextInput/kbd",
        REPO_ROOT / "artifacts/rootfs/System/Library/LaunchDaemons/com.apple.TextInput.kbd.plist",
        REPO_ROOT / "artifacts/rootfs/extracted_daemons/System/Library/CoreServices/FullKeyboardAccess.app/FullKeyboardAccess",
        REPO_ROOT / "artifacts/rootfs/extracted_daemons/System/Library/PrivateFrameworks/Stickers.framework/Support/stickersd",
        REPO_ROOT / "artifacts/rootfs/System/Library/LaunchDaemons/com.apple.stickersd.plist",
        REPO_ROOT / "artifacts/rootfs/System/Library/LaunchDaemons/com.apple.fullkeyboardaccess.plist",
    ]
    for p in expected_separated:
        if p.exists():
            separated_verified += 1
            runner.assert_true(True, f"Separated filesystem artifact verified on disk: {p.name} ({p.stat().st_size} bytes)")
        else:
            runner.assert_true(False, f"Separated filesystem artifact missing: {p.name}", str(p))

    # 3. Dyld Shared Cache disk slices check
    staged_sc_master = SHARED_CACHE_DIR / "dyld_shared_cache_arm64e"
    staged_sc_36 = SHARED_CACHE_DIR / "dyld_shared_cache_arm64e.36"
    staged_sc_atlas = SHARED_CACHE_DIR / "dyld_shared_cache_arm64e.atlas"
    runner.assert_true(staged_sc_master.is_file() and staged_sc_master.stat().st_size == 802816, "Staged master cache header is 802,816 bytes")
    runner.assert_true(staged_sc_36.is_file() and staged_sc_36.stat().st_size == 131547136, "Staged subcache .36 is 131,547,136 bytes")
    runner.assert_true(staged_sc_atlas.is_file() and staged_sc_atlas.stat().st_size == 3102982, "Staged selector atlas is 3,102,982 bytes")

    # 4. Decrypted Master DMGs check
    rootfs_dmg = CRYPTO_DIR / "141-08876-216_rootfs.dmg"
    cryptex_dmg = CRYPTO_DIR / "141-09724-226_cryptex_systemos.dmg"
    runner.assert_true(rootfs_dmg.is_file() and rootfs_dmg.stat().st_size == 10561257472, "Decrypted RootFS DMG is 10,561,257,472 bytes")
    runner.assert_true(cryptex_dmg.is_file() and cryptex_dmg.stat().st_size == 6322913280, "Decrypted Cryptex SystemOS DMG is 6,322,913,280 bytes")

    # -------------------------------------------------------------------------
    # Suite 8: Unresolved Components Documentation Invariants
    # -------------------------------------------------------------------------
    print("\n[SUITE 8] 08_UNRESOLVED_COMPONENTS.md Invariants")
    with open(UNRESOLVED_MD, 'r', encoding='utf-8') as f:
        unres_text = f.read()
    for u_id in ['U1:', 'U2:', 'U3:', 'U4:', 'U5:', 'U6:', 'U7:']:
        runner.assert_true(u_id in unres_text, f"08_UNRESOLVED_COMPONENTS: covers component {u_id}")

    # -------------------------------------------------------------------------
    # Suite 9: Anti-Placeholder & Token Integrity Scan
    # -------------------------------------------------------------------------
    print("\n[SUITE 9] Anti-Placeholder & Token Integrity Scan")
    target_docs = [
        WORKSPACE_AUDIT,
        COMPONENT_CSV,
        RESOURCE_CSV,
        UNRESOLVED_MD
    ]
    total_placeholder_matches = 0
    for doc_path in target_docs:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = BANNED_PLACEHOLDER_REGEX.findall(content)
        runner.assert_true(
            len(matches) == 0,
            f"{doc_path.name}: 0 placeholder tokens detected (found: {len(matches)})",
            f"Matches: {matches[:5]}"
        )
        total_placeholder_matches += len(matches)

    runner.assert_true(
        total_placeholder_matches == 0,
        f"Complete repository deliverables: zero placeholder tokens across all 4 files (total: {total_placeholder_matches})"
    )

    # -------------------------------------------------------------------------
    # Suite 10: Original Restore Container Read-Only Protocol
    # -------------------------------------------------------------------------
    print("\n[SUITE 10] Original Restore Container Read-Only Verification")
    runner.assert_true(RESTORE_DIR.is_dir(), "IPSW restore container exists", str(RESTORE_DIR))
    test_restore_file = RESTORE_DIR / "BuildManifest.plist"
    if test_restore_file.is_file():
        is_writable = os.access(test_restore_file, os.W_OK)
        runner.assert_true(not is_writable, "Restore container BuildManifest.plist is strictly READ-ONLY (W_OK is False)")

    return runner.summarize()

if __name__ == "__main__":
    sys.exit(run_tests())
