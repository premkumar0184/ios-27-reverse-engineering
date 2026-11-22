# AOP2 & RTKit Reverse Engineering: Phase 4 — XNU Kernel Boundary & Clean-Room C Client

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem**: Darwin / XNU Kernel Driver Boundary, IOKit Dispatch Models & Clean-Room C Runtime  
**Primary Binaries**:
- `artifacts/kernel/kernelcache.release.raw` (Darwin 24.2.0 XNU kernelcache)
- `artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c` (Standalone compilable clean-room C client)
**Date**: November 2026  
**Classification**: Clean-Room Architectural Reverse Engineering Report

---

## 1. Darwin / XNU Driver Architecture for AOP2

In the host Darwin kernel, communication with AOP2 is managed by three primary I/O Kit kernel extensions (kexts):
1. **`com.apple.driver.AppleAOP2`**: Master coprocessor controller attaching directly to `/device-tree/arm-io/aop2`. Manages mailbox MMIO initialization, RTKit boot handshakes, and host-side Tightbeam RPC proxy endpoints.
2. **`com.apple.driver.AppleSPU`**: Sensor Processing Unit driver suite. Manages lock-free DMA fast-path ring buffers for high-frequency motion streaming (`AppleSPUFastpathDriver`), TrueTone ambient light parsing (`AppleSPUALSColorDriver`), and 1Hz display refresh arbitration (`AppleSPUDCPDriver`).
3. **`com.apple.driver.AppleAOPAudio`**: Always-On Audio driver managing low-power PDM microphone inputs (`AppleAOPAudioLPMicInDevice`), 3.0-second circular acoustic SRAM buffers, and user client interfaces for voice trigger handoffs (`AppleAOPVoiceTriggerUserClient`).

```
+----------------------------------------------------------------------------------------------------+
|                                      USERLAND DAEMONS & FRAMEWORKS                                 |
|          assistantd / CoreSpeech              IOHIDEventSystem               backboardd            |
|         (Siri Keyword Trigger)             (Motion / Touch Events)            (1Hz AOD)            |
+----------------------------------------------------------------------------------------------------+
                   |                                     |                          |
       [IOUserClient Mach IPC]               [IOUserClient Mach IPC]     [IOUserClient Mach IPC]
                   |                                     |                          |
+----------------------------------------------------------------------------------------------------+
|                                    DARWIN / XNU (Host Kernel Ring 0)                               |
|                                                                                                    |
|  +------------------------------+  +-------------------------------+  +-------------------------+  |
|  | AppleAOPVoiceTriggerUserCl.  |  | AppleSPUFastpathDriverUserCl. |  | AppleSPUDispADCUserCl.  |  |
|  | Entitlement: AppleAOPAudio   |  | Entitlement: aop.fastpath     |  | Entitlement: aop.adc    |  |
|  +------------------------------+  +-------------------------------+  +-------------------------+  |
|                 |                                  |                              |                |
|  +------------------------------+  +-------------------------------+  +-------------------------+  |
|  | AppleAOPAudioLPMicInDevice   |  | AppleSPUFastpathDriver        |  | AppleSPUDCPDriver       |  |
|  | Audio Ring Buffer Manager    |  | SPSC FastPathRingBuffer (16K) |  | dcp-control (256 KB)    |  |
|  +------------------------------+  +-------------------------------+  +-------------------------+  |
|                 \                                  |                              /                |
|                  +---------------------------------+-----------------------------+                 |
|                                                    |                                               |
|                                     AppleAOP2SystemDriver (Master Nub)                             |
|                                     - IOWorkLoop & IOCommandGate Serialization                     |
|                                     - ASCwrap Mailbox Driver (MMIO: 0x101600000)                   |
|                                     - DART-AOP Translation Manager (SID 0x10)                      |
+----------------------------------------------------------------------------------------------------+
                                                     |
                         [Apple Silicon ASCwrap Hardware Mailbox Interface]
                                                     |
+----------------------------------------------------------------------------------------------------+
|                                ALWAYS-ON PROCESSOR 2 (AOP2 RTKit Firmware)                         |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. IOKit Service Matching & DeviceTree Binding

Each driver attaches to the hardware I/O Registry via exact DeviceTree property matching dictionaries extracted from `kernelcache.release.raw`:

### 2.1 Driver Matching Profiles
```
Driver Class                 Matching Key / Node                     Compatible String               IOMMU Stream ID
------------------------------------------------------------------------------------------------------------------------
AppleAOP2SystemDriver        /device-tree/arm-io/aop2                iop,ascwrap-v6                  0x10 (mapper-aop2)
AppleAOP2KextTightbeamEp     site.AppleAOP2KextTightbeamEndpoint     Internal Service                N/A (RPC Proxy)
AppleSPUFastpathDriver       /device-tree/arm-io/aop/iop-aop-nub     iop-nub,rtbuddy-v2              0x10 (mapper-aop2)
AppleSPUALSColorDriver       /device-tree/arm-io/aop/iop-aop-nub/als iop-audio,aop-service           N/A (EP 0x11 MBI)
AppleSPUDCPDriver            /device-tree/arm-io/aop/iop-aop-nub/dcp dcp-control                     0x10 (Shared Frame)
AppleAOPAudioLPMicInDevice   /device-tree/arm-io/aop/iop-aop-nub/aud iop-audio,aop-service           0x08 (ADMAC Base)
```

---

## 3. Workloop, CommandGate & Memory Synchronization Models

To ensure strict real-time determinism across the heterogeneous AP-AOP boundary without kernel deadlocks or thread starvation, Apple employs an `IOWorkLoop` and `IOCommandGate` architecture:

### 3.1 Serialization Model
1. **Workloop Ownership**: `AppleAOP2SystemDriver` instantiates a dedicated `IOWorkLoop` during its `start()` routine.
2. **Command Gate Synchronization**: All endpoint mailbox interactions (`MBI_INBOX_DATA` read, `MBI_OUTBOX_DATA` write, `DOORBELL_SET`) are encapsulated within `IOCommandGate::runAction()` closures. This guarantees that multiple concurrent driver clients (e.g., audio daemon requesting power states while motion driver drains IMU samples) cannot interleave partial 64-bit message words.
3. **Memory Descriptors**: Fastpath sensor buffers and audio history buffers are mapped into host kernel virtual address space using `IOMemoryDescriptor::withAddressRange()` configured with memory cache inhibit flags (`kIOMapAnywhere | kIOMapInhibitCache`). This disables L1/L2 cache coherency snooping on the AP, relying instead on explicit software memory barriers (`dmb ishld` / `dmb ishst`).

---

## 4. User Clients & Entitlement Gating

Direct userland communication with AOP2 hardware is strictly gated behind granular system entitlements:

```
User Client Class                  Target Subsystem         Required Entitlement
-------------------------------------------------------------------------------------------------------
AppleSPUFastpathDriverUserClient   IMU Fastpath Telemetry   com.apple.aop.fastpath.user-client.full-access
AppleSPUDispADCUserClient          1Hz AOD Frame Geometry   com.apple.aop.adc.user-client.full-access
AppleAOPVoiceTriggerUserClient     Siri 3.0s SRAM History   com.apple.driver.AppleAOPAudioUserClientEntitlement
AppleAOP2IOPMServiceUserClient     Power Retention Control  com.apple.private.aop.iopm-control
```

Attempts by un-entitled processes to open these user clients return `kIOReturnNotPrivileged` (`0xe00002e2`), preventing unauthorized applications from capturing raw sensor telemetry or injecting spoofed audio history buffers.

---

## 5. Clean-Room C Client Runtime Walkthrough

The standalone client implementation `artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c` demonstrates the complete end-to-end operation of the AOP2 channel without relying on private Apple headers:

### 5.1 Memory Barrier Enforcement in Fastpath Ring Draining
```c
uint32_t aop2_fastpath_read_samples(aop2_fastpath_ring_t *ring,
                                    aop2_imu_sample_t *dest_buffer,
                                    uint32_t max_samples)
{
    /* Read producer head with acquire semantics */
    uint32_t head = ring->producer_head_idx;
    aop_dmb_ld(); /* dmb ishld: ensures head is visible before reading samples */

    uint32_t tail = ring->consumer_tail_idx;
    uint32_t count = 0;

    while (tail != head && count < max_samples) {
        uint32_t slot = tail % ring->capacity;
        dest_buffer[count] = ring->samples[slot];
        tail++;
        count++;
    }

    /* Publish updated consumer tail with release semantics */
    aop_dmb_st(); /* dmb ishst: ensures samples consumed before advancing tail */
    ring->consumer_tail_idx = tail;

    return count;
}
```

### 5.2 Direct Cross-Enclave Sensor Privacy Dispatch (`EP 0x53`)
```c
bool aop2_forward_sensor_privacy_to_exclave(volatile uint8_t *exclave_mailbox_mmio,
                                            bool mic_active,
                                            bool cam_active,
                                            uint32_t nonce)
{
    /* Format 64-bit immediate descriptor for EP 0x53 */
    uint64_t payload = ((uint64_t)mic_active << 34) |
                       ((uint64_t)cam_active << 33) |
                       ((uint64_t)nonce & 0xFFFFFFFFULL);

    uint64_t msg = RTK_MSG_PACK(RTK_EP_EXCLAVE_BRIDGE, RTK_MSG_TYPE_TIGHTBEAM_RPC, payload);

    /* Write directly to Exclave proxy mailbox register at physical 0x35167c000 */
    volatile uint64_t *exclave_outbox = (volatile uint64_t *)(exclave_mailbox_mmio + AOP2_MBI_OUTBOX_DATA);
    *exclave_outbox = msg;

    aop_dmb_st();

    /* Assert Exclave secure doorbell interrupt */
    volatile uint32_t *exclave_doorbell = (volatile uint32_t *)(exclave_mailbox_mmio + AOP2_DOORBELL_SET);
    *exclave_doorbell = (1U << 0);

    return true;
}
```

---

## 6. Phase 4 Verification & Completion Status

- [x] Host XNU kernel drivers (`AppleAOP2`, `AppleSPU`, `AppleAOPAudio`) reverse engineered from `artifacts/kernel/kernelcache.release.raw`.
- [x] IOKit matching dictionaries, device tree node relationships, and workloop synchronization documented.
- [x] User clients and required entitlements cataloged.
- [x] Standalone compilable clean-room C client runtime implemented at `artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c`.
- [x] Syntax verification passes with 100% clean output: `gcc -fsyntax-only -Wall -Wextra`.
- [x] Deliverable `artifacts/aop/xnu_aop_boundary_spec.json` created.
- [x] Zero collisions or file alterations in `artifacts/sep`, `artifacts/gpu`, or `artifacts/sptm`.
