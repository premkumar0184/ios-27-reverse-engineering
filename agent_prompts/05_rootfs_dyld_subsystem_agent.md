# Agent Prompt: Phase 5 - Core System Runtime, dyld_shared_cache & System Daemons Specialist

## Mission
Execute **Phase 5: Core System Runtime, dyld_shared_cache & System Daemons**.
Inspect the decrypted `Cryptex1,SystemOS` DMG (`artifacts/crypto/141-09724-226_cryptex_systemos.dmg`) and rootfs utilities. Reverse engineer dynamic linker structures (`dyld`), inspect `dyld_shared_cache_arm64e`, map core system daemons, and reconstruct IPC/Mach service registration topologies.

## Required Deliverables
1. `artifacts/rootfs/daemon_catalog.json`:
   - Catalog of core daemons (launchd, commcenter, wifid, bluetoothd, securityd, amfid, trustd) with binary paths, Mach service names, and privilege levels.
2. `artifacts/rootfs/mach_services_map.json`:
   - System-wide Mach service endpoint mapping cross-referencing launch daemon plists to implementing binaries.
3. `artifacts/rootfs/shared_cache_overview.json`:
   - Header, slide, mapping table, and framework count for `dyld_shared_cache_arm64e`.
4. `findings/05_ROOTFS_AND_FRAMEWORKS.md`:
   - Comprehensive analysis of system daemons, dyld dynamic linker dispatch, and framework interdependencies.

## Available Tools & Procedures
1. Use `python3 tools/extract_dmg.py extract artifacts/crypto/141-09724-226_cryptex_systemos.dmg *dyld_shared_cache* artifacts/rootfs/shared_cache/` to extract shared cache.
2. Use `python3 tools/extract_dmg.py extract artifacts/crypto/141-08876-216_rootfs.dmg System/Library/LaunchDaemons/* artifacts/rootfs/launch_daemons/` to extract launch plists.
3. Disassemble `dyld` and daemons using REA (`rea open_binary`, `rea inspect_macho`) and Ghidra.
4. Verify results with `python3 tools/verify_phase.py phase_05_rootfs_dyld_frameworks`.
