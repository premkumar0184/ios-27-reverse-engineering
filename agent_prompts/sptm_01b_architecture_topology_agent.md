# Agent Prompt: SPTM & TXM RE Phase 1B — Architecture & Hypervisor Topology

## Objective
Reverse engineer the runtime execution model and privilege hierarchy of Apple Silicon A19 Pro (`t8150`) under iOS 27.2. Map the interaction between Guarded EL2 (GL2) Secure Page Table Monitor (SPTM), Guarded EL1 (GL1) Trusted Execution Monitor (TXM), EL1 Darwin/XNU kernel, and EL0 Conclaves/Userland. Dissect TXM's Code Signing Monitor (CSM) symbol table and runtime function exports preserved in the research build.

## Target Binaries
- `artifacts/firmware/sptm.t8150.release.raw` (1,327,136 bytes, Mach-O 64-bit arm64e)
- `artifacts/firmware/txm.iphoneos.research.raw` (557,088 bytes, Mach-O 64-bit arm64e with symbols)

## Target Deliverables to Produce
1. `artifacts/sptm/sptm_topology_spec.json`:
   - Execution privilege hierarchy: GL2 (SPTM), GL1 (TXM), EL1 (XNU), EL0 (Darwin Apps / Exclave Conclaves).
   - SPTM memory layout: `__TEXT` (`0xfffffff027004000`), `__DATA_CONST`, `__LATE_CONST`, `__TEXT_EXEC` (`0xfffffff0270b4000`), `__LAST`, `__DATA`, `__BOOTDATA`, `__LINKEDIT`.
   - Entry point (`0xfffffff0270bc388`), Mach-O UUID (`6fb95ed6-be8a-39cf-862b-250ba7efd5a5`), exception vector table base (`0xfffffff027118000`).
   - Guarded Execution Feature (GXF) hardware configuration registers and context switching logic.
2. `artifacts/sptm/txm_csm_architecture.json`:
   - TXM Code Signing Monitor (CSM) architecture and Image4 trust evaluation pipeline.
   - Preserved research symbols: `_txm_runtime_log`, `_txm_runtime_alloc_type`, `_txm_runtime_dealloc_type`, `_txm_runtime_set_nonce`, `_txm_runtime_roll_nonce`, `_txm_runtime_copy_nonce`.
   - DeviceTree nodes monitored: `/chosen`, `/product`, `/defaults`, `/chosen/manifest-properties`, `/chosen/asmb`.
   - TrustCache evaluation flow and dynamic code signature validation.
3. `findings/sptm/01B_ARCHITECTURE_AND_TOPOLOGY.md`:
   - Architectural report on Apple's hypervisor topology, GXF hardware enforcement, privilege transitions, and TXM-SPTM co-design.

## Verification Gate
```bash
python3 tools/verify_phase.py sptm_phase_1b_architecture_topology
```
