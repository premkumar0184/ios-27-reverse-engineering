# Design: Phase 5 - Core System Runtime, dyld_shared_cache & System Daemons

## Architecture & Extraction Strategy
1. **APFS DMG Extraction**:
   - Use `tools/extract_dmg.py` with `7z` to extract `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e*` from `artifacts/crypto/141-09724-226_cryptex_systemos.dmg`.
   - Extract `System/Library/LaunchDaemons/` plists and binaries (`/usr/libexec`, `/usr/sbin`) from `artifacts/crypto/141-08876-216_rootfs.dmg`.
2. **Dynamic Linker & Shared Cache Dissection**:
   - Parse `dyld_cache_header` (magic `dyld_v1   arm64e`, mapping count, images offset, sub-caches).
   - Walk image descriptors to catalog all system dylibs and private frameworks.
3. **Daemon & Mach Service IPC Reification**:
   - Parse XML/binary property lists to extract `Label`, `ProgramArguments`, `MachServices`, `POSIXSpawnType`, and launch constraints.
   - Cross-reference Mach services to binaries and client connection entitlements.
4. **Validation**:
   - Generate `artifacts/rootfs/daemon_catalog.json`, `artifacts/rootfs/mach_services_map.json`, and `artifacts/rootfs/shared_cache_overview.json`.
   - Author `findings/05_ROOTFS_AND_FRAMEWORKS.md` and pass `tools/verify_phase.py phase_05_rootfs_dyld_frameworks`.
