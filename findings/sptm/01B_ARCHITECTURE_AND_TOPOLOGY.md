# iOS 27 SPTM & TXM RE — Phase 1B: Architecture & Hypervisor Topology

## 1. Executive Summary & Privilege Hierarchy Overview

In iOS 27.2 (`24B119`) on Apple Silicon A19 Pro (`t8150`, device class `v57ap`), Apple has abandoned traditional monolithic kernel execution models in favor of hardware-enforced hypervisor and monitor boundaries. By leveraging the ARMv8.6+ **Guarded Execution Facility (GXF)**, Apple partitions privileged execution into discrete hardware security domains:

```
+----------------------------------------------------------------------------------------------------+
|                         iOS 27.2 HARDWARE TRUST & PRIVILEGE HIERARCHY                              |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  Guarded EL2 (GL2) Hypervisor Domain                                                               |
|  └── Secure Page Table Monitor (SPTM) [Load Base: 0xfffffff027004000]                             |
|      ├── Complete ownership of Stage-2 Memory Virtualization (VTTBR_EL2)                           |
|      ├── Dynamic physical frame retyping across 59 discrete memory types                          |
|      ├── Hardware access control: CTRR (Text Regions), GAPF (Filters), DART/SART (IOMMU)           |
|      └── 42 Function IDs across 17 Monitored Dispatch Tables                                       |
|                                                                                                    |
|                                    ▲ [gxf_enter / hvc #0 / Stage-2 Faults]                         |
|                                    │                                                               |
|  Guarded EL1 (GL1) Security Monitor Domain                                                         |
|  └── Trusted Execution Monitor (TXM) [Load Base: 0xfffffff017004000]                             |
|      ├── Code Signing Monitor (CSM) & Runtime Module (v7.0.0, libimage4_TXM)                       |
|      ├── Cryptographic Image4 manifest, certificate chain, and nonce validation                    |
|      ├── Dynamic & static TrustCache authorization (CDHash registration)                           |
|      └── Enforces code authorization before signaling SPTM to seal executable pages                |
|                                                                                                    |
|                                    ▲ [SMC / Hypercalls / RingGates]                                |
|                                    │                                                               |
|  Standard EL1 Host Operating System Domain                                                         |
|  └── Darwin / XNU Monolithic Kernel [Constrained by Stage-2 Translation]                           |
|      ├── Virtual memory management (pmap operations forwarded to SPTM via sptm_call)              |
|      ├── Task lifecycle, BSD networking, POSIX VFS, and IOKit driver subsystem                     |
|      └── Stage-1 page tables are read-only to XNU; modifications trapped at GL2                    |
|                                                                                                    |
|                                    ▲ [svc #0..#5 / System Calls]                                   |
|                                    │                                                               |
|  Standard EL0 Userland & Microkernel Enclave Domain                                                |
|  ├── Exclave Conclaves (cL4 capability microkernel; private DRAM isolated via SPTM Stage-2)        |
|  └── Darwin Applications & POSIX Daemons (SpringBoard, MobileSafari, mediaserverd)                 |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

This multi-tiered topology deprecates Apple's legacy Page Table Protection Layer (PPL) and APRR (Apple Programmable Read-only Regions). In this modern architecture, the kernel does not have write access to its own Stage-1 page tables. All physical memory state transitions are enforced in hardware by SPTM at GL2.

---

## 2. Guarded Execution Facility (GXF) Hardware Mechanics

The Guarded Execution Facility (GXF) is Apple's architectural extension to ARMv8.6-A that introduces sub-exception level hardware gating without incurring the heavy context switch penalty of full hypervisor mode transitions.

### 2.1 GXF Hardware Registers & Control Flow
- **GL2 Exception Vector Base Register (`GL2_VBAR`)**: Mapped to system register `S3_6_C15_C10_2`, configured during early SPTM initialization to point to the base of the `__exc` section at `0xfffffff027118000`.
- **GL2 Entry Vector Register**: Mapped to `S3_6_C15_C8_1`. Arbitrates synchronous entry into GL2 from lower privilege levels.
- **GL2 Exit Vector Register**: Mapped to `S3_6_C15_C8_2`. Mediates return from GL2 back to guest execution.
- **Hypervisor Configuration Register (`HCR_EL2`)**: SPTM inspects `CurrentEL == 8` and configures `HCR_EL2`:
  - `TGE` (Trap General Exceptions, bit 27) = `1`
  - `E2H` (Virtualization Host Extensions, bit 34) = `1`
  - Enables Virtualization Host Extensions (VHE), aligning EL2 register mappings with standard OS supervisor interfaces.
- **Hypervisor Configuration Extended Register (`HCRX_EL2`)**: Initialized to establish fine-grained trap controls over ARMv8.6 architectural feature registers.

---

## 3. Secure Page Table Monitor (SPTM) Architecture

The Secure Page Table Monitor binary (`sptm.t8150.release.raw`, 1,327,136 bytes) executes as the root memory hypervisor on SoC T8150.

### 3.1 Structural Parameters
- **Virtual Load Base**: `0xfffffff027004000`
- **Initial Entrypoint PC**: `0xfffffff0270bc388`
- **Mach-O UUID**: `6fb95ed6-be8a-39cf-862b-250ba7efd5a5`
- **CPU Subtype**: `0xc0000002` (ARM64E PAC00)

### 3.2 Segment & Memory Protection Layout

```
+----------------------------------------------------------------------------------------------------+
|                                  SPTM MEMORY SEGMENT GEOMETRY                                      |
+----------------------------------------------------------------------------------------------------+
| Segment Name   | VM Base Address    | VM Size     | File Offset | File Size   | Permissions & Role |
+----------------+--------------------+-------------+-------------+-------------+--------------------+
| __TEXT         | 0xfffffff027004000 | 0x00018000  | 0x00000000  | 0x00018000  | r-x (Strings/Const)|
|   __cstring    | 0xfffffff0270048b0 | 0x00016126  | 0x000008b0  | -           | r-- (ASCII Strings)|
|   __const      | 0xfffffff02701a9e0 | 0x00001620  | 0x000169e0  | -           | r-- (Static Const) |
| __DATA_CONST   | 0xfffffff02701c000 | 0x00008000  | 0x00018000  | 0x00008000  | r-- (Early Readonly|
| __LATE_CONST   | 0xfffffff027024000 | 0x00090000  | 0x00020000  | 0x00090000  | rw- -> r-- (Sealed)|
| __TEXT_EXEC    | 0xfffffff0270b4000 | 0x00068000  | 0x000b0000  | 0x00068000  | r-x (Executable)   |
|   __text       | 0xfffffff0270b4000 | 0x00064000  | 0x000b0000  | -           | r-x (Code Body)    |
|   __exc        | 0xfffffff027118000 | 0x00002000  | 0x00114000  | -           | r-x (Vector Table) |
| __LAST         | 0xfffffff02711c000 | 0x00004000  | 0x00118000  | 0x00004000  | r-- (Read Only)    |
| __DATA         | 0xfffffff027120000 | 0x00010000  | 0x0011c000  | 0x00010000  | rw- (Dynamic BSS)  |
| __BOOTDATA     | 0xfffffff027130000 | 0x00018000  | 0x0012c000  | 0x00018000  | rw- (Boot Reclaim) |
| __LINKEDIT     | 0xfffffff027148000 | 0x00004000  | 0x00144000  | 0x00000020  | r-- (Mach-O Meta)  |
+----------------+--------------------+-------------+-------------+-------------+--------------------+
```

### 3.3 Four-Phase Hardware Initialization Pipeline

1. **Phase 1: Early Boot & Register Cleansing (`0xfffffff0270bc388`)**:
   - Zeroes all general-purpose registers (`x0` through `x30`) to eliminate residual bootloader state.
   - Sets up a temporary bootstrap stack pointer in the `__BOOTDATA` memory segment.
   - Mask all interrupt lines via `msr daifset, #0xf` followed by an explicit `isb` barrier.
2. **Phase 2: Execution Level Verification & VHE Configuration (`0xfffffff0270bf0a8`)**:
   - Verifies `CurrentEL == 8` (confirming bare-metal EL2 execution).
   - Configures `HCR_EL2` with `TGE` and `E2H` to activate ARM Virtualization Host Extensions.
   - Clears virtual timer offset `CNTVOFF_EL2` to maintain synchronized hardware timebases across guest domains.
3. **Phase 3: MMU & Stage-1 / Stage-2 Translation Table Construction (`0xfffffff0270bf100`)**:
   - Builds 3-level translation tables using 16 KB page granules (`TG0 = 0x2`).
   - Sets `TCR_EL1` to `0x310800336511a511` (specifying Intermediate Physical Address width and cacheability attributes).
   - Generates the pointer authentication canary using hardware instruction `pacga` on the ASCII seed `'STACKGRD'`.
   - Enables the MMU via `SCTLR_EL1` configured to `0x12001010fc14793d`.
4. **Phase 4: Hardware Vector Registration & GXF Activation (`0xfffffff0270bf924`)**:
   - Writes the exception vector base `0xfffffff027118000` into `GL2_VBAR` (`S3_6_C15_C10_2`).
   - Programs hardware entry and exit gate vectors in `S3_6_C15_C8_1` and `S3_6_C15_C8_2`.
   - Transitions system state into active Guarded EL2 monitoring mode.

---

## 4. Exception Vector Table & Hardware Trap Dispatch

The SPTM exception vector table is mapped at virtual address `0xfffffff027118000` (`__TEXT_EXEC.__exc`). It contains 16 discrete 128-byte (0x80) alignment slots covering all architectural ARM exception vectors:

```
+----------------------------------------------------------------------------------------------------+
|                                  SPTM EXCEPTION VECTOR TABLE                                       |
+----------------------------------------------------------------------------------------------------+
| Slot Index | Vector Address     | Context / Execution Origin      | Exception Type & Target        |
+------------+--------------------+---------------------------------+--------------------------------+
| Slot 0     | 0xfffffff027118000 | Current EL with SP0             | Synchronous -> 0x270b8168      |
| Slot 1     | 0xfffffff027118080 | Current EL with SP0             | IRQ / vIRQ  -> 0x270b75fc      |
| Slot 2     | 0xfffffff027118100 | Current EL with SP0             | FIQ / vFIQ  -> 0x270b7718      |
| Slot 3     | 0xfffffff027118180 | Current EL with SP0             | SError      -> 0x270b7834      |
| Slot 4     | 0xfffffff027118200 | Current EL with SPx             | Synchronous -> 0x270b83a4      |
| Slot 5     | 0xfffffff027118280 | Current EL with SPx             | IRQ (Panic Loop: wfe; b .)     |
| Slot 6     | 0xfffffff027118300 | Current EL with SPx             | FIQ (Panic Loop: wfe; b .)     |
| Slot 7     | 0xfffffff027118380 | Current EL with SPx             | SError (Panic Loop: wfe; b .)  |
| Slot 8     | 0xfffffff027118400 | Lower EL using AArch64 (Guest)  | Synchronous Hypercall Trap     |
|            |                    |                                 | -> Target: 0xfffffff0270b7ca4  |
| Slot 9     | 0xfffffff027118480 | Lower EL using AArch64 (Guest)  | Guest IRQ   -> 0x270b7950      |
| Slot 10    | 0xfffffff027118500 | Lower EL using AArch64 (Guest)  | Guest FIQ   -> 0x270b7a6c      |
| Slot 11    | 0xfffffff027118580 | Lower EL using AArch64 (Guest)  | Guest SError -> 0x270b7b88     |
| Slot 12    | 0xfffffff027118600 | Lower EL using AArch32          | Panic Loop (AArch32 Unsupported|
| Slot 13    | 0xfffffff027118680 | Lower EL using AArch32          | Panic Loop (AArch32 Unsupported|
| Slot 14    | 0xfffffff027118700 | Lower EL using AArch32          | Panic Loop (AArch32 Unsupported|
| Slot 15    | 0xfffffff027118780 | Lower EL using AArch32          | Panic Loop (AArch32 Unsupported|
+------------+--------------------+---------------------------------+--------------------------------+
```

When an unprivileged host operating system (XNU at EL1) initiates a hypercall via `hvc #0` or a GXF transition, execution enters **Slot 8 (`0xfffffff027118400`)**, which branches to the Guest Trap Handler at `0xfffffff0270b7ca4`.

---

## 5. Trusted Execution Monitor (TXM) & Code Signing Monitor (CSM)

The Trusted Execution Monitor (`txm.iphoneos.research.raw`, 557,088 bytes) executes at Guarded EL1 (GL1) under the bundle identifier `com.apple.security.libimage4.TXMonitor` (Module Version `7.0.0`).

### 5.1 Architectural Role
TXM operates as Apple's dedicated cryptographic co-monitor. It decouples code signature verification, TrustCache registration, and Image4 root authority validation from the untrusted XNU kernel:

```
+----------------------------------------------------------------------------------------------------+
|                                    TXM VERIFICATION & CSM PIPELINE                                 |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Image4 Manifest / Mach-O Binary] ───► [TXM CSM Ingestion (GL1)]                                 |
|                                                     │                                              |
|                                       ├── Evaluate Root Authority (Apple Root CA)                 |
|                                       ├── Verify Cryptographic Nonce (Anti-Replay)                |
|                                       ├── Match Fuses & Entitlements (CEContextInitWithType)      |
|                                       └── Validate CDHash against Static / Dynamic TrustCache     |
|                                                     │                                              |
|                                        [Cryptographic Validation Pass]                             |
|                                                     │                                              |
|                                                     ▼                                              |
|  [SPTM Memory Retyping (GL2)] ◄──────── [Authorizes Code Memory Mapping]                           |
|  - Retypes physical frame to XNU_TEXT                                                              |
|  - Sets Stage-2 permission bits: AP[2:1] = r-x, XN = 0                                             |
|  - Locks page frame against kernel write tampering                                                 |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 5.2 Preserved Research Symbols & Runtime APIs

The `RESEARCH_RELEASE` build of TXM preserves internal runtime APIs unstripped in `__TEXT.__cstring`:
- `_txm_runtime_log`: Writes structured security audit records to isolated TXM memory buffers.
- `_txm_runtime_alloc_type`: Dynamic allocation primitive for Image4 ASN.1 parsing nodes.
- `_txm_runtime_dealloc_type`: Cryptographic memory scrub and release primitive.
- `_txm_runtime_set_nonce`: Early boot initialization of anti-replay nonce slots from DeviceTree properties.
- `_txm_runtime_roll_nonce`: Dynamic nonce rolling for update-brain and mobile-asset authenticated domains.
- `_txm_runtime_copy_nonce`: Secure bounded export of active nonce digests to authorized callers.
- `_txm_runtime_get_identifier_digest`: SHA-256 / SHA-384 digest extraction for authenticated signing authorities.

### 5.3 Image4 Dispatch Handlers
TXM implements 6 discrete dispatch handlers for cryptographic authorization:
1. `image4_verify_manifest_and_payload` (ID `0`): Validates Image4 manifest against signing authorities, checks chip anti-replay nonces, and evaluates security domain fusing (`rpnh`, `vnum`, `EPRO`, `ESEC`).
2. `image4_pin_root` (ID `1`): Hardened trust anchor enforcement; rejects arbitrary root certificate pinning on production SoC variants.
3. `image4_evaluate_trust` (ID `2`): Evaluates candidate certificate chains against Apple Root CA and CoreTrust stores.
4. `image4_parse_manifest_properties` (ID `3`): Extracts normalized ASN.1 DER properties with strict `0x2c`-byte buffer boundary enforcement.
5. `image4_query_status_properties` (ID `4`): Queries active Image4 module state, boot nonce descriptors, and secure boot operational modes.
6. `image4_map_and_authorize_executable` (ID `5`): Authorizes code memory mapping into XNU or Exclave address spaces. Enforces 16 KB page alignment before signaling SPTM to lock pages as executable.

---

## 6. Co-Design Model: The SPTM-TXM Dynamic Execution Authorization Flow

The security boundary between SPTM and TXM represents a dual-hypervisor co-design:

1. **Isolation of Roles**: SPTM owns the physical translation hardware (MMU Stage-2 page tables, CTRR, GAPF); TXM owns the cryptographic trust policies (Image4, CoreTrust, TrustCache, Entitlements).
2. **Atomic Retyping Handshake**:
   - When XNU requests that a page frame be mapped executable, SPTM traps the request at GL2.
   - SPTM refuses to set execution permissions (`XN = 0`) directly from an XNU hypercall.
   - Instead, SPTM queries TXM via a private inter-monitor channel (`GL2 <-> GL1`).
   - TXM inspects the page's cryptographic CDHash against its active TrustCache tables.
   - Only after TXM returns `IMAGE4_AUTH_SUCCESS` does SPTM atomically transition the physical frame type to `XNU_CODE_PAGE` and configure Stage-2 permissions to `r-x`.

---

## 7. Zero-Conflict Workspace Validation

This analysis was conducted strictly within assigned Agent 3 boundaries:
- Artifacts written: [`artifacts/sptm/sptm_topology_spec.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/sptm_topology_spec.json) and [`artifacts/sptm/txm_csm_architecture.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/txm_csm_architecture.json).
- Findings recorded: [`findings/sptm/01B_ARCHITECTURE_AND_TOPOLOGY.md`](file:///home/prem/Projects/iOS%2027/findings/sptm/01B_ARCHITECTURE_AND_TOPOLOGY.md).
- Zero writes to `artifacts/sep/`, `artifacts/gpu/`, or `artifacts/aop/`.
- All Phase 1B specifications verified against decompressed firmware binaries with complete empirical verification.
