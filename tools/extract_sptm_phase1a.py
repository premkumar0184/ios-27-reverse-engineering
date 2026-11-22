#!/usr/bin/env python3
"""
tools/extract_sptm_phase1a.py — Extract and dissect SPTM, TXM, iBoot, LLB, and DeviceTree
for iOS 27.2 (24B119) / Apple Silicon A19 Pro (t8150 / v57ap).
Generates artifacts/sptm/phase_1a_workspace_baseline.json and image4_container_spec.json.
"""

import sys
import os
import struct
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from parse_im4p import parse_im4p

TARGETS = [
    {
        "id": "sptm",
        "name": "Secure Page Table Monitor",
        "fourcc": "sptm",
        "im4p_path": "iPhone18,3_27.2_24B119_Restore/Firmware/sptm.t8150.release.im4p",
        "raw_path": "artifacts/sptm/extracted/sptm.t8150.release.raw",
        "role": "Guarded EL2 (GL2) Hypervisor Memory Isolation Monitor",
        "format": "Mach-O 64-bit arm64e"
    },
    {
        "id": "txm",
        "name": "Trusted Execution Monitor (Research)",
        "fourcc": "trxm",
        "im4p_path": "iPhone18,3_27.2_24B119_Restore/Firmware/txm.iphoneos.research.im4p",
        "raw_path": "artifacts/sptm/extracted/txm.iphoneos.research.raw",
        "role": "Guarded EL1 (GL1) Code Signing Monitor & Trust Evaluation Engine",
        "format": "Mach-O 64-bit arm64e"
    },
    {
        "id": "iboot",
        "name": "Stage-2 Research Bootloader (iBoot)",
        "fourcc": "ibot",
        "im4p_path": "iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/iBoot.v57.RESEARCH_RELEASE.im4p",
        "raw_path": "artifacts/sptm/extracted/iBoot.v57.RESEARCH_RELEASE.raw",
        "role": "Stage-2 Diagnostic Bootloader with Research Diagnostic Shell",
        "format": "Bare-Metal ARM64 Executable (mBoot-20457.42.5)"
    },
    {
        "id": "llb",
        "name": "Low Level Bootloader (LLB)",
        "fourcc": "illb",
        "im4p_path": "iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/LLB.v57.RESEARCH_RELEASE.im4p",
        "raw_path": "artifacts/sptm/extracted/LLB.v57.RESEARCH_RELEASE.raw",
        "role": "Stage-1 Bootloader with Diagnostic Initialization",
        "format": "Bare-Metal ARM64 Executable (mBoot-20457.42.5)"
    },
    {
        "id": "devicetree",
        "name": "Hardware DeviceTree",
        "fourcc": "dtre",
        "im4p_path": "iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/DeviceTree.v57ap.im4p",
        "raw_path": "artifacts/sptm/extracted/DeviceTree.v57ap.raw",
        "role": "SoC T8150 Hardware Node & Physical Memory Carveout Descriptor",
        "format": "Embedded DeviceTree (EmbeddedDeviceTrees-12661.42.3)"
    }
]

def parse_asn1_container(im4p_file: Path) -> dict:
    data = im4p_file.read_bytes()
    idx = 0
    seq_tag = data[idx]; idx += 1
    first = data[idx]; idx += 1
    if first < 0x80:
        seq_len = first
    else:
        n = first & 0x7f
        seq_len = int.from_bytes(data[idx:idx+n], "big")
        idx += n
    
    # Tag 1: IA5String / Magic
    idx += 1
    magic_len = data[idx]; idx += 1
    magic = data[idx:idx+magic_len].decode("ascii", errors="replace"); idx += magic_len
    
    # Tag 2: IA5String / Type
    idx += 1
    type_len = data[idx]; idx += 1
    type_str = data[idx:idx+type_len].decode("ascii", errors="replace"); idx += type_len
    
    # Tag 3: IA5String / Description
    idx += 1
    desc_len = data[idx]; idx += 1
    desc_str = data[idx:idx+desc_len].decode("ascii", errors="replace"); idx += desc_len
    
    # Tag 4: OctetString / Payload
    idx += 1
    first_p = data[idx]; idx += 1
    if first_p < 0x80:
        payload_len = first_p
    else:
        np = first_p & 0x7f
        payload_len = int.from_bytes(data[idx:idx+np], "big")
        idx += np
    payload_offset = idx
    
    comp = "raw"
    if data[idx:idx+4] == b"bvx2":
        comp = "lzfse"
    elif data[idx:idx+4] == b"\xcf\xfa\xed\xfe":
        comp = "mach-o-64"
    elif data[idx:idx+8] == b"complzss":
        comp = "complzss"
        
    return {
        "magic": magic,
        "type": type_str,
        "description": desc_str,
        "asn1_sequence_len": seq_len,
        "payload_offset": payload_offset,
        "payload_length_bytes": payload_len,
        "compression": comp,
        "payload_header_hex": data[idx:idx+16].hex()
    }

def parse_macho_structures(macho_bytes: bytes) -> dict:
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", macho_bytes[:32])
    
    segments = []
    uuid = None
    entrypoint = None
    
    offset = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", macho_bytes[offset:offset+8])
        cmd_data = macho_bytes[offset+8:offset+cmdsize]
        
        if cmd == 0x19: # LC_SEGMENT_64
            segname = cmd_data[:16].split(b"\x00")[0].decode("ascii", errors="replace")
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack("<QQQQIIII", cmd_data[16:64])
            
            sections = []
            s_offset = 64
            for _ in range(nsects):
                sect_bytes = cmd_data[s_offset:s_offset+80]
                sectname = sect_bytes[:16].split(b"\x00")[0].decode("ascii", errors="replace")
                s_segname = sect_bytes[16:32].split(b"\x00")[0].decode("ascii", errors="replace")
                s_addr, s_size, s_off, s_align, s_reloff, s_nreloc, s_flags, r1, r2, r3 = struct.unpack("<QQIIIIIIII", sect_bytes[32:80])
                sections.append({
                    "name": sectname,
                    "segment": s_segname,
                    "addr": hex(s_addr),
                    "size": hex(s_size),
                    "size_bytes": s_size,
                    "offset": hex(s_off)
                })
                s_offset += 80
                
            segments.append({
                "name": segname,
                "vmaddr": hex(vmaddr),
                "vmsize": hex(vmsize),
                "vmsize_bytes": vmsize,
                "fileoff": hex(fileoff),
                "filesize": hex(filesize),
                "filesize_bytes": filesize,
                "initprot": initprot,
                "maxprot": maxprot,
                "sections": sections
            })
            
        elif cmd == 0x1b: # LC_UUID
            raw_u = cmd_data[:16].hex()
            uuid = f"{raw_u[0:8]}-{raw_u[8:12]}-{raw_u[12:16]}-{raw_u[16:20]}-{raw_u[20:32]}"
            
        elif cmd == 0x80000028: # LC_MAIN
            entryoff = struct.unpack("<Q", cmd_data[:8])[0]
            entrypoint = hex(entryoff)
        elif cmd == 0x5: # LC_UNIXTHREAD
            flavor, count = struct.unpack("<II", cmd_data[:8])
            if flavor == 6:
                pc = struct.unpack("<Q", cmd_data[264:272])[0]
                entrypoint = hex(pc)
            
        offset += cmdsize
        
    return {
        "magic": hex(magic),
        "cputype": hex(cputype),
        "cpusubtype": hex(cpusubtype),
        "filetype": hex(filetype),
        "ncmds": ncmds,
        "uuid": uuid,
        "entrypoint": entrypoint,
        "segments": segments
    }

def main():
    print("[+] Extracting and cataloging SPTM & TXM target assets...")
    out_dir = ROOT / "artifacts/sptm/extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    baseline_catalog = {}
    container_specs = []
    
    for t in TARGETS:
        im4p_p = ROOT / t["im4p_path"]
        raw_p = ROOT / t["raw_path"]
        
        im4p_data = im4p_p.read_bytes()
        im4p_sha256 = hashlib.sha256(im4p_data).hexdigest()
        
        # Decompress/extract raw payload
        parse_im4p(im4p_p, raw_p)
        raw_data = raw_p.read_bytes()
        raw_sha256 = hashlib.sha256(raw_data).hexdigest()
        
        asn1_meta = parse_asn1_container(im4p_p)
        
        macho_meta = None
        if raw_data.startswith(b"\xcf\xfa\xed\xfe"):
            macho_meta = parse_macho_structures(raw_data)
            
        asset_info = {
            "id": t["id"],
            "name": t["name"],
            "role": t["role"],
            "fourcc_tag": t["fourcc"],
            "format": t["format"],
            "source_im4p": t["im4p_path"],
            "im4p_size_bytes": len(im4p_data),
            "im4p_sha256": im4p_sha256,
            "raw_payload_path": t["raw_path"],
            "raw_size_bytes": len(raw_data),
            "raw_sha256": raw_sha256,
            "asn1_metadata": asn1_meta
        }
        if macho_meta:
            asset_info["macho_metadata"] = macho_meta
            
        baseline_catalog[t["id"]] = asset_info
        
        container_specs.append({
            "asset_id": t["id"],
            "fourcc_tag": t["fourcc"],
            "description": asn1_meta["description"],
            "im4p_size_bytes": len(im4p_data),
            "payload_offset": asn1_meta["payload_offset"],
            "payload_length_bytes": asn1_meta["payload_length_bytes"],
            "compression_type": asn1_meta["compression"],
            "decompressed_size_bytes": len(raw_data),
            "sha256_im4p": im4p_sha256,
            "sha256_raw": raw_sha256
        })
        print(f"  [+] Cataloged {t['id']} ({t['fourcc']}) -> {len(raw_data)} bytes raw")

    # 1. artifacts/sptm/phase_1a_workspace_baseline.json
    baseline_json = {
        "schema_version": "1.0",
        "phase": "sptm_phase_1a_workspace_baseline",
        "target_device": {
            "hardware_platform": "Apple Silicon A19 Pro",
            "soc": "t8150",
            "device_class": "v57ap",
            "model": "iPhone18,3",
            "os_build": "iOS 27.2 (24B119)",
            "darwin_version": "Darwin Kernel Version 24.2.0: Fri Oct 11 20:30:00 PDT 2026",
            "architecture": "arm64e (ARMv8.6+ Guarded Execution Feature, PAC00)"
        },
        "hardware_context": {
            "execution_privilege_tiers": [
                {"tier": "Guarded EL2 (GL2)", "component": "Secure Page Table Monitor (SPTM)"},
                {"tier": "Guarded EL1 (GL1)", "component": "Trusted Execution Monitor (TXM)"},
                {"tier": "Standard EL1", "component": "Darwin / XNU Monolithic Kernel"},
                {"tier": "Standard EL0", "component": "Userland Applications & Exclave Conclaves"}
            ],
            "hardware_security_primitives": [
                "Guarded Execution Facility (GXF)",
                "Stage-2 Translation Table Virtualization (VTTBR_EL2)",
                "Configurable Text Region Register (CTRR)",
                "Guarded Address Protection Filter (GAPF)",
                "Device Address Resolution Table (DART) Stream Isolation",
                "Pointer Authentication Code (PAC00)"
            ]
        },
        "firmware_assets": baseline_catalog
    }
    
    baseline_out = ROOT / "artifacts/sptm/phase_1a_workspace_baseline.json"
    baseline_out.write_text(json.dumps(baseline_json, indent=2))
    print(f"[+] Wrote {baseline_out}")
    
    # 2. artifacts/sptm/image4_container_spec.json
    container_json = {
        "schema_version": "1.0",
        "specification": "Apple Image4 (IM4P) Payload Container Architecture",
        "parser_specification": {
            "encoding": "ASN.1 DER Sequence",
            "magic_tag": "0x16 (IA5String) -> 'IM4P'",
            "type_tag": "0x16 (IA5String) -> 4-character FourCC code",
            "desc_tag": "0x16 (IA5String) -> Build/Version descriptor string",
            "payload_tag": "0x04 (OCTET STRING) -> Compressed / Raw Binary Data",
            "compression_formats_supported": ["lzfse (bvx2 magic)", "complzss", "raw Mach-O"]
        },
        "containers": container_specs
    }
    
    container_out = ROOT / "artifacts/sptm/image4_container_spec.json"
    container_out.write_text(json.dumps(container_json, indent=2))
    print(f"[+] Wrote {container_out}")

if __name__ == "__main__":
    main()
