# Design: Phase 3 - Kernelcache, SPTM, TXM & ExclaveOS Security Architecture

## Architecture & Analysis Strategy
1. **Mach-O `MH_FILESET` Dissection**: Modern Apple Silicon kernelcaches are `MH_FILESET` containers containing embedded Mach-O binaries for the kernel and every KEXT via `LC_FILESET_ENTRY` load commands. We will implement an automated parser to walk fileset entries, extract bundle identifiers, virtual memory addresses, file offsets, and Mach-O segments.
2. **KEXT Differential Matrix**: Cross-reference release vs. research filesets to identify exclusive KEXTs, symbol differences, and security research capabilities.
3. **SPTM & TXM Firmware Dissection**: Unpack `sptm.t8150.release.im4p` and `txm.iphoneos.*.im4p` via `tools/parse_im4p.py`. Dissect header load commands, entry vectors, and architecture descriptors.
4. **ExclaveOS Microkernel Dissection**: Reverse engineer the extracted Mach-O binaries (`00_tightbeam_runtime.macho`, `01_pmm_server.macho`, `02_vascore_platform.macho`, `03_jg_sharedmem_preload.macho`) to document IPC topologies and memory isolation barriers.
5. **Phase Verification**: Validate required artifacts and findings structure via `tools/verify_phase.py phase_03_kernel_sptm_txm`.
