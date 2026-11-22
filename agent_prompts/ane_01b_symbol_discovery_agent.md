# Agent Prompt: ANE RE Phase 1B — Symbol Discovery: Client/Server Topology & Ivar Layouts

## Objective
Enumerate the complete symbol table, Objective-C classes, C++ compiler classes, and method signatures across `AppleNeuralEngine.framework`, `ANECompiler.framework`, `ANEServices.framework`, and `AppleT8150ANEHAL.kext`. Dissect `_ANEClient`, `_ANEDeviceInfo`, `_ANERequest`, `_ANEModel`, and `_ANECompiler`. Output `artifacts/ane/symbol_inventory.json` and `artifacts/ane/client_server_topology.json`.

## Prerequisites
- Phase A1A (`ane_phase_1a_workspace_baseline`) must be `completed`.

## Step-by-Step Instructions

### Step 1: Userland Symbol Extraction
Extract classes and protocols from:
1. `AppleNeuralEngine.framework` (`.15` @ `0x1bda6d000`):
   - `_ANEClient`: Client connection manager, model compilation submission, and evaluation dispatch.
   - `_ANEDeviceInfo`: Hardware capability detection (core count, tile count, generation H18 identifier).
   - `_ANERequest`: Inference request wrapper, input/output buffer tracking, completion callbacks.
   - `_ANEModel`: Model container, `.hwx` bundle reference, IOMMU shared memory handles.
   - `_ANEQoSMapper`: Task scheduling priority mapping.
2. `ANECompiler.framework` (`.11` @ `0x1ab96c000`):
   - `_ANECompiler`: Top-level graph compiler interface (`compileModel:options:error:`).
   - `_ANEProgramForEvaluation`: In-memory compiled program representation.
   - C++ compiler symbols (AST nodes, optimization passes, memory layout planners).
3. `ANEServices.framework` & `MilAneflow.framework`:
   - Hardware diagnostic endpoints, MIL graph conversion bridge.

### Step 2: Ivar Layouts & Memory Structures
Extract byte offsets, types, and flags for:
- `struct _ANEModel_IVARS`
- `struct _ANERequest_IVARS`
- `struct _ANEClient_IVARS`

### Step 3: Kernel Driver Dispatch Table
In `AppleT8150ANEHAL.kext`:
- Locate `AppleT8150ANEUserClient` in `__DATA_CONST.__const`.
- Extract `sMethods` dispatch table (external method count, scalar/structure input/output sizes).
- Map user client selector indices (e.g. `open`, `close`, `map_buffers`, `submit_command_buffer`, `wait_completion`).

### Step 4: Write Phase Artifacts
1. `artifacts/ane/symbol_inventory.json`:
   - Categorized listing of classes, protocols, methods, and ivars across all frameworks.
2. `artifacts/ane/client_server_topology.json`:
   - Client-server IPC flow (App $\to$ CoreML $\to$ `_ANEClient` $\to$ `aned` daemon $\to$ `AppleT8150ANEUserClient` $\to$ Hardware Queues).

### Step 5: Verification Gate
```bash
python3 tools/verify_phase.py ane_phase_1b_symbol_discovery
```
Update `progress.json` to mark Phase A1B completed.
