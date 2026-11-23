# Phase 3 Findings: Apple Silicon A19 Pro (t8150) Master AIC Interrupt Matrix & ASCwrap Mailbox Architecture

**Target Platform**: Apple Silicon A19 Pro (`t8150`) / iPhone18,3 / Device Class `v57ap`  
**Interrupt Controller**: AIC Gen3 (Apple Interrupt Controller Version 3, Base `0x00000000f3c00000`)  
**Hardware Mailbox**: ASCwrap-v6 (Apple Serial Communication Wrapper Version 6)  
**Artifact Dependencies**:
- [`artifacts/synthesis/master_aic_interrupt_matrix.json`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/master_aic_interrupt_matrix.json)
- [`artifacts/synthesis/ascwrap_mailbox_matrix.json`](file:///home/prem/Projects/iOS%2027/artifacts/synthesis/ascwrap_mailbox_matrix.json)
- [`artifacts/aop/aop_mailbox_protocol.json`](file:///home/prem/Projects/iOS%2027/artifacts/aop/aop_mailbox_protocol.json)

---

## 1. Apple Interrupt Controller (AIC Gen3) Architecture

The **Apple Interrupt Controller (AIC Gen3)** anchored at MMIO base `0x00000000f3c00000` provides centralized interrupt routing across all 6 Application Processor (AP) cores and external coprocessor mailboxes on the A19 Pro. 

AIC Gen3 manages up to 1024 interrupt vectors, supporting four primary interrupt classes:
1. **FIQ (Fast Interrupt Request)**: Prioritized non-preemptible interrupts for timebase sync, timer tick, and NMI.
2. **IRQ (Normal Interrupt Request)**: Level- and edge-triggered coprocessor mailbox and I/O interrupts.
3. **Cross-Core IPI (Inter-Processor Interrupts)**: Direct register writes triggering target core scheduling.
4. **Hardware Diagnostic NMI**: Non-maskable interrupts triggered upon CTRR or GAPF violation.

```
+----------------------------------------------------------------------------------------------------+
| AIC GEN3 HARDWARE INTERRUPT ROUTING TOPOLOGY                                                       |
+----------------------------------------------------------------------------------------------------+
|  Hardware Sources (109 Nodes):                                                                     |
|    - CPUs (68, 71, 74, 77, 88, 91)       ====> [ AIC Gen3 Master Arbiter ]                         |
|    - SEP Mailbox & ESM (304..307, 311)   ====> [ Base: 0x00000000f3c00000 ]                        |
|    - AOP1 & AOP2 (349..364, 387)         ====> [ Priority Filter & Routing]                        |
|    - AGX G18 & RTBuddy (933..936, 952..959) ===> [ Per-CPU FIQ/IRQ Target  ]                        |
|    - ANE H18 (607, 608, 620)             ====> [ Core 0..1 (Everest)      ]                        |
|    - DCP & Display (632..654)            ====> [ Core 2..5 (Sawtooth)     ]                        |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Master AIC Interrupt Vector Cross-Reference Table

Extraction from `DeviceTree.v57ap.im4p` confirmed exact vector assignments across all major subsystems:

| Vector (Dec) | Vector (Hex) | DeviceTree Node | Hardware Interrupt Role |
| :---: | :---: | :--- | :--- |
| **68, 71** | `0x0044, 0x0047` | `/device-tree/cpus/cpu0,1` | Everest Cores 0 & 1 Performance Monitor Overflows |
| **74, 77** | `0x004a, 0x004d` | `/device-tree/cpus/cpu2,3` | Sawtooth Cores 0 & 1 Performance Monitor Overflows |
| **88, 91** | `0x0058, 0x005b` | `/device-tree/cpus/cpu4,5` | Sawtooth Cores 2 & 3 Performance Monitor Overflows |
| **304** | `0x0130` | `/device-tree/arm-io/sep` | Host-to-SEP Mailbox Inbox Pending |
| **305** | `0x0131` | `/device-tree/arm-io/sep` | SEP-to-Host Mailbox Outbox Consumed Ack |
| **306** | `0x0132` | `/device-tree/arm-io/sep` | SEP Doorbell Interrupt Trigger |
| **307** | `0x0133` | `/device-tree/arm-io/sep` | SEP System Error / Panic Telemetry |
| **311** | `0x0137` | `/device-tree/arm-io/esm` | Embedded Security Module Physical Tamper Alarm |
| **314** | `0x013a` | `/device-tree/arm-io/dart-sep` | DART-SEP IOMMU Translation Fault |
| **349, 350** | `0x015d, 0x015e` | `/device-tree/arm-io/aop` | AOP1 Legacy Mailbox Inbox & Outbox |
| **351, 352** | `0x015f, 0x0160` | `/device-tree/arm-io/aop` | AOP1 Legacy Doorbell & Error |
| **353, 356** | `0x0161, 0x0164` | `/device-tree/arm-io/aop-exclave-mailbox` | AOP1 Exclave Proxy Inbox & Outbox |
| **357** | `0x0165` | `/device-tree/arm-io/aop2` | AOP2 Primary Mailbox Inbox Message Pending |
| **358** | `0x0166` | `/device-tree/arm-io/aop2` | AOP2 Primary Mailbox Outbox Consumed Ack |
| **359** | `0x0167` | `/device-tree/arm-io/aop2` | AOP2 Doorbell Aggregator Trigger |
| **360** | `0x0168` | `/device-tree/arm-io/aop2` | AOP2 Hardware Error / RTKit Panic Notification |
| **361, 364** | `0x0169, 0x016c` | `/device-tree/arm-io/aop2-exclave-mailbox`| AOP2 Exclave Mailbox Proxy Inbox & Outbox |
| **387** | `0x0183` | `/device-tree/arm-io/dart-aop` | DART-AOP IOMMU Translation Fault |
| **607** | `0x025f` | `/device-tree/arm-io/ane` | ANE H18 Layer Execution Complete |
| **608** | `0x0260` | `/device-tree/arm-io/dart-ane` | DART-ANE IOMMU Translation Fault |
| **620** | `0x026c` | `/device-tree/arm-io/ane` | ANE Hardware Mailbox FIFO Interrupt |
| **632, 633** | `0x0278, 0x0279` | `/device-tree/arm-io/dcp` | DCP Primary Mailbox Inbox & Outbox |
| **634, 635** | `0x027a, 0x027b` | `/device-tree/arm-io/dcp` | DCP Doorbell & Hardware Error |
| **636, 639** | `0x027c, 0x027f` | `/device-tree/arm-io/dcp-exclave-mailbox` | DCP Exclave Mailbox Proxy Inbox & Outbox |
| **640** | `0x0280` | `/device-tree/arm-io/disp0` | Display VSYNC Primary Interrupt |
| **651** | `0x028b` | `/device-tree/arm-io/dart-dcp` | DART-DCP IOMMU Translation Fault |
| **776, 777** | `0x0308, 0x0309` | `/device-tree/arm-io/pmp` | PMP Firmware Mailbox Inbox & Outbox |
| **780** | `0x030c` | `/device-tree/arm-io/dart-pmp` | DART-PMP IOMMU Translation Fault |
| **933, 934** | `0x03a5, 0x03a6` | `/device-tree/arm-io/sgx` | AGX G18 Shader Core Clusters 0 & 1 Complete |
| **935** | `0x03a7` | `/device-tree/arm-io/sgx` | AGX G18 Hardware BVH Traversal Engine Done |
| **936** | `0x03a8` | `/device-tree/arm-io/sgx` | AGX G18 Tile Memory Overflow / Hardware Fault |
| **952, 953** | `0x03b8, 0x03b9` | `/device-tree/arm-io/gfx-asc` | AGX RTBuddy Core 0 Mailbox Inbox & Outbox |
| **956, 957** | `0x03bc, 0x03bd` | `/device-tree/arm-io/gfx1-asc` | AGX RTBuddy Core 1 Mailbox Inbox & Outbox |
| **972, 974** | `0x03cc, 0x03ce` | `/device-tree/arm-io/ans` | Apple NAND Subsystem Command Rings 0 & 1 Complete |
| **973** | `0x03cd` | `/device-tree/arm-io/ans` | SART-ANS Storage IOMMU Translation Fault |
| **1041** | `0x0411` | `/device-tree/arm-io/aes` | Hardware AES Engine Cryptographic Complete |
| **1142, 1150**| `0x0476, 0x047e` | `/device-tree/arm-io/dart-apcie0,1` | PCIe Ports 0 & 1 IOMMU Translation Faults |

---

## 3. Unified ASCwrap-v6 Mailbox & Doorbell Matrix

All inter-processor messaging between the host AP and coprocessors relies on the **ASCwrap-v6** register model.

```
+----------------------------------------------------------------------------------------------------+
| ASCWRAP-v6 REGISTER GEOMETRY & DOORBELL PROTOCOL                                                  |
+----------------------------------------------------------------------------------------------------+
| Register Name   | Offset | Width  | Function                                                       |
| MBI_INBOX_CTRL  | +0x00  | 32-bit | Target Inbox Control: Enable IRQ (Bit 0), FIFO Count (Bits 15:8)|
| MBI_INBOX_DATA  | +0x08  | 64-bit | 64-Bit Message Queue: Reads pop entry from hardware FIFO       |
| MBI_OUTBOX_CTRL | +0x20  | 32-bit | Sender Outbox Control: Acknowledge & Status Flags              |
| MBI_OUTBOX_DATA | +0x28  | 64-bit | 64-Bit Message Write: Stores push entry into destination FIFO  |
| MBI_STATUS      | +0x40  | 32-bit | Status Flags: Bit 0 (FIFO Empty), Bit 1 (FIFO Full)            |
+----------------------------------------------------------------------------------------------------+
| DOORBELL_SET    | +0x00  | 32-bit | Doorbell Register: Write-1-to-set triggers destination AIC IRQ |
| DOORBELL_CLEAR  | +0x04  | 32-bit | Doorbell Register: Write-1-to-clear acknowledges pending IRQ   |
| DOORBELL_STATUS | +0x08  | 32-bit | Doorbell Register: Current pending interrupt bitmask           |
+----------------------------------------------------------------------------------------------------+
```

### 3.1 Hardware Doorbell Handshake Sequence
1. Sender writes 64-bit message word into `MBI_OUTBOX_DATA` (`+0x0028`).
2. Sender executes an ARM64 Inner Shareable Store memory barrier (`dmb ishst`).
3. Sender writes bit 0 into `DOORBELL_SET` (`+0x0000`).
4. Hardware propagates doorbell interrupt directly to AIC (e.g. IRQ `357` on AOP2, IRQ `304` on SEP).
5. Receiver service routine reads 64-bit word from `MBI_INBOX_DATA` (`+0x0008`), automatically dequeuing entry.
6. Receiver executes an ARM64 Inner Shareable Load memory barrier (`dmb ishld`).
7. Receiver writes bit 0 into `DOORBELL_CLEAR` (`+0x0004`) to dismiss pending line.

### 3.2 Secure Exclave Mailbox Proxies
Exclave proxies (`aop2-exclave-mailbox` at `0x35167c000`, `dcp-exclave-mailbox` at `0x1fa27c000`) differ from standard ASCwrap instances:
- Mapped exclusively into **SPTM Stage-2 protected space**.
- Attempts by Darwin Ring 0 to read/write these MMIO ranges trigger an immediate Stage-2 synchronous instruction/data abort (`ESR_EL2` EC `0x24`).
- Used exclusively by ExclaveOS conclaves to signal out-of-band Sensor Indicator Light (SIL) status.
