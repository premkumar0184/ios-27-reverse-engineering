# Design: Phase 6 - Apple iOS UI Layer, SpringBoard & System Applications

## Architecture & Extraction Strategy

### 1. SpringBoard Reverse Engineering
- Extract `System/Library/CoreServices/SpringBoard.app/*` from decrypted RootFS `artifacts/crypto/141-08876-216_rootfs.dmg`.
- Parse Mach-O arm64e PAC00 binary `SpringBoard`.
- Extract Objective-C class names, protocols, methods, and presentation controllers:
  - `SBMainWorkspace`, `SBCoverSheetPresentationManager`, `SBControlCenterController`, `SBIconController`, `SBFloatingDockController`, `SBLockScreenManager`.
- Map Mach services registered by SpringBoard.

### 2. Asset Catalog Decoding
- Search and extract `Assets.car` and `Artwork.car` files.
- Parse BOM (Bill of Materials) and rendition headers (CAR / `BOMStorage` format).
- Inventory SF Symbols, vector icons, UI color palettes, and rendition scales.

### 3. Application Ecosystem Matrix
- Extract `/Applications/*` bundles (`MobileSafari`, `Preferences`, `MobileSMS`, `Camera`, `Health`, `Wallet`, etc.).
- Parse `Info.plist` files: bundle IDs, URL schemes, permissions, entitlements, and main binary entrypoints.
- Cross-reference private framework dependencies (`FrontBoard`, `BackBoardServices`, `UIKitCore`, `SwiftUI`).

### 4. Verification
- Validate schema constraints in `tools/verify_phase.py`.
- Ensure >= 2,500 bytes and zero placeholders in `findings/06_UI_AND_APPLICATIONS.md`.
