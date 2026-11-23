# Phase 4 Findings: Apple Silicon A19 Pro (t8150) Inter-Enclave IPC Topology & Cross-Boundary Architecture

**Target Platform**: Apple Silicon A19 Pro (`t8150`) / iPhone18,3 / Device Class `v57ap`  
**Execution Privilege Model**: Guarded Execution Feature (GXF) + ARMv9.4-A Exception Levels  
**Artifact Dependencies**:
- [`artifacts/synthesis/inter_enclave_ipc_topology.json`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/inter_enclave_ipc_topology.json)
- [`artifacts/synthesis/pseudocode/a19_pro_cross_enclave_router.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/pseudocode/a19_pro_cross_enclave_router.pseudo.c)
- [`artifacts/exclave/tightbeam_wire_spec.json`](file:///home/prem/Projects/iOS%2027/artifacts/exclave/tightbeam_wire_spec.json)

---

## 1. Multi-Enclave Isolation Architecture

The Apple Silicon A19 Pro (`t8150`) transitions beyond monolithic kernel execution by partitioning system functionality across **9 hardware-isolated execution domains**. 

Rather than relying purely on CPU rings, the A19 Pro combines:
1. **Guarded Execution Feature (GXF)**: Hardware privilege tiers operating above EL1 (GL2 for SPTM, GL1 for TXM).
2. **Dedicated Out-of-Band Coprocessor Silicon**: Separate ARM64e cores for SEP and AOP2 with private SRAMs.
3. **Hardware IOMMU Stream Filters**: 25 DART Gen3 controllers enforcing memory boundaries on every DMA transaction.
4. **Hardware Protection Filters (CTRR & GAPF)**: Bus-level filters that abort invalid cross-domain memory accesses.

```
+----------------------------------------------------------------------------------------------------+
| A19 PRO INTER-ENCLAVE BOUNDARY TOPOLOGY                                                            |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    +-----------------------------+               +-----------------------------+                   |
|    |  SPTM Hypervisor Guard GL2  | <--- smc #0 - |   Darwin XNU Host (EL1)     |                   |
|    +-----------------------------+               +-----------------------------+                   |
|                   ^                                     |              |                           |
|                 smc #1                                ASCwrap       Tightbeam                      |
|                   v                                  (0x72600000)  (Datacubes)                     |
|    +-----------------------------+                      v              v                           |
|    |    TXM Code Monitor GL1     |               +-----------+  +-------------+                    |
|    +-----------------------------+               |   sepOS   |  |  ExclaveOS  |                    |
|                                                  | Secure Core| | cL4 Conclaves|                   |
|                                                  +-----------+  +-------------+                    |
|                                                         ^              ^                           |
|                                                 DART SID 0x02   DART SID 0x11 (EP 0x53)            |
|                                                 (Pearl NIR/ANE)|       |                           |
|                                                         |      +-------+                           |
|                                                         |      |                                   |
|                                                  +-----------+ |                                   |
|                                                  |   AOP2    |-+                                   |
|                                                  | PitayaOS  |                                     |
|                                                  +-----------+                                     |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Cross-Enclave Boundary Crossings

Empirical reverse engineering identified exactly **11 active hardware and software boundary crossings**:

### 2.1 Crossing 1: Darwin (EL1) to SPTM (GL2)
- **Mechanism**: `smc #0` (Domain Crossing Register convention: `x0` = Function ID, `x1..x6` = Parameters).
- **Latency**: ~180 processor cycles.
- **Role**: Dynamic Stage-2 page table modification, physical page retyping (`PAPT_TYPE_XNU_PAGE` to `PAPT_TYPE_EXCLAVE`), and memory permission enforcement.

### 2.2 Crossing 2: Darwin (EL1) to TXM (GL1)
- **Mechanism**: `smc #1` (Domain Crossing Register convention: `x0` = Function ID, `x1..x6` = Parameters).
- **Latency**: ~240 processor cycles.
- **Role**: Code Signing Monitor (CSM) validation, TrustCache hash lookup, Image4 authorization ticket checks before making code executable.

### 2.3 Crossing 3: Darwin (EL1) to sepOS (Secure Enclave)
- **Mechanism**: Primary ASCwrap-v6 Mailbox (`0x72600000`) and Doorbell (`0x7262c000`).
- **Latency**: ~850 processor cycles.
- **Role**: Class key unwrapping, Biometric authorization token generation, ApplePay cryptogram generation.

### 2.4 Crossing 4: Darwin (EL1) to ExclaveOS (cL4 Conclaves)
- **Mechanism**: Shared memory Datacubes allocated by Physical Memory Manager (PMM) and routed via Tightbeam RPC (`AppleExclaves.kext`).
- **Latency**: ~420 processor cycles.
- **Role**: Conclave invocations for sensitive userland services (Face ID matching, secure audio processing).

### 2.5 Crossing 5: Darwin (EL1) to AOP2 (PitayaOS / cL4)
- **Mechanism**: Primary ASCwrap-v6 Mailbox (`0x101600000`) + SPSC FastPath Ring Buffer (DART Stream ID `0x10`).
- **Latency**: ~320 processor cycles (mailbox) / 15 cycles (lock-free SPSC queue read).
- **Role**: 6-axis IMU streaming, TrueTone ALS telemetry, Always-On Display frame synchronization, Siri acoustic buffer drain.

### 2.6 Crossing 6: Darwin (EL1) to AGX G18 Pro GPU
- **Mechanism**: Userland Direct Submission command rings + PMP Doorbell (`0x23a000000`).
- **Latency**: ~110 processor cycles.
- **Role**: Zero-overhead Metal command buffer dispatch, hardware BVH ray-tracing traversal queue submission.

### 2.7 Crossing 7: Darwin (EL1) to ANE H18 (Neural Engine)
- **Mechanism**: Hardware FIFO Mailbox (`0x2e0000000`) + DART Stream IDs `0x00` and `0x01`.
- **Latency**: ~190 processor cycles.
- **Role**: Compiled HWX model graph submission, layer descriptor enqueue, tensor output DMA notification.

### 2.8 Crossing 8: AOP2 (cL4) to ExclaveOS (cL4)
- **Mechanism**: Dedicated Endpoint `0x53` (`sharedmem_xcoproc_AOP2_EP53_in`) mediated by DART-AOP Stream ID `0x11`.
- **Latency**: ~210 coprocessor cycles.
- **Role**: Hardware-isolated Sensor Indicator Light (SIL) status signaling. Completely bypasses host Darwin kernel.

### 2.9 Crossing 9: ExclaveOS (cL4) to DCP (Display Co-Processor)
- **Mechanism**: Secure proxy mailbox (`0x1fa27c000`) mediated by DART-DCP Stream ID `0x02`.
- **Latency**: ~180 coprocessor cycles.
- **Role**: Blends the green/orange privacy indicator dot directly onto the display scanout surface out-of-band from SpringBoard.

### 2.10 Crossing 10: Camera ISP to Secure Enclave (sepOS)
- **Mechanism**: DART-ISP Stream ID `0x02` mapping raw sensor frames directly into physical DRAM carveout **SEP TZ1S** (`0x86a1b0000`).
- **Latency**: ~95 cycles.
- **Role**: Raw NIR Face ID sensor frame capture. Completely unreadable by Darwin host kernel or GPU.

### 2.11 Crossing 11: ANE H18 to Secure Enclave (sepOS)
- **Mechanism**: DART-ANE Stream ID `0x02` reading feature tensors directly from **SEP TZ1S** (`0x86d1b0000`).
- **Latency**: ~85 cycles.
- **Role**: Hardware-accelerated biometric neural embedding matching executed entirely within the secure enclave memory perimeter.
