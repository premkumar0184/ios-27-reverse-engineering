# Battery Security, Beads Cryptographic Authentication & USB-PD Architecture

**Document Identifier**: `findings/pmic/07_BATTERY_SECURITY_AND_CHARGER_SUBSYSTEM.md`  
**Target SoC**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Operating System**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Driver Subsystem**: `AppleGasGaugeBeadsUpdate`, `AppleSmartBatteryManagerEmbedded`, `spmi-hpm0-tnt`  
**Grounding Assets**: `artifacts/sptm/extracted/DeviceTree.v57ap.raw`, `artifacts/kernel/kernelcache.release.raw`  

---

## 1. Executive Summary

Battery safety and supply-chain integrity on the A19 Pro are enforced through the **Beads Cryptographic Authentication Subsystem** paired with an autonomous **USB-C Power Delivery Controller (`spmi-hpm0-tnt`)**.

The battery pack's Protection Circuit Module (PCM) integrates a dedicated security coprocessor (`Beads`) executing hardware-isolated ECDSA P-256 challenge-response verification against the Secure Enclave Processor (SEP). Non-genuine or uncertified batteries fail authentication, disabling maximum fast-charging profiles and logging non-authentic status flags in the platform diagnostics plane.

---

## 2. Beads Cryptographic Challenge-Response Protocol

The kernel driver `AppleGasGaugeBeadsUpdate` initiates battery authentication during early user-space initialization:

```
+----------------------------------------------------------------------------------------------------+
|                         BEADS CRYPTOGRAPHIC AUTHENTICATION PROTOCOL FLOW                           |
+----------------------------------------------------------------------------------------------------+
| Host / Secure Enclave (SEP)                          Battery Pack Beads Coprocessor                |
| ---------------------------                          ------------------------------                |
| 1. Generate 32-byte CSPRNG Nonce                                                                   |
| 2. Transmit Nonce via SPMI / HDQ ------------------> [0x01: AUTH_CHALLENGE (32 Bytes)]            |
|                                                      3. Hash: SHA256(Nonce || Serial || ChemID)   |
|                                                      4. Sign: ECDSA_P256(Hash, DevicePrivateKey)   |
| 5. Receive Signature & Cert <----------------------- [AUTH_RESPONSE: 64B (r,s) || 512B Cert]      |
| 6. Validate Certificate with Apple Battery Root CA                                                 |
| 7. Verify ECDSA Signature with Extracted Device PubKey                                             |
| 8. Authentication SUCCESS -> Unlock Battery Health & Fast Charge Telemetry                         |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 Packet Structures
- **Challenge Packet (37 Bytes)**: `Command ID (0x01)` + `32-byte Nonce` + `4-byte Timestamp`.
- **Response Packet (579 Bytes)**: `Status Code (0x00)` + `32-byte Signature R` + `32-byte Signature S` + `2-byte Length` + `512-byte X.509 Certificate Chain`.

### 2.2 Security Invariants
- Nonces are strictly single-use and generated via SEP TRNG to prevent replay attacks.
- Private keys are stored in tamper-proof, laser-etched eFuses inside the Beads silicon on the battery PCM. Any attempt to decap or probe the die clears the private key instantly.

---

## 3. High Power Management & USB-PD (`nub-spmi-a0`)

Charging is regulated through the dedicated `nub-spmi-a0` SPMI controller interfacing with the `spmi-hpm0-tnt` device at Slave ID `0x0A`:
- **Transceiver**: CBTL1702 USB Type-C Configuration Channel (CC) controller.
- **Power Delivery Profiles**: Supports USB-PD 3.1 Extended Power Range (EPR) up to $27\text{ W}$ ($9\text{ V} \times 3\text{ A}$ / $15\text{ V} \times 1.8\text{ A}$).
- **Autonomous Thermal Tapering**: When PMIC die temperatures exceed $105^\circ\text{C}$ or battery temperatures exceed $42^\circ\text{C}$, the charging current is tapered from $3000\text{ mA}$ down to $1200\text{ mA}$ via direct hardware SPMI register writes without requiring host CPU intervention.

---

## 4. Blackbox Shutdown History Telemetry

When power is interrupted, the PMIC latches over 22 parameters into non-volatile scratchpad memory:

```
+----------------------------------------------------------------------------------------------------+
|                         BLACKBOX SHUTDOWN TELEMETRY RECORD (PMIC SCRATCHPAD)                       |
+----------------------------------------------------------------------------------------------------+
| Key Register                    | Unit   | Operational Rationale                                   |
+---------------------------------+--------+---------------------------------------------------------+
| ShutDownVoltage                 | mV     | Terminal voltage at the instant of power collapse       |
| ShutDownPrevVoltage             | mV     | Terminal voltage 100ms before collapse                  |
| ShutDownAverageCurrent          | mA     | Rolling average current draw during final minute        |
| ShutDownFilteredCurrent         | mA     | Low-pass filtered instantaneous current                 |
| ShutDownMaxDischargeCurrent     | mA     | Peak current spike that triggered brownout protection    |
| ShutDownNominalChargeCapacity   | mAh    | Estimated capacity remaining in battery                 |
| ShutDownPassedCharge            | mAh    | Total Coulombs discharged across session                |
| ShutDownFullChargeCapacity      | mAh    | Learned battery full charge capacity                    |
| ShutDownPresentDOD              | %      | Instantaneous Depth of Discharge                        |
| ShutDownTemperature             | 0.1 C  | Battery pack temperature                                |
| ShutDownUISoc                   | %      | Displayed SoC presented to user (0%..100%)              |
| ShutDownUpoReboot               | bool   | True if shutdown was forced by Under-Power-Out (UPO)    |
| ShutDownDynSdVoltage            | mV     | Dynamically adjusted cutoff threshold                   |
| ShutDownDynamicSOCVcut          | mV     | IR-compensated cutoff accounting for cell resistance Ri |
| ShutDownRaTableRaw              | hex    | Complete snapshot of 15-point Ra table at shutdown      |
+---------------------------------+--------+---------------------------------------------------------+
```
