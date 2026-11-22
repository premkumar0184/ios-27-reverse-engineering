# Agent Prompt: ExclaveOS RE Phase 1B — cL4 Microkernel Architecture, Syscalls & Capability Delegation

## Objective
Reverse engineer Apple's commercial L4 microkernel (**cL4**) powering ExclaveOS. Dissect the microkernel system call interface, capability delegation model, capability space (CSpace) layout, badging mechanisms, and memory management subsystems (`pmm-server` and `vascore`).

## Target Binaries
- `artifacts/firmware/exclavecore_bundle_unpacked/01_pmm_server.macho`
- `artifacts/firmware/exclavecore_bundle_unpacked/02_vascore_platform.macho`
- `System/ExclaveKit/usr/lib/dyld`

## Target Deliverables
1. `artifacts/exclave/cl4_microkernel_spec.json`:
   - System call table: `L4_Cap_Mint_Ep`, `L4_MsgTag`, `L4_Call`, `L4_ReplyWait`, `L4_Send`, `L4_NBSend`, `L4_Yield`, `L4_ThreadSwitch`.
   - CSpace (Capability Space) layout: 2-level CNode radix tree, slot allocation, root capability table (`vas_root_cap_copy`).
   - Virtual Address Space (`VAS`) manager: span tables, memory fault handlers, page mapping bias.
2. `artifacts/exclave/capability_delegation_model.json`:
   - Capability types: Endpoint (`L4_Cap_Ep`), Thread (`L4_Cap_Thread`), Memory Frame (`L4_Cap_Frame`), CNode (`L4_Cap_CNode`).
   - Capability rights: `L4_CanRead` (bit 0), `L4_CanWrite` (bit 1), `L4_CanGrant` (bit 2).
   - Badge encoding: client ID, session tokens, and security domain badges.
3. `findings/exclave/01B_CL4_MICROKERNEL.md`:
   - Comprehensive technical findings document on cL4, microkernel traps, capability operations, and memory limits.

## Verification Gate
```bash
python3 tools/verify_phase.py exclave_phase_1b_cl4_microkernel
```
