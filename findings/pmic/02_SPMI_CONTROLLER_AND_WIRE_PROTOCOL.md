# MIPI SPMI v2.0 Controller Architecture & Command Queue Wire Protocol

**Document Identifier**: `findings/pmic/02_SPMI_CONTROLLER_AND_WIRE_PROTOCOL.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Driver Subsystem**: `com.apple.driver.AppleSPMI` (Generation 4)  
**Standard**: MIPI Alliance Specification for System Power Management Interface (SPMI) Version 2.0  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/kernel/kernelcache.release.raw`  

---

## 1. Executive Summary

Apple Silicon A19 Pro implements five discrete Generation 4 MIPI SPMI v2.0 master controllers partitioned across the Application Processor (`nub-spmi*`) and Always-On Processor (`aop-spmi*`) power planes. Each controller features a tri-aperture memory-mapped I/O (MMIO) architecture comprising:
1. **Aperture 0 (`+0x14000` / `+0x08000`, 16 KB)**: Command ring queue submission, response queues, and FIFO controls.
2. **Aperture 1 (`+0x04000`, 16 KB)**: Physical bus clocking, timing division, and arbitration controllers.
3. **Aperture 2 (`+0x00000`, 16 KB)**: Interrupt Event Service (`spmiIES`) and Hardware Fault Event Service (`spmiFaultIES`).

Each controller drives a 256-slot, 16-byte packed ring queue enabling asynchronous, zero-copy burst command dispatch at bus clock frequencies of $19.2\text{ MHz}$, $24.0\text{ MHz}$, or $26.0\text{ MHz}$.

---

## 2. Hardware Controller Topologies & Memory Mappings

```
+---------------------------------------------------------------------------------------------------------------+
|                                A19 PRO SPMI CONTROLLER HARDWARE TOPOLOGY                                      |
+---------------------------------------------------------------------------------------------------------------+
| Controller  | Domain | MMIO Aperture 0 | MMIO Aperture 1 | MMIO Aperture 2 | IRQ | Slaves & Roles                 |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
| nub-spmi0   | AP     | 0x00F8714000    | 0x00F8704000    | 0x00F8700000    | 256 | 0x0E: Brooklands Primary PMIC  |
|             |        |                 |                 |                 |     | 0x0E: BTM Fuel Gauge Submodule |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
| nub-spmi1   | AP     | 0x00F8614000    | 0x00F8604000    | 0x00F8600000    | 256 | 0x0C: Shamisen RF/Cellular PMIC|
|             |        |                 |                 |                 |     | 0x0F: Stonehenge Camera PMIC   |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
| aop-spmi0   | AOP    | 0x0100914000    | 0x0100904000    | 0x0100900000    | 256 | 0x02: Stockholm NFC Primary    |
|             |        |                 |                 |                 |     | 0x03: Hammerfest NFC Secondary |
|             |        |                 |                 |                 |     | 0x04: WLAN-HEB Power Hub       |
|             |        |                 |                 |                 |     | 0x05: Baseband-HEB Power Hub   |
|             |        |                 |                 |                 |     | 0x06: UWB0 Transceiver         |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
| aop-spmi1   | AOP    | 0x0100B14000    | 0x0100B04000    | 0x0100B00000    | 256 | 0x07: Secondary UWB Controller |
|             |        |                 |                 |                 |     | 0x08: WLAN-IDC Coexistence     |
|             |        |                 |                 |                 |     | 0x09: Baseband-IDC Coexistence |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
| nub-spmi-a0 | HPM    | 0x00F8908000    | 0x00F8904000    | 0x00F8900000    | 256 | 0x0A: USB-C CBTL1702 PD PMIC   |
+-------------+--------+-----------------+-----------------+-----------------+-----+--------------------------------+
```

---

## 3. MIPI SPMI Command Frame Wire Format

The physical interface uses a two-wire bus: bidirectional data line (`SDATA`) and clock line (`SCLK`). Every transmission begins with a Sequence Start Condition (SSC) and terminates with a Bus Parking cycle.

### 3.1 Frame Sequence
```
+-----+----------+--------------+------------------+------------------+--------+----------+----------+
| SSC | Slave ID | Command Byte | Address [15:8]   | Address [7:0]    | Data N | Parity P | ACK/NACK |
|     | (4 bits) | (8 bits)     | (8 bits, Ext)    | (8 bits, Ext)    | (8 b)  | (1 bit)  | (1 bit)  |
+-----+----------+--------------+------------------+------------------+--------+----------+----------+
```

### 3.2 Command Opcodes
1. **`REG_0_WR` (`0x00`)**: Zero-payload write. Writes zero to register `0x00` of the addressed slave. Used for quick interrupt acknowledge and state clear.
2. **`REG_WR` (`0x10`)**: Standard Register Write. 8-bit address, 1-byte data payload.
3. **`REG_RD` (`0x20`)**: Standard Register Read. 8-bit address, 1-byte response.
4. **`EXT_REG_WR` (`0x30`)**: Extended Register Write. 16-bit address, burst length from 1 to 16 bytes.
5. **`EXT_REG_RD` (`0x38`)**: Extended Register Read. 16-bit address, burst length from 1 to 16 bytes.
6. **`EXT_REG_WRL` (`0x3A`)**: Extended Register Write Long. 16-bit address, burst length from 1 to 32 bytes.
7. **`EXT_REG_RDL` (`0x3E`)**: Extended Register Read Long. 16-bit address, burst length from 1 to 32 bytes.

### 3.3 Parity & Acknowledgment Rules
- **Odd Parity**: Each byte transmitted (Command, Address, Data) is accompanied by 1 parity bit ensuring the total count of binary 1s is odd.
- **ACK/NACK Bit**: Slaves pull `SDATA` low during the ACK cycle to confirm receipt. If `SDATA` remains floating high, a NACK condition is registered.

---

## 4. Hardware Ring Queue Geometry (256 Slots, 16 Bytes Each)

The command ring buffer resides in physical DRAM mapped directly to Aperture 0:
```c
typedef struct __attribute__((packed)) {
    uint16_t target_address;      /* [15:0]: Target Register Address (0x0000..0xFFFF) */
    uint8_t  byte_count_minus1:4; /* [19:16]: Byte Count BC (0=1B, 15=16B) */
    uint8_t  priority:2;          /* [21:20]: Priority (0=Low, 1=Med, 2=High, 3=Critical) */
    uint8_t  reserved0:2;
    uint8_t  opcode:4;            /* [27:24]: Command Opcode */
    uint8_t  slave_id:4;          /* [31:28]: SPMI Slave ID */

    uint32_t payload_low;         /* Bytes 0..3 payload data */
    uint32_t payload_high;        /* Bytes 4..7 payload data */

    uint8_t  flags;               /* Bit 0: Valid, Bit 1: IRQ En, Bit 2: Read/Write */
    uint8_t  token;               /* Request tracking token */
    uint16_t hardware_status;     /* Completion result status populated by controller */
} spmi_command_descriptor_t;
```

### 4.1 Queue Index Servicing
- **Producer Pointer (`SPMI_REG_CMD_PROD_IDX`, `+0x0010`)**: Written by software driver when appending new commands.
- **Consumer Pointer (`SPMI_REG_CMD_CONS_IDX`, `+0x0014`)**: Read by software to track hardware execution progress.
- **Ring Wrap**: Indices increment modulo 256. When `PROD == CONS`, the ring is empty; when `(PROD + 1) % 256 == CONS`, the queue is full.

---

## 5. Bus Protocol Errors & Interrupt Event Service (`spmiIES`)

The controller isolates and logs physical wire faults in Aperture 2 (`SPMI_REG_IES_STATUS`, `+0x0000`):
- `BusPr-CmdPrty-BOM`: Command byte parity failed at Beginning of Message.
- `BusPr-CmdPrty-NoBOM`: Command parity failed mid-frame during multi-byte burst.
- `BusPr-AdrPrty`: 16-bit address field parity check error.
- `BusPr-DatPrty`: Data payload byte parity violation.
- `BusPr-CmdUnrecog`: Slave returned unrecognized command indication.
- `BusPr-ExtColl`: Bus arbitration collision detected during multi-master contention.
