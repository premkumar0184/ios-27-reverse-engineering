# iOS 27.2 Full-Stack Reverse Engineering Base

An evidence-driven, multi-agent reverse engineering framework built to methodically dissect and analyze the entire **iOS 27.2 (Build 24B119 - iPhone18,3 - SoC T8150)** operating system across all layers—from low-level bootchain and coprocessors up to the userland SpringBoard UI, asset catalogs, and system applications.

---

## 1. Core Architecture & Directory Layout

```
.
├── iPhone18,3_27.2_24B119_Restore/ # Raw unpacked IPSW restore bundle (12+ GB)
│   ├── 141-*.dmg / *.dmg.aea       # Filesystem images (APFS, AEA encrypted)
│   ├── BuildManifest.plist         # Restore identities, Cryptex, ExclaveOS definitions
│   ├── Firmware/                   # Coprocessor firmware, boot chain, baseband, TrustCaches
│   ├── kernelcache.release.v57     # Production kernelcache (IM4P container)
│   └── kernelcache.research.v57    # Research kernelcache (IM4P container)
├── progress.json                   # Authoritative execution tracker and phase state machine
├── .agent_rules/
│   ├── CORE_RULES.md               # Strict execution, anti-hallucination, and anti-cheating directives
│   ├── TOOLING_GUIDE.md            # REA, Ghidra, Graphify, and Python tooling reference
│   └── PHASE_WORKFLOW.md           # Phase transition state machine and verification protocol
├── agent_prompts/                  # Step-by-step role prompts for AI agents
│   ├── 00_orchestrator_controller.md
│   ├── 01_manifest_recon_agent.md
│   ├── 02_decryption_extraction_agent.md
│   ├── 03_kernel_sptm_txm_agent.md
│   ├── 04_firmware_coprocessor_agent.md
│   ├── 05_rootfs_dyld_subsystem_agent.md
│   ├── 06_ui_and_applications_agent.md
│   ├── 07_security_trust_agent.md
│   └── 08_graphify_synthesis_agent.md
├── artifacts/                      # Verified extracted data, JSON matrices, and raw binaries
│   ├── manifests/
│   ├── crypto/
│   ├── kernel/
│   ├── firmware/
│   ├── coprocessors/
│   ├── rootfs/
│   ├── ui/
│   └── security/
├── findings/                       # Comprehensive, verifiable technical analysis reports
│   └── 00_PROJECT_OVERVIEW.md      # Target identification and system overview
├── tools/                          # Deterministic local parsers & mechanical validators
│   ├── parse_manifests.py          # Deterministic plist & restore bundle inventory parser
│   ├── parse_im4p.py               # Apple Image4 payload (IM4P) unpacker & LZFSE decompressor
│   ├── parse_trustcache.py         # Apple TrustCache v1/v2 parser & CDHash extractor
│   ├── decrypt_aea.py              # Apple Encrypted Archive (AEA) profile 1 streaming decryptor
│   ├── extract_dmg.py              # APFS DMG subtree extractor using 7z
│   └── verify_phase.py             # Mechanical phase verification engine
└── logs/                           # Agent execution traces
```

---

## 2. Mandatory Execution Rules

All agents and subagents operating in this workspace must adhere to the rules defined in `.agent_rules/CORE_RULES.md`:

1. **Sequential Execution**: Execute exactly **one major phase at a time**.
2. **Authoritative Tracker**: `progress.json` is the single source of truth for phase state.
3. **Zero-Tolerance for Placeholders**: No placeholder documentation ("TODO", "TBD", "placeholder", "omitted for brevity") may ever be committed.
4. **Empirical Evidence Required**: Every claim must cite raw binary data, hex offsets, tool outputs, or plist keys.
5. **Mechanical Verification**: A phase cannot be marked complete without passing `python3 tools/verify_phase.py <phase_id>`.
6. **Graphify Navigation**: Agents must query the knowledge graph (`graphify-out/graph.json` via `graphify query`) instead of blindly wandering or running recursive greps across raw 12+ GB directories.

---

## 3. The 8 Investigation Phases

| Phase | Identifier | Focus | Key Tools |
| :---: | :--- | :--- | :--- |
| **1** | `phase_01_recon_and_inventory` | Plists, hardware models (`v57ap`/`iPhone18,3`), image catalog | `tools/parse_manifests.py` |
| **2** | `phase_02_crypto_and_extraction` | AEA decryption (RootFS, Cryptex, Exclaves), kernel Mach-O extraction | `tools/decrypt_aea.py`, `tools/parse_im4p.py` |
| **3** | `phase_03_kernel_sptm_txm` | Release vs Research kernel, KEXT diff, SPTM, TXM, Exclaves | REA, Ghidra |
| **4** | `phase_04_firmware_coprocessors` | AOP/AOP2, ANE, AGX, Rose, SEP, Baseband modem package | REA, Ghidra, `7z` |
| **5** | `phase_05_rootfs_dyld_frameworks` | dyld_shared_cache_arm64e, system daemons (launchd, commcenter, amfid) | `tools/extract_dmg.py`, REA, Ghidra |
| **6** | `phase_06_ui_and_applications` | SpringBoard, Asset Catalogs (`Assets.car`), built-in apps, SwiftUI/UIKit | `tools/extract_dmg.py`, REA, Ghidra |
| **7** | `phase_07_security_trust_architecture` | TrustCache CDHashes, root hashes, AMFI, full-stack entitlement matrix | `tools/parse_trustcache.py`, REA |
| **8** | `phase_08_graphify_synthesis` | Cross-component knowledge graph, IPC maps, master dossier | `graphify` |

---

## 4. Verification & Transition Protocol

To verify the deliverables of any phase:
```bash
python3 tools/verify_phase.py <phase_id>
```
*Example:*
```bash
python3 tools/verify_phase.py phase_01_recon_and_inventory
```
If the script passes (exit code 0), `progress.json` may be updated to mark the phase `completed`.
