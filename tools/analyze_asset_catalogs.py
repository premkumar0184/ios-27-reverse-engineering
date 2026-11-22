#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Asset Catalog Decoder & Inventory
Parses compiled CoreUI Asset Catalogs (Assets.car) via BOMStore structures,
CARHEADER, stream descriptors, and extracted icon/rendition metadata.
"""

import sys
import os
import re
import struct
import json
from pathlib import Path

def parse_car_file(car_path: Path) -> dict:
    with open(car_path, "rb") as f:
        file_size = car_path.stat().st_size
        raw_data = f.read()

    if len(raw_data) < 32 or raw_data[:8] != b'BOMStore':
        return {"error": "Not a valid BOMStore file"}

    # Parse BOM Header
    magic = raw_data[:8].decode('ascii', errors='ignore')
    version, num_paths, index_off, index_len, vars_off, vars_len = struct.unpack('>IIIIII', raw_data[8:32])

    # Parse Variables Table
    vars_dict = {}
    if vars_off + vars_len <= len(raw_data):
        vdata = raw_data[vars_off:vars_off+vars_len]
        if len(vdata) >= 4:
            count = struct.unpack('>I', vdata[:4])[0]
            v_offset = 4
            for _ in range(count):
                if v_offset + 5 > len(vdata):
                    break
                idx, nlen = struct.unpack('>IB', vdata[v_offset:v_offset+5])
                vname = vdata[v_offset+5:v_offset+5+nlen].decode('ascii', errors='ignore')
                vars_dict[vname] = idx
                v_offset += 5 + nlen

    # Parse Block Table
    blocks = []
    if index_off + index_len <= len(raw_data):
        bdata = raw_data[index_off:index_off+index_len]
        if len(bdata) >= 4:
            num_blocks = struct.unpack('>I', bdata[:4])[0]
            for i in range(num_blocks):
                if 4 + (i+1)*8 > len(bdata):
                    break
                b_addr, b_len = struct.unpack('>II', bdata[4+i*8:4+(i+1)*8])
                blocks.append((b_addr, b_len))

    # Parse CARHEADER
    car_header_info = {}
    carheader_block_idx = vars_dict.get("CARHEADER")
    if carheader_block_idx is not None and carheader_block_idx < len(blocks):
        b_addr, b_len = blocks[carheader_block_idx]
        if b_addr + b_len <= len(raw_data) and b_len >= 28:
            chdr = raw_data[b_addr:b_addr+b_len]
            tag, coreui_ver, storage_ver, storage_flags, rend_count = struct.unpack('<IIIII', chdr[:20])
            tag_str = struct.pack('<I', tag).decode('ascii', errors='ignore')
            creator = chdr[28:156].split(b'\x00')[0].decode('utf-8', errors='ignore')
            car_header_info = {
                "tag": tag_str,
                "coreui_version": coreui_ver,
                "storage_version": storage_ver,
                "storage_flags": f"0x{storage_flags:x}",
                "renditions_count": rend_count,
                "creator": creator
            }

    # Extract Asset and Rendition Names from BOM Data
    # Scan for recognizable asset filenames and symbols
    strings = set(re.findall(rb'[a-zA-Z0-9_\-\.]{4,60}', raw_data))
    filtered_assets = []
    for s in strings:
        s_str = s.decode('ascii', errors='ignore')
        if any(term in s_str.lower() for term in [
            'icon', 'glyph', 'button', 'widget', 'home', 'lock', 'camera',
            'safari', 'messages', 'health', 'wallet', 'pass', 'card',
            'appearance', 'tintable', 'dark', 'stack', 'symbol', 'badge'
        ]):
            filtered_assets.append(s_str)

    filtered_assets = sorted(list(set(filtered_assets)))

    # Appearance mode classification
    appearances = {
        "has_dark_mode_variants": any("dark" in a.lower() for a in filtered_assets),
        "has_tintable_variants": any("tintable" in a.lower() for a in filtered_assets),
        "has_icon_stacks": any("stack" in a.lower() for a in filtered_assets),
        "has_sf_symbols": any("symbol" in a.lower() or "glyph" in a.lower() for a in filtered_assets)
    }

    return {
        "catalog_path": str(car_path),
        "file_size": file_size,
        "bom_storage": {
            "magic": magic,
            "version": version,
            "num_paths": num_paths,
            "total_blocks": len(blocks),
            "stream_variables": vars_dict
        },
        "car_header": car_header_info,
        "appearance_features": appearances,
        "sample_renditions_and_assets": filtered_assets[:40],
        "total_extracted_named_assets": len(filtered_assets)
    }

def main():
    target_cars = sorted(list(Path("artifacts/ui").rglob("Assets.car")))
    print(f"[*] Dynamically detected and analyzing {len(target_cars)} Asset Catalogs across UI artifacts...")
    catalogs = []
    for car in target_cars:
        if car.is_file():
            print(f"    - Parsing {car.relative_to(Path('artifacts/ui'))} ({car.stat().st_size} bytes)...")
            entry = parse_car_file(car)
            catalogs.append(entry)

    out_file = Path("artifacts/ui/asset_catalog_inventory.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(catalogs, f, indent=2)

    print(f"[+] Successfully wrote {out_file} ({out_file.stat().st_size} bytes)")
    print(f"    - Cataloged {len(catalogs)} CoreUI Asset Catalogs.")

if __name__ == "__main__":
    main()
