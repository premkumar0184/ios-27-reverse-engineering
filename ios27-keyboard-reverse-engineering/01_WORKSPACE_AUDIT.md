# 01. Workspace Audit & Binary Distribution Specification

- **Target Build**: iOS 27.2 (Build `24B119`)
- **Hardware Platform**: `iPhone18,3` (SoC: Apple Silicon `t8150` / A19 Pro family)
- **Architecture**: `arm64e` (Pointer Authentication: `PAC00`, Page Size: 16 KB)
- **Integrity Mode**: Strict Read-Only Extraction & Reconstruction Baseline
- **Audit Date**: 2026-11-08

---

## 1. Executive Summary & Container Inventory

The iOS 27 keyboard ecosystem reverse engineering workspace (`/home/prem/Projects/iOS 27`) contains an exhaustive repository of Apple IPSW restore images, decrypted APFS containers, staged dyld shared-cache slices, and decompiled system manifests. 

A rigorous audit of the workspace reveals complete binary separation: all userland system daemons (`kbd`, `stickersd`) and standalone utilities (`FullKeyboardAccess.app`) exist as isolated Mach-O executables on the decrypted root filesystem (`141-08876-216_rootfs.dmg`), whereas all system frameworks, rendering engines (`UIKitCore`, `TextInputUI`), arbiters (`KeyboardArbiter`), language managers (`TextInputCore`, `TextInputCJK`), and compiled layout bundles (`TextInput_*.bundle`) have been pre-linked and stripped into the 81 subcaches of the cryptex dynamic linker shared cache (`141-09724-226_cryptex_systemos.dmg`).

### Master Container Catalog

| Container Path | Format / Filesystem | File Size (Bytes) | SHA-256 Digest | Status & Access Policy | System Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `iPhone18,3_27.2_24B119_Restore/` | Directory / IPSW Package | ~13 GB total | N/A (Directory) | **Read-Only Baseline** (`chmod 444`) | Master IPSW restore bundle containing raw firmware, bootloaders, and AEA archives |
| `iPhone18,3_27.2_24B119_Restore/141-08876-216.dmg.aea` | Apple Encrypted Archive (AEA Profile 1) | 9,126,805,504 | `396263cdbd3aeab8164a1a12f45b9cfa83ae7d99c015435a1664453909d68212` | **Read-Only Original** | Encrypted OS Root Filesystem archive |
| `iPhone18,3_27.2_24B119_Restore/141-09724-226.dmg.aea` | Apple Encrypted Archive (AEA Profile 1) | 2,415,919,104 | `8790eefa11031e50181b3eef19ad7b11b8baa18fa70f1785c2c65167bec4da36` | **Read-Only Original** | Encrypted Cryptex1 SystemOS archive |
| `iPhone18,3_27.2_24B119_Restore/141-08904-238.dmg.aea` | Apple Encrypted Archive (AEA Profile 1) | 536,870,912 | `0b67f6821d673c20234dd26fca65cbf8861b8ade155f11766712b29f273aef70` | **Read-Only Original** | Encrypted ExclaveOS Microkernel archive |
| `iPhone18,3_27.2_24B119_Restore/141-09644-240.dmg.aea` | Apple Encrypted Archive (AEA Profile 1) | 260,046,848 | `7ba3784a075d756d4640695fe7df3e6cfe6407c4c708234481215ba97fda9105` | **Read-Only Original** | Encrypted RecoveryOS / Update OS archive |
| `iPhone18,3_27.2_24B119_Restore/141-09491-242.dmg` | APFS Disk Image | 247,463,963 | `e26da3df75d2b3232d7eedc776222e327b0fe6e774466e66ce2aa52fd6336a63` | **Read-Only Original** | Unencrypted Restore RamDisk |
| `iPhone18,3_27.2_24B119_Restore/141-10399-240.dmg` | APFS Disk Image | 245,366,811 | `42f7e2fe5f3bf6add09156f569c750bccf06d458cbe0ec82559cbb64d4a46cca` | **Read-Only Original** | Unencrypted Secondary Restore RamDisk |
| `iPhone18,3_27.2_24B119_Restore/141-08824-244.dmg` | APFS Disk Image | 16,777,216 | `8a70ca8f34f8604f436dd3ec23d27aea21a9dc5b28f114acc7ada0ee76df010c` | **Read-Only Original** | Unencrypted Cryptex1 AppOS image |
| `artifacts/crypto/141-08876-216_rootfs.dmg` | APFS Disk Image (Blocksize 4096) | 10,561,257,472 | `00fff0758bcf28a458021c95ad746bbf78102ce1bf4b1fb0ac09c9926b6c8137` | **Decrypted Master Image** (Read-Only) | Decrypted RootFS: hosts system daemons, launchd configs, asset catalogs, and 98 layout bundles |
| `artifacts/crypto/141-09724-226_cryptex_systemos.dmg` | APFS Disk Image (Blocksize 4096) | 6,322,913,280 | `b316f66dc5f79c7bafee40552b6de3b73114d0a31f27b94ffc5b08d3fd9481c5` | **Decrypted Master Image** (Read-Only) | Decrypted SystemOS Cryptex: hosts master `dyld_shared_cache_arm64e` and 81 subcaches |
| `artifacts/crypto/141-08904-238_exclaveos.dmg` | APFS Disk Image (Blocksize 4096) | 631,242,752 | `c9d40574be65d376906eee095dda0cf92db6608a56629efe865cbd6e4ff9e242` | **Decrypted Master Image** (Read-Only) | Decrypted ExclaveOS microkernel and Tightbeam IPC runtime binaries |
| `artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/` | Staging Directory | 135,452,934 | N/A (Directory) | **Staged Cache Components** | Staged master header (`855f9c...`), subcache `.36` (`807631...`), and selector atlas (`a902a4...`) |
| `artifacts/rootfs/shared_cache_overview.json` | JSON Metadata Index | 1,296,416 | `36d7c4480aff3738196138744203c9faebc884d5505f854c8188908d8060c5c2` | Verified Structural Artifact | Machine-parsed architectural manifest indexing 4,770 frameworks and 81 subcaches |

---

## 2. Container Structural Specifications

### 2.1 Restore Container (`iPhone18,3_27.2_24B119_Restore/`)
- **Origin**: Official Apple IPSW archive for iPhone 16 Pro Max (`iPhone18,3`, Board ID `v57ap`, SoC `t8150`).
- **Cryptographic Security Layer**: Four primary system partitions are encrypted at rest using Apple Encrypted Archive (AEA) Profile 1. Profile 1 employs `scrypt` key derivation with symmetric 256-bit AES-GCM encryption authenticated via root header MAC and cluster authentication tags.
- **Payload Inventory**:
  - `BuildManifest.plist` (1,461,641 bytes): Declares signing identities, digest manifests, component board mappings, and TrustCache registrations.
  - `Firmware/`: Contains peripheral coprocessor firmware (`sep-firmware.v57.RELEASE.im4p`, `Mav25-2.20.04.Release.bbfw`, `sptm.t8150.release.im4p`, `txm.iphoneos.release.im4p`).
  - `kernelcache.release.v57` (23,714,695 bytes) & `kernelcache.research.v57` (23,714,658 bytes): Dual `arm64e` `MH_FILESET` kernelcaches.

### 2.2 Decrypted Root Filesystem Container (`141-08876-216_rootfs.dmg`)
- **Filesystem Format**: Apple File System (APFS), Case-Sensitive, Inode Blocksize: 4096 bytes.
- **Volume Metrics**: Total uncompressed logical capacity: 10,561,257,472 bytes (~9.84 GiB). Total indexed filesystem records: 264,289 entries.
- **Keyboard Subsystem Distribution on RootFS**:
  - **Executable Daemons**: `/System/Library/TextInput/kbd` (292,688 bytes, Mach-O arm64e PAC00).
  - **Accessibility Applications**: `/System/Library/CoreServices/FullKeyboardAccess.app/FullKeyboardAccess` (259,328 bytes).
  - **LaunchDaemon Configurations**: `/System/Library/LaunchDaemons/com.apple.TextInput.kbd.plist` (1,397 bytes, declaring 17 MachServices).
  - **Declarative Layout Bundles**: 98 locale directories located at `/System/Library/TextInput/TextInput_*.bundle/` containing 710 layout and input mode property lists.
  - **Linguistic Data Assets**: `/System/Library/LinguisticData/` containing 755 dictionary packages (`RequiredAssets_*.bundle`) housing double-array tries (`sys.dic`), bigram cost matrices (`matrix.bin`), and language model transition tables (`lm.dat`, `fst.dat`).
  - **CoreUI Asset Catalogs**:
    - `System/Library/PrivateFrameworks/UIKitCore.framework/Artwork.bundle/Assets.car` (3,308,040 bytes, 1,058 renditions).
    - `System/Library/PrivateFrameworks/TextInputUI.framework/Assets.car` (1,168,296 bytes, 300 renditions).
    - `System/Library/PrivateFrameworks/UIKitCore.framework/CarPlayArtwork.bundle/Assets.car` (209,176 bytes).
  - **Vector CAML & Metal Shaders**:
    - Vector animations: `System/Library/PrivateFrameworks/TextInputUI.framework/Genmoji-*.ca/document.caml` (CoreAnimation vector shapes for Apple Intelligence Genmoji).
    - Metal swipe pipelines: `System/Library/PrivateFrameworks/TextInputUI.framework/TextInputUI_iOS.pipelinelib/` (precompiled `PathPipeline` GPU shaders).

### 2.3 Decrypted SystemOS Cryptex Container (`141-09724-226_cryptex_systemos.dmg`)
- **Filesystem Format**: APFS sealed system cryptex image, Blocksize: 4096 bytes.
- **Volume Metrics**: Uncompressed file size: 6,322,913,280 bytes (~5.89 GiB). Contains 87 specialized dynamic cache files totaling 7,551,548,968 bytes (~7.03 GiB).
- **Embedded dyld Shared Cache Architecture**:
  - Contains the production split cache `dyld_shared_cache_arm64e` and its 81 subcaches (`.01` through `.81`).
  - DriverKit cache: `System/DriverKit/System/Library/dyld/dyld_shared_cache_arm64e` (33,865,728 bytes).
  - Complete unstripped symbol database: `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.symbols` (1,251,819,520 bytes).
  - Selector and symbol atlas: `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.atlas` (3,102,982 bytes).

### 2.4 Staged Shared Cache Workspace (`artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/`)
- Houses staged components for low-latency analysis without mounting the 6.32 GB Cryptex disk image:
  - `dyld_shared_cache_arm64e` (802,816 bytes, SHA-256: `855f9c313795186c45b93c5ad082edbb989839dcc0f82a6b1b10d46c25784adf`): Master split-cache header file containing global mapping tables, slide info headers, subcache UUID descriptors, and image path lookup tables.
  - `dyld_shared_cache_arm64e.36` (131,547,136 bytes, SHA-256: `8076316dc72292e12ca13c4b935278113d1b33631ed376004b93f359adfe03ac`): Complete binary slice covering VM range `0x220400000` to `0x228134000`, containing `KeyboardArbiter.framework` and `SpringBoard.framework`.
  - `dyld_shared_cache_arm64e.atlas` (3,102,982 bytes, SHA-256: `a902a4c9e35b24c0aff2c29998d8713b9f10bcae7108484c4bf8b88a42bb1bbe`): AppleArchive container indexing all compressed export trie selectors.

---

## 3. Binary Separation vs. dyld Shared Cache Architecture

Apple's architectural paradigm in iOS 27 strictly separates executable binaries into two categories:
1. **Separated Standalone Binaries (RootFS)**: Executables that run as independent Mach tasks with their own address spaces and ASLR slide domains (`MH_EXECUTE`).
2. **Unified Embedded Frameworks (dyld Shared Cache)**: Dynamic libraries (`MH_DYLIB`) and bundle modules (`MH_BUNDLE`) pre-linked into a monolithic 64-bit address space spanning `0x180000000` to `0x2ffffffff`, sharing physical memory pages across all processes via Copy-On-Write (COW).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          iOS 27 BINARY DISTRIBUTION TOPOLOGY                           │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│   SEPARATED STANDALONE BINARIES (ROOTFS) │   EMBEDDED DYLD SHARED CACHE FRAMEWORKS     │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ - kbd (/System/Library/TextInput/kbd)    │ - UIKitCore.framework (Subcache .01)        │
│   Mach-O arm64e PAC00, 292 KB            │   UIKeyboardImpl, UIKeyboardLayoutStar      │
│   102 Entitlements, 8 MB Jetsam Budget   ├─────────────────────────────────────────────┤
│   17 MachServices                        │ - TextInput.framework (Subcache .03)        │
├──────────────────────────────────────────┤   TIKeyboardInput, TIKeyboardState          │
│ - FullKeyboardAccess                     ├─────────────────────────────────────────────┤
│   (/System/Library/CoreServices/FKA.app) │ - TextInputUI.framework (Subcache .03)      │
│   Mach-O arm64e PAC00, 259 KB            │   TUICandidateCell, TUIAssistantButtonBar   │
│   34 Entitlements, Event Tap Pipeline    ├─────────────────────────────────────────────┤
├──────────────────────────────────────────┤ - RemoteTextInput.framework (Subcache .23)  │
│ - stickersd                              │   RTIInputSystemClient, RTI Oneness IPC     │
│   (/System/Library/Support/stickersd)    ├─────────────────────────────────────────────┤
│   Mach-O arm64e PAC00, 324 KB            │ - KeyboardArbiter.framework (Subcache .36)  │
│   Sticker & Starmoji Indexer Service     │   _UIKeyboardArbiter, Focus Stealing        │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ - TextInputAppIntentsExtension           │ - TextInputCore.framework (Subcache .42)    │
│   (/System/Library/ExtensionKit/...)     │   FavoniusCandQualityFilter, Autocorrect    │
│   Mach-O arm64e PAC00, 102 KB            ├─────────────────────────────────────────────┤
│   Siri & App Shortcuts Integration       │ - TextInputCJK.framework (Subcache .69)     │
│                                          │   Mecabra Engine C++ Bridge, Kana Flick     │
│                                          ├─────────────────────────────────────────────┤
│                                          │ - 34 TextInput_*.bundle (Subcache .73)      │
│                                          │   Compiled input methods (en, zh, ja, etc.) │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

### 3.1 Separated Binaries Specification Matrix

| Binary Name | Absolute Path | Type | Architecture | File Size (Bytes) | Load Base | Entitlements | Primary MachServices / Roles |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`kbd`** | `/System/Library/TextInput/kbd` | `MH_EXECUTE` | `arm64e` (PAC00) | 292,688 | `0x100000000` | 102 | `com.apple.TextInput`, `com.apple.TextInput.shortcuts`, `com.apple.TextInput.emoji`, `com.apple.TextInput.rdt` |
| **`FullKeyboardAccess`** | `/System/Library/CoreServices/FullKeyboardAccess.app/FullKeyboardAccess` | `MH_EXECUTE` | `arm64e` (PAC00) | 259,328 | `0x100000000` | 34 | `com.apple.fullkeyboardaccess`, `com.apple.fullkeyboardaccess.gsEvents` |
| **`stickersd`** | `/System/Library/PrivateFrameworks/Stickers.framework/Support/stickersd` | `MH_EXECUTE` | `arm64e` (PAC00) | 324,640 | `0x100000000` | 28 | `com.apple.stickers.api`, `com.apple.stickers.recency`, `com.apple.stickers.StarmojiIndexerService` |
| **`TextInputAppIntentsExtension`** | `/System/Library/ExtensionKit/Extensions/TextInputAppIntentsExtension.appex/TextInputAppIntentsExtension` | `MH_EXECUTE` | `arm64e` (PAC00) | 102,448 | `0x100000000` | 16 | ExtensionKit AppIntents integration for keyboard actions |

### 3.2 dyld Shared Cache Architecture (81 Subcaches)

The master split cache `dyld_shared_cache_arm64e` defines the global virtual memory topology:
- **Magic**: `dyld_v1  arm64e\0`
- **Cache Type**: `2` (`Production Split Cache`)
- **Master Header Size**: 802,816 bytes
- **Global Base Virtual Address**: `0x180000000`
- **Total Registered Images**: 4,770 Mach-O images
- **Category Distribution**:
  - `PrivateFramework`: 3,256 images (68.3%)
  - `Other` (Bundles, App Extensions, Plugins): 724 images (15.2%)
  - `UsrLibDylib`: 383 images (8.0%)
  - `PublicFramework`: 368 images (7.7%)
  - `SystemSublibrary`: 39 images (0.8%)

#### Subcache Extension Taxonomy & Structural Layout

The 81 subcaches span extensions `.01` through `.81`. In addition to standard code-bearing slices, Apple isolates data and linkedit segments into dedicated specialized subcaches:
- **Code Slices**: `.01` – `.24`, `.27` – `.53`, `.56` – `.78` (Hold `__TEXT` segments for dylibs and bundles).
- **Data Slices (`*.dylddata`)**:
  - Subcache Index 24: `.25.dylddata` (VM Offset: `0x600f4000`, Size: 229,425,152 bytes)
  - Subcache Index 53: `.54.dylddata` (VM Offset: `0xe8120000`, Size: 228,847,616 bytes)
  - Subcache Index 78: `.79.dylddata` (VM Offset: `0x158020000`, Size: 231,149,568 bytes)
- **Read-Only Data Slices (`*.dyldreadonly`)**:
  - Subcache Index 25: `.26.dyldreadonly` (VM Offset: `0x71b50000`, Size: 196,935,680 bytes)
  - Subcache Index 54: `.55.dyldreadonly` (VM Offset: `0xf9274000`, Size: 195,891,200 bytes)
  - Subcache Index 79: `.80.dyldreadonly` (VM Offset: `0x166930000`, Size: 65,536 bytes)
- **LinkEdit Monolith (`*.dyldlinkedit`)**:
  - Subcache Index 80: `.81.dyldlinkedit` (VM Offset: `0x16693c000`, Size: 698,613,760 bytes / ~698.6 MB). Contains unified export tries, binding opcodes, lazy symbol pointers, and code signature blobs.

#### Core Keyboard & Text Processing Framework Subcache Matrix

| Subsystem Component | Virtual Load Base (`vmaddr`) | Subcache Extension | Subcache VM Base | File Offset in Subcache | Segment Protections |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`UIKitCore.framework`** | `0x184752000` | `.01` | `0x180400000` | `0x04352000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInput.framework`** | `0x18a6bd000` | `.03` | `0x188400000` | `0x022bd000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputUI.axbundle`** | `0x18c342000` | `.03` | `0x188400000` | `0x03f42000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputUI.framework`** | `0x18fa93000` | `.03` | `0x188400000` | `0x07693000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`CoreEmoji.framework`** | `0x1c153a000` | `.17` | `0x1c0400000` | `0x0113a000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`EmojiFoundation.framework`** | `0x1c1db9000` | `.17` | `0x1c0400000` | `0x019b9000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`RemoteTextInput.framework`** | `0x1dcd80000` | `.23` | `0x1d8400000` | `0x04980000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`KeyboardArbiter.framework`** | `0x226550000` | `.36` | `0x220400000` | `0x06150000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputCore.framework`** | `0x23c2e0000` | `.42` | `0x238400000` | `0x03ee0000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`KeyboardSettings.axbundle`** | `0x2467bb000` | `.44` | `0x240400000` | `0x063bb000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`IOHIDKeyboardFilter.plugin`** | `0x2529b8000` | `.48` | `0x250400000` | `0x025b8000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`KeyboardServices.framework`** | `0x28eee4000` | `.59` | `0x288400000` | `0x06ae4000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`KeyboardSettings.framework`** | `0x28ef1b000` | `.59` | `0x288400000` | `0x06b1b000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`KeyboardSettingsFeedback.framework`** | `0x28ef4e000` | `.59` | `0x288400000` | `0x06b4e000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`LinguisticData.framework`** | `0x28ff1e000` | `.59` | `0x288400000` | `0x07b1e000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputCJK.framework`** | `0x2b710b000` | `.69` | `0x2b0400000` | `0x06d0b000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`StickersSearchCore.framework`**| `0x2b7130000` | `.69` | `0x2b0400000` | `0x06d30000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputSwift.framework`** | `0x2b713e000` | `.69` | `0x2b0400000` | `0x06d3e000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **`TextInputTestingKit.framework`**| `0x2b7141000` | `.69` | `0x2b0400000` | `0x06d41000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |
| **34 `TextInput_*.bundle` Dylibs** | `0x2c5906000` – `0x2c596b000` | `.73` | `0x2c0400000` | `0x05506000` – `0x0556b000` | `__TEXT` (r-x), `__DATA_CONST` (r--) |

---

## 4. Tool Availability & Extraction Prerequisites

The reverse engineering environment on the Linux host has been thoroughly audited for binary inspection, decompilation, and archive handling capabilities.

### 4.1 Installed Host Tool Matrix

| Tool | Host Path | Version | Verification Command | Supported Capabilities & Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **`7z`** | `/usr/bin/7z` | `7-Zip 26.06 (x64)` | `7z --help` | Direct APFS DMG listing (`7z l`), recursive file extraction (`7z x`), and streaming stdout pipe extraction (`7z e -so`) for property lists and SQLite databases without mounting. |
| **`python3`** | `/usr/bin/python3` | `Python 3.14.9` | `python3 --version` | Standard library `plistlib` for binary/XML property lists, `struct` for binary Mach-O header parsing, `sqlite3` for schema validation, `subprocess` for pipeline orchestration. |
| **`llvm-objdump`** | `/usr/bin/llvm-objdump` | `LLVM 23.1.4` | `llvm-objdump --version` | Mach-O 64-bit arm64e disassembler (`--macho --disassemble`), segment/section load command inspection (`--all-headers`), and Objective-C metadata dumping. |
| **`strings`** | `/usr/bin/strings` | `GNU Binutils 2.47` | `strings --version` | Rapid ASCII and UTF-8 string scanning across raw Mach-O binaries, serialized CoreUI catalogs, and subcache slices. |
| **`nm` / `llvm-nm`** | `/usr/bin/nm`, `/usr/bin/llvm-nm` | `GNU Binutils 2.47` / `LLVM 23.1.4` | `llvm-nm --version` | Symbol table dumping for standalone executables (`kbd`, `FullKeyboardAccess`) and extraction of unstripped symbols from `.symbols` files. |
| **`ghidra`** | `/usr/bin/ghidra` | `Ghidra v11+` | `ghidra --version` | Full-stack interactive decompiler and headless disassembler for complex C++ control flow and Objective-C method dispatch reconstruction. |
| **`rea` MCP** | Agent Environment | REA Suite | `call_mcp_tool rea` | Native Apple Silicon binary inspection, Mach-O header analysis, Swift type metadata demangling, and Objective-C class hierarchy extraction. |

### 4.2 Missing macOS Tools & Standardized Mitigations

Because analysis is conducted on an enterprise Linux workstation, certain proprietary Darwin-exclusive utilities are absent. Robust, verified mitigations are established below:

| Missing macOS Tool | Technical Function | Linux-Native Clean-Room Mitigation | Verification & Implementation Command |
| :--- | :--- | :--- | :--- |
| **`dsc_extractor`** | Extracts individual dynamic libraries from monolithic shared cache | Streamed offset extraction via `7z e -so` combined with Python binary slice reading (`f.seek(file_offset)`) based on `shared_cache_overview.json` | `python3 tools/analyze_dyld_cache.py` maps all 4,770 image offsets directly. |
| **`jtool` / `jtool2`** | Detailed Mach-O and Objective-C metadata parser | `llvm-objdump --macho --all-headers` supplemented by Python `struct` scripts parsing `LC_SEGMENT_64`, `__objc_classlist`, and `__objc_methlist`. | `python3 -c "import struct; ..."` extracts section boundaries and load commands. |
| **`assetutil`** | Decodes Apple CoreUI `Assets.car` asset catalogs | Python BOMStore parser (`tools/analyze_asset_catalogs.py`) extracting `RATC` / `CARHEADER` records, rendition attributes, and embedded PNG/PDF bitmaps. | Inspects `Artwork.bundle/Assets.car` directly without Apple proprietary tools. |
| **`hdiutil`** | Mounts and attaches Apple DMG files | `7z` native APFS container navigation. `7z x` extracts any subfolder or file directly from APFS disk images without root loopback mounts. | `7z e -so artifacts/crypto/141-08876-216_rootfs.dmg <path>` |

---

## 5. Strict Read-Only Audit Procedures & Integrity Rules

To guarantee zero corruption of original reverse engineering artifacts, ensure forensic reproducibility, and adhere to strict clean-room engineering standards, the following operational procedures are enforced across all milestones:

1. **Absolute Immutability of Original Restore Images**:
   - The directory `iPhone18,3_27.2_24B119_Restore/` and all files therein must remain strictly read-only (`chmod -R 444`).
   - No command may invoke in-place modification (`sed -i`, `truncate`, `dd conv=notrunc`, or `write` syscalls) on any `.dmg`, `.aea`, `.im4p`, or `.plist` file within the restore package.
2. **Decrypted Artifact Isolation**:
   - The master decrypted images (`artifacts/crypto/141-08876-216_rootfs.dmg` and `artifacts/crypto/141-09724-226_cryptex_systemos.dmg`) serve as immutable reference goldens.
   - Any extraction of files must extract copies to target output directories (`ios27-keyboard-reverse-engineering/` or staging directories in `/tmp`).
3. **Streamed In-Memory Extraction Over Full Disk Unpacking**:
   - To conserve filesystem space and eliminate disk I/O bottlenecks, property lists, SQLite schemas, and localized string tables must be inspected via stdout streaming (`7z e -so <dmg> <path> | python3 -c ...`).
4. **Agent Workspace Sandboxing**:
   - Subagents must write solely within their assigned working directory (`.agents/teamwork/<agent_id>/`) or the project deliverables folder (`ios27-keyboard-reverse-engineering/`).
   - `.agents/teamwork/` must contain only operational metadata (plans, progress, handoffs, research notes). Source code, compiled tests, or binary dumps must never be stored in the root of `.agents/teamwork/`.
5. **Pre- and Post-Execution Cryptographic Integrity Verification**:
   - Any pipeline task touching crypto DMGs must verify the container SHA-256 digests against the master catalog before concluding.
