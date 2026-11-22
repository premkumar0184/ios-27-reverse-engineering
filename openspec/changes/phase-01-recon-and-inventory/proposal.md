# Proposal: Phase 1 - IPSW Reconnaissance, Manifest Parsing & Component Inventory

## Why
Reverse engineering an unfamiliar 12+ GB modern Apple operating system restore package requires an authoritative, machine-readable inventory of all partition images, hardware configurations, build trains, and coprocessor subdirectories before performing binary decompilation or filesystem extraction.

## What Changes
- Parse all root plists (`BuildManifest.plist`, `Restore.plist`, `SystemVersion.plist`, `RestoreVersion.plist`).
- Map hardware identifiers: Board configuration `v57ap`, Device `iPhone18,3`, Platform/CPID `t8150` (`33104`), Build Train `RaveB`, Build ID `79DC7400-CE82-11F1-B523-97A425208D9D`.
- Generate machine-readable JSON inventories:
  - `artifacts/manifests/manifest_summary.json`
  - `artifacts/manifests/image_inventory.json`
  - `artifacts/manifests/firmware_inventory.json`
  - `artifacts/manifests/component_map.json`
- Compile verified technical findings document in `findings/01_RECON_AND_INVENTORY.md`.

## Capabilities
- Pure investigation and manifest parsing: `skip_specs: true`.

## Impact
- Unblocks Phase 2 (Cryptographic Decryption & Full Filesystem Extraction) by providing exact component roles and path resolutions for all restore images.
