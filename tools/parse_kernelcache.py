#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Kernelcache MH_FILESET Parser & KEXT Catalog Extractor
========================================================================================
Parses 64-bit arm64e MH_FILESET containers (Mach-O filetype 0xc = MH_FILESET),
iterates all LC_FILESET_ENTRY load commands (cmd 0x80000035), unpacks nested
Mach-O headers (MH_EXECUTE and MH_KEXT_BUNDLE), segment load commands (LC_SEGMENT_64),
section headers (struct section_64), Mach-O UUIDs (LC_UUID), entrypoints
(LC_UNIXTHREAD for kernel, __TEXT_EXEC for KEXTs), correlates embedded prelink
property list metadata (__PRELINK_INFO), and emits structured JSON catalogs.

Hardware Target: iPhone18,3 (D93AP/D94AP)
SoC: Apple Silicon T8150 (A18 Pro)
OS Build: iOS 27.2 (24B119)
"""

import sys
import os
import struct
import json
import plistlib
import argparse
from pathlib import Path

# Mach-O Header Constants
MH_MAGIC_64 = 0xfeedfacf  # Little-endian 64-bit Mach-O
MH_CIGAM_64 = 0xcffaedfe  # Big-endian 64-bit Mach-O
CPU_TYPE_ARM64 = 0x0100000c
CPU_SUBTYPE_ARM64E = 0xc0000002

# Mach-O File Types
MH_EXECUTE = 0x2
MH_KEXT_BUNDLE = 0xb
MH_FILESET = 0xc

# Load Command Constants
LC_REQ_DYLD = 0x80000000
LC_SEGMENT_64 = 0x19
LC_SYMTAB = 0x2
LC_UNIXTHREAD = 0x5
LC_UUID = 0x1b
LC_BUILD_VERSION = 0x32
LC_DYLD_CHAINED_FIXUPS = 0x34 | LC_REQ_DYLD  # 0x80000034
LC_FILESET_ENTRY = 0x35 | LC_REQ_DYLD        # 0x80000035

# Thread state flavors (ARM64)
ARM_THREAD_STATE64 = 6
ARM_THREAD_STATE64_COUNT = 68


def parse_kernelcache(kc_path: Path) -> tuple:
    """
    Parses an arm64e MH_FILESET kernelcache binary.

    Returns:
        tuple: (catalog, metadata)
            catalog: list of 302 KEXT/kernel catalog dictionaries
            metadata: dictionary containing container-level Mach-O properties
    """
    kc_path = Path(kc_path).resolve()
    if not kc_path.is_file():
        raise FileNotFoundError(f"Kernelcache binary not found: {kc_path}")

    file_size = kc_path.stat().st_size
    print(f"[*] Opening kernelcache: {kc_path.name} ({file_size:,} bytes)")

    with open(kc_path, "rb") as f:
        # 1. Parse Mach-O 64-bit Container Header (32 bytes)
        hdr_bytes = f.read(32)
        if len(hdr_bytes) < 32:
            raise ValueError(f"File too small for 64-bit Mach-O header ({len(hdr_bytes)} bytes)")

        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack(
            "<IIIIIIII", hdr_bytes
        )

        if magic not in (MH_MAGIC_64, MH_CIGAM_64):
            raise ValueError(f"Invalid Mach-O 64-bit magic {hex(magic)} in {kc_path}")
        if filetype != MH_FILESET:
            print(f"[!] Warning: Mach-O filetype {hex(filetype)} is not canonical MH_FILESET (0xc)")

        print(f"  [+] Mach-O 64-bit Header: magic={hex(magic)} cputype={hex(cputype)} "
              f"cpusubtype={hex(cpusubtype)} filetype={hex(filetype)} (MH_FILESET) ncmds={ncmds}")

        # 2. Iterate Container Load Commands
        fileset_commands = []
        container_segments = {}
        container_uuid = None
        container_unixthread_pc = None
        prelink_info_offset = None
        prelink_info_size = 0

        pos = 32
        for cmd_idx in range(ncmds):
            f.seek(pos)
            cmd_hdr = f.read(8)
            if len(cmd_hdr) < 8:
                break
            cmd, cmdsize = struct.unpack("<II", cmd_hdr)

            if cmd == LC_FILESET_ENTRY:
                # struct fileset_entry_command {
                #     uint32_t cmd; uint32_t cmdsize; uint64_t vmaddr;
                #     uint64_t fileoff; union lc_str entry_id; uint32_t reserved;
                # };
                cmd_data = f.read(cmdsize - 8)
                vmaddr, fileoff = struct.unpack("<QQ", cmd_data[:16])
                entry_id_offset = struct.unpack("<I", cmd_data[16:20])[0]
                # String starts at entry_id_offset from start of load command
                str_rel_offset = entry_id_offset - 8
                entry_id = cmd_data[str_rel_offset:].split(b"\x00")[0].decode("utf-8", errors="replace")
                fileset_commands.append({
                    "entry_id": entry_id,
                    "vmaddr": vmaddr,
                    "fileoff": fileoff,
                    "cmdsize": cmdsize
                })

            elif cmd == LC_SEGMENT_64:
                segname = f.read(16).rstrip(b"\x00").decode("utf-8", errors="replace")
                svmaddr, svmsize, sfileoff, sfilesize, maxprot, initprot, nsects, sflags = struct.unpack(
                    "<QQQQIIII", f.read(48)
                )
                container_segments[segname] = {
                    "vmaddr": hex(svmaddr),
                    "vmsize": svmsize,
                    "fileoff": hex(sfileoff),
                    "filesize": sfilesize,
                    "nsects": nsects
                }
                if segname == "__PRELINK_INFO":
                    prelink_info_offset = sfileoff
                    prelink_info_size = sfilesize

            elif cmd == LC_UUID:
                uuid_bytes = f.read(16)
                container_uuid = uuid_bytes.hex()

            elif cmd == LC_UNIXTHREAD:
                flavor, count = struct.unpack("<II", f.read(8))
                if flavor == ARM_THREAD_STATE64 and count >= 68:
                    regs = struct.unpack("<33Q", f.read(33 * 8))
                    container_unixthread_pc = hex(regs[32])

            pos += cmdsize

        print(f"  [+] Container UUID: {container_uuid}")
        print(f"  [+] Found {len(fileset_commands)} LC_FILESET_ENTRY commands")
        print(f"  [+] Found {len(container_segments)} container segments")

        # 3. Parse Embedded __PRELINK_INFO XML Plist
        prelink_meta = {}
        if prelink_info_offset and prelink_info_size > 0:
            print(f"[*] Parsing __PRELINK_INFO at file offset {hex(prelink_info_offset)} ({prelink_info_size:,} bytes)...")
            f.seek(prelink_info_offset)
            plist_raw = f.read(prelink_info_size).rstrip(b"\x00")
            try:
                pl = plistlib.loads(plist_raw)
                prelink_list = pl.get("_PrelinkInfoDictionary", [])
                for item in prelink_list:
                    bid = item.get("CFBundleIdentifier")
                    if bid:
                        prelink_meta[bid] = item
                print(f"  [+] Loaded {len(prelink_meta)} bundle metadata descriptors from _PrelinkInfoDictionary")
            except Exception as pe:
                print(f"[!] Warning: Failed to parse __PRELINK_INFO plist: {pe}")

        # 4. Iterate and Parse Each Sub-Binary Mach-O
        print(f"[*] Dissecting {len(fileset_commands)} sub-binaries at their respective file offsets...")
        catalog = []

        for idx, fc in enumerate(fileset_commands):
            entry_id = fc["entry_id"]
            vmaddr = fc["vmaddr"]
            fileoff = fc["fileoff"]

            f.seek(fileoff)
            sub_hdr = f.read(32)
            if len(sub_hdr) < 32:
                print(f"[!] Warning: Sub-binary header truncated for {entry_id} at {hex(fileoff)}")
                continue

            smagic, scpu, ssubcpu, sfiletype, sncmds, sszcmds, sflags, _ = struct.unpack(
                "<IIIIIIII", sub_hdr
            )
            if smagic not in (MH_MAGIC_64, MH_CIGAM_64):
                print(f"[!] Warning: Invalid magic {hex(smagic)} in sub-binary {entry_id} at {hex(fileoff)}")
                continue

            sub_pos = fileoff + 32
            segments_list = []
            segment_map = {}
            total_resident_size = 0
            sub_unixthread_pc = None
            sub_uuid = None

            for _ in range(sncmds):
                f.seek(sub_pos)
                scmd_hdr = f.read(8)
                if len(scmd_hdr) < 8:
                    break
                scmd, scmdsize = struct.unpack("<II", scmd_hdr)

                if scmd == LC_SEGMENT_64:
                    sname = f.read(16).rstrip(b"\x00").decode("utf-8", errors="replace")
                    svmaddr, svmsize, sfileoff, sfilesize, maxprot, initprot, nsects, sflags = struct.unpack(
                        "<QQQQIIII", f.read(48)
                    )

                    sections = []
                    for _ in range(nsects):
                        sec_name = f.read(16).rstrip(b"\x00").decode("utf-8", errors="replace")
                        sec_segname = f.read(16).rstrip(b"\x00").decode("utf-8", errors="replace")
                        sec_addr, sec_size, sec_off, sec_align, sec_reloff, sec_nreloc, sec_flags, r1, r2, r3 = struct.unpack(
                            "<QQIIIIIIII", f.read(48)
                        )
                        sections.append({
                            "name": sec_name,
                            "segname": sec_segname,
                            "addr": hex(sec_addr),
                            "addr_int": sec_addr,
                            "size": sec_size,
                            "offset": sec_off,
                            "offset_hex": hex(sec_off),
                            "align": sec_align,
                            "flags": sec_flags
                        })

                    seg_obj = {
                        "name": sname,
                        "vmaddr": hex(svmaddr),
                        "vmaddr_int": svmaddr,
                        "vmsize": svmsize,
                        "fileoff": sfileoff,
                        "fileoff_hex": hex(sfileoff),
                        "filesize": sfilesize,
                        "maxprot": maxprot,
                        "initprot": initprot,
                        "nsects": nsects,
                        "sections": sections
                    }
                    segments_list.append(seg_obj)
                    segment_map[sname] = seg_obj

                    # Dedicated resident memory footprint excludes shared master __LINKEDIT
                    if sname != "__LINKEDIT":
                        total_resident_size += svmsize

                elif scmd == LC_UNIXTHREAD:
                    t_hdr = f.read(8)
                    if len(t_hdr) == 8:
                        flavor, count = struct.unpack("<II", t_hdr)
                        if flavor == ARM_THREAD_STATE64 and count >= 68:
                            regs_data = f.read(33 * 8)
                            if len(regs_data) == 33 * 8:
                                regs = struct.unpack("<33Q", regs_data)
                                sub_unixthread_pc = hex(regs[32])

                elif scmd == LC_UUID:
                    uuid_bytes = f.read(16)
                    if len(uuid_bytes) == 16:
                        sub_uuid = uuid_bytes.hex()

                sub_pos += scmdsize

            # Determine Entrypoint and Entrypoint Type
            if entry_id == "com.apple.kernel" and sub_unixthread_pc:
                entrypoint = sub_unixthread_pc
                entrypoint_type = "LC_UNIXTHREAD"
            elif sub_unixthread_pc:
                entrypoint = sub_unixthread_pc
                entrypoint_type = "LC_UNIXTHREAD"
            elif "__TEXT_EXEC" in segment_map:
                entrypoint = segment_map["__TEXT_EXEC"]["vmaddr"]
                entrypoint_type = "__TEXT_EXEC"
            elif "__TEXT" in segment_map:
                entrypoint = segment_map["__TEXT"]["vmaddr"]
                entrypoint_type = "__TEXT"
            else:
                entrypoint = hex(vmaddr)
                entrypoint_type = "vmaddr"

            # Cross-reference with Prelink Plist Metadata
            pl_info = prelink_meta.get(entry_id, {})
            version = pl_info.get("CFBundleShortVersionString") or pl_info.get("CFBundleVersion")
            dependencies = list(pl_info.get("OSBundleLibraries", {}).keys())
            bundle_path = pl_info.get("_PrelinkBundlePath")

            # Format Filetype Label
            filetype_label = (
                "MH_EXECUTE" if sfiletype == MH_EXECUTE
                else "MH_KEXT_BUNDLE" if sfiletype == MH_KEXT_BUNDLE
                else hex(sfiletype)
            )

            # Build Full Catalog Entry
            entry_dict = {
                "bundle_id": entry_id,
                "fileset_entry": entry_id,
                "vmaddr": hex(vmaddr),
                "vmaddr_int": vmaddr,
                "fileoff": fileoff,
                "fileoff_hex": hex(fileoff),
                "size": total_resident_size,
                "filetype": filetype_label,
                "filetype_id": sfiletype,
                "uuid": sub_uuid,
                "entrypoint": entrypoint,
                "entrypoint_type": entrypoint_type,
                "num_segments": len(segments_list),
                "segments": segments_list,
                "segment_map": segment_map,
                "version": version,
                "dependencies": dependencies,
                "bundle_path": bundle_path
            }
            catalog.append(entry_dict)

        metadata = {
            "kernelcache_file": kc_path.name,
            "kernelcache_path": str(kc_path),
            "file_size": file_size,
            "magic": hex(magic),
            "cputype": hex(cputype),
            "cpusubtype": hex(cpusubtype),
            "filetype": hex(filetype),
            "container_uuid": container_uuid,
            "container_ncmds": ncmds,
            "fileset_entry_count": len(fileset_commands),
            "cataloged_entry_count": len(catalog),
            "prelink_bundle_count": len(prelink_meta),
            "container_segments": container_segments
        }

        print(f"[+] Successfully extracted catalog with {len(catalog)} entries from {kc_path.name}")
        return catalog, metadata


def process_kernelcache_to_catalog(kc_path: Path, out_path: Path) -> list:
    """Parses kernelcache and writes catalog JSON to disk."""
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    catalog, meta = parse_kernelcache(kc_path)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    written_size = out_path.stat().st_size
    print(f"[+] Wrote catalog JSON to {out_path} ({written_size:,} bytes, {len(catalog)} entries)")
    return catalog


def main():
    parser = argparse.ArgumentParser(
        description="iOS 27 arm64e MH_FILESET Kernelcache Parser & KEXT Catalog Generator"
    )
    parser.add_argument("input", nargs="?", help="Path to input kernelcache.raw binary")
    parser.add_argument("output", nargs="?", help="Path to output kext_catalog.json")
    parser.add_argument("--release", action="store_true", help="Parse release kernelcache only")
    parser.add_argument("--research", action="store_true", help="Parse research kernelcache only")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    # Explicit input/output arguments provided
    if args.input and args.output:
        process_kernelcache_to_catalog(Path(args.input), Path(args.output))
        return

    # Mode-based or default execution (processes both release and research)
    release_raw = project_root / "artifacts/kernel/kernelcache.release.raw"
    research_raw = project_root / "artifacts/kernel/kernelcache.research.raw"
    release_json = project_root / "artifacts/kernel/kext_catalog_release.json"
    research_json = project_root / "artifacts/kernel/kext_catalog_research.json"

    if args.release:
        process_kernelcache_to_catalog(release_raw, release_json)
    elif args.research:
        process_kernelcache_to_catalog(research_raw, research_json)
    else:
        print("================================================================================")
        print("iOS 27.2 (24B119) MH_FILESET Dual Kernelcache Parser & KEXT Extractor")
        print("================================================================================")
        cat_rel = process_kernelcache_to_catalog(release_raw, release_json)
        print("-" * 80)
        cat_res = process_kernelcache_to_catalog(research_raw, research_json)
        print("================================================================================")
        print(f"[SUMMARY] Successfully generated dual catalogs:")
        print(f"  - Release Catalog:  {release_json} ({len(cat_rel)} entries)")
        print(f"  - Research Catalog: {research_json} ({len(cat_res)} entries)")
        print("================================================================================")


if __name__ == "__main__":
    main()
