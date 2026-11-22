#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Application Ecosystem Matrix
Extracts metadata, exported URL schemes, Mach-O load commands, imported dylibs,
and embedded code signature entitlements for core iOS applications.
"""

import sys
import os
import plistlib
import struct
import json
from pathlib import Path

APPS_CONFIG = [
    {
        "canonical_name": "Preferences",
        "display_name": "Settings",
        "relative_dir": "Applications/Preferences.app",
        "binary_name": "Preferences"
    },
    {
        "canonical_name": "MobileSafari",
        "display_name": "Safari",
        "relative_dir": "private/var/staged_system_apps/MobileSafari.app",
        "binary_name": "MobileSafari"
    },
    {
        "canonical_name": "MobileSMS",
        "display_name": "Messages",
        "relative_dir": "private/var/staged_system_apps/MobileSMS.app",
        "binary_name": "MobileSMS"
    },
    {
        "canonical_name": "Camera",
        "display_name": "Camera",
        "relative_dir": "private/var/staged_system_apps/Camera.app",
        "binary_name": "Camera"
    },
    {
        "canonical_name": "Health",
        "display_name": "Health",
        "relative_dir": "private/var/staged_system_apps/Health.app",
        "binary_name": "Health"
    },
    {
        "canonical_name": "Passbook",
        "display_name": "Wallet",
        "relative_dir": "private/var/staged_system_apps/Passbook.app",
        "binary_name": "Passbook"
    }
]

def parse_macho_app(bin_path: Path) -> dict:
    if not bin_path.is_file():
        return {}

    with open(bin_path, "rb") as f:
        data = f.read(4096)
        if len(data) < 32:
            return {}

        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', data[:32])
        if magic != 0xfeedfacf:
            return {}

        f.seek(32)
        cmds_data = f.read(sizeofcmds)

    offset = 0
    uuid_str = None
    cs_offset, cs_size = 0, 0
    dylibs = []
    entryoff = None

    for _ in range(ncmds):
        if offset + 8 > len(cmds_data):
            break
        cmd, cmdsize = struct.unpack('<II', cmds_data[offset:offset+8])
        if cmd == 0x1b and cmdsize >= 24: # LC_UUID
            ubytes = cmds_data[offset+8:offset+24]
            uuid_str = f"{ubytes[:4].hex()}-{ubytes[4:6].hex()}-{ubytes[6:8].hex()}-{ubytes[8:10].hex()}-{ubytes[10:].hex()}"
        elif cmd == 0x1d and cmdsize >= 16: # LC_CODE_SIGNATURE
            cs_offset, cs_size = struct.unpack('<II', cmds_data[offset+8:offset+16])
        elif cmd == 0x80000028: # LC_MAIN
            entryoff = struct.unpack('<QQ', cmds_data[offset+8:offset+24])[0]
        elif cmd in (0xc, 0xd, 0x80000018):
            str_off = struct.unpack('<I', cmds_data[offset+8:offset+12])[0]
            dname = cmds_data[offset+str_off:offset+cmdsize].split(b'\x00')[0].decode('utf-8', errors='ignore')
            dylibs.append(dname)
        offset += cmdsize

    entitlements_dict = None
    if cs_offset > 0:
        with open(bin_path, "rb") as f:
            f.seek(cs_offset)
            cs_super = f.read(12)
            if len(cs_super) == 12:
                cs_magic, cs_len, cs_count = struct.unpack('>III', cs_super)
                if cs_magic == 0xfade0cc0:
                    for _ in range(cs_count):
                        idx_data = f.read(8)
                        if len(idx_data) < 8:
                            break
                        blob_type, blob_off = struct.unpack('>II', idx_data)
                        if blob_type == 5: # CSSLOT_ENTITLEMENTS
                            cur = f.tell()
                            f.seek(cs_offset + blob_off)
                            e_hdr = f.read(8)
                            if len(e_hdr) == 8:
                                e_magic, e_len = struct.unpack('>II', e_hdr)
                                e_bytes = f.read(e_len - 8)
                                try:
                                    entitlements_dict = plistlib.loads(e_bytes)
                                except Exception:
                                    entitlements_dict = {"raw_xml": e_bytes.decode('utf-8', errors='ignore')}
                            f.seek(cur)
                            break

    return {
        "file_size": bin_path.stat().st_size,
        "uuid": uuid_str,
        "entryoff": f"0x{entryoff:x}" if entryoff is not None else None,
        "load_commands_count": ncmds,
        "imported_dylibs_count": len(dylibs),
        "imported_dylibs": dylibs,
        "entitlements_count": len(entitlements_dict) if entitlements_dict else 0,
        "entitlements": entitlements_dict
    }

def main():
    base_dir = Path("artifacts/ui/Applications")
    if not base_dir.is_dir():
        print(f"[ERROR] Base dir not found: {base_dir}")
        sys.exit(1)

    app_dirs = sorted([d for d in base_dir.rglob("*.app") if d.is_dir()])
    print(f"[*] Dynamically detected {len(app_dirs)} extracted system application bundles...")
    matrix = []

    for app_dir in app_dirs:
        plist_path = app_dir / "Info.plist"
        if not plist_path.is_file():
            continue

        try:
            with open(plist_path, "rb") as f:
                plist_data = plistlib.load(f)
        except Exception as pe:
            print(f"[WARN] Failed to read {plist_path}: {pe}")
            continue

        exec_name = plist_data.get("CFBundleExecutable", app_dir.stem)
        bin_path = app_dir / exec_name

        # Extract URL schemes
        url_schemes = []
        for url_type in plist_data.get("CFBundleURLTypes", []):
            url_schemes.extend(url_type.get("CFBundleURLSchemes", []))

        # Mach-O inspection
        macho_info = parse_macho_app(bin_path)

        app_record = {
            "canonical_name": app_dir.stem,
            "display_name": plist_data.get("CFBundleDisplayName", plist_data.get("CFBundleName", app_dir.stem)),
            "relative_path": str(app_dir.relative_to(base_dir)),
            "bundle_identifier": plist_data.get("CFBundleIdentifier"),
            "bundle_version": plist_data.get("CFBundleVersion"),
            "short_version": plist_data.get("CFBundleShortVersionString"),
            "executable_name": exec_name,
            "device_family": plist_data.get("UIDeviceFamily"),
            "exported_url_schemes": sorted(list(set(url_schemes))),
            "minimum_os_version": plist_data.get("MinimumOSVersion"),
            "sdk_build": plist_data.get("DTSDKBuild"),
            "background_modes": plist_data.get("UIBackgroundModes", []),
            "scene_manifest": bool(plist_data.get("UIApplicationSceneManifest")),
            "macho_analysis": macho_info
        }
        matrix.append(app_record)

    out_file = Path("artifacts/ui/app_ecosystem_matrix.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print(f"[+] Successfully wrote {out_file} ({out_file.stat().st_size} bytes)")
    print(f"    - Cataloged {len(matrix)} core applications.")
    for app in matrix:
        print(f"      * {app['display_name']} ({app['bundle_identifier']}): {len(app['exported_url_schemes'])} schemes, {app['macho_analysis'].get('imported_dylibs_count', 0)} dylibs, {app['macho_analysis'].get('entitlements_count', 0)} entitlements")

if __name__ == "__main__":
    main()
