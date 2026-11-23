# DVFS Voltage Rail Engine, CLPC v3 & PMP Coprocessor Dissection

**Document Identifier**: `findings/pmic/04_DVFS_VOLTAGE_RAILS_AND_CLPC_ENGINE.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Driver Subsystem**: `com.apple.driver.AppleT8150CLPC`, `com.apple.driver.AppleT8150PMGR`, `ApplePMGR`  
**Coprocessor Firmware**: `t8150pmp.raw` (Platform Management Processor RTKit)  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/pmic/extracted/t8150pmp.raw`  

---

## 1. Executive Summary

Dynamic Voltage and Frequency Scaling (DVFS) on the A19 Pro is orchestrated through a tripartite hierarchy:
1. **The Host Kernel Driver (`AppleT8150CLPC`)**: Calculates sustainable power limits (SPL), CPU workload metrics, and thread migration heuristics at $4\text{ ms}$ sampling intervals.
2. **The Hardware Power Manager (`ApplePMGR`)**: Comprises 51 MMIO apertures interfacing with 15 discrete performance domains.
3. **The Platform Management Processor (`t8150pmp`)**: An autonomous 64-bit ARM64 RTKit microcontroller running on-chip microcode that executes high-frequency fast die control loops at $100\text{ kHz}$ ($10\ \mu\text{s}$ response) to counter voltage droops ($V_{droop}$) and manage long-term reliability aging ($V_{LTS}$).

---

## 2. Voltage Rails & Performance Domains

The SoC power plane partitions into 8 primary buck-regulated rails:

```
+----------------------------------------------------------------------------------------------------+
|                                A19 PRO DVFS VOLTAGE RAIL GEOMETRY                                  |
+----------------------------------------------------------------------------------------------------+
| Rail Identifier     | PMGR Domain | Nominal Range    | Step Size | Step Delay | Primary Regulator  |
+---------------------+-------------+------------------+-----------+------------+--------------------+
| kVoltageRailECPU    | 1 (ECPU)    | 600 - 1150 mV    | 6.25 mV   | 500 us     | PMIC Buck 0/1      |
| kVoltageRailPCPU    | 3 (PCPU)    | 625 - 1280 mV    | 6.25 mV   | 500 us     | PMIC Buck 2/3      |
| kVoltageRailSOC     | 0 (SOC)     | 650 - 950 mV     | 12.5 mV   | 250 us     | PMIC Buck 4        |
| kVoltageRailDCS     | 2 (DCS)     | 600 - 900 mV     | 12.5 mV   | 250 us     | PMIC Buck 5        |
| kVoltageRailANE     | 4 (ANE)     | 650 - 1100 mV    | 6.25 mV   | 350 us     | PMIC Buck 6        |
| kVoltageRailAVE     | 5 (AVE)     | 650 - 1050 mV    | 12.5 mV   | 300 us     | PMIC Buck 7        |
| kVoltageRailDISP    | 6 (DISP)    | 700 - 1000 mV    | 12.5 mV   | 200 us     | PMIC Buck 8        |
| kVoltageRailAGX     | 8 (AGX)     | 600 - 1200 mV    | 6.25 mV   | 400 us     | Multi-Phase External|
+---------------------+-------------+------------------+-----------+------------+--------------------+
```

### 2.1 PMGR 15 Performance Domains
- Domain 0: `SOC` (Fabric, peripherals, always-on logic)
- Domain 1: `ECPU` (4x Efficiency cores)
- Domain 2: `DCS` (Dynamic Memory Controller Subsystem)
- Domain 3: `PCPU` (2x Performance cores)
- Domain 4: `ANE` (Neural Engine)
- Domain 5: `AVE` (Video Encoder 2)
- Domain 6: `DISP` (Display Pipe)
- Domains 7..13: `PMP-SOC`, `PMP-FAB0..3`, `PMP-DCS`, `PMP-AVE` (Coprocessor-managed domains)
- Domain 14: `PERF-API` (UserClient telemetry hook)

---

## 3. CPU Low Power Controller (CLPC v3) Engine

CLPC v3 (`AppleCLPC-1794.40.23.0.1`) monitors performance counters and dispatches OPP transitions:

### 3.1 Operating Performance Points (OPPs)
- **ECPU OPPs**: 6 states from $600\text{ MHz}$ ($625\text{ mV}$) to $2700\text{ MHz}$ ($1020\text{ mV}$).
- **PCPU OPPs**: 6 states from $800\text{ MHz}$ ($650\text{ mV}$) to $4050\text{ MHz}$ ($1220\text{ mV}$).

### 3.2 Dynamic Control Constants
- `sampling-interval-ms`: $4\text{ ms}$ sampling window.
- `thermal-interval-ms`: $12\text{ ms}$ thermal averaging period.
- `cpu-perf-cnt-filter-tc-up`: 10 cycles (rapid ramp up).
- `cpu-perf-cnt-filter-tc-down`: 10 cycles.
- `cpu-e-step-down-delay-us`: $500\ \mu\text{s}$ delay during downward voltage transitions to prevent inductor ringing.
- `pkg-sustainable-power-target`: $235,929\ \mu\text{W}$ ($235.9\text{ W}$ normalized burst limit).

---

## 4. Platform Management Processor (`t8150pmp`) Firmware

Extracted from `Firmware/pmp/t8150pmp.im4p` ($643,072\text{ bytes}$ Mach-O `MH_PRELOAD`):
```
+----------------------------------------------------------------------------------------------------+
|                         PMP FIRMWARE VIRTUAL MEMORY LAYOUT (MH_PRELOAD)                            |
+----------------------------------------------------------------------------------------------------+
| Segment     | VM Address         | VM Size     | Protection | Purpose                              |
+-------------+--------------------+-------------+------------+--------------------------------------+
| __TEXT      | 0x0000000001000000 | 0x00033000  | r-x        | Microcode, IRQ vectors, cstring      |
| __DATA      | 0x0000000001033000 | 0x0005E000  | rw-        | RTKit boot stacks, page tables, tunables|
| __ETEXT     | 0x00000000010A0000 | 0x0000B000  | r-x        | Fast Die Control Loop micro-engine   |
+-------------+--------------------+-------------+------------+--------------------------------------+
```

### 4.1 Fast Die Control Loop (`fast-die-ctrl-loop`)
PMP executes an autonomous closed-loop voltage servo sampling on-die telemetry diodes at $100\text{ kHz}$. When a sudden current surge occurs ($dI/dt > 10\text{ A}/\mu\text{s}$), the Fast Die controller modulates the clock divisor on the Adaptive Clock Controller (`PACC0`) to prevent rail collapse while the PMIC buck converters ramp current.

### 4.2 Long-Term Reliability & Aging (LTS Engine)
`lts-voltage` tracks Time-Dependent Dielectric Breakdown (TDDB) and Hot Carrier Injection (HCI). PMP increases target voltages by $12.5\text{ mV}$ per operational year to compensate for transistor threshold voltage shifts.
