#!/usr/bin/env python3
"""
verify_rtbuddy_firmware.py
Apple AGX G18 RTBuddy Dual-Core Firmware & RTKit Microkernel Verifier
Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)

Strict clean-room verification asserting all container offsets, SHA-256 digests,
rkosftab multi-stepping entries, Mach-O headers, segments, sections, canaries,
shared memory contracts, patchbay TLV records, symbol tables, exception vectors,
crashlog apertures, stepping variations, and specification JSONs directly against disk.
"""

import os
import sys
import struct
import hashlib
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = WORKSPACE_ROOT / "iPhone18,3_27.2_24B119_Restore" / "Firmware" / "agx"
ARTIFACTS_DIR = WORKSPACE_ROOT / "artifacts" / "gpu" / "firmware"

# Master ground truth constants
EXPECTED_CONTAINERS = {
    "armfw_g18p.im4p": {
        "filesize": 3510409,
        "sha256": "2c3d3d88483a05264f8163ea12d6139deea760d0ef4993f6c0207cf0f2eb1e6e",
        "fourcc": "gfxf",
        "payload_offset": 25,
        "payload_size": 3510384,
        "payload_sha256": "80bc203d95ec9da7b619b827fc768194f73d2f89f293d20c57c2e9e3d3a39f89",
        "steppings": {
            "a000": {"offset": 0x60, "size": 1170096, "sha256": "669a5c2acc07c9680a7425933c6e4ae8fca16287625945540a5faace098e6107"},
            "b000": {"offset": 0x11db10, "size": 1170096, "sha256": "3a37fd8aca5e5b6c9b30f1b9c2d8d7f39a9c025a19f20c3df7893ea5506e4554"},
            "a010": {"offset": 0x23b5c0, "size": 1170096, "sha256": "165c6b185f7a3d27c6cfedb20639fa1a38da7fa3959f99cde66d4e4c11e2734f"}
        }
    },
    "armfw1_g18p.im4p": {
        "filesize": 3313873,
        "sha256": "22b7c5dbfcfe818af2aa96ef6c58dd2ca3ea056835db80892bc0a7a61bd74645",
        "fourcc": "gf1f",
        "payload_offset": 25,
        "payload_size": 3313848,
        "payload_sha256": "e87f1ae96bdc6ba7729f0843842700b403fc11c8aed5b3b97103e786a1f2a4a6",
        "steppings": {
            "a000": {"offset": 0x60, "size": 1104584, "sha256": "f08c92e3da689c5b60d9ed8d5e84588439116ef846898566277ab0ef946452b7"},
            "b000": {"offset": 0x10db28, "size": 1104584, "sha256": "512160b0a0daecd59bec0c265bea57ed5c81e92c590e30ed2bb7841bbaba3ee6"},
            "a010": {"offset": 0x21b5f0, "size": 1104584, "sha256": "b16b710bca604f22b8a92cc610e903e19a58455c824796dbc27e2789e758e8c4"}
        }
    }
}

EXPECTED_SECTIONS_A000_CORE0 = {
    "__TEXT.__text": {"addr": 0xfffffc0000000000, "size": 0x3d008, "fileoff": 0x4000},
    "__TEXT.__gxf_code": {"addr": 0xfffffc0000040000, "size": 0x5120, "fileoff": 0x44000},
    "__TEXT.__gxf_shr_code": {"addr": 0xfffffc0000048000, "size": 0x560, "fileoff": 0x4c000},
    "__TEXT.__const": {"addr": 0xfffffc0000048560, "size": 0x10ad, "fileoff": 0x4c560},
    "__TEXT._rtk_tunables": {"addr": 0xfffffc000004960d, "size": 0x740, "fileoff": 0x4d60d},
    "__TEXT._rtk_patchbay": {"addr": 0xfffffc0000049d4d, "size": 0x231, "fileoff": 0x4dd4d},
    "__TEXT.__cstring": {"addr": 0xfffffc0000049f7e, "size": 0x2346, "fileoff": 0x4df7e},
    "__DATA.__gxf_data": {"addr": 0xfffffc0000050000, "size": 0x8160, "fileoff": 0x54000},
    "__DATA._rtk_init_stack": {"addr": 0xfffffc0000073d30, "size": 0x4000, "fileoff": 0x77d30},
    "__DATA._rtk_irq_stack": {"addr": 0xfffffc00000784e0, "size": 0x4000, "fileoff": 0x7c4e0},
    "__DATA._rtk_exc_stack": {"addr": 0xfffffc000007c4e0, "size": 0x4000, "fileoff": 0x804e0},
    "__DATA._rtk_boot_l1": {"addr": 0xfffffc00000804e0, "size": 0x200, "fileoff": 0x844e0},
    "__DATA._rtk_boot": {"addr": 0xfffffc0000084000, "size": 0xc000, "fileoff": 0x88000},
    "__DATA._rtk_mtab": {"addr": 0xfffffc0000090000, "size": 0x390, "fileoff": 0x94000},
    "__DATA._rtk_power": {"addr": 0xfffffc0000090390, "size": 0x398, "fileoff": 0x94390},
    "__DATA._rtk_page_tables": {"addr": 0xfffffc0000094000, "size": 0x20000, "fileoff": 0x98000},
    "__DATA.__zerofill": {"addr": 0xfffffc00000b4040, "size": 0x5a778, "fileoff": 0xb8040},
    "__DATA_SHARED_RO._RTK_EXT_SHD_DTA": {"addr": 0xfffffc0000110000, "size": 0x8000, "fileoff": 0x114000}
}

EXPECTED_SECTIONS_A000_CORE1 = {
    "__TEXT.__text": {"addr": 0xfffffc0000000000, "size": 0x3d99c, "fileoff": 0x4000},
    "__TEXT.__gxf_code": {"addr": 0xfffffc0000040000, "size": 0x5120, "fileoff": 0x44000},
    "__TEXT.__gxf_shr_code": {"addr": 0xfffffc0000048000, "size": 0x560, "fileoff": 0x4c000},
    "__TEXT.__const": {"addr": 0xfffffc0000048560, "size": 0xac5, "fileoff": 0x4c560},
    "__TEXT._rtk_tunables": {"addr": 0xfffffc0000049025, "size": 0x740, "fileoff": 0x4d025},
    "__TEXT._rtk_patchbay": {"addr": 0xfffffc0000049765, "size": 0x231, "fileoff": 0x4d765},
    "__TEXT.__cstring": {"addr": 0xfffffc0000049996, "size": 0x239d, "fileoff": 0x4d996},
    "__DATA.__gxf_data": {"addr": 0xfffffc000004c000, "size": 0x8160, "fileoff": 0x50000},
    "__DATA._rtk_init_stack": {"addr": 0xfffffc000006fd30, "size": 0x4000, "fileoff": 0x73d30},
    "__DATA._rtk_irq_stack": {"addr": 0xfffffc00000745c0, "size": 0x4000, "fileoff": 0x785c0},
    "__DATA._rtk_exc_stack": {"addr": 0xfffffc00000785c0, "size": 0x4000, "fileoff": 0x7c5c0},
    "__DATA._rtk_boot_l1": {"addr": 0xfffffc000007c5c0, "size": 0x200, "fileoff": 0x805c0},
    "__DATA._rtk_boot": {"addr": 0xfffffc0000080000, "size": 0xc000, "fileoff": 0x84000},
    "__DATA._rtk_mtab": {"addr": 0xfffffc000008c000, "size": 0x390, "fileoff": 0x90000},
    "__DATA._rtk_power": {"addr": 0xfffffc000008c390, "size": 0x398, "fileoff": 0x90390},
    "__DATA._rtk_page_tables": {"addr": 0xfffffc0000090000, "size": 0x20000, "fileoff": 0x94000},
    "__DATA.__zerofill": {"addr": 0xfffffc00000b0080, "size": 0x4f6b8, "fileoff": 0xb4080},
    "__DATA_SHARED_RO._RTK_EXT_SHD_DTA": {"addr": 0xfffffc0000100000, "size": 0x8000, "fileoff": 0x104000}
}

EXPECTED_CORE0_SYMBOLS = {
    "new_rtk_start_anywhere_uatv2": 0xfffffc0000000000,
    "__rtk_arch_vectors": 0xfffffc0000002000,
    "__rtk_arch_gxf_vectors": 0xfffffc0000001800,
    "__rtk_arch_gxf_vector_abort": 0xfffffc0000001a00,
    "__rtk_arch_fast_interrupt": 0xfffffc000002b664,
    "__rtk_arch_interrupt": 0xfffffc000002b608,
    "__rtk_arch_exception": 0xfffffc000002c5a8,
    "__rtk_arch_svc_handler": 0xfffffc000002b688,
    "__nmi_frame": 0xfffffc000010e5e8,
    "_gCrashLog": 0xfffffc0000110000,
    "__rtk_crashlog_is_local": 0xfffffc00000730f0,
    "__rtk_crashlog_requested_size": 0xfffffc00000730e0,
    "___stack_chk_guard": 0xfffffc000005c000,
    "_SH_DATA_SEGS": 0xfffffc0000000244
}

EXPECTED_CORE1_SYMBOLS = {
    "new_rtk_start_anywhere_uatv2": 0xfffffc0000000000,
    "__rtk_arch_vectors": 0xfffffc0000002000,
    "__rtk_arch_gxf_vectors": 0xfffffc0000001800,
    "__rtk_arch_gxf_vector_abort": 0xfffffc0000001a00,
    "__rtk_arch_fast_interrupt": 0xfffffc000002b9cc,
    "__rtk_arch_interrupt": 0xfffffc000002b970,
    "__rtk_arch_exception": 0xfffffc000002c910,
    "__rtk_arch_svc_handler": 0xfffffc000002b9f0,
    "__nmi_frame": 0xfffffc00000ff568,
    "_gCrashLog": 0xfffffc0000100000,
    "__rtk_crashlog_is_local": 0xfffffc000006f0f0,
    "__rtk_crashlog_requested_size": 0xfffffc000006f0e0,
    "___stack_chk_guard": 0xfffffc0000058000,
    "_SH_DATA_SEGS": 0xfffffc0000000244,
    "___powisf2": 0xfffffc0000002f84
}

class VerificationTracker:
    def __init__(self):
        self.passes = 0
        self.failures = 0

    def assert_true(self, condition, message):
        if condition:
            self.passes += 1
            print(f"  [PASS] {message}")
        else:
            self.failures += 1
            print(f"  [FAIL] {message}")

def parse_macho_sections(macho_bytes):
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", macho_bytes[:32])
    assert magic == 0xfeedfacf
    offset = 32
    sections = {}
    for i in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", macho_bytes[offset : offset + 8])
        if cmd == 0x19: # LC_SEGMENT_64
            nsects = struct.unpack("<I", macho_bytes[offset + 64 : offset + 68])[0]
            sec_off = offset + 72
            for s in range(nsects):
                sectname_b, s_segname_b, s_addr, s_size, s_offset = struct.unpack("<16s16sQQI", macho_bytes[sec_off : sec_off + 52])
                sectname = sectname_b.decode("ascii", errors="ignore").rstrip("\x00")
                s_segname = s_segname_b.decode("ascii", errors="ignore").rstrip("\x00")
                key = f"{s_segname}.{sectname}"
                sections[key] = {"addr": s_addr, "size": s_size, "fileoff": s_offset}
                sec_off += 80
        offset += cmdsize
    return sections

def parse_macho_symbols(macho_bytes):
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", macho_bytes[:32])
    assert magic == 0xfeedfacf
    offset = 32
    syms = {}
    for i in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", macho_bytes[offset : offset + 8])
        if cmd == 0x2: # LC_SYMTAB
            symoff, nsyms, stroff, strsize = struct.unpack("<IIII", macho_bytes[offset + 8 : offset + 24])
            strtab = macho_bytes[stroff : stroff + strsize]
            for s in range(nsyms):
                n_strx, n_type, n_sect, n_desc, n_value = struct.unpack("<IBBhQ", macho_bytes[symoff + s * 16 : symoff + (s + 1) * 16])
                sym_name = strtab[n_strx:].split(b"\x00")[0].decode("ascii", errors="ignore")
                syms[sym_name] = {
                    "value": n_value,
                    "sect": n_sect,
                    "type": n_type,
                    "desc": n_desc
                }
            break
        offset += cmdsize
    return syms

def parse_patchbay_tlv(patchbay_bytes):
    off = 0
    records = []
    while off < len(patchbay_bytes):
        tag = patchbay_bytes[off : off + 4]
        tag_str = tag.decode("ascii", errors="ignore")
        length = struct.unpack("<I", patchbay_bytes[off + 4 : off + 8])[0]
        val_bytes = patchbay_bytes[off + 8 : off + 8 + length]
        val_int = int.from_bytes(val_bytes, "little")
        records.append({
            "offset": off,
            "tag": tag_str,
            "tag_ascii": tag_str[::-1],
            "length": length,
            "val_bytes": val_bytes,
            "val_int": val_int
        })
        off += 8 + length
    return records

def main():
    tracker = VerificationTracker()
    print("=" * 80)
    print("RTBuddy Firmware Verification Suite (Clean-Room Assertions)")
    print("=" * 80)

    # 1. Container Verification
    print("\n--- 1. Image4 (IM4P) Container Integrity ---")
    for filename, meta in EXPECTED_CONTAINERS.items():
        container_path = INPUT_DIR / filename
        tracker.assert_true(container_path.exists(), f"Container exists: {filename}")
        with open(container_path, "rb") as f:
            cdata = f.read()
        tracker.assert_true(len(cdata) == meta["filesize"], f"{filename} file size == {meta['filesize']:,} bytes")
        c_hash = hashlib.sha256(cdata).hexdigest()
        tracker.assert_true(c_hash == meta["sha256"], f"{filename} SHA-256 match: {c_hash}")

        # Header tags
        fourcc = cdata[13:17].decode("ascii")
        tracker.assert_true(fourcc == meta["fourcc"], f"{filename} FourCC '{fourcc}' == '{meta['fourcc']}'")

        payload = cdata[meta["payload_offset"] : meta["payload_offset"] + meta["payload_size"]]
        tracker.assert_true(len(payload) == meta["payload_size"], f"{filename} payload size == {meta['payload_size']:,} bytes")
        p_hash = hashlib.sha256(payload).hexdigest()
        tracker.assert_true(p_hash == meta["payload_sha256"], f"{filename} payload SHA-256 match")

    # 2. rkosftab Multi-Stepping Table Verification
    print("\n--- 2. rkosftab Multi-Stepping Table Geometry ---")
    for filename, meta in EXPECTED_CONTAINERS.items():
        with open(INPUT_DIR / filename, "rb") as f:
            cdata = f.read()
        payload = cdata[meta["payload_offset"]:]

        tab_magic = cdata[0x39:0x41]
        tracker.assert_true(tab_magic == b"rkosftab", f"{filename} rkosftab magic at 0x39")
        entry_cnt = struct.unpack("<Q", cdata[0x41:0x49])[0]
        tracker.assert_true(entry_cnt == 3, f"{filename} rkosftab entry count == 3")

        for idx, (tag, smeta) in enumerate(meta["steppings"].items()):
            eoff = 0x49 + idx * 16
            t_tag, p_off, p_sz, res = struct.unpack("<4sIII", cdata[eoff:eoff+16])
            tracker.assert_true(t_tag.decode("ascii") == tag, f"{filename} entry {idx} tag '{tag}'")
            tracker.assert_true(p_off == smeta["offset"], f"{filename} entry {idx} offset 0x{p_off:x} == 0x{smeta['offset']:x}")
            tracker.assert_true(p_sz == smeta["size"], f"{filename} entry {idx} size {p_sz:,} == {smeta['size']:,}")

            macho_blob = payload[p_off : p_off + p_sz]
            m_hash = hashlib.sha256(macho_blob).hexdigest()
            tracker.assert_true(m_hash == smeta["sha256"], f"{filename} stepping '{tag}' SHA-256 match: {m_hash[:16]}...")

    # 3. Extracted Mach-O Artifacts Verification
    print("\n--- 3. Extracted Mach-O Binaries & 64-bit Header Dissection ---")
    for filename, meta in EXPECTED_CONTAINERS.items():
        prefix = "armfw_g18p" if meta["fourcc"] == "gfxf" else "armfw1_g18p"
        for tag, smeta in meta["steppings"].items():
            extracted_path = ARTIFACTS_DIR / f"{prefix}_{tag}.macho"
            tracker.assert_true(extracted_path.exists(), f"Extracted file exists: {extracted_path.name}")
            with open(extracted_path, "rb") as f:
                mdata = f.read()
            tracker.assert_true(len(mdata) == smeta["size"], f"{extracted_path.name} size {len(mdata):,} == {smeta['size']:,}")
            tracker.assert_true(hashlib.sha256(mdata).hexdigest() == smeta["sha256"], f"{extracted_path.name} SHA-256 verified")

            # Mach-O Header Fields
            magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", mdata[:32])
            tracker.assert_true(magic == 0xfeedfacf, f"{extracted_path.name} MH_MAGIC_64 (0xfeedfacf)")
            tracker.assert_true(cputype == 0x100000c, f"{extracted_path.name} CPU_TYPE_ARM64 (0x100000c)")
            tracker.assert_true(cpusubtype == 0x80000002, f"{extracted_path.name} CPU_SUBTYPE_ARM64E_PAC00 (0x80000002)")
            tracker.assert_true(filetype == 5, f"{extracted_path.name} MH_PRELOAD (5)")
            tracker.assert_true(ncmds == 8, f"{extracted_path.name} ncmds == 8")
            tracker.assert_true(sizeofcmds == 2944, f"{extracted_path.name} sizeofcmds == 2944")

            # LC_UNIXTHREAD PC entrypoint
            offset = 32
            pc_val = None
            for _ in range(ncmds):
                cmd, cmdsize = struct.unpack("<II", mdata[offset:offset+8])
                if cmd == 0x5: # LC_UNIXTHREAD
                    regs = struct.unpack("<34Q", mdata[offset+16 : offset+16+34*8])
                    pc_val = regs[32]
                    break
                offset += cmdsize
            tracker.assert_true(pc_val == 0xfffffc0000000000, f"{extracted_path.name} entrypoint PC == 0xfffffc0000000000")

    # 4. Core 0 vs Core 1 Exact Section Mapping (a000 stepping)
    print("\n--- 4. Memory Layout & Section Verification (a000 Stepping) ---")
    with open(ARTIFACTS_DIR / "armfw_g18p_a000.macho", "rb") as f:
        core0_sects = parse_macho_sections(f.read())
    for sname, expected in EXPECTED_SECTIONS_A000_CORE0.items():
        tracker.assert_true(sname in core0_sects, f"Core 0 section present: {sname}")
        if sname in core0_sects:
            actual = core0_sects[sname]
            tracker.assert_true(actual["addr"] == expected["addr"], f"Core 0 {sname} addr 0x{actual['addr']:x} == 0x{expected['addr']:x}")
            tracker.assert_true(actual["size"] == expected["size"], f"Core 0 {sname} size 0x{actual['size']:x} == 0x{expected['size']:x}")
            tracker.assert_true(actual["fileoff"] == expected["fileoff"], f"Core 0 {sname} fileoff 0x{actual['fileoff']:x} == 0x{expected['fileoff']:x}")

    with open(ARTIFACTS_DIR / "armfw1_g18p_a000.macho", "rb") as f:
        core1_sects = parse_macho_sections(f.read())
    for sname, expected in EXPECTED_SECTIONS_A000_CORE1.items():
        tracker.assert_true(sname in core1_sects, f"Core 1 section present: {sname}")
        if sname in core1_sects:
            actual = core1_sects[sname]
            tracker.assert_true(actual["addr"] == expected["addr"], f"Core 1 {sname} addr 0x{actual['addr']:x} == 0x{expected['addr']:x}")
            tracker.assert_true(actual["size"] == expected["size"], f"Core 1 {sname} size 0x{actual['size']:x} == 0x{expected['size']:x}")
            tracker.assert_true(actual["fileoff"] == expected["fileoff"], f"Core 1 {sname} fileoff 0x{actual['fileoff']:x} == 0x{expected['fileoff']:x}")

    # 5. Stepping Variations (b000 and a010)
    print("\n--- 5. Stepping Variations (b000 & a010) ---")
    with open(ARTIFACTS_DIR / "armfw_g18p_b000.macho", "rb") as f:
        c0_b000_sects = parse_macho_sections(f.read())
    tracker.assert_true(c0_b000_sects["__TEXT.__text"]["size"] == 0x3cc68, "Core 0 b000 __text size == 0x3cc68 (248,936 B)")
    tracker.assert_true(c0_b000_sects["__TEXT.__cstring"]["size"] == 0x23fc, "Core 0 b000 __cstring size == 0x23fc (9,212 B)")

    with open(ARTIFACTS_DIR / "armfw1_g18p_b000.macho", "rb") as f:
        c1_b000_sects = parse_macho_sections(f.read())
    tracker.assert_true(c1_b000_sects["__TEXT.__text"]["size"] == 0x3d954, "Core 1 b000 __text size == 0x3d954 (252,244 B)")
    tracker.assert_true(c1_b000_sects["__TEXT.__cstring"]["size"] == 0x239d, "Core 1 b000 __cstring size == 0x239d (9,117 B)")

    # 6. Shared Memory Wire Contract & _SH_DATA_SEGS
    print("\n--- 6. Inter-Core Shared Memory & _SH_DATA_SEGS Wire Contract ---")
    with open(ARTIFACTS_DIR / "armfw_g18p_a000.macho", "rb") as f:
        m0 = f.read()
    with open(ARTIFACTS_DIR / "armfw1_g18p_a000.macho", "rb") as f:
        m1 = f.read()

    w0 = struct.unpack("<8Q", m0[0x4244 : 0x4244 + 64])
    w1 = struct.unpack("<8Q", m1[0x4244 : 0x4244 + 64])

    tracker.assert_true((w0[0] & 0xffffffff) == 0x67657364, "Core 0 _SH_DATA_SEGS magic == 'dseg'")
    tracker.assert_true((w1[0] & 0xffffffff) == 0x67657364, "Core 1 _SH_DATA_SEGS magic == 'dseg'")
    tracker.assert_true((w0[0] >> 32) == 1, "Core 0 _SH_DATA_SEGS version == 1")
    tracker.assert_true((w1[0] >> 32) == 1, "Core 1 _SH_DATA_SEGS version == 1")
    tracker.assert_true(w0[2] == 0xc0000, "Core 0 _SH_DATA_SEGS offset == 0xc0000")
    tracker.assert_true(w1[2] == 0xb4000, "Core 1 _SH_DATA_SEGS offset == 0xb4000")
    tracker.assert_true(w0[3] == 0xfffffc0000110000, "Core 0 _SH_DATA_SEGS target VA == 0xfffffc0000110000")
    tracker.assert_true(w1[3] == 0xfffffc0000100000, "Core 1 _SH_DATA_SEGS target VA == 0xfffffc0000100000")
    tracker.assert_true(w0[4] == 0x8000, "Core 0 _SH_DATA_SEGS length == 32 KB (0x8000)")
    tracker.assert_true(w1[4] == 0x8000, "Core 1 _SH_DATA_SEGS length == 32 KB (0x8000)")

    # 7. RTKit Version String Assertions
    print("\n--- 7. RTKit OS Version Strings ---")
    v0 = m0[0x4d5d8 : 0x4d5d8 + 80].split(b"\x00")[0].decode("ascii")
    v1 = m1[0x4cff0 : 0x4cff0 + 80].split(b"\x00")[0].decode("ascii")
    expected_v = "RTKit_armv8_lightning_Oz_flto_pac-3514.40.18.release"
    tracker.assert_true(v0 == expected_v, f"Core 0 RTKit version match: {v0}")
    tracker.assert_true(v1 == expected_v, f"Core 1 RTKit version match: {v1}")

    # 8. Boot Patchbay 39 TLV Geometry & Canaries
    print("\n--- 8. Boot Patchbay 39 TLV Records & Values ---")
    pb0_data = m0[0x4dd4d : 0x4dd4d + 0x231]
    pb1_data = m1[0x4d765 : 0x4d765 + 0x231]
    tracker.assert_true(len(pb0_data) == 561, f"Core 0 patchbay size 561 == {len(pb0_data)}")
    tracker.assert_true(len(pb1_data) == 561, f"Core 1 patchbay size 561 == {len(pb1_data)}")

    pb0_records = parse_patchbay_tlv(pb0_data)
    pb1_records = parse_patchbay_tlv(pb1_data)
    tracker.assert_true(len(pb0_records) == 39, f"Core 0 patchbay record count 39 == {len(pb0_records)}")
    tracker.assert_true(len(pb1_records) == 39, f"Core 1 patchbay record count 39 == {len(pb1_records)}")

    # Map tags to values
    r0_map = {r["tag_ascii"]: r for r in pb0_records}
    r1_map = {r["tag_ascii"]: r for r in pb1_records}

    # Canary & geometry checks
    tracker.assert_true(r0_map["STKG"]["val_int"] == 0xaff, "Core 0 STKG (Stack Guard) == 0xaff")
    tracker.assert_true(r1_map["STKG"]["val_int"] == 0xaff, "Core 1 STKG (Stack Guard) == 0xaff")
    tracker.assert_true(r0_map["GxPB"]["val_int"] == 0x488000000, "Core 0 GxPB (GXF Base Physical) == 0x488000000")
    tracker.assert_true(r0_map["GxPS"]["val_int"] == 0x4000000, "Core 0 GxPS (GXF Physical Size) == 64 MB (0x4000000)")
    tracker.assert_true(r0_map["SLID"]["val_int"] == 0x14000, "Core 0 SLID (ASLR Slide) == 0x14000")
    tracker.assert_true(r0_map["CSSS"]["val_int"] == 0x4c2c4, "Core 0 CSSS (Chained Starts) == 0x4c2c4")
    tracker.assert_true(r1_map["CSSS"]["val_int"] == 0x4bd34, "Core 1 CSSS (Chained Starts) == 0x4bd34")
    tracker.assert_true(r0_map["RTSZ"]["val_int"] == 0x110000, "Core 0 RTSZ (Runtime Size) == 0x110000")
    tracker.assert_true(r1_map["RTSZ"]["val_int"] == 0x100000, "Core 1 RTSZ (Runtime Size) == 0x100000")
    tracker.assert_true(r0_map["T1Ps"]["val_int"] == 0x2000000000, "Core 0 T1Ps (TTBR1 Size) == 128 GB (0x2000000000)")
    tracker.assert_true(r0_map["GptS"]["val_int"] == 0x4000, "Core 0 GptS (GPTBAT Size) == 16 KB (0x4000)")
    tracker.assert_true(r0_map["TUNS"]["val_int"] == 0xfffffc000004960d, "Core 0 TUNS (Tunables Start) == 0xfffffc000004960d")
    tracker.assert_true(r1_map["TUNS"]["val_int"] == 0xfffffc0000049025, "Core 1 TUNS (Tunables Start) == 0xfffffc0000049025")
    tracker.assert_true(r0_map["TUNZ"]["val_int"] == 0x740, "Core 0 TUNZ (Tunables Size) == 0x740")
    tracker.assert_true(r1_map["TUNZ"]["val_int"] == 0x740, "Core 1 TUNZ (Tunables Size) == 0x740")
    tracker.assert_true(r0_map["SOC_"]["val_int"] == 0xffffffff, "Core 0 SOC_ (Target SoC Mask) == 0xffffffff")
    tracker.assert_true(r0_map["SOCR"]["val_int"] == 0xffffffff, "Core 0 SOCR (Target SoC Revision Mask) == 0xffffffff")
    tracker.assert_true(r0_map["pFLG"]["val_int"] == 0x2, "Core 0 pFLG (Platform Flags) == 0x2")
    tracker.assert_true(r0_map["RTLL"]["val_int"] == 0x1, "Core 0 RTLL (Lock Legacy) == 0x1")
    tracker.assert_true(r0_map["McRA"]["val_int"] == 0x4000, "Core 0 McRA (MC Remote Alignment) == 16 KB (0x4000)")

    # 9. Symbol Table Dissection & Exception Vector Assertions
    print("\n--- 9. Microkernel Symbol Tables & Exception Vector Assertions ---")
    c0_syms = parse_macho_symbols(m0)
    c1_syms = parse_macho_symbols(m1)

    tracker.assert_true(len(c0_syms) == 172, f"Core 0 symbol count == 172 (found {len(c0_syms)})")
    tracker.assert_true(len(c1_syms) == 173, f"Core 1 symbol count == 173 (found {len(c1_syms)})")
    tracker.assert_true("___powisf2" in c1_syms, "Core 1 contains unique symbol '___powisf2'")

    for sname, expected_addr in EXPECTED_CORE0_SYMBOLS.items():
        tracker.assert_true(sname in c0_syms, f"Core 0 symbol present: {sname}")
        if sname in c0_syms:
            actual_addr = c0_syms[sname]["value"]
            tracker.assert_true(actual_addr == expected_addr, f"Core 0 {sname} addr 0x{actual_addr:016x} == 0x{expected_addr:016x}")

    for sname, expected_addr in EXPECTED_CORE1_SYMBOLS.items():
        tracker.assert_true(sname in c1_syms, f"Core 1 symbol present: {sname}")
        if sname in c1_syms:
            actual_addr = c1_syms[sname]["value"]
            tracker.assert_true(actual_addr == expected_addr, f"Core 1 {sname} addr 0x{actual_addr:016x} == 0x{expected_addr:016x}")

    # 10. Hardware Stepping 38-Byte Difference Assertions
    print("\n--- 10. Hardware Stepping 38-Byte Difference Assertions ---")
    with open(ARTIFACTS_DIR / "armfw_g18p_b000.macho", "rb") as f:
        c0_b000_raw = f.read()
    with open(ARTIFACTS_DIR / "armfw_g18p_a010.macho", "rb") as f:
        c0_a010_raw = f.read()
    with open(ARTIFACTS_DIR / "armfw1_g18p_b000.macho", "rb") as f:
        c1_b000_raw = f.read()
    with open(ARTIFACTS_DIR / "armfw1_g18p_a010.macho", "rb") as f:
        c1_a010_raw = f.read()

    diffs_c0 = [i for i in range(len(c0_b000_raw)) if c0_b000_raw[i] != c0_a010_raw[i]]
    diffs_c1 = [i for i in range(len(c1_b000_raw)) if c1_b000_raw[i] != c1_a010_raw[i]]
    tracker.assert_true(len(diffs_c0) == 38, f"Core 0 b000 vs a010 byte diff count == 38 (found {len(diffs_c0)})")
    tracker.assert_true(len(diffs_c1) == 38, f"Core 1 b000 vs a010 byte diff count == 38 (found {len(diffs_c1)})")

    # Variant target check
    var_c0_b = c0_b000_raw[0x4ece6 : 0x4ece6 + 4].decode("ascii")
    var_c0_a = c0_a010_raw[0x4ece6 : 0x4ece6 + 4].decode("ascii")
    tracker.assert_true(var_c0_b == "g18p" and var_c0_a == "g18a", f"Core 0 variant string diff: b000 '{var_c0_b}' vs a010 '{var_c0_a}'")

    var_c1_b = c1_b000_raw[0x4e2bc : 0x4e2bc + 4].decode("ascii")
    var_c1_a = c1_a010_raw[0x4e2bc : 0x4e2bc + 4].decode("ascii")
    tracker.assert_true(var_c1_b == "g18p" and var_c1_a == "g18a", f"Core 1 variant string diff: b000 '{var_c1_b}' vs a010 '{var_c1_a}'")

    ver_c0_b = c0_b000_raw[0x4ecff : 0x4ecff + 2].decode("ascii")
    ver_c0_a = c0_a010_raw[0x4ecff : 0x4ecff + 2].decode("ascii")
    tracker.assert_true(ver_c0_b == "b0" and ver_c0_a == "a0", f"Core 0 build version diff: b000 '{ver_c0_b}' vs a010 '{ver_c0_a}'")

    # 11. Generated JSON Specifications Validation
    print("\n--- 11. Generated Specification JSONs Integrity ---")
    for jname in ["rtbuddy_macho_manifest.json", "rtbuddy_core_partition_spec.json", "rtbuddy_shared_memory_spec.json"]:
        jpath = ARTIFACTS_DIR / jname
        tracker.assert_true(jpath.exists(), f"JSON spec exists: {jname}")
        with open(jpath) as f_json:
            parsed = json.load(f_json)
        tracker.assert_true(len(parsed) > 0, f"JSON spec valid and non-empty: {jname}")

    # Semantic checks inside rtbuddy_shared_memory_spec.json
    with open(ARTIFACTS_DIR / "rtbuddy_shared_memory_spec.json") as f:
        sh_spec = json.load(f)
    handlers = {h["name"]: h for h in sh_spec["stacks_and_exception_handling"]["exception_vector_tables"]["handlers"]}
    tracker.assert_true(handlers["__rtk_arch_fast_interrupt"]["core_0_addr"] == "0xfffffc000002b664", "Spec Core 0 __rtk_arch_fast_interrupt == 0xfffffc000002b664")
    tracker.assert_true(handlers["__rtk_arch_fast_interrupt"]["core_1_addr"] == "0xfffffc000002b9cc", "Spec Core 1 __rtk_arch_fast_interrupt == 0xfffffc000002b9cc")
    tracker.assert_true(handlers["__rtk_arch_interrupt"]["core_0_addr"] == "0xfffffc000002b608", "Spec Core 0 __rtk_arch_interrupt == 0xfffffc000002b608")
    tracker.assert_true(handlers["__rtk_arch_interrupt"]["core_1_addr"] == "0xfffffc000002b970", "Spec Core 1 __rtk_arch_interrupt == 0xfffffc000002b970")
    tracker.assert_true(handlers["__rtk_arch_exception"]["core_0_addr"] == "0xfffffc000002c5a8", "Spec Core 0 __rtk_arch_exception == 0xfffffc000002c5a8")
    tracker.assert_true(handlers["__rtk_arch_exception"]["core_1_addr"] == "0xfffffc000002c910", "Spec Core 1 __rtk_arch_exception == 0xfffffc000002c910")
    tracker.assert_true(handlers["__rtk_arch_svc_handler"]["core_0_addr"] == "0xfffffc000002b688", "Spec Core 0 __rtk_arch_svc_handler == 0xfffffc000002b688")
    tracker.assert_true(handlers["__rtk_arch_svc_handler"]["core_1_addr"] == "0xfffffc000002b9f0", "Spec Core 1 __rtk_arch_svc_handler == 0xfffffc000002b9f0")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {tracker.passes} passed, {tracker.failures} failed")
    print("=" * 80)
    if tracker.failures > 0:
        sys.exit(1)
    else:
        print("[SUCCESS] 100% GREEN PASS. All RTBuddy firmware assertions verified against disk.")
        sys.exit(0)

if __name__ == "__main__":
    main()
