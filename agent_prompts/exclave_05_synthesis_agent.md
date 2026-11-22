# Agent Prompt: ExclaveOS RE Phase 5 — Cross-Validation, Clean-Room Driver Spec & Publication Dossier

## Objective
Synthesize all prior ExclaveOS reverse engineering phases into the final publication-grade dossier `IOS_27_EXCLAVEOS_TIGHTBEAM_RE.md` (target $\ge 50,000$ bytes). Validate all microkernel invariants, capability syscalls, and Tightbeam message structures using a standalone verification script `tools/verify_exclave_constants.py`. Produce `artifacts/exclave/cross_validation_matrix.json`. Update the knowledge graph via `graphify`.

## Prerequisites
- All previous ExclaveOS phases (E1A, E1B, E2, E3, E4) must be `completed`.
- All intermediate artifacts in `artifacts/exclave/` and `findings/exclave/` must exist and be non-empty.

## Step-by-Step Instructions

### Step 1: Write Verification Script
Write `tools/verify_exclave_constants.py`:
- Validate BUND magic (`0x444e5542`), FourCC tags, cL4 capability rights bitmasks, Tightbeam header structures, and Datacube retyping invariants.
- Exit code 0 on success.

### Step 2: Cross-Validation Matrix
Write `artifacts/exclave/cross_validation_matrix.json`:
- Schema version 1.0, extraction confidence counts (`EXTRACTED`, `INFERRED`, `TENTATIVE`, `UNKNOWN`).
- Cross-validation entries mapping binary addresses, file offsets, and structural invariants.

### Step 3: Master Publication Dossier
Write `IOS_27_EXCLAVEOS_TIGHTBEAM_RE.md` ($\ge 50,000$ bytes).
Required sections:
1. Executive Summary & Microkernel Security Paradigm (A19 Pro `t8150`, ExclaveOS 24B119)
2. ExclaveOS Architecture & cL4 Microkernel Foundation
3. Apple BUND (DNUB) Container Specification & Multi-Binary Layout
4. Capability Delegation Model (CSpace, Endpoints, Badges & Rights)
5. Tightbeam RPC Protocol & Binary Wire Serialization Specification
6. Memory Management Subsystem: PMM Server, MTE & Datacube Retyping
7. Jungle Shared Memory (`jg_sharedmem`) & Hardware Acceleration Bridges
8. The XNU-Exclave Boundary: System Call Traps & `xnuproxy`
9. Clean-Room Client Implementation (C/Swift Tightbeam Runtime)
10. Independent Numerical Verification & Cross-Validation Results

### Step 4: Update Knowledge Graph
```bash
graphify artifacts/exclave/ --update --code-only --no-viz
```

### Step 5: Verification Gate
```bash
python3 tools/verify_exclave_constants.py
python3 tools/verify_phase.py exclave_phase_5_synthesis
```
Update `progress.json`:
- Set `exclave_phase_5_synthesis.status = "completed"`
- Set `active_phase_id = null`
