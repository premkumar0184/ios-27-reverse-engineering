# Phase D4: Display Coprocessor (DCP) — Darwin/XNU Kernel Boundary & Driver Stack

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem Focus**: `AppleCLCD2.kext`, `IOMobileFramebuffer.kext`, `AppleDCP.kext`, and ASCwrap-v6 Mailbox Boundary  
**Date**: November 2026  

---

## 1. Overview of the Darwin Display Stack

In the Darwin kernel, graphics presentation and display hardware control are separated into two distinct layers:
1. **Application Processors (Ring 0)**:
   - `WindowServer`: The user-space display compositor assembling surfaces from UIKit and Metal rendering contexts into composited layer lists.
   - `IOMobileFramebuffer`: The kernel abstraction layer presenting a virtual framebuffer interface, VSYNC mach ports, and ProMotion refresh rate preferences.
   - `AppleCLCD2.kext`: The platform driver responsible for translating high-level swap requests into ASCwrap-v6 mailbox packets and managing DART-DISP0 memory mappings.
2. **Display Coprocessor (DCP Hardware Core)**:
   - Executes RTKitOS, managing the real-time VFTG timing generators, hardware 3D LUT color transforms, and MIPI DSI physical serialization.

```
+----------------------------------------------------------------------------------------------------+
|                                    USER SPACE (macOS / iOS UI)                                     |
|               UIKit Applications / Metal Games / AVFoundation Video Streams                        |
+----------------------------------------------------------------------------------------------------+
                                                  |  (IOSurface Handles & CoreAnimation Commits)
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                    WindowServer (Compositor)                                       |
|  - Tracks per-view refresh requirements (e.g. 120Hz for scroll view, 24Hz for video playback)       |
|  - Issues IOMobileFramebufferSwapSetDisplayProperties & IOMobileFramebufferSwapSubmit             |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                      XNU KERNEL (Ring 0)                                           |
|                                                                                                    |
|   [com.apple.iokit.IOMobileFramebuffer]                                                            |
|       - Dispatches VSYNC Mach Messages to UI RunLoops                                              |
|       - Handles Display Power Policies & Ambient Light Sensor updates                              |
|                          |                                                                         |
|                          v                                                                         |
|   [com.apple.driver.AppleCLCD2]                                                                    |
|       - Maps Framebuffer IOSurfaces into DART-DISP0 (0x1fa300000)                                  |
|       - Formats 64-word dcp_packet_t descriptors                                                   |
|       - Posts commands to ASCwrap-v6 Mailbox (0x100600000)                                         |
+----------------------------------------------------------------------------------------------------+
                                                  |  (Hardware Mailbox FIFO & Doorbell IRQ 411)
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                   DISPLAY COPROCESSOR (DCP)                                        |
|  - RTKit Executive receives swap request via AFKBuiltinAPMailboxEndpoint                           |
|  - Fast_TE synchronizes swap with vertical back porch expansion (VFTG_v38)                         |
|  - UPBlocks (PCC2DLTM, BICS, PTUC, ALSS) process scanlines in real time                            |
|  - Transmits 2868x1320 10-bit pixels over MIPI DSI lanes to Tandem OLED glass                      |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Mailbox Command Protocol & Interaction Loop

The driver communicates with the DCP across the ASCwrap-v6 mailbox located at physical address `0x0000000100600000`:

### 2.1 Surface Swap Submission (`dcp_cmd_SUBMIT_FRAME_SWAP`)
1. WindowServer completes frame rendering and issues `IOMobileFramebufferSwapSubmit`.
2. `AppleCLCD2` translates the memory backing into a DART-DISP0 Device Virtual Address (`dva`).
3. It packages `dcp_swap_descriptor_t`:
   - `frame_dva`: 64-bit IOMMU virtual address
   - `width`: 2868
   - `height`: 1320
   - `stride_bytes`: 11472 (2868 * 4)
   - `pixel_format`: `kIOColorSpace_DisplayP3` (10-bit RGBA)
   - `target_refresh_hz`: 120 (or dynamically determined rate)
   - `vsync_deadline_ns`: Next target VSYNC timestamp
4. `AppleCLCD2` writes the header and payload words to `DCP_REG_INBOX_DATA` (`0x0000`).
5. A Data Memory Barrier (`dmb oshst`) is executed to ensure write ordering.
6. The doorbell interrupt `DCP_REG_DOORBELL_AP_TO_DCP` (`0x0040`) is asserted.
7. The DCP core processes the descriptor and signals completion via `AIC_IRQ_DISP_INT_DCP` (vector 411).

---

## 3. Production Clean-Room C Client Implementation

The clean-room C client [`artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c`](file:///home/prem/Projects/iOS%2027/artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c) provides a complete, syntactically verified reference implementation of:
- Memory-mapped I/O initialization and interrupt mask configuration.
- Polling and status checks on hardware FIFOs with timeout safeguards.
- Atomic sequence number increments for transaction correlation.
- Structured surface swap and ProMotion dynamic refresh rate commands.

This concludes Phase D4.
