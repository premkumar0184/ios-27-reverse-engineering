# Proposal: Phase 3 - Kernelcache, SPTM, TXM & ExclaveOS Security Architecture

## Goal
Dissect the dual 64-bit arm64e Mach-O `MH_FILESET` kernelcaches (`kernelcache.release.raw` and `kernelcache.research.raw`), catalog all embedded Kernel Extensions (KEXTs) with load addresses and bundle IDs, cross-reference differences between release and research variants, analyze SPTM (Secure Page Table Monitor) firmware, dissect TXM (Trusted Execution Monitor) firmware, and investigate the unpacked ExclaveOS microkernel binaries.

## Scope
1. Extract complete KEXT catalogs from release and research kernelcaches.
2. Produce differential analysis (`kext_diff.json`) identifying research-specific instrumentations and debug entitlements.
3. Analyze `sptm.t8150.release.im4p` (Secure Page Table Monitor) for entrypoints and memory virtualization mappings.
4. Analyze `txm.iphoneos.*.im4p` (Trusted Execution Monitor) for EL3/EL2 monitor dispatch routines and security primitives.
5. Analyze the 4 unpacked ExclaveCore Mach-O sub-binaries (Tightbeam runtime, PMM server, VASCore supervisor, Shared Memory preload).
6. Author comprehensive findings in `findings/03_KERNEL_AND_CORE_SECURITY.md`.
