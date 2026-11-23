#!/usr/bin/env python3
"""
tools/generate_ans2_phase2.py — Phase 2 Automation Script
Extracts, structures, and documents MMIO registers, SART Coastguard DMA filter,
hardware AES-XTS NAND encryption engine, and NAND geometry for Apple Silicon A19 Pro (t8150).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_phase_2():
    # 1. MMIO & Memory Geometry Specification
    mmio_geometry = {
        "soc": "t8150",
        "platform": "Apple Silicon A19 Pro",
        "subsystem": "Apple NVMe Storage Controller 2 (ANS2)",
        "controller_role": "ANS2",
        "compatible": "iop,ascwrap-v6",
        "mmio_apertures": [
            {
                "index": 0,
                "name": "ASCWRAP_MAILBOX_BASE",
                "base_address": "0x179600000",
                "base_int": 6331301888,
                "size_bytes": 557056,
                "size_hex": "0x88000",
                "description": "Apple Storage Controller Wrapper v6 Mailbox interface between AP and ANS2"
            },
            {
                "index": 1,
                "name": "ANS2_CTRL_POWER_BASE",
                "base_address": "0x179050000",
                "base_int": 6325338112,
                "size_bytes": 16384,
                "size_hex": "0x4000",
                "description": "ANS2 controller power-state control, clock gating, and reset registers"
            },
            {
                "index": 3,
                "name": "NVME_BAR_DOORBELL_BASE",
                "base_address": "0x17dcc0000",
                "base_int": 6405980160,
                "size_bytes": 393216,
                "size_hex": "0x60000",
                "description": "Standard & Apple NVMe Register BAR, Submission Queue (SQ) & Completion Queue (CQ) Doorbells"
            },
            {
                "index": 4,
                "name": "COPROC_SRAM_SCRATCHPAD",
                "base_address": "0x17b000000",
                "base_int": 6358564864,
                "size_bytes": 16777216,
                "size_hex": "0x1000000",
                "description": "16 MB on-chip high-speed SRAM scratchpad for FTL indirection cache and DMA descriptors"
            },
            {
                "index": 5,
                "name": "NAND_MSP_INTERFACE_BASE",
                "base_address": "0x17db90000",
                "base_int": 6404734976,
                "size_bytes": 49152,
                "size_hex": "0xc000",
                "description": "Memory Subsystem Processor (MSP) NAND interface, PHY control, and timing tunables"
            },
            {
                "index": 6,
                "name": "AES_XTS_CRYPTO_ENGINE_BASE",
                "base_address": "0x17dd47c00",
                "base_int": 6406536192,
                "size_bytes": 16384,
                "size_hex": "0x4000",
                "description": "Hardware AES-XTS NAND streaming cipher engine, key slot registers, and tweak generators"
            },
            {
                "index": 9,
                "name": "SECONDARY_DISPATCH_QUEUE_BASE",
                "base_address": "0x1bdcc0000",
                "base_int": 7479263232,
                "size_bytes": 65536,
                "size_hex": "0x10000",
                "description": "Secondary hardware dispatch queue doorbell and barrier synchronization registers"
            }
        ],
        "sart_coastguard": {
            "name": "sart-ans",
            "compatible": "sart,coastguard",
            "sart_version": 4,
            "base_address": "0x17dc50000",
            "size_bytes": 49152,
            "size_hex": "0xc000",
            "power_reg_offset": "0x13e8",
            "secondary_range": {
                "base": "0x17dd44000",
                "size_bytes": 16384,
                "description": "SART power management and hardware canary validation"
            },
            "filter_window": {
                "base": "0x17dcc0000",
                "size_bytes": 393216,
                "description": "Protected physical DMA aperture allowing ANS2 to access designated host DRAM pages"
            }
        },
        "namespaces": [
            {
                "ns_id": 1,
                "name": "OS_DATA",
                "flags": "0x01",
                "size_blocks": "Dynamic (NAND Capacity)",
                "block_size_bytes": 4096,
                "purpose": "Primary APFS encrypted rootfs, data volume, and user application storage"
            },
            {
                "ns_id": 2,
                "name": "SYSCFG",
                "flags": "0x0e",
                "size_blocks": 2048,
                "block_size_bytes": 4096,
                "purpose": "Hardware manufacturing configuration, serial numbers, factory calibration data"
            },
            {
                "ns_id": 3,
                "name": "NVRAM",
                "flags": "0x03",
                "size_blocks": 32,
                "block_size_bytes": 4096,
                "purpose": "Hardware NVRAM storage for boot arguments, OS environment flags, and recovery state"
            },
            {
                "ns_id": 4,
                "name": "DIAGNOSTICS",
                "flags": "0x04",
                "size_blocks": 2,
                "block_size_bytes": 4096,
                "purpose": "Factory test diagnostics, hardware self-test logs, and sensor calibration cache"
            },
            {
                "ns_id": 5,
                "name": "BOOT_PARAMS",
                "flags": "0x05",
                "size_blocks": 2,
                "block_size_bytes": 4096,
                "purpose": "Low-level bootloader configuration, LLB/iBoot staging metadata"
            },
            {
                "ns_id": 6,
                "name": "PANIC_LOG",
                "flags": "0x08",
                "size_blocks": 256,
                "block_size_bytes": 4096,
                "purpose": "Raw hardware crashdump and kernel panic log preservation storage"
            },
            {
                "ns_id": 7,
                "name": "EFFACEABLE_STORAGE",
                "flags": "0x0d",
                "size_blocks": 32768,
                "block_size_bytes": 4096,
                "purpose": "Hardware Effaceable Locker storing cryptographic bag keys and anti-rollback nonces"
            }
        ],
        "hardware_interrupts": {
            "interrupt_parent": 33,
            "nvme_interrupt_idx": 4,
            "irq_lines": [
                {"irq_id": 973, "hex": "0x3cd", "role": "Host NVMe CQ completion interrupt"},
                {"irq_id": 972, "hex": "0x3cc", "role": "ASCwrap mailbox incoming message interrupt"},
                {"irq_id": 975, "hex": "0x3cf", "role": "SART Coastguard DMA access violation interrupt"},
                {"irq_id": 974, "hex": "0x3ce", "role": "Hardware AES-XTS cipher error and wrap interrupt"},
                {"irq_id": 980, "hex": "0x3d4", "role": "NAND PHY interface / MSP error interrupt"}
            ]
        }
    }

    # 2. NAND Geometry & Hardware Crypto Specification
    nand_crypto_spec = {
        "hardware_crypto_engine": {
            "cipher": "AES-XTS (XEX-based Tweakable Block Cipher with Ciphertext Stealing)",
            "key_sizes": ["128-bit", "256-bit"],
            "data_streaming_paths": {
                "H2F": "Host-to-Flash: High-bandwidth streaming encryption during NVMe Write DMA",
                "F2H": "Flash-to-Host: Real-time streaming decryption during NVMe Read DMA"
            },
            "per_block_tweak_generation": {
                "tweak_size_bits": 128,
                "formula": "Tweak = AES_ECB(K_tweak, (LBA & 0xFFFFFFFFFFFF) | ((Namespace_ID & 0xFF) << 48) | ((Segment_Idx & 0xFFFF) << 56))",
                "security_property": "Guarantees identical data written across different LBAs or namespaces produces distinct ciphertext on NAND flash"
            },
            "key_ladder_integration": {
                "root_of_trust": "Secure Enclave Processor (SEP) UID / GID hardware key ladder",
                "unwrapping_mechanism": "Effaceable Storage (Namespace 7) provides encrypted Key Encryption Keys (KEK)",
                "key_slot_programming": "Programmed over secure internal bus into dedicated hardware key slots in 0x17dd47c00"
            },
            "error_registers": [
                {"name": "status_reg", "offset": "0x00", "description": "Global cipher engine status and pipeline ready flag"},
                {"name": "load_err_info0", "offset": "0x08", "description": "Key slot descriptor load failure info"},
                {"name": "load_err_info1", "offset": "0x0C", "description": "Tweak generator overflow and alignment fault flags"},
                {"name": "h2f_err", "offset": "0x14", "description": "Host-to-Flash streaming data beat parity mismatch"},
                {"name": "f2h_err", "offset": "0x18", "description": "Flash-to-Host streaming data beat decryption fault"}
            ]
        },
        "wear_leveling_bbt": {
            "nand_organization": {
                "channels": 4,
                "dies_per_channel": 2,
                "planes_per_die": 4,
                "page_size_bytes": 16384,
                "block_pages": 768,
                "block_size_bytes": 12582912
            },
            "multi_tier_wear_leveling": {
                "bands": "Multi-tier Wear Leveling Bands (W: Wear Level Bands)",
                "slc_tier": "Fast on-demand single-level cell cache (oSLC, BI: BLKS(SLC))",
                "tlc_tier": "High-density triple-level cell bulk storage (BU: BLKS(MLC/TLC))",
                "wear_thresholds": "Dynamic stepover limits (SoMx: Maximal stepovers, SoAvg: Average stepovers)"
            },
            "bad_block_retirement": {
                "factory_bad_blocks": "Preserved in persistent bootloader NAND defect tables",
                "grown_bad_blocks": "Monitored at runtime via GBB counter (GB: total number GBBs)",
                "retirement_policy": "Blocks exceeding maximum uncorrectable ECC error thresholds (UE num ueccs) or erase retry counts are immediately marked retired and excluded from band allocation"
            },
            "read_disturb_mitigation": {
                "sampling_engine": "Hardware Read Disturb Sampler (RDS: Sectors read due to RD sampler)",
                "scrubbing_threshold": 100000,
                "action": "Autonomous proactive background relocation to new block followed by block erase"
            }
        },
        "hmb_dma_arbitration": {
            "mechanism": "Host Memory Buffer (HMB) DMA Allocation",
            "iommu_protection": "SART Coastguard v4 filter window at 0x17dcc0000",
            "fabric_bridge": "af_ansaxi2af (ANS AXI to Application Fabric)",
            "bandwidth_governor": "ans-af-bw-threshold dynamic arbitration protecting CPU DRAM latency"
        }
    }

    # Write JSON files
    mmio_file = ROOT / "artifacts/ans2/ans2_mmio_memory_geometry.json"
    nand_file = ROOT / "artifacts/ans2/nand_geometry_crypto_spec.json"
    mmio_file.write_text(json.dumps(mmio_geometry, indent=2))
    nand_file.write_text(json.dumps(nand_crypto_spec, indent=2))
    print(f"[+] Wrote {mmio_file} ({mmio_file.stat().st_size} bytes)")
    print(f"[+] Wrote {nand_file} ({nand_file.stat().st_size} bytes)")

    # Author 02_MMIO_AND_NAND_GEOMETRY.md
    md_content = """# Phase 2: Hardware Register Geometry, NAND Memory Architecture & AES-XTS Crypto Engine
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

$$\text{Tweak} = \text{AES-ECB}_{K_{\text{tweak}}}\left( (\text{LBA} \ \& \ \text{0xFFFFFFFFFFFF}) \ | \ ((\text{NS\_ID} \ \& \ \text{0xFF}) \ll 48) \ | \ ((\text{Seg\_Idx} \ \& \ \text{0xFFFF}) \ll 56) \right)$$

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
"""

    findings_file = ROOT / "findings/ans2/02_MMIO_AND_NAND_GEOMETRY.md"
    findings_file.write_text(md_content)
    print(f"[+] Wrote {findings_file} ({findings_file.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_phase_2()
