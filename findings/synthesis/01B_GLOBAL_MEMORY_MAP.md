# Phase 1B Findings: Apple Silicon A19 Pro (t8150) Global Physical Memory Map (32 GB)

**Target Platform**: Apple Silicon A19 Pro (`t8150`) / iPhone18,3 / Device Class `v57ap`  
**Installed Memory**: 32 GB LPDDR5X-8533 (Physical Base `0x800000000` to Limit `0xfffffffff`)  
**Physical Address Width**: 36 bits (64 GB Architectural Maximum)  
**Artifact Dependencies**:
- [`artifacts/synthesis/global_physical_memory_map.json`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/global_physical_memory_map.json)
- [`artifacts/sptm/devicetree_hardware_map.json`](file:///home/prem/Projects/iOS%2027/artifacts/sptm/devicetree_hardware_map.json)
- [`artifacts/sep/sepos_microkernel_spec.json`](file:///home/prem/Projects/iOS%2027/artifacts/sep/sepos_microkernel_spec.json)

---

## 1. Global Physical Memory Architecture

The Apple Silicon A19 Pro (`t8150`) organizes its physical address space across a unified 36-bit physical bus aperture. Unlike traditional architectures where physical memory is monolithic and accessible to Ring 0, modern Apple Silicon enforces a strict, hardware-fenced partitioning model where over 1.74 GB of physical DRAM is permanently withheld from the host Darwin kernel at boot.

```
+----------------------------------------------------------------------------------------------------+
| A19 PRO (t8150) GLOBAL 32 GB DRAM PARTITIONING                                                     |
+----------------------------------------------------------------------------------------------------+
| 0x0000000800000000 +-----------------------------------------------------------------------------+ |
|                    | SPTM Hypervisor Partition (512 MB)                                          | |
|                    | - VTTBR_EL2 Stage-2 Translation Tables (16 KB granule)                       | |
|                    | - PAPT Physical Address Page Table (Frame tracking)                         | |
|                    | - Xenon Microkernel Code & Stacks (CTRR Region A Protected)                 | |
| 0x0000000820000000 +-----------------------------------------------------------------------------+ |
|                    | TXM Code Signing Monitor Partition (64 MB)                                  | |
|                    | - TrustCache CDHash Catalog & Image4 Verifier (CTRR Region B Protected)     | |
|                    | - CSM Dynamic Execution Authorization Rules                                 | |
| 0x0000000824000000 +-----------------------------------------------------------------------------+ |
|                    | ExclaveCore Microkernel Conclave Pool (1 GB)                                | |
|                    | - VasCore cL4 Microkernel Conclaves                                         | |
|                    | - Physical Memory Manager (PMM) Datacubes                                   | |
|                    | - Tightbeam Cross-Enclave Buffer Staging                                    | |
| 0x0000000864000000 +-----------------------------------------------------------------------------+ |
|                    | Secure Enclave TZ0S Partition (97.6875 MB)                                  | |
|                    | - sepOS 27.2 Microkernel Text, Kernel Heap, KeyStore Pools                   | |
|                    | - Hardware Key Ladder AES-XTS Unwrap Staging                                | |
| 0x000000086a1b0000 +-----------------------------------------------------------------------------+ |
|                    | Secure Enclave TZ1S Sensor Buffer (80.375 MB)                               | |
|                    | - Pearl NIR Camera Raw Sensor Frame Buffer (48 MB)                          | |
|                    | - ANE Embedding Tensor Verification Buffer (16 MB)                          | |
|                    | - Exclave Secure Privacy Window (16.375 MB)                                 | |
| 0x000000086f210000 +-----------------------------------------------------------------------------+ |
|                    | Darwin XNU Host Usable Physical DRAM (30.30 GB)                             | |
|                    | - XNU Mach Kernel Text, Zone Allocators, Page Cache                         | |
|                    | - Userland Address Spaces, Metal Unified Memory Pool                         | |
| 0x0000000fffffffff +-----------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Forensic Analysis of DRAM Carveouts

### 2.1 SPTM Hypervisor Carveout (`0x800000000` - `0x81fffffff`, 512 MB)
Allocated by iBoot during cold boot, the **Secure Page Table Monitor (SPTM)** partition operates at Guarded Execution Feature tier **GL2**. It manages Stage-2 address translation for the host kernel, preventing any unverified page table modifications even if Ring 0 is fully compromised.
- `0x800000000 - 0x802000000` (32 MB): SPTM Text and Read-Only Data locked under hardware CTRR Region A.
- `0x802000000 - 0x810000000` (224 MB): Physical Address Page Table (PAPT) housing metadata for all 2,097,152 physical 16 KB pages.
- `0x810000000 - 0x81fffffff` (256 MB): Dynamic Stage-2 translation page pool.

### 2.2 TXM Code Signing Monitor Carveout (`0x820000000` - `0x823ffffff`, 64 MB)
Operating at Guarded Execution Feature tier **GL1**, the **Trusted Execution Monitor (TXM)** hosts the Code Signing Monitor (CSM).
- Houses the static system TrustCache extracted from `iPhone18,3_27.2_24B119_Restore`.
- Enforces strict code signature verification prior to SPTM marking any physical page as executable (`PAPT_TYPE_XNU_TEXT`).

### 2.3 ExclaveCore Microkernel Carveout (`0x824000000` - `0x863ffffff`, 1 GB)
A dynamically retypable physical DRAM carveout dedicated to **ExclaveOS**.
- Managed by the Exclave Physical Memory Manager (PMM).
- Pages in this region can be transitioned between `PMM_TYPE_UNTYPED`, `PMM_TYPE_CONCLAVE_TEXT`, and `PMM_TYPE_DATACUBE`.
- Memory is isolated from the host AP by Stage-2 fault barriers.

### 2.4 Secure Enclave Partitions: TZ0S & TZ1S (178.0625 MB Total)
The Secure Enclave utilizes two contiguous physical DRAM carveouts:
1. **TZ0S (`0x864000000`, 97.6875 MB)**: Dedicated strictly to internal `sepOS 27.2` operations. Mapped through DART-SEP Stream ID `0x00`. Completely inaccessible to host AP or any external coprocessor.
2. **TZ1S (`0x86a1b0000`, 80.375 MB)**: Multi-coprocessor shared memory window:
   - Pearl NIR Camera Buffer: 48 MB (`0x03000000`) mapped by Camera ISP via `isp_map_iobmd`.
   - ANE Tensor Staging Buffer: 16 MB (`0x01000000`) mapped by ANE via `ane_map_iobmd`.
   - Exclave Secure Window: 16.375 MB (`0x01060000`) mapped via DART-SEP Stream ID `0x02`.

---

## 3. Dedicated Coprocessor Internal SRAMs

In addition to system DRAM, high-throughput coprocessors maintain dedicated on-chip retention SRAMs that remain powered across core sleep states:

| Coprocessor | SRAM Size | Physical Addressing | Function |
| :--- | :---: | :--- | :--- |
| **Secure Enclave (SEP)** | 512 KB | `0x00000000` (Internal) | Zero-leakage AES key ladder registers & instant zeroization hardware |
| **Always-On Processor (AOP2)** | 5.34 MB | `0x10000000` (Internal) | PitayaOS cL4 microkernel, 3.0s Siri VAD FIFO, and FastPath queue |
| **Neural Engine (ANE H18)** | 32 MB | `0x20000000` (Internal) | Spatial tensor weight caching & zero-DRAM intermediate layer storage |
| **Apple AGX G18 Pro GPU** | 16 MB | Internal Tile Memory | TBDR on-chip tile buffers & hardware BVH traversal cache |

---

## 4. Hardware MMIO Windows & Protection Fences

The A19 Pro maps all system control registers, mailboxes, and DMA engines across a 12.25 GB MMIO aperture (`0x0000000070000000` to `0x00000003ffffffff`):

```
+----------------------------------------------------------------------------------------------------+
| A19 PRO (t8150) HARDWARE MMIO REGISTER WINDOWS                                                     |
+----------------------------------------------------------------------------------------------------+
| 0x0000000070000000 - 0x000000008fffffff | Low MMIO: DART-SEP (0x70c80000), ASCwrap-SEP (0x72600000)|
| 0x00000000f0000000 - 0x00000000ffffffff | Core Fabric: PMGR (0xf3400000), AIC (0xf3c00000), DART-PMP |
| 0x0000000100000000 - 0x00000001ffffffff | Mid MMIO: AOP2 (0x101600000), DART-AOP, DART-ISP, DART-DCP  |
| 0x0000000200000000 - 0x00000003ffffffff | High MMIO: AGX GPU (0x230000000), ANE H18 (0x271800000)     |
+----------------------------------------------------------------------------------------------------+
```

### 4.1 Configurable Text Region Restriction (CTRR)
Hardware registers lock down critical executable pages against memory writes:
- **CTRR Region A (`0x800000000..0x802000000`, 32 MB)**: Locks SPTM hypervisor text. Any store instruction targeting this range causes an immediate, non-maskable hardware bus panic.
- **CTRR Region B (`0x820000000..0x821000000`, 16 MB)**: Locks TXM code signing validation rules.

### 4.2 Guarded Address Protection Filters (GAPF)
Hardware filters positioned at the fabric ports of the Apple Coherent Fabric (ACF7):
- Evaluates bus master transaction credentials on every cycle.
- Automatically drops and flags any non-secure DMA transaction attempting to access physical addresses in the range `0x800000000..0x86f20ffff`.
