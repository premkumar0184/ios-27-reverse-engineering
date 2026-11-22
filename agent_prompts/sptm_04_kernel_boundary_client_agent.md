# Agent Prompt: SPTM & TXM RE Phase 4 — Kernel Boundary & Clean-Room C Client

## Objective
Dissect the host XNU kernel's interface with the SPTM and TXM hypervisors, and synthesize an independent, clean-room C client (`sptm_hypercall_client.pseudo.c`). The C client must define all hypercall structs, function IDs, register wrappers, and verification helpers, passing `gcc -fsyntax-only` with zero compiler errors.

## Target Assets
- `artifacts/kernel/kernelcache.release.raw` / `artifacts/kernel/kernelcache.research.raw`
- `artifacts/firmware/sptm.t8150.release.raw`
- `artifacts/firmware/txm.iphoneos.research.raw`

## Target Deliverables to Produce
1. `artifacts/sptm/xnu_sptm_boundary_spec.json`:
   - XNU kernel implementation: `sptm_call` wrappers, `pmap_enter_sptm`, `pmap_remove_sptm`, `txm_trust_cache_register`.
   - Stage-2 translation fault handling in XNU, panic strings, and telemetry hooks.
2. `artifacts/sptm/pseudocode/sptm_hypercall_client.pseudo.c`:
   - Clean-room C client:
     - Header definitions: data types, error codes (`SPTM_SUCCESS`, `SPTM_ERR_INVALID_FRAME`, etc.).
     - 42 SPTM Function ID constants and 17 Dispatch Table enums.
     - 59 Physical Frame Type enums.
     - Inline assembly / function prototypes for hypercall traps (`sptm_hypercall_invoke`).
     - TXM Image4 validation client and TrustCache registration helper.
     - iBoot research command dispatcher mockup.
   - Verification: Must compile cleanly with `gcc -fsyntax-only -Wall -Wextra -Werror artifacts/sptm/pseudocode/sptm_hypercall_client.pseudo.c`.
3. `findings/sptm/04_KERNEL_BOUNDARY_CLIENT.md`:
   - Documentation of the host kernel bridge, memory retyping flow, and clean-room implementation design.

## Verification Gate
```bash
python3 tools/verify_phase.py sptm_phase_4_kernel_boundary
```
