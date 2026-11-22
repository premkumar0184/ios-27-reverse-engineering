# Agent Prompt: ANE RE Phase 5 — Cross-Validation, Standalone Driver Spec & Publication Dossier

## Objective
Synthesize all prior ANE reverse engineering phases into the final publication-grade dossier `IOS_27_APPLE_NEURAL_ENGINE_RE.md` (target $\ge 50,000$ bytes). Validate all hardware constants and structures using a standalone verification script `tools/verify_ane_constants.py`. Produce `artifacts/ane/cross_validation_matrix.json`. Update the knowledge graph via `graphify`.

## Prerequisites
- All previous ANE phases (A1A, A1B, A2, A3, A4) must be `completed`.
- All intermediate artifacts in `artifacts/ane/` and `findings/ane/` must exist and be non-empty.

## Step-by-Step Instructions

### Step 1: Write Verification Script
Write `tools/verify_ane_constants.py`:
- Validate tile size (`0x4000`), tile count (`0x20`), FIFO Node ID (`0x40`), command granularity (`0x10`), and HWX header format.
- Exit code 0 on success.

### Step 2: Cross-Validation Matrix
Write `artifacts/ane/cross_validation_matrix.json`:
- Schema version 1.0, extraction confidence counts (`EXTRACTED`, `INFERRED`, `TENTATIVE`, `UNKNOWN`).
- Detailed comparison between M1/M2 prior art (`eiln/ane`) and A19 Pro H18 changes.

### Step 3: Master Publication Dossier
Write `IOS_27_APPLE_NEURAL_ENGINE_RE.md` ($\ge 50,000$ bytes).
Required sections:
1. Executive Summary & Hardware Baseline (A19 Pro `t8150`, H18 Apollo v5)
2. ANE System Architecture & Framework Hierarchy (`AppleNeuralEngine`, `ANECompiler`, `AppleT8150ANEHAL`)
3. HWX Container Binary Specification & Section Layout
4. Hardware Instruction Set Architecture (ISA) & Opcode Matrix
5. 16KB Tile Spatial Geometry & Multi-Channel Memory Mapping
6. Kernel Dispatch Protocol, Ring Buffers & FIFO Submission
7. Bare-Metal Clean-Room Driver Runtime Specification (C/Rust)
8. Cross-Generation Evolution: A14/M1 vs A17/M3 vs A19 Pro H18
9. Independent Numerical Verification & Cross-Validation Results
10. Unresolved Dynamic Hardware Invariants & Future Research

### Step 4: Update Knowledge Graph
```bash
graphify artifacts/ane/ --update --code-only --no-viz
```

### Step 5: Verification Gate
```bash
python3 tools/verify_ane_constants.py
python3 tools/verify_phase.py ane_phase_5_synthesis
```
Update `progress.json`:
- Set `ane_phase_5_synthesis.status = "completed"`
- Set `active_phase_id = null`
