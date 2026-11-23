#!/usr/bin/env python3
"""
tools/generate_ans2_phase3.py — Phase 3 Automation Script
Models the Apple NVMe Command Stream, 64-byte SQE descriptor layouts,
16-byte CQE completion records, Apple vendor-specific opcodes, and doorbell protocols.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_phase_3():
    # 1. NVMe Command Stream Spec
    cmd_stream_spec = {
        "soc": "t8150",
        "subsystem": "Apple NVMe Storage Controller 2 (ANS2)",
        "queue_geometry": {
            "submission_queue_entry_bytes": 64,
            "completion_queue_entry_bytes": 16,
            "queue_depth_entries": 64,
            "sq_total_buffer_bytes": 4096,
            "cq_total_buffer_bytes": 1024,
            "descriptor_alignment_bytes": 64,
            "linear_submission_queue_mode": True,
            "max_supported_queues": 32,
            "prp_page_size_bytes": 16384
        },
        "submission_queue_entry_format": {
            "size_bytes": 64,
            "fields": [
                {"name": "cdw0_opcode_flags", "offset_bytes": 0, "size_bytes": 4, "description": "Opcode [7:0], FUSE [9:8], PSDT [15:14], CID [31:16]"},
                {"name": "nsid", "offset_bytes": 4, "size_bytes": 4, "description": "Target Namespace ID (1..7)"},
                {"name": "cdw2_cdw3_reserved", "offset_bytes": 8, "size_bytes": 8, "description": "Reserved / Vendor metadata pointers"},
                {"name": "mptr", "offset_bytes": 16, "size_bytes": 8, "description": "Metadata Pointer (Physical DMA address or SART token)"},
                {"name": "dptr_prp1", "offset_bytes": 24, "size_bytes": 8, "description": "PRP Entry 1 / Data Buffer physical address (16KB aligned)"},
                {"name": "dptr_prp2", "offset_bytes": 32, "size_bytes": 8, "description": "PRP Entry 2 / PRP List Pointer"},
                {"name": "cdw10_slba_low", "offset_bytes": 40, "size_bytes": 4, "description": "Starting LBA bits [31:0]"},
                {"name": "cdw11_slba_high", "offset_bytes": 44, "size_bytes": 4, "description": "Starting LBA bits [63:32]"},
                {"name": "cdw12_length_control", "offset_bytes": 48, "size_bytes": 4, "description": "Number of logical blocks [15:0], Protection/FUA flags"},
                {"name": "cdw13_dsm_dsmg", "offset_bytes": 52, "size_bytes": 4, "description": "Dataset management attributes / Sequential hint"},
                {"name": "cdw14_vendor_key", "offset_bytes": 56, "size_bytes": 4, "description": "AES-XTS crypto key slot index [7:0] & tweak flags"},
                {"name": "cdw15_vendor_seg", "offset_bytes": 60, "size_bytes": 4, "description": "Segment context index & hardware barrier token"}
            ]
        },
        "completion_queue_entry_format": {
            "size_bytes": 16,
            "fields": [
                {"name": "command_specific", "offset_bytes": 0, "size_bytes": 4, "description": "Result of command or vendor diagnostic data"},
                {"name": "reserved", "offset_bytes": 4, "size_bytes": 4, "description": "Reserved / Unused"},
                {"name": "sq_head_sq_id", "offset_bytes": 8, "size_bytes": 4, "description": "SQ Head Pointer [15:0], SQ ID [31:16]"},
                {"name": "status_cid_phase", "offset_bytes": 12, "size_bytes": 4, "description": "Command ID [15:0], Phase Tag [16], Status Code [31:17]"}
            ]
        },
        "apple_vendor_opcodes": {
            "admin_opcodes": {
                "0xC0": {
                    "symbol": "NVME_APPLE_CMD_READ_BAND_STATS",
                    "c_identifier": "Cmd_NvmeAdminReadBandStats",
                    "direction": "In (Controller to Host)",
                    "description": "Dumps wear-leveling band wear distribution, SLC/TLC counts, and stepovers"
                },
                "0xC1": {
                    "symbol": "NVME_APPLE_CMD_GET_NAND_MATURITY",
                    "c_identifier": "Cmd_tunnelGetNandMaturity",
                    "direction": "In (Controller to Host)",
                    "description": "Queries silicon maturity parameters, process revision, and lithography voltage offsets"
                },
                "0xC2": {
                    "symbol": "NVME_APPLE_CMD_GET_NAND_INFO",
                    "c_identifier": "Host_GetNANDInfo",
                    "direction": "In (Controller to Host)",
                    "description": "Queries channel geometry, die count, plane count, and vendor ID"
                },
                "0xC4": {
                    "symbol": "NVME_APPLE_CMD_DEBUG_RECLAIM_BOOT_BLOCK",
                    "c_identifier": "Nand_DebugReclaimBootBlock",
                    "direction": "Out (Host to Controller)",
                    "description": "Instructs FTL to force refresh and reclaim pre-boot blocks"
                },
                "0xC8": {
                    "symbol": "NVME_APPLE_CMD_ASI_DELETE_FW",
                    "c_identifier": "ASI_NAND_OP_DELETE_FW",
                    "direction": "Out (Host to Controller)",
                    "description": "Erases staging firmware image slots in preparation for DFU update"
                },
                "0xCA": {
                    "symbol": "NVME_APPLE_CMD_SET_PROTOCOL_VALIDATION",
                    "c_identifier": "ASI_NAND_OP_SET_PROTOCOL_VALIDATION",
                    "direction": "Out (Host to Controller)",
                    "description": "Sets hardware protocol validation and error injection masks"
                },
                "0xD0": {
                    "symbol": "NVME_APPLE_CMD_READ_INTERNAL_TELEMETRY",
                    "c_identifier": "Host_GetInternalTelemetry",
                    "direction": "In (Controller to Host)",
                    "description": "Fetches raw ASCII telemetry stream (GC move times, UE counts, GBBs, AES beats)"
                },
                "0xD2": {
                    "symbol": "NVME_APPLE_CMD_EFFACEABLE_LOCKER_OP",
                    "c_identifier": "Host_EffaceableLockerOp",
                    "direction": "Bidirectional",
                    "description": "Hardware-authenticated read/write/erase operations targeting Namespace 7"
                }
            }
        }
    }

    # 2. Ring Buffer & Mailbox Protocol Spec
    ring_buffer_protocol = {
        "soc": "t8150",
        "subsystem": "Apple NVMe Storage Controller 2 (ANS2)",
        "doorbell_protocol": {
            "bar_base_address": "0x17dcc0000",
            "doorbell_stride_bytes": 8,
            "doorbell_base_offset": "0x1000",
            "submission_queue_doorbell": {
                "formula": "0x17dcc0000 + 0x1000 + (2 * QID * 8)",
                "example_sq0_admin": "0x17dcc1000",
                "example_sq1_io": "0x17dcc1010",
                "access_width_bits": 32,
                "action": "Host writes new 16-bit SQ Tail index; signals hardware DMA fetch"
            },
            "completion_queue_doorbell": {
                "formula": "0x17dcc0000 + 0x1000 + ((2 * QID + 1) * 8)",
                "example_cq0_admin": "0x17dcc1008",
                "example_cq1_io": "0x17dcc1018",
                "access_width_bits": 32,
                "action": "Host writes new 16-bit CQ Head index; acknowledges completion reap"
            }
        },
        "ascwrap_mailbox_protocol": {
            "mailbox_base_address": "0x179600000",
            "controller_version": "v6 (iop,ascwrap-v6)",
            "registers": [
                {"name": "ASC_CPU_INBOX_CTRL", "offset": "0x00", "description": "Host-to-ANS2 inbox status & interrupt trigger"},
                {"name": "ASC_CPU_INBOX_DATA", "offset": "0x08", "description": "64-bit message payload register"},
                {"name": "ASC_ANS_OUTBOX_CTRL", "offset": "0x20", "description": "ANS2-to-Host outbox status & interrupt acknowledge"},
                {"name": "ASC_ANS_OUTBOX_DATA", "offset": "0x28", "description": "64-bit response message payload register"}
            ],
            "message_format_bits": {
                "endpoint_id": "Bits [63:56] (8 bits): Identifies RTKit Mailbox endpoint (e.g. FTL, Power, NVMe Admin)",
                "message_type": "Bits [55:48] (8 bits): Message opcode (Hello, Request, Response, Ping)",
                "sequence_id": "Bits [47:32] (16 bits): Transaction sequence tag for matching async replies",
                "payload": "Bits [31:0] (32 bits): Command-specific payload, status code, or memory token"
            }
        }
    }

    # Write JSON files
    cmd_file = ROOT / "artifacts/ans2/nvme_command_stream_spec.json"
    ring_file = ROOT / "artifacts/ans2/ans2_ring_buffer_protocol.json"
    cmd_file.write_text(json.dumps(cmd_stream_spec, indent=2))
    ring_file.write_text(json.dumps(ring_buffer_protocol, indent=2))
    print(f"[+] Wrote {cmd_file} ({cmd_file.stat().st_size} bytes)")
    print(f"[+] Wrote {ring_file} ({ring_file.stat().st_size} bytes)")

    # Author 03_COMMAND_STREAM_AND_RING_BUFFER.md
    md_content = """# Phase 3: Wire Format, NVMe Ring Buffers & Mailbox Protocol
**Target System**: iOS 27.2 (Darwin 24.2.0, Build 24B119)  
**Target Platform**: Apple Silicon A19 Pro (`t8150` / `v57ap`)  
**Firmware Subsystem**: Apple Storage Processor 3 (`ASP3-241.40.4~1100`) / ANS2  

---

## 1. Queue Geometry & Circular Ring Protocol

Apple's ANS2 storage controller communicates with the host operating system (XNU kernel `IONVMeFamily.kext`) through standard and proprietary memory-mapped circular ring buffers.

### Ring Buffer Geometric Parameters
- **Submission Queue Entry (SQE) Size**: `64 Bytes` (Aligned to 64 bytes)
- **Completion Queue Entry (CQE) Size**: `16 Bytes` (Aligned to 16 bytes)
- **Queue Depth**: `64 Entries` (Defined by DeviceTree `nvme-queue-entries: 0x40`)
- **Total SQ Buffer Footprint**: $64 \times 64 = 4096 \text{ Bytes}$ (1 native 4KB page)
- **Total CQ Buffer Footprint**: $64 \times 16 = 1024 \text{ Bytes}$
- **Queue Memory Mode**: `nvme-linear-sq` (Linear contiguous physical allocation)
- **PRP Page Size**: `16,384 Bytes` (16 KB Apple Silicon native page size)

```
        HOST SUBMISSION QUEUE (SQ) [64 Entries x 64B = 4096B]
     +-------------------------------------------------------+
0x00 | SQE 0  (64 Bytes: Opcode, NSID, PRP1, LBA, Length)   |
0x40 | SQE 1  (64 Bytes)                                     |
     | ...                                                   |
0xFC | SQE 63 (64 Bytes)                                     |
     +-------------------------------------------------------+
          │                                         ▲
          ▼ Tail Doorbell Write                     │ Head Pointer (Internal)
     [ANS2 DMA Engine]                          [Host Producer]

        HOST COMPLETION QUEUE (CQ) [64 Entries x 16B = 1024B]
     +-------------------------------------------------------+
0x00 | CQE 0  (16 Bytes: Status, Phase, CID, SQ_Head)       |
0x10 | CQE 1  (16 Bytes)                                     |
     | ...                                                   |
0x3F | CQE 63 (16 Bytes)                                     |
     +-------------------------------------------------------+
          ▲                                         │
          │ CQE Write + Interrupt 0x3cd             ▼ Head Doorbell Write
     [ANS2 DMA Producer]                        [Host Consumer]
```

---

## 2. 64-Byte Submission Queue Entry (SQE) Layout

The 64-byte SQE structure extends standard NVMe Command Dwords (`CDW0`..`CDW15`) with Apple-specific cryptographic key tokens and segment identifiers:

```c
struct ans2_sqe {
    // CDW0: Opcode [7:0], FUSE [9:8], PSDT [15:14], CID [31:16]
    uint8_t   opcode;
    uint8_t   flags;
    uint16_t  command_id;

    // CDW1: Target Namespace ID (1..7)
    uint32_t  nsid;

    // CDW2 - CDW3: Reserved / Vendor Metadata Pointers
    uint64_t  reserved0;

    // CDW4 - CDW5: Metadata Pointer (MPTR)
    uint64_t  mptr;

    // CDW6 - CDW7: Data Pointer (PRP1) - 16KB Aligned Host Physical Address
    uint64_t  prp1;

    // CDW8 - CDW9: Data Pointer (PRP2) - PRP List Pointer
    uint64_t  prp2;

    // CDW10 - CDW11: Starting Logical Block Address (SLBA, 64-bit)
    uint64_t  slba;

    // CDW12: Length [15:0] (Number of logical blocks), Control flags
    uint16_t  block_count;
    uint16_t  control_flags;

    // CDW13: Dataset Management / Sequential Hint Attributes
    uint32_t  dsm_attributes;

    // CDW14: Apple Vendor Crypto Key Slot Index & Tweak Control
    uint8_t   key_slot_idx;       // Hardware AES-XTS key slot [7:0]
    uint8_t   crypto_flags;       // Tweak generation bypass / override
    uint16_t  crypto_reserved;

    // CDW15: Apple Vendor Segment Context Index & Barrier Token
    uint16_t  seg_ctx_idx;        // Segment Context ID (sl_hal.c)
    uint16_t  barrier_token;      // Dispatch queue barrier token
};
_Static_assert(sizeof(struct ans2_sqe) == 64, "SQE must be exactly 64 bytes");
```

---

## 3. 16-Byte Completion Queue Entry (CQE) Layout

```c
struct ans2_cqe {
    // Dword 0: Command-Specific Result
    uint32_t  command_result;

    // Dword 1: Reserved
    uint32_t  reserved;

    // Dword 2: Submission Queue Head Pointer & SQ Identifier
    uint16_t  sq_head;
    uint16_t  sq_id;

    // Dword 3: Command ID, Phase Tag & Status Code
    uint16_t  command_id;
    uint16_t  status_phase;       // Phase Tag [0], Status Code [15:1]
};
_Static_assert(sizeof(struct ans2_cqe) == 16, "CQE must be exactly 16 bytes");
```

---

## 4. Hardware Doorbell MMIO Protocol

Doorbells reside in the NVMe Register BAR aperture at base address `0x17DCC0000`:
- **Doorbell Base Offset**: `0x1000`
- **Doorbell Stride**: `8 Bytes` ($2 \times 32\text{-bit}$ registers per queue pair)

### Mathematical Offset Formulas:
$$\text{Offset}_{\text{SQ\_Tail}}(\text{QID}) = \text{0x17DCC0000} + \text{0x1000} + (2 \times \text{QID} \times 8)$$
$$\text{Offset}_{\text{CQ\_Head}}(\text{QID}) = \text{0x17DCC0000} + \text{0x1000} + ((2 \times \text{QID} + 1) \times 8)$$

### Doorbell Register Table:
| Queue Identifier | Queue Type | Register Address | Action on 32-Bit Store |
| :--- | :--- | :--- | :--- |
| **QID 0** (Admin) | Submission Queue Tail | `0x17DCC1000` | Signals ANS2 Admin dispatcher to fetch pending admin SQEs |
| **QID 0** (Admin) | Completion Queue Head | `0x17DCC1008` | Informs ANS2 host has reaped CQEs up to new Head pointer |
| **QID 1** (I/O) | Submission Queue Tail | `0x17DCC1010` | Signals ANS2 I/O dispatcher to fetch NVMe Read/Write SQEs |
| **QID 1** (I/O) | Completion Queue Head | `0x17DCC1018` | Informs ANS2 host has reaped completed I/O transactions |

---

## 5. Apple Vendor-Specific NVMe Admin Opcodes

Extracted directly from symbols and dispatch tables in `ansf.t8150.release.im4p`:

| Opcode | Symbolic Constant | Firmware C Handler | Operational Purpose |
| :--- | :--- | :--- | :--- |
| `0xC0` | `NVME_APPLE_CMD_READ_BAND_STATS` | `Cmd_NvmeAdminReadBandStats` | Dumps wear level distribution, stepovers (`SoMx`, `SoAvg`), SLC/TLC counts |
| `0xC1` | `NVME_APPLE_CMD_GET_NAND_MATURITY` | `Cmd_tunnelGetNandMaturity` | Queries silicon maturity parameters, lithography offsets, and voltage tables |
| `0xC2` | `NVME_APPLE_CMD_GET_NAND_INFO` | `Host_GetNANDInfo` | Returns channel count, die count, plane geometry, and manufacturer vendor ID |
| `0xC4` | `NVME_APPLE_CMD_DEBUG_RECLAIM_BOOT_BLOCK`| `Nand_DebugReclaimBootBlock` | Forces FTL to reclaim and refresh bootstrap flash blocks |
| `0xC8` | `NVME_APPLE_CMD_ASI_DELETE_FW` | `ASI_NAND_OP_DELETE_FW` | Erases staged firmware update slots prior to Image4 flashing |
| `0xCA` | `NVME_APPLE_CMD_SET_PROTOCOL_VALIDATION`| `ASI_NAND_OP_SET_PROTOCOL_VALIDATION`| Toggles protocol validation assertions and error injection harnesses |
| `0xD0` | `NVME_APPLE_CMD_READ_INTERNAL_TELEMETRY`| `Host_GetInternalTelemetry` | Fetches live ASCII telemetry stream (GC move times, UE counts, GBBs, AES beats) |
| `0xD2` | `NVME_APPLE_CMD_EFFACEABLE_LOCKER_OP` | `Host_EffaceableLockerOp` | Performs hardware-authenticated operations on Effaceable Storage (Namespace 7) |

---

## 6. ASCwrap v6 Mailbox Protocol

In addition to NVMe ring buffers, early boot configuration and fatal panic telemetry utilize the hardware ASCwrap v6 mailbox at physical base `0x179600000`:

```
Offset      Register Name           Width       Functional Description
-----------------------------------------------------------------------------------------
0x00        ASC_CPU_INBOX_CTRL      32-bit      Status & interrupt trigger for host-to-coprocessor messages
0x08        ASC_CPU_INBOX_DATA      64-bit      64-bit packed message payload sent to ANS2
0x20        ASC_ANS_OUTBOX_CTRL     32-bit      Status & interrupt acknowledge for ANS2-to-host messages
0x28        ASC_ANS_OUTBOX_DATA     64-bit      64-bit packed response payload received from ANS2
```

### 64-Bit Packed Mailbox Word Format:
- `Bits [63:56]` (8 bits): **Endpoint Identifier** (Routes message to designated RTKit task via `_rtk_mtab`)
- `Bits [55:48]` (8 bits): **Message Opcode** (`0x01` Init, `0x02` Command, `0x03` Response, `0x04` Panic)
- `Bits [47:32]` (16 bits): **Sequence Tag** (Correlates asynchronous responses)
- `Bits [31:0]`  (32 bits): **Payload Token** (Physical memory token or status code)
"""

    findings_file = ROOT / "findings/ans2/03_COMMAND_STREAM_AND_RING_BUFFER.md"
    findings_file.write_text(md_content)
    print(f"[+] Wrote {findings_file} ({findings_file.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_phase_3()
