#!/usr/bin/env python3
"""
tools/extract_centauri_ftab.py

Deterministic extractor and cataloger for Apple Centauri (t2026phoneG1 / Proxima) FTAB firmware.
Extracts all 78 primary partitions, nested 2ftb memory overlays, and _osl string database.
Outputs:
  - artifacts/centauri/firmware/partitions/*.bin
  - artifacts/centauri/firmware/ftab_manifest.json
  - artifacts/centauri/firmware/memory_overlay_map.json
  - artifacts/centauri/firmware/osl_string_database.json
"""

import os
import sys
import json
import struct
import hashlib
from pathlib import Path

DEFAULT_FTAB_PATH = Path("iPhone18,3_27.2_24B119_Restore/Firmware/t2026phoneG1/Release/ftab.bin")
DEFAULT_OUT_DIR = Path("artifacts/centauri/firmware")

FTAB_MAGIC = b"rkosftab"
HEADER_OFFSET_MAGIC = 0x20
HEADER_OFFSET_NUM_ENTRIES = 0x28
TABLE_START_OFFSET = 0x30
ENTRY_SIZE = 16

def extract_ftab(ftab_path: Path, out_dir: Path):
    if not ftab_path.exists():
        raise FileNotFoundError(f"FTAB file not found at: {ftab_path}")

    partitions_dir = out_dir / "partitions"
    partitions_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    file_size = ftab_path.stat().st_size

    with open(ftab_path, "rb") as f:
        # Read header prefix
        header_data = f.read(TABLE_START_OFFSET)
        magic = header_data[HEADER_OFFSET_MAGIC:HEADER_OFFSET_MAGIC + len(FTAB_MAGIC)]
        if magic != FTAB_MAGIC:
            raise ValueError(f"Invalid FTAB magic: {magic!r}, expected {FTAB_MAGIC!r}")

        num_entries = struct.unpack("<I", header_data[HEADER_OFFSET_NUM_ENTRIES:HEADER_OFFSET_NUM_ENTRIES + 4])[0]
        
        # Read partition table
        table_bytes = f.read(num_entries * ENTRY_SIZE)
        if len(table_bytes) != num_entries * ENTRY_SIZE:
            raise ValueError("Truncated FTAB partition table")

        entries = []
        for i in range(num_entries):
            chunk = table_bytes[i * ENTRY_SIZE : (i + 1) * ENTRY_SIZE]
            tag_raw = chunk[0:4]
            tag_str = tag_raw.decode("latin1", errors="replace")
            offset, size, flags = struct.unpack("<III", chunk[4:16])
            entries.append({
                "index": i,
                "tag": tag_str,
                "offset": offset,
                "size": size,
                "flags": flags
            })

        # Deterministically extract and hash each partition
        manifest_entries = []
        raw_partitions = {}
        for e in entries:
            f.seek(e["offset"])
            part_data = f.read(e["size"])
            if len(part_data) != e["size"]:
                raise IOError(f"Failed to read complete partition {e['tag']} at 0x{e['offset']:x}: expected {e['size']} bytes, got {len(part_data)}")

            raw_partitions[e["tag"]] = part_data
            sha256_hash = hashlib.sha256(part_data).hexdigest()

            safe_tag = "".join(c if c.isalnum() or c in ("_", "-") else f"_{ord(c):02x}" for c in e["tag"])
            filename = f"{e['index']:02d}_{safe_tag}.bin"
            file_path = partitions_dir / filename
            with open(file_path, "wb") as pf:
                pf.write(part_data)

            alias_path = partitions_dir / f"{safe_tag}.bin"
            if not alias_path.exists():
                with open(alias_path, "wb") as pf:
                    pf.write(part_data)

            manifest_entries.append({
                "index": e["index"],
                "tag": e["tag"],
                "offset_hex": f"0x{e['offset']:08x}",
                "offset_dec": e["offset"],
                "size_hex": f"0x{e['size']:08x}",
                "size_dec": e["size"],
                "flags_hex": f"0x{e['flags']:08x}",
                "flags_dec": e["flags"],
                "sha256": sha256_hash,
                "filename": filename,
                "relative_path": str(file_path.relative_to(out_dir.parent.parent))
            })

    manifest = {
        "ftab_path": str(ftab_path),
        "ftab_size": file_size,
        "magic": FTAB_MAGIC.decode("ascii"),
        "total_partitions": num_entries,
        "partitions": manifest_entries
    }

    manifest_file = out_dir / "ftab_manifest.json"
    with open(manifest_file, "w") as mf:
        json.dump(manifest, mf, indent=2)

    print(f"Successfully unpacked {num_entries} partitions to {partitions_dir}")
    print(f"Manifest written to {manifest_file}")

    # Process nested 2ftb partition
    if "2ftb" in raw_partitions:
        p2_data = raw_partitions["2ftb"]
        if len(p2_data) >= 0x30 and p2_data[0x20:0x28] == FTAB_MAGIC:
            p2_num = struct.unpack("<I", p2_data[0x28:0x2c])[0]
            p2_entries = []
            for i in range(p2_num):
                c = p2_data[0x30 + i * 16 : 0x30 + (i + 1) * 16]
                ptag = c[0:4].decode("latin1", errors="replace")
                poff, psz, pfl = struct.unpack("<III", c[4:16])
                p2_entries.append({
                    "index": i,
                    "tag": ptag,
                    "start_hex": f"0x{poff:08x}",
                    "start_dec": poff,
                    "end_hex": f"0x{poff+psz:08x}",
                    "end_dec": poff + psz,
                    "size_bytes": psz,
                    "size_kb": round(psz / 1024, 2),
                    "flags_hex": f"0x{pfl:08x}"
                })
            overlay_map = {
                "source": "2ftb (Partition 75)",
                "magic": "rkosftab",
                "total_segments": p2_num,
                "total_span_bytes": max(e["end_dec"] for e in p2_entries),
                "total_span_mb": round(max(e["end_dec"] for e in p2_entries) / (1024 * 1024), 2),
                "segments": p2_entries
            }
            overlay_file = out_dir / "memory_overlay_map.json"
            with open(overlay_file, "w") as of:
                json.dump(overlay_map, of, indent=2)
            print(f"Parsed 2ftb memory overlay map ({p2_num} segments) to {overlay_file}")

    # Process _osl strings and rkos xrefs
    if "_osl" in raw_partitions and "rkos" in raw_partitions:
        osl_data = raw_partitions["_osl"][0x40:]
        rkos_data = raw_partitions["rkos"]

        pc_refs = {}
        for pc in range(0, len(rkos_data) - 4, 4):
            word = struct.unpack("<I", rkos_data[pc:pc+4])[0]
            if (word & 0x9f000000) == 0x90000000:
                immlo = (word >> 29) & 3
                immhi = (word >> 5) & 0x7ffff
                imm = (immhi << 2) | immlo
                if imm & (1 << 20):
                    imm -= (1 << 21)
                page = (pc & ~0xfff) + (imm << 12)
                if page == 0x173000:
                    next_word = struct.unpack("<I", rkos_data[pc+4:pc+8])[0]
                    if (next_word & 0xff800000) == 0x91000000:
                        add_imm = (next_word >> 10) & 0xfff
                        if add_imm not in pc_refs:
                            pc_refs[add_imm] = []
                        pc_refs[add_imm].append(f"0x{pc:05x}")

        raw_strings = osl_data.split(b"\x00")
        osl_records = []
        off = 0
        idx = 0
        for s in raw_strings:
            if len(s) > 0:
                str_text = s.decode("latin1", errors="replace")
                va = 0x173000 + off
                refs = pc_refs.get(off, [])
                
                cat = "General"
                low = str_text.lower()
                if any(k in low for k in ["crash", "panic", "fault"]): cat = "Crash & Diagnostics"
                elif any(k in low for k in ["acipc", "pcie", "ptm", "gtb", "link", "doorbell"]): cat = "ACIPC & PCIe"
                elif any(k in low for k in ["sram", "heap", "mem", "alloc", "swap"]): cat = "Memory & Heap"
                elif any(k in low for k in ["regu", "power", "sar", "eirp", "table", "pcal", "fem", "sku", "hw id"]): cat = "Regulatory & RF Power"
                elif any(k in low for k in ["boot", "rks", "init", "shell"]): cat = "Boot & Early Init"
                elif any(k in low for k in ["wifi", "wlan", "lmac", "umac"]): cat = "Wi-Fi Subsystem"
                elif any(k in low for k in ["bt", "bluetooth", "lpm"]): cat = "Bluetooth Subsystem"

                osl_records.append({
                    "index": idx,
                    "offset_hex": f"0x{off:04x}",
                    "offset_dec": off,
                    "virtual_address": f"0x{va:06x}",
                    "rkos_pc_xrefs": refs,
                    "category": cat,
                    "text": str_text
                })
                idx += 1
            off += len(s) + 1

        osl_db = {
            "source": "_osl (Partition 76)",
            "virtual_base_address": "0x173000",
            "total_strings": len(osl_records),
            "referenced_in_rkos": sum(1 for r in osl_records if len(r["rkos_pc_xrefs"]) > 0),
            "strings": osl_records
        }
        osl_db_file = out_dir / "osl_string_database.json"
        with open(osl_db_file, "w") as sf:
            json.dump(osl_db, sf, indent=2)
        print(f"Extracted _osl string database ({len(osl_records)} strings) to {osl_db_file}")

if __name__ == "__main__":
    ftab_input = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FTAB_PATH
    out_dir_input = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    extract_ftab(ftab_input, out_dir_input)
