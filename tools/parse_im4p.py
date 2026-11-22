#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Apple Image4 (IM4P) Payload Extractor (Hardened)
Parses ASN.1 DER structures, identifies compression formats (LZFSE/bvx2, complzss, raw Mach-O),
recognizes APFS container superblocks (NXSB) inside rdsk payloads, unpacks BUND (ExclaveCore)
sub-binaries, and deterministically extracts payloads to disk.
"""

import sys
import os
import struct
import json
from pathlib import Path

# Ensure virtualenv site-packages is in sys.path
for venv_path in [
    Path("/home/prem/.venv/lib/python3.14/site-packages"),
    Path.home() / ".venv/lib/python3.14/site-packages"
]:
    if venv_path.is_dir() and str(venv_path) not in sys.path:
        sys.path.insert(0, str(venv_path))

LZFSE_AVAILABLE = False
try:
    import lzfse
    LZFSE_AVAILABLE = True
except ImportError:
    pass

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

def unpack_bund(data: bytes, output_dir: Path) -> list:
    """
    Unpacks Apple BUND ('DNUB') multi-binary container (used in ExclaveCore bundles).
    Identifies all embedded Mach-O 64-bit binaries and extracts them with exact load-command sizes.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    idx = data.find(b'DNUB')
    if idx == -1:
        return []

    extracted_items = []
    import re
    macho_offsets = [m.start() for m in re.finditer(b"\xcf\xfa\xed\xfe", data)]

    well_known_names = [
        "00_tightbeam_runtime.macho",
        "01_pmm_server.macho",
        "02_vascore_platform.macho",
        "03_jg_sharedmem_preload.macho"
    ]

    for i, off in enumerate(macho_offsets):
        macho = data[off:]
        if len(macho) < 32:
            continue
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', macho[:32])
        p = 32
        max_fileoff = 0
        for _ in range(ncmds):
            if p + 8 > len(macho):
                break
            cmd, cmdsize = struct.unpack_from('<II', macho, p)
            if cmd == 0x19 and p + 56 <= len(macho): # LC_SEGMENT_64
                vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', macho, p+24)
                if fileoff + filesize > max_fileoff:
                    max_fileoff = fileoff + filesize
            elif cmd == 0x1d and p + 16 <= len(macho): # LC_CODE_SIGNATURE
                dataoff, datasize = struct.unpack_from('<II', macho, p+8)
                if dataoff + datasize > max_fileoff:
                    max_fileoff = dataoff + datasize
            p += cmdsize
        if max_fileoff == 0:
            max_fileoff = min(len(macho), 1024 * 1024)

        name = well_known_names[i] if i < len(well_known_names) else f"sub_binary_{i:02d}.macho"
        out_file = output_dir / name
        sub_data = data[off:off+max_fileoff]
        with open(out_file, "wb") as f_out:
            f_out.write(sub_data)

        extracted_items.append({
            "name": name,
            "offset": off,
            "size": len(sub_data),
            "filetype": filetype,
            "file": str(out_file)
        })

    return extracted_items

def parse_im4p(im4p_path: Path, output_raw_path: Path = None) -> dict:
    with open(im4p_path, "rb") as f:
        data = f.read()

    metadata = {
        "source_file": str(im4p_path),
        "total_file_size": len(data),
        "is_valid_im4p": False,
        "magic": None,
        "type": None,
        "description": None,
        "payload_length_encoded": 0,
        "compression": "unknown",
        "format_identified": "unknown",
        "decompressed_size": 0,
        "output_extracted_file": None,
        "bund_entries": []
    }

    if not data or data[0] != 0x30:
        return metadata

    seq_len, offset = read_asn1_length(data, 1)

    # Tag 1: IA5String 'IM4P'
    if offset >= len(data) or data[offset] != 0x16:
        return metadata
    offset += 1
    magic_len, offset = read_asn1_length(data, offset)
    magic = data[offset:offset+magic_len].decode("ascii", errors="replace")
    offset += magic_len
    metadata["magic"] = magic

    if magic != "IM4P":
        return metadata
    metadata["is_valid_im4p"] = True

    # Tag 2: IA5String Type
    if offset < len(data) and data[offset] == 0x16:
        offset += 1
        type_len, offset = read_asn1_length(data, offset)
        metadata["type"] = data[offset:offset+type_len].decode("ascii", errors="replace")
        offset += type_len

    # Tag 3: IA5String Description
    if offset < len(data) and data[offset] == 0x16:
        offset += 1
        desc_len, offset = read_asn1_length(data, offset)
        metadata["description"] = data[offset:offset+desc_len].decode("ascii", errors="replace")
        offset += desc_len

    # Tag 4: Octet String (Payload)
    if offset < len(data) and data[offset] == 0x04:
        offset += 1
        payload_len, offset = read_asn1_length(data, offset)
        payload = data[offset:offset+payload_len]
        metadata["payload_length_encoded"] = len(payload)

        # 1. Check for LZFSE
        if payload.startswith(b"bvx2"):
            metadata["compression"] = "lzfse"
            if LZFSE_AVAILABLE:
                try:
                    decompressed = lzfse.decompress(payload)
                    metadata["decompressed_size"] = len(decompressed)
                    out_data = decompressed
                    if decompressed.startswith(b"\xcf\xfa\xed\xfe"):
                        metadata["format_identified"] = "Mach-O 64-bit (MH_MAGIC_64)"
                    else:
                        metadata["format_identified"] = "Decompressed Binary"
                except Exception as e:
                    print(f"[!] LZFSE decompression error: {e}")
                    out_data = payload
            else:
                out_data = payload

        # 2. Check for APFS Superblock (NXSB) at offset 32 (standard for rdsk)
        elif len(payload) > 36 and payload[32:36] == b"NXSB":
            metadata["compression"] = "none (uncompressed)"
            metadata["format_identified"] = "Apple File System (APFS) Disk Image"
            metadata["decompressed_size"] = len(payload)
            out_data = payload

        # 3. Check for Apple BUNDLE (DNUB) Container
        elif b"DNUB" in payload[:64]:
            metadata["compression"] = "none (container)"
            metadata["format_identified"] = "Apple BUNDLE (ExclaveCore Archive)"
            metadata["decompressed_size"] = len(payload)
            out_data = payload
            if output_raw_path:
                bund_dir = output_raw_path.parent / f"{output_raw_path.stem}_unpacked"
                metadata["bund_entries"] = unpack_bund(payload, bund_dir)

        # 4. Check for LZSS
        elif payload.startswith(b"complzss"):
            metadata["compression"] = "lzss"
            metadata["format_identified"] = "Apple LZSS Compressed Stream"
            out_data = payload

        # 5. Check for raw Mach-O
        elif payload.startswith(b"\xcf\xfa\xed\xfe"):
            metadata["compression"] = "none"
            metadata["format_identified"] = "Mach-O 64-bit (MH_MAGIC_64)"
            metadata["decompressed_size"] = len(payload)
            out_data = payload
        else:
            metadata["compression"] = "raw"
            metadata["format_identified"] = f"Raw Binary (Magic: {payload[:4].hex()})"
            metadata["decompressed_size"] = len(payload)
            out_data = payload

        if output_raw_path:
            output_raw_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_raw_path, "wb") as out_f:
                out_f.write(out_data)
            metadata["output_extracted_file"] = str(output_raw_path)
            print(f"[+] Extracted {metadata['format_identified']} ({len(out_data)} bytes) to {output_raw_path}")

    return metadata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/parse_im4p.py <input.im4p> [output_payload.raw]")
        sys.exit(1)

    in_file = Path(sys.argv[1])
    out_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    meta = parse_im4p(in_file, out_file)
    print(json.dumps(meta, indent=2))
