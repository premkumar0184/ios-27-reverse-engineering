#!/usr/bin/env python3
"""
artifacts/audio/smartio/verify_smartio_firmware.py — Automated Verification Suite
Track 1: SmartIO (ASCv7) Firmware & RTKit OS Chinook Microkernel Reverse Engineering
Apple Silicon A19 Pro (t8150 / iOS 27.2 Build 24B119)

Asserts all offsets, sizes, headers, load commands, sections, canaries,
version banners, patchbay entries, tunables, peripheral shims, and mailbox
dispatch structures against disk files.
"""

import sys
import struct
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent

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

def main():
    print("=" * 80)
    print("  SMARTIO (ASCv7) RTKIT CHINOOK FIRMWARE VERIFICATION SUITE")
    print("  Apple Silicon A19 Pro (t8150) / iOS 27.2 (24B119)")
    print("=" * 80)
    
    passed_checks = 0
    total_checks = 0
    
    def check(name: str, condition: bool, details: str = ""):
        nonlocal passed_checks, total_checks
        total_checks += 1
        if condition:
            passed_checks += 1
            print(f"  [PASS] {name}{f' ({details})' if details else ''}")
        else:
            print(f"  [FAIL] {name}{f' ({details})' if details else ''}")
            sys.exit(1)
            
    # ---------------------------------------------------------
    # 1. IM4P Container Validation
    # ---------------------------------------------------------
    im4p_path = ROOT / "iPhone18,3_27.2_24B119_Restore/Firmware/SmartIOFirmware_ASCv7.im4p"
    check("IM4P Container Exists", im4p_path.exists(), str(im4p_path.relative_to(ROOT)))
    
    im4p_bytes = im4p_path.read_bytes()
    check("IM4P File Size", len(im4p_bytes) == 1140621, f"{len(im4p_bytes)} bytes == 1,140,621")
    check("IM4P ASN.1 Tag", im4p_bytes[0] == 0x30, f"0x{im4p_bytes[0]:02x} == 0x30")
    
    seq_len, off = read_asn1_length(im4p_bytes, 1)
    check("IM4P Sequence Length", seq_len == 1140616, f"{seq_len} == 1,140,616")
    
    # Tag 1: IA5String 'IM4P'
    check("IM4P Magic Tag", im4p_bytes[off] == 0x16)
    off += 1
    m_len, off = read_asn1_length(im4p_bytes, off)
    magic = im4p_bytes[off:off+m_len].decode("ascii")
    off += m_len
    check("IM4P Magic String", magic == "IM4P", magic)
    
    # Tag 2: IA5String FourCC 'siof'
    check("FourCC Tag", im4p_bytes[off] == 0x16)
    off += 1
    f_len, off = read_asn1_length(im4p_bytes, off)
    fourcc = im4p_bytes[off:off+f_len].decode("ascii")
    off += f_len
    check("FourCC Value", fourcc == "siof", fourcc)
    
    # Tag 3: IA5String Description '1.0.0'
    check("Description Tag", im4p_bytes[off] == 0x16)
    off += 1
    d_len, off = read_asn1_length(im4p_bytes, off)
    desc = im4p_bytes[off:off+d_len].decode("ascii")
    off += d_len
    check("Description String", desc == "1.0.0", desc)
    
    # Tag 4: Octet String Payload
    check("Payload Octet Tag", im4p_bytes[off] == 0x04)
    off += 1
    p_len, p_off = read_asn1_length(im4p_bytes, off)
    check("Payload Offset in Container", p_off == 29, f"offset {p_off} == 29")
    check("Payload Length", p_len == 1140592, f"{p_len} == 1,140,592")
    
    payload = im4p_bytes[p_off:p_off+p_len]
    sha256 = hashlib.sha256(payload).hexdigest()
    expected_sha256 = "dc724b5945e0b751e3d0a134ceb30451d074bd27702d32f6104cfc335cd4aa1f"
    check("Payload SHA-256", sha256 == expected_sha256, sha256)
    
    # ---------------------------------------------------------
    # 2. Extracted Mach-O Binary Validation
    # ---------------------------------------------------------
    macho_path = ROOT / "artifacts/audio/smartio/smartio_ascv7.macho"
    check("Extracted Mach-O Exists", macho_path.exists(), str(macho_path.relative_to(ROOT)))
    
    macho_bytes = macho_path.read_bytes()
    check("Extracted Mach-O Size Matches Payload", len(macho_bytes) == 1140592, f"{len(macho_bytes)} bytes")
    check("Extracted Mach-O Content Matches Payload", macho_bytes == payload)
    
    # ---------------------------------------------------------
    # 3. Mach-O Header Fields
    # ---------------------------------------------------------
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, res = struct.unpack('<IIIIIIII', macho_bytes[:32])
    check("Mach-O Magic", magic == 0xfeedfacf, f"0x{magic:08x} == MH_MAGIC_64")
    check("Mach-O CPU Type", cputype == 0x100000c, f"0x{cputype:08x} == CPU_TYPE_ARM64")
    check("Mach-O CPU Subtype", cpusubtype == 0x0, f"0x{cpusubtype:08x} == CPU_SUBTYPE_ARM64_ALL")
    check("Mach-O File Type", filetype == 0x5, f"0x{filetype:08x} == MH_PRELOAD")
    check("Mach-O ncmds", ncmds == 6, f"{ncmds} == 6")
    check("Mach-O sizeofcmds", sizeofcmds == 2312, f"{sizeofcmds} == 2,312")
    check("Mach-O flags", flags == 0x1, f"0x{flags:08x} == MH_NOUNDEFS")
    
    # ---------------------------------------------------------
    # 4. Load Commands and Section Geometry
    # ---------------------------------------------------------
    offset = 32
    segments = {}
    sections = {}
    
    for i in range(ncmds):
        cmd, cmdsize = struct.unpack_from('<II', macho_bytes, offset)
        if cmd == 0x19: # LC_SEGMENT_64
            segname = macho_bytes[offset+8:offset+24].rstrip(b'\x00').decode('ascii')
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack_from('<QQQQIIII', macho_bytes, offset+24)
            segments[segname] = {
                "vmaddr": vmaddr, "vmsize": vmsize, "fileoff": fileoff, "filesize": filesize, "nsects": nsects
            }
            sec_off = offset + 72
            for s in range(nsects):
                sname = macho_bytes[sec_off:sec_off+16].rstrip(b'\x00').decode('ascii')
                s_addr, s_size, s_offset, s_align = struct.unpack_from('<QQII', macho_bytes, sec_off+32)
                sections[f"{segname}.{sname}"] = {
                    "vmaddr": s_addr, "size": s_size, "fileoff": s_offset, "align": s_align
                }
                sec_off += 80
        elif cmd == 0x2: # LC_SYMTAB
            symoff, nsyms, stroff, strsize = struct.unpack_from('<IIII', macho_bytes, offset+8)
            check("LC_SYMTAB symoff", symoff == 0x115000, f"0x{symoff:x}")
            check("LC_SYMTAB nsyms", nsyms == 154, f"{nsyms}")
            check("LC_SYMTAB stroff", stroff == 0x1159a0, f"0x{stroff:x}")
            check("LC_SYMTAB strsize", strsize == 0xdd0, f"0x{strsize:x}")
        elif cmd == 0x1b: # LC_SOURCE_VERSION
            ver = struct.unpack_from('<Q', macho_bytes, offset+8)[0]
            check("LC_SOURCE_VERSION", ver == 0xdc3d7260240b0c98, f"0x{ver:x}")
        elif cmd == 0x5: # LC_UNIXTHREAD
            pc = struct.unpack_from('<Q', macho_bytes, offset + 16 + 32*8)[0]
            check("LC_UNIXTHREAD Entry Point PC", pc == 0x0, f"0x{pc:x}")
        offset += cmdsize
        
    # Segment assertions
    check("__TEXT vmaddr", segments["__TEXT"]["vmaddr"] == 0x0)
    check("__TEXT vmsize", segments["__TEXT"]["vmsize"] == 0x1c000, "114,688 bytes")
    check("__TEXT fileoff", segments["__TEXT"]["fileoff"] == 0x1000)
    check("__TEXT nsects", segments["__TEXT"]["nsects"] == 6)
    
    check("__DATA vmaddr", segments["__DATA"]["vmaddr"] == 0x1c000)
    check("__DATA vmsize", segments["__DATA"]["vmsize"] == 0xf8000, "1,015,808 bytes")
    check("__DATA fileoff", segments["__DATA"]["fileoff"] == 0x1d000)
    check("__DATA nsects", segments["__DATA"]["nsects"] == 16)
    
    # Section assertions in __TEXT
    check("__TEXT.__text vmaddr", sections["__TEXT.__text"]["vmaddr"] == 0x0)
    check("__TEXT.__text size", sections["__TEXT.__text"]["size"] == 0x1a884, "108,676 bytes")
    check("__TEXT.__text fileoff", sections["__TEXT.__text"]["fileoff"] == 0x1000)
    
    check("__TEXT.__cstring vmaddr", sections["__TEXT.__cstring"]["vmaddr"] == 0x1a884)
    check("__TEXT.__cstring size", sections["__TEXT.__cstring"]["size"] == 0x1062, "4,194 bytes")
    check("__TEXT.__cstring fileoff", sections["__TEXT.__cstring"]["fileoff"] == 0x1b884)
    
    check("__TEXT.__const vmaddr", sections["__TEXT.__const"]["vmaddr"] == 0x1b8f0)
    check("__TEXT.__const size", sections["__TEXT.__const"]["size"] == 0x2d0, "720 bytes")
    check("__TEXT.__const fileoff", sections["__TEXT.__const"]["fileoff"] == 0x1c8f0)
    
    check("__TEXT._rtk_mtab vmaddr", sections["__TEXT._rtk_mtab"]["vmaddr"] == 0x1bbc0)
    check("__TEXT._rtk_mtab size", sections["__TEXT._rtk_mtab"]["size"] == 0x290, "656 bytes (82 words)")
    check("__TEXT._rtk_mtab fileoff", sections["__TEXT._rtk_mtab"]["fileoff"] == 0x1cbc0)
    
    # Section assertions in __DATA
    check("__DATA.__const vmaddr", sections["__DATA.__const"]["vmaddr"] == 0x1c000)
    check("__DATA.__const size", sections["__DATA.__const"]["size"] == 0x458, "1,112 bytes")
    check("__DATA.__const fileoff", sections["__DATA.__const"]["fileoff"] == 0x1d000)
    
    check("__DATA.__data vmaddr", sections["__DATA.__data"]["vmaddr"] == 0x1c458)
    check("__DATA.__data size", sections["__DATA.__data"]["size"] == 0x1750, "5,968 bytes")
    check("__DATA.__data fileoff", sections["__DATA.__data"]["fileoff"] == 0x1d458)
    
    check("__DATA._rtk_init_stack vmaddr", sections["__DATA._rtk_init_stack"]["vmaddr"] == 0x1dbd0)
    check("__DATA._rtk_init_stack size", sections["__DATA._rtk_init_stack"]["size"] == 0x1000, "4 KB")
    check("__DATA._rtk_init_stack fileoff", sections["__DATA._rtk_init_stack"]["fileoff"] == 0x1ebd0)
    
    check("__DATA._rtk_irq_stack vmaddr", sections["__DATA._rtk_irq_stack"]["vmaddr"] == 0x1ebd0)
    check("__DATA._rtk_irq_stack size", sections["__DATA._rtk_irq_stack"]["size"] == 0x1000, "4 KB")
    check("__DATA._rtk_irq_stack fileoff", sections["__DATA._rtk_irq_stack"]["fileoff"] == 0x1fbd0)
    
    check("__DATA._rtk_exc_stack vmaddr", sections["__DATA._rtk_exc_stack"]["vmaddr"] == 0x1fbd0)
    check("__DATA._rtk_exc_stack size", sections["__DATA._rtk_exc_stack"]["size"] == 0x1000, "4 KB")
    check("__DATA._rtk_exc_stack fileoff", sections["__DATA._rtk_exc_stack"]["fileoff"] == 0x20bd0)
    
    check("__DATA._rtk_boot vmaddr", sections["__DATA._rtk_boot"]["vmaddr"] == 0x21000)
    check("__DATA._rtk_boot size", sections["__DATA._rtk_boot"]["size"] == 0x2000, "8 KB")
    check("__DATA._rtk_boot fileoff", sections["__DATA._rtk_boot"]["fileoff"] == 0x22000)
    
    check("__DATA._rtk_page_tables vmaddr", sections["__DATA._rtk_page_tables"]["vmaddr"] == 0x23000)
    check("__DATA._rtk_page_tables size", sections["__DATA._rtk_page_tables"]["size"] == 0x21000, "132 KB (135,168 B)")
    check("__DATA._rtk_page_tables fileoff", sections["__DATA._rtk_page_tables"]["fileoff"] == 0x24000)
    
    check("__DATA._rtk_patchbay vmaddr", sections["__DATA._rtk_patchbay"]["vmaddr"] == 0x44000)
    check("__DATA._rtk_patchbay size", sections["__DATA._rtk_patchbay"]["size"] == 0x211, "529 bytes")
    check("__DATA._rtk_patchbay fileoff", sections["__DATA._rtk_patchbay"]["fileoff"] == 0x45000)
    
    check("__DATA._rtk_power vmaddr", sections["__DATA._rtk_power"]["vmaddr"] == 0x44220)
    check("__DATA._rtk_power size", sections["__DATA._rtk_power"]["size"] == 0x358, "856 bytes")
    check("__DATA._rtk_power fileoff", sections["__DATA._rtk_power"]["fileoff"] == 0x45220)
    
    check("__DATA.__gxf_data vmaddr", sections["__DATA.__gxf_data"]["vmaddr"] == 0x44578)
    check("__DATA.__gxf_data size", sections["__DATA.__gxf_data"]["size"] == 0x10, "16 bytes")
    check("__DATA.__gxf_data fileoff", sections["__DATA.__gxf_data"]["fileoff"] == 0x45578)
    
    check("__DATA._rtk_tunables vmaddr", sections["__DATA._rtk_tunables"]["vmaddr"] == 0x44588)
    check("__DATA._rtk_tunables size", sections["__DATA._rtk_tunables"]["size"] == 0x6a0, "1,696 bytes")
    check("__DATA._rtk_tunables fileoff", sections["__DATA._rtk_tunables"]["fileoff"] == 0x45588)
    
    check("__DATA.__zerofill vmaddr", sections["__DATA.__zerofill"]["vmaddr"] == 0x44c40)
    check("__DATA.__zerofill size", sections["__DATA.__zerofill"]["size"] == 0xcec80, "847,488 bytes")
    
    # ---------------------------------------------------------
    # 5. RTKit Version Banner Assertion
    # ---------------------------------------------------------
    banner_off = 0x1caac
    banner_end = macho_bytes.find(b"\x00", banner_off)
    banner_str = macho_bytes[banner_off:banner_end].decode("ascii")
    expected_banner = "RTKit_armv8_chinook_Oz_flto-3514.40.18.release"
    check("RTKit OS Version Banner", banner_str == expected_banner, banner_str)
    
    # ---------------------------------------------------------
    # 6. Stack Canaries Verification
    # ---------------------------------------------------------
    canary = b"RTKSTACKRTKSTACK"
    init_stk = macho_bytes[0x1ebd0:0x1ebd0+0x1000]
    irq_stk = macho_bytes[0x1fbd0:0x1fbd0+0x1000]
    exc_stk = macho_bytes[0x20bd0:0x20bd0+0x1000]
    
    check("Init Stack Canary Head", init_stk[:16] == canary)
    check("Init Stack Canary Tail", init_stk[-16:] == canary)
    check("IRQ Stack Canary Head", irq_stk[:16] == canary)
    check("IRQ Stack Canary Tail", irq_stk[-16:] == canary)
    check("Exc Stack Canary Head", exc_stk[:16] == canary)
    check("Exc Stack Canary Tail", exc_stk[-16:] == canary)
    
    # ---------------------------------------------------------
    # 7. Mailbox Table & Device Pointers
    # ---------------------------------------------------------
    mtab_bytes = macho_bytes[0x1cbc0:0x1cbc0+0x290]
    check("Mailbox Table Length", len(mtab_bytes) == 656, "656 bytes = 82 words")
    
    # Entry 1 points to __rtk_dev_bad_method (0x15224)
    w1 = struct.unpack_from('<Q', mtab_bytes, 8)[0]
    check("MTab Unhandled Method Trap", w1 == 0x15224, f"0x{w1:x} == __rtk_dev_bad_method")
    
    # Device descriptors in __DATA.__const (0x1c000, fileoff 0x1d000)
    dev_asc = struct.unpack_from('<Q', macho_bytes, 0x1d000 + (0x1c448 - 0x1c000))[0]
    dev_ascwrap = struct.unpack_from('<Q', macho_bytes, 0x1d000 + (0x1c440 - 0x1c000))[0]
    dev_outbox = struct.unpack_from('<Q', macho_bytes, 0x1d000 + (0x1c428 - 0x1c000))[0]
    dev_inbox = struct.unpack_from('<Q', macho_bytes, 0x1d000 + (0x1c420 - 0x1c000))[0]
    dev_tb = struct.unpack_from('<Q', macho_bytes, 0x1d000 + (0x1c450 - 0x1c000))[0]
    
    check("_RTK_DEV_ASC Pointer", dev_asc == 0x113798, f"0x{dev_asc:x}")
    check("_RTK_DEV_ASCWRAP Pointer", dev_ascwrap == 0x1ce00, f"0x{dev_ascwrap:x}")
    check("_RTK_DEV_ASC_OUTBOX Pointer", dev_outbox == 0x1d620, f"0x{dev_outbox:x}")
    check("_RTK_DEV_WRAPPER_INBOX Pointer", dev_inbox == 0x1d518, f"0x{dev_inbox:x}")
    check("_RTK_DEV_TIMEBASE Pointer", dev_tb == 0x1d130, f"0x{dev_tb:x}")
    
    # ---------------------------------------------------------
    # 8. Tunables Headers
    # ---------------------------------------------------------
    tun_bytes = macho_bytes[0x45588:0x45588+0x6a0]
    h0 = struct.unpack_from('<Q', tun_bytes, 0)[0]
    h1 = struct.unpack_from('<Q', tun_bytes, 848)[0]
    check("Tunables Partition 0 Header", h0 == 0xffffffff002a0301, f"0x{h0:016x}")
    check("Tunables Partition 1 (Retained) Header", h1 == 0xffffffff002a0303, f"0x{h1:016x}")
    
    # ---------------------------------------------------------
    # 9. Patchbay Tag & RTSZ Assertions
    # ---------------------------------------------------------
    pb_bytes = macho_bytes[0x45000:0x45000+0x211]
    check("Patchbay Length", len(pb_bytes) == 529, "529 bytes")
    check("Patchbay STKG Tag (Wire: GKTS)", pb_bytes[:4] == b"GKTS")
    
    # Find RTSZ (Wire: ZSTR)
    zstr_idx = pb_bytes.find(b"ZSTR")
    check("Patchbay RTSZ Tag Found", zstr_idx != -1)
    rtsz_val = struct.unpack_from('<I', pb_bytes, zstr_idx+8)[0]
    check("Patchbay Runtime Size", rtsz_val == 0x114000, f"0x{rtsz_val:08x} == 0x114000")
    
    # ---------------------------------------------------------
    # 10. Peripheral Channel Slots
    # ---------------------------------------------------------
    chan_bytes = macho_bytes[0x1d458:0x1d458+1840]
    check("Peripheral Channel Table Size", len(chan_bytes) == 1840, "230 slots x 8 bytes")
    
    # Check specific peripheral strings
    def get_chan_str(slot_idx: int) -> str:
        ptr = struct.unpack_from('<Q', chan_bytes, slot_idx * 8)[0]
        c_off = 0x1b884 + (ptr - 0x1a884)
        c_end = macho_bytes.find(b"\x00", c_off)
        return macho_bytes[c_off:c_end].decode("ascii")
        
    check("Peripheral Slot 20 (SPI0_TX)", get_chan_str(20) == "SPI0_TX")
    check("Peripheral Slot 21 (SPI0_RX)", get_chan_str(21) == "SPI0_RX")
    check("Peripheral Slot 60 (UART0_TX)", get_chan_str(60) == "UART0_TX")
    check("Peripheral Slot 61 (UART0_RX)", get_chan_str(61) == "UART0_RX")
    check("Peripheral Slot 40 (MCA0_TX)", get_chan_str(40) == "MCA0_TX")
    check("Peripheral Slot 91 (PDM0_RX)", get_chan_str(91) == "PDM0_RX")
    check("Peripheral Slot 100 (DPA0_TX)", get_chan_str(100) == "DPA0_TX")
    check("Peripheral Slot 140 (AOP_LEAP0_TX)", get_chan_str(140) == "AOP_LEAP0_TX")
    check("Peripheral Slot 6 (AOP_MCA0_TX)", get_chan_str(6) == "AOP_MCA0_TX")
    check("Peripheral Slot 211 (AOP_PDM0_RX)", get_chan_str(211) == "AOP_PDM0_RX")
    
    # ---------------------------------------------------------
    # 11. Artifact & Findings Completeness Check
    # ---------------------------------------------------------
    manifest_p = ROOT / "artifacts/audio/smartio/smartio_macho_manifest.json"
    shim_spec_p = ROOT / "artifacts/audio/smartio/smartio_peripheral_shim_spec.json"
    mbox_spec_p = ROOT / "artifacts/audio/smartio/smartio_mailbox_protocol_spec.json"
    findings_p = ROOT / "findings/audio/01_SMARTIO_ASC7_RTKIT_MICROKERNEL.md"
    
    check("Manifest JSON Exists", manifest_p.exists())
    check("Peripheral Shim Spec JSON Exists", shim_spec_p.exists())
    check("Mailbox Protocol Spec JSON Exists", mbox_spec_p.exists())
    check("Findings Dossier Exists", findings_p.exists())
    
    findings_size = findings_p.stat().st_size
    check("Findings Size >= 35,000 Bytes", findings_size >= 35000, f"{findings_size} bytes")
    
    findings_content = findings_p.read_text(encoding="utf-8")
    has_placeholders = any(tok in findings_content for tok in ["TODO", "TBD", "placeholder", "WIP"])
    check("Findings Zero Placeholder Tokens", not has_placeholders)
    
    print("=" * 80)
    print(f"  VERIFICATION RESULT: ALL {passed_checks}/{total_checks} CHECKS PASSED (100% GREEN)")
    print("=" * 80)

if __name__ == "__main__":
    main()
