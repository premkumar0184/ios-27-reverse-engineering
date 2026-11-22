# Agent Prompt: SPTM & TXM RE Phase 5 — Synthesis, Test Suite & Master Publication Dossier

## Objective
Synthesize all SPTM, TXM, and Research Boot Chain reverse engineering findings into the final master publication dossier `IOS_27_SPTM_TXM_BOOT_RE.md` ($\ge 50,000$ bytes). Validate all extracted constants, dispatch table indices, frame types, and container offsets with an independent Python test suite `tools/verify_sptm_constants.py`. Produce `artifacts/sptm/cross_validation_matrix.json`, update knowledge graphs, and define the standalone open-source repository `premkumar0184/apple-sptm-txm-re`.

## Target Deliverables to Produce
1. `tools/verify_sptm_constants.py`:
   - Independent verification test suite verifying all Image4 tags, magic numbers, Mach-O load command offsets, dispatch table function counts, frame type enums, and C pseudocode syntax.
   - Exit code 0 on success.
2. `artifacts/sptm/cross_validation_matrix.json`:
   - Extraction confidence matrix (`EXTRACTED`, `INFERRED`, `TENTATIVE`).
   - Cross-validation mapping of all physical addresses, hypercall indices, and structural invariants.
3. Master Dossier: `IOS_27_SPTM_TXM_BOOT_RE.md` ($\ge 50,000$ bytes):
   - Exhaustive technical treatise covering:
     1. Executive Summary & Hardware Memory Virtualization
     2. Image4 Container Specification & Firmware Layout
     3. Hypervisor Topology: Guarded EL2 (SPTM) & Guarded EL1 (TXM)
     4. Stage-2 Memory Translation (VTTBR_EL2) & 59 Physical Frame Types
     5. Hardware Access Control: CTRR, GAPF & DART/SART Bus Isolation
     6. SPTM Hypercall ABI & 17 Monitored Dispatch Tables (42 Function IDs)
     7. Trusted Execution Monitor (TXM) Code Signing Monitor & Image4 Pipeline
     8. iBoot and LLB Research Boot Chain Diagnostics & Memory Shell
     9. Host Kernel Bridge (XNU pmap & GXF Transitions)
     10. Clean-Room C Client Specification (`sptm_hypercall_client.pseudo.c`)
     11. Numerical Cross-Validation Matrix & Test Suite Verification
4. GitHub Target Repository Specification:
   - Standalone open-source repo: `premkumar0184/apple-sptm-txm-re` with README, specifications, pseudocode runtime, and test suite.

## Verification Gate
```bash
python3 tools/verify_sptm_constants.py
python3 tools/verify_phase.py sptm_phase_5_synthesis
```
