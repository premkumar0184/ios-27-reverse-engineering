# Change: Phase 6 - Apple iOS UI Layer, SpringBoard & System Applications

## Why
Reverse engineer the complete iOS visual interface, SpringBoard display controller, system asset catalogs, and core built-in application ecosystem from the decrypted RootFS (`artifacts/crypto/141-08876-216_rootfs.dmg`).

## What Changes
1. Extract and reverse engineer `SpringBoard.app` to produce `artifacts/ui/springboard_analysis.json`.
2. Extract and decode system Asset Catalogs (`Assets.car`, `Artwork.car`) into `artifacts/ui/asset_catalog_inventory.json`.
3. Dissect core system applications (`MobileSafari`, `Preferences`, `MobileSMS`, `Camera`, `Health`, `Wallet`) into `artifacts/ui/app_ecosystem_matrix.json`.
4. Author comprehensive findings document `findings/06_UI_AND_APPLICATIONS.md`.
5. Execute mechanical verification via `tools/verify_phase.py phase_06_ui_and_applications`.
