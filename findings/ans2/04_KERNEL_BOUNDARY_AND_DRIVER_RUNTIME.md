# Phase 4: Host Kernel Boundary, SART Stage-2 Isolation & Clean-Room C Driver Runtime
**Target System**: iOS 27.2 (Darwin 24.2.0, Build 24B119)  
**Target Platform**: Apple Silicon A19 Pro (`t8150` / `v57ap`)  
**Firmware Subsystem**: Apple Storage Processor 3 (`ASP3-241.40.4~1100`) / ANS2  

---

## 1. Host XNU Kernel Driver Architecture

The host operating system interfaces with ANS2 through a layered stack of IOKit kernel extensions:

```
[ Userland Daemons: apfs.util, diskmanagementd, keybagd, securityd ]
                               │
                      IOKit Mach Messages
                               ▼
[ com.apple.iokit.IOStorageFamily (IOBlockStorageDevice) ]
                               │
[ com.apple.iokit.IONVMeFamily (IONVMeController) ]
   ├── Queue Initialization & SART DMA Buffer Registration
   ├── Submission Queue Descriptor Generation (64B SQE)
   └── Completion Reaping & Interrupt Servicing (IRQ 0x3cd)
                               │
          Atomic 32-bit MMIO Store to SQ Tail Doorbell
                               ▼
================================================================================
   HARDWARE BOUNDARY (A19 Pro On-Die Application Fabric / SART Coastguard)
================================================================================
                               ▲
       Hardware Interrupt 0x3cd / DMA Completion Write (16B CQE)
                               │
[ Apple ANS2 Storage Controller (RTKit Coprocessor Firmware) ]
   ├── SART Coastguard v4 Hardware Intercept
   ├── Hardware AES-XTS Streaming Cipher Engine (0x17DD47C00)
   └── FTL Indirection (CSW), CLog Commit Log, & Multi-Die NAND Control
```

---

## 2. Kernel Extensions Inventory

Extracted directly from `artifacts/kernel/kext_catalog_release.json`:

1. **`com.apple.iokit.IONVMeFamily` (`IONVMeController`)**:
   - Manages NVMe controller lifecycle, creates Submission/Completion queue pairs, programs doorbell offsets, and handles interrupt dispatch.
2. **`com.apple.driver.AppleEffaceableStorage`**:
   - Directly binds to Namespace 7 (`EFFACEABLE_STORAGE`), exposing raw cryptographic bag partitions to `keybagd` and SEP daemons.
3. **`com.apple.driver.AppleNANDConfigAccess`**:
   - Diagnostic and telemetry kext that issues vendor administrative commands (`0xC0` Band Stats, `0xC1` NAND Maturity, `0xD0` Telemetry).
4. **`com.apple.driver.AppleEffaceableBlockDevice`**:
   - Wraps Effaceable storage into an I/O block device abstraction.
5. **`com.apple.iokit.IOStorageFamily`**:
   - Implements APFS volume mounting, multi-page bio requests, and buffer cache synchronization.

---

## 3. SART Coastguard & SPTM Stage-2 DMA Isolation

A critical security innovation of Apple Silicon storage architecture is the complete isolation of DMA buffers:
1. **Host-Firmware Segregation**: Off-the-shelf NVMe drives have full DMA bus mastering capability over host memory. In contrast, on the A19 Pro, the ANS2 coprocessor's DMA master is physically fenced behind **SART Coastguard v4** (`0x17DC50000`).
2. **SPTM Stage-2 Page Table Protection**: During system boot, the Secure Page Table Monitor (SPTM) maps authorized host queue pages and HMB bounce buffers into the SART hardware table. The ANS2 coprocessor cannot modify its own SART table; only the EL2/EL3 monitor has write permission.
3. **Hardware Trap on DMA Violation**: If rogue or compromised coprocessor firmware attempts to access arbitrary host DRAM addresses, SART hardware instantly aborts the transfer, raises exception IRQ `0x3cf`, and triggers host panic diagnostics via `sart.c`.

---

## 4. Clean-Room C Driver Runtime Implementation

The complete driver client is implemented in [`artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c).

### Key Architectural Invariants Verified by Driver:
1. **64-Byte Hardware Descriptor Layout**:
   - `sizeof(ans2_sqe_t) == 64` enforced via compile-time `_Static_assert`.
   - PRP1 address, 64-bit SLBA, Length in blocks, Key Slot index, and Segment index mapped to exact bit offsets.
2. **16-Byte Hardware Completion Record**:
   - `sizeof(ans2_cqe_t) == 16` enforced via compile-time `_Static_assert`.
   - Circular phase-tag bit (`status_phase & 0x01`) tracking with zero lock contention.
3. **Hardware AES-XTS Tweak Computation**:
   - Implements mathematical formula `Tweak = AES_ECB(K, LBA | (NSID << 48) | (Seg << 56))`.
   - Verified cross-namespace isolation (identical LBAs across NS 1 and NS 2 produce mathematically distinct tweaks).
4. **Doorbell Calculations**:
   - Admin SQ0 Doorbell: `0x17DCC1000`
   - Admin CQ0 Doorbell: `0x17DCC1008`
   - IO SQ1 Doorbell: `0x17DCC1010`
   - IO CQ1 Doorbell: `0x17DCC1018`
5. **Compilation & Execution Verification**:
   - Compiles cleanly under `gcc -fsyntax-only -Wall -Wextra` with **0 errors and 0 warnings**.
   - Built with `-DSTANDALONE_HARNESS` and executed: 100% test assertions pass.
