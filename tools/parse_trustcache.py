#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Apple TrustCache Parser (Hardened & Enhanced)
Parses Apple TrustCache files wrapped in IM4P containers or raw binaries.
Extracts TrustCache version (v1/v2), UUID, entry counts, CDHashes, flags, and constraint categories.
Preserves top-level array structure required by tools/verify_phase.py.
"""

import sys
import os
import json
import struct
import uuid
from pathlib import Path

# Ensure tools directory is on sys.path for parse_im4p import
tools_dir = Path(__file__).resolve().parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from parse_im4p import read_asn1_length

def parse_trustcache_payload(payload: bytes) -> dict:
    result = {
        "format": "unknown",
        "version": None,
        "uuid": None,
        "entry_count": 0,
        "hash_type": "unknown",
        "is_sorted": True,
        "entries": []
    }

    if len(payload) < 24:
        return result

    # Apple TrustCache header:
    # uint32_t version (little-endian)
    # uint8_t uuid[16]
    # uint32_t num_entries (little-endian)
    version, = struct.unpack_from("<I", payload, 0)
    tc_uuid = uuid.UUID(bytes=payload[4:20])
    num_entries, = struct.unpack_from("<I", payload, 20)

    result["version"] = version
    result["uuid"] = str(tc_uuid)
    result["entry_count"] = num_entries

    offset = 24
    last_cdhash = None
    all_hash_types = set()

    if version == 1:
        # v1 entry: 20-byte cdhash, uint8_t hash_type, uint8_t flags (22 bytes)
        entry_size = 22
        result["format"] = "Apple TrustCache v1"
        for _ in range(num_entries):
            if offset + entry_size > len(payload):
                break
            raw_cdhash = payload[offset:offset+20]
            if last_cdhash is not None and raw_cdhash < last_cdhash:
                result["is_sorted"] = False
            last_cdhash = raw_cdhash

            cdhash = raw_cdhash.hex()
            h_type, flags = struct.unpack_from("<BB", payload, offset+20)
            all_hash_types.add(h_type)
            result["entries"].append({
                "cdhash": cdhash,
                "hash_type": h_type,
                "flags": flags
            })
            offset += entry_size

    elif version == 2:
        # v2 entry: 20-byte cdhash, uint8_t hash_type, uint8_t flags, uint8_t constraintCategory, uint8_t reserved0 (24 bytes)
        entry_size = 24
        result["format"] = "Apple TrustCache v2"
        for _ in range(num_entries):
            if offset + entry_size > len(payload):
                break
            raw_cdhash = payload[offset:offset+20]
            if last_cdhash is not None and raw_cdhash < last_cdhash:
                result["is_sorted"] = False
            last_cdhash = raw_cdhash

            cdhash = raw_cdhash.hex()
            h_type, flags, cat, res0 = struct.unpack_from("<BBBB", payload, offset+20)
            all_hash_types.add(h_type)
            result["entries"].append({
                "cdhash": cdhash,
                "hash_type": h_type,
                "flags": flags,
                "category": cat,
                "reserved0": res0
            })
            offset += entry_size
    else:
        result["format"] = f"Unknown TrustCache version {version}"

    if all_hash_types == {2}:
        result["hash_type"] = "SHA-256 (type 2)"
    elif all_hash_types:
        result["hash_type"] = f"Mixed ({sorted(list(all_hash_types))})"

    return result

def parse_trustcache_file(tc_path: Path) -> dict:
    with open(tc_path, "rb") as f:
        data = f.read()

    # If wrapped in IM4P ASN.1 DER container
    if data.startswith(b"\x30") and b"IM4P" in data[:32]:
        seq_len, offset = read_asn1_length(data, 1)
        # Advance through IM4P header to payload
        offset += 1
        m_len, offset = read_asn1_length(data, offset)
        offset += m_len  # skip IM4P magic
        tag_4cc = "unknown"
        if data[offset] == 0x16:
            offset += 1
            t_len, offset = read_asn1_length(data, offset)
            tag_4cc = data[offset:offset+t_len].decode("ascii", errors="replace")
            offset += t_len  # skip 4CC tag (trca, trst, extc, rtsc, trcs)
        if data[offset] == 0x16:
            offset += 1
            d_len, offset = read_asn1_length(data, offset)
            desc_val = data[offset:offset+d_len].decode("ascii", errors="replace")
            offset += d_len  # skip desc
        if data[offset] == 0x04:
            offset += 1
            p_len, offset = read_asn1_length(data, offset)
            payload = data[offset:offset+p_len]
            parsed = parse_trustcache_payload(payload)
            parsed["container"] = f"IM4P ({tag_4cc})"
            parsed["im4p_tag"] = tag_4cc
            parsed["file"] = tc_path.name
            return parsed

    # Raw payload fallback
    parsed = parse_trustcache_payload(data)
    parsed["container"] = "raw"
    parsed["im4p_tag"] = None
    parsed["file"] = tc_path.name
    return parsed

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/parse_trustcache.py <path_or_dir> [output_dir]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("artifacts/security")
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog = []
    if input_path.is_file():
        res = parse_trustcache_file(input_path)
        catalog.append(res)
    elif input_path.is_dir():
        # Handle case where user passes restore root instead of Firmware/
        if (input_path / "Firmware").is_dir():
            search_dir = input_path / "Firmware"
        else:
            search_dir = input_path

        tc_files = sorted(search_dir.glob("*.trustcache"))
        for tc_file in tc_files:
            print(f"[*] Parsing {tc_file.name}...")
            res = parse_trustcache_file(tc_file)
            catalog.append(res)

    out_file = output_dir / "trustcache_catalog.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"[+] Wrote TrustCache catalog ({len(catalog)} files, {sum(c['entry_count'] for c in catalog)} entries) to {out_file}")

if __name__ == "__main__":
    main()
