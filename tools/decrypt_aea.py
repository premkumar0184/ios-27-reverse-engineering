#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Apple Encrypted Archive (AEA) Decryptor
Decrypts AEA profile 1 archives (RootFS, Cryptex1 SystemOS, ExclaveOS, RecoveryOS)
using verified 256-bit symmetric keys.
"""

import sys
import os
import base64
import time
from pathlib import Path

# Ensure venv site-packages is in sys.path
for venv_path in [
    Path("/home/prem/.venv/lib/python3.14/site-packages"),
    Path.home() / ".venv/lib/python3.14/site-packages"
]:
    if venv_path.is_dir() and str(venv_path) not in sys.path:
        sys.path.insert(0, str(venv_path))

try:
    import aea
except ImportError:
    print("[ERROR] python-aea library not found. Run: uv pip install python-aea")
    sys.exit(1)

# Verified Symmetric Keys for iOS 27.2 (24B119 - iPhone18,3 - RaveB)
VERIFIED_KEYS = {
    "141-08876-216.dmg.aea": {
        "role": "Root Filesystem (OS / SpringBoard / Frameworks)",
        "key_base64": "+y/m7vi8ar9XDoVgVLca+mto3RGEBzqPorAG9EQdogE=",
        "output_filename": "141-08876-216_rootfs.dmg"
    },
    "141-09724-226.dmg.aea": {
        "role": "Cryptex1,SystemOS (dyld_shared_cache)",
        "key_base64": "SN6iJqVqGATlCB0o2OKLkLF46DoneTg84htO/STd0FI=",
        "output_filename": "141-09724-226_cryptex_systemos.dmg"
    },
    "141-08904-238.dmg.aea": {
        "role": "Ap,ExclaveOS (Exclave Microkernel Root)",
        "key_base64": "0H82ALGVVzn/LVRYcag866+uoQeqst6xfa1VkxEJIdY=",
        "output_filename": "141-08904-238_exclaveos.dmg"
    },
    "141-09644-240.dmg.aea": {
        "role": "RecoveryOS / Update OS",
        "key_base64": "68Paat8a7qgbIe43Yju1uUI1TN2ZmeTnATD8Ah0LeUA=",
        "output_filename": "141-09644-240_recoveryos.dmg"
    }
}

def verify_key(aea_path: Path, key_bytes: bytes) -> dict:
    """Verifies a key against an AEA header by validating MAC authentication."""
    with open(aea_path, "rb") as f:
        header_sample = f.read(4096)
    
    import io
    inp = io.BytesIO(header_sample)
    hdr = aea.FileHeader()
    hdr.decode(inp.read(12))
    auth_data = inp.read(hdr.auth_data_size)
    sig_start = inp.tell()
    sig = inp.read(aea.SignatureSize[hdr.profile_id])
    sig_end = inp.tell()
    pub_key = inp.read(aea.PublicKeySize[hdr.profile_id])
    main_salt = inp.read(32)
    root_header_mac = inp.read(32)
    root_header_data = inp.read(48)
    cluster_mac = inp.read(32)

    main_key = aea.derive_main_key(
        hdr.profile_id, hdr.scrypt_strength, None, None,
        None, key_bytes, main_salt
    )
    kd = aea.KeyDerivation(main_key, aea.KeySize[hdr.profile_id])
    root_header_key = kd.root_header_key()
    root_header_salt = cluster_mac + auth_data
    decrypted_rh = aea.decrypt_and_verify(
        root_header_key, root_header_data, root_header_salt, root_header_mac
    )
    rh = aea.RootHeader()
    rh.decode(decrypted_rh)
    
    comp_name = aea.CompressionAlgorithm(rh.compression_algorithm).name
    return {
        "verified": True,
        "profile_id": hdr.profile_id,
        "original_size": rh.original_size,
        "compression": comp_name
    }

def decrypt_aea_file(input_path: Path, output_path: Path, key_bytes: bytes):
    """Decrypts an AEA file streaming to output_path."""
    print(f"[*] Decrypting {input_path.name} -> {output_path.name}...")
    t0 = time.time()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(input_path, "rb") as in_f, open(output_path, "wb") as out_f:
        aea.decode_stream(in_f, out_f, symmetric_key=key_bytes)
        
    elapsed = round(time.time() - t0, 2)
    out_size = output_path.stat().st_size
    print(f"[+] Decryption complete in {elapsed}s! Wrote {out_size} bytes ({round(out_size/(1024*1024), 2)} MB).")

def main():
    project_root = Path(__file__).resolve().parent.parent
    restore_dir = project_root / "iPhone18,3_27.2_24B119_Restore"
    output_dir = project_root / "artifacts" / "crypto"

    if len(sys.argv) > 1 and sys.argv[1] == "--verify-only":
        print("=== VERIFYING AEA SYMMETRIC KEYS ===")
        for fname, info in VERIFIED_KEYS.items():
            aea_file = restore_dir / fname
            if not aea_file.is_file():
                print(f"[!] File not found: {fname}")
                continue
            key_bytes = base64.b64decode(info["key_base64"])
            try:
                res = verify_key(aea_file, key_bytes)
                print(f"[+] {fname} ({info['role']}):")
                print(f"    STATUS: UNLOCKED! Original Size: {round(res['original_size']/(1024*1024*1024), 2)} GB (Compression: {res['compression']})")
            except Exception as e:
                print(f"[-] {fname}: FAILED verification ({e})")
        return

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 tools/decrypt_aea.py --verify-only")
        print("  python3 tools/decrypt_aea.py <input.aea> [output.dmg] [key_base64]")
        print("  python3 tools/decrypt_aea.py --all-crypto")
        sys.exit(0)

    # Specific file decryption
    in_file = Path(sys.argv[1])
    if in_file.name in VERIFIED_KEYS and len(sys.argv) == 2:
        info = VERIFIED_KEYS[in_file.name]
        out_file = output_dir / info["output_filename"]
        key_bytes = base64.b64decode(info["key_base64"])
    elif len(sys.argv) >= 3:
        out_file = Path(sys.argv[2])
        if len(sys.argv) >= 4:
            key_bytes = base64.b64decode(sys.argv[3])
        elif in_file.name in VERIFIED_KEYS:
            key_bytes = base64.b64decode(VERIFIED_KEYS[in_file.name]["key_base64"])
        else:
            print(f"[ERROR] No key provided for {in_file.name}")
            sys.exit(1)
    else:
        print(f"[ERROR] Unknown file {in_file.name}. Provide output path and key.")
        sys.exit(1)

    decrypt_aea_file(in_file, out_file, key_bytes)

if __name__ == "__main__":
    main()
