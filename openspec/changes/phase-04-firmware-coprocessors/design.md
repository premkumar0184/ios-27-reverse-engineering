# Design: Phase 4 - Coprocessor & Peripheral Firmware Reverse Engineering

## Architecture & Tooling Strategy
1. **Container Extraction**:
   - Parse ASN.1 Image4 (`.im4p`) envelopes with `tools/parse_im4p.py` to extract raw binary payloads for AOP, Rose, AGX, AVE, and SEP.
   - Extract Qualcomm/Apple baseband archive (`Mav25-2.20.04.Release.bbfw`) using `7z` to unpack partition images (`qdsp6sw.mbn`, `sbl1.mbn`, `tz.mbn`).
2. **Binary Architecture & Disassembly**:
   - Inspect instruction sets (ARM Cortex-M, RISC-V, Hexagon QDSP6, ARM64) and vector tables.
   - Map memory layouts, entrypoints, and RTOS signatures (FreeRTOS, RTKit).
3. **Synthesis & Schema Enforcement**:
   - Output structured JSON matrices: `coprocessor_inventory.json`, `aop_analysis.json`, `sep_analysis.json`, and `baseband_inventory.json`.
   - Validate findings in `findings/04_FIRMWARE_COPROCESSORS.md` using `tools/verify_phase.py`.
