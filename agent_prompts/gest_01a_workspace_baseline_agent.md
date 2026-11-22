# Agent Prompt: Gesture RE Phase 1A — Workspace Baseline & DSC Address Resolution

## Objective
Open `Gestures.framework` from subcache `.03`, verify it is correctly positioned at VM base `0x18a169000`, confirm the pan touch-slop anchors from the scrolling RE, and map all Mach-O segments. Write the baseline JSON artifact.

## Prerequisites
- Read `.agent_rules/CORE_RULES.md` and `.agent_rules/TOOLING_GUIDE.md` before starting.
- Confirm `progress.json` shows `gest_phase_1a_workspace_baseline` as `pending` or `active`.

## Step-by-Step Instructions

### Step 0: Graphify Orientation (mandatory first step)
```bash
graphify query "Gestures.framework UIGestureRecognizer arbitration"
graphify query "touch slop velocity threshold gesture"
graphify path "UIGestureRecognizer" "Gestures"
```
Document any existing nodes related to gesture recognition.

### Step 1: Open Gestures.framework via REA
```json
{
  "ServerName": "rea",
  "ToolName": "open_binary",
  "Arguments": {
    "path": "/home/prem/Projects/iOS 27/artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e",
    "image_path": "/System/Library/PrivateFrameworks/Gestures.framework/Gestures"
  }
}
```
If REA returns `target_unavailable`, fall back to Python raw parsing (see Step 1B).

### Step 1B: Fallback — Python raw extraction
```python
import struct
from pathlib import Path

subcache = Path("artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.03")
file_offset = 0x01d69000
vm_base = 0x18a169000

with open(subcache, 'rb') as f:
    f.seek(file_offset)
    mach_header = f.read(32)
    magic, cpu_type, cpu_subtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', mach_header)
    print(f"Magic: {hex(magic)}, CPU: {hex(cpu_type)}, Cmds: {ncmds}")
```
Expected: magic = `0xFEEDFACF` (MH_MAGIC_64), cpu_type = `0x0100000C` (ARM64).

### Step 2: Verify Pan Slop Anchors
Open UIKitCore in subcache `.01` and verify the known scrolling spring addresses:
- `0x1848c8110` → `1.000` (SpringMass)
- `0x1848c8118` → `100.000` (SpringStiffness)
- `0x1848c8120` → `18.000` (SpringDamping)

Also search for the pan touch-slop constants (should be `10`, `4`, `2`, `0` stored as int32 or float64).

### Step 3: Map Gestures.framework Mach-O Segments
Use `inspect_macho` or `binary_overview` on the opened Gestures binary. Record:
- All `__TEXT`, `__DATA`, `__DATA_CONST`, `__AUTH_CONST` segments
- Section sizes and VM addresses
- Load commands (LC_ID_DYLIB, LC_LOAD_DYLIB for imports)
- UUID

### Step 4: Write Phase Artifact
Write `artifacts/gesture/phase_1a_workspace_baseline.json`:
```json
{
  "phase": "gest_phase_1a_workspace_baseline",
  "frameworks": {
    "Gestures": {
      "dsc_image_path": "/System/Library/PrivateFrameworks/Gestures.framework/Gestures",
      "subcache_slice": ".03",
      "vm_base": "0x18a169000",
      "file_offset_in_subcache": "0x01d69000",
      "mach_header_magic": "0xFEEDFACF",
      "cpu_type": "ARM64E",
      "uuid": "<extracted>",
      "segments": [ ... ],
      "load_verified": true
    },
    "UIKitCore": { ... }
  },
  "anchor_verification": {
    "spring_mass_at_0x1848c8110": 1.0,
    "spring_stiffness_at_0x1848c8118": 100.0,
    "spring_damping_at_0x1848c8120": 18.0,
    "pan_slop_tiers": [10, 4, 2, 0],
    "toolchain_trusted": true
  }
}
```

### Step 5: Verify & Complete
```bash
python3 tools/verify_phase.py gest_phase_1a_workspace_baseline
```
Update `progress.json` `active_phase_id` and set `gest_phase_1a_workspace_baseline.status = "completed"`.

## Required Output Artifact
- `artifacts/gesture/phase_1a_workspace_baseline.json` — Must contain `frameworks`, `anchor_verification`, and `toolchain_trusted: true`

## Confidence Gate
Do not proceed to Phase 1B unless `toolchain_trusted: true` and Gestures.framework segments are mapped.
