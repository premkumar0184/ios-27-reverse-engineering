# Agent Prompt: Phase 6 - Apple iOS UI Layer, SpringBoard & System Applications Specialist

## Mission
Execute **Phase 6: Apple iOS UI Layer, SpringBoard & System Applications**.
Reverse engineer the complete iOS visual interface and application ecosystem from the decrypted RootFS (`artifacts/crypto/141-08876-216_rootfs.dmg`). Dissect `SpringBoard.app`, extract Asset Catalogs (`Assets.car`, `Artwork.car`), catalog built-in system applications, and analyze SwiftUI/UIKit runtime dispatchers.

## Required Deliverables
1. `artifacts/ui/springboard_analysis.json`:
   - Architectural breakdown of `SpringBoard.app`:
     - Presentation controllers (`SBMainWorkspace`, `SBCoverSheetPresentationManager`, `SBControlCenterController`, `SBIconController`).
     - Mach services registered by SpringBoard.
     - Entrypoints, gesture recognizer dispatchers, and window management hooks.
2. `artifacts/ui/asset_catalog_inventory.json`:
   - Detailed inventory of decoded asset catalogs (`Assets.car`):
     - SF Symbols, vector icons, interface bitmaps, color schemes, and rendition metadata extracted via REA `inspect_asset_catalog`.
3. `artifacts/ui/app_ecosystem_matrix.json`:
   - Comprehensive matrix of core system applications (`MobileSafari`, `Preferences`/Settings, `MobileSMS`, `Camera`, `Health`, `Wallet`):
     - Bundle identifiers, exported URL schemes, `Info.plist` properties, and main binary entrypoints.
4. `findings/06_UI_AND_APPLICATIONS.md`:
   - Exhaustive technical treatise detailing the iOS 27 user experience architecture:
     - SpringBoard window server and gesture pipeline.
     - UI asset catalog compositions and vector structures.
     - Application sandbox profiles and private UI framework dependencies (`FrontBoard`, `BackBoardServices`, `UIKitCore`, `SwiftUI`).

## Available Tools & Procedures
1. Extract SpringBoard bundle:
   ```bash
   python3 tools/extract_dmg.py extract artifacts/crypto/141-08876-216_rootfs.dmg System/Library/CoreServices/SpringBoard.app/* artifacts/ui/SpringBoard/
   ```
2. Extract system applications:
   ```bash
   python3 tools/extract_dmg.py extract artifacts/crypto/141-08876-216_rootfs.dmg Applications/* artifacts/ui/Applications/
   ```
3. Use REA tools:
   - `rea inspect_asset_catalog` on extracted `Assets.car` files.
   - `rea open_binary` on `artifacts/ui/SpringBoard/SpringBoard` to inspect Mach-O classes and Objective-C/Swift metadata.
   - `rea demangle_swift` on mangled UI symbols.
4. Use Ghidra for decompiling critical UI presentation methods.
5. Verify results with `python3 tools/verify_phase.py phase_06_ui_and_applications`.
