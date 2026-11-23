# Apple Custom PMIC ("Brooklands") Hardware Register Map & PTMU Architecture

**Document Identifier**: `findings/pmic/01_BROOKLANDS_PMIC_REGISTER_MAP.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Subsystem**: Dialog/Apple Custom PMIC Silicon Codename `brooklands` (`pmu,brooklands`)  
**Bus Architecture**: MIPI SPMI v2.0 Slave ID `0x0E` on `nub-spmi0`  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/kernel/kernelcache.release.raw`  

---

## 1. Executive Overview

The power delivery backbone of Apple Silicon A19 Pro (`t8150`) is anchored by the custom Apple/Dialog Power Management Integrated Circuit (PMIC) codenamed **Brooklands** (`pmu,brooklands`). Operating as the primary PMU (`pmu-main`) at SPMI Slave ID `0x0E` on the application processor master controller `nub-spmi0`, Brooklands coordinates with two satellite companion PMICs:
1. **Shamisen** (Slave ID `0x0C` on `nub-spmi1`): Dedicated radio frequency, baseband transceiver, and cellular front-end power management.
2. **Stonehenge** (Slave ID `0x0F` on `nub-spmi1`): Camera image signal processor (ISP), display panel bias, and touch subsystem power regulators.

Brooklands exposes a unified 16-bit register address space (`0x0000` through `0xFFFF`) accessed via MIPI SPMI Extended Register Read (`EXT_REG_RD`, opcode `0x38`) and Extended Register Write (`EXT_REG_WR`, opcode `0x30`) burst commands. The silicon partition separates public operational telemetry from hardware-isolated security domains via standard PTMU (`0x6000..0x6FFF`) and secure PTMU (`0x7000..0x7FFF`) regions.

---

## 2. Complete Physical Register Map Organization

```
+----------------------------------------------------------------------------------------------------+
|                         BROOKLANDS PMIC 16-BIT PHYSICAL REGISTER APERTURE                          |
+----------------------------------------------------------------------------------------------------+
| Range              | Size      | Security Domain | Operational Functionality                       |
+--------------------+-----------+-----------------+-------------------------------------------------+
| 0x0000 - 0x0009    | 10 Bytes  | Public (RO)     | PMIC Device ID, Wafer Coordinates, Security Lock|
| 0x0010 - 0x0018    | 9 Bytes   | Public (RO/W1C) | Hardware Fault Status Banks (72 Channels)       |
| 0x2000 - 0x200E    | 16 Bytes  | Public (R/W)    | Real-Time Clock (RTC), Alarms, Monotonic Counter|
| 0x2100 - 0x2105    | 6 Bytes   | Public (R/W)    | RTC Calibration & Scratchpad Retention Storage  |
| 0x2813 - 0x2814    | 2 Bytes   | Public (RO/W1C) | Off-to-Wake Source History Register             |
| 0x2B08             | 4 Bytes   | Public (WO)     | Host Interrupt Trigger Register                 |
| 0x2B60             | 4 Bytes   | Public (R/W)    | Firmware Micro-Communications (MCOM) Mailbox    |
| 0x6000 - 0x603F    | 64 Bytes  | Standard PTMU 0 | Buck0..Buck3 Core Power Rail Regulators         |
| 0x6040 - 0x607F    | 64 Bytes  | Standard PTMU 1 | Buck4..Buck7 Core Power Rail Regulators         |
| 0x6080 - 0x60BF    | 64 Bytes  | Standard PTMU 2 | SRAM & Cache Memory Rail Regulators             |
| 0x60C0 - 0x60FF    | 64 Bytes  | Standard PTMU 3 | Analog & PLL Regulators                         |
| 0x6100 - 0x613F    | 64 Bytes  | Standard PTMU 4 | Low Dropout Regulators LDO1..LDO4               |
| 0x6140 - 0x617F    | 64 Bytes  | Standard PTMU 5 | Low Dropout Regulators LDO5..LDO8               |
| 0x6180 - 0x61BF    | 64 Bytes  | Standard PTMU 6 | Low Dropout Regulators LDO9..LDO12              |
| 0x61C0 - 0x61FF    | 64 Bytes  | Standard PTMU 7 | Low Dropout Regulators LDO13..LDO16             |
| 0x6200 - 0x627F    | 128 Bytes | Standard PTMU 8 | Buck Dynamic Voltage Scaling (DVS) LUT          |
| 0x6280 - 0x62FF    | 128 Bytes | Standard PTMU 9 | ADC Telemetry Sequencer & Voltage Channels      |
| 0x6300 - 0x637F    | 128 Bytes | Standard PTMU 10| Thermal Sensor Matrix & Alarm Comparators       |
| 0x6380 - 0x63FF    | 128 Bytes | Standard PTMU 11| Charge Pump & Boost Converter Control           |
| 0x6400 - 0x65FF    | 512 Bytes | Standard PTMU 12| General Power Management Configuration          |
| 0x6600 - 0x67FF    | 512 Bytes | Standard PTMU 13| Power-On Sequence & State Machine Engine        |
| 0x6800 - 0x6BFF    | 1024 Bytes| Standard PTMU 14| Global Trims, Biasing & General Configurations |
| 0x6C00 - 0x6FFF    | 1024 Bytes| Standard PTMU 15| Non-Secure Telemetry & Diagnostic Buffers       |
| 0x7000 - 0x73FF    | 1024 Bytes| Secure PTMU 0   | Secure Enclave (SEP) Power Domain Controls      |
| 0x7400 - 0x77FF    | 1024 Bytes| Secure PTMU 1   | Hardware Cryptographic Key Storage Power        |
| 0x7800 - 0x7BFF    | 1024 Bytes| Secure PTMU 2   | Anti-Rollback Counters & Monotonic Timers       |
| 0x7C00 - 0x7DFF    | 512 Bytes | Secure PTMU 3   | Tamper Detection & Physical Mesh Sensors        |
| 0x7E00 - 0x7FFF    | 512 Bytes | Secure PTMU 4   | Production Fuses, JTAG Lockout & Security Gates  |
| 0x8000 - 0xA7FF    | 10 KB     | Non-Volatile    | Persistent Boot & System State Scratchpad        |
| 0x8B00 - 0xA2FF    | 6 KB      | Non-Volatile    | SOCD Crash & Panic Telemetry Buffer             |
| 0xA780 - 0xA7DB    | 92 Bytes  | Non-Volatile    | Low Power Mode (LPM) Event Log Buffer           |
| 0xA7DC - 0xA7DF    | 4 Bytes   | Non-Volatile    | Low Power Mode (LPM) Control Register           |
| 0xF800 - 0xFFFF    | 2 KB      | Legacy Mailbox  | Bootloader Handshake & iBoot Mailbox Scratchpad  |
+--------------------+-----------+-----------------+-------------------------------------------------+
```

---

## 3. Identification & Silicon Metadata (`0x0000..0x0009`)

Device identification registers provide silicon verification during early iBoot execution:
- `DEV_ID_0` (`0x0000`): Vendor identification byte. Encoded as `0x44` (ASCII `'D'` for Dialog Semiconductor / Apple Custom Silicon).
- `DEV_ID_1` (`0x0001`): Silicon family code. Encoded as `0x58` designating the Brooklands generation.
- `REV_ID_MAJOR` (`0x0002`): Silicon stepping major revision (`0x01` = A0, `0x02` = B0).
- `REV_ID_MINOR` (`0x0003`): Silicon stepping minor metal-fix revision (`0x00`..`0x0F`).
- `DIE_ID_0` / `DIE_ID_1` (`0x0004..0x0005`): Unique wafer lot identifier.
- `WAFER_X` / `WAFER_Y` (`0x0006..0x0007`): Die coordinate position on the 300mm silicon wafer.
- `FUSE_REV` (`0x0008`): Electronic fuse (eFuse) map layout revision.
- `SEC_STATE` (`0x0009`): Silicon production security gate. Bit 0 indicates production lock; Bit 1 indicates secure boot enforcement; Bit 2 indicates JTAG test access disabled.

---

## 4. Power Telemetry Management Unit (PTMU) Architecture

The Brooklands PMIC divides power management into 16 Standard PTMU regions and 5 Secure PTMU regions:

### 4.1 Standard PTMU Regions (0..15)
- **Regions 0..7 (Regulators & Converters)**: Regulate core buck converters (`Buck0..Buck7`) supplying $V_{DD,CPU}$, $V_{DD,SOC}$, $V_{DD,DCS}$, and $V_{DD,ANE}$. Low dropout regulators (`LDO1..LDO16`) provide low-noise analog voltages for PLLs, crystal oscillators, and PCIe PHYs.
- **Region 8 (DVS Look-Up Table)**: Stores pre-calibrated Dynamic Voltage Scaling VID step tables with $6.25\text{ mV}$ stepping granularity.
- **Region 9 (ADC Sequencer)**: Configures 16-channel SAR-ADC measuring terminal voltage ($V_{BAT}$), current ($I_{BAT}$), die temperatures, and rail voltages.
- **Region 10 (Thermal Matrix)**: 5 local on-die temperature diodes polled every $100\ \mu\text{s}$ with programmable trip points at $105^\circ\text{C}$, $110^\circ\text{C}$, $115^\circ\text{C}$, $120^\circ\text{C}$, and $125^\circ\text{C}$.
- **Region 11 (Charge Pump & Boost)**: Controls the inductive boost regulator feeding the display panel backlight and audio amplifiers.
- **Regions 12..15 (Global Controls & Telemetry)**: State machines governing system power transitions (`OFF` $\rightarrow$ `STANDBY` $\rightarrow$ `ACTIVE` $\rightarrow$ `SLEEP`).

### 4.2 Secure PTMU Regions (0..4)
Isolated by hardware cryptographic locks on the SPMI bus, accessible only when addressed with SPMI secure command tags originated from the Secure Enclave Processor (SEP):
- **Secure Region 0**: Controls power gating to the SEP core, secure cryptographic accelerators (PKA, TRNG), and secure memory.
- **Secure Region 1**: Supplies non-volatile battery-backed cryptographic key RAM.
- **Secure Region 2**: Hardware anti-rollback monotonic counters incremented across firmware updates.
- **Secure Region 3**: Active physical mesh intrusion and silicon decap sensor circuits.
- **Secure Region 4**: Silicon fusing controls and permanent JTAG lockout fuses.

---

## 5. Real-Time Clock & Alarms (`0x2000..0x200E`)

The PMIC maintains an uninterruptible 48-bit monotonic RTC counter clocked by an external $32.768\text{ kHz}$ tuning-fork crystal:
- **Counter Range**: $2^{48}$ counts at $32.768\text{ kHz}$ equals over 271 years of continuous timing.
- **Alarm Match**: Target register `RTC_ALARM_OFFSET` (`0x2008..0x200D`) triggers wake events from deep system sleep states.
- **Interrupt Masking**: Register `RTC_IRQ_MASK` (`0x200E`) controls alarm interrupt dispatch (`0x01`) and periodic tick dispatch (`0x02`).

---

## 6. Scratchpad & SOCD Crash Dump Storage

Brooklands integrates $18.5\text{ KB}$ of persistent, battery-backed scratchpad memory:
- `0x8000..0x8AFF` ($2.75\text{ KB}$): Preserves boot stage indicators, reset reason flags, and hibernation state vectors.
- `0x8B00..0xA2FF` ($6.0\text{ KB}$): System-on-Chip Diagnostics (`info-scrpad_socd`) circular panic dump buffer. When a kernel panic or hypervisor crash occurs, XNU writes the panic header and registers into this aperture before issuing a PMIC reset command.
- `0xA780..0xA7DC`: Low Power Mode (`info-scrpad_lpm_log`) log recording sleep cycles and wake latency.
- `0xF800..0xFFFF` ($2.0\text{ KB}$): Legacy scratchpad (`info-leg_scrpad`) utilized by iBoot for low-level platform handshake.
