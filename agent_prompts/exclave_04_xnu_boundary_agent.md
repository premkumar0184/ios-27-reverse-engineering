# Agent Prompt: ExclaveOS RE Phase 4 — XNU Boundary, xnuproxy & Conclave Lifecycle Management

## Objective
Reverse engineer the kernel-to-exclave boundary across XNU and ExclaveOS. Dissect the XNU trap interfaces, `xnuproxy` request dispatch, SPM (Secure Page Table Monitor) domain transitions, and construct a clean-room C client runtime for communicating over Tightbeam.

## Target Binaries
- `artifacts/kernel/kernelcache.release.raw` (XNU exclave syscall handlers)
- `artifacts/firmware/exclavecore_bundle_unpacked/00_tightbeam_runtime.macho`
- `artifacts/firmware/exclavecore_bundle_unpacked/03_jg_sharedmem_preload.macho`

## Target Deliverables
1. `artifacts/exclave/xnu_boundary_spec.json`:
   - XNU system call trap table:
     - `_exclaves_ctl_trap` (operation codes, entitlement enforcement)
     - `_exclaves_call_trap` (synchronous conclave invocation)
     - `_exclaves_boot_trap` (bootstrap and trust verification)
   - `xnuproxy` notification server: `JgXnuProxyComponents.XnuProxyNotificationServer` (notificationUpcalls, notificationId).
   - SPM domain transitions: memory barrier retyping and domain fault isolation.
2. `artifacts/exclave/pseudocode/tightbeam_client.pseudo.c`:
   - Standalone clean-room C client runtime demonstrating how to allocate an endpoint, build a Tightbeam message header, serialize positional parameters, and dispatch via the cL4 transport.
3. `findings/exclave/04_XNU_BOUNDARY.md`:
   - Technical findings document on the XNU-Exclave interface, `xnuproxy`, and trap dispatch.

## Verification Gate
```bash
python3 tools/verify_phase.py exclave_phase_4_xnu_boundary
```
