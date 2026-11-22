# Architectural Treatise: iOS 27.2 Platform Security, TrustCache & Full-Stack Entitlement Matrix

**Target System**: iOS 27.2 (`24B119`)  
**Hardware Platform**: iPhone 16 Pro / iPhone18,3 (SoC `t8150`, Apple A18 Pro)  
**Security Architecture**: Secure Page Table Monitor (SPTM), Trusted Execution Monitor (TXM), AppleMobileFileIntegrity (AMFI), Seatbelt Sandbox, Dual ARM64E PAC00 MH_FILESET Kernelcaches  
**Date**: November 2026  
**Status**: Authoritative Reverse Engineering Specification

---

## 1. Executive Summary & Architectural Overview

The platform security model of iOS 27.2 represents the culmination of hardware-enforced immutability, hierarchical trust anchors, and hypervisor-level monitor controls. Unlike traditional Unix security architectures where the operating system kernel is the ultimate security arbiter, iOS 27.2 strips the XNU kernel of autonomous code execution authority. The kernel cannot unilaterally designate memory pages as executable, nor can it bypass binary code signature verification without triggering hardware-enforced exception traps within the Secure Page Table Monitor (SPTM) at Exception Level 2 (EL2).

Platform security on the `t8150` architecture rests upon five mutually reinforcing pillars:
1. **Apple TrustCache Subsystem**: Pre-compiled, cryptographic tables containing SHA-256 Code Directory digests (CDHashes) for all operating system binaries, system daemons, extensions, and staged applications across root, recovery, RamDisk, Cryptex, and Exclave partitions.
2. **Execution Constraint Categorization**: In TrustCache v2, every binary is tagged with an execution constraint category ($0..18$), binding executables to launch constraints that restrict parent processes, launch entitlements, and process identity.
3. **AMFID Bootstrap Gate**: Self-referential trust establishment for `/usr/libexec/amfid` via `flags == 1`, permitting the userland integrity daemon to be validated directly by the kernel without chicken-and-egg dependency loops.
4. **Full-Stack Entitlement Matrix**: A 4-tier capability hierarchy spanning 680 system executables and 4,463 unique entitlement keys, strictly delineating root hardware access, private Apple SPIs, Transparency, Consent, and Control (TCC) overrides, and Mach service lookup assertions.
5. **SPTM Stage-2 Translation & Kernel AMFI Hooks**: Kernel Mandatory Access Control (MAC) hooks (`mac_vnode_check_signature`, `_check_cdhash_in_trustcache`, `mac_cred_label_update_execve`) operating in conjunction with SPTM `VTTBR_EL2` Stage-2 memory protection, rendering code pages immutable in physical DRAM.

---

## 2. Apple TrustCache Binary Dissection

### 2.1 Complete Inventory of the 7 Apple TrustCache Containers

The iOS 27.2 restore package (`iPhone18,3_27.2_24B119_Restore/Firmware/`) distributes 7 distinct Apple TrustCache binaries. Every TrustCache file is either encapsulated within an Apple Image4 Payload (`IM4P`) ASN.1 DER container or provided as a raw binary image. Across all 7 containers, exactly **5,204 CDHash entries** are declared, representing **4,527 unique CDHashes**.

| Binary Filename | Container Format | IM4P 4CC Tag | TrustCache Version | Entry Count | UUID (RFC 4122) | Backing Filesystem Image / System Role |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| `141-08876-216.dmg.aea.trustcache` | IM4P DER Sequence | `trst` | **v2** (24B) | **3,883** | `f6833d3e-79e1-41b0-9330-36528a635147` | Full RootFS System Image (`141-08876-216_rootfs.dmg`, 9.9 GB) |
| `141-09491-242.dmg.trustcache` | IM4P DER Sequence | `rtsc` | **v1** (22B) | **378** | `d1f46b33-ea2a-430b-baa3-060b2ca06537` | Factory Restore RamDisk Image (`141-09491-242.dmg`, 236 MB) |
| `141-10399-240.dmg.trustcache` | IM4P DER Sequence | `rtsc` | **v1** (22B) | **371** | `3f3ee769-60ec-4618-adc0-de62d30e0d13` | System Update RamDisk Image (`141-10399-240.dmg`, 234 MB) |
| `141-09644-240.dmg.aea.trustcache` | IM4P DER Sequence | `trst` | **v2** (24B) | **334** | `29f39160-7792-4997-b244-5b78873111b3` | Cryptex1 Base App OS Image (`141-09644-240.dmg.aea`, 248 MB) |
| `141-09724-226.dmg.aea.trustcache` | IM4P DER Sequence | `trcs` | **v2** (24B) | **132** | `67cec60f-f05f-4a22-b92c-6fb4ece48049` | Cryptex1 SystemOS Image (`141-09724-226_cryptex_systemos.dmg`, 2.3 GB) |
| `141-08904-238.dmg.aea.trustcache` | IM4P DER Sequence | `extc` | **v1** (22B) | **72** | `74f103f4-2c18-4fda-bbd2-8107884214f2` | ExclaveOS Microkernel Domain (`141-08904-238_exclaveos.dmg`, 512 MB) |
| `141-08824-244.dmg.trustcache` | IM4P DER Sequence | `trca` | **v2** (24B) | **34** | `622e2402-da38-48d0-9883-d5bf33b1d92e` | Cryptex1 AppOS Staged Extensions (`141-08824-244.dmg`, 16 MB) |
| **Consolidated Total** | — | — | **3 v1 / 4 v2** | **5,204** | — | **Complete Platform Trust Anchor Coverage** |

### 2.2 IM4P ASN.1 DER Envelope Encoding

All 7 TrustCache containers adhere to the standard Apple Image4 Payload (`IM4P`) DER specification. The outer envelope is an ASN.1 `SEQUENCE` (`0x30`), followed by four typed elements:

```asn1
Image4Payload ::= SEQUENCE {
    magic           IA5String,              -- ASCII "IM4P" (0x16 0x04 0x49 0x4d 0x34 0x50)
    type            IA5String,              -- 4CC identifier: "trca", "trst", "extc", "rtsc", "trcs"
    desc            IA5String,              -- Payload version string: ASCII "1" (0x16 0x01 0x31)
    payload         OCTET STRING            -- Raw TrustCache binary stream (offset 0x17 or 0x19)
}
```

The 4CC type tags designate partition trust domains:
- `trst`: Production System Static TrustCache (`141-08876-216` RootFS, `141-09644-240` Base OS).
- `rtsc`: Restore RamDisk TrustCache (`141-09491-242`, `141-10399-240`).
- `trcs`: Cryptex1 SystemOS TrustCache (`141-09724-226`).
- `extc`: ExclaveOS Microkernel TrustCache (`141-08904-238`).
- `trca`: Cryptex1 AppOS Extension TrustCache (`141-08824-244`).

### 2.3 Binary Header & Structural Evolution: v1 vs v2

The raw payload encapsulated inside each IM4P container begins with a 24-byte master header:

```c
struct trust_cache_header {
    uint32_t version;     /* 1 = Legacy/Exclave, 2 = Modern iOS with Launch Constraints */
    uint8_t  uuid[16];    /* 128-bit RFC 4122 container UUID */
    uint32_t num_entries; /* Total entry count (little-endian unsigned 32-bit int) */
} __attribute__((__packed__));
```

#### TrustCache v1 (22 Bytes per Entry)
Used in 3 binaries (`141-08904-238` ExclaveOS, `141-09491-242` RamDisk, `141-10399-240` Update RamDisk), totaling 821 entries:
```c
struct trust_cache_entry_v1 {
    uint8_t cdhash[20];   /* Truncated 160-bit SHA-256 Code Directory digest */
    uint8_t hash_type;    /* 2 = CS_HASHTYPE_SHA256 (100% of entries in iOS 27.2) */
    uint8_t flags;        /* 0 = Standard, 2 = Exclave/Restricted */
} __attribute__((__packed__));
```

#### TrustCache v2 (24 Bytes per Entry)
Used in 4 binaries (`141-08824-244` AppOS, `141-08876-216` RootFS, `141-09644-240` Base OS, `141-09724-226` SystemOS), totaling 4,383 entries:
```c
struct trust_cache_entry_v2 {
    uint8_t cdhash[20];            /* Truncated 160-bit SHA-256 Code Directory digest */
    uint8_t hash_type;             /* 2 = CS_HASHTYPE_SHA256 */
    uint8_t flags;                 /* 0 = Standard, 1 = AMFID Bootstrap, 2 = Restricted */
    uint8_t constraint_category;   /* Launch Constraint Category index (0..18) */
    uint8_t reserved0;             /* Padding byte (empirically 0x00 across all 4,383 entries) */
} __attribute__((__packed__));
```

### 2.4 Cryptographic Hashing & Pre-Sorted Binary Search Invariant

Analysis across all 5,204 entries confirms two vital architectural properties:
1. **100% SHA-256 Uniformity**: Across all 7 TrustCache files, 100% of entries declare `hash_type == 2` (`CS_HASHTYPE_SHA256`). There are **zero SHA-1 entries** in iOS 27.2.
2. **Lexicographical Sort Invariant**: In every TrustCache file, entries are strictly sorted in ascending order of their 20-byte `cdhash` values:
   $$\text{cdhash}_{i} < \text{cdhash}_{i+1} \quad \forall \; i \in [0, N-2]$$
   This invariant allows the kernel function `_check_cdhash_in_trustcache` to perform an $O(\log_2 N)$ binary search over memory-mapped TrustCache tables without requiring in-kernel sorting, hash table allocations, or dynamic memory overhead during process execution (`execve`).

---

## 3. TrustCache v2 Execution Constraint Categories

TrustCache v2 embeds an 8-bit unsigned integer `constraint_category` at offset 22 of each entry. Rather than merely authenticating code identity, TrustCache v2 enforces execution privilege separation at the kernel boundary.

### Table 3.1: Execution Constraint Category Distribution & Privilege Roles

| Category ID | Total Entries | RootFS (`141-08876-216`) | Recovery (`141-09644-240`) | Cryptex (`141-09724-226`) | AppOS (`141-08824-244`) | Architectural Role & Privilege Domain | Representative Executables |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **0** | 396 | 222 | 67 | 107 | 0 | Unconstrained / Cryptex Default | Dynamic linkers, utility scripts |
| **1** | 729 | 621 | 93 | 1 | 14 | Core System Daemons & Services | `wifid`, `bluetoothd`, `securityd`, `tccd` |
| **2** | 1,609 | 1,491 | 86 | 12 | 20 | High-Privilege Bootstrap & Runtime | `/sbin/launchd`, `/usr/lib/dyld` |
| **3** | 116 | 90 | 26 | 0 | 0 | Security & Network Infrastructure | `/usr/libexec/trustd`, `bootpd`, `mDNSResponder` |
| **4** | 857 | 831 | 21 | 5 | 0 | App Extensions & Diagnostic PlugIns | `.appex` bundles, `SpringBoardDiagnosticExtension` |
| **5** | 376 | 347 | 22 | 7 | 0 | Framework Helpers & Cryptex OS Tools | WebKit helpers, Safari sync daemons |
| **10** | 16 | 9 | 7 | 0 | 0 | Specialized Hardware Controllers | Sensor monitors, baseband helpers |
| **11** | 23 | 18 | 5 | 0 | 0 | Telephony & Diagnostic Logging | Cellular interface daemons, `sysdiagnosed` |
| **12** | 15 | 8 | 7 | 0 | 0 | Factory Diagnostics & Network Subsystems | Hardware test agents |
| **14** | 191 | 191 | 0 | 0 | 0 | Core Root System Applications | `/Applications/Preferences.app/Preferences` |
| **15** | 2 | 2 | 0 | 0 | 0 | Critical Hardware Enclave Agents | Biometric & Keybag security managers |
| **16** | 52 | 52 | 0 | 0 | 0 | Staged System Applications | `/private/var/staged_system_apps/*.app` |
| **18** | 1 | 1 | 0 | 0 | 0 | Hardened Security Domain Agent | Kernel security bridge daemon |

---

## 4. The AMFID Bootstrap Trust Gate (`flags == 1`)

In the Apple Code Signing architecture, userland signature verification creates an inherent bootstrap circularity:
- The XNU kernel delegates third-party code validation to the userland daemon `amfid` (`/usr/libexec/amfid`) via Mach IPC message port `com.apple.MobileFileIntegrity`.
- However, when `launchd` spawns `amfid` during system ignition, the kernel cannot query `amfid` to validate `amfid`'s own signature.

Apple resolves this bootstrap recursion in iOS 27.2 via the TrustCache entry `flags` byte:
- Exactly **1 unique CDHash** across the entire 5,204-entry corpus has `flags == 1`:
  $$\text{CDHash} = \mathtt{8c8cbe476a8882df62f8250d7f1e7903778445f6}$$
- This CDHash appears in exactly 2 TrustCache files:
  - `141-08876-216.dmg.aea.trustcache` (RootFS, index 2,108)
  - `141-09644-240.dmg.aea.trustcache` (Base OS, index 201)
- Calculating the SHA-256 Code Directory hash from `artifacts/rootfs/binaries/usr/libexec/amfid` confirms an exact match:
  $$\text{SHA256}(\text{CS\_CodeDirectory})[0:20] = \mathtt{8c8cbe476a8882df62f8250d7f1e7903778445f6}$$

When AMFI's kernel hook `mac_vnode_check_signature` encounters an executable matching this CDHash with `flags == 1`, AMFI assigns `CS_VALID | CS_PLATFORM_BINARY | CS_HARD | CS_KILL`, establishing the root of userland integrity without invoking userland RPC.

---

## 5. Comprehensive CDHash Database & Binary Cross-Referencing

The master CDHash database (`artifacts/security/cdhash_database.json`) correlates all 4,527 unique CDHashes with 680 decrypted system executables across the root filesystem, application bundles, and system daemons.

### 5.1 CodeDirectory Hash Derivation Mathematics

Every 64-bit Mach-O binary embeds an `LC_CODE_SIGNATURE` load command (`cmd = 0x1d`):
```
Mach-O Header (64-bit ARM64E)
  └── LC_CODE_SIGNATURE (cmd 0x1d, dataoff, datasize)
        └── CS_SuperBlob (magic 0xfade0cc0, count N)
              ├── Slot 0: CSSLOT_CODEDIRECTORY (magic 0xfade0c02)
              ├── Slot 2: CSSLOT_REQUIREMENTS (magic 0xfade0c01)
              ├── Slot 5: CSSLOT_ENTITLEMENTS (magic 0xfade7171, XML property list)
              ├── Slot 7: CSSLOT_DER_ENTITLEMENTS (magic 0xfade7172, ASN.1 DER stream)
              └── Slot 9: CSSLOT_LAUNCH_CONSTRAINTS (magic 0xfade8181)
```

Within `CSSLOT_CODEDIRECTORY`, the header declares:
```c
struct CS_CodeDirectory {
    uint32_t magic;          /* 0xfade0c02 */
    uint32_t length;         /* Total CodeDirectory byte size */
    uint32_t version;        /* 0x20400 */
    uint32_t flags;          /* CS_ADHOC, CS_HARD, CS_KILL, etc. */
    uint32_t hashOffset;     /* Offset to slot 0 page hash */
    uint32_t identOffset;    /* Offset to UTF-8 signing identifier */
    uint32_t nSpecialSlots;  /* Negative slot count (requirements, entitlements) */
    uint32_t nCodeSlots;     /* Total signed virtual memory page count */
    uint32_t codeLimit;      /* Signed binary payload byte limit */
    uint8_t  hashSize;       /* 32 bytes */
    uint8_t  hashType;       /* 2 = SHA-256 */
    uint8_t  platform;       /* Platform binary identifier */
    uint8_t  pageSize;       /* log2(page_size), 12 = 4096 bytes or 14 = 16384 bytes */
    uint32_t spare2;
};
```

The 20-byte truncated CDHash is calculated over the entire `CS_CodeDirectory` blob:
$$\text{CDHash} = \text{SHA256}(\text{CS\_CodeDirectory}[0:\text{length}])[0:20]$$

### Table 5.1: Master Cross-Reference of Key System Binaries and Empirical CDHashes

| Canonical Binary Path | Embedded Signing Identifier | Mach-O CPUType / Subtype | PAC ABI | Calculated CDHash (Truncated SHA-256) | TrustCache Category | Code Signing Flags |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| `/sbin/launchd` | `com.apple.xpc.launchd` | ARM64 / ARM64E | PAC00 | `51d581be575bfc1e9cf2587eb39beddedb235158` | 2 | `CS_ADHOC` (`0x02`) |
| `/usr/lib/dyld` | `com.apple.darwin.ignition` | ARM64 / ARM64E | PAC00 | `73eacd413d3930ebcde071068c63fef0f8102f55` | 2 | `CS_ADHOC` (`0x02`) |
| `/usr/libexec/amfid` | `com.apple.amfid` | ARM64 / ARM64E | PAC00 | `8c8cbe476a8882df62f8250d7f1e7903778445f6` | 1 | `CS_ADHOC` (`0x02`) |
| `/usr/libexec/trustd` | `com.apple.trustd` | ARM64 / ARM64E | PAC00 | `0b5433aa7439283094c030a9c16456799d81e9de` | 3 | `CS_ADHOC` (`0x02`) |
| `/usr/libexec/securityd` | `com.apple.securityd` | ARM64 / ARM64E | PAC00 | `e7bc79e7b5a913215db536a7d7c4a85806936ced` | 1 | `CS_ADHOC` (`0x02`) |
| `/usr/sbin/wifid` | `com.apple.wifi.manager` | ARM64 / ARM64E | PAC00 | `a5ff38b588233405d997690069a66a8a47720e06` | 1 | `CS_ADHOC` (`0x02`) |
| `/usr/sbin/bluetoothd` | `com.apple.bluetoothd` | ARM64 / ARM64E | PAC00 | `fa1857d47dc01663ae83a04228369e4fbb975393` | 1 | `CS_ADHOC` (`0x02`) |
| `Support/CommCenter` | `com.apple.coretelephony` | ARM64 / ARM64E | PAC00 | `89ec2935164378e0998fce57495710bceea2a344` | 1 | `CS_ADHOC` (`0x02`) |
| `Support/tccd` | `com.apple.tccd` | ARM64 / ARM64E | PAC00 | `e2d0ef627e51340ebf65a61717170e42f20d835f` | 1 | `CS_ADHOC` (`0x02`) |
| `SpringBoard.app/SpringBoard` | `com.apple.springboard` | ARM64 / ARM64E | PAC00 | `93942d0622f54ff1b788f6e902d186fc01f2340f` | 1 | `CS_ADHOC` (`0x02`) |
| `Preferences.app/Preferences` | `com.apple.Preferences` | ARM64 / ARM64E | PAC00 | `9b63d84cea4639f88b4cf71bc08cca3401175fba` | 14 | `CS_ADHOC` (`0x02`) |
| `Reminders.app/Reminders` | `com.apple.reminders` | ARM64 / ARM64E | PAC00 | `a7db321a7c95eafe7212e262739c12f456bdb1d6` | 16 | `CS_ADHOC` (`0x02`) |
| `MobileSafari.app/MobileSafari` | `com.apple.mobilesafari` | ARM64 / ARM64E | PAC00 | `9fed373e9a31f6c715cd75cbf70d126ff4a6b8ca` | 16 | `CS_ADHOC` (`0x02`) |

---

## 6. Full-Stack Entitlement Matrix & 4-Tier Security Taxonomy

Across the 680 system executables cataloged in `artifacts/security/entitlements_analysis.json`, 667 binaries embed code signing entitlements, yielding **4,463 unique entitlement keys**. These keys are structured into a 4-tier security hierarchy:

```
Full-Stack Entitlement Taxonomy (4,463 Unique Keys)
├── Tier 1: Root / Hardware Capabilities (238 keys)
├── Tier 2: Private Apple Entitlements (1,620 keys)
├── Tier 3: TCC Access Overrides (24 keys, 99 asserted services)
├── Tier 4: Mach Lookup Assertions (8 keys, 1,723 asserted endpoints)
└── Standard & Developer Capabilities (2,573 keys)
```

### Table 6.1: Taxonomy Metrics and Boundary Roles

| Entitlement Security Tier | Unique Key Count | Asserted Tokens / Endpoints | Enforcing Subsystem | Privilege Boundary Function |
| :--- | :---: | :---: | :--- | :--- |
| **1. Root / Hardware Capabilities** | 238 | N/A | XNU Kernel & SPTM | Authorizes direct hardware, NVRAM, kernel task ports, SIP rootless bypass, and PMAP TrustCache operations. |
| **2. Private Apple Entitlements** | 1,620 | N/A | Apple Security Daemons | Authorizes private cross-daemon SPI communication (`com.apple.private.*`). |
| **3. TCC Access Overrides** | 24 | 99 Services | `tccd` & Privacy Frameworks | Hard-coded authorization bypassing user privacy consent prompts for camera, mic, photos, contacts, and location. |
| **4. Mach Lookup Assertions** | 8 | 1,723 Endpoints | Sandbox Kernel Extension | Whitelists process capability to resolve and communicate with global Mach service ports via `bootstrap_look_up`. |
| **Standard / Developer Capabilities** | 2,573 | N/A | AMFI Userland Validation | Standard capabilities (`com.apple.developer.*`), keychain access groups, App Groups. |

### 6.2 Deep-Dive Entitlement Profile Audits

#### `/sbin/launchd` (PID 1 Root Supervisor)
- `com.apple.private.pmap.load-trust-cache`: Array of authorized TrustCache domains (`cryptex1.boot.os`, `cryptex1.boot.app`, `cryptex1.boot.rosetta`). Enables PID 1 to instruct the SPTM/PMAP subsystem to map supplemental TrustCache tables into kernel virtual memory.
- `com.apple.private.amfi.can-allow-non-platform`: Authorizes launchd to spawn developer-signed and non-platform binaries in developer mode.
- `com.apple.private.kernel.system-override`: Authorizes kernel subsystem configuration overrides.
- `com.apple.private.iokit.system-nvram-allow`: Direct raw NVRAM variable manipulation.

#### `/usr/libexec/amfid` (Apple Mobile File Integrity Daemon)
- `com.apple.private.mis.trust.set`: Grants amfid exclusive authority to write dynamic trust anchors to the kernel AMFI driver.
- `com.apple.private.amfi.developer-mode-control`: Authorizes toggling of Developer Mode state machines.
- `com.apple.private.security.storage.amfid`: Exclusive private storage container isolation.
- `com.apple.keystore.keybag.load`: Keybag decryption authorization for provisioning profiles.

#### `SpringBoard.app` (System UI Compositor & Shell)
- Contains 534 entitlements and 52 Mach service registrations.
- `com.apple.private.tcc.allow`: Grants SpringBoard unprompted access to `kTCCServiceAddressBook`, `kTCCServiceCalendar`, `kTCCServiceCamera`, `kTCCServicePhotos`, `kTCCServiceMicrophone`, and `kTCCServiceFaceID`.
- `com.apple.security.mach-lookup.global-name`: Asserts lookup access to 142 distinct system Mach services including `com.apple.backboard.display.services`, `com.apple.coremedia.admin`, and `com.apple.appprotectiond.read`.

---

## 7. AMFI Kernel Implementation & Hook Disassembly

The kernel driver `com.apple.driver.AppleMobileFileIntegrity` is embedded within the `MH_FILESET` kernelcache (`artifacts/kernel/kernelcache.release.raw`). AMFI registers Mandatory Access Control (MAC) hooks that intercept all file execution requests.

### 7.1 `mac_vnode_check_signature` Disassembly Citation

- **Virtual Address**: `0xfffffe0009297d7c` (kernelcache file offset `0x2293d7c`)
- **ARM64E PAC Architecture**: Employs Pointer Authentication B-key instruction prologue (`pacibsp` = `0xd503237f`) and allocates an 816-byte stack frame (`0x330`):

```assembly
; ==============================================================================
; Subroutine: com.apple.driver.AppleMobileFileIntegrity:mac_vnode_check_signature
; Target VA:  0xfffffe0009297d7c
; Signature:  int mac_vnode_check_signature(struct vnode *vp, struct label *vl,
;                                           user_addr_t cs_blob, int flags)
; ==============================================================================
0xfffffe0009297d7c: 7f 23 03 d5    pacibsp                         ; Sign LR with Instruction B-key
0xfffffe0009297d80: fc 6f ba a9    stp    x28, x27, [sp, #-0x60]!  ; Allocate frame & spill callee-saved registers
0xfffffe0009297d84: fa 67 01 a9    stp    x26, x25, [sp, #0x10]
0xfffffe0009297d88: f8 5f 02 a9    stp    x24, x23, [sp, #0x20]
0xfffffe0009297d8c: f6 57 03 a9    stp    x22, x21, [sp, #0x30]
0xfffffe0009297d90: f4 4f 04 a9    stp    x20, x19, [sp, #0x40]
0xfffffe0009297d94: fd 7b 05 a9    stp    fp, lr, [sp, #0x50]
0xfffffe0009297d98: fd 43 01 91    add    fp, sp, #0x50
0xfffffe0009297d9c: ff c3 0c d1    sub    sp, sp, #0x330           ; Reserve 816 bytes for signature validation state
0xfffffe0009297da0: e6 af 00 b9    str    w6, [sp, #0xac]
0xfffffe0009297da4: f7 03 05 aa    mov    x23, x5
0xfffffe0009297da8: fa 03 04 aa    mov    x26, x4
...
0xfffffe0009297ddc: a0 1e ff b0    adrp   x0, 0xfffffe000766c000   ; Format string: "AMFI: vnode_check_signature called with platform %d"
0xfffffe0009297de0: 00 10 1b 91    add    x0, x0, #0x6c4           ; Address: 0xfffffe000766c6c4
0xfffffe0009297de4: ae 6d 00 94    bl     0xfffffe00092b349c       ; os_log_debug telemetry logger
...
0xfffffe0009297e24: 30 0a c1 da    pacda  x16, x1                  ; Authenticate data pointer with A-key
...
0xfffffe0009297e70: 90 1b c1 da    autda  x16, x27                 ; Verify data pointer integrity
```

### 7.2 `_check_cdhash_in_trustcache` Disassembly Citation

- **Virtual Address**: `0xfffffe0009299730` (kernelcache file offset `0x2295730`)
- **ARM64E PAC Architecture**: Employs `pacibsp` (`0xd503237f`), allocating a 304-byte frame (`0x130`):

```assembly
; ==============================================================================
; Subroutine: com.apple.driver.AppleMobileFileIntegrity:_check_cdhash_in_trustcache
; Target VA:  0xfffffe0009299730
; Signature:  int _check_cdhash_in_trustcache(const uint8_t cdhash[20],
;                                             uint32_t *out_category, uint32_t *out_flags)
; ==============================================================================
0xfffffe0009299730: 7f 23 03 d5    pacibsp                         ; Sign LR with Instruction B-key
0xfffffe0009299734: ff c3 04 d1    sub    sp, sp, #0x130           ; Allocate 304-byte frame
0xfffffe0009299738: fa 67 0e a9    stp    x26, x25, [sp, #0xe0]
0xfffffe000929973c: f8 5f 0f a9    stp    x24, x23, [sp, #0xf0]
0xfffffe0009299740: f6 57 10 a9    stp    x22, x21, [sp, #0x100]
0xfffffe0009299744: f4 4f 11 a9    stp    x20, x19, [sp, #0x110]
0xfffffe0009299748: fd 7b 12 a9    stp    fp, lr, [sp, #0x120]
0xfffffe000929974c: fd 83 04 91    add    fp, sp, #0x120
0xfffffe0009299750: a8 75 ff d0    adrp   x8, 0xfffffe000766c000   ; Master in-kernel TrustCache linked list head
0xfffffe0009299754: 08 b1 47 f9    ldr    x8, [x8, #0xf60]
0xfffffe0009299758: 08 01 40 f9    ldr    x8, [x8]
0xfffffe000929975c: a8 83 1b f8    stur   x8, [x29, #-0x48]
```

**Bypass Mechanism**:
When `_check_cdhash_in_trustcache` locates the target CDHash in the pre-sorted static tables:
1. It immediately assigns `CS_VALID | CS_PLATFORM_BINARY` to the vnode's code signing state.
2. The userland Mach message dispatch to `/usr/libexec/amfid` is completely bypassed.
3. The binary achieves zero-overhead execution authorization.

### 7.3 `mac_cred_label_update_execve` Disassembly Citation

- **Virtual Address**: `0xfffffe00092961f4` (kernelcache file offset `0x22921f4`)
- **ARM64E PAC Architecture**: Employs `pacibsp` (`0xd503237f`), allocating a 144-byte frame (`0x90`):

```assembly
; ==============================================================================
; Subroutine: com.apple.driver.AppleMobileFileIntegrity:mac_cred_label_update_execve
; Target VA:  0xfffffe00092961f4
; Signature:  void mac_cred_label_update_execve(struct ucred *old_cred, struct ucred *new_cred,
;                                               struct proc *p, struct vnode *vp, ...)
; ==============================================================================
0xfffffe00092961f4: 7f 23 03 d5    pacibsp                         ; Sign LR with Instruction B-key
0xfffffe00092961f8: ff 43 02 d1    sub    sp, sp, #0x90            ; Allocate 144-byte frame
0xfffffe00092961fc: fc 6f 03 a9    stp    x28, x27, [sp, #0x30]
0xfffffe0009296200: fa 67 04 a9    stp    x26, x25, [sp, #0x40]
0xfffffe0009296204: f8 5f 05 a9    stp    x24, x23, [sp, #0x50]
0xfffffe0009296208: f6 57 06 a9    stp    x22, x21, [sp, #0x60]
0xfffffe000929620c: f4 4f 07 a9    stp    x20, x19, [sp, #0x70]
0xfffffe0009296210: fd 7b 08 a9    stp    fp, lr, [sp, #0x80]
0xfffffe0009296214: fd 03 02 91    add    fp, sp, #0x80
0xfffffe0009296218: e2 32 00 b4    cbz    x2, 0xfffffe0009296874   ; Abort if proc is NULL
...
0xfffffe0009296284: ADRP + ADD pointing to string:
; "AMFI: hook..execve() killing %s (pid %u): Attempt to execute completely unsigned code"
```

If an executable is neither present in any TrustCache nor validated by `amfid`, AMFI triggers an unconditional kernel termination (`SIGKILL`) with the diagnostic above.

---

## 8. Sandbox Architecture & Kernel Pre-Compiled Bytecode Container

The iOS 27.2 sandbox subsystem (`com.apple.security.sandbox`) enforces fine-grained capability isolation across system daemons and applications.

### 8.1 Filesystem Scheme Profiles vs Kernel Pre-Compiled Bytecode

The sandbox environment utilizes a dual-tier policy representation:
1. **Userland Scheme Profiles (`.sb`)**: 42 plaintext Scheme files reside in framework bundles and system directories inside the RootFS (e.g., `System/Library/Sandbox/Profiles/com.apple.doorsd.sb`). These profiles declare operations such as `(deny default)`, `(deny file-map-executable)`, and `(deny dynamic-code-generation)`.
2. **Kernel Pre-Compiled Bytecode Container**: In the release kernelcache, the compiled policy database is embedded directly inside the `com.apple.security.sandbox` fileset entry (`vmaddr = 0xfffffe0007b76f70`, file offset `0xb72f70`).

### 8.2 Embedded Bytecode Metrics

Within section `__TEXT,__const`:
- **Bytecode Container VA**: `0xfffffe0007b79330`
- **Bytecode Container File Offset**: `0xb75330`
- **Container Size**: Exactly **2,038,569 bytes** (~2.04 MB)
- **Policy Complexity**: Contains **18,224 pre-compiled bytecode rules**, operation filters, and literal entitlement keys.

Empirical string extraction from the container at `0xb75330` reveals direct enforcement strings:
- `com.apple.developer.cs.allow-jit` (JIT dynamic compilation authorization)
- `com.apple.private.cs.allow-jit`
- `com.apple.rootless.storage.Safari`
- `task_for_pid-allow`
- `com.apple.system-task-ports.control`

When a sandboxed process invokes a Mach trap (`mach_msg`) or file access syscall (`open`, `stat`), the sandbox kernel extension walks this pre-compiled decision tree in memory. If an entitlement required by a branch is missing from the process's verified credential label, the operation is blocked with `EPERM` without consulting userland.

---

## 9. Secure Page Table Monitor (SPTM) & Hardware-Enforced Memory Immutability

The fundamental constraint that prevents bypass of AMFI and Sandbox checks in iOS 27.2 is the Secure Page Table Monitor (SPTM), executing at ARMv9.2-A Exception Level 2 (EL2).

### 9.1 Stage-2 Translation Control (`VTTBR_EL2`)

Under the ARM64 virtualization architecture on the Apple `t8150` SoC:
- The XNU kernel operates at EL1 and manages Stage-1 virtual-to-physical translation tables (`TTBR0_EL1` for userland, `TTBR1_EL1` for kernel).
- However, the hardware MMU routes all physical address accesses through Stage-2 translation controlled by `VTTBR_EL2` (Virtualization Translation Table Base Register at EL2).
- The SPTM firmware owns `VTTBR_EL2`. The XNU kernel possesses **no write permissions** to its own Stage-1 page tables in the Stage-2 translation map.

```
CPU Memory Access (VA)
    │
    ▼
[Stage-1 MMU (EL1)] ──► Intermediate Physical Address (IPA)
                            │
                            ▼
                        [Stage-2 MMU (EL2 - SPTM VTTBR_EL2)]
                            │
                            ├─► Physical DRAM (PA)
                            └─► Exception Trap (Monitor Fault if CTRR or W^X violated)
```

### 9.2 The 59 Physical Frame Types & CTRR Hardware Locks

As cataloged in `artifacts/kernel/sptm_analysis.json`:
1. Every physical 16 KB DRAM page is assigned one of **59 frame types** (`SPTM_FRAME_TYPE_*`) tracked in an internal monitor database.
2. **Configurable Translation Read-Only Region (CTRR)** registers in the memory controller hardware-lock the kernel's read-only zones (`XNU_ROZONE`, `SPTM_CODE`, `AMFI_POLICY`).
3. To alter page permissions (e.g., executing `mprotect` with `PROT_EXEC`), XNU must execute an `HVC` (Hypervisor Call) or `SMC` trap into SPTM.
4. The SPTM handler validates:
   - Is the target frame backed by an immutable TrustCache entry?
   - Does the process hold the requisite `com.apple.private.cs.allow-jit` or `dynamic-code-generation` entitlement?
   - If not, the hypervisor refuses to clear the Stage-2 Execute-Never (`XN`) bit, permanently preventing execution of unauthorized code even in the presence of an arbitrary kernel read/write primitive.

---

## 10. Platform Security Architecture Synthesis

The integration of TrustCache, AMFI, Sandbox, and SPTM forms an unbroken, mathematically verifiable chain of trust across iOS 27.2:

```
[Hardware BootROM / SecureROM]
       │  (Authenticates iBoot via Hardware PKI)
       ▼
[iBoot (Stage 2)]
       │  (Loads and verifies SPTM, TXM, and MH_FILESET Kernelcaches)
       ▼
[SPTM Monitor (EL2)] ◄── Locks Stage-2 MMU (VTTBR_EL2) & CTRR Registers
       │
       ▼
[XNU Kernel (EL1)]
       │
       ├─► [AMFI Kernel Driver]
       │         │
       │         ├─► Evaluates CDHash against 7 In-Kernel TrustCaches (5,204 Entries)
       │         │         │
       │         │         ├─► [MATCH]: Sets CS_VALID | CS_PLATFORM_BINARY (Bypasses AMFID)
       │         │         └─► [NO MATCH]: Triggers Mach RPC to /usr/libexec/amfid
       │         │
       │         └─► Enforces Launch Constraints (Categories 0..18)
       │
       ├─► [Sandbox KEXT] ◄── Walks 2.04 MB Pre-Compiled Bytecode (0xfffffe0007b79330)
       │
       ▼
[Userland Ignition (PID 1: launchd)]
       │  (Authenticated via TrustCache Category 2: 51d581be575bfc1e9cf2587eb39beddedb235158)
       │
       ├─► Spawns /usr/libexec/amfid (Validated via TrustCache flags == 1 Bootstrap Gate)
       ├─► Spawns Core System Daemons (Category 1: wifid, bluetoothd, securityd, tccd)
       ├─► Spawns Security Services (Category 3: trustd, bootpd)
       └─► Launches SpringBoard & Staged System Applications (Categories 14 & 16)
```

Through this unified architecture, iOS 27.2 achieves total privilege compartmentalization, ensuring that platform binaries, dynamic extensions, and hardware capabilities remain strictly bounded by cryptographic signatures and hardware-enforced memory immutability.
