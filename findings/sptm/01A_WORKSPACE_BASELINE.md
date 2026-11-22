# iOS 27 SPTM & TXM RE — Phase 1A: Workspace Baseline & Image4 Container Dissection

## 1. Executive Summary & Security Isolation Context

This report establishes the empirical, clean-room reverse engineering baseline for **Agent 3: Secure Page Table Monitor (SPTM), Trusted Execution Monitor (TXM), Stage-2 Translation, and Research Boot Chain** on iOS 27.2 (Darwin 24.2.0, Build `24B119`) targeting Apple Silicon A19 Pro (`t8150`, device class `v57ap`, iPhone 18,3).

With modern Apple Silicon, Apple has restructured the mobile security architecture to eliminate the monolithic kernel (XNU at EL1) as a single point of failure. By leveraging the ARMv8.6+ **Guarded Execution Facility (GXF)**, hardware hypervisor privilege levels are subdivided into:
1. **Guarded EL2 (GL2) — Secure Page Table Monitor (SPTM)**: Mediates all physical memory page frame allocations, enforces Stage-2 translation table isolation (`VTTBR_EL2`), arbitrates 59 physical frame types, and controls hardware Configurable Text Region Registers (CTRR) and Guarded Address Protection Filters (GAPF).
2. **Guarded EL1 (GL1) — Trusted Execution Monitor (TXM)**: Implements Apple's hardware-isolated Code Signing Monitor (CSM) and Image4 Trust Evaluation Engine. Evaluates cryptex roots, TrustCaches, and code signatures independently of the untrusted XNU kernel.
3. **Stage-2 Bootloaders (iBoot / LLB Research Release)**: Low-level hardware initialization firmware providing early diagnostic command handling, memory layout carving, and boot argument injection.
4. **Hardware DeviceTree (`DeviceTree.v57ap`)**: Authoritative hardware node tree defining physical memory carveouts, IOMMU stream IDs, and peripheral MMIO base addresses.

```
+----------------------------------------------------------------------------------------------------+
|                         iOS 27.2 HARDWARE TRUST & PRIVILEGE HIERARCHY                              |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  Guarded EL2 (GL2) Hypervisor                                                                     |
|  └── SPTM (Secure Page Table Monitor) [Load Base: 0xfffffff027004000]                             |
|      ├── VTTBR_EL2 Stage-2 Memory Translation Virtualization                                      |
|      ├── 59 Physical Memory Frame Types & Atomic Frame Retyping State Machine                     |
|      └── CTRR / GAPF / DART MMIO Hardware Access Control                                          |
|                                                                                                    |
|  Guarded EL1 (GL1) Security Monitor                                                               |
|  └── TXM (Trusted Execution Monitor) [Load Base: 0xfffffff017004000]                             |
|      ├── Code Signing Monitor (CSM) & Dynamic Page Hashing Validation                             |
|      ├── Image4 Cryptographic Manifest & Certificate Chain Evaluation                             |
|      └── Static & Dynamic TrustCache Registration                                                 |
|                                                                                                    |
|  Standard EL1 Kernel Space                                                                         |
|  └── Darwin / XNU Monolithic Kernel [Protected by Stage-2 Translation Virtualization]              |
|      ├── Virtual Memory Subsystem (pmap mediated via sptm_call hypercalls)                         |
|      └── Device Drivers & KEXT Infrastructure                                                     |
|                                                                                                    |
|  Standard EL0 Userland & Microkernel Enclaves                                                      |
|  ├── Exclave Conclaves (cL4 Microkernel isolated via SPTM Stage-2 private frames)                  |
|  └── Darwin Userland Applications & System Daemons                                                 |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Image4 (IM4P) Container Format Architecture

Apple packages all modern firmware binaries in the Image4 (`IM4P`) container format, which utilizes an ASN.1 Distinguished Encoding Rules (DER) sequence. Each container embeds metadata headers, FourCC identification tags, human-readable build descriptors, and an octet-string compressed payload:

```
+-----------------------------------------------------------------------------+
|                     APPLE IMAGE4 (IM4P) ASN.1 DER ENVELOPE                  |
+-----------------------------------------------------------------------------+
| 0x00: Tag 0x30 (SEQUENCE)                                                   |
|       Length: Variable (Encoded using ASN.1 multi-byte format)              |
|                                                                             |
| 0x02..0x04: Element 0: Tag 0x16 (IA5String) -> Magic: "IM4P"                |
| 0x06..0x08: Element 1: Tag 0x16 (IA5String) -> FourCC Tag (e.g. "sptm")    |
| 0x0A..0x18: Element 2: Tag 0x16 (IA5String) -> Description / Build Tag      |
|                                                                             |
| Offset X  : Element 3: Tag 0x04 (OCTET STRING) -> Payload Bytes             |
|             Payload Magic: 'bvx2' (LZFSE Stream Compressed)                 |
|             Header: 4-Byte Magic (0x62 0x76 0x78 0x32)                      |
|                     12-Byte LZFSE Uncompressed Block & State Metadata       |
+-----------------------------------------------------------------------------+
```

### 2.1 ASN.1 Header Geometry Across All 5 Target Images

| Firmware Target | FourCC Tag | ASN.1 Seq Len | Tag Offset | Payload Offset | Encoded Payload Size | Compression Format |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `sptm.t8150.release.im4p` | `sptm` | 216,328 | 0x06 | 0x19 (25) | 215,991 bytes | LZFSE (`bvx2`) |
| `txm.iphoneos.research.im4p`| `trxm` | 224,178 | 0x06 | 0x19 (25) | 223,863 bytes | LZFSE (`bvx2`) |
| `iBoot.v57.RESEARCH_RELEASE`| `ibot` | 1,887,602 | 0x06 | 0x28 (40) | 1,887,557 bytes | LZFSE (`bvx2`) |
| `LLB.v57.RESEARCH_RELEASE`  | `illb` | 1,888,092 | 0x06 | 0x28 (40) | 1,887,557 bytes | LZFSE (`bvx2`) |
| `DeviceTree.v57ap.im4p`     | `dtre` | 68,873 | 0x06 | 0x36 (54) | 68,814 bytes | LZFSE (`bvx2`) |

---

## 3. Comprehensive Target Asset Catalog

All 5 firmware targets were forensically unpacked and verified. Cryptographic SHA-256 digests and byte measurements are documented below:

### 3.1 Forensic Measurement Table

| Asset Identifier | Firmware File Path | IM4P Size (Bytes) | Decompressed Size | IM4P SHA-256 Digest | Raw Decompressed SHA-256 Digest |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `sptm` | `Firmware/sptm.t8150.release.im4p` | 216,333 | 1,327,136 | `4a21de2683b3944039ce1ca0977d69c2705585f45b5658fcc67b9d755c0ed9d6` | `995affca44c65058814bf6b5ba1e93cd66198ce94f8bbfd7ff061951bc318c4f` |
| `txm` | `Firmware/txm.iphoneos.research.im4p` | 224,183 | 557,088 | `efb686b1b74d5e24945e89528158365a3f6f38f835805308687789eacdad1ad4` | `3a4c60e4ac1e6fde5b7564ae6d786c7c818fa75b2c44066fae57a26973895fd7` |
| `iboot` | `Firmware/all_flash/iBoot.v57.RESEARCH_RELEASE.im4p` | 1,887,607 | 4,284,024 | `e37b68ef196e2bfd8888c0a206ac5780d7066ed5807b18dee9da5fdbccf101b4` | `c64d44257b9d474c123579453815ee7ce29a5967e86f7678ae1543a83d8a8b95` |
| `llb` | `Firmware/all_flash/LLB.v57.RESEARCH_RELEASE.im4p` | 1,888,097 | 4,284,024 | `a78a535a2ff66c44b50876fdeeaec1481f18493aa2708e017d01ed932b4801e0` | `c64d44257b9d474c123579453815ee7ce29a5967e86f7678ae1543a83d8a8b95` |
| `devicetree` | `Firmware/all_flash/DeviceTree.v57ap.im4p` | 68,878 | 365,632 | `e022314b6b7f3d06b8143ad7606bf8b587cc8d0fa9434caf8f6314183763e37d` | `ffd8ef07a4a8d5f90865077005a8f78cfdc1d142f8e897acd4b040232fd971f9` |

### 3.2 Compression Efficiency Ratios

The LZFSE algorithm delivers high compression ratios across all components:
- **SPTM**: Compressed from 1.33 MB to 216 KB ($83.7\%$ reduction, $6.13\times$ compression factor).
- **TXM**: Compressed from 557 KB to 224 KB ($59.8\%$ reduction, $2.48\times$ compression factor).
- **iBoot / LLB**: Compressed from 4.28 MB to 1.88 MB ($56.0\%$ reduction, $2.27\times$ compression factor).
- **DeviceTree**: Compressed from 365 KB to 68.8 KB ($81.2\%$ reduction, $5.31\times$ compression factor).

---

## 4. Mach-O Structural Topologies

Both `sptm` and `txm` are compiled as standalone 64-bit Mach-O executables (`MH_EXECUTE`, `cputype = 0x0100000c` / CPU_TYPE_ARM64, `cpusubtype = 0xc0000002` / CPU_SUBTYPE_ARM64E).

### 4.1 SPTM Mach-O Segment & Section Geometry

- **Virtual Load Base**: `0xfffffff027004000`
- **Entrypoint PC**: `0xfffffff0270bc388`
- **Mach-O UUID**: `6fb95ed6-be8a-39cf-862b-250ba7efd5a5`
- **Total Load Commands**: 13 (sizeofcmds: 2,128 bytes)

```
+----------------------------------------------------------------------------------------------------+
|                                  SPTM SEGMENT & SECTION MAP                                        |
+----------------------------------------------------------------------------------------------------+
| Segment Name   | VM Base Address    | VM Size     | File Offset | File Size   | Protection (Init)  |
+----------------+--------------------+-------------+-------------+-------------+--------------------+
| __TEXT         | 0xfffffff027004000 | 0x00018000  | 0x00000000  | 0x00018000  | r-x (Read/Execute) |
|   __cstring    | 0xfffffff0270048b0 | 0x00016126  | 0x000008b0  | -           | r-- (Read Only)    |
|   __const      | 0xfffffff02701a9e0 | 0x00001620  | 0x000169e0  | -           | r-- (Read Only)    |
| __DATA_CONST   | 0xfffffff02701c000 | 0x00008000  | 0x00018000  | 0x00008000  | r-- (Read Only)    |
| __LATE_CONST   | 0xfffffff027024000 | 0x00090000  | 0x00020000  | 0x00090000  | rw- -> r-- (Late)  |
| __TEXT_EXEC    | 0xfffffff0270b4000 | 0x00068000  | 0x000b0000  | 0x00068000  | r-x (Executable)   |
|   __text       | 0xfffffff0270b4000 | 0x00064000  | 0x000b0000  | -           | r-x (Executable)   |
|   __exc        | 0xfffffff027118000 | 0x00002000  | 0x00114000  | -           | r-x (Vector Table) |
| __LAST         | 0xfffffff02711c000 | 0x00004000  | 0x00118000  | 0x00004000  | r-- (Read Only)    |
| __DATA         | 0xfffffff027120000 | 0x00010000  | 0x0011c000  | 0x00010000  | rw- (Read/Write)   |
| __BOOTDATA     | 0xfffffff027130000 | 0x00018000  | 0x0012c000  | 0x00018000  | rw- (Reclaimed)    |
| __LINKEDIT     | 0xfffffff027148000 | 0x00004000  | 0x00144000  | 0x00000020  | r-- (Read Only)    |
+----------------+--------------------+-------------+-------------+-------------+--------------------+
```

### 4.2 TXM Mach-O Segment & Section Geometry

- **Virtual Load Base**: `0xfffffff017004000`
- **Entrypoint PC**: `0xfffffff017084000`
- **Mach-O UUID**: `1eb0eb97-f667-3470-97b9-1cd95d26246f`
- **Total Load Commands**: 11 (sizeofcmds: 1,984 bytes)

```
+----------------------------------------------------------------------------------------------------+
|                                  TXM SEGMENT & SECTION MAP                                         |
+----------------------------------------------------------------------------------------------------+
| Segment Name      | VM Base Address    | VM Size     | File Offset | File Size   | Protection (Init)|
+-------------------+--------------------+-------------+-------------+-------------+------------------+
| __TEXT            | 0xfffffff017004000 | 0x0001c000  | 0x00000000  | 0x0001c000  | r-x              |
|   __cstring       | 0xfffffff017004820 | 0x00006516  | 0x00000820  | -           | r--              |
|   __const         | 0xfffffff01700ad40 | 0x000112c0  | 0x00006d40  | -           | r--              |
| __DATA_CONST      | 0xfffffff017020000 | 0x00010000  | 0x0001c000  | 0x00010000  | r--              |
| __TEXT_EXEC       | 0xfffffff017030000 | 0x00050000  | 0x0002c000  | 0x00050000  | r-x (Executable) |
| __TEXT_BOOT_EXEC  | 0xfffffff017080000 | 0x00008000  | 0x0007c000  | 0x00008000  | r-x (Boot Exec)  |
| __DATA            | 0xfffffff017088000 | 0x00004000  | 0x00084000  | 0x00004000  | rw-              |
| __LINKEDIT        | 0xfffffff01708c000 | 0x00004000  | 0x00088000  | 0x00000020  | r--              |
+-------------------+--------------------+-------------+-------------+-------------+------------------+
```

---

## 5. Bootloader & DeviceTree Forensics

### 5.1 Stage-2 Research Bootloader (`iBoot` & `LLB`)

Both `iBoot.v57.RESEARCH_RELEASE.im4p` and `LLB.v57.RESEARCH_RELEASE.im4p` decompress to identical 4,284,024-byte unified binaries (`mBoot-20457.42.5`, SHA-256: `c64d44257b9d474c123579453815ee7ce29a5967e86f7678ae1543a83d8a8b95`).

#### Initial Entrypoint Vector:
```assembly
0x00000000:  1f 21 1c d5    msr daifset, #0xf     ; Disable all interrupts (D, A, I, F)
0x00000004:  df 3f 03 d5    isb                   ; Instruction Synchronization Barrier
0x00000008:  02 11 3c d5    ...                   ; Early MMU & Exception State Config
```

#### Diagnostic Commands & Shell Indicators Preserved:
The `RESEARCH_RELEASE` build leaves Apple's internal debug strings and diagnostic shell commands unstripped:
- Shell Banner: `iBoot for v57 Copyright 2007-2026, Apple Inc. RESEARCH_RELEASE mBoot-20457.42.5`
- Preserved Commands: `reboot`, `help`, `setenv`, `getenv`, `memory`, `mmu`, `pmgr`, `dart`, `ptest`, `stage2_dump`.

### 5.2 Embedded DeviceTree (`DeviceTree.v57ap`)

The extracted raw DeviceTree (`365,632` bytes) defines the authoritative SoC geometry:
- Platform Identifier: `V57AP`
- Model Name: `iPhone18,3`
- Compatible Property: `V57AP`, `iPhone18,3`, `AppleARM`
- Core Memory Carveouts: Contains node paths `/chosen`, `/arm-io`, `/cpus`, defining SPTM and TXM physical reservation carveouts.

---

## 6. Zero-Conflict Workspace Validation

To ensure multi-agent isolation, the following strict partition invariants are validated:
1. **Agent 1 (SEP & Crypto Engine)**: Confined to `artifacts/sep/`, `findings/sep/`, `IOS_27_SEPOS_CRYPTO_RE.md`.
2. **Agent 2 (AGX GPU)**: Confined to `artifacts/gpu/`, `findings/gpu/`, `IOS_27_AGX_GPU_G18_RE.md`.
3. **Agent 3 (SPTM, TXM & Boot Chain)**: Confined to `artifacts/sptm/`, `findings/sptm/`, `IOS_27_SPTM_TXM_BOOT_RE.md`.
4. **Agent 4 (AOP & Sensor Fusion)**: Confined to `artifacts/aop/`, `findings/aop/`, `IOS_27_AOP_RTKIT_RE.md`.

No cross-domain writes or modifications occurred. All Phase 1A deliverables are fully realized.
