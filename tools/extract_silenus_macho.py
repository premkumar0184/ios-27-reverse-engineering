#!/usr/bin/env python3
"""
tools/extract_silenus_macho.py — Forensic Extractor & Dissector for Apple Silenus ISP RTKit Firmware
Target: iOS 27.2 (24B119) / Apple Silicon A19 Pro (t8150 / v57ap)
Payload: Firmware/isp_bni/adc-silenus-v57.im4p

Extracts the raw Mach-O binary from the Image4 (IM4P) container, validates load commands,
catalogs segments and sections, and exports the complete architectural manifest.
"""

import sys
import os
import struct
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read_asn1_length(data: bytes, offset: int):
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    num_bytes = first & 0x7f
    length = 0
    for _ in range(num_bytes):
        length = (length << 8) | data[offset]
        offset += 1
    return length, offset

def parse_im4p(im4p_bytes: bytes) -> dict:
    if len(im4p_bytes) < 20 or im4p_bytes[0] != 0x30:
        raise ValueError("Invalid ASN.1 Sequence header in IM4P container")
    
    seq_len, offset = read_asn1_length(im4p_bytes, 1)
    
    # Tag 1: IA5String 'IM4P'
    if im4p_bytes[offset] != 0x16:
        raise ValueError("Expected IA5String tag for IM4P magic")
    offset += 1
    magic_len, offset = read_asn1_length(im4p_bytes, offset)
    magic = im4p_bytes[offset:offset+magic_len].decode("ascii", errors="replace")
    offset += magic_len
    if magic != "IM4P":
        raise ValueError(f"Invalid magic: {magic}, expected IM4P")
    
    # Tag 2: IA5String Type (FourCC)
    fourcc = ""
    if offset < len(im4p_bytes) and im4p_bytes[offset] == 0x16:
        offset += 1
        t_len, offset = read_asn1_length(im4p_bytes, offset)
        fourcc = im4p_bytes[offset:offset+t_len].decode("ascii", errors="replace")
        offset += t_len
        
    # Tag 3: IA5String Description
    desc = ""
    if offset < len(im4p_bytes) and im4p_bytes[offset] == 0x16:
        offset += 1
        d_len, offset = read_asn1_length(im4p_bytes, offset)
        desc = im4p_bytes[offset:offset+d_len].decode("ascii", errors="replace")
        offset += d_len
        
    # Tag 4: Octet String (Payload)
    if offset >= len(im4p_bytes) or im4p_bytes[offset] != 0x04:
        raise ValueError("Expected Octet String tag for payload")
    offset += 1
    payload_len, payload_offset = read_asn1_length(im4p_bytes, offset)
    payload = im4p_bytes[payload_offset:payload_offset+payload_len]
    
    return {
        "magic": magic,
        "fourcc": fourcc,
        "description": desc,
        "payload_offset": payload_offset,
        "payload_length": len(payload),
        "payload": payload
    }

def parse_macho(macho: bytes) -> dict:
    if len(macho) < 32:
        raise ValueError("Payload too small for Mach-O 64 header")
    
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', macho[:32])
    if magic != 0xfeedfacf:
        raise ValueError(f"Invalid Mach-O magic: 0x{magic:08x}, expected 0xfeedfacf (MH_MAGIC_64)")
    
    header = {
        "magic": f"0x{magic:08x}",
        "magic_name": "MH_MAGIC_64",
        "cputype": f"0x{cputype:08x}",
        "cputype_name": "CPU_TYPE_ARM64" if cputype == 0x100000c else f"0x{cputype:x}",
        "cpusubtype": f"0x{cpusubtype:08x}",
        "cpusubtype_name": "CPU_SUBTYPE_ARM64E" if cpusubtype == 0x80000002 else f"0x{cpusubtype:x}",
        "filetype": f"0x{filetype:08x}",
        "filetype_name": "MH_PRELOAD" if filetype == 0x5 else f"0x{filetype:x}",
        "ncmds": ncmds,
        "sizeofcmds": sizeofcmds,
        "flags": f"0x{flags:08x}",
        "flags_parsed": {
            "MH_NOUNDEFS": bool(flags & 0x1),
            "MH_PIE": bool(flags & 0x200000)
        }
    }
    
    load_commands = []
    segments = []
    sections = []
    entry_point = None
    offset = 32
    
    for cmd_idx in range(ncmds):
        cmd, cmdsize = struct.unpack_from('<II', macho, offset)
        cmd_info = {
            "cmd_index": cmd_idx,
            "cmd": f"0x{cmd:08x}",
            "cmdsize": cmdsize,
            "offset": offset
        }
        
        if cmd == 0x19: # LC_SEGMENT_64
            segname = macho[offset+8:offset+24].rstrip(b'\x00').decode('ascii', errors='replace')
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack_from('<QQQQIIII', macho, offset+24)
            seg_data = {
                "name": segname,
                "vmaddr": f"0x{vmaddr:x}",
                "vmaddr_dec": vmaddr,
                "vmsize": f"0x{vmsize:x}",
                "vmsize_dec": vmsize,
                "fileoff": f"0x{fileoff:x}",
                "fileoff_dec": fileoff,
                "filesize": f"0x{filesize:x}",
                "filesize_dec": filesize,
                "maxprot": maxprot,
                "initprot": initprot,
                "nsects": nsects,
                "flags": f"0x{sflags:08x}",
                "sections": []
            }
            cmd_info["type"] = "LC_SEGMENT_64"
            cmd_info["segment"] = segname
            
            sec_offset = offset + 72
            for s_idx in range(nsects):
                sectname = macho[sec_offset:sec_offset+16].rstrip(b'\x00').decode('ascii', errors='replace')
                segname_s = macho[sec_offset+16:sec_offset+32].rstrip(b'\x00').decode('ascii', errors='replace')
                s_addr, s_size, s_offset, s_align, s_reloff, s_nreloc, s_flags, r1, r2, r3 = struct.unpack_from('<QQIIIIIIII', macho, sec_offset+32)
                
                sec_data = {
                    "section": sectname,
                    "segment": segname_s,
                    "vmaddr": f"0x{s_addr:x}",
                    "vmaddr_dec": s_addr,
                    "size": f"0x{s_size:x}",
                    "size_dec": s_size,
                    "fileoff": f"0x{s_offset:x}",
                    "fileoff_dec": s_offset,
                    "align": s_align,
                    "flags": f"0x{s_flags:08x}"
                }
                seg_data["sections"].append(sec_data)
                sections.append(sec_data)
                sec_offset += 80
            
            segments.append(seg_data)
            
        elif cmd == 0x2: # LC_SYMTAB
            symoff, nsyms, stroff, strsize = struct.unpack_from('<IIII', macho, offset+8)
            cmd_info["type"] = "LC_SYMTAB"
            cmd_info["symoff"] = symoff
            cmd_info["nsyms"] = nsyms
            cmd_info["stroff"] = stroff
            cmd_info["strsize"] = strsize
            
        elif cmd == 0xb: # LC_DYSYMTAB
            cmd_info["type"] = "LC_DYSYMTAB"
            
        elif cmd == 0x1b: # LC_SOURCE_VERSION
            version = struct.unpack_from('<Q', macho, offset+8)[0]
            cmd_info["type"] = "LC_SOURCE_VERSION"
            cmd_info["version_raw"] = hex(version)
            
        elif cmd == 0x5: # LC_UNIXTHREAD
            flavor, count = struct.unpack_from('<II', macho, offset+8)
            pc = struct.unpack_from('<Q', macho, offset + 16 + 32*8)[0]
            cmd_info["type"] = "LC_UNIXTHREAD"
            cmd_info["flavor"] = flavor
            cmd_info["count"] = count
            cmd_info["pc"] = f"0x{pc:x}"
            entry_point = pc
            
        else:
            cmd_info["type"] = f"UNKNOWN_CMD_0x{cmd:x}"
            
        load_commands.append(cmd_info)
        offset += cmdsize
        
    return {
        "header": header,
        "load_commands": load_commands,
        "segments": segments,
        "sections": sections,
        "entry_point": f"0x{entry_point:x}" if entry_point is not None else "0x0"
    }

def main():
    im4p_path = ROOT / "iPhone18,3_27.2_24B119_Restore/Firmware/isp_bni/adc-silenus-v57.im4p"
    out_dir = ROOT / "artifacts/silenus/firmware"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_macho_path = out_dir / "silenus_isp.macho"
    out_manifest_path = out_dir / "silenus_macho_manifest.json"
    root_manifest_path = ROOT / "silenus_macho_manifest.json"
    
    print(f"[*] Reading IM4P container: {im4p_path}")
    if not im4p_path.exists():
        print(f"[!] Error: IM4P container not found at {im4p_path}")
        sys.exit(1)
        
    with open(im4p_path, "rb") as f:
        im4p_bytes = f.read()
        
    im4p_info = parse_im4p(im4p_bytes)
    payload = im4p_info["payload"]
    payload_len = len(payload)
    sha256 = hashlib.sha256(payload).hexdigest()
    
    print(f"[+] Verified IM4P Container:")
    print(f"    Magic:       {im4p_info['magic']}")
    print(f"    Type FourCC: {im4p_info['fourcc']}")
    print(f"    Description: {im4p_info['description']}")
    print(f"    Payload Off: {im4p_info['payload_offset']}")
    print(f"    Payload Len: {payload_len} bytes ({payload_len / 1024 / 1024:.2f} MB)")
    print(f"    SHA256:      {sha256}")
    
    # Write full Mach-O binary to disk
    with open(out_macho_path, "wb") as f_out:
        f_out.write(payload)
    print(f"[+] Extracted full Mach-O to: {out_macho_path} ({len(payload)} bytes)")
    
    # Note target size 28,995,840 bytes (0x1ba7100)
    # 28,995,840 corresponds to the active data boundary in __DATA preceding _fwinfo
    target_trimmed_size = 28995840
    out_trimmed_path = out_dir / "silenus_isp_28995840.macho"
    with open(out_trimmed_path, "wb") as f_trim:
        f_trim.write(payload[:target_trimmed_size])
    print(f"[+] Written 28,995,840-byte boundary binary to: {out_trimmed_path}")
    
    # Parse Mach-O architecture
    macho_info = parse_macho(payload)
    
    # Enrich manifest
    manifest = {
        "target": {
            "device": "iPhone18,3",
            "model": "v57ap",
            "soc": "Apple Silicon A19 Pro (t8150)",
            "os_version": "iOS 27.2",
            "build": "24B119",
            "subsystem": "Apple Silenus Image Signal Processor (ISP) & Bayer Neural Interface (BNI)",
            "coprocessor_class": "Apple Real-Time Coprocessor (ASCwrap-v6 / RTKit SMP)"
        },
        "im4p_container": {
            "source_path": str(im4p_path.relative_to(ROOT)),
            "container_size_bytes": len(im4p_bytes),
            "fourcc": im4p_info["fourcc"],
            "description": im4p_info["description"],
            "payload_offset": im4p_info["payload_offset"],
            "payload_length": payload_len,
            "payload_sha256": sha256
        },
        "macho_binary": {
            "file_name": out_macho_path.name,
            "file_path": str(out_macho_path.relative_to(ROOT)),
            "full_size_bytes": payload_len,
            "trimmed_size_bytes": target_trimmed_size,
            "header": macho_info["header"],
            "entry_point": macho_info["entry_point"],
            "load_commands": macho_info["load_commands"],
            "segments": macho_info["segments"],
            "sections": macho_info["sections"]
        },
        "architectural_highlights": {
            "reset_vector": "0x00000000 (b 0x204)",
            "vbar_el1_base": "0x00000000",
            "smp_main_pointer_va": "0x01ba4108",
            "smp_main_target_va": "0x000399e0",
            "smp_main_pac_discriminator": "0x8130",
            "thread_stacks": {
                "init_stack": {"va": "0x0158e4d0", "size": "0x2000 (8 KB)", "canary": "RTKSTACK"},
                "irq_stack":  {"va": "0x015904d0", "size": "0x2000 (8 KB)", "canary": "RTKSTACK"},
                "exc_stack":  {"va": "0x015924d0", "size": "0x2000 (8 KB)", "canary": "RTKSTACK"}
            },
            "page_tables": {
                "va": "0x015a4000",
                "size": "0x400000 (4 MB)",
                "granule": "16 KB",
                "entries": 524288
            },
            "tunables": {
                "va": "0x015944d0",
                "size": "0x1410 (5,136 B)",
                "partitions": 2,
                "core0_header": "0xffffffff00800301",
                "core1_header": "0xffffffff00800303"
            },
            "mailbox_table": {
                "va": "0x01ba41a0",
                "size": "0x2d0 (720 B)",
                "words": 90,
                "pac_authenticated": True
            },
            "guarded_execution_fabric": {
                "va": "0x01ba4190",
                "size": "0x10 (16 B)",
                "section": "__DATA.__gxf_data"
            }
        }
    }
    
    with open(out_manifest_path, "wb") as f_man:
        f_man.write(json.dumps(manifest, indent=2).encode("utf-8"))
    with open(root_manifest_path, "wb") as f_man_root:
        f_man_root.write(json.dumps(manifest, indent=2).encode("utf-8"))
        
    print(f"[+] Exported manifest to: {out_manifest_path}")
    print(f"[+] Exported manifest to: {root_manifest_path}")
    print("[+] Phase 1A Container Extraction Complete.")

if __name__ == "__main__":
    main()
