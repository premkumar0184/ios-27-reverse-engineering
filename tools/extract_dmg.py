#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: APFS DMG Extractor
Extracts files, bundles, and directories from decrypted APFS disk images using 7z.
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def list_dmg_contents(dmg_path: Path, filter_pattern: str = None) -> list:
    """Lists files in the DMG, optionally filtering by pattern."""
    cmd = ["7z", "l", str(dmg_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 7z failed to list {dmg_path}: {result.stderr}")
        return []

    lines = result.stdout.splitlines()
    files = []
    header_passed = False
    for line in lines:
        if line.startswith("-------------------"):
            header_passed = not header_passed
            continue
        if header_passed and len(line) > 53:
            # 7z output format: Date Time Attr Size Compressed Name
            name = line[53:].strip()
            if filter_pattern is None or filter_pattern.lower() in name.lower():
                files.append(name)
    return files

def extract_from_dmg(dmg_path: Path, target_pattern: str, output_dir: Path) -> bool:
    """Extracts files matching target_pattern into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Extracting '{target_pattern}' from {dmg_path.name} into {output_dir}...")
    
    cmd = ["7z", "x", str(dmg_path), f"-o{output_dir}", target_pattern, "-r", "-y"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 7z extraction failed: {result.stderr}")
        return False
        
    print(f"[+] Successfully extracted '{target_pattern}' to {output_dir}")
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python3 tools/extract_dmg.py list <image.dmg> [filter_substring]")
        print("  python3 tools/extract_dmg.py extract <image.dmg> <pattern> <output_dir>")
        print("\nExamples:")
        print("  python3 tools/extract_dmg.py extract artifacts/crypto/141-08876-216_rootfs.dmg System/Library/CoreServices/SpringBoard.app/* artifacts/ui/SpringBoard/")
        print("  python3 tools/extract_dmg.py extract artifacts/crypto/141-08876-216_rootfs.dmg *.car artifacts/ui/assets/")
        print("  python3 tools/extract_dmg.py extract artifacts/crypto/141-09724-226_cryptex_systemos.dmg *dyld_shared_cache* artifacts/rootfs/shared_cache/")
        sys.exit(1)

    action = sys.argv[1].lower()
    dmg_path = Path(sys.argv[2])

    if not dmg_path.is_file():
        print(f"[ERROR] DMG file not found at {dmg_path}")
        sys.exit(1)

    if action == "list":
        filter_str = sys.argv[3] if len(sys.argv) > 3 else None
        files = list_dmg_contents(dmg_path, filter_str)
        print(f"Found {len(files)} files matching filter '{filter_str}':")
        for f in files[:100]:
            print(f"  {f}")
        if len(files) > 100:
            print(f"  ... and {len(files) - 100} more files.")
    elif action == "extract":
        if len(sys.argv) < 5:
            print("Error: extract requires <pattern> and <output_dir>")
            sys.exit(1)
        pattern = sys.argv[3]
        out_dir = Path(sys.argv[4])
        success = extract_from_dmg(dmg_path, pattern, out_dir)
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
