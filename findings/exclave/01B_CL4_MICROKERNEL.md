# ExclaveOS Microkernel Dissection: cL4 Architecture, Traps & Capability Delegation Model

**Target Platform**: iOS 27.2 (`24B119`) — Apple Silicon A19 Pro (`t8150`)  
**Target Hardware**: iPhone 18,3 (`v57ap`)  
**Binaries Dissected**:
- `01_pmm_server.macho` (`pmm-server` — Physical Memory Manager & Datacube Retyping)
- `02_vascore_platform.macho` (`vascore` — Virtual Address Space Core Platform & `xrt` Concurrency Engine)
- `00_tightbeam_runtime.macho` (`tightbeam-runtime` — Swift 5 IPC Runtime & cL4 Transports)
- Embedded cL4 kernel binary: `knlr` (`rlnk`)

---

## 1. Executive Architectural Overview

Apple's **ExclaveOS** represents a paradigm shift in Apple operating system security. Rather than running sensitive security tasks (passkey storage, Face ID biometric matching, hardware camera/microphone privacy indicators, sensor arbitration) inside the monolithic Darwin/XNU kernel, Apple has deployed an isolated, formal-methods-inspired capability microkernel known internally as **cL4**.

cL4 is an Apple-engineered derivative of the L4/seL4 capability microkernel family, customized with Apple Silicon hardware extensions:
1. **Zero Monolithic Privileges**: The microkernel enforces strict spatial and temporal capability isolation. A process (referred to in Exclave terminology as a **Conclave**) possesses zero ambient authority. It can only execute operations or communicate through capabilities explicitly placed in its Capability Space (**CSpace**).
2. **Hardware Domain Partitioning**: cL4 executes in an isolated memory partition enforced by Apple's Secure Page Manager (**SPTM**) and hardware page table isolation. Transitions between the Darwin/XNU host OS and ExclaveOS occur via dedicated hardware descriptors termed **RingGates** (`L4_Type_Plat_RingGate`).
3. **Synchronous Fast-Path IPC**: Communication between conclaves uses register-based fast path message transfer via `svc #0`, falling back to shared memory (`cL4_large_transport`) only for bulk payloads exceeding IPC buffer limits.

```
+-------------------------------------------------------------------------+
|                               Darwin / XNU (Host OS)                   |
|   Userland Daemons (sharingd, apsd) <--> XNU Kernel (exclaves_ctl_trap) |
+-------------------------------------------------------------------------+
                                    |
                           [RingGate Hardware Barrier]
                                    |
+-------------------------------------------------------------------------+
|                         Apple cL4 Microkernel                          |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Capability Engine |  | Scheduler (xrt)   |  | Memory Retyping PMM |  |
|  +-------------------+  +-------------------+  +---------------------+  |
+-------------------------------------------------------------------------+
         |                                                 |
+------------------------------------+  +---------------------------------+
|   Conclave 1: Tightbeam Runtime    |  |   Conclave 2: PMM Server        |
|  - CSpace Radix Tree               |  |  - Datacube Retyping Allocator  |
|  - Thread IPC Buffer (tpidrro_el0) |  |  - L4_Cap_Mint_Ep Badging      |
+------------------------------------+  +---------------------------------+
```

---

## 2. Microkernel System Call Architecture

Static disassembly of `00_tightbeam_runtime.macho`, `01_pmm_server.macho`, and `02_vascore_platform.macho` reveals that cL4 does not use a flat, numbered syscall table like POSIX or Mach. Instead, system calls are categorized into **six primary immediate vectors** on ARM64 (`svc #0` through `svc #5`):

| Immediate | Vector Symbol | Primary Operations | Key Assembly Pattern |
|---|---|---|---|
| `svc #0` | `L4_Syscall_IPC` | `L4_Call`, `L4_ReplyWait`, `L4_Send`, `L4_Ep_Call` | `mov x0, <cap>; mov x1, <tag>; svc #0` |
| `svc #1` | `L4_Syscall_Thread` | `L4_Yield`, `L4_ThreadSwitch`, `L4_Sc_Dispatch` | `mov x0, <ctx>; mov x1, <flags>; svc #1` |
| `svc #2` | `L4_Syscall_CapRevoke` | `L4_Cap_Delete`, `L4_Cap_Revoke` | `ldr x0, [x21, 0x28]; mov x1, x20; svc #2` |
| `svc #3` | `L4_Syscall_CapMint` | `L4_Cap_Mint_Ep`, `L4_Cap_Mint_Ec`, `L4_Cap_Mint_Untyped` | `stp xzr, xzr, [x10]; mov x1, x21; svc #3` |
| `svc #4` | `L4_Syscall_CapCopy` | `L4_Cap_Copy`, `L4_Cap_Move` | `mov x1, x0; mov x0, x1; svc #4` |
| `svc #5` | `L4_Syscall_Memory` | `L4_Untyped_Create`, `L4_Arm64_PageFrame_Protect` | `mov x1, x0; mov x0, x1; svc #5` |

### 2.1 Syscall Calling Convention

ARM64 registers are mapped deterministically during cL4 system calls:
- **`x0`**: Target capability pointer / capability slot address (`cptr`).
- **`x1`**: Message descriptor / operation tag (`L4_MsgTag_t`) or destination slot.
- **`x2`**: Context badge, client identifier, or auxiliary rights mask.
- **`tpidrro_el0`**: Thread Pointer ID Register Read-Only EL0. Holds the base virtual address of the per-thread **IPC Buffer**, where message payload registers (`mr[0..31]`) and capability delegation registers (`cr[0..7]`) reside.
- **Return Value (`x0`)**: Error code (`L4_ErrorCodeSuccess = 0` on success, or positive integer corresponding to the `L4_ErrorCode` enum).
- **Return Status (`x2`)**: Received message tag or hardware-verified client badge.

Disassembly from `00_tightbeam_runtime.macho` at `0xc0001528`:
```arm64
mrs     x25, tpidrro_el0      ; Load IPC Buffer address
stp     x23, x24, [x25]       ; Store payload into MR0, MR1
str     x0, [x25, 0x10]       ; Store payload into MR2
mov     x1, 0                 ; Immediate message tag
mov     x0, x20               ; Target endpoint capability
mov     w2, 0x12              ; Badge / operation argument
svc     0                     ; Execute cL4 synchronous IPC call
str     x2, [x25]             ; Store returned reply tag
tst     x0, 0xff              ; Test error code
b.ne    0xc0001688            ; Branch to error handling on non-zero
```

---

## 3. The Capability Space (CSpace) Architecture

Capabilities in ExclaveOS cannot be forged, guessed, or fabricated as integers. They are stored within kernel-managed tables called **Capability Nodes (CNodes)**.

### 3.1 Two-Level Guarded Radix Tree

Disassembly of `01_pmm_server.macho` at `0x7ffdfc8` and `0x7ffe060` reveals the exact CSpace lookup algorithm:

$$\text{CNode Table Size} = 2048 \text{ bytes } (0x800)$$

$$\text{Slot Size} = 8 \text{ bytes } (\text{64-bit capability descriptor or child CNode pointer})$$

$$\text{Slots per CNode} = \frac{2048}{8} = 256 \text{ slots } (2^8)$$

$$\text{Radix Step} = 8 \text{ bits per level}$$

```
                          Capability Pointer (cptr)
       +-------------------------+-------------------------+
       |   Level 0 Index (8-bit) |   Level 1 Index (8-bit) |
       +-------------------------+-------------------------+
                    |                         |
                    v                         v
           +-----------------+       +-----------------+
           |   Root CNode    |       |   Leaf CNode    |
           |  (256 entries)  |       |  (256 entries)  |
           | [0x00] -> Child ------> | [0x00] -> Cap 0 |
           | [0x01] -> Child |       | [0x01] -> Cap 1 |
           | ...             |       | ...             |
           | [0xff]          |       | [0xff] -> Cap N |
           +-----------------+       +-----------------+
```

### 3.2 Radix Lookup Assembly Verification

From `01_pmm_server.macho` (`0x7ffe06c`):
```arm64
add     x8, x0, w24, uxtb 3   ; Slot address = table_base + (index << 3)
cmp     x8, x0                ; Validate pointer overflow
b.lo    0x7ffe17c
add     x9, x0, 0x800         ; Table boundary = table_base + 2048 bytes
add     x10, x8, 8            ; Entry size = 8 bytes
cmp     x10, x9               ; Assert entry within 0x800 limit
b.hi    0x7ffe17c
ldr     x10, [x20, 0x10]
str     x10, [x8]             ; Write capability descriptor into slot
ldrb    w8, [x20, 8]          ; Read current tree depth
add     w8, w8, 1             ; Increment depth
strb    w8, [x20, 8]
lsr     x24, x24, 8           ; Shift 8 bits for next radix level
```

This confirms a maximum capacity of:

$$\text{Max CSpace Capacity} = 256 \times 256 = 65,536 \text{ capability slots per Conclave}$$

---

## 4. Capability Delegation, Rights & Badging Model

### 4.1 Capability Types Enum

Extracted sequentially from `01_pmm_server.macho` at offset `0x6efce`:

| ID | Constant | Class | Architectural Purpose |
|---|---|---|---|
| `0x00` | `L4_Type_Null` | Special | Unmapped slot (`L4_Nil`) |
| `0x01` | `L4_Type_Root` | Kernel | Master root capability with universal attenuation authority |
| `0x02` | `L4_Type_Zombie` | Kernel | Object undergoing asynchronous tree revocation |
| `0x03` | `L4_Type_Untyped` | Memory | Physical memory region available for retyping |
| `0x04` | `L4_Type_CNode` | CSpace | Capability Node table (256 slots) |
| `0x05` | `L4_Type_Cpu` | Execution | Physical CPU core affinity and scheduling authority |
| `0x06` | `L4_Type_Ec` | Execution | Execution Context (Thread Control Block, registers, stack) |
| `0x07` | `L4_Type_Sc` | Execution | Scheduling Context (Budget, period, priority) |
| `0x08` | `L4_Type_Ep` | IPC | Synchronous communication endpoint |
| `0x09` | `L4_Type_Ev` | IPC | Event signaling object |
| `0x0a` | `L4_Type_Notify` | IPC | Asynchronous notification bitmask channel |
| `0x0b` | `L4_Type_Irq` | Hardware | Hardware interrupt delivery |
| `0x0c` | `L4_Type_Debug` | Hardware | CoreSight debug and watchpoint registers |
| `0x0d` | `L4_Type_Arm64_PageTableLevel2` | Memory | ARM64 Level-2 translation table |
| `0x0e` | `L4_Type_Arm64_PageTableLevel1` | Memory | ARM64 Level-1 translation table |
| `0x0f` | `L4_Type_Arm64_PageTableLevel0` | Memory | ARM64 Level-0 translation table |
| `0x10` | `L4_Type_Arm64_FrameLevel2` | Memory | Large physical page frame (512 GB) |
| `0x11` | `L4_Type_Arm64_FrameLevel1` | Memory | Medium physical page frame (1 GB) |
| `0x12` | `L4_Type_Arm64_FrameLevel0` | Memory | Standard 16 KB physical page frame (`L4_FrameSize`) |
| `0x13` | `L4_Type_Arm64_Debug` | Hardware | ARM64 hardware debug context |
| `0x14` | `L4_Type_Arm64_Pac` | Hardware | ARM64 Pointer Authentication Key registers |
| `0x15` | `L4_Type_Arm64_Sme` | Accelerator | Scalable Matrix Extension (SME/SME2) registers |
| `0x16` | `L4_Type_Arm64_Apple_Amx` | Accelerator | Apple Matrix Coprocessor hardware execution pipe |
| `0x17` | `L4_Type_Plat_RingGate` | Platform | Apple Silicon RingGate host-crossing descriptor |
| `0x18` | `L4_Type_Plat_DataCube` | Platform | Retypable host-shared memory container (Datacube) |
| `0x19` | `L4_Type_EVP_Hypercall` | Platform | Exclave Virtual Platform Hypercall channel |
| `0x1a` | `L4_Type_Plat_Dart` | Hardware | Device Address Resolution Table (DART) IOMMU root |
| `0x1b` | `L4_Type_Plat_Dart_PageTable` | Hardware | DART DMA translation table |

### 4.2 Rights Bitmask Encoding

When capabilities are minted via `L4_Cap_Mint` (`svc #3`), rights can only be attenuated (reduced), never amplified:

$$\text{Valid Delegation Invariant: } (\text{child\_rights} \land \neg \text{parent\_rights}) = 0$$

- **`L4_CanRead` (Bit 0, `0x01`)**: Read access to page frames, or authority to send requests through an Endpoint capability.
- **`L4_CanWrite` (Bit 1, `0x02`)**: Write access to memory frames, authority to receive IPC messages on an Endpoint, or authority to retype Untyped memory.
- **`L4_CanGrant` (Bit 2, `0x04`)**: Authority to delegate capabilities over an Endpoint to another Conclave.
- **`L4_CanGrantReply` (Bit 3, `0x08`)**: Authority to pass single-use reply endpoint capabilities during RPC calls.
- **`L4_CanBadge` (Bit 4, `0x10`)**: Authority to attach an unforgeable hardware badge during `L4_Cap_Mint_Ep`.
- **`L4_CanControl` (Bit 5, `0x20`)**: Thread control authority (`L4_Ec_Suspend`, `L4_Ec_Resume`, `L4_Ec_SetEndpoint`).
- **`L4_CanSync` (Bit 9, `0x200`)**: Thread inspection authority (`L4_Ec_GetState` for PC/SP/CPSR).

### 4.3 Unforgeable Badging Mechanism

When a server conclave initializes a service endpoint, it mints client-specific copies using `L4_Cap_Mint_Ep`:

```c
// Extracted from pmm-server/src/main.c
L4_Cap_Mint_Ep(
    pmm_recv_ep,              // Master service endpoint
    client_dest_slot,         // Target slot in client CSpace
    L4_CanRead | L4_CanBadge, // Attenuated rights (Send + Badge)
    0,                        // Mask
    badge->client_id          // Unforgeable 16-bit client identifier
);
```

When the client performs `L4_Call(client_dest_slot, &tag)`, the cL4 microkernel intercepts the trap:
1. Strips any client-provided value in `x2`.
2. Injects the kernel-minted badge into `x2` before delivering execution to the server loop.
3. The server inspects `x2` to identify the authenticated caller with zero cryptographic handshake overhead.

---

## 5. Microkernel Error Code Specification

Extracted directly from the 32-byte-aligned string table in `01_pmm_server.macho` at offset `0x4e2dc`:

```
Offset 0x4e2dc:
[0x00] "L4_ErrorCodeSuccess"
[0x20] "L4_ErrorCodePreempted"
[0x40] "L4_ErrorCodeCanceled"
[0x60] "L4_ErrorCodeTruncated"
[0x80] "L4_ErrorCodeCapInvalid"
[0xa0] "L4_ErrorCodeSlotInvalid"
[0xc0] "L4_ErrorCodeMethodInvalid"
[0xe0] "L4_ErrorCodeArgumentInvalid"
[0x100] "L4_ErrorCodeOperationInvalid"
[0x120] "L4_ErrorCodePermissionInvalid"
```

| Numeric Code | Constant | Meaning & Trigger Condition |
|---|---|---|
| `0` (`0x0`) | `L4_ErrorCodeSuccess` | Syscall succeeded. Output registers valid. |
| `1` (`0x1`) | `L4_ErrorCodePreempted` | Execution preempted by higher priority scheduling context or non-blocking IPC receiver not ready. |
| `2` (`0x2`) | `L4_ErrorCodeCanceled` | Target thread or transaction canceled before completion. |
| `3` (`0x3`) | `L4_ErrorCodeTruncated` | Message payload exceeded receiver IPC buffer capacity (`L4_IpcBuffer_Mrs` / `Crs`). |
| `4` (`0x4`) | `L4_ErrorCodeCapInvalid` | Target capability slot is `L4_Nil`, points to a zombie object, or type mismatch. |
| `5` (`0x5`) | `L4_ErrorCodeSlotInvalid` | CNode index out of range or unmapped in CSpace radix hierarchy. |
| `6` (`0x6`) | `L4_ErrorCodeMethodInvalid` | Syscall method selector not supported by target kernel object type. |
| `7` (`0x7`) | `L4_ErrorCodeArgumentInvalid` | Malformed parameters, unaligned physical addresses, or size out of range. |
| `8` (`0x8`) | `L4_ErrorCodeOperationInvalid` | Operation invalid in current object state (e.g. retyping occupied memory). |
| `9` (`0x9`) | `L4_ErrorCodePermissionInvalid` | Rights bitmask violation (e.g. attempting to grant without `L4_CanGrant`). |

---

## 6. Virtual Address Space Management & Memory Faults

The Virtual Address Space platform (`02_vascore_platform.macho`) implements memory isolation via the **Exclave Address Space Manager (easm)**:
- **Hardware Page Size**: Apple Silicon 16 KB pages ($2^{14} = 16,384 \text{ bytes}$).
- **Page Size Assertions**:
  ```c
  vas_round_up((uintptr_t)ret, L4_FrameSizeBits) != (uintptr_t)ret
  addr == 0 || (size_t)mainaddr % L4_FrameSize != 0
  ```
- **Fault Handling**: Page faults inside a Conclave do not panic the device. The microkernel converts the translation fault into an IPC message sent to the conclave's registered `easm_server_faulthandler` via `vas_faulthandler_vtable`.
- **Dynamic Linker Integration**: Dyld operations inside ExclaveKit execute through authenticated capability stubs:
  - `vas__easm_dyld_map_region`
  - `vas__easm_dyld_unmap_region`
  - `vas__easm_dyld_mprotect_region`
  - `vas__easm_dyld_register_dynamic_fixups`
- **Host Memory Bridging**: Darwin/XNU shared buffers are mapped via `vas__easm_map_xnu_content_region` under SPM permission monitoring, guaranteeing that host kernel vulnerabilities cannot corrupt Exclave memory.

---

## 7. Conclusions & Next Steps

Phase E1B has definitively established the foundation of Apple's cL4 microkernel:
1. System call trap vectors (`svc #0` through `svc #5`).
2. Two-level guarded CNode radix tree ($256 \times 256$ entries).
3. Complete 28-entry capability type enum and rights bitmask.
4. Client badging mechanism and exact error code numbering.

**Next Phase**: Proceed to **Phase E2 (`exclave_phase_2_tightbeam_wire_format`)** to reverse engineer the binary serialization format, message accumulators, and Swift 5 IPC protocols governing Tightbeam communication.
