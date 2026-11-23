#!/usr/bin/env python3
"""
extract_msrf_macho.py - Extract and Dissect MSRF (Memory Subsystem Resource Firmware) Mach-O Binary
Target: iPhone18,3_27.2_24B119_Restore/Firmware/msr/t8150.msrf.im4p
Output: artifacts/gpu/tbdr/t8150.msrf.macho and artifacts/gpu/tbdr/msrf_macho_manifest.json
"""

import os
import sys
import json
import struct
from pathlib import Path

DEFAULT_MSRF_PATH = "iPhone18,3_27.2_24B119_Restore/Firmware/msr/t8150.msrf.im4p"
DEFAULT_OUTPUT_MACHO = "artifacts/gpu/tbdr/t8150.msrf.macho"
DEFAULT_OUTPUT_MANIFEST = "artifacts/gpu/tbdr/msrf_macho_manifest.json"

def unpack_im4p(im4p_bytes):
    """
    Parses ASN.1 DER IM4P container and extracts Mach-O payload starting at offset 25.
    Header structure:
      0..4:   30 83 02 78 78 (SEQUENCE len 0x27878)
      5..10:  16 04 49 4d 34 50 (IA5String "IM4P")
      11..16: 16 04 6d 73 72 66 (IA5String "msrf")
      17..19: 16 01 31 (IA5String "1")
      20..24: 04 83 02 78 64 (OCTET STRING len 0x27864)
      25..:   Mach-O 32-bit payload (starts with 0xfeedface)
    """
    if len(im4p_bytes) < 32:
        raise ValueError("IM4P file too short")
    
    seq_tag = im4p_bytes[0]
    if seq_tag != 0x30:
        raise ValueError(f"Invalid ASN.1 SEQUENCE tag: {hex(seq_tag)}")
    
    magic_tag = im4p_bytes[7:11]
    if magic_tag != b'IM4P':
        raise ValueError(f"Invalid IM4P magic: {magic_tag}")
    
    fourcc = im4p_bytes[13:17].decode('ascii', errors='replace')
    version = im4p_bytes[19:20].decode('ascii', errors='replace')
    
    # Octet string starts at 20
    octet_tag = im4p_bytes[20]
    if octet_tag != 0x04:
        raise ValueError(f"Invalid OCTET STRING tag: {hex(octet_tag)}")
    
    payload_len = (im4p_bytes[22] << 16) | (im4p_bytes[23] << 8) | im4p_bytes[24]
    macho_bytes = im4p_bytes[25:25 + payload_len]
    
    # Verify Mach-O 32-bit header
    macho_magic = struct.unpack('<I', macho_bytes[:4])[0]
    if macho_magic != 0xfeedface:
        raise ValueError(f"Invalid Mach-O magic: {hex(macho_magic)} (expected 0xfeedface)")
    
    return {
        "fourcc": fourcc,
        "version": version,
        "payload_len": payload_len,
        "total_file_len": len(im4p_bytes),
        "payload_offset": 25,
        "macho_bytes": macho_bytes
    }

def parse_macho(macho_bytes):
    """
    Parses 32-bit Mach-O headers, segments, sections, and symbol table.
    """
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack('<7I', macho_bytes[:28])
    
    cpu_map = {0x0c: "CPU_TYPE_ARM"}
    subtype_map = {0x0f: "CPU_SUBTYPE_ARM_V7EM (Cortex-M3/M4)"}
    filetype_map = {0x05: "MH_PRELOAD"}
    
    header_info = {
        "magic": hex(magic),
        "magic_name": "MH_MAGIC (32-bit Little-Endian)",
        "cputype": cputype,
        "cputype_name": cpu_map.get(cputype, f"UNKNOWN_{cputype}"),
        "cpusubtype": cpusubtype,
        "cpusubtype_name": subtype_map.get(cpusubtype, f"UNKNOWN_{cpusubtype}"),
        "filetype": filetype,
        "filetype_name": filetype_map.get(filetype, f"UNKNOWN_{filetype}"),
        "ncmds": ncmds,
        "sizeofcmds": sizeofcmds,
        "flags": hex(flags),
        "flags_desc": "MH_NOUNDEFS" if flags == 1 else hex(flags)
    }
    
    segments = []
    sections = []
    symtab_info = {}
    
    offset = 28
    for cmd_idx in range(ncmds):
        cmd, cmdsize = struct.unpack('<2I', macho_bytes[offset:offset+8])
        cmd_data = macho_bytes[offset:offset+cmdsize]
        
        if cmd == 1: # LC_SEGMENT (32-bit)
            segname_raw, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack(
                '<16sIIIIIIII', cmd_data[8:56]
            )
            segname = segname_raw.decode('utf-8', errors='ignore').rstrip('\x00')
            seg_entry = {
                "segment_name": segname,
                "vmaddr": hex(vmaddr),
                "vmaddr_int": vmaddr,
                "vmsize": hex(vmsize),
                "vmsize_int": vmsize,
                "fileoff": hex(fileoff),
                "fileoff_int": fileoff,
                "filesize": hex(filesize),
                "filesize_int": filesize,
                "maxprot": maxprot,
                "initprot": initprot,
                "nsects": nsects,
                "flags": sflags,
                "sections": []
            }
            
            so = 56
            for s_idx in range(nsects):
                sectname_raw, segname2_raw, saddr, ssize, soff, salign, sreloff, snrel, sectflags, r1, r2 = struct.unpack(
                    '<16s16s9I', cmd_data[so:so+68]
                )
                sectname = sectname_raw.decode('utf-8', errors='ignore').rstrip('\x00')
                sect_entry = {
                    "section_name": sectname,
                    "segment_name": segname,
                    "addr": hex(saddr),
                    "addr_int": saddr,
                    "size": hex(ssize),
                    "size_int": ssize,
                    "offset": hex(soff),
                    "offset_int": soff,
                    "align": salign,
                    "reloff": sreloff,
                    "nreloc": snrel,
                    "flags": hex(sectflags)
                }
                seg_entry["sections"].append(sect_entry)
                sections.append(sect_entry)
                so += 68
            segments.append(seg_entry)
            
        elif cmd == 2: # LC_SYMTAB
            symoff, nsyms, stroff, strsize = struct.unpack('<4I', cmd_data[8:24])
            symtab_info = {
                "symoff": symoff,
                "nsyms": nsyms,
                "stroff": stroff,
                "strsize": strsize
            }
        offset += cmdsize
        
    # Helper for address lookup
    def va_to_fileoff(va):
        for seg in segments:
            if seg["vmaddr_int"] <= va < seg["vmaddr_int"] + seg["vmsize_int"]:
                return seg["fileoff_int"] + (va - seg["vmaddr_int"])
        return None

    # Parse symbols
    symbols = []
    symbol_dict = {}
    if symtab_info:
        stroff = symtab_info["stroff"]
        strsize = symtab_info["strsize"]
        strings = macho_bytes[stroff:stroff+strsize]
        symoff = symtab_info["symoff"]
        nsyms = symtab_info["nsyms"]
        
        current_source_file = "global"
        for i in range(nsyms):
            n_strx, n_type, n_sect, n_desc, n_value = struct.unpack('<IBBhI', macho_bytes[symoff + i*12 : symoff + (i+1)*12])
            end = strings.find(b'\x00', n_strx)
            sname = strings[n_strx:end].decode('utf-8', errors='ignore') if end != -1 else ''
            
            if n_type == 0x64: # N_SO
                if sname and not sname.endswith('/'):
                    current_source_file = sname
            
            sym_rec = {
                "name": sname,
                "type": hex(n_type),
                "type_int": n_type,
                "section": n_sect,
                "desc": n_desc,
                "value": hex(n_value),
                "value_int": n_value,
                "source_file": current_source_file
            }
            symbols.append(sym_rec)
            if sname:
                symbol_dict[sname] = sym_rec

    # Extract Key Tables & Constants
    extracted_tables = {}
    
    # 1. _DEFAULT_BLOCK_EN_LIST (0x00111092)
    def_blist_off = va_to_fileoff(0x00111092)
    if def_blist_off:
        blist_bytes = macho_bytes[def_blist_off:def_blist_off+48]
        blist_words = struct.unpack('<24H', blist_bytes)
        entries = []
        for i in range(0, 24, 4):
            entries.append([hex(w) for w in blist_words[i:i+4]])
        extracted_tables["_DEFAULT_BLOCK_EN_LIST"] = {
            "address": "0x00111092",
            "size_bytes": 48,
            "num_entries": 6,
            "raw_hex": blist_bytes.hex(),
            "entries_uint16": entries
        }
    
    # 2. _TD_CACHE_MAPPING (0x00111704)
    td_cache_off = va_to_fileoff(0x00111704)
    if td_cache_off:
        td_bytes = macho_bytes[td_cache_off:td_cache_off+16]
        extracted_tables["_TD_CACHE_MAPPING"] = {
            "address": "0x00111704",
            "size_bytes": 16,
            "raw_hex": td_bytes.hex(),
            "mapping_table": [b if b != 0xff else -1 for b in td_bytes]
        }
        
    # 3. _MSR_MAX_TILE_SIZE (0x001116f0)
    tile_size_off = va_to_fileoff(0x001116f0)
    if tile_size_off:
        ts_bytes = macho_bytes[tile_size_off:tile_size_off+4]
        width, height = struct.unpack('<HH', ts_bytes)
        extracted_tables["_MSR_MAX_TILE_SIZE"] = {
            "address": "0x001116f0",
            "size_bytes": 4,
            "raw_hex": ts_bytes.hex(),
            "max_tile_width": width,
            "max_tile_height": height,
            "dimensions_str": f"{width}x{height}"
        }
        
    # 4. _BITMAP_TO_CNT (0x001116f4)
    bmp_cnt_off = va_to_fileoff(0x001116f4)
    if bmp_cnt_off:
        bmp_bytes = macho_bytes[bmp_cnt_off:bmp_cnt_off+16]
        extracted_tables["_BITMAP_TO_CNT"] = {
            "address": "0x001116f4",
            "size_bytes": 16,
            "raw_hex": bmp_bytes.hex(),
            "lookup_table": list(bmp_bytes)
        }
        
    # 5. _msr_block_attributes (0x00111444)
    blk_attr_off = va_to_fileoff(0x00111444)
    if blk_attr_off:
        blk_bytes = macho_bytes[blk_attr_off:blk_attr_off+60]
        blk_entries = []
        for i in range(0, 60, 4):
            blk_entries.append(list(blk_bytes[i:i+4]))
        extracted_tables["_msr_block_attributes"] = {
            "address": "0x00111444",
            "size_bytes": 60,
            "num_entries": 15,
            "raw_hex": blk_bytes.hex(),
            "entries": blk_entries
        }

    # 6. _CONTROL_BLOCK_CONST (0x00110ed0)
    cbc_off = va_to_fileoff(0x00110ed0)
    if cbc_off:
        cbc_bytes = macho_bytes[cbc_off:cbc_off+0x108]
        extracted_tables["_CONTROL_BLOCK_CONST"] = {
            "address": "0x00110ed0",
            "size_bytes": 264,
            "firmware_uuid": cbc_bytes[:16].hex(),
            "raw_hex": cbc_bytes.hex(),
            "log_main_buf_offset": hex(struct.unpack('<I', cbc_bytes[0x18:0x1c])[0]),
            "log_prof_buf_offset": hex(struct.unpack('<I', cbc_bytes[0x20:0x24])[0]),
            "tdr_buf_offset": hex(struct.unpack('<I', cbc_bytes[0x28:0x2c])[0]),
            "sdr_buf_offset": hex(struct.unpack('<I', cbc_bytes[0x30:0x34])[0]),
            "magic_tag": cbc_bytes[0x38:0x3c].decode('ascii', errors='replace')
        }

    # 7. _fmt_info (0x001110c2) - 64 Hardware Format Entries (14 bytes each = 896 bytes + 2 pad)
    fmt_off = va_to_fileoff(0x001110c2)
    if fmt_off:
        fmt_raw = macho_bytes[fmt_off:fmt_off+898]
        fmt_entries = []
        for f_idx in range(64):
            f_entry = fmt_raw[f_idx*14:(f_idx+1)*14]
            fmt_entries.append({
                "format_id": f_idx,
                "component_count": f_entry[0],
                "bit_depths": list(f_entry[1:5]),
                "bit_shifts": list(f_entry[5:9]),
                "bytes_per_pixel": f_entry[9],
                "flags": list(f_entry[10:14]),
                "raw_hex": f_entry.hex()
            })
        extracted_tables["_fmt_info"] = {
            "address": "0x001110c2",
            "size_bytes": 898,
            "total_formats": 64,
            "entry_size_bytes": 14,
            "formats": fmt_entries
        }

    # 8. _msr_comp_attributes (0x00111480) - 15 Blocks x 32 bytes = 480 bytes
    comp_off = va_to_fileoff(0x00111480)
    if comp_off:
        comp_raw = macho_bytes[comp_off:comp_off+480]
        comp_blocks = []
        for b_idx in range(15):
            blk_data = comp_raw[b_idx*32:(b_idx+1)*32]
            comp_blocks.append({
                "block_index": b_idx,
                "raw_hex": blk_data.hex(),
                "bytes": list(blk_data)
            })
        extracted_tables["_msr_comp_attributes"] = {
            "address": "0x00111480",
            "size_bytes": 480,
            "num_blocks": 15,
            "block_size_bytes": 32,
            "blocks": comp_blocks
        }

    # 9. _DEFAULT_ITERATION_ORDER (0x00111083) & _SCL_MODE_ITERATION_ORDER (0x00111074)
    io_off = va_to_fileoff(0x00111083)
    scl_io_off = va_to_fileoff(0x00111074)
    if io_off and scl_io_off:
        io_bytes = list(macho_bytes[io_off:io_off+15])
        scl_io_bytes = list(macho_bytes[scl_io_off:scl_io_off+15])
        extracted_tables["_DEFAULT_ITERATION_ORDER"] = {
            "address": "0x00111083",
            "size_bytes": 15,
            "order": io_bytes
        }
        extracted_tables["_SCL_MODE_ITERATION_ORDER"] = {
            "address": "0x00111074",
            "size_bytes": 15,
            "order": scl_io_bytes
        }

    # 10. _nc_attr_all (0x00111714)
    nc_off = va_to_fileoff(0x00111714)
    if nc_off:
        nc_bytes = macho_bytes[nc_off:nc_off+32]
        extracted_tables["_nc_attr_all"] = {
            "address": "0x00111714",
            "size_bytes": 32,
            "raw_hex": nc_bytes.hex()
        }

    # 11. Cortex-M3 Vector Table (_Vectors at 0x00100000)
    vec_off = va_to_fileoff(0x00100000)
    if vec_off:
        vec_bytes = macho_bytes[vec_off:vec_off+64]
        vec_words = struct.unpack('<16I', vec_bytes)
        vector_names = [
            "Initial_SP", "Reset_ISR", "NMI_Handler", "HardFault_Handler",
            "MemManage_Handler", "BusFault_Handler", "UsageFault_Handler", "Reserved_7",
            "Reserved_8", "Reserved_9", "Reserved_10", "SVCall_Handler",
            "DebugMon_Handler", "Reserved_13", "PendSV_Handler", "SysTick_Handler"
        ]
        extracted_tables["_Vectors"] = {
            "address": "0x00100000",
            "size_bytes": 64,
            "entries": [{
                "vector_index": i,
                "name": vector_names[i],
                "address": hex(vec_words[i]),
                "address_int": vec_words[i]
            } for i in range(16)]
        }

    return {
        "header": header_info,
        "segments": segments,
        "sections": sections,
        "symtab_header": symtab_info,
        "total_symbols": len(symbols),
        "tables": extracted_tables,
        "symbols": symbols
    }

def main():
    msrf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MSRF_PATH
    output_macho = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_MACHO
    output_manifest = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_OUTPUT_MANIFEST

    print(f"[*] Reading MSRF IM4P container from: {msrf_path}")
    if not os.path.exists(msrf_path):
        print(f"[-] Error: file {msrf_path} not found.")
        sys.exit(1)

    with open(msrf_path, 'rb') as f:
        im4p_data = f.read()

    unpacked = unpack_im4p(im4p_data)
    print(f"[+] Unpacked IM4P container:")
    print(f"    FourCC:          {unpacked['fourcc']}")
    print(f"    Version:         {unpacked['version']}")
    print(f"    Payload Offset:  {unpacked['payload_offset']} bytes")
    print(f"    Payload Size:    {unpacked['payload_len']} bytes")

    Path(output_macho).parent.mkdir(parents=True, exist_ok=True)
    with open(output_macho, 'wb') as f:
        f.write(unpacked["macho_bytes"])
    print(f"[+] Saved extracted 32-bit Mach-O binary to: {output_macho}")

    print(f"[*] Parsing Mach-O binary structures...")
    manifest = parse_macho(unpacked["macho_bytes"])
    
    # Check for recovery firmware (rmsr) and verify payload match
    rmsr_path = Path(msrf_path).parent / "t8150.rmsr.im4p"
    rmsr_meta = None
    if rmsr_path.exists():
        print(f"[*] Verifying recovery firmware container from: {rmsr_path}")
        with open(rmsr_path, 'rb') as f:
            rmsr_bytes = f.read()
        rmsr_unpacked = unpack_im4p(rmsr_bytes)
        payload_identical = (rmsr_unpacked["macho_bytes"] == unpacked["macho_bytes"])
        rmsr_meta = {
            "source_path": str(rmsr_path),
            "file_size_bytes": rmsr_unpacked["total_file_len"],
            "fourcc": rmsr_unpacked["fourcc"],
            "version": rmsr_unpacked["version"],
            "macho_offset": rmsr_unpacked["payload_offset"],
            "macho_size_bytes": rmsr_unpacked["payload_len"],
            "payload_identical_to_msrf": payload_identical
        }
        print(f"[+] Verified RMSR container: FourCC='{rmsr_unpacked['fourcc']}', payload identical to MSRF: {payload_identical}")

    # Enrich manifest with container details
    full_manifest = {
        "container": {
            "source_path": msrf_path,
            "file_size_bytes": unpacked["total_file_len"],
            "fourcc": unpacked["fourcc"],
            "version": unpacked["version"],
            "macho_offset": unpacked["payload_offset"],
            "macho_size_bytes": unpacked["payload_len"]
        },
        "recovery_container": rmsr_meta,
        "macho": manifest
    }

    with open(output_manifest, 'w') as f:
        json.dump(full_manifest, f, indent=2)
    print(f"[+] Generated Mach-O manifest to: {output_manifest}")

    print("\n[+] Extraction Summary:")
    print(f"    Mach-O Magic:    {manifest['header']['magic']} ({manifest['header']['magic_name']})")
    print(f"    CPU Architecture:{manifest['header']['cpusubtype_name']}")
    for seg in manifest["segments"]:
        print(f"    Segment {seg['segment_name']:12s}: vmaddr={seg['vmaddr']} vmsize={seg['vmsize']} fileoff={seg['fileoff']} filesize={seg['filesize']}")
        for s in seg["sections"]:
            print(f"      Section {s['section_name']:16s}: addr={s['addr']} size={s['size']} offset={s['offset']}")
    print(f"    Total Symbols:   {manifest['total_symbols']}")
    print(f"    Default Block List: {manifest['tables']['_DEFAULT_BLOCK_EN_LIST']['num_entries']} entries")
    print(f"    Max Tile Size:      {manifest['tables']['_MSR_MAX_TILE_SIZE']['dimensions_str']}")
    print(f"    TD Cache Mapping:   {manifest['tables']['_TD_CACHE_MAPPING']['mapping_table']}")

if __name__ == "__main__":
    main()
