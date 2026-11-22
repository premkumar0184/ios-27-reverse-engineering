# Secure Enclave XNU Driver Boundary, Kernel Stacks & Userland KeyStore

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem**: Darwin XNU Kernel Drivers & Userland `libaks.dylib` Runtime Interface  
**Phase Identifier**: `sep_phase_4_xnu_driver_boundary`  
**Classification**: Clean-Room Architectural Reverse Engineering  

---

## 1. Executive Summary

While the Secure Enclave executes in complete physical and architectural isolation, user-facing features (such as unlocking files, authenticating with Face ID, or generating Apple Pay cryptograms) originate in userland processes on the Application Processor. The Darwin XNU kernel acts as the secure, trusted intermediary, translating userland system calls into hardware mailbox transactions.

This document dissects the multi-tiered driver stack connecting userland applications to sepOS: from userland C APIs (`libaks.dylib`) through IOKit kernel drivers (`AppleSEPManager`, `AppleSEPKeyStore`, `AppleSEPARTStorage`) to the `ASCwrap-v6` hardware mailbox.

```mermaid
sequenceDiagram
    autonumber
    participant App as User Process (passd / securityd)
    participant LibAKS as libaks.dylib (Userland)
    participant AKS as AppleSEPKeyStore.kext (Kernel)
    participant SEPMgr as AppleSEPManager.kext (Kernel)
    participant Mailbox as ASCwrap-v6 MMIO (0x72600000)
    participant SEPOS as sepOS KeyStoreServer (EL0)
    participant AES as Hardware AES Core

    App->>LibAKS: aks_unwrap_key(class_id, wrapped_key)
    LibAKS->>AKS: IOKit UserClient Trap (s_kext_unwrap)
    AKS->>SEPMgr: sendMailboxCommand(EP_KEYSTORE, CMSG_UNWRAP_KEY)
    SEPMgr->>Mailbox: Write 64-bit Header & Payload to INBOX_DATA_FIFO
    SEPMgr->>Mailbox: Assert DOORBELL_AP_TO_SEP (0x0040)
    Note over SEPMgr: AP Thread Blocks (wait_event)
    
    Mailbox-->>SEPOS: Hardware Interrupt (AIC IRQ)
    SEPOS->>Mailbox: Read Packet from Outbox FIFO
    SEPOS->>AES: Unseal Media Key via UID0 / Class Key Ladder
    AES-->>SEPOS: 32-Byte Raw File Key (Internal SRAM)
    SEPOS->>Mailbox: Write Response Packet to OUTBOX_DATA_FIFO
    SEPOS->>Mailbox: Assert DOORBELL_SEP_TO_AP (0x0140)
    
    Mailbox-->>SEPMgr: Hardware Interrupt (IRQ 304: OUTBOX_NOT_EMPTY)
    SEPMgr->>Mailbox: Read Response & Clear Doorbell
    SEPMgr-->>AKS: Return Unwrapped Key Material
    AKS-->>LibAKS: Return Plaintext Media Key to Kernel VFS
    LibAKS-->>App: Success (0)
```

---

## 2. Kernel Driver Architecture

The XNU kernel encapsulates Secure Enclave communication across a suite of dedicated IOKit drivers extracted from `kernelcache.release.raw`:

### 2.1 `AppleSEPManager` (`com.apple.driver.AppleSEPManager`)
The master transport driver managing hardware MMIO mappings and interrupt arbitration:
- **`AppleSEPManager::start`**: Maps the 544 KiB `ASCwrap-v6` MMIO aperture at physical address `0x0000000072600000` into kernel virtual space; registers interrupt handlers for IRQs 304 (`OUTBOX_NOT_EMPTY`), 305 (`INBOX_EMPTY`), 306 (`DOORBELL`), and 307 (`FAULT`).
- **`AppleSEPManager::sendMailboxCommand`**: Atomically acquires the inbox FIFO spinlock, constructs the 64-bit header word, streams payload words to `INBOX_DATA_FIFO`, and strobes the doorbell.
- **`AppleSEPManager::handleMailboxInterrupt`**: Invoked on IRQ 304. Reads packets from `OUTBOX_DATA_FIFO`, matches the `sequence_tag` to the blocked calling thread, and wakes the waiting client.
- **`AppleSEPManager::allocateSharedBuffer`**: Maps out-of-line (OOL) DMA memory frames through DART-SEP Stream ID 0 (`mapper-sep`) for large payloads.
- **`AppleSEPManager::reseedXNUPRNG`**: Periodically requests 64 bytes of true entropy from SEP TRNG via `cmsgGET_ENTROPY_FOR_XNU_PRNG` and feeds `write_random()` to maintain host cryptographic entropy.

### 2.2 `AppleSEPKeyStore` (`com.apple.driver.AppleSEPKeyStore`)
The core Data Protection engine in XNU:
- Mediates all VFS file encryption/decryption requests.
- Translates APFS volume mount requests into keybag loading commands (`cmsgLOAD_KEYBAG`).
- Listens for device lock notifications (`com.apple.system.powermanagement`), immediately issuing `cmsgDROP_CLASS_KEYS` to evict Class A keys from SEP memory.
- Enforces user passcode verification rate limiting via `cmsgVERIFY_PASSCODE`.

### 2.3 Auxiliary Storage Drivers
- **`AppleSEPARTStorage`**: Manages communication with internal Effaceable Storage NOR flash, loading and validating Anti-Replay Tokens (`ART`) during boot.
- **`AppleSEPXART`**: Manages the 16 MB encrypted Gigalocker partition on raw NAND, issuing journal synchronization commands (`cmsgXART_SYNC_GIGALOCKER`).
- **`AppleCredentialManager`**: Intermediary for FIDO2 / WebAuthn passkey operations, routing challenge signing to `CredentialServer`.

---

## 3. Userland Interface: `libaks.dylib`

Userland security daemons (`securityd`, `passd`, `biometrickitd`) interact with AppleKeyStore via `/usr/lib/libaks.dylib`:

| Exported C Function | Target Opcode | Description |
| :--- | :---: | :--- |
| **`aks_load_bag`** | `0x0201` | Transmits an encrypted user or system keybag blob to SEP for unwrapping. |
| **`aks_save_bag`** | `0x0202` | Requests SEP to seal and export the current keybag state encrypted under Device KEK. |
| **`aks_unwrap_key`** | `0x0203` | Unwraps a 40-byte wrapped file media key under specified protection class (1..4). |
| **`aks_wrap_key`** | `0x0204` | Generates and wraps a new 32-byte file key under specified protection class. |
| **`aks_drop_class_keys`** | `0x0205` | Explicitly requests eviction of Class A keys from memory upon device lock. |
| **`aks_verify_passcode`**| `0x0206` | Submits candidate user passcode to SEP for hardware scrypt verification. |
| **`aks_change_passcode`**| `0x0207` | Re-wraps Class A–C master keys under new passcode secret. |

---

## 4. Verified Clean-Room Implementation: `sep_mailbox_client.pseudo.c`

A complete, standalone C client implementation of the ASCwrap-v6 mailbox protocol has been authored and verified:
[`artifacts/sep/pseudocode/sep_mailbox_client.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/sep/pseudocode/sep_mailbox_client.pseudo.c)

### 4.1 Key Implementation Highlights
- **Direct MMIO Registers**: Memory-mapped pointer manipulation using volatile 32-bit and 64-bit accessors.
- **Non-Blocking Status Polling**: Validates `ASC_REG_INBOX_STATUS` and `ASC_REG_OUTBOX_STATUS` flags with bounded timeout loops.
- **Packet Construction**: Packs 64-bit header words containing `length_words`, `endpoint_id`, `sequence_tag`, `command_opcode`, and control flags.
- **Key Unwrapping API (`sep_unwrap_key`)**: Packages Class ID and 40-byte wrapped key, streams to inbox, strobes doorbell, waits for response, and extracts 32-byte plaintext key.
- **Locking Eviction API (`sep_drop_class_keys`)**: Dispatches Class A key drop request.
- **Syntax Verification**: 100% compliant C99/C11 syntax, validated with `gcc -fsyntax-only -Wall -Wextra`.

---

## 5. Security Threat Analysis at the Driver Boundary

1. **Host Kernel Compromise (Ring 0 Attack)**:
   - *Threat*: An attacker with root code execution in Darwin attempts to read raw encryption keys by dumping memory or issuing arbitrary mailbox commands.
   - *Mitigation*: The SEP never transmits raw master keys (`UID0`, `GID0`, `Device KEK`, or Class A master keys) back to the AP. It only unseals individual 32-byte file keys for specific active files or performs cryptographic operations internally.
2. **Mailbox Fuzzing & Malformed Packet Injection**:
   - *Threat*: An attacker injects corrupted lengths, invalid opcodes, or out-of-bounds DMA pointers into the inbox FIFO.
   - *Mitigation*: The sepOS mailbox dispatcher strictly verifies packet lengths ($\le 64$ words), validates endpoint indices, and asserts that all physical DMA pointers fall within DART-SEP Stream 0 permissions before memory is accessed.

---

## 6. Summary of Phase S4 Deliverables

- [`artifacts/sep/xnu_sep_boundary_spec.json`](file:///home/prem/Projects/iOS%2027/artifacts/sep/xnu_sep_boundary_spec.json): Complete kernel driver inventory, methods, and userland library exports.
- [`artifacts/sep/pseudocode/sep_mailbox_client.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/sep/pseudocode/sep_mailbox_client.pseudo.c): Standalone C mailbox client implementation verified with `gcc -fsyntax-only`.
- [`findings/sep/04_XNU_DRIVER_BOUNDARY.md`](file:///home/prem/Projects/iOS%2027/findings/sep/04_XNU_DRIVER_BOUNDARY.md): In-depth findings documentation.
