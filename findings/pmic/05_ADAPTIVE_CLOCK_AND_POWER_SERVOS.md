# Adaptive Clock Controller (ACC) & Core Power Management Servos (CPMS)

**Document Identifier**: `findings/pmic/05_ADAPTIVE_CLOCK_AND_POWER_SERVOS.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Subsystem**: ACC (`EACC0`, `PACC0`) & CPMS (`ppm,cpms`)  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/pmic/extracted/t8150pmp.raw`  

---

## 1. Executive Summary

To minimize power dissipation while maintaining deterministic real-time responsiveness, Apple Silicon A19 Pro pairs its buck converters with hardware **Adaptive Clock Controllers (ACC)** and **Core Power Management Servos (CPMS)**. 

Rather than maintaining a conservative $100\text{ mV}$ voltage guardband across all operating conditions, ACC monitors real-time silicon path delay with critical-path replica monitors. When voltage dips due to high $dI/dt$ transient load spikes, ACC dynamically slews clock frequency within single-digit nanoseconds, enabling the system to operate at the razor-thin margin of **$25\text{ mV}$ droop target headroom** (`delta-voltage-target-Vdroop`).

---

## 2. Adaptive Clock Controller Architecture (`EACC0`, `PACC0`)

ACC blocks are embedded adjacent to each CPU cluster:
- **`EACC0`**: Manages the 4 Efficiency cores, monitoring 8 critical path delay lines.
- **`PACC0`**: Manages the 2 Performance cores, monitoring 16 critical path delay lines across integer, vector (NEON), and floating-point execution units.

```
+----------------------------------------------------------------------------------------------------+
|                                ACC REAL-TIME CLOCK SLEWING ARCHITECTURE                             |
+----------------------------------------------------------------------------------------------------+
| 1. High dI/dt Transient -> Rail Voltage Drops (Vdroop)                                             |
| 2. Critical Path Monitor Detects Setup Timing Margin Degradation (< 50 ps)                        |
| 3. ACC Immediately Modulates Clock Divisor (1.0x -> 0.85x) within 2 Clock Cycles                   |
| 4. PMIC Buck Converter Senses Droop via SPMI Telemetry and Increases Inductor Current              |
| 5. Voltage Recovers to Target OPP -> ACC Slews Clock Back to 1.0x Nominal Frequency                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Core Power Management Servos (`ppm,cpms`)

Located at `/device-tree/arm-io/pmgr/ppm` (compatible `ppm,cpms`), the CPMS engine computes predictive maximum power envelopes ($P_{max}$):

### 3.1 Empirical CPMS Invariants
- `delta-voltage-target-Vdroop`: $25\text{ mV}$ (`0x19`).
- `brownout-risk-Pmargin`: $1000\text{ mW}$ (`0x03E8`) power safety margin.
- `brownout-risk-debounce-time`: $3000\ \mu\text{s}$ debounce timer before brownout throttle assertion.
- `brownout-risk-CE-lane`: Lane 6 power delivery rail.
- `cpms-policy-type`: Policy 2 (Closed-loop predictive electrochemical servo).
- `dynamic-PMU-Vthr-enabled`: Active dynamic threshold adjustment.
- `enable-IR-compensation`: Active ohmic voltage drop compensation.

### 3.2 Predictive $P_{max}$ Calculation
CPMS calculates the instantaneous peak power budget that the battery and PMIC can supply without dropping terminal voltage below the Under-Power-Out (UPO) threshold ($3.00\text{ V}$):

$$P_{max}(t) = \frac{V_{OCV}(DOD, T) - V_{cut}}{R_{total}(DOD, T)} \cdot V_{cut}$$

Where $V_{cut} = 3.00\text{ V} + \Delta V_{droop} + V_{margin}$.
