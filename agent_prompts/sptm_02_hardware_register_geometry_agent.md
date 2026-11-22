# Agent Prompt: SPTM & TXM RE Phase 2 — Hardware Register & Stage-2 Memory Geometry

## Objective
Reverse engineer Apple Silicon A19 Pro (`t8150`) hardware memory virtualization and protection mechanisms. Extract Stage-2 translation table geometries (`VTTBR_EL2`, `VTCR_EL2`), define the 59 physical frame types arbitrated by SPTM, analyze hardware protection registers (CTRR, GAPF, DART/SART), and map the decrypted DeviceTree hardware properties for `v57ap`.

## Target Assets
- `artifacts/firmware/sptm.t8150.release.raw`
- `iPhone18,3_27.2_24B119_Restore/Firmware/all_flash/DeviceTree.v57ap.im4p` (decompressed: 365,632 bytes)

## Target Deliverables to Produce
1. `artifacts/sptm/stage2_translation_geometry.json`:
   - Stage-2 Translation Table structure: 16 KB page granule (`TG0 = 0x2`), 4-level translation, Intermediate Physical Address (IPA) width, `VTTBR_EL2` register format.
   - Catalog of 59 Physical Frame Types: XNU Kernel Text/Data, Page Table (L1/L2/L3), Exclave Conclave Private Frame, Datacube Shared Frame, Secure Enclave Carveout, Device MMIO, CTRR Locked.
   - Hardware register definitions: Configurable Text Region Register (CTRR), Guarded Address Protection Filter (GAPF), SPRR/APRR deprecation status.
   - DART (Device Address Resolution Table) and SART hardware stream ID isolation across coprocessors (ANE, AGX, AOP, SEP).
2. `artifacts/sptm/devicetree_hardware_map.json`:
   - Decoded DeviceTree nodes: `/chosen` (boot arguments, SPTM reserve base & size, TXM reserve base & size, memory maps), `/arm-io` (memory controller, MMIO base addresses), `/cpus`.
3. `findings/sptm/02_HARDWARE_REGISTER_GEOMETRY.md`:
   - Technical report on Stage-2 hardware memory isolation, physical frame typing state machine, hardware access control registers, and DeviceTree topology.

## Verification Gate
```bash
python3 tools/verify_phase.py sptm_phase_2_hardware_register_geometry
```
