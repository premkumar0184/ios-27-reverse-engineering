# Agent Prompt: Phase 2 - Cryptographic Decryption & Full Filesystem Extraction Specialist

## Mission
Execute **Phase 2: Cryptographic Decryption & Full Filesystem Extraction**.
Using the verified 256-bit symmetric keys, decrypt the primary AEA archives (Full RootFS, Cryptex1 SystemOS, ExclaveOS, RecoveryOS), extract raw APFS ramdisk images from Image4 containers, decompress 64-bit Mach-O kernelcaches via LZFSE, and unpack ExclaveCore microkernel sub-binaries.

## Required Deliverables
1. `artifacts/crypto/141-08876-216_rootfs.dmg`:
   - Decrypted 9.84 GB APFS root filesystem containing SpringBoard, system apps, and private frameworks.
2. `artifacts/crypto/141-09724-226_cryptex_systemos.dmg`:
   - Decrypted 5.89 GB APFS filesystem containing `dyld_shared_cache_arm64e`.
3. `artifacts/crypto/141-08904-238_exclaveos.dmg`:
   - Decrypted 590 MB APFS filesystem containing ExclaveOS microkernel root.
4. `artifacts/kernel/kernelcache.release.raw` & `artifacts/kernel/kernelcache.research.raw`:
   - Raw decompressed 75.33 MB Mach-O payloads extracted from the IM4P containers.
5. `findings/02_CRYPTO_AND_EXTRACTION.md`:
   - Comprehensive technical analysis of Apple's modern encryption scheme, AEA profile 1 format, key derivation, and extraction outcomes.
   - **Zero-Placeholder Invariant**: Real byte offsets, format signatures, and concrete data.

## Available Tools & Procedures
1. Run `python3 tools/decrypt_aea.py --verify-only` to confirm key authentication.
2. Run `python3 tools/decrypt_aea.py iPhone18,3_27.2_24B119_Restore/141-08876-216.dmg.aea artifacts/crypto/141-08876-216_rootfs.dmg` to decrypt RootFS.
3. Run `python3 tools/decrypt_aea.py iPhone18,3_27.2_24B119_Restore/141-09724-226.dmg.aea artifacts/crypto/141-09724-226_cryptex_systemos.dmg` to decrypt Cryptex SystemOS.
4. Run `python3 tools/decrypt_aea.py iPhone18,3_27.2_24B119_Restore/141-08904-238.dmg.aea artifacts/crypto/141-08904-238_exclaveos.dmg` to decrypt ExclaveOS.
5. Run `python3 tools/parse_im4p.py iPhone18,3_27.2_24B119_Restore/kernelcache.release.v57 artifacts/kernel/kernelcache.release.raw`.
6. Run `python3 tools/parse_im4p.py iPhone18,3_27.2_24B119_Restore/kernelcache.research.v57 artifacts/kernel/kernelcache.research.raw`.
7. Verify results with `python3 tools/verify_phase.py phase_02_crypto_and_extraction`.
