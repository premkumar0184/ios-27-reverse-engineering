# PMIC Hardware Fault Telemetry & Off-to-Wake Vector Dissection

**Document Identifier**: `findings/pmic/03_HARDWARE_FAULT_AND_WAKEUP_CHANNELS.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Subsystem**: Brooklands PMIC Fault Management & Cold Boot Wakeup Engine  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/kernel/kernelcache.release.raw`  

---

## 1. Executive Summary

The Brooklands PMIC continuously monitors system electrical, thermal, and protocol invariants across **72 hardware fault channels** organized into nine 8-bit status banks (`0x0010..0x0018`). In the event of an electrical excursion (e.g. $V_{DD,MAIN}$ collapse) or catastrophic thermal runaway, hardware comparators trigger autonomous power-down sequences within $10\ \mu\text{s}$, latching the fault cause into non-volatile registers before rail collapse.

Additionally, the PMIC maintains a 15-channel **Off-to-Wake Source (O2WS)** vector register (`0x2813..0x2814`) capturing the exact physical or logical event responsible for booting the SoC from an unpowered (`OFF`) state.

---

## 2. The 72 PMIC Hardware Fault Channels

```
+----------------------------------------------------------------------------------------------------+
|                         BROOKLANDS PMIC 72 HARDWARE FAULT CHANNELS                                 |
+----------------------------------------------------------------------------------------------------+
| Bank | Reg    | Bit | Channel Identifier             | Category       | Tripping Condition         |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 0    | 0x0010 | 3   | uv,vddmain_uvlo                | Voltage        | VDD_MAIN < 3.00 V          |
| 0    | 0x0010 | 5   | uv,vdd_boost_uvlo              | Voltage        | VDD_BOOST < 4.20 V         |
| 0    | 0x0010 | 6   | ov,vdd_boost_ovlo              | Voltage        | VDD_BOOST > 5.50 V         |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 1    | 0x0011 | 0   | por                            | Reset          | Power-On Reset Circuit     |
| 1    | 0x0011 | 1   | rst                            | Reset          | External HW Reset Pin      |
| 1    | 0x0011 | 2   | ot,overtemp                    | Thermal        | PMIC Global Die > 125 C    |
| 1    | 0x0011 | 3   | ov,vddmain_ovlo                | Voltage        | VDD_MAIN > 4.85 V          |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 2    | 0x0012 | 0   | btn_rst,two_finger_rst         | User Input     | Vol-Down + Side Key Force  |
| 2    | 0x0012 | 1   | crash,crash0_in                | Crash          | AP Crash0 Pin Asserted     |
| 2    | 0x0012 | 2   | btn_rst,btn_seq_reset          | User Input     | Tri-Button DFU Sequence    |
| 2    | 0x0012 | 3   | btn_rst,sec_btn_seq            | User Input     | Secondary Button Combo     |
| 2    | 0x0012 | 4   | wdog,reset_in_1                | Watchdog       | Reset-In 1 AP Wdog Expired |
| 2    | 0x0012 | 5   | dbg_rst,reset_in_2             | Debug          | JTAG/SWD Debugger Reset    |
| 2    | 0x0012 | 6   | sochot,reset_in_3              | Thermal        | SoCHot Hardware Emergency  |
| 2    | 0x0012 | 7   | rst_in,reset_in_1_deassert     | Reset          | Reset-In 1 Deassert Detect |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 3    | 0x0013 | 0   | spmi,spmi_fault                | Bus Protocol   | SPMI Parity/Framing Error  |
| 3    | 0x0013 | 1   | ntc_shdn                       | Thermal        | External NTC Pin Trip      |
| 3    | 0x0013 | 2   | timeout,dblclick_timeout       | User Input     | Side Button Double Click   |
| 3    | 0x0013 | 4   | timeout,watchdog_timeout       | Watchdog       | Internal PMIC Safety Timer |
| 3    | 0x0013 | 5   | sstate,button_dfu_recover      | Recovery       | Boot into DFU Recovery     |
| 3    | 0x0013 | 6   | sstate,dfu_btn_seq_reset       | Recovery       | DFU Button Trigger Reset   |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 4    | 0x0014 | 3   | otp_crc                        | Security       | eFuse Hash Mismatch        |
| 4    | 0x0014 | 4   | sgpio                          | Hardware GPIO  | Serial GPIO Bus Fault      |
| 4    | 0x0014 | 5   | btn_shdn                       | User Input     | Long-Press Button Turn-Off |
| 4    | 0x0014 | 6   | xtal_wdog_expiry               | Clock          | 32.768 kHz Quartz Loss     |
| 4    | 0x0014 | 7   | mfsm_sgpio                     | Hardware FSM   | Master FSM Handshake Fail  |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 5    | 0x0015 | 0   | crash,hyp_fw_crash             | Firmware       | SPTM / Hyp Firmware Panic  |
| 5    | 0x0015 | 1   | crash,hyp_hw_crash             | Hardware       | Hyp Memory Access Violation|
| 5    | 0x0015 | 2   | timeout,target_st_wdog_timeout | Watchdog       | Power State Change Timeout |
| 5    | 0x0015 | 3   | timeout,wdog_fw_timeout        | Firmware       | Kernel Heartbeat Lost      |
| 5    | 0x0015 | 4   | emerg_shdn                     | Critical       | Immediate Rail Kill Command|
| 5    | 0x0015 | 2*  | target_off_restart             | State Engine   | Orderly Restart Transition |
| 5    | 0x0015 | 3*  | target_off_shutdown            | State Engine   | Orderly Power-Off Done     |
| 5    | 0x0015 | 4*  | target_off_conflict            | State Engine   | Simultaneous On/Off Request|
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 6    | 0x0016 | 0   | ot,tdie_overtemp_idx0          | Thermal Diode  | Core Diode 0 > 105 C       |
| 6    | 0x0016 | 1   | ot,tdie_overtemp_idx1          | Thermal Diode  | Core Diode 1 > 110 C       |
| 6    | 0x0016 | 2   | ot,tdie_overtemp_idx2          | Thermal Diode  | Core Diode 2 > 115 C       |
| 6    | 0x0016 | 3   | ot,tdie_overtemp_idx3          | Thermal Diode  | Core Diode 3 > 120 C       |
| 6    | 0x0016 | 4   | ot,tdie_overtemp_idx4          | Thermal Diode  | Core Diode 4 > 125 C       |
| 6    | 0x0016 | 5   | ot,tdie_overtemp               | Thermal Trip   | Aggregate Die Thermal Trip |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 7    | 0x0017 | 0   | uv,cp_uvlo                     | Charge Pump    | Charge Pump < 3.20 V       |
| 7    | 0x0017 | 1   | ov,cp_ovlo                     | Charge Pump    | Charge Pump > 5.25 V       |
| 7    | 0x0017 | 2   | cp_wdog_expiry                 | Charge Pump    | CP Regulation Loop Stuck   |
+------+--------+-----+--------------------------------+----------------+----------------------------+
| 8    | 0x0018 | 4   | uv,ldo9_uv                     | Linear Reg     | LDO9 Voltage Collapse      |
| 8    | 0x0018 | 5   | ov,ldo9_ov                     | Linear Reg     | LDO9 Voltage Overshoot     |
| 8    | 0x0018 | 6   | uv,ldo9b_uv                    | Linear Reg     | LDO9b Voltage Collapse     |
| 8    | 0x0018 | 7   | ov,ldo9b_ov                    | Linear Reg     | LDO9b Voltage Overshoot    |
+------+--------+-----+--------------------------------+----------------+----------------------------+
```

---

## 3. The 15 Off-to-Wake Sources (O2WS)

The O2WS register (`0x2813..0x2814`) indicates what prompted the system power-up:

1. `fw_nonsec_off_wakeup_csr` (Bit 0): Software requested cold restart via CSR.
2. `gcb_off_wakeup` (Bit 1): Side power button asserted from deep off state.
3. `gcb_wakeup` (Bit 2): Side power button pressed during suspended standby.
4. `rtc_alarm_wakeup` (Bit 3): Monotonic 48-bit RTC comparator match.
5. `auto_wakeup` (Bit 4): External charger connected (VBUS detect on Type-C).
6. `gcb_crash_wakeup` (Bit 5): Hardware recovery wake following panic reboot.
7. `hw_wdog_wakeup` (Bit 6): Hardware watchdog triggered system reset.
8. `fw_wdog_wakeup` (Bit 7): Firmware watchdog heartbeat timeout recovery.
9. `dft_ctrl2_wakeup` (Bit 8): Factory manufacturing test fixture wake.
10. `target_state_wdog_timeout` (Bit 10): Power state machine stalled during sleep transition.
11. `fw_nonsec_off_wakeup_wdog` (Bit 13): Secondary firmware watchdog reboot.
12. `fw_req_auto_wakeup` (Bit 14): Scheduled system maintenance autonomous wake.

---

## 4. Kernel Driver Fault Handling (`AppleSPMIPMU`)

Upon cold boot or wake from sleep, `com.apple.driver.AppleSPMIPMU`:
1. Dispatches an SPMI burst read (`EXT_REG_RD`) to `0x0010` (9 bytes).
2. Evaluates the bitmask; if any non-zero fault bit is encountered, logs an IOKit power event and preserves the snapshot in the IORegistry plane under `IOPMUBootFaultLog`.
3. Reads `0x2813` (2 bytes) to populate `IOPMUBootWakeSource`.
4. Writes `0x00` across all banks to acknowledge and arm the comparators for subsequent events.
