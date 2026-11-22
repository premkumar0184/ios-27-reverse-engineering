# Agent Prompt: ExclaveOS RE Phase 2 — Tightbeam RPC Serialization, Wire Protocol & Transports

## Objective
Reverse engineer the **Tightbeam** RPC serialization framework, binary wire protocol, message accumulator structures, and transport abstraction layers used across ExclaveOS conclaves.

## Target Binaries
- `artifacts/firmware/exclavecore_bundle_unpacked/00_tightbeam_runtime.macho`
- `System/ExclaveKit/System/Library/PrivateFrameworks/Tightbeam.framework/Tightbeam`
- `System/ExclaveKit/usr/bin/tightbeam_stub`

## Target Deliverables
1. `artifacts/exclave/tightbeam_wire_spec.json`:
   - Message header encoding: Magic, flags, transaction ID, endpoint token, payload length.
   - Positional serialization rules: alignment constraints, primitive type layouts, dynamic arrays.
   - Transport layers:
     - `cL4`: Inline register-based IPC transport (`cL4_transport.c`) for low-latency messages.
     - `cL4_large`: Shared-memory message accumulator transport (`cL4_large_transport.c`) for bulk payloads.
2. `artifacts/exclave/tightbeam_protocol_schema.json`:
   - Swift 5 protocol definitions:
     - `TightbeamServiceInitProtocol`
     - `TightbeamBadge`
     - `TightbeamDecoderProtocol` / `TightbeamEncoderProtocol`
     - `TightbeamEndpoint`
     - `TightbeamMessage`
     - `TightbeamResourceSerializerProtocol`
     - `TightbeamBuilderApi`
   - Descriptor types and component bindings.
3. `findings/exclave/02_TIGHTBEAM_WIRE_FORMAT.md`:
   - Deep structural report on Tightbeam message wire layout, accumulator mechanisms, and transport mechanics.

## Verification Gate
```bash
python3 tools/verify_phase.py exclave_phase_2_tightbeam_wire_format
```
