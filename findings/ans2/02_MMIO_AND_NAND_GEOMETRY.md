# Phase 2: Hardware Register Geometry, NAND Memory Architecture & AES-XTS Crypto Engine
**Target System**: iOS 27.2 (Darwin 24.2.0, Build 24B119)  
**Target Platform**: Apple Silicon A19 Pro (`t8150` / `v57ap`)  
**Firmware Subsystem**: Apple Storage Processor 3 (`ASP3-241.40.4~1100`) / ANS2  

---

## 1. MMIO Apertures & Hardware Register Map

The ANS2 controller interface is exposed to the system via multiple discrete memory-mapped physical apertures declared in the DeviceTree under `/arm-io/ans` and protected by SART Coastguard:

### ANS2 MMIO Register Table
| Region Index | Symbolic Constant | Physical Base | Size (Bytes) | Size (Hex) | Subsystem Function |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | `ASCWRAP_MAILBOX_BASE` | `0x179600000` | 557,056 B | `0x88000` (544 KB) | ASCwrap v6 Mailbox interface between AP and ANS2 coprocessor |
| **1** | `ANS2_CTRL_POWER_BASE` | `0x179050000` | 16,384 B | `0x4000` (16 KB) | ANS2 power states, clock gates (`ANS-V`), and controller reset |
| **3** | `NVME_BAR_DOORBELL_BASE` | `0x17DCC0000` | 393,216 B | `0x60000` (384 KB) | NVMe Register BAR, Submission Queue (SQ) & Completion Queue (CQ) Doorbells |
| **4** | `COPROC_SRAM_SCRATCHPAD` | `0x17B000000` | 16,777,216 B | `0x1000000` (16 MB) | On-chip high-speed SRAM scratchpad for FTL indirection tables |
| **5** | `NAND_MSP_INTERFACE_BASE` | `0x17DB90000` | 49,152 B | `0xC000` (48 KB) | Memory Subsystem Processor (MSP) PHY control & timing tunables |
| **6** | `AES_XTS_CRYPTO_ENGINE_BASE`| `0x17DD47C00` | 16,384 B | `0x4000` (16 KB) | Hardware AES-XTS streaming cipher engine & tweak registers |
| **9** | `SECONDARY_DISPATCH_QUEUE` | `0x1BDCC0000` | 65,536 B | `0x10000` (64 KB) | Secondary hardware dispatch queue & barrier synchronization |

---

## 2. SART Coastguard v4 DMA Protection Engine

Direct Memory Access (DMA) between ANS2 and host system DRAM is strictly governed by Apple's proprietary **SART Coastguard** controller (`sart-ans`):
- **SART Controller Physical Base**: `0x17DC50000` (Size: `0xC000` / 48 KB)
- **SART Generation**: Version 4 (`sart-version: 0x04`, `compatible: "sart,coastguard"`)
- **Power Management Offset**: `0x13E8` (`sart-power-reg-offset`)
- **Secondary Range**: `0x17DD44000` (16 KB, hardware canary integrity registers)
- **Protected Filter Window**: `0x17DCC0000` (384 KB aperture)

### SART Filtering Architecture
Whenever ANS2 initiates a DMA transfer to host memory (e.g. reading from a Submission Queue or writing to a Completion Queue), SART hardware intercepts the transaction:
1. Validates that the target physical address falls strictly within an authorized SART table entry.
2. Checks that the transfer length does not overrun the designated queue buffer.
3. If an unauthorized address is accessed, SART immediately aborts the bus transaction, fires interrupt `0x3cf` (IRQ 975), and records the fault in `sart.c`:
   `SART error. Interrupt status 0x%x`
   `LLT_WR_ERR: AWADDR 0x%llx AWID 0x%x`

---

## 3. Hardware Namespaces Architecture

The A19 Pro ANS2 controller natively partitions flash storage into **7 discrete hardware namespaces**:

| Namespace ID | Identifier | Flags | Allocation Size | Block Size | Architectural Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NS 1** | `OS_DATA` | `0x01` | Dynamic (NAND size) | 4096 B | Primary encrypted APFS filesystem (RootFS, SystemOS, Data) |
| **NS 2** | `SYSCFG` | `0x0e` | 2,048 Blocks (8 MB) | 4096 B | Hardware calibration, serial numbers, regulatory parameters |
| **NS 3** | `NVRAM` | `0x03` | 32 Blocks (128 KB) | 4096 B | Non-volatile environment parameters, boot-args, panic counts |
| **NS 4** | `DIAGNOSTICS` | `0x04` | 2 Blocks (8 KB) | 4096 B | Factory hardware test logs, production diagnostics |
| **NS 5** | `BOOT_PARAMS` | `0x05` | 2 Blocks (8 KB) | 4096 B | Low-level boot parameters, stage-2 handoff configuration |
| **NS 6** | `PANIC_LOG` | `0x08` | 256 Blocks (1 MB) | 4096 B | Raw kernel panic dumps preserved across reboots |
| **NS 7** | `EFFACEABLE_STORAGE`| `0x0d` | 32,768 Blocks (128 MB) | 4096 B | Cryptographic key locker for volume keys and anti-replay nonces |

Namespace isolation is enforced directly in hardware. Read and write requests to protected namespaces (such as `EFFACEABLE_STORAGE`) require specialized administrative entitlements and hardware key ladder clearance.

---

## 4. Hardware AES-XTS NAND Encryption Engine

Apple integrates an ultra-low-latency AES-XTS streaming cipher engine directly inside the ANS2 storage controller datapath at MMIO address `0x17DD47C00`.

### 4.1 Data Streaming Pipeline
- **Host-to-Flash (`H2F`)**: When host writes data via NVMe, data beats are encrypted on-the-fly before reaching the raw NAND flash buffers.
- **Flash-to-Host (`F2H`)**: When host reads data from NVMe, data beats are decrypted on-the-fly before SART commits them to host DRAM.

### 4.2 Per-Block 128-Bit Tweak Generation Formula
In AES-XTS, each 4096-byte logical sector is encrypted using a unique 128-bit cryptographic tweak derived from the sector address:

$$	ext{Tweak} = 	ext{AES-ECB}_{K_{	ext{tweak}}}\left( (	ext{LBA} \ \& \ 	ext{0xFFFFFFFFFFFF}) \ | \ ((	ext{NS\_ID} \ \& \ 	ext{0xFF}) \ll 48) \ | \ ((	ext{Seg\_Idx} \ \& \ 	ext{0xFFFF}) \ll 56) ight)$$

This mathematical formulation guarantees:
1. Writing identical plaintext to different LBAs produces completely uncorrelated ciphertext on the NAND flash.
2. Cross-namespace cryptographic replay attacks are prevented because `NS_ID` is permanently bonded into the tweak upper bits.
3. Physical sector relocation during garbage collection does not invalidate ciphertext because the tweak is anchored to the logical coordinate.

### 4.3 Hardware Error Diagnostics (`sl_hal.c`)
The cipher engine hardware status is continuously monitored via dedicated registers:
```c
struct ans2_crypto_status_regs {
    uint32_t status_reg;      // Offset 0x00: Ready, Busy, Error flags
    uint32_t reserved0;
    uint32_t load_err_info0;  // Offset 0x08: Key descriptor load error
    uint32_t load_err_info1;  // Offset 0x0C: Tweak generator alignment fault
    uint32_t reserved1;
    uint32_t h2f_err;         // Offset 0x14: Host-to-Flash write cipher error
    uint32_t f2h_err;         // Offset 0x18: Flash-to-Host read cipher error
};
```

---

## 5. Wear Leveling & Bad Block Management (FTL Engine)

The ANS2 FTL implements a sophisticated, multi-tier endurance preservation system:

### 5.1 On-Demand SLC (oSLC) Dynamic Caching
- Incoming host writes are initially absorbed into high-speed Single-Level Cell cache bands (`BI: BLKS(SLC)`).
- As write bursts subside, background defragmentation workers (`gc.c`, `ldefrag.c`) fold the data into high-density Triple-Level Cell bands (`BU: BLKS(MLC/TLC)`).

### 5.2 Bad Block Retirement (BBT) & Grown Bad Blocks (`GBB`)
- Factory defective blocks are identified during manufacturing and locked out.
- During device operation, blocks that encounter repeated erase timeouts or uncorrectable ECC errors (`UE num ueccs`) are dynamically classified as **Grown Bad Blocks (GBBs)** (`GB: total number GBBs`).
- The FTL immediately maps out the failed physical block and relocates active data using the hardware RAID parity reconstruction engine (`RH: host reconstructions`).

### 5.3 Autonomous Read Disturb Scrubber (`readdisturb.c`)
- Repeated reads to a physical NAND block cause subtle voltage drift in adjacent flash cells.
- ANS2 implements hardware read samplers (`RDS: Sectors read due to RD sampler`). When a block's read counter crosses 100,000 accesses, the FTL automatically schedules a background relocation and block rewrite.
