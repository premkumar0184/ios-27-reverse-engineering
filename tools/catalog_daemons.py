#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Daemon & Mach Services Cataloger
Extracts launch daemon plists, Mach services, privilege topologies,
and cross-references core daemons with Mach-O load commands and entitlements.
"""

import sys
import os
import struct
import plistlib
import json
from pathlib import Path
from collections import defaultdict

CORE_DAEMONS = {
    "launchd": "sbin/launchd",
    "commcenter": "System/Library/Frameworks/CoreTelephony.framework/Support/CommCenter",
    "wifid": "usr/sbin/wifid",
    "bluetoothd": "usr/sbin/bluetoothd",
    "securityd": "usr/libexec/securityd",
    "amfid": "usr/libexec/amfid",
    "trustd": "usr/libexec/trustd",
    "dyld": "usr/lib/dyld",
    "logd": "usr/libexec/logd",
    "notifyd": "usr/sbin/notifyd",
    "containermanagerd": "usr/libexec/containermanagerd",
    "sysdiagnosed": "usr/libexec/sysdiagnosed",
    "thermalmonitord": "usr/libexec/thermalmonitord",
    "UserEventAgent": "usr/libexec/UserEventAgent",
    "tccd": "System/Library/PrivateFrameworks/TCC.framework/Support/tccd"
}

def parse_macho_details(binary_path: Path) -> dict:
    if not binary_path.is_file():
        return {}

    with open(binary_path, "rb") as f:
        data = f.read(4096)
        if len(data) < 32:
            return {}

        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', data[:32])
        if magic != 0xfeedfacf: # MH_MAGIC_64
            return {}

        f.seek(32)
        cmds_data = f.read(sizeofcmds)

    offset = 0
    uuid_str = None
    cs_offset, cs_size = 0, 0
    dylibs = []

    for _ in range(ncmds):
        if offset + 8 > len(cmds_data):
            break
        cmd, cmdsize = struct.unpack('<II', cmds_data[offset:offset+8])
        if cmd == 0x1b and cmdsize >= 24: # LC_UUID
            ubytes = cmds_data[offset+8:offset+24]
            uuid_str = f"{ubytes[:4].hex()}-{ubytes[4:6].hex()}-{ubytes[6:8].hex()}-{ubytes[8:10].hex()}-{ubytes[10:].hex()}"
        elif cmd == 0x1d and cmdsize >= 16: # LC_CODE_SIGNATURE
            cs_offset, cs_size = struct.unpack('<II', cmds_data[offset+8:offset+16])
        elif cmd in (0xc, 0xd, 0x80000018): # LC_LOAD_DYLIB / LC_ID_DYLIB / LC_LOAD_UPWARD_DYLIB
            str_off = struct.unpack('<I', cmds_data[offset+8:offset+12])[0]
            dylib_name = cmds_data[offset+str_off:offset+cmdsize].split(b'\x00')[0].decode('utf-8', errors='ignore')
            dylibs.append(dylib_name)
        offset += cmdsize

    entitlements_dict = None
    if cs_offset > 0:
        with open(binary_path, "rb") as f:
            f.seek(cs_offset)
            cs_super = f.read(12)
            if len(cs_super) == 12:
                cs_magic, cs_len, cs_count = struct.unpack('>III', cs_super)
                if cs_magic == 0xfade0cc0: # CSMAGIC_EMBEDDED_SIGNATURE
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
        "file_size": binary_path.stat().st_size,
        "uuid": uuid_str,
        "load_commands_count": ncmds,
        "sizeofcmds": sizeofcmds,
        "imported_dylibs_count": len(dylibs),
        "imported_dylibs": dylibs,
        "entitlements": entitlements_dict
    }

def main():
    launch_daemons_dir = Path("artifacts/rootfs/launch_daemons")
    binaries_dir = Path("artifacts/rootfs/binaries")
    
    if not launch_daemons_dir.is_dir():
        print(f"[ERROR] Launch daemons directory not found: {launch_daemons_dir}")
        sys.exit(1)

    plist_files = sorted(launch_daemons_dir.glob("*.plist"))
    print(f"[*] Scanning {len(plist_files)} launch daemon plists...")

    daemons = []
    mach_services_map = {}
    user_counts = defaultdict(int)
    process_type_counts = defaultdict(int)

    for pfile in plist_files:
        try:
            with open(pfile, "rb") as fp:
                d = plistlib.load(fp)
        except Exception as e:
            print(f"[WARN] Failed to parse plist {pfile.name}: {e}")
            continue

        label = d.get("Label", pfile.stem)
        prog = d.get("Program")
        prog_args = d.get("ProgramArguments", [])
        if not prog and prog_args and len(prog_args) > 0:
            prog = prog_args[0]

        # MachServices
        mach_svcs = []
        raw_ms = d.get("MachServices", {})
        if isinstance(raw_ms, dict):
            mach_svcs = list(raw_ms.keys())
        elif isinstance(raw_ms, list):
            mach_svcs = raw_ms

        user = d.get("UserName", "root")
        if isinstance(user, dict):
            user_key = f"conditional:{user.get('#Then', user.get('#Else', 'unknown'))}"
        else:
            user_key = str(user)

        group = d.get("GroupName", "wheel" if user == "root" else ("mobile" if user == "mobile" else "daemon"))
        if isinstance(group, dict):
            group_key = f"conditional:{group.get('#Then', group.get('#Else', 'unknown'))}"
        else:
            group_key = str(group)

        ptype = d.get("ProcessType", "Standard")
        ptype_key = str(ptype) if not isinstance(ptype, dict) else f"conditional:{ptype.get('#Then', 'unknown')}"

        user_counts[user_key] += 1
        process_type_counts[ptype_key] += 1

        daemon_info = {
            "label": label,
            "plist_file": pfile.name,
            "program": prog,
            "program_arguments": prog_args,
            "user": user,
            "group": group,
            "process_type": ptype,
            "posix_spawn_type": d.get("POSIXSpawnType"),
            "run_at_load": d.get("RunAtLoad", False),
            "keep_alive": d.get("KeepAlive", False),
            "enable_transactions": d.get("EnableTransactions", False),
            "mach_services": mach_svcs,
            "raw_mach_services_dict": raw_ms if isinstance(raw_ms, dict) else {},
            "environment_variables": d.get("EnvironmentVariables", {}),
            "jetsam_properties": d.get("JetsamProperties") or d.get("JetsamPriority")
        }
        daemons.append(daemon_info)

        for ms in mach_svcs:
            mach_services_map[ms] = {
                "daemon_label": label,
                "plist_file": pfile.name,
                "program": prog,
                "user": user,
                "process_type": ptype
            }

    print(f"[+] Cataloged {len(daemons)} daemons with {len(mach_services_map)} distinct MachServices.")

    # Core Daemons Deep-Dive
    core_daemon_profiles = {}
    EXACT_PLIST_MAP = {
        "launchd": None, # PID 1 root supervisor spawned directly by XNU kernel
        "commcenter": "com.apple.CommCenter.plist",
        "wifid": "com.apple.wifid.plist",
        "bluetoothd": "com.apple.bluetoothd.plist",
        "securityd": "com.apple.securityd.plist",
        "amfid": "com.apple.MobileFileIntegrity.plist",
        "trustd": "com.apple.trustd.plist",
        "dyld": None, # Dynamic linker mapped into userspace by kernel
        "logd": "com.apple.logd.plist",
        "notifyd": "com.apple.notifyd.plist",
        "containermanagerd": "com.apple.containermanagerd.system.plist",
        "sysdiagnosed": "com.apple.sysdiagnose.plist",
        "thermalmonitord": "com.apple.thermalmonitord.plist",
        "UserEventAgent": "com.apple.UserEventAgent-System.plist",
        "tccd": "com.apple.tccd.plist"
    }

    for name, rel_bin_path in CORE_DAEMONS.items():
        bin_path = binaries_dir / rel_bin_path
        macho_info = parse_macho_details(bin_path)

        target_plist = EXACT_PLIST_MAP.get(name)
        matched_daemon = None
        if target_plist:
            matches = [d for d in daemons if d["plist_file"] == target_plist]
            if matches:
                matched_daemon = matches[0]

        core_daemon_profiles[name] = {
            "canonical_name": name,
            "binary_path": "/" + rel_bin_path,
            "role": "PID 1 Boot Supervisor" if name == "launchd" else ("Dynamic Linker" if name == "dyld" else "System Daemon"),
            "disk_extracted_path": str(bin_path) if bin_path.exists() else None,
            "macho_analysis": macho_info,
            "launchd_configuration": matched_daemon
        }

    # Generate daemon_catalog.json
    catalog_artifact = {
        "metadata": {
            "total_daemons": len(daemons),
            "total_mach_services": len(mach_services_map),
            "user_distribution": dict(user_counts),
            "process_type_distribution": dict(process_type_counts),
            "core_daemons_cataloged": list(CORE_DAEMONS.keys())
        },
        "core_system_daemons": core_daemon_profiles,
        "all_daemons": daemons
    }

    out_catalog = Path("artifacts/rootfs/daemon_catalog.json")
    with open(out_catalog, "w", encoding="utf-8") as f:
        json.dump(catalog_artifact, f, indent=2)
    print(f"[+] Wrote {out_catalog} ({out_catalog.stat().st_size} bytes)")

    # Generate mach_services_map.json
    services_artifact = {
        "metadata": {
            "total_mach_services": len(mach_services_map),
            "total_registered_daemons": len(daemons)
        },
        "services": mach_services_map
    }

    out_services = Path("artifacts/rootfs/mach_services_map.json")
    with open(out_services, "w", encoding="utf-8") as f:
        json.dump(services_artifact, f, indent=2)
    print(f"[+] Wrote {out_services} ({out_services.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
