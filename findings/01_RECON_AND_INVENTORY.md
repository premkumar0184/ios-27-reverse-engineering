# Phase 1: IPSW Reconnaissance, Manifest Parsing & Component Inventory

## 1. Executive Summary & Hardware Topology

Phase 1 establishes the empirical foundation for the reverse engineering pipeline by systematically dissecting all metadata manifests, root properties, disk images, and peripheral firmware containers present in the `iPhone18,3_27.2_24B119_Restore` restore bundle.

### Verified Target Specifications
- **Operating System**: Apple iPhone OS / iOS 27.2
- **Build Identifier**: `79DC7400-CE82-11F1-B523-97A425208D9D`
- **Product Build Version**: `24B119`
- **Build Train**: `RaveB`
- **Device Class**: `v57ap`
- **Target Hardware Model**: `iPhone18,3`
- **Platform / SoC Identifier**: `t8150` (Apple Silicon Next-Gen Architecture, CPID `0x8150` / `33104`)
- **Board Identifier (BDID)**: `8`
- **Security Domain (SDOM)**: `1`
- **Cellular Baseband Package**: `Mav25-2.20.04.Release.bbfw`
- **Vinyl Firmware**: `vinyl_20.vnlfw`

```
+-----------------------------------------------------------------------------------------+
|                         iOS 27.2 (24B119) HARDWARE TOPOLOGY                             |
+-----------------------------------------------------------------------------------------+
|  Target Hardware: iPhone18,3 (DeviceClass: v57ap, BoardID: 8)                           |
|  SoC Family: Apple T8150 (CPID: 33104 / 0x8150)                                         |
|  Security Modes: SecureROM DFU (134250832), Production / Demotion Override Supported    |
|  Restore Engine: FDRSupport=True, AttestationMode=8, ImageName=V57RestoreIPSW           |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Plist Dissection & Restore Variant Analysis

Parsing `BuildManifest.plist`, `Restore.plist`, `SystemVersion.plist`, and `RestoreVersion.plist` revealed five distinct `BuildIdentities`, demonstrating dual production and security research operational paths:

| Identity Index | Restore Variant | Build Number | Manifest Components | Security Policy & Nonce Requirements |
| :---: | :--- | :---: | :---: | :--- |
| **0** | Customer Erase Install (IPSW) | `24B119` | 167 | Requires Nonce Slot: Yes; UID Mode: Yes; Wipe behavior: Erase |
| **1** | Customer Upgrade Install (IPSW) | `24B119` | 167 | In-place OTA upgrade; Preserves user data partition |
| **2** | Research Customer Erase Install | `24B119` | 167 | Apple Security Research Device (SRD) variant; Debug entitlements |
| **3** | Research Customer Upgrade Install | `24B119` | 167 | Research upgrade build; Dual research kernelcache binding |
| **4** | Recovery Customer Install | `24B119` | 69 | Minimal bootstrap ramdisk and recovery boot chain |

### Critical Manifest Properties Extracted
From `BuildManifest.plist` Info dictionary:
```xml
<dict>
    <key>DeviceClass</key>
    <string>v57ap</string>
    <key>BuildTrain</key>
    <string>RaveB</string>
    <key>BuildNumber</key>
    <string>24B119</string>
    <key>ContentEncoding</key>
    <string>aea</string>
    <key>Cryptex1,AppOSSize</key>
    <integer>16</integer>
    <key>Cryptex1,SystemOSSize</key>
    <integer>6030</integer>
    <key>MinimumSystemPartition</key>
    <integer>9522</integer>
    <key>OSDiskImageSize</key>
    <integer>10072</integer>
    <key>RestoreAttestationMode</key>
    <integer>8</integer>
    <key>RestoreBehavior</key>
    <string>Erase</string>
</dict>
```

---

## 3. Filesystem Images & Container Inventory

The restore bundle contains nine primary root partition images, cryptex volumes, ramdisks, and kernelcaches. Each has been classified by packaging format, encryption status, and designated restore role:

| Image Filename | Encrypted (AEA) | Container / Format | Physical Size | Decrypted / Virtual Size | Apple Restore Role (`BuildIdentity`) |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `141-08876-216.dmg.aea` | **Yes** | AEA1 (Profile 1, LZFSE) | 9.12 GB | **9.84 GB** (10,561,257,472 B) | `OS` (Full Root Filesystem: SpringBoard, Frameworks) |
| `141-09724-226.dmg.aea` | **Yes** | AEA1 (Profile 1, LZFSE) | 2.41 GB | **5.89 GB** (6,322,913,280 B) | `Cryptex1,SystemOS` (`dyld_shared_cache_arm64e`) |
| `141-08904-238.dmg.aea` | **Yes** | AEA1 (Profile 1, LZFSE) | 536.8 MB | **590.0 MB** (631,242,752 B) | `Ap,ExclaveOS` (Exclave Microkernel Root) |
| `141-09644-240.dmg.aea` | **Yes** | AEA1 (Profile 1, LZFSE) | 260.0 MB | **245.4 MB** (257,355,284 B) | `OS` (Customer Upgrade Delta Partition) |
| `141-08824-244.dmg` | **No** | Raw APFS (`NXSB`) | 16.0 MB | 16.0 MB | `Cryptex1,AppOS` (Safari, WebKit, Notification Bundles) |
| `141-09491-242.dmg` | **No** | IM4P (`rdsk`) -> APFS | 247.4 MB | 247.4 MB (60,416 blocks) | `RestoreRamDisk` (Erase Install Recovery Environment) |
| `141-10399-240.dmg` | **No** | IM4P (`rdsk`) -> APFS | 245.3 MB | 245.3 MB (59,904 blocks) | `RestoreRamDisk` (Upgrade Install Recovery Environment) |
| `kernelcache.release.v57` | **No** | IM4P (`krnl`) -> LZFSE | 23.7 MB | **75.33 MB** (Mach-O 64-bit) | `KernelCache` / `RestoreKernelCache` (Production XNU) |
| `kernelcache.research.v57`| **No** | IM4P (`krnl`) -> LZFSE | 23.7 MB | **75.33 MB** (Mach-O 64-bit) | `KernelCache` (Research XNU with extra debug symbols) |

---

## 4. Firmware Subsystems & Peripheral Coprocessor Mapping

The `Firmware/` hierarchy contains 126 files distributed across 25 specialized hardware controllers. Every peripheral subsystem has been mapped to its hardware coprocessor and load stage:

| Subsystem Directory | Component Count | Hardware Identifier | Firmware Type / Format | Function & Architectural Domain |
| :--- | :---: | :--- | :--- | :--- |
| `Firmware/all_flash/` | 13 | LLB, iBoot, SEP, DevTree | IM4P containers | Application Processor Boot Chain (EL0/EL1/EL2) |
| `Firmware/dfu/` | 4 | iBSS, iBEC | IM4P containers | DFU Recovery Bootloaders (Release & Research) |
| `Firmware/image4/` | 2 | `exclavecore_bundle` | IM4P (`excl` / `BUND`) | ExclaveOS Microkernel Bundle (`knlr`, `knlu`, `tsru`) |
| `Firmware/AOP/`, `AOP2/`| 2 | `aopfw-v57aop*` | IM4P (`aopf`, `aop2`) | Always-On Processor Sensor Hub (RTOS) |
| `Firmware/ane/` | 1 | `h18_ane_fw_apollo_v5x` | IM4P (`anef`) | Apple Neural Engine (ANE) Inference Coprocessor |
| `Firmware/agx/` | 2 | `armfw_g18p`, `armfw1_g18p`| IM4P (`gfxf`, `gf1f`) | Apple G18P Metal GPU Microcode |
| `Firmware/Rose/` | 3 | Rose UWB | Binary / Patch table | Ultra-Wideband (UWB) Spatial Positioning |
| `Firmware/SE/` | 2 | `StockholmE` | Secure Element FW | Apple Pay, NFC Controller, and eSE Microcode |
| `Firmware/ave/` | 10 | `AppleAVE2FW_H18*` | IM4P (`ave0`-`ave8`) | Hardware Video Encoder / Decoder Multi-Core Units |
| `Firmware/dcp/` | 2 | `t8150dcp*` | IM4P (`dcpf`) | Display Coprocessor & Timing Controller |
| `Firmware/msr/`, `pmc/` | 5 | `t8150msr`, `t8150pmc` | IM4P (`msrf`, `pmcf`) | System Power, Thermal, and Memory Scaling Controllers |
| `Firmware/` Root | 7 | `Mav25-2.20.04.Release` | `.bbfw` (ZIP), `.vnlfw` | Cellular Modem Baseband Package & Vinyl RF Firmware |

### Discovered Auxiliary Plists (Unreferenced in Main Manifest)
During the bidirectional mapping audit, 28 auxiliary configuration plists were isolated in `Firmware/`. These contain undocumented hardware patch definitions:
- `Firmware/Aries/JasmineIR1,FwPatch*.plist`: 16 calibration files for the FaceID infrared structured light projector.
- `Firmware/Summerville/Yonkers,SysTopPatch*.plist`: Touch-screen controller firmware patches.
- `Firmware/Volchok/X3357/`: Ambient light and proximity sensor calibration matrices.
- `Firmware/all_flash/sep-firmware.v57.RELEASE.im4p.plist`: Secure Enclave load parameters and memory requirements.

---

## 5. Artifact Verification & Execution Gate Log

All generated Phase 1 artifacts have been mechanically verified:

```bash
$ python3 tools/verify_phase.py phase_01_recon_and_inventory
============================================================
Verifying Phase: IPSW Reconnaissance, Manifest Parsing & Component Inventory (phase_01_recon_and_inventory)
============================================================
[*] Checking 4 required disk artifacts...
  [+] Verified artifact: artifacts/manifests/manifest_summary.json (4486 bytes)
  [+] Verified artifact: artifacts/manifests/image_inventory.json (1938 bytes)
  [+] Verified artifact: artifacts/manifests/firmware_inventory.json (20120 bytes)
  [+] Verified artifact: artifacts/manifests/component_map.json (38924 bytes)
[*] Verifying findings document: findings/01_RECON_AND_INVENTORY.md...
  [+] Findings document verified (passed authenticity & structural richness scans).

[PASS] All verification checks PASSED for phase 'phase_01_recon_and_inventory'.
```

### Generated Machine-Readable Data Files
1. [`artifacts/manifests/manifest_summary.json`](file:///home/prem/Projects/iOS%2027/artifacts/manifests/manifest_summary.json): Complete dictionary of plist declarations, build IDs, attestation parameters, and BuildIdentity trees.
2. [`artifacts/manifests/image_inventory.json`](file:///home/prem/Projects/iOS%2027/artifacts/manifests/image_inventory.json): Byte-accurate catalogue of all root filesystem images with encryption classification.
3. [`artifacts/manifests/firmware_inventory.json`](file:///home/prem/Projects/iOS%2027/artifacts/manifests/firmware_inventory.json): Full survey of all 126 firmware elements.
4. [`artifacts/manifests/component_map.json`](file:///home/prem/Projects/iOS%2027/artifacts/manifests/component_map.json): Bidirectional mapping connecting every file to its Apple restore identity.

Phase 1 is complete and verified. The workspace is formally ready to transition to **Phase 2: Cryptographic Decryption & Full Filesystem Extraction**.
