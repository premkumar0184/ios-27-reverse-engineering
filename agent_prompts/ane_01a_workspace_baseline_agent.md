# Agent Prompt: ANE RE Phase 1A — Workspace Baseline & Subcache Address Resolution

## Objective
Establish the concrete binary anchors and physical file offsets for all Apple Neural Engine (ANE) userland frameworks, kernel extensions, and coprocessor firmware. Verify Mach-O headers, segment tables, and extract the raw IM4P firmware payload for generation H18 (Apollo v5). Produce `artifacts/ane/phase_1a_workspace_baseline.json`.

## Target Binaries & Memory Locations
1. `AppleNeuralEngine.framework` (VM `0x1bda6d000`, subcache `.15`)
2. `ANECompiler.framework` (VM `0x1ab96c000`, subcache `.11`)
3. `ANEServices.framework` (VM `0x253d18000`, subcache `.48`)
4. `MilAneflow.framework` (VM `0x297d81000`, subcache `.61`)
5. `com.apple.driver.AppleT8150ANEHAL` (VM `0xfffffe00077b9580` in `artifacts/kernel/kernelcache.release.raw`)
6. `Firmware/ane/h18_ane_fw_apollo_v5x.im4p` (1,540,121 bytes)

## Step-by-Step Instructions

### Step 0: Knowledge Graph Query
```bash
graphify query "AppleNeuralEngine ANECompiler"
graphify query "AppleT8150ANEHAL h18_ane_fw"
```

### Step 1: Subcache Slices & Mach-O Verification
For each framework in the dyld shared cache:
1. Seek to the subcache file offset corresponding to the framework's VM base address.
2. Read 32-byte `mach_header_64`:
   - Magic: `0xFEEDFACF`
   - CPU Type: `0x0100000C` (ARM64)
   - CPU Subtype: `0x80000002` (ARM64E / PAC00)
   - Load commands count (`ncmds`) and size (`sizeofcmds`).
3. Parse segment load commands (`LC_SEGMENT_64`) to record `__TEXT`, `__DATA_CONST`, `__DATA`, `__LINKEDIT`.
4. Extract UUID from `LC_UUID`.

### Step 2: Kernelcache KEXT Verification
Verify `com.apple.driver.AppleT8150ANEHAL` and `com.apple.driver.AppleH16ANEInterface` in `artifacts/kernel/kext_catalog_release.json`. Record their `__TEXT_EXEC` virtual address and entrypoint.

### Step 3: Parse ANE IM4P Firmware
Using `tools/parse_im4p.py`:
1. Parse `Firmware/ane/h18_ane_fw_apollo_v5x.im4p`.
2. Extract payload type, version string, uncompressed size, and extract raw firmware payload to `artifacts/ane/h18_ane_fw_apollo_v5x.raw`.

### Step 4: Write Phase Artifact
Write `artifacts/ane/phase_1a_workspace_baseline.json`:
```json
{
  "phase": "ane_phase_1a_workspace_baseline",
  "target_soc": "t8150 (Apple A19 Pro)",
  "ane_generation": "H18 (Apollo v5)",
  "frameworks": {
    "AppleNeuralEngine": { ... },
    "ANECompiler": { ... },
    "ANEServices": { ... },
    "MilAneflow": { ... }
  },
  "kernel_drivers": {
    "AppleT8150ANEHAL": { ... },
    "AppleH16ANEInterface": { ... }
  },
  "firmware": {
    "im4p_path": "Firmware/ane/h18_ane_fw_apollo_v5x.im4p",
    "payload_size": 1540121,
    "payload_type": "anef",
    "verified": true
  },
  "toolchain_trusted": true
}
```

### Step 5: Verification Gate
```bash
python3 tools/verify_phase.py ane_phase_1a_workspace_baseline
```
Update `progress.json` to mark Phase A1A completed and set `active_phase_id = "ane_phase_1b_symbol_discovery"`.
