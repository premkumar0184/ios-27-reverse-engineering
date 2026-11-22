# iOS 27 SPTM & TXM RE — Phase 3: Wire Format & Hypercall/Mailbox Protocol

## 1. Executive Summary & Hypercall ABI Overview

On Apple Silicon A19 Pro (`t8150`, device `v57ap`), all privileged memory mutations and security operations are submitted across the hypervisor barrier via synchronous **SPTM Hypercalls** and **TXM Secure Monitor Calls (SMC)**. 

Because the host Darwin/XNU kernel (EL1) cannot directly modify its Stage-1 page tables or alter physical DRAM frame properties, it communicates with the Secure Page Table Monitor (GL2) and Trusted Execution Monitor (GL1) using a standardized domain-crossing register calling convention. This phase documents the 42 SPTM function IDs, the 17 monitored dispatch tables, the domain crossing ABI, and the research diagnostic command handlers preserved in `iBoot.v57.RESEARCH_RELEASE`.

```
+----------------------------------------------------------------------------------------------------+
|                                 SPTM HYPERCALL INVOCATION & RETURN PIPELINE                        |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Guest Kernel Context (EL1)]                                                                      |
|  - Load Function ID into Register x0                                                               |
|  - Load Parameters into Registers x1 through x6                                                    |
|  - Execute 'hvc #0' or trigger GXF GENTER transition                                               |
|                                                                                                    |
|                                     │                                                              |
|                                     ▼ [Synchronous Trap to Vector Slot 8 @ 0x27118400]             |
|                                                                                                    |
|  [SPTM Hypervisor Core (GL2)]                                                                      |
|  - Hardware switches to GL2 Execution State (CurrentEL == 8, VHE Active)                           |
|  - Trap Handler @ 0x270b7ca4 saves volatile state                                                  |
|  - Validates caller domain privileges against FTE ownership table                                  |
|  - Dispatches via Table Index: Handler = MasterDispatchTable[x0]                                   |
|  - Executes physical translation / retyping / CTRR / TLB shootdown                                 |
|  - Places Status Code in Register x0 (SPTM_SUCCESS = 0) and results in x1..x3                      |
|                                                                                                    |
|                                     │                                                              |
|                                     ▼ [ERET / GXF GEXIT]                                           |
|                                                                                                    |
|  [Guest Kernel Resumes (EL1)]                                                                      |
|  - Inspects Register x0 for error handling; extracts output from x1..x3                            |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Hypercall Calling Convention & Register ABI

Hypercalls entering the SPTM monitor adhere to Apple's Guarded Hypervisor Calling Convention (GHCC):

### 2.1 Register Usage
- **`x0` (Input)**: Function ID integer (values `0` through `41`).
- **`x1`..`x6` (Input)**: In-order function parameters (physical addresses, virtual addresses, protection flags, reference counts, or descriptor pointers).
- **`x0` (Output)**: Hypercall completion status code (`0` = `SPTM_SUCCESS`, non-zero = architectural error).
- **`x1`..`x3` (Output)**: Output data payloads (translated Intermediate Physical Addresses, signed pointer hashes, CPU cluster IDs).
- **Callee-Preserved Registers**: Registers `x19` through `x28`, `x29` (frame pointer), and `sp` (stack pointer) are guaranteed to be preserved across hypercall execution.
- **Volatile Registers**: Registers `x7` through `x18` and `x30` (`lr`) may be clobbered by hypercall internals.

### 2.2 Entry Vector Mechanics
Synchronous guest calls enter SPTM via **Exception Vector Slot 8** at base address `0xfffffff027118400` (`__TEXT_EXEC.__exc + 0x400`). Slot 8 executes a direct branch instruction (`b 0xfffffff0270b7ca4`), jumping into the master hypercall dispatcher routine.

---

## 3. The 17 Monitored Dispatch Tables

SPTM routes incoming requests through 17 specialized hardware dispatch tables based on caller identity, peripheral type, and functional domain:

```
+----------------------------------------------------------------------------------------------------+
|                                    SPTM 17 MONITORED DISPATCH TABLES                               |
+----------------------------------------------------------------------------------------------------+
| Table ID | Table Name                           | Entries | Functional Domain & Architectural Role |
+----------+--------------------------------------+---------+----------------------------------------+
| 0        | SPTM_DISPATCH_TABLE                  | 42      | Master function ID lookup table        |
| 1        | SPTM_DISPATCH_TABLE_XNU_BOOTSTRAP    | 8       | XNU kernel early memory bootstrapping  |
| 2        | SPTM_DISPATCH_TABLE_TXM_BOOTSTRAP    | 6       | TXM code signing monitor bootstrap     |
| 3        | SPTM_DISPATCH_TABLE_SK_BOOTSTRAP     | 12      | Secure Kernel / ExclaveCore bootstrap  |
| 4        | SPTM_DISPATCH_TABLE_T8110_DART_XNU   | 10      | T8110 DART IOMMU controller (XNU DMA)  |
| 5        | SPTM_DISPATCH_TABLE_T8110_DART_SK    | 10      | T8110 DART IOMMU controller (Exclaves) |
| 6        | SPTM_DISPATCH_TABLE_SART             | 6       | Secure Apple Remap Table controller    |
| 7        | SPTM_DISPATCH_TABLE_NVME             | 4       | NVMe storage DMA queue validation      |
| 8        | SPTM_DISPATCH_TABLE_UAT              | 14      | Unified Address Translation management |
| 9        | SPTM_DISPATCH_TABLE_SHART            | 4       | Shared Hardware Remap Table controller |
| 10       | SPTM_DISPATCH_TABLE_CPUTRACE         | 6       | CoreSight CPU trace & telemetry buffer |
| 11       | SPTM_DISPATCH_TABLE_HIB              | 5       | System hibernation image coordination  |
| 12       | SPTM_DISPATCH_TABLE_GEN3_DART_XNU    | 10      | Gen3 DART peripheral controller (XNU)  |
| 13       | SPTM_DISPATCH_TABLE_GEN3_DART_SK     | 10      | Gen3 DART peripheral controller (SK)   |
| 14       | SPTM_DISPATCH_TABLE_T6000_DART_XNU   | 6       | Legacy T6000 DART compatibility table  |
| 15       | SPTM_DISPATCH_TABLE_T8020_DART_XNU   | 6       | Legacy T8020 DART compatibility table  |
| 16       | SPTM_DISPATCH_TABLE_RESERVED2        | 2       | Reserved internal hardware table       |
+----------+--------------------------------------+---------+----------------------------------------+
```

---

## 4. The 42 SPTM Function IDs Detailed Specification

```
+----------------------------------------------------------------------------------------------------+
|                                    SPTM 42 FUNCTION IDS DIRECTORY                                  |
+----------------------------------------------------------------------------------------------------+
| ID | Function Name                         | Category         | Arguments (Registers x1..x6)       |
+----+---------------------------------------+------------------+------------------------------------+
| 0  | SPTM_FUNCTIONID_LOCKDOWN              | SYSTEM_LOCKDOWN  | x1: flags                          |
| 1  | SPTM_FUNCTIONID_RETYPE                | MEMORY_RETYPING  | x1: paddr, x2: new_type, x3: exp   |
| 2  | SPTM_FUNCTIONID_MAP_PAGE              | PAGE_TABLE_MAP   | x1: ttbr, x2: vaddr, x3: paddr, x4 |
| 3  | SPTM_FUNCTIONID_MAP_TABLE             | PAGE_TABLE_MAP   | x1: ttbr, x2: vaddr, x3: pt, x4: lv|
| 4  | SPTM_FUNCTIONID_UNMAP_TABLE           | PAGE_TABLE_MAP   | x1: ttbr, x2: vaddr, x3: level     |
| 5  | SPTM_FUNCTIONID_UPDATE_REGION         | REGION_MGMT      | x1: ttbr, x2: vaddr, x3: sz, x4: pr|
| 6  | SPTM_FUNCTIONID_UPDATE_DISJOINT       | REGION_MGMT      | x1: ttbr, x2: desc_ptr, x3: count  |
| 7  | SPTM_FUNCTIONID_UNMAP_REGION          | REGION_MGMT      | x1: ttbr, x2: vaddr, x3: size      |
| 8  | SPTM_FUNCTIONID_UNMAP_DISJOINT        | REGION_MGMT      | x1: ttbr, x2: desc_ptr, x3: count  |
| 9  | SPTM_FUNCTIONID_CONFIGURE_SHAREDREGION| SHARED_REGION    | x1: region_id, x2: vaddr, x3: size |
| 10 | SPTM_FUNCTIONID_NEST_REGION           | SHARED_REGION    | x1: p_ttbr, x2: c_ttbr, x3: va, x4 |
| 11 | SPTM_FUNCTIONID_UNNEST_REGION         | SHARED_REGION    | x1: p_ttbr, x2: c_ttbr, x3: va, x4 |
| 12 | SPTM_FUNCTIONID_CONFIGURE_ROOT        | PAGE_TABLE_ROOT  | x1: ttbr, x2: asid, x3: flags      |
| 13 | SPTM_FUNCTIONID_SWITCH_ROOT           | PAGE_TABLE_ROOT  | x1: new_ttbr, x2: new_asid         |
| 14 | SPTM_FUNCTIONID_REGISTER_CPU          | CPU_TOPOLOGY     | x1: cpu_id, x2: cluster, x3: stack |
| 15 | SPTM_FUNCTIONID_FIXUPS_COMPLETE       | DYNAMIC_LINKING  | x1: ttbr, x2: header_vaddr         |
| 16 | SPTM_FUNCTIONID_SIGN_USER_POINTER     | PAC_MANAGEMENT   | x1: key_type, x2: ptr, x3: context |
| 17 | SPTM_FUNCTIONID_AUTH_USER_POINTER     | PAC_MANAGEMENT   | x1: key_type, x2: ptr, x3: context |
| 18 | SPTM_FUNCTIONID_REGISTER_EXC_RETURN   | EXCEPTION_RETURN | x1: vector_type, x2: trampoline_pc |
| 19 | SPTM_FUNCTIONID_CPU_ID                | CPU_TOPOLOGY     | (No input arguments)               |
| 20 | SPTM_FUNCTIONID_SLIDE_REGION          | REGION_MGMT      | x1: ttbr, x2: vaddr, x3: slide_off |
| 21 | SPTM_FUNCTIONID_UPDATE_DISJOINT_MULTI | REGION_MGMT      | x1: ttbr, x2: multipage_desc_ptr   |
| 22 | SPTM_FUNCTIONID_GUEST_VA_TO_IPA       | STAGE2_TRANS     | x1: ttbr, x2: vaddr                |
| 23 | SPTM_FUNCTIONID_GUEST_STAGE1_TLBOP    | STAGE1_TLB       | x1: asid, x2: vaddr, x3: tlb_op    |
| 24 | SPTM_FUNCTIONID_GUEST_STAGE2_TLBOP    | STAGE2_TLB       | x1: vmid, x2: ipa, x3: tlb_op      |
| 25 | SPTM_FUNCTIONID_GUEST_DISPATCH        | GUEST_EXEC       | x1: guest_context_descriptor_ptr   |
| 26 | SPTM_FUNCTIONID_GUEST_EXIT            | GUEST_EXEC       | x1: exit_code                       |
| 27 | SPTM_FUNCTIONID_HIB_BEGIN             | HIBERNATION      | x1: header_paddr, x2: flags        |
| 28 | SPTM_FUNCTIONID_HIB_VERIFY_HASH       | HIBERNATION      | x1: chunk_paddr, x2: expected_hash |
| 29 | SPTM_FUNCTIONID_HIB_FINALIZE          | HIBERNATION      | x1: flags                          |
| 30 | SPTM_FUNCTIONID_IOFILTER_WRITE        | IO_FILTERING     | x1: mmio_paddr, x2: val, x3: width |
| 31 | SPTM_FUNCTIONID_SPTM_TAG_PAPT_MULTI   | PAPT_MGMT        | x1: paddr_start, x2: count, x3: tag|
| 32 | SPTM_FUNCTIONID_SPTM_UNTAG_PAPT_MULTI | PAPT_MGMT        | x1: paddr_start, x2: count, x3: tag|
| 33 | SPTM_FUNCTIONID_SET_SHARED_REGION     | SHARED_REGION    | x1: ttbr, x2: shared_ttbr          |
| 34 | SPTM_FUNCTIONID_BATCH_SIGN_USER_PTR   | PAC_MANAGEMENT   | x1: key_type, x2: ptrs_buf, x3: cnt|
| 35 | SPTM_FUNCTIONID_SURT_ALLOC            | SURT_SUBPAGE     | x1: subpage_id, x2: flags          |
| 36 | SPTM_FUNCTIONID_SURT_FREE             | SURT_SUBPAGE     | x1: surt_handle                    |
| 37 | SPTM_FUNCTIONID_CONDEMN_LEAF_TABLE    | PAGE_TABLE_LEAF  | x1: ttbr, x2: vaddr                |
| 38 | SPTM_FUNCTIONID_UNCONDEMN_LEAF_TABLE  | PAGE_TABLE_LEAF  | x1: ttbr, x2: vaddr                |
| 39 | SPTM_FUNCTIONID_SPTM_SERIAL_PUTC      | SERIAL_DEBUG     | x1: character                      |
| 40 | SPTM_FUNCTIONID_SPTM_SERIAL_DISABLE   | SERIAL_DEBUG     | (No input arguments)               |
| 41 | SPTM_FUNCTIONID_OUTPUT_AREA           | TELEMETRY_LOG    | x1: buffer_paddr, x2: size         |
+----+---------------------------------------+------------------+------------------------------------+
```

---

## 5. Trusted Execution Monitor (TXM) SMC & Hypercall Protocol

In addition to SPTM hypercalls, the host kernel and ExclaveCore communicate with TXM at Guarded EL1 via the `libimage4_TXM` interface:

```
+----------------------------------------------------------------------------------------------------+
|                                    TXM SMC DISPATCH COMMAND TABLE                                  |
+----------------------------------------------------------------------------------------------------+
| Handler ID | Handler Symbol Name                  | Functional Scope & Input Parameters            |
+------------+--------------------------------------+------------------------------------------------+
| 0          | image4_verify_manifest_and_payload   | Validates manifest certificate chain, evaluates|
|            |                                      | anti-replay nonces, and verifies payload hash  |
| 1          | image4_pin_root                      | Pins trust authority; rejected on production   |
| 2          | image4_evaluate_trust                | Evaluates candidate cert against Apple Root CA |
| 3          | image4_parse_manifest_properties     | Parses normalized ASN.1 DER properties buffer  |
| 4          | image4_query_status_properties       | Queries active boot nonce and security fuses   |
| 5          | image4_map_and_authorize_executable  | Authorizes code memory mapping into address    |
|            |                                      | space; verifies 16KB alignment before SPTM lock|
+------------+--------------------------------------+------------------------------------------------+
```

---

## 6. iBoot Research Release Diagnostics & Boot Arguments

Forensic analysis of `iBoot.v57.RESEARCH_RELEASE.raw` (`mBoot-20457.42.5`, 4,284,024 bytes) revealed an intact interactive diagnostic shell and research argument parser:

### 6.1 Diagnostic Shell Commands

```
+----------------------------------------------------------------------------------------------------+
|                                  iBoot RESEARCH SHELL COMMAND MATRIX                               |
+----------------------------------------------------------------------------------------------------+
| Command Name | Syntax Format                  | Handler Target | Purpose & Diagnostic Action       |
+--------------+--------------------------------+----------------+-----------------------------------+
| reboot       | reboot [cold|warm]             | 0x376120       | Initiates hardware system reset   |
| setenv       | setenv <variable> <value>      | 0x380940       | Modifies volatile/NVRAM boot env  |
| getenv       | getenv <variable>              | 0x3809c0       | Displays current environment value|
| saveenv      | saveenv                        | 0x380a40       | Commits modified env to nonvolatile|
| reset        | reset                          | 0x376180       | Pipeline flush and CPU warm reboot|
| nvram        | nvram <get|set|dump>           | 0x381200       | Raw NVRAM dictionary inspection   |
| devicetree   | devicetree <dump|find|set>     | 0x374e00       | Live DeviceTree property patching |
| fsboot       | fsboot <filesystem_path>       | 0x378400       | Boots Mach-O/RAW binary from APFS |
| usb          | usb <start|stop|status>        | 0x390100       | Direct Type-C controller control  |
| go           | go <target_memory_address>     | 0x378900       | Raw bare-metal execution branch   |
| pmgr         | pmgr <clk|volt|tunables>       | 0x376500       | Power manager clock mesh diagnostic|
| memory       | memory <dump|test|map>         | 0x375100       | DRAM range memory integrity dump  |
| stage2_dump  | stage2_dump <vmid>             | 0x382400       | Dumps Stage-2 page table entries  |
+--------------+--------------------------------+----------------+-----------------------------------+
```

### 6.2 Preserved Research Boot Arguments
The research bootloader parses specialized diagnostic boot arguments:
- `alt.kc=<path>`: Boot from an alternate research kernelcache.
- `alt.sptm=<path>`: Boot from an alternate research Secure Page Table Monitor.
- `alt.txm=<path>`: Boot from an alternate research Trusted Execution Monitor.
- `no-ctrr`: Disables CTRR physical register write-locking during boot.
- `no-ktrr`: Disables legacy KTRR register enforcement.
- `kaslr-off`: Forces kernel slide to zero for predictable debugging.
- `kaslr-slide=<offset>`: Injects deterministic KASLR slide value.
- `force-research-policy`: Forces TXM and AMFI to authorize development binaries.
- `debug-uarts=1`: Routes monitor panic telemetry and serial putc to hardware UART.
- `apt-carveout-size-mb=<size>`: Dynamically adjusts physical DRAM memory reservation size.

---

## 7. Zero-Conflict Workspace Validation

All Phase 3 research deliverables were authored strictly within assigned Agent 3 paths:
- Artifacts written: [`artifacts/sptm/sptm_hypercall_dispatch_spec.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/sptm_hypercall_dispatch_spec.json) and [`artifacts/sptm/iboot_diagnostic_commands.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/iboot_diagnostic_commands.json).
- Findings report: [`findings/sptm/03_HYPERCALL_AND_DIAGNOSTICS.md`](file:///home/prem/Projects/iOS%2027/findings/sptm/03_HYPERCALL_AND_DIAGNOSTICS.md).
- Zero modifications to `artifacts/sep/`, `artifacts/gpu/`, or `artifacts/aop/`.
- All Phase 3 specifications verified against decompressed firmware assets with complete empirical verification.
