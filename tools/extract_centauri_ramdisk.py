#!/usr/bin/env python3
"""
extract_centauri_ramdisk.py — Centauri DriverKit & Host Binary Extraction Harness
iOS 27.2 (24B119) / Apple Silicon A19 Pro (t8150 / v57ap)

Extracts all Centauri DriverKit bundles, dexts, frameworks, plists, and updaters
from the restore ramdisk APFS image into artifacts/centauri/driverkit/.
Validates Mach-O headers, compute SHA256 hashes, parses IOKitPersonalities,
and outputs artifacts/centauri/driverkit/extraction_inventory.json.
"""

import os
import sys
import json
import hashlib
import struct
import subprocess
import plistlib
from pathlib import Path

ROOT = Path("/home/prem/Projects/iOS 27")
RAMDISK_APFS = ROOT / "artifacts/rootfs/141-09491-242_restoreramdisk.apfs"
RESTORE_DMG = ROOT / "iPhone18,3_27.2_24B119_Restore/141-09491-242.dmg"
OUTPUT_DIR = ROOT / "artifacts/centauri/driverkit"
INVENTORY_JSON = OUTPUT_DIR / "extraction_inventory.json"

TARGET_EXTRACT_PATTERNS = [
    "System/Library/DriverExtensions/AppleCentauri*",
    "System/DriverKit/System/Library/PrivateFrameworks/*Centauri*",
    "System/DriverKit/System/Library/PrivateFrameworks/AirshipDK.framework*",
    "System/Library/PrivateFrameworks/Airship*",
    "System/Library/PrivateFrameworks/Centauri*",
    "usr/lib/updaters/libCentauriUpdater.dylib"
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inspect_macho(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            header = f.read(32)
        if len(header) < 32:
            return {"is_macho": False}
        magic = struct.unpack("<I", header[:4])[0]
        if magic != 0xfeedfacf: # MH_MAGIC_64
            return {"is_macho": False, "magic_hex": hex(magic)}
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack("<IIIIII", header[4:28])
        cpu_name = "arm64" if cputype == 0x0100000c else hex(cputype)
        if cpusubtype == 0x80000002 or (cpusubtype & 0xff) == 2:
            cpu_name = "arm64e"
        filetype_names = {
            2: "MH_EXECUTE",
            6: "MH_DYLIB",
            7: "MH_DYLINKER",
            8: "MH_BUNDLE"
        }
        return {
            "is_macho": True,
            "cpu_architecture": cpu_name,
            "cputype": cputype,
            "cpusubtype": cpusubtype,
            "filetype": filetype_names.get(filetype, hex(filetype)),
            "ncmds": ncmds,
            "sizeofcmds": sizeofcmds,
            "flags": hex(flags)
        }
    except Exception as e:
        return {"is_macho": False, "error": str(e)}

def parse_plist_file(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            pl = plistlib.load(f)
        summary = {
            "is_plist": True,
            "keys": list(pl.keys())
        }
        if "CFBundleIdentifier" in pl:
            summary["bundle_identifier"] = pl["CFBundleIdentifier"]
        if "CFBundleExecutable" in pl:
            summary["bundle_executable"] = pl["CFBundleExecutable"]
        if "IOKitPersonalities" in pl:
            personalities = {}
            for name, pdef in pl["IOKitPersonalities"].items():
                pinfo = {}
                for k in ["IOClass", "IOProviderClass", "IONameMatch", "CFBundleIdentifier", "IOMatchCategory", "IOUserServerName"]:
                    if k in pdef:
                        pinfo[k] = pdef[k]
                personalities[name] = pinfo
            summary["iokit_personalities"] = personalities
        return summary
    except Exception as e:
        return {"is_plist": False, "error": str(e)}

def run_extraction():
    print(f"[*] Centauri DriverKit Extraction Harness")
    print(f"[*] Target RAMDisk: {RAMDISK_APFS}")
    print(f"[*] Target Output: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAMDISK_APFS.exists():
        if RESTORE_DMG.exists():
            print(f"[!] {RAMDISK_APFS} not found. Attempting extraction from IM4P DMG...")
            # Unpack rdsk from IM4P if needed
            raise FileNotFoundError(f"Missing APFS image: {RAMDISK_APFS}")
        else:
            raise FileNotFoundError(f"Missing restore assets: {RAMDISK_APFS}")

    # Invoke 7z to extract patterns
    cmd = ["7z", "x", "-y", f"-o{OUTPUT_DIR}", str(RAMDISK_APFS)] + TARGET_EXTRACT_PATTERNS
    print(f"[*] Executing 7z extraction command...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] 7z extraction warning / error: {res.stderr}")
    else:
        print(f"[+] 7z extraction completed successfully.")

    # Catalog extracted files
    inventory = {
        "source_ramdisk": str(RAMDISK_APFS.relative_to(ROOT)),
        "source_size_bytes": RAMDISK_APFS.stat().st_size,
        "source_sha256": sha256_file(RAMDISK_APFS),
        "target_output_directory": str(OUTPUT_DIR.relative_to(ROOT)),
        "extracted_files": [],
        "dext_bundles": [],
        "framework_bundles": [],
        "configuration_plists": []
    }

    print("\n" + "="*90)
    print(f"{'Extracted File / Binary':<55} | {'Size (B)':<10} | {'Type / Architecture'}")
    print("="*90)

    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            fp = Path(root) / f
            rel_path = str(fp.relative_to(OUTPUT_DIR))
            size = fp.stat().st_size
            sha = sha256_file(fp)
            macho_info = inspect_macho(fp)
            plist_info = {}
            if f.endswith(".plist"):
                plist_info = parse_plist_file(fp)

            file_entry = {
                "relative_path": rel_path,
                "size_bytes": size,
                "sha256": sha,
                "macho": macho_info,
                "plist": plist_info
            }
            inventory["extracted_files"].append(file_entry)

            type_desc = "Resource/Other"
            if macho_info.get("is_macho"):
                type_desc = f"Mach-O {macho_info['cpu_architecture']} ({macho_info['filetype']})"
            elif plist_info.get("is_plist"):
                type_desc = f"Property List ({len(plist_info.get('keys', []))} keys)"

            print(f"{rel_path:<55} | {size:<10} | {type_desc}")

    # Group bundles
    for d in OUTPUT_DIR.glob("**/*.dext"):
        info_p = d / "Info.plist"
        pdata = parse_plist_file(info_p) if info_p.exists() else {}
        inventory["dext_bundles"].append({
            "name": d.name,
            "path": str(d.relative_to(OUTPUT_DIR)),
            "info": pdata
        })

    for fw in OUTPUT_DIR.glob("**/*.framework"):
        info_p = fw / "Info.plist"
        pdata = parse_plist_file(info_p) if info_p.exists() else {}
        inventory["framework_bundles"].append({
            "name": fw.name,
            "path": str(fw.relative_to(OUTPUT_DIR)),
            "info": pdata
        })

    for pl in OUTPUT_DIR.glob("**/*.plist"):
        if not str(pl).endswith("Info.plist"):
            inventory["configuration_plists"].append({
                "name": pl.name,
                "path": str(pl.relative_to(OUTPUT_DIR)),
                "size_bytes": pl.stat().st_size,
                "sha256": sha256_file(pl)
            })

    with open(INVENTORY_JSON, "w") as f:
        json.dump(inventory, f, indent=2)

    print("="*90)
    print(f"[+] Total files extracted: {len(inventory['extracted_files'])}")
    print(f"[+] Dext bundles cataloged: {len(inventory['dext_bundles'])}")
    print(f"[+] Framework bundles cataloged: {len(inventory['framework_bundles'])}")
    print(f"[+] Saved inventory spec to: {INVENTORY_JSON.relative_to(ROOT)}")

if __name__ == "__main__":
    run_extraction()
