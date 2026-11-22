# Agent Prompt: Phase 3 - Kernelcache, SPTM, TXM & ExclaveOS Specialist

## Mission
Execute **Phase 3: Kernelcache, SPTM, TXM & ExclaveOS Deep Dive**.
Reverse engineer the raw Mach-O kernelcache images, analyze the differential between `release` and `research` builds, dissect the Secure Page Table Monitor (SPTM) and Trusted Execution Monitor (TXM), and trace ExclaveOS security boundaries.

## Required Deliverables
1. `artifacts/kernel/kext_catalog_release.json` & `artifacts/kernel/kext_catalog_research.json`:
   - Extracted KEXT bundles (identifiers, version, segment offsets, dependencies).
2. `artifacts/kernel/kext_diff.json`:
   - Detailed delta comparing release vs research kernelcache (extra debug symbols, test drivers, research privileges).
3. `artifacts/kernel/sptm_analysis.json` & `artifacts/kernel/txm_analysis.json`:
   - Architecture, entrypoints, and EL2/EL3 security boundary hooks.
4. `findings/03_KERNEL_AND_CORE_SECURITY.md`:
   - In-depth architectural treatise on iOS 27 XNU kernel, SPTM memory protection, TXM isolation, and Exclave microkernel interfaces.

## Available Tools & Procedures
1. Use REA (`rea open_binary`, `rea inspect_macho`, `rea binary_overview`, `rea procedure_pseudo_code`).
2. Use Ghidra MCP tools (`ghidra decompile_function`, `ghidra get_function_xrefs`).
3. Extract `sptm.t8150.release.im4p` and `txm.iphoneos.*.im4p` using `tools/parse_im4p.py`.
4. Verify results with `python3 tools/verify_phase.py phase_03_kernel_sptm_txm`.
