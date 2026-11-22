# ExclaveOS Kernel Boundary: XNU Traps, xnuproxy & Conclave Lifecycle

**Target Platform**: iOS 27.2 (`24B119`) — Apple Silicon A19 Pro (`t8150`)  
**Target Hardware**: iPhone 18,3 (`v57ap`)  
**Binaries Dissected**:
- `artifacts/kernel/kernelcache.release.raw` (Darwin / XNU Kernelcache)
- `artifacts/firmware/exclavecore_bundle_unpacked/00_tightbeam_runtime.macho` (Tightbeam Runtime)
- `artifacts/firmware/exclavecore_bundle_unpacked/03_jg_sharedmem_preload.macho` (xnuproxy components)

---

## 1. Executive Boundary Architecture

In iOS 27, the privilege boundary between the monolithic Darwin/XNU kernel and isolated ExclaveOS conclaves is strictly arbitrated. Darwin does not execute within Exclave memory, nor can an Exclave directly inspect arbitrary host DRAM. The boundary is governed by three architectural pillars:

1. **Dedicated System Call Traps**: Darwin provides three specialized entrypoints:
   - `_exclaves_ctl_trap`: Administrative control, physical Datacube memory donation, sensor arbitration.
   - `_exclaves_call_trap`: Synchronous invocation of Exclave services from userland or kernel extensions.
   - `_exclaves_boot_trap`: Bootstrap measurement and trust verification of the ExclaveCore BUND.
2. **`xnuproxy` Dispatch Engine**: Located in `xnu/osfmk/arm64/exclaves_xnuproxy.c`, this kernel subsystem handles thread scheduling across the domain boundary and dispatches asynchronous notifications via `JgXnuProxyComponents.XnuProxyNotificationServer`.
3. **SPTM Hardware Partitioning**: The Apple Silicon **Secure Page Table Monitor** (SPTM) enforces hardware Stage-2 memory fencing and synchronizes domain crossings via the **RingGate** mechanism (`sk_enter` and `xrt__plat_RingGate_Return`).

```
+-------------------------------------------------------------------------------+
|                            Darwin Userland / Daemons                          |
|         (e.g. sharingd, apsd, backboardd, CoreAudio HAL, sksd)                |
+-------------------------------------------------------------------------------+
                                        |
                          System Call Trap Interface
                                        |
+-------------------------------------------------------------------------------+
|                             Darwin / XNU Kernel                               |
|  - _exclaves_ctl_trap (Donation, Reclaim, Sensor State)                       |
|  - _exclaves_call_trap (Synchronous RPC Dispatch)                            |
|  - _exclaves_boot_trap (BUND Verification & IPL)                              |
|  - exclaves_xnuproxy.c (Thread Context & Notification Handlers)               |
|  - Per-thread IPC Buffer (ipcb_paddr: Exclaves_L4_IpcBuffer_t)                |
+-------------------------------------------------------------------------------+
                                        |
                        [RingGate Hardware Barrier: sk_enter]
                                        |
+-------------------------------------------------------------------------------+
|                            Apple cL4 Microkernel                              |
|  - Validates RingGate transition descriptor                                   |
|  - Switches MMU Stage-2 attributes to Conclave domain                         |
|  - Delivers IPC to target Endpoint (L4_Cap_Ep)                                 |
+-------------------------------------------------------------------------------+
```

---

## 2. XNU Exclave System Call Traps

Static inspection of `artifacts/kernel/kernelcache.release.raw` reveals the core syscall implementations:

### 2.1 `_exclaves_ctl_trap`
Provides administrative control over the ExclaveOS lifecycle and hardware resources:

```c
int _exclaves_ctl_trap(uint32_t operation, void *args, size_t args_size);
```

| Operation Code | Symbol | Functionality |
|---|---|---|
| `0x01` | `EXCLAVES_CTL_DONATE_PAGE` | Unmaps host DRAM pages and donates them as Datacubes to `pmm-server`. |
| `0x02` | `EXCLAVES_CTL_RECLAIM_PAGE` | Reclaims released Datacubes after ExclaveOS zero-fill scrubbing. |
| `0x03` | `EXCLAVES_CTL_GET_STATUS` | Queries ExclaveOS health, memory stats, and active Conclaves. |
| `0x04` | `EXCLAVES_CTL_SET_SENSOR_STATE` | Dispatches `_exclaves_indicator_system_state_change` to arbitrate privacy indicators. |

**Entitlement Enforcement**:
Calling `_exclaves_ctl_trap` requires either `com.apple.private.exclaves.control` or `com.apple.private.exclaves.sensor`. Calling without proper entitlements yields `EPERM` immediately before reaching the kernel handler.

### 2.2 `_exclaves_call_trap`
Enables synchronous RPC calls from Darwin into a Conclave service:

```c
int _exclaves_call_trap(
    uint64_t endpoint_token,
    const void *in_msg,
    size_t in_size,
    void *out_msg,
    size_t *out_size
);
```

**Dispatch Sequence**:
1. Copies the input Tightbeam message from userland into the thread's physical IPC buffer (`ipcb_paddr`).
2. Asserts page permissions: `exclaves_memory_pa_page_is_sk_shared_rw(trunc_page_64(ipcb_paddr))`.
3. Invokes `exclaves_run` in `exclaves_xnuproxy.c`.
4. Executes the hardware RingGate crossing primitive `sk_enter`.
5. Suspends the calling XNU thread while execution runs on the assigned CPU core inside ExclaveOS.
6. Upon Conclave completion (`xrt__plat_RingGate_Return`), execution resumes in XNU and return values are copied back to userland.

### 2.3 `_exclaves_boot_trap`
Manages early bootstrap verification:
- `exclaves_aoe_boot`: Boots the Apple Operating Environment for ExclaveCore.
- `exclaves_bootinfo`: Passes physical memory carveout tables to the SPTM.
- Verifies that `sk_enter` initializes without `RINGGATE_STATUS_ERROR`.

---

## 3. The `xnuproxy` Architecture & Notification Upcalls

The `xnuproxy` subsystem (`exclaves_xnuproxy.c`) bridges asynchronous events and scheduling between XNU and ExclaveOS:

### 3.1 Per-Thread Exclave Context (`struct exclaves_ctx`)
Each Darwin thread that interacts with Exclaves contains a pointer in its `thread_t` structure:
```c
struct exclaves_ctx {
    uint64_t                ipcb_paddr;       // Physical address of thread IPC buffer
    uint64_t                ringgate_token;   // Hardware RingGate authorization token
    struct arm_saved_state *saved_state;      // Saved ARM64 general-purpose registers
    uint64_t                active_endpoint;  // Target Conclave capability index
};
```

Verified invariant from `exclaves_xnuproxy.c`:
```c
// Asserts that the IPC buffer does not straddle a 16 KB page boundary
trunc_page_64(ipcb_paddr) == trunc_page_64(ipcb_paddr + sizeof(Exclaves_L4_IpcBuffer_t) - 1);
```

### 3.2 Notification Servers
From `03_jg_sharedmem_preload.macho`:
- `JgXnuProxyComponents.XnuProxyNotificationServer`: Generic asynchronous event notification channel.
- `JgXnuProxyComponents.DaemonNotificationServer`: Routes incoming Exclave notifications (e.g. Face ID completion, sensor status changes) to Darwin userland daemons (`sharingd`, `apsd`, `backboardd`).

---

## 4. SPTM Domain Transitions & Hardware Isolation

### 4.1 RingGate Domain Boundary
The **RingGate** (`L4_Type_Plat_RingGate = 0x17`) is an Apple Silicon hardware structure that facilitates controlled transitions between exception domains:
- **Host Enter (`sk_enter`)**: Saves Darwin thread register state, switches MMU Stage-2 translation tables to the Exclave domain, and restores Exclave thread state.
- **Exclave Exit (`xrt__plat_RingGate_Return`)**: Issues `svc #0` to cL4, cleans dirty cache lines (`dc cvac`), and restores execution to XNU at the trap return point.

### 4.2 Domain Fault Isolation
If an Exclave Conclave encounters a crash (e.g. NULL pointer dereference, assertion failure):
- The fault is intercepted by the microkernel's `vas_faulthandler_vtable`.
- The Conclave is suspended and transitions to `EXCLAVES_PANIC_WAIT_THREAD`.
- **Zero Host Panic**: The Darwin host kernel is physically insulated from the crash and continues normal operation.
- The Darwin inspection daemon collects a crash stackshot from `exclaves_inspection.c` (`output_length <= EXCLAVES_STACKSHOT_BUFFER_SIZE`).

---

## 5. Clean-Room C Client Runtime Implementation

To validate our reverse engineered wire specifications and trap mechanics, we implemented a complete standalone clean-room C client runtime at:
[`artifacts/exclave/pseudocode/tightbeam_client.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/exclave/pseudocode/tightbeam_client.pseudo.c)

### 5.1 Core Runtime Features
- **Zero-Allocation Inline IPC**: Uses register `tpidrro_el0` to write directly to the 512-byte `L4_IpcBuffer_t`.
- **Tightbeam Header Construction**: Builds the 88-byte `struct tb_message_s` header with `TB_MESSAGE_DISPOSITION_QUERY` (1), monotonic `invocation_id`, and `endpoint_token`.
- **Positional Encoding**: Serializes `uint64_t` (`tb_client_encode_u64`), `float` (`tb_client_encode_f32`), and capability registers (`tb_client_encode_capability`).
- **Synchronous Dispatch**: Executes `cl4_ipc_call` (`svc #0`), validates return codes against `L4_SUCCESS`, and unpacks server responses from `ipcb->mr[4..7]`.

---

## 6. Conclusions & Next Steps

Phase E4 has documented the complete kernel boundary interface:
1. System call trap vector specifications (`_exclaves_ctl_trap`, `_exclaves_call_trap`, `_exclaves_boot_trap`).
2. `xnuproxy` thread context (`struct exclaves_ctx`) and notification server architectures.
3. SPTM RingGate hardware transition mechanics and domain fault isolation.
4. Clean-room standalone C client runtime (`tightbeam_client.pseudo.c`).

**Next Phase**: Proceed to **Phase E5 (`exclave_phase_5_synthesis`)** to author the master verification script (`tools/verify_exclave_constants.py`), compile the cross-validation matrix, and publish the Master Publication Dossier (`IOS_27_EXCLAVEOS_TIGHTBEAM_RE.md`).
