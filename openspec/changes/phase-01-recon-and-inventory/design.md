# Design: Phase 1 - IPSW Reconnaissance & Manifest Parsing

## Architectural Approach
1. **Deterministic Plist Loading**:
   Use `tools/parse_manifests.py` to parse XML plists into structured Python objects using `plistlib`, preventing regex-based extraction errors.
2. **Bidirectional Component Mapping**:
   Iterate over all five `BuildIdentities` in `BuildManifest.plist`. Map every component name to its image path and vice versa, accounting for AEA encryption flags and hash methods (`sha2-384`).
3. **Firmware Survey**:
   Recursively traverse `Firmware/` to catalog all 126 components across 25 hardware coprocessor domains.
4. **Mechanical Quality Gate**:
   Execute `tools/verify_phase.py` to mechanically test all generated JSON files and ensure the findings document exceeds 2,500 bytes with zero placeholder phrases.
