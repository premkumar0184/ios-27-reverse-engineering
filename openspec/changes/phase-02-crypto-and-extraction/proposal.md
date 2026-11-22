# Proposal: Phase 2 - Cryptographic Decryption & Full Filesystem Extraction

## Goal
Decrypt all symmetric Apple Encrypted Archive (AEA) images, extract compressed IM4P LZFSE kernelcache binaries, extract restore ramdisk APFS containers, and dissect nested ExclaveCore BUND multi-binary archives.

## Scope
- Decrypt `141-08876-216.dmg.aea` (RootFS 9.84 GB -> 10.56 GB APFS)
- Decrypt `141-09724-226.dmg.aea` (Cryptex1 SystemOS 5.89 GB -> 6.32 GB APFS)
- Decrypt `141-08904-238.dmg.aea` (ExclaveOS 590 MB -> 631 MB APFS)
- Extract `kernelcache.release.raw` and `kernelcache.research.raw` (78.98 MB arm64e `MH_FILESET` each)
- Extract `141-09491-242_restoreramdisk.apfs` (247 MB APFS)
- Unpack ExclaveCore BUND container into 4 microkernel Mach-O sub-binaries (Tightbeam, PMM, VASCore, JgSharedMemory)
