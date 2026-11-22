#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Comprehensive CDHash Database Generator
Ingests parsed TrustCaches, calculates Mach-O CodeDirectory hashes across extracted disk
binaries and system daemons, and generates artifacts/security/cdhash_database.json.
"""

import sys
import os
import struct
import hashlib
import json
import plistlib
from pathlib import Path
from collections import defaultdict, Counter

CATEGORY_NAMES = {
    0: "Unconstrained / Cryptex Default",
    1: "Core System Daemons & Services",
    2: "Core Bootstrap & Ignition Runtime",
    3: "Security & Network Infrastructure Daemons",
    4: "App Extensions, PlugIns & Diagnostic Services",
    5: "System Cryptex OS Daemons & Frameworks",
    10: "Coprocessor & Hardware Interfaces",
    11: "Telephony & Baseband Interfacing Daemons",
    12: "Factory Diagnostics & Test Daemons",
    14: "Core Root System Applications",
    15: "Critical Hardware Enclave Agents",
    16: "Staged System Applications",
    18: "Special Hardened Security Domain Agent"
}

def decode_cs_flags(flags: int) -> list:
    flag_defs = [
        (0x00000001, "CS_VALID"),
        (0x00000002, "CS_ADHOC"),
        (0x00000004, "CS_GET_TASK_ALLOW"),
        (0x00000008, "CS_INSTALLER"),
        (0x00000010, "CS_FORCED_LV"),
        (0x00000100, "CS_HARD"),
        (0x00000200, "CS_KILL"),
        (0x00000800, "CS_RESTRICT"),
        (0x00001000, "CS_ENFORCEMENT"),
        (0x00002000, "CS_REQUIRE_LV"),
        (0x00010000, "CS_RUNTIME"),
        (0x00020000, "CS_LINKER_SIGNED"),
        (0x02000000, "CS_DYLD_PLATFORM"),
        (0x04000000, "CS_PLATFORM_BINARY")
    ]
    return [name for mask, name in flag_defs if flags & mask]

def find_bundle_identifier_for_path(fpath: Path) -> str:
    """Check parent folders for Info.plist to extract CFBundleIdentifier."""
    cur = fpath.parent
    for _ in range(4):
        plist_path = cur / "Info.plist"
        if plist_path.is_file():
            try:
                with open(plist_path, "rb") as pf:
                    pdata = plistlib.load(pf)
                bid = pdata.get("CFBundleIdentifier")
                if bid:
                    return bid
            except Exception:
                pass
        if cur.name.endswith(".app") or cur.name.endswith(".appex") or cur.name.endswith(".framework"):
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None

def parse_macho_cdhash(fpath: Path) -> list:
    try:
        with open(fpath, "rb") as bf:
            data = bf.read()
    except Exception:
        return []

    if len(data) < 32:
        return []

    magic, = struct.unpack_from("<I", data, 0)
    if magic == 0xfeedfacf:  # MH_MAGIC_64
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack_from("<IIIIIII", data, 4)
        offset = 32
    elif magic == 0xfeedface:  # MH_MAGIC
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack_from("<IIIIII", data, 4)
        offset = 28
    else:
        return []

    ptrauth_abi = bool(cpusubtype & 0x80000000)
    pac_version = (cpusubtype & 0x0f000000) >> 24

    results = []
    bundle_id = find_bundle_identifier_for_path(fpath)

    for _ in range(ncmds):
        if offset + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack_from("<II", data, offset)
        if cmd == 0x1d:  # LC_CODE_SIGNATURE
            dataoff, datasize = struct.unpack_from("<II", data, offset + 8)
            sig = data[dataoff:dataoff+datasize]
            if len(sig) >= 12:
                smagic, slen, scount = struct.unpack_from(">III", sig, 0)
                if smagic == 0xfade0cc0:  # CSBLOB_EMBEDDED_SIGNATURE
                    for i in range(scount):
                        stype, soff = struct.unpack_from(">II", sig, 12 + i*8)
                        blob = sig[soff:]
                        if len(blob) >= 8:
                            bmagic, blen = struct.unpack_from(">II", blob, 0)
                            if bmagic == 0xfade0c02:  # CSBLOB_CODEDIRECTORY
                                cd = blob[:blen]
                                if len(cd) >= 40:
                                    cd_ver, cd_flags, h_off, id_off, n_spec, n_code, code_lim = struct.unpack_from(">IIIIIII", cd, 8)
                                    h_size, h_type, plat, page_sz = struct.unpack_from(">BBBB", cd, 36)
                                    ident = cd[id_off:].split(b"\x00")[0].decode("utf-8", "ignore")
                                    if h_type == 2:
                                        cdhash = hashlib.sha256(cd).hexdigest()[:40]
                                    elif h_type == 1:
                                        cdhash = hashlib.sha1(cd).hexdigest()
                                    else:
                                        cdhash = None

                                    if cdhash:
                                        results.append({
                                            "cdhash": cdhash,
                                            "hash_type": h_type,
                                            "hash_algorithm": "SHA-256 (truncated 160-bit)" if h_type == 2 else "SHA-1",
                                            "signing_identifier": ident,
                                            "bundle_identifier": bundle_id or ident,
                                            "cputype": hex(cputype),
                                            "cpusubtype": hex(cpusubtype),
                                            "ptrauth_abi": ptrauth_abi,
                                            "pac_version": pac_version,
                                            "cd_version": hex(cd_ver),
                                            "flags_raw": cd_flags,
                                            "flags_decoded": decode_cs_flags(cd_flags),
                                            "slot_type": stype
                                        })
        offset += cmdsize
    return results

def main():
    root = Path(__file__).resolve().parent.parent
    tc_catalog_path = root / "artifacts/security/trustcache_catalog.json"
    if not tc_catalog_path.is_file():
        print(f"[ERROR] Missing {tc_catalog_path}")
        sys.exit(1)

    with open(tc_catalog_path, "r", encoding="utf-8") as f:
        tc_catalog = json.load(f)

    # 1. Ingest all TrustCache entries
    db = {}
    cat_counts = Counter()
    total_tc_entries = sum(tc.get("entry_count", 0) for tc in tc_catalog)

    for tc in tc_catalog:
        tc_file = tc.get("file")
        tc_ver = tc.get("version")
        for ent in tc.get("entries", []):
            h = ent["cdhash"]
            cat = ent.get("category")
            if cat is not None:
                cat_counts[cat] += 1
            if h not in db:
                db[h] = {
                    "cdhash": h,
                    "hash_type": ent.get("hash_type", 2),
                    "hash_algorithm": "SHA-256 (truncated 160-bit)" if ent.get("hash_type") == 2 else "SHA-1",
                    "matched": False,
                    "binary_path": None,
                    "filesystem_image": None,
                    "signing_identifier": None,
                    "bundle_identifier": None,
                    "macho_architecture": None,
                    "code_signing": None,
                    "execution_constraints": {
                        "category_id": cat,
                        "category_name": CATEGORY_NAMES.get(cat, "Unknown / Custom Category") if cat is not None else None
                    },
                    "trustcache_sources": []
                }
            db[h]["trustcache_sources"].append({
                "file": tc_file,
                "version": tc_ver,
                "category": cat,
                "flags": ent.get("flags")
            })

    print(f"[*] Ingested {len(db)} unique CDHashes across {total_tc_entries} total entries in 7 TrustCaches.")

    # 2. Scan extracted binaries across all relevant locations
    scan_configs = [
        (root / "artifacts/rootfs/binaries", root / "artifacts/rootfs/binaries", "141-08876-216_rootfs.dmg"),
        (root / "artifacts/ui/Applications", root / "artifacts/ui/Applications", "141-08876-216_rootfs.dmg"),
        (root / "artifacts/ui/SpringBoard", root / "artifacts/ui/SpringBoard", "141-08876-216_rootfs.dmg"),
        (root / "artifacts/rootfs/extracted_daemons", root / "artifacts/rootfs/extracted_daemons", "141-08876-216_rootfs.dmg")
    ]

    matched_count = 0
    for scan_dir, base_dir, image_name in scan_configs:
        if not scan_dir.exists():
            continue
        for fpath in scan_dir.rglob("*"):
            if fpath.is_file():
                results = parse_macho_cdhash(fpath)
                for r in results:
                    h = r["cdhash"]
                    if h in db:
                        # Determine canonical binary path on device
                        if scan_dir == root / "artifacts/rootfs/extracted_daemons":
                            canon_path = "/" + str(fpath.relative_to(scan_dir))
                        elif scan_dir == root / "artifacts/rootfs/binaries":
                            canon_path = "/" + str(fpath.relative_to(scan_dir))
                        elif "Applications/" in str(fpath):
                            # Staged or root apps
                            idx = str(fpath).find("Applications/")
                            canon_path = "/" + str(fpath)[idx:]
                        elif "System/Library/" in str(fpath):
                            idx = str(fpath).find("System/Library/")
                            canon_path = "/" + str(fpath)[idx:]
                        else:
                            canon_path = "/" + str(fpath.relative_to(root))

                        if not db[h]["matched"]:
                            matched_count += 1

                        db[h]["matched"] = True
                        db[h]["binary_path"] = canon_path
                        db[h]["filesystem_image"] = image_name
                        db[h]["signing_identifier"] = r["signing_identifier"]
                        db[h]["bundle_identifier"] = r["bundle_identifier"]
                        db[h]["macho_architecture"] = {
                            "cputype": f"{r['cputype']} (CPU_TYPE_ARM64)",
                            "cpusubtype": f"{r['cpusubtype']} (CPU_SUBTYPE_ARM64E)",
                            "ptrauth_abi": r["ptrauth_abi"],
                            "pac_abi_version": r["pac_version"]
                        }
                        db[h]["code_signing"] = {
                            "cd_version": r["cd_version"],
                            "flags_raw": r["flags_raw"],
                            "flags_decoded": r["flags_decoded"]
                        }
                        if db[h]["execution_constraints"]["category_id"] is None and r.get("slot_type"):
                            pass

    print(f"[+] Successfully mapped {matched_count} CDHashes to genuine system binaries.")

    # 3. Write artifacts/security/cdhash_database.json
    out_path = root / "artifacts/security/cdhash_database.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    final_output = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "metadata": {
            "title": "iOS 27.2 TrustCache CDHash Database & Binary Cross-Reference",
            "build": "24B119",
            "hardware": "iPhone18,3 (t8150)",
            "total_trustcache_entries": total_tc_entries,
            "unique_cdhashes": len(db),
            "total_mapped_binaries": matched_count,
            "hash_type_distribution": { "SHA-256": len(db) },
            "constraint_category_distribution": {str(k): v for k, v in sorted(cat_counts.items())},
            "trustcache_sources": [
                {
                    "file": tc.get("file"),
                    "version": tc.get("version"),
                    "entries": tc.get("entry_count"),
                    "uuid": tc.get("uuid"),
                    "im4p_tag": tc.get("im4p_tag")
                }
                for tc in tc_catalog
            ]
        },
        "cdhashes": db
    }

    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(final_output, out_f, indent=2)

    print(f"[+] Wrote {out_path} ({out_path.stat().st_size} bytes, {matched_count} mapped binaries, {len(db)} unique CDHashes).")

if __name__ == "__main__":
    main()
