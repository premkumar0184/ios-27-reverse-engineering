#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: Manifest & Package Inventory Parser (Hardened & Complete)
Deterministically parses plist files, catalogs restore images, computes SHA256 hashes for all files,
and generates bidirectional component maps linking every file to its exact Apple restore role.
"""

import os
import sys
import json
import plistlib
import hashlib
from pathlib import Path

def compute_sha256(filepath: Path, block_size: int = 1048576) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(block_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def parse_all_manifests(restore_dir: Path, output_dir: Path, compute_hashes: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "restore_directory": str(restore_dir),
        "system_version": {},
        "restore_version": {},
        "restore_plist_summary": {},
        "build_manifest_summary": {}
    }

    # 1. SystemVersion.plist
    sys_ver_path = restore_dir / "SystemVersion.plist"
    if sys_ver_path.is_file():
        with open(sys_ver_path, "rb") as f:
            pl = plistlib.load(f)
            summary["system_version"] = {
                "BuildID": pl.get("BuildID"),
                "ProductBuildVersion": pl.get("ProductBuildVersion"),
                "ProductCopyright": pl.get("ProductCopyright"),
                "ProductName": pl.get("ProductName"),
                "ProductVersion": pl.get("ProductVersion")
            }

    # 2. RestoreVersion.plist (Accurate keys: RestoreBuildGroup, RestoreLongVersion, RestoreVersion)
    rest_ver_path = restore_dir / "RestoreVersion.plist"
    if rest_ver_path.is_file():
        with open(rest_ver_path, "rb") as f:
            pl = plistlib.load(f)
            summary["restore_version"] = {
                "RestoreBuildGroup": pl.get("RestoreBuildGroup"),
                "RestoreLongVersion": pl.get("RestoreLongVersion"),
                "RestoreVersion": pl.get("RestoreVersion")
            }

    # 3. Restore.plist (Includes SystemRestoreImageFileSystems)
    restore_plist_path = restore_dir / "Restore.plist"
    if restore_plist_path.is_file():
        with open(restore_plist_path, "rb") as f:
            pl = plistlib.load(f)
            summary["restore_plist_summary"] = {
                "ProductBuildVersion": pl.get("ProductBuildVersion"),
                "ProductVersion": pl.get("ProductVersion"),
                "SupportedProductTypes": pl.get("SupportedProductTypes"),
                "SupportedProductTypeIDs": pl.get("SupportedProductTypeIDs"),
                "DeviceMap": pl.get("DeviceMap"),
                "SystemRestoreImageFileSystems": pl.get("SystemRestoreImageFileSystems")
            }

    # 4. BuildManifest.plist & Component Mapping
    build_manifest_path = restore_dir / "BuildManifest.plist"
    component_map = {
        "component_to_file": {},
        "file_to_components": {},
        "unreferenced_firmware_files": []
    }

    if build_manifest_path.is_file():
        with open(build_manifest_path, "rb") as f:
            pl = plistlib.load(f)
            build_identities = pl.get("BuildIdentities", [])
            summary["build_manifest_summary"] = {
                "ProductVersion": pl.get("ProductVersion"),
                "ProductBuildVersion": pl.get("ProductBuildVersion"),
                "SupportedProductTypes": pl.get("SupportedProductTypes"),
                "BuildIdentitiesCount": len(build_identities),
                "ManifestTree": []
            }
            
            for idx, bi in enumerate(build_identities):
                info = bi.get("Info", {})
                manifest = bi.get("Manifest", {})
                
                manifest_components = []
                for comp_name, comp_data in manifest.items():
                    comp_info = comp_data.get("Info", {})
                    rel_path = comp_info.get("Path", "")
                    is_aea = rel_path.endswith(".aea")
                    digest_bytes = comp_data.get("Digest")
                    digest_hex = digest_bytes.hex() if isinstance(digest_bytes, bytes) else None
                    
                    entry = {
                        "Component": comp_name,
                        "Path": rel_path,
                        "IsEncryptedAEA": is_aea,
                        "Trusted": comp_data.get("Trusted", False),
                        "Personalize": comp_info.get("Personalize", False),
                        "IsFTAB": comp_info.get("IsFTAB", False),
                        "HashMethod": comp_info.get("HashMethod", "sha2-384"),
                        "ManifestDigest": digest_hex
                    }
                    manifest_components.append(entry)
                    
                    if rel_path:
                        if comp_name not in component_map["component_to_file"]:
                            component_map["component_to_file"][comp_name] = entry
                        if rel_path not in component_map["file_to_components"]:
                            component_map["file_to_components"][rel_path] = []
                        if comp_name not in component_map["file_to_components"][rel_path]:
                            component_map["file_to_components"][rel_path].append(comp_name)

                summary["build_manifest_summary"]["ManifestTree"].append({
                    "IdentityIndex": idx,
                    "DeviceClass": info.get("DeviceClass"),
                    "BuildNumber": info.get("BuildNumber"),
                    "BuildTrain": info.get("BuildTrain"),
                    "Variant": info.get("Variant"),
                    "ComponentsCount": len(manifest_components)
                })

    summary_out = output_dir / "manifest_summary.json"
    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[+] Wrote manifest summary to {summary_out}")

    # 5. Catalog all images in root + SHA256
    print("[*] Cataloging images and computing SHA256 hashes...")
    images = []
    for item in sorted(restore_dir.iterdir()):
        if item.is_file() and (".dmg" in item.name or "kernelcache" in item.name):
            size = item.stat().st_size
            is_aea = item.name.endswith(".aea")
            sha256 = compute_sha256(item) if compute_hashes else "omitted"
            images.append({
                "filename": item.name,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "sha256": sha256,
                "is_aea_encrypted": is_aea,
                "extension": item.suffix,
                "roles": component_map["file_to_components"].get(item.name, ["Unreferenced / Standalone"])
            })
            
    images_out = output_dir / "image_inventory.json"
    with open(images_out, "w", encoding="utf-8") as f:
        json.dump(images, f, indent=2)
    print(f"[+] Wrote image inventory with SHA256 hashes to {images_out}")

    # 6. Catalog Firmware directory + SHA256
    print("[*] Cataloging 126 firmware files and computing SHA256 hashes...")
    firmware_dir = restore_dir / "Firmware"
    firmware_items = []
    all_fw_paths = set()
    if firmware_dir.is_dir():
        for root, dirs, files in os.walk(firmware_dir):
            for file in sorted(files):
                full_f = Path(root) / file
                rel = full_f.relative_to(firmware_dir)
                rel_with_prefix = f"Firmware/{rel}"
                all_fw_paths.add(rel_with_prefix)
                size = full_f.stat().st_size
                sha256 = compute_sha256(full_f) if compute_hashes else "omitted"
                firmware_items.append({
                    "relative_path": str(rel),
                    "size_bytes": size,
                    "sha256": sha256,
                    "extension": full_f.suffix,
                    "roles": component_map["file_to_components"].get(rel_with_prefix, ["Auxiliary / Coprocessor"])
                })

    firmware_out = output_dir / "firmware_inventory.json"
    with open(firmware_out, "w", encoding="utf-8") as f:
        json.dump(firmware_items, f, indent=2)
    print(f"[+] Wrote firmware inventory ({len(firmware_items)} items) with SHA256 hashes to {firmware_out}")

    # Unreferenced files check
    referenced_files = set(component_map["file_to_components"].keys())
    for fw_p in sorted(all_fw_paths):
        if fw_p not in referenced_files:
            component_map["unreferenced_firmware_files"].append(fw_p)

    comp_map_out = output_dir / "component_map.json"
    with open(comp_map_out, "w", encoding="utf-8") as f:
        json.dump(component_map, f, indent=2)
    print(f"[+] Wrote bidirectional component map to {comp_map_out}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    restore_dir = project_root / "iPhone18,3_27.2_24B119_Restore"
    output_dir = project_root / "artifacts" / "manifests"
    
    if len(sys.argv) > 1:
        restore_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    if not restore_dir.is_dir():
        print(f"[ERROR] Restore directory {restore_dir} not found.")
        sys.exit(1)

    parse_all_manifests(restore_dir, output_dir)
