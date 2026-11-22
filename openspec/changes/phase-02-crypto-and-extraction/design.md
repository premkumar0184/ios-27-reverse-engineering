# Design: Phase 2 - Cryptographic Decryption & Full Filesystem Extraction

## Architecture
1. **AEA Decryption**: Use streaming AES-256-GCM HKDF-SHA256 Profile 1 decryptor (`tools/decrypt_aea.py`) with verified symmetric keys. Validate APFS container superblock (`NXSB`) at offset 0x20.
2. **IM4P Payload Extraction**: Parse ASN.1 DER Image4 envelopes (`tools/parse_im4p.py`), decompress `bvx2` LZFSE streams, and unpack BUND (`DNUB`) containers into constituent 64-bit arm64e Mach-O binaries.
3. **Verification**: Execute `tools/verify_phase.py phase_02_crypto_and_extraction` to mechanically assert artifact existence, file size consistency, and authentic findings documentation.
