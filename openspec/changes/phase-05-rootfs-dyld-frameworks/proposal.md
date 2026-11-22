# Proposal: Phase 5 - Core System Runtime, dyld_shared_cache & System Daemons

## Goal
Dissect the core userland execution environment, dynamic linker shared cache (`dyld_shared_cache_arm64e`), launch daemon configurations, and Mach/XPC service registration graph extracted from the decrypted Cryptex1 SystemOS and RootFS APFS disk images.

## Scope
1. **Dynamic Linker Shared Cache**: Extract and parse `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e` from `141-09724-226_cryptex_systemos.dmg`. Analyze headers, mappings, slide tables, and embedded dylibs/frameworks (`artifacts/rootfs/shared_cache_overview.json`).
2. **Launch Daemons & System Services**: Extract `/System/Library/LaunchDaemons` and `/Library/LaunchDaemons` plists from `141-08876-216_rootfs.dmg`. Catalog all core daemons (`launchd`, `commcenter`, `wifid`, `bluetoothd`, `securityd`, `amfid`, `trustd`) in `artifacts/rootfs/daemon_catalog.json`.
3. **Mach Services & XPC Endpoint Map**: Reconstruct the system-wide IPC registration topology mapping Mach service names to backing binaries and entitlement requirements in `artifacts/rootfs/mach_services_map.json`.
4. **Architectural Treatise**: Author comprehensive documentation in `findings/05_ROOTFS_AND_FRAMEWORKS.md`.
5. **Phase Verification**: Validate with `python3 tools/verify_phase.py phase_05_rootfs_dyld_frameworks`.
