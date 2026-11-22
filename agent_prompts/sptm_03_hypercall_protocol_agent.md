# Agent Prompt: SPTM & TXM RE Phase 3 — Wire Format & Hypercall/Mailbox Protocol

## Objective
Reverse engineer the communication protocol and invocation interfaces across Apple's hypervisor barrier. Map all 42 SPTM function IDs across 17 monitored dispatch tables, define the register calling conventions (`x0`..`x7`), document TXM hypercall/SMC entry points, and forensicly catalog diagnostic command handlers preserved in `iBoot.v57.RESEARCH_RELEASE` and `LLB.v57.RESEARCH_RELEASE`.

## Target Assets
- `artifacts/firmware/sptm.t8150.release.raw`
- `artifacts/firmware/txm.iphoneos.research.raw`
- `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/iBoot.v57.RESEARCH_RELEASE.im4p` (decompressed raw: 4,284,024 bytes)
- `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/LLB.v57.RESEARCH_RELEASE.im4p` (decompressed raw: 4,284,024 bytes)

## Target Deliverables to Produce
1. `artifacts/sptm/sptm_hypercall_dispatch_spec.json`:
   - SPTM Dispatch Table architecture: 17 Monitored Dispatch Tables and 42 discrete Function IDs (e.g., `sptm_retype_page`, `sptm_map_stage2`, `sptm_unmap_stage2`, `sptm_register_exclave_conclave`, `sptm_set_ctrr`).
   - Domain Crossing ABI: Entry instruction (`hvc #0` / GXF transition), argument registers (`x0` = function ID, `x1`..`x6` = parameters), return status (`x0` error code).
   - TXM SMC/Hypercall dispatch table: Image4 manifest verification calls, TrustCache registration, code signing validation hooks.
2. `artifacts/sptm/iboot_diagnostic_commands.json`:
   - Catalog of preserved research commands in `RESEARCH_RELEASE` iBoot and LLB (e.g., memory dump commands, register inspection, boot argument injection, Stage-2 table query).
   - Diagnostic command parser format, handler function addresses, and privilege escalation flags.
3. `findings/sptm/03_HYPERCALL_AND_DIAGNOSTICS.md`:
   - Detailed specification of the hypercall wire protocol, dispatch table indices, domain crossing serialization, and research bootloader diagnostics.

## Verification Gate
```bash
python3 tools/verify_phase.py sptm_phase_3_hypercall_protocol
```
