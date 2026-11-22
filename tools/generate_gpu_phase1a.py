#!/usr/bin/env python3
"""
generate_gpu_phase1a.py — Deterministic Generator for Phase 1A GPU Baseline & Container Specs
iOS 27.2 (Darwin 24.2.0, Build 24B119) — SoC t8150 (Apple A19 Pro v57ap)
"""

import json
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_macho_segments(data: bytes):
    magic = struct.unpack('<I', data[:4])[0]
    segments = []
    
    if magic == 0xfeedfacf: # 64-bit
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', data[:32])
        offset = 32
        for _ in range(ncmds):
            cmd, cmdsize = struct.unpack('<II', data[offset:offset+8])
            if cmd == 0x19: # LC_SEGMENT_64
                segname = data[offset+8:offset+24].rstrip(b'\x00').decode('latin1')
                vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack('<QQQQIIII', data[offset+24:offset+72])
                segments.append({
                    "name": segname,
                    "vmaddr": f"0x{vmaddr:016x}",
                    "vmaddr_int": vmaddr,
                    "vmsize": vmsize,
                    "vmsize_hex": f"0x{vmsize:x}",
                    "fileoff": fileoff,
                    "fileoff_hex": f"0x{fileoff:x}",
                    "filesize": filesize,
                    "maxprot": maxprot,
                    "initprot": initprot
                })
            offset += cmdsize
        return {
            "format": "Mach-O 64-bit",
            "magic": f"0x{magic:08x}",
            "cputype": f"0x{cputype:x}",
            "cputype_name": "CPU_TYPE_ARM64",
            "cpusubtype": f"0x{cpusubtype:x}",
            "filetype": filetype,
            "ncmds": ncmds,
            "segments": segments
        }
    elif magic == 0xfeedface: # 32-bit
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack('<IIIIIII', data[:28])
        offset = 28
        for _ in range(ncmds):
            cmd, cmdsize = struct.unpack('<II', data[offset:offset+8])
            if cmd == 0x1: # LC_SEGMENT
                segname = data[offset+8:offset+24].rstrip(b'\x00').decode('latin1')
                vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack('<IIIIIIII', data[offset+24:offset+56])
                segments.append({
                    "name": segname,
                    "vmaddr": f"0x{vmaddr:08x}",
                    "vmaddr_int": vmaddr,
                    "vmsize": vmsize,
                    "vmsize_hex": f"0x{vmsize:x}",
                    "fileoff": fileoff,
                    "fileoff_hex": f"0x{fileoff:x}",
                    "filesize": filesize,
                    "maxprot": maxprot,
                    "initprot": initprot
                })
            offset += cmdsize
        return {
            "format": "Mach-O 32-bit",
            "magic": f"0x{magic:08x}",
            "cputype": f"0x{cputype:x}",
            "cputype_name": "CPU_TYPE_ARM",
            "cpusubtype": f"0x{cpusubtype:x}",
            "filetype": filetype,
            "ncmds": ncmds,
            "segments": segments
        }
    else:
        return {"format": "Raw Binary", "magic": f"0x{magic:08x}"}

def parse_rkosftab(payload: bytes):
    # offset 0x20 in payload
    magic = payload[0x20:0x28].decode('latin1')
    if magic != 'rkosftab':
        return None
    count = struct.unpack('<Q', payload[0x28:0x30])[0]
    entries = []
    curr = 0x30
    for _ in range(count):
        tag_b, offset, size, reserved = struct.unpack('<4sIII', payload[curr:curr+16])
        tag = tag_b.decode('latin1')
        entry_payload = payload[offset:offset+size]
        macho_info = parse_macho_segments(entry_payload)
        entries.append({
            "tag": tag,
            "offset": offset,
            "offset_hex": f"0x{offset:x}",
            "size": size,
            "size_hex": f"0x{size:x}",
            "reserved": reserved,
            "sha256": compute_sha256(entry_payload),
            "macho": macho_info
        })
        curr += 16
    return {
        "magic": magic,
        "entry_count": count,
        "entries": entries
    }

def main():
    print("Extracting GPU baseline and container specifications...")

    # 1. Target Firmware Binaries
    fw_targets = [
        {
            "id": "armfw_g18p",
            "rel_path": "iPhone18,3_27.2_24B119_Restore/Firmware/agx/armfw_g18p.im4p",
            "tag": "gfxf",
            "desc": "Graphics Firmware Core 0 (Management, Power, Telemetry & Scheduling)"
        },
        {
            "id": "armfw1_g18p",
            "rel_path": "iPhone18,3_27.2_24B119_Restore/Firmware/agx/armfw1_g18p.im4p",
            "tag": "gf1f",
            "desc": "Graphics Firmware Core 1 (Context Dispatch, Compute & Render Pipelines)"
        },
        {
            "id": "t8150_msrf",
            "rel_path": "iPhone18,3_27.2_24B119_Restore/Firmware/msr/t8150.msrf.im4p",
            "tag": "msrf",
            "desc": "DRAM Memory Subsystem Resource Coprocessor Firmware (Release)"
        },
        {
            "id": "t8150_rmsr",
            "rel_path": "iPhone18,3_27.2_24B119_Restore/Firmware/msr/t8150.rmsr.im4p",
            "tag": "rmsr",
            "desc": "DRAM Memory Subsystem Resource Coprocessor Firmware (Research / Recovery)"
        }
    ]

    im4p_specs = {}
    firmware_inventory = {}

    for t in fw_targets:
        fpath = ROOT / t["rel_path"]
        raw = fpath.read_bytes()
        fsize = len(raw)
        fsha = compute_sha256(raw)
        
        # ASN.1 header: 25 bytes
        asn1_hdr = raw[:25]
        payload = raw[25:]
        psha = compute_sha256(payload)
        
        rkos = None
        macho = None
        if t["tag"] in ["gfxf", "gf1f"]:
            rkos = parse_rkosftab(payload)
        elif t["tag"] in ["msrf", "rmsr"]:
            macho = parse_macho_segments(payload)

        im4p_specs[t["id"]] = {
            "file_path": t["rel_path"],
            "total_size": fsize,
            "sha256": fsha,
            "fourcc_tag": t["tag"],
            "description": t["desc"],
            "header_bytes_hex": asn1_hdr.hex(),
            "payload_offset": 25,
            "payload_size": len(payload),
            "payload_sha256": psha,
            "rkosftab": rkos,
            "macho": macho
        }

        firmware_inventory[t["id"]] = {
            "path": t["rel_path"],
            "size": fsize,
            "sha256": fsha,
            "tag": t["tag"],
            "role": t["desc"],
            "payload_size": len(payload),
            "payload_sha256": psha
        }

    # 2. Kernel Extensions from kext_catalog_release.json
    kext_catalog = json.loads((ROOT / "artifacts/kernel/kext_catalog_release.json").read_text())
    target_kext_ids = [
        "com.apple.AGXG18P",
        "com.apple.AGXFirmwareKextG18PRTBuddy",
        "com.apple.AGXFirmwareKextRTBuddy64",
        "com.apple.iokit.IOGPUFamily"
    ]
    kernel_driver_inventory = {}
    for k in kext_catalog:
        bid = k.get("bundle_id")
        if bid in target_kext_ids:
            kernel_driver_inventory[bid] = {
                "bundle_id": bid,
                "version": k.get("version"),
                "bundle_path": k.get("bundle_path"),
                "dependencies": k.get("dependencies", []),
                "segments": {
                    sname: {
                        "vmaddr": sdata.get("vmaddr"),
                        "vmsize": sdata.get("vmsize"),
                        "fileoff": sdata.get("fileoff_hex"),
                        "filesize": sdata.get("filesize")
                    }
                    for sname, sdata in k.get("segment_map", {}).items()
                }
            }

    # 3. Userland Frameworks from shared_cache_overview.json
    sc_overview = json.loads((ROOT / "artifacts/rootfs/shared_cache_overview.json").read_text())
    target_framework_paths = [
        "/System/Library/Extensions/AGXMetalG18P.bundle/AGXMetalG18P",
        "/System/Library/PrivateFrameworks/IOGPU.framework/IOGPU",
        "/System/Library/PrivateFrameworks/IOAccelerator.framework/IOAccelerator",
        "/System/Library/PrivateFrameworks/AGXCompilerCore.framework/AGXCompilerCore",
        "/System/Library/PrivateFrameworks/AGXGPURawCounter.framework/AGXGPURawCounter",
        "/System/Library/Frameworks/MetalPerformanceShaders.framework/Frameworks/MPSRayIntersector.framework/MPSRayIntersector",
        "/System/Library/Frameworks/Metal.framework/Metal"
    ]
    userland_framework_inventory = {}
    for img in sc_overview.get("all_images", []):
        ipath = img.get("path")
        if ipath in target_framework_paths:
            userland_framework_inventory[ipath] = {
                "index": img.get("index"),
                "address": img.get("address"),
                "address_int": img.get("address_int"),
                "path": ipath,
                "category": img.get("category")
            }

    # 4. Construct Workspace Baseline Artifact
    workspace_baseline = {
        "system_environment": {
            "os_name": "iOS",
            "os_version": "27.2",
            "darwin_version": "24.2.0",
            "build_train": "24B119",
            "target_hardware": "iPhone18,3",
            "device_class": "v57ap",
            "soc": "t8150",
            "soc_marketing": "Apple A19 Pro",
            "gpu_generation": "G18",
            "gpu_variant": "AGX G18P",
            "root_directory": "/home/prem/Projects/iOS 27"
        },
        "anchor_verification": {
            "toolchain_trusted": True,
            "restore_image": "iPhone18,3_27.2_24B119_Restore",
            "kext_catalog_source": "artifacts/kernel/kext_catalog_release.json",
            "shared_cache_source": "artifacts/rootfs/shared_cache_overview.json"
        },
        "firmware_inventory": firmware_inventory,
        "kernel_driver_inventory": kernel_driver_inventory,
        "userland_framework_inventory": userland_framework_inventory
    }

    # 5. Construct Firmware Container Spec Artifact
    container_spec = {
        "container_format": "Apple Image4 Payload (IM4P) ASN.1 Wrapper",
        "asn1_structure": "SEQUENCE { IA5String 'IM4P', IA5String FourCC, IA5String description, OCTET STRING payload }",
        "header_length_bytes": 25,
        "fourcc_catalog": {
            "gfxf": {
                "name": "Graphics Firmware Core 0",
                "subsystem": "AGX G18P Coprocessor Scheduler & Telemetry",
                "binary": "armfw_g18p.im4p",
                "sub_container_magic": "rkosftab",
                "sub_container_entries": 3
            },
            "gf1f": {
                "name": "Graphics Firmware Core 1",
                "subsystem": "AGX G18P Coprocessor Context & Compute Dispatch",
                "binary": "armfw1_g18p.im4p",
                "sub_container_magic": "rkosftab",
                "sub_container_entries": 3
            },
            "msrf": {
                "name": "Memory Subsystem Resource (Release)",
                "subsystem": "DRAM Memory Compression & Fabric Interface",
                "binary": "t8150.msrf.im4p",
                "format": "Mach-O 32-bit (ARMv7k / CPU_SUBTYPE_ARM_V7K)"
            },
            "rmsr": {
                "name": "Memory Subsystem Resource (Research/Recovery)",
                "subsystem": "DRAM Memory Compression & Diagnostics",
                "binary": "t8150.rmsr.im4p",
                "format": "Mach-O 32-bit (ARMv7k / CPU_SUBTYPE_ARM_V7K)"
            }
        },
        "im4p_containers": {
            "armfw_g18p": im4p_specs["armfw_g18p"],
            "armfw1_g18p": im4p_specs["armfw1_g18p"]
        },
        "msr_containers": {
            "t8150_msrf": im4p_specs["t8150_msrf"],
            "t8150_rmsr": im4p_specs["t8150_rmsr"]
        }
    }

    # Write out JSON files
    p1a_path = ROOT / "artifacts/gpu/phase_1a_workspace_baseline.json"
    p1a_path.write_text(json.dumps(workspace_baseline, indent=2))
    print(f"Wrote {p1a_path} ({p1a_path.stat().st_size} bytes)")

    spec_path = ROOT / "artifacts/gpu/agx_firmware_container_spec.json"
    spec_path.write_text(json.dumps(container_spec, indent=2))
    print(f"Wrote {spec_path} ({spec_path.stat().st_size} bytes)")

    # 6. Domain-isolated progress ledger
    gpu_progress = {
        "project": "Apple AGX GPU (Generation G18) Microarchitecture Reverse Engineering",
        "soc": "t8150",
        "device": "iPhone18,3 (v57ap)",
        "version": "27.2",
        "build": "24B119",
        "active_phase_id": "gpu_phase_1a_workspace_baseline",
        "phases": {
            "gpu_phase_1a_workspace_baseline": {
                "title": "Workspace Baseline & Container Spec",
                "status": "completed",
                "required_artifacts": [
                    "artifacts/gpu/phase_1a_workspace_baseline.json",
                    "artifacts/gpu/agx_firmware_container_spec.json",
                    "findings/gpu/01A_WORKSPACE_BASELINE.md"
                ]
            },
            "gpu_phase_1b_microarchitecture": {
                "title": "G18 Microarchitecture & RTBuddy Coprocessor Topology",
                "status": "pending"
            },
            "gpu_phase_2_mmio_and_tile_geometry": {
                "title": "Hardware Register & Memory Geometry",
                "status": "pending"
            },
            "gpu_phase_3_command_stream": {
                "title": "Wire Format, Command Descriptors & Ring Buffer Protocol",
                "status": "pending"
            },
            "gpu_phase_4_kernel_boundary": {
                "title": "Kernel Boundary & Clean-Room Direct Submission Client",
                "status": "pending"
            },
            "gpu_phase_5_synthesis": {
                "title": "Synthesis, Verification Test Suite & Standalone Repository",
                "status": "pending"
            }
        }
    }
    prog_path = ROOT / "artifacts/gpu/progress_gpu.json"
    prog_path.write_text(json.dumps(gpu_progress, indent=2))
    print(f"Wrote {prog_path} ({prog_path.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
