# Agent Prompt: Phase 4 - Coprocessor & Low-Level Subsystem Firmware Specialist

## Mission
Execute **Phase 4: Coprocessor & Low-Level Subsystem Firmware Reverse Engineering**.
Reverse engineer peripheral coprocessor images in `Firmware/`, including Always-On Processor (AOP/AOP2), Apple Neural Engine (ANE), GPU (AGX), Rose (UWB), Secure Enclave (SEP), and Modem/Baseband packages.

## Required Deliverables
1. `artifacts/coprocessors/coprocessor_inventory.json`:
   - Matrix of coprocessors (firmware name, CPU architecture, container format, size, purpose).
2. `artifacts/coprocessors/aop_analysis.json`:
   - Disassembly, RTOS identifiers, and sensor hub IPC dispatchers for AOP/AOP2.
3. `artifacts/coprocessors/sep_analysis.json`:
   - Secure Enclave Processor firmware format, memory ranges, and security isolation primitives.
4. `artifacts/coprocessors/baseband_inventory.json`:
   - Extraction and partition inventory of `Mav25-2.20.04.Release.bbfw`.
5. `findings/04_FIRMWARE_COPROCESSORS.md`:
   - Deep architectural documentation covering coprocessor memory maps, IPC channels, and firmware entrypoints.

## Available Tools & Procedures
1. Use `7z l` / `7z x` to inspect and unpack `.bbfw` (ZIP format).
2. Use `tools/parse_im4p.py` to unpack `.im4p` firmware files.
3. Use REA (`rea open_binary`, `rea inspect_macho`) and Ghidra for disassembly.
4. Verify results with `python3 tools/verify_phase.py phase_04_firmware_coprocessors`.
