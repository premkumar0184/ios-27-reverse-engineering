# Agent Prompt: ANE RE Phase 2 — Model Compilation & HWX Container Dissection

## Objective
Reverse engineer the internal architecture of the compiled `.hwx` ("Hardware Executable") container and the graph compiler pipeline in `ANECompiler.framework`. Determine how MIL/CoreML computational graphs are partitioned, optimized, and lowered into ANE task descriptors (`td`), task streams (`tsk`), and kernel weights (`krn`). Output `artifacts/ane/hwx_container_spec.json` and `findings/ane/02_HWX_COMPILER.md`.

## Prerequisites
- Phase A1B (`ane_phase_1b_symbol_discovery`) must be `completed`.

## Step-by-Step Instructions

### Step 1: HWX Container File Format & Mach-O Sections
A `.hwx` file is structured as a specialized Mach-O container with designated section tags:
1. Identify all section names parsed by `_ANECompiler` and `_ANEProgramForEvaluation`:
   - `__TEXT.__text`: Microcode execution stream
   - `__DATA.__td`: Task Descriptors
   - `__DATA.__krn`: Weight and bias parameter payloads
   - `__DATA.__desc`: Model tensor shape descriptors and channel layouts
2. Reverse engineer the `anec` header layout (revisiting `eiln/ane` prior art and comparing against A19 Pro H18 changes):
   - Model size, `td_size`, `td_count`, `tsk_size`, `krn_size`, `src_count`, `dst_count`
   - Multi-channel mapping: `tiles[32]` and `nchw[32][6]` tensor shape matrices

### Step 2: Compiler Lowering & Operator Mapping
Analyze `ANECompiler.framework`:
1. Track how common neural operations are mapped:
   - Convolution (2D/Depthwise/Grouped)
   - Matrix Multiplication (GEMM / Batched MatMul)
   - Normalization (LayerNorm, RMSNorm, BatchNorm)
   - Activations (ReLU, GeLU, SiLU / Swish, Sigmoid)
   - Transpose / Permute
2. Document fused operators (e.g. Conv + Bias + ReLU / GeLU fusion in a single hardware step).

### Step 3: Write Phase Artifacts
1. `artifacts/ane/hwx_container_spec.json`:
   - Complete binary struct definitions for HWX sections and headers.
   - Operator capability matrix.
2. `findings/ane/02_HWX_COMPILER.md`:
   - Architectural document detailing compiler phases, IR lowering, and container layout.

### Step 4: Verification Gate
```bash
python3 tools/verify_phase.py ane_phase_2_hwx_compiler
```
Update `progress.json`.
