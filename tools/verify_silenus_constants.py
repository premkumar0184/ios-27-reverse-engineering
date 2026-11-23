#!/usr/bin/env python3
"""
verify_silenus_constants.py — Comprehensive Empirical Architectural Verification Suite
Apple Silenus ISP RTKit SMP Microkernel & System Architecture (A19 Pro / t8150 / v57ap)
Target: iOS 27.2 (Darwin 24.2.0, Build 24B119)
"""

import sys
import os
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def verify_assertion(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if details:
        msg += f" ({details})"
    print(msg)
    return condition

def run_all_verifications() -> bool:
    print("=====================================================================================")
    print(" Apple Silenus ISP RTKit SMP Microkernel Verification Suite (Phase 1A - 1D)")
    print("=====================================================================================")
    all_ok = True

    # ---------------------------------------------------------------------------------
    # Suite 1: Deliverables Inventory
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 1: Verifying Deliverables Inventory ---")
    required_files = [
        ROOT / "artifacts/silenus/firmware/silenus_isp.macho",
        ROOT / "artifacts/silenus/firmware/silenus_isp_28995840.macho",
        ROOT / "artifacts/silenus/firmware/silenus_macho_manifest.json",
        ROOT / "artifacts/silenus/firmware/silenus_rtkit_cstring_dictionary.json",
        ROOT / "artifacts/silenus/firmware/silenus_rtkit_mtab.json",
        ROOT / "artifacts/silenus/firmware/silenus_rtkit_tunables.json",
        ROOT / "artifacts/silenus/firmware/silenus_rtkit_mmu_map.json",
        ROOT / "findings/silenus/01_RTKIT_SMP_MICROKERNEL.md",
        ROOT / "tools/extract_silenus_macho.py",
        ROOT / "tools/extract_silenus_rtkit_details.py",
    ]
    for rf in required_files:
        exists = rf.is_file()
        size = rf.stat().st_size if exists else 0
        all_ok &= verify_assertion(f"Deliverable exists: {rf.name}", exists, f"{size} bytes")

    # ---------------------------------------------------------------------------------
    # Suite 2: Mach-O Geometry & Checksum Verification
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 2: Verifying Mach-O Geometry & Checksums ---")
    macho_path = ROOT / "artifacts/silenus/firmware/silenus_isp.macho"
    if macho_path.is_file():
        data = macho_path.read_bytes()
        size = len(data)
        all_ok &= verify_assertion("Mach-O Full Size is 29,016,064 bytes", size == 29016064, f"{size} bytes")
        
        trimmed_path = ROOT / "artifacts/silenus/firmware/silenus_isp_28995840.macho"
        trimmed_size = trimmed_path.stat().st_size if trimmed_path.is_file() else 0
        all_ok &= verify_assertion("Trimmed Mach-O is 28,995,840 bytes", trimmed_size == 28995840, f"{trimmed_size} bytes")
        
        # Verify Mach-O Header
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack('<IIIIIII', data[:28])
        all_ok &= verify_assertion("Magic is MH_MAGIC_64 (0xfeedfacf)", magic == 0xfeedfacf, hex(magic))
        all_ok &= verify_assertion("cputype is CPU_TYPE_ARM64 (0x100000c)", cputype == 0x100000c, hex(cputype))
        all_ok &= verify_assertion("cpusubtype is CPU_SUBTYPE_ARM64E (0x80000002)", cpusubtype == 0x80000002, hex(cpusubtype))
        all_ok &= verify_assertion("filetype is MH_PRELOAD (5)", filetype == 5, str(filetype))
        all_ok &= verify_assertion("ncmds is 7", ncmds == 7, str(ncmds))

    # ---------------------------------------------------------------------------------
    # Suite 3: SMP Microkernel & Thread Stacks Verification
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 3: Verifying SMP Microkernel & Thread Stacks ---")
    if macho_path.is_file():
        # Reset vector at offset 0x4000
        reset_inst = struct.unpack('<I', data[0x4000:0x4004])[0]
        all_ok &= verify_assertion("Reset vector is b 0x204 (0x14000081)", reset_inst == 0x14000081, hex(reset_inst))
        
        # _rtk_smp_main pointer at 0x1ba8108
        smp_main_ptr = struct.unpack('<Q', data[0x1ba8108:0x1ba8110])[0]
        pac_disc = (smp_main_ptr >> 48) & 0xffff
        target_va = smp_main_ptr & 0x000000ffffffffff
        all_ok &= verify_assertion("_rtk_smp_main target VA is 0x399e0", target_va == 0x399e0, hex(target_va))
        all_ok &= verify_assertion("_rtk_smp_main PAC discriminator is 0x8130", pac_disc == 0x8130, hex(pac_disc))
        
        # Verify Stacks watermark (RTKSTACK)
        init_stk = data[0x15924d0:0x15924d8]
        irq_stk = data[0x15944d0:0x15944d8]
        exc_stk = data[0x15964d0:0x15964d8]
        expected_canary = b"RTKSTACK"
        all_ok &= verify_assertion("_rtk_init_stack has RTKSTACK canary", init_stk == expected_canary, str(init_stk))
        all_ok &= verify_assertion("_rtk_irq_stack has RTKSTACK canary", irq_stk == expected_canary, str(irq_stk))
        all_ok &= verify_assertion("_rtk_exc_stack has RTKSTACK canary", exc_stk == expected_canary, str(exc_stk))

    # ---------------------------------------------------------------------------------
    # Suite 4: Page Tables & MMU Configuration Verification
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 4: Verifying 4 MB Page Tables & Memory Protection ---")
    if macho_path.is_file():
        # Page table section length: 0x400000 (4 MB)
        # Check manifest
        man_path = ROOT / "artifacts/silenus/firmware/silenus_macho_manifest.json"
        if man_path.is_file():
            man = json.loads(man_path.read_text())
            pt_sec = next((s for s in man["macho_binary"]["sections"] if s["section"] == "_rtk_page_tables"), None)
            all_ok &= verify_assertion("_rtk_page_tables section exists", pt_sec is not None)
            if pt_sec:
                all_ok &= verify_assertion("_rtk_page_tables VA is 0x15a4000", pt_sec["vmaddr"] == "0x15a4000", pt_sec["vmaddr"])
                all_ok &= verify_assertion("_rtk_page_tables size is 4 MB (0x400000)", pt_sec["size"] == "0x400000", pt_sec["size"])
                
        # GXF data section
        gxf_sec = next((s for s in man["macho_binary"]["sections"] if s["section"] == "__gxf_data"), None)
        all_ok &= verify_assertion("__gxf_data section exists", gxf_sec is not None)
        if gxf_sec:
            all_ok &= verify_assertion("__gxf_data VA is 0x1ba4190", gxf_sec["vmaddr"] == "0x1ba4190", gxf_sec["vmaddr"])
            all_ok &= verify_assertion("__gxf_data size is 16 bytes (0x10)", gxf_sec["size"] == "0x10", gxf_sec["size"])

    # ---------------------------------------------------------------------------------
    # Suite 5: Mailbox Tables & Firmware Tunables Verification
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 5: Verifying Mailbox Tables & Tunables ---")
    mtab_path = ROOT / "artifacts/silenus/firmware/silenus_rtkit_mtab.json"
    if mtab_path.is_file():
        mtab = json.loads(mtab_path.read_text())
        all_ok &= verify_assertion("_rtk_mtab total words is 90", mtab["total_words"] == 90, str(mtab["total_words"]))
        all_ok &= verify_assertion("_rtk_mtab active handlers >= 30", mtab["total_active_handlers"] >= 30, str(mtab["total_active_handlers"]))

    tunables_path = ROOT / "artifacts/silenus/firmware/silenus_rtkit_tunables.json"
    if tunables_path.is_file():
        tunables = json.loads(tunables_path.read_text())
        all_ok &= verify_assertion("Tunables has 2 core partitions", tunables["partition_count"] == 2, str(tunables["partition_count"]))
        all_ok &= verify_assertion("Core 0 header magic is 0xffffffff00800301", tunables["partitions"][0]["header_magic"] == "0xffffffff00800301")
        all_ok &= verify_assertion("Core 1 header magic is 0xffffffff00800303", tunables["partitions"][1]["header_magic"] == "0xffffffff00800303")

    cstring_path = ROOT / "artifacts/silenus/firmware/silenus_rtkit_cstring_dictionary.json"
    if cstring_path.is_file():
        cs = json.loads(cstring_path.read_text())
        all_ok &= verify_assertion("Total strings >= 17,000", cs["metadata"]["total_strings"] >= 17000, str(cs["metadata"]["total_strings"]))
        all_ok &= verify_assertion("Total format strings >= 7,000", cs["metadata"]["total_format_strings"] >= 7000, str(cs["metadata"]["total_format_strings"]))

    # ---------------------------------------------------------------------------------
    # Suite 6: Dossier Completeness & Zero-Placeholder Verification
    # ---------------------------------------------------------------------------------
    print("\n--- Suite 6: Verifying Master Dossier Cleanliness ---")
    dossier_path = ROOT / "findings/silenus/01_RTKIT_SMP_MICROKERNEL.md"
    if dossier_path.is_file():
        dossier_text = dossier_path.read_text(encoding="utf-8", errors="replace")
        dossier_size = len(dossier_text.encode("utf-8"))
        all_ok &= verify_assertion("Master Dossier Volume >= 30,000 bytes", dossier_size >= 30000, f"{dossier_size} bytes")
        
        forbidden = ["TODO", "TBD", "placeholder", "coming soon", "work in progress"]
        found = [tok for tok in forbidden if tok.lower() in dossier_text.lower()]
        all_ok &= verify_assertion("Zero placeholder tokens found", len(found) == 0, f"Found: {found}")

    print("\n=====================================================================================")
    if all_ok:
        print(" ALL VERIFICATIONS PASSED (100% EMPIRICAL CONFIRMATION)")
    else:
        print(" SOME VERIFICATIONS FAILED")
    print("=====================================================================================")
    return all_ok

if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
