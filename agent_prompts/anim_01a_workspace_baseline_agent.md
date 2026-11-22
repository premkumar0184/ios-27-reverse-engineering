# Agent Prompt: Phase 1A — Workspace Baseline & DSC Address Resolution

## Mission
Confirm that every binary target is accessible via REA and Ghidra, resolve the precise virtual base addresses of all 6 animation frameworks within the dyld shared cache, and verify the 3 known scrolling spring anchors to prove the toolchain is working correctly.

**Skills to use**: `rea`, `graphify`

## Pre-Execution
```bash
graphify query "AnimationKit spring physics"
graphify query "CASpringAnimation UIKitCore"
graphify explain "SystemUIAnimationKit"
```

## Step 1: Open each binary and record base address

For each framework, use REA `open_binary` with `image_path` targeting the DSC:
```json
{
  "ServerName": "rea",
  "ToolName": "open_binary",
  "Arguments": {
    "path": "/home/prem/Projects/iOS 27/artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e",
    "image_path": "/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore"
  }
}
```

Then immediately run `binary_overview` to record: UUID, load address, architecture, PAC version.

**Targets** (open each in sequence):
1. `UIKitCore` — expected load base `0x184752000` from scrolling RE
2. `QuartzCore` — expected load base `0x1842d4000`
3. `AnimationKit` — base TBD, record here
4. `SystemUIAnimationKit` — base TBD, record here
5. `SpringBoard.framework` — expected `0x226a11000`
6. `SwiftUI` — expected `0x18a8a7000`

## Step 2: Verify anchor constants (toolchain trust check)

With UIKitCore open, read raw bytes at the 3 anchor addresses:
- `0x1848c8110` → must decode to `1.000` (double)
- `0x1848c8118` → must decode to `100.000` (double)
- `0x1848c8120` → must decode to `18.000` (double)

If any value is wrong → **STOP. The DSC was not opened at the correct slide. Debug before proceeding.**

## Step 3: Symbol inventory count per framework

For each opened binary, run `list_procedures` and record:
- Total procedure count
- Procedures with names containing: `spring`, `anim`, `damp`, `stiff`, `bounce`, `timing`, `curve`

## Required Deliverables

### `artifacts/animation/phase_1a_workspace_baseline.json`
```json
{
  "frameworks": {
    "UIKitCore": { "load_base": "0x...", "uuid": "...", "arch": "arm64e", "spring_symbol_count": N },
    "QuartzCore": { ... },
    "AnimationKit": { "load_base": "0x...", ... },
    "SystemUIAnimationKit": { "load_base": "0x...", ... },
    "SpringBoard": { ... },
    "SwiftUI": { ... }
  },
  "anchor_verification": {
    "mass_address": "0x1848c8110", "mass_value": 1.0, "verified": true,
    "stiffness_address": "0x1848c8118", "stiffness_value": 100.0, "verified": true,
    "damping_address": "0x1848c8120", "damping_value": 18.0, "verified": true
  },
  "toolchain_trusted": true
}
```

## Completion Gate
`python3 tools/verify_phase.py anim_phase_1a_workspace_baseline`

Verification checks:
- `phase_1a_workspace_baseline.json` exists and is valid JSON
- `anchor_verification.toolchain_trusted` is `true`
- All 6 frameworks have `load_base` populated with a hex address
