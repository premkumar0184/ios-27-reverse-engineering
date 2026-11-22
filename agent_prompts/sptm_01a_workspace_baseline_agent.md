# Agent Prompt: SPTM & TXM RE Phase 1A — Workspace Baseline & Image4 Container Dissection

## Objective
Establish the deterministic reverse engineering baseline for **SPTM, TXM, and the Research Boot Chain** on Apple Silicon A19 Pro (`t8150`, iOS 27.2 build `24B119`, device `v57ap`). Unpack and inspect all 5 target Image4 (`.im4p`) firmware containers using ASN.1 DER parsing, extract raw binary payloads, record byte offsets, SHA-256 digests, FourCC tags, and Mach-O load command structures.

## Target Assets
1. `iPhone18,3_27.2_24B119_Restore/Firmware/sptm.t8150.release.im4p` (FourCC: `sptm`)
2. `iPhone18,3_27.2_24B119_Restore/Firmware/txm.iphoneos.research.im4p` (FourCC: `trxm`)
3. `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/iBoot.v57.RESEARCH_RELEASE.im4p` (FourCC: `ibot`)
4. `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/LLB.v57.RESEARCH_RELEASE.im4p` (FourCC: `illb`)
5. `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/DeviceTree.v57ap.im4p` (FourCC: `dtre`)

## Target Deliverables to Produce
1. `artifacts/sptm/phase_1a_workspace_baseline.json`:
   - System version (`24B119`, Darwin 24.2.0), hardware target (`t8150`, `v57ap`).
   - Image mapping: paths, file sizes, SHA-256 digests, decompressed sizes, FourCC tags.
   - Mach-O structure summaries for `sptm` and `trxm` (segments, sections, UUIDs, entrypoints).
2. `artifacts/sptm/image4_container_spec.json`:
   - Image4 container format specification: ASN.1 DER sequence layout, magic (`IM4P`), tag offsets, payload offsets, compression algorithms (`lzfse` / `bvx2`), payload headers.
   - Extraction mapping: input container -> output raw payload path and verification metadata.
3. `findings/sptm/01A_WORKSPACE_BASELINE.md`:
   - Deep forensic report on the 5 firmware images: Image4 container architecture, ASN.1 parsing mechanics, LZFSE decompression, raw Mach-O headers, and cryptographic integrity hashes.

## Verification Gate
```bash
python3 tools/verify_phase.py sptm_phase_1a_workspace_baseline
```
