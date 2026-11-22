# Proposal: Phase 4 - Coprocessor & Peripheral Firmware Reverse Engineering

## Goal
Perform comprehensive reverse engineering of peripheral coprocessor firmware packages in the `Firmware/` tree of the iOS 27 restore bundle (`iPhone18,3_27.2_24B119_Restore`), cataloging architectures, entrypoints, and communication topologies across Always-On Processor (AOP), Apple Neural Engine (ANE), GPU (AGX), Rose (UWB), Secure Enclave (SEP), and Modem/Cellular Baseband.

## Scope
1. **Peripheral Firmware Survey**: Extract and inventory all coprocessor payloads (`artifacts/coprocessors/coprocessor_inventory.json`).
2. **AOP / Sensor Hub Analysis**: Unpack and dissect AOP/AOP2 firmware, mapping RTOS vectors and sensor hub IPC endpoints (`artifacts/coprocessors/aop_analysis.json`).
3. **Secure Enclave Processor (SEP)**: Inspect and analyze SEP firmware containers (`sep-firmware.v57.RELEASE.im4p`) and memory protection envelopes (`artifacts/coprocessors/sep_analysis.json`).
4. **Cellular Baseband & Modem**: Unpack `Mav25-2.20.04.Release.bbfw` (ZIP archive), inventory all modem partitions, bootloader stages, and DSP images (`artifacts/coprocessors/baseband_inventory.json`).
5. **Comprehensive Treatise**: Document all hardware topologies, instruction sets, and memory layouts in `findings/04_FIRMWARE_COPROCESSORS.md`.
6. **Phase Verification**: Validate with `python3 tools/verify_phase.py phase_04_firmware_coprocessors`.
