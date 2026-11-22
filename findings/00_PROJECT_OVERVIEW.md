# iOS 27.2 Reverse Engineering Project: Master Overview (Full-Stack)

## Target Identification
- **Target OS**: Apple iOS / iPhone OS 27.2
- **Build ID**: `79DC7400-CE82-11F1-B523-97A425208D9D`
- **Product Build Version**: `24B119`
- **Device Class**: `v57ap`
- **Target Hardware**: `iPhone18,3`
- **SoC Identifier**: `t8150` (Apple Silicon Next-Gen Architecture)
- **Build Train**: `RaveB`
- **Firmware Package**: `iPhone18,3_27.2_24B119_Restore`

---

## Complete Scope: 100% Reachable System
Every layer of the iOS 27 system is reachable and verified on this machine:
1. **The User Experience & UI Layer** (Unlocked via Verified AEA Key):
   - `SpringBoard.app`: Main desktop, lock screen, control center, notifications, and Dynamic Island presentation managers.
   - `Assets.car` / `Artwork.car`: Vector renditions, SF Symbols, app icons, and UI textures.
   - Core Applications: `MobileSafari`, `Preferences` (Settings), `MobileSMS`, `Camera`, `Health`, `Wallet`.
2. **System Daemons & Shared Cache** (Unlocked via Verified AEA Key):
   - `dyld_shared_cache_arm64e`: Complete pre-linked cache of all system frameworks.
   - Core Daemons: `launchd`, `commcenter`, `securityd`, `wifid`, `bluetoothd`, `amfid`, `trustd`.
3. **ExclaveOS Microkernel Security Domain** (Unlocked via Verified AEA Key & BUND Archive):
   - Microkernel components: `knlr` (kernel release), `knlu` (kernel user), and `tsru` (trust runtime).
4. **SPTM & TXM Core Monitors** (Uncompressed Mach-O 64-bit):
   - Secure Page Table Monitor (SPTM) and Trusted Execution Monitor (TXM) at EL2/EL3.
5. **Dual XNU Kernelcache** (Uncompressed Mach-O 64-bit):
   - `kernelcache.release.v57` and `kernelcache.research.v57` (75.33 MB Mach-O binaries).
6. **Hardware Coprocessors & Bootchain**:
   - AOP/AOP2, ANE Neural Engine, AGX GPU, Rose UWB, Baseband modem package (`bbfw`), SEP, iBoot, and DeviceTree.

---

## 8-Phase Full-Stack Reverse Engineering Pipeline

```
[Phase 1: Manifest Recon & Hardware Topology]
                      │
                      ▼
[Phase 2: Decryption & Full Filesystem Extraction] (AEA + IM4P + APFS Unpack)
                      │
                      ▼
[Phase 3: Kernelcache, SPTM, TXM & ExclaveOS Microkernel]
                      │
                      ▼
[Phase 4: Peripheral Coprocessors & Baseband Modem]
                      │
                      ▼
[Phase 5: Core System Runtime, dyld_shared_cache & Daemons]
                      │
                      ▼
[Phase 6: Apple UI Layer, SpringBoard & System Applications]
                      │
                      ▼
[Phase 7: Platform Security, TrustCache & Full Entitlement Matrix]
                      │
                      ▼
[Phase 8: Knowledge Graph Synthesis & Master Architectural Dossier]
```

---

## Operational Directives
- **Authoritative Tracker**: `progress.json`
- **Verification Gate**: `python3 tools/verify_phase.py <phase_id>`
- **Navigation Engine**: Graphify (`/graphify`, `graphify query`, `graphify path`)
- **Strict Evidence Rule**: Every technical claim must reference empirical binary data or offsets. Zero placeholder documentation permitted.
