# Agent Prompt: Phase 7 - Platform Security, TrustCache & Full Entitlement Matrix Auditor

## Mission
Execute **Phase 7: Platform Security, TrustCache & Full Entitlement Matrix**.
Parse all Apple TrustCache binaries, cross-reference CDHashes against decrypted system binaries and root hashes, reconstruct the full-stack entitlement matrix across all system binaries, and dissect sandbox enforcement and AMFI hooks.

## Required Deliverables
1. `artifacts/security/trustcache_catalog.json`:
   - Full catalog of all TrustCache files with version, UUID, entry counts, and container types.
2. `artifacts/security/cdhash_database.json`:
   - Extracted table of CDHashes, hash types, execution flags, and constraint categories cross-referenced with decrypted rootfs binaries.
3. `artifacts/security/entitlements_analysis.json`:
   - Full-stack entitlement matrix cataloging root privileges, private entitlements (`com.apple.private.*`), and sandbox profiles across all daemons and applications.
4. `findings/07_SECURITY_TRUST_ARCHITECTURE.md`:
   - Deep analysis of Apple's modern trust architecture: TrustCache verification paths, AMFI enforcement hooks, and sandbox policy containers.

## Available Tools & Procedures
1. Run `python3 tools/parse_trustcache.py iPhone18,3_27.2_24B119_Restore/Firmware/ artifacts/security/`.
2. Cross-reference CDHashes against decrypted system binaries in `artifacts/crypto/141-08876-216_rootfs.dmg` and `artifacts/rootfs/`.
3. Use REA (`rea analyze_function`, `rea inspect_macho`) to trace AMFI verification logic.
4. Verify results with `python3 tools/verify_phase.py phase_07_security_trust_architecture`.
