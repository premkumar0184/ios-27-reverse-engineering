# Agent Prompt: ExclaveOS RE Phase 1A — Workspace Baseline, Image Extraction & BUND Container Dissection

## Objective
Establish the deterministic reverse engineering baseline for **ExclaveOS and Tightbeam IPC** on Apple Silicon A19 Pro (`t8150`, iOS 27.2 build `24B119`). Extract and map `dyld_shared_cache_arm64e` from the decrypted ExclaveOS filesystem (`141-08904-238_exclaveos.dmg`), dissect the Apple `BUND` (`DNUB`) container format inside `exclavecore_bundle.t8150.RELEASE.im4p`, and catalog the 4 core microkernel Mach-O binaries.

## Prerequisites
- Decrypted ExclaveOS rootfs `artifacts/crypto/141-08904-238_exclaveos.dmg` must exist.
- `iPhone18,3_27.2_24B119_Restore/Firmware/image4/exclavecore_bundle.t8150.RELEASE.im4p` must exist.
- Unpacked microkernel Mach-Os in `artifacts/firmware/exclavecore_bundle_unpacked/`.

## Target Artifacts to Produce
1. `artifacts/exclave/phase_1a_workspace_baseline.json`:
   - System version, build train (`RaveB24B119.V57ExclaveOS.apfs`), hardware target (`t8150`, `v57ap`).
   - Image mapping: file paths, SHA-256 hashes, sizes, APFS volume parameters.
   - Microkernel binary inventory: `00_tightbeam_runtime.macho`, `01_pmm_server.macho`, `02_vascore_platform.macho`, `03_jg_sharedmem_preload.macho`.
2. `artifacts/exclave/bund_container_spec.json`:
   - Apple BUND container header layout: Magic (`0x444e5542` / `DNUB`), version, entry count.
   - FourCC tag catalog:
     - `ktxt` / `txtk`: Kernel Code
     - `kdat` / `tadk`: Kernel Data
     - `rtxt` / `txtr`: Runtime Code
     - `rdat` / `tadr`: Runtime Data
     - `utxt` / `txtu`: User Code
     - `udat` / `tadu`: User Data
     - `rlnk` / `knlr`: Kernel Release
     - `urst` / `tsru`: Trust Services Runtime Unit
     - `ubdl` / `ldbu`: Bundle Loader
   - Entry list with file offsets, sizes, and target binaries.
3. `findings/exclave/01A_WORKSPACE_BASELINE.md`:
   - Deep structural report on the ExclaveOS image, APFS volume attributes, BUND format, and microkernel components.

## Verification Gate
```bash
python3 tools/verify_phase.py exclave_phase_1a_workspace_baseline
```
