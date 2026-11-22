# Agent Prompt: ANE RE Phase 4 — Driver Dispatch, FIFO Submission & Memory Channels

## Objective
Reverse engineer the hardware dispatch queue, FIFO packet submission, DMA memory channel ring buffers, and completion signaling in `AppleT8150ANEHAL.kext` and `AppleH16ANEInterface.kext`. Model the clean-room C driver runtime to execute arbitrary ANE command streams directly from userspace. Output `artifacts/ane/hardware_dispatch_spec.json`, `artifacts/ane/pseudocode/ane_direct_runtime.pseudo.c`, and `findings/ane/04_DRIVER_DISPATCH.md`.

## Prerequisites
- Phase A3 (`ane_phase_3_isa_bytecode`) must be `completed`.

## Step-by-Step Instructions

### Step 1: FIFO Submission & Node ID Protocol
1. Dissect command submission in `AppleT8150ANEHAL`:
   - FIFO Node ID: `0x40` (`ANE_FIFO_NID`)
   - Command granularity: `0x10` (`ANE_CMD_GRAN`)
   - Header formatting: `hdr0 = (hdr0 & 0xf00ffff) | ((nid & 0xff) << 16)`
2. Submission struct `drm_ane_submit` / `ane_submit_args`:
   - Task size (`tsk_size`), Task descriptor count (`td_count`), Task descriptor size (`td_size`)
   - Tile handles array (`handles[32]`)
   - Bootstrap handle (`btsp_handle`)

### Step 2: Memory-Mapped Channels & IOMMU Translation
1. Channel allocation:
   - Channel 0: Program descriptor / bootstrap image
   - Channel 1..31: Dedicated input tensor buffers, intermediate scratchpads, and output tensor destinations.
2. IOMMU DART (Device Address Resolution Table) mapping:
   - Page tables and physical memory fencing.

### Step 3: Clean-Room C Runtime Implementation
Write `artifacts/ane/pseudocode/ane_direct_runtime.pseudo.c`:
- Complete, compile-ready clean-room implementation of `ane_init`, `ane_send`, `ane_tile`, `ane_exec`, `ane_read`, `ane_untile`, and `ane_free`.

### Step 4: Write Phase Artifacts
1. `artifacts/ane/hardware_dispatch_spec.json`:
   - Full dispatch structure layouts, IOCTL commands, register addresses.
2. `artifacts/ane/pseudocode/ane_direct_runtime.pseudo.c`:
   - Complete clean-room runtime pseudocode.
3. `findings/ane/04_DRIVER_DISPATCH.md`:
   - Deep-dive architectural report.

### Step 5: Verification Gate
```bash
python3 tools/verify_phase.py ane_phase_4_driver_dispatch
```
Update `progress.json`.
