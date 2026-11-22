# Agent Prompt: Phase 1 - IPSW Reconnaissance & Manifest Auditor

## Mission
Execute **Phase 1: IPSW Reconnaissance, Manifest Parsing & Component Inventory** for the iOS 27.2 restore package (`iPhone18,3_27.2_24B119_Restore`).

## Required Deliverables
1. `artifacts/manifests/manifest_summary.json`:
   - Extracted values from `BuildManifest.plist`, `Restore.plist`, `SystemVersion.plist`, and `RestoreVersion.plist`.
   - Identified SoC (`t8150`), Device Class (`v57ap`), Target Hardware (`iPhone18,3`), and Build Train (`RaveB`).
2. `artifacts/manifests/image_inventory.json`:
   - Exact file list of all `.dmg` and `.dmg.aea` files in the bundle root with size (bytes/MB), format classification, and encryption flags.
3. `artifacts/manifests/firmware_inventory.json`:
   - Complete inventory of the `Firmware/` tree (coprocessors, boot chain, baseband, trustcaches, root hashes).
4. `findings/01_RECON_AND_INVENTORY.md`:
   - Full technical report detailing device specifications, partitioning scheme, Cryptex1 container references, ExclaveOS mentions, and image catalog.
   - **Zero-Placeholder Invariant**: Must contain verified empirical data, hex offsets, and table citations.

## Available Tools & Procedures
1. Run `python3 tools/parse_manifests.py` to deterministically parse plists and generate the JSON inventories.
2. Inspect `BuildManifest.plist` for `VariantContents` (Cryptex1, ExclaveOS, SPTM, TXM, SEP).
3. Use REA (`rea inspect_artifact`) or python scripts to inspect packaging headers.
4. Verify results with `python3 tools/verify_phase.py phase_01_recon_and_inventory`.
