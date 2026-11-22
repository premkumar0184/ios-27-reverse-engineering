#!/usr/bin/env python3
"""
Milestone 3 Empirical Verification & Adversarial Stress-Test Suite
==================================================================
Empirically tests and stress-tests Milestone 3 SPTM and TXM binary extraction:
- Validates Mach-O headers, magic, and entrypoints against raw binaries.
- Disassembles and verifies exception vector table slots (0-15) for both monitors.
- Verifies all 42 SPTM function IDs and 17 dispatch tables.
- Validates TXM indirect branch dispatchers and panic loops.
- Verifies exact byte-level differential analysis between release and research TXM.
- Validates JSON schemas and checks for banned placeholders.
"""

import sys
import os
import json
import struct
import re
from pathlib import Path

REPO_ROOT = Path("/home/prem/Projects/iOS 27")
SPTM_RAW = REPO_ROOT / "artifacts/firmware/sptm.t8150.release.raw"
TXM_REL_RAW = REPO_ROOT / "artifacts/firmware/txm.iphoneos.release.raw"
TXM_RES_RAW = REPO_ROOT / "artifacts/firmware/txm.iphoneos.research.raw"
SPTM_JSON = REPO_ROOT / "artifacts/kernel/sptm_analysis.json"
TXM_JSON = REPO_ROOT / "artifacts/kernel/txm_analysis.json"

BANNED_PLACEHOLDERS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bPLACEHOLDER\b",
    r"\bLOREM IPSUM\b",
    r"\bINSERT HERE\b",
    r"\bCOMING SOON\b",
    r"\bOMITTED FOR BREVITY\b",
    r"\bNOT YET IMPLEMENTED\b",
    r"\[TBD\]",
    r"\[TODO\]",
]


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.details = []

    def check(self, condition: bool, msg: str):
        if not condition:
            self.passed = False
            self.details.append(f"FAILED: {msg}")
        else:
            self.details.append(f"PASSED: {msg}")


def parse_macho_header_and_commands(data: bytes):
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', data[:32])
    offset = 32
    segments = []
    unixthread_pc = None
    uuid_str = None
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack('<II', data[offset:offset+8])
        if cmd == 0x19: # LC_SEGMENT_64
            segname = data[offset+8:offset+24].split(b'\x00')[0].decode('utf-8', errors='ignore')
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack('<QQQQIIII', data[offset+24:offset+72])
            sects = []
            sect_off = offset + 72
            for _ in range(nsects):
                sectname = data[sect_off:sect_off+16].split(b'\x00')[0].decode('utf-8', errors='ignore')
                ssegname = data[sect_off+16:sect_off+32].split(b'\x00')[0].decode('utf-8', errors='ignore')
                s_addr, s_size, s_offset, s_align, s_reloff, s_nreloc, s_flags = struct.unpack('<QQIIIII', data[sect_off+32:sect_off+68])
                sects.append({
                    'sectname': sectname,
                    'segname': ssegname,
                    'addr': s_addr,
                    'size': s_size,
                    'offset': s_offset
                })
                sect_off += 80
            segments.append({
                'segname': segname,
                'vmaddr': vmaddr,
                'vmsize': vmsize,
                'fileoff': fileoff,
                'filesize': filesize,
                'sections': sects
            })
        elif cmd == 0x5: # LC_UNIXTHREAD
            flavor, count = struct.unpack('<II', data[offset+8:offset+16])
            pc = struct.unpack('<Q', data[offset+16+256:offset+16+264])[0]
            unixthread_pc = pc
        elif cmd == 0x1b: # LC_UUID
            uuid_bytes = data[offset+8:offset+24]
            uuid_str = f"{uuid_bytes[0:4].hex()}-{uuid_bytes[4:6].hex()}-{uuid_bytes[6:8].hex()}-{uuid_bytes[8:10].hex()}-{uuid_bytes[10:16].hex()}"
        offset += cmdsize
    return {
        'magic': magic,
        'cputype': cputype,
        'cpusubtype': cpusubtype,
        'filetype': filetype,
        'ncmds': ncmds,
        'sizeofcmds': sizeofcmds,
        'flags': flags,
        'segments': segments,
        'unixthread_pc': unixthread_pc,
        'uuid': uuid_str
    }


def test_sptm_raw_binary():
    res = TestResult("SPTM Raw Binary & Header Verification")
    with open(SPTM_RAW, 'rb') as f:
        data = f.read()

    info = parse_macho_header_and_commands(data)

    res.check(info['magic'] == 0xfeedfacf, f"Magic 0xfeedfacf (got {hex(info['magic'])})")
    res.check(info['cputype'] == 0x0100000c, f"CPUType ARM64 (got {hex(info['cputype'])})")
    res.check(info['cpusubtype'] in (0x80000002, 0xc0000002), f"CPUSubtype ARM64E (got {hex(info['cpusubtype'])})")
    res.check(info['filetype'] == 0x2, f"FileType MH_EXECUTE (got {hex(info['filetype'])})")
    res.check(info['unixthread_pc'] == 0xfffffff0270bc388, f"LC_UNIXTHREAD PC 0xfffffff0270bc388 (got {hex(info['unixthread_pc'] if info['unixthread_pc'] else 0)})")

    # Locate __exc section
    exc_sect = None
    for seg in info['segments']:
        for s in seg['sections']:
            if s['sectname'] == '__exc':
                exc_sect = s
                break
    res.check(exc_sect is not None, "__exc section found in Mach-O")
    if exc_sect:
        res.check(exc_sect['addr'] == 0xfffffff027118000, f"__exc addr 0xfffffff027118000 (got {hex(exc_sect['addr'])})")
        res.check(exc_sect['offset'] == 0x114000, f"__exc file offset 0x114000 (got {hex(exc_sect['offset'])})")
        res.check(exc_sect['size'] == 0x2000, f"__exc size 0x2000 (got {hex(exc_sect['size'])})")

    return res, data, info, exc_sect


def test_sptm_exception_vectors(data: bytes, exc_sect: dict):
    res = TestResult("SPTM Exception Vectors Disassembly Verification")
    base_va = exc_sect['addr']
    base_off = exc_sect['offset']

    expected_targets = {
        0: 0xfffffff0270b8168,
        1: 0xfffffff0270b75fc,
        2: 0xfffffff0270b7718,
        3: 0xfffffff0270b7834,
        4: 0xfffffff0270b83a4,
        8: 0xfffffff0270b7ca4,
        9: 0xfffffff0270b7950,
        10: 0xfffffff0270b7a6c,
        11: 0xfffffff0270b7b88,
    }
    panic_slots = [5, 6, 7, 12, 13, 14, 15]

    for slot_idx in range(16):
        slot_va = base_va + slot_idx * 0x80
        slot_off = base_off + slot_idx * 0x80
        insts = struct.unpack('<IIII', data[slot_off:slot_off+16])

        if slot_idx in expected_targets:
            inst0 = insts[0]
            is_b = (inst0 & 0x7c000000) == 0x14000000
            res.check(is_b, f"Slot {slot_idx} starts with unconditional branch 'b' opcode")
            if is_b:
                imm26 = inst0 & 0x03ffffff
                if imm26 & 0x02000000:
                    imm26 -= 0x04000000
                target = slot_va + imm26 * 4
                exp = expected_targets[slot_idx]
                res.check(target == exp, f"Slot {slot_idx} branch target 0x{target:x} == 0x{exp:x}")
        elif slot_idx in panic_slots:
            # Panic loop: mov x0, #0xdead; wfe; b .
            # mov x0, #0xdead -> 0xd29bd5a0
            # wfe -> 0xd503205f
            # b . -> 0x17ffffff
            is_panic = (insts[0] == 0xd29bd5a0) and (insts[1] == 0xd503205f) and (insts[2] == 0x17ffffff)
            res.check(is_panic, f"Slot {slot_idx} panic spin loop (mov x0, #0xdead; wfe; b .)")

    return res


def test_sptm_strings_and_tables(data: bytes):
    res = TestResult("SPTM Function IDs and Dispatch Tables String Verification")

    # 42 Function IDs
    matches_fn = [(m.start(), m.group().decode()) for m in re.finditer(rb'SPTM_FUNCTIONID_[A-Z0-9_]+', data)]
    res.check(len(matches_fn) == 42, f"Exactly 42 SPTM_FUNCTIONID_* strings found (got {len(matches_fn)})")
    if matches_fn:
        res.check(matches_fn[0][1] == "SPTM_FUNCTIONID_LOCKDOWN", f"First function ID is SPTM_FUNCTIONID_LOCKDOWN (got {matches_fn[0][1]})")
        res.check(matches_fn[0][0] == 0x124e6, f"First function ID offset 0x124e6 (got {hex(matches_fn[0][0])})")
        res.check(matches_fn[-1][1] == "SPTM_FUNCTIONID_OUTPUT_AREA", f"Last function ID is SPTM_FUNCTIONID_OUTPUT_AREA (got {matches_fn[-1][1]})")
        res.check(matches_fn[-1][0] == 0x12a10, f"Last function ID offset 0x12a10 (got {hex(matches_fn[-1][0])})")

    # 17 Dispatch Tables
    # In binary: 1 instance of SPTM_DISPATCH_TABLE (in VIOLATION_ILLEGAL_SPTM_DISPATCH_TABLE) at 0xca81,
    # plus 16 contiguous domain tables from 0x11f19 to 0x120e5.
    dt_matches = [(m.start(), m.group().decode()) for m in re.finditer(rb'SPTM_DISPATCH_TABLE[A-Z0-9_]*', data)]
    seen_dt = set()
    ordered_dt = []
    for off, name in dt_matches:
        if name not in seen_dt:
            seen_dt.add(name)
            ordered_dt.append((off, name))

    res.check(len(ordered_dt) == 17, f"Exactly 17 unique SPTM_DISPATCH_TABLE* string names found (got {len(ordered_dt)})")
    res.check(ordered_dt[0][1] == "SPTM_DISPATCH_TABLE" and ordered_dt[0][0] == 0xca81, f"Table 0 is SPTM_DISPATCH_TABLE at 0xca81 (got {ordered_dt[0]})")
    res.check(ordered_dt[1][1] == "SPTM_DISPATCH_TABLE_XNU_BOOTSTRAP" and ordered_dt[1][0] == 0x11f19, f"Table 1 is SPTM_DISPATCH_TABLE_XNU_BOOTSTRAP at 0x11f19")
    res.check(ordered_dt[-1][1] == "SPTM_DISPATCH_TABLE_RESERVED2" and ordered_dt[-1][0] == 0x120e5, f"Table 16 is SPTM_DISPATCH_TABLE_RESERVED2 at 0x120e5")

    return res


def test_txm_raw_binary():
    res = TestResult("TXM Raw Binary & Entrypoint Verification")
    with open(TXM_REL_RAW, 'rb') as f:
        data = f.read()

    info = parse_macho_header_and_commands(data)

    res.check(info['magic'] == 0xfeedfacf, f"Magic 0xfeedfacf (got {hex(info['magic'])})")
    res.check(info['unixthread_pc'] == 0xfffffff017084000, f"LC_UNIXTHREAD PC 0xfffffff017084000 (got {hex(info['unixthread_pc'] if info['unixthread_pc'] else 0)})")

    # Locate __bootcode and __exc sections
    exc_sect = None
    bootcode_sect = None
    for seg in info['segments']:
        for s in seg['sections']:
            if s['sectname'] == '__exc':
                exc_sect = s
            elif s['sectname'] == '__bootcode':
                bootcode_sect = s

    res.check(bootcode_sect is not None, "__bootcode section found in Mach-O")
    if bootcode_sect:
        res.check(bootcode_sect['addr'] == 0xfffffff017084060, f"__bootcode addr 0xfffffff017084060 (got {hex(bootcode_sect['addr'])})")
        res.check(bootcode_sect['offset'] == 0x80060, f"__bootcode file offset 0x80060 (got {hex(bootcode_sect['offset'])})")

    res.check(exc_sect is not None, "__exc section found in Mach-O")
    if exc_sect:
        res.check(exc_sect['addr'] == 0xfffffff01707c000, f"__exc addr 0xfffffff01707c000 (got {hex(exc_sect['addr'])})")
        res.check(exc_sect['offset'] == 0x78000, f"__exc file offset 0x78000 (got {hex(exc_sect['offset'])})")
        res.check(exc_sect['size'] == 0x8a0, f"__exc size 0x8a0 (got {hex(exc_sect['size'])})")

    return res, data, info, exc_sect


def test_txm_exception_vectors(data: bytes, exc_sect: dict):
    res = TestResult("TXM Exception Vectors Indirect Branch Disassembly Verification")
    base_va = exc_sect['addr']
    base_off = exc_sect['offset']

    # Slots 0-3: stp x0, x1, [sp, #-16]!; mov x1, #id; ldr x0, [pool]; braaz x0
    expected_slot_ids = {0: 3, 1: 0, 2: 1, 3: 2}
    expected_literals = {
        0: 0xfffffff01707c898,
        1: 0xfffffff01707c890,
        2: 0xfffffff01707c890,
        3: 0xfffffff01707c890,
    }

    for slot_idx in range(4):
        slot_va = base_va + slot_idx * 0x80
        slot_off = base_off + slot_idx * 0x80
        insts = struct.unpack('<IIII', data[slot_off:slot_off+16])

        # 1. stp x0, x1, [sp, #-16]! -> 0xa9bf07e0
        res.check(insts[0] == 0xa9bf07e0, f"Slot {slot_idx} inst 0 is stp x0, x1, [sp, #-16]! (0x{insts[0]:08x})")
        # 2. mov x1, #id -> 0xd2800001 | (id << 5)
        exp_id = expected_slot_ids[slot_idx]
        exp_mov = 0xd2800001 | (exp_id << 5)
        res.check(insts[1] == exp_mov, f"Slot {slot_idx} inst 1 is mov x1, #{exp_id} (0x{insts[1]:08x})")
        # 3. ldr x0, literal_pool (0x58000000 mask 0xff000000)
        is_ldr = (insts[2] & 0xff000000) == 0x58000000
        res.check(is_ldr, f"Slot {slot_idx} inst 2 is ldr x0 literal")
        if is_ldr:
            imm19 = (insts[2] >> 5) & 0x7ffff
            if imm19 & 0x40000:
                imm19 -= 0x80000
            target_lit = (slot_va + 8) + imm19 * 4
            exp_lit = expected_literals[slot_idx]
            res.check(target_lit == exp_lit, f"Slot {slot_idx} literal addr 0x{target_lit:x} == 0x{exp_lit:x}")
        # 4. braaz x0 -> 0xd61f081f
        res.check(insts[3] == 0xd61f081f, f"Slot {slot_idx} inst 3 is braaz x0 (0x{insts[3]:08x})")

    # Slots 4-15: Panic spin loops
    for slot_idx in range(4, 16):
        slot_off = base_off + slot_idx * 0x80
        insts = struct.unpack('<IIII', data[slot_off:slot_off+16])
        is_panic = (insts[0] == 0xd29bd5a0) and (insts[1] == 0xd503205f) and (insts[2] == 0x17ffffff)
        res.check(is_panic, f"Slot {slot_idx} panic spin loop (mov x0, #0xdead; wfe; b .)")

    return res


def test_txm_differential():
    res = TestResult("TXM Differential Release vs Research Empirical Test")
    with open(TXM_REL_RAW, 'rb') as f:
        rel = f.read()
    with open(TXM_RES_RAW, 'rb') as f:
        res_data = f.read()

    res.check(len(rel) == len(res_data) == 557088, f"Sizes match exactly (557,088 bytes)")
    diff_indices = [i for i in range(len(rel)) if rel[i] != res_data[i]]
    res.check(len(diff_indices) == 3981, f"Total divergent bytes == 3981 (got {len(diff_indices)})")

    chunks = []
    if diff_indices:
        cur_start = diff_indices[0]
        cur_prev = diff_indices[0]
        for idx in diff_indices[1:]:
            if idx == cur_prev + 1:
                cur_prev = idx
            else:
                chunks.append((cur_start, cur_prev))
                cur_start = idx
                cur_prev = idx
        chunks.append((cur_start, cur_prev))

    res.check(len(chunks) == 267, f"Total contiguous chunks == 267 (got {len(chunks)})")

    # Check text section differences
    text_start = 0x2c000
    text_end = 0x2c000 + 0x49c28
    text_diff_indices = [i for i in diff_indices if text_start <= i < text_end]
    res.check(len(text_diff_indices) == 125, f"__text divergent bytes == 125 (got {len(text_diff_indices)})")

    diff_words = sorted(list(set(i // 4 * 4 for i in text_diff_indices)))
    res.check(len(diff_words) == 124, f"__text divergent instruction words == 124 (got {len(diff_words)})")

    all_adds = True
    all_diff_one = True
    for w in diff_words:
        i_rel = struct.unpack('<I', rel[w:w+4])[0]
        i_res = struct.unpack('<I', res_data[w:w+4])[0]
        is_add_rel = (i_rel & 0xff800000) == 0x91000000
        is_add_res = (i_res & 0xff800000) == 0x91000000
        if not (is_add_rel and is_add_res):
            all_adds = False
        imm_rel = (i_rel >> 10) & 0xfff
        imm_res = (i_res >> 10) & 0xfff
        if (imm_res - imm_rel) != 1:
            all_diff_one = False

    res.check(all_adds, "All 124 divergent instructions are ADD immediate opcodes")
    res.check(all_diff_one, "All 124 instructions have immediate offset shift of exactly +1")

    return res


def test_json_schemas_and_placeholders():
    res = TestResult("JSON Schema Integrity & Anti-Placeholder Test")

    with open(SPTM_JSON, 'r') as f:
        sptm_text = f.read()
        sptm_data = json.loads(sptm_text)

    with open(TXM_JSON, 'r') as f:
        txm_text = f.read()
        txm_data = json.loads(txm_text)

    # Check placeholders
    for p in BANNED_PLACEHOLDERS:
        m_sptm = re.findall(p, sptm_text, re.IGNORECASE)
        res.check(len(m_sptm) == 0, f"SPTM JSON free of placeholder '{p}' (found {len(m_sptm)})")
        m_txm = re.findall(p, txm_text, re.IGNORECASE)
        res.check(len(m_txm) == 0, f"TXM JSON free of placeholder '{p}' (found {len(m_txm)})")

    # Invariants in SPTM JSON
    res.check(sptm_data['summary']['entry_point'] == '0xfffffff0270bc388', "SPTM entry_point == 0xfffffff0270bc388")
    res.check(len(sptm_data['function_ids']) == 42, "SPTM function_ids count == 42")
    res.check(len(sptm_data['dispatch_tables']) == 17, "SPTM dispatch_tables count == 17")
    res.check(len(sptm_data['exception_vectors']['slots']) == 16, "SPTM vector slots count == 16")
    res.check(sptm_data['hardware_protection_registers']['ctrr_protection']['device_tree_property'] == 'key-sptm-ctrr', "SPTM CTRR device tree property")
    res.check(sptm_data['hardware_protection_registers']['gapf_protection']['enable_register_prop'] == 'sptm-gapf-enable-reg', "SPTM GAPF enable register property")

    # Invariants in TXM JSON
    res.check(txm_data['summary']['entry_point'] == '0xfffffff017084000', "TXM entry_point == 0xfffffff017084000")
    res.check(txm_data['entrypoints']['primary_entrypoint']['virtual_address'] == '0xfffffff017084000', "TXM primary_entrypoint VA == 0xfffffff017084000")
    res.check(txm_data['entrypoints']['bootcode_entrypoint']['virtual_address'] == '0xfffffff017084060', "TXM bootcode_entrypoint VA == 0xfffffff017084060")
    res.check(len(txm_data['exception_vectors']['slots']) == 16, "TXM vector slots count == 16")
    res.check(len(txm_data['smc_dispatch_tables']['image4_dispatch_handlers']) == 6, "TXM Image4 dispatch handlers count == 6")
    res.check(txm_data['differential_release_vs_research']['total_divergent_bytes'] == 3981, "TXM differential total_divergent_bytes == 3981")
    res.check(txm_data['differential_release_vs_research']['code_logic_divergence_count'] == 0, "TXM differential code_logic_divergence == 0")

    return res


def main():
    print("=" * 70)
    print("RUNNING EMPIRICAL CHALLENGER VERIFICATION HARNESS FOR MILESTONE 3")
    print("=" * 70)

    all_tests = []

    t1, sptm_data, sptm_info, sptm_exc = test_sptm_raw_binary()
    all_tests.append(t1)

    t2 = test_sptm_exception_vectors(sptm_data, sptm_exc)
    all_tests.append(t2)

    t3 = test_sptm_strings_and_tables(sptm_data)
    all_tests.append(t3)

    t4, txm_data, txm_info, txm_exc = test_txm_raw_binary()
    all_tests.append(t4)

    t5 = test_txm_exception_vectors(txm_data, txm_exc)
    all_tests.append(t5)

    t6 = test_txm_differential()
    all_tests.append(t6)

    t7 = test_json_schemas_and_placeholders()
    all_tests.append(t7)

    total_passed = 0
    total_checks = 0
    failures = 0

    for t in all_tests:
        print(f"\n--- {t.name} ---")
        for detail in t.details:
            print(f"  {detail}")
            total_checks += 1
            if detail.startswith("PASSED"):
                total_passed += 1
            else:
                failures += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {total_passed}/{total_checks} checks passed across {len(all_tests)} test suites.")
    if failures == 0:
        print("VERDICT: ALL TESTS PASSED. WORKER FINDINGS EMPIRICALLY CONFIRMED.")
        return 0
    else:
        print(f"VERDICT: {failures} FAILURES DETECTED. REQUEST CHANGES.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
