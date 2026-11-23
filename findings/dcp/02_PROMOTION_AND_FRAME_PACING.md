# Phase D2: ProMotion Dynamic Refresh Rate Arbitration & Frame Pacing Engine

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem Focus**: Vertical Flexible Timing Generator (`UPBlock_VFTG_v38`) & Software-Managed Pixel Refresh (`UPBlock_SWMPR_v1`)  
**Date**: November 2026  

---

## 1. The ProMotion Architectural Challenge on OLED Panels

Traditional variable refresh rate (VRR) monitors in desktop displays vary the pixel clock frequency to alter the frame rate. However, on active-matrix Organic Light-Emitting Diode (AMOLED) and Tandem OLED panels, altering the pixel clock or line scan time alters the electrical charge decay rate of the driving Thin-Film Transistors (TFTs). This causes severe visual artifacts, including:
- **Luminance Fluctuation (Flicker)**: The display dims or brightens as refresh rate shifts.
- **Color Shift**: Differential subpixel voltage thresholds shift white point chromaticity.
- **Image Sticking**: Static charges accumulate unevenly across the panel.

On the A19 Pro running iOS 27.2, Apple solves this fundamental physics challenge through the combination of **Low-Temperature Polycrystalline Oxide (LTPO 3.0)** panel technology and the **Vertical Flexible Timing Generator (VFTG_v38)** running within the Display Coprocessor (DCP).

---

## 2. Vertical Flexible Timing Generator (VFTG_v38) Mechanics

### 2.1 The Principle of Fast Scan / Dynamic Blanking
The core invariant of Apple's VFTG implementation is **Scan-Time Invariance**:

$$\text{Line Time} = \frac{\text{Total Horizontal Pixels}}{\text{Pixel Clock}} = \frac{1400}{504\text{ MHz}} \approx 2.7778 \ \mu\text{s}$$

Regardless of whether the display is operating at 120Hz, 60Hz, 24Hz, 10Hz, or 1Hz:
- All 2868 active vertical lines are ALWAYS scanned out at the maximum 504 MHz pixel clock rate ($\approx 7.967$ ms scan time).
- Refresh rate variations are achieved entirely by **modulating the duration of the Vertical Back Porch ($VBP$)** during the vertical blanking interval ($VBLANK$).

```
120Hz Frame (8.333 ms):
+------------------------------------------+-----------------------+
| Active Display Scan (2868 lines, 7.97ms) | VBLANK (132 lines)    |
+------------------------------------------+-----------------------+

60Hz Frame (16.666 ms):
+------------------------------------------+-----------------------------------------------+
| Active Display Scan (2868 lines, 7.97ms) | Extended VBLANK (3132 lines, 8.70ms)          |
+------------------------------------------+-----------------------------------------------+

10Hz Frame (100.000 ms):
+--------------------+----------------------------------------------------------------------+
| Active Scan (7.97ms| Extremely Extended VBLANK (33132 lines, 92.03ms)                     |
+--------------------+----------------------------------------------------------------------+
```

### 2.2 Numerical VFTG Parameter Matrix

| Mode | Refresh Rate | Frame Period ($\mu$s) | Active Lines | Front Porch | Sync Width | Back Porch Lines | Total Lines |
|---|---|---|---|---|---|---|---|
| **Max ProMotion** | 120 Hz | 8,333.33 | 2868 | 12 | 4 | 116 | 3,000 |
| **Intermediate** | 80 Hz | 12,500.00 | 2868 | 12 | 4 | 1,616 | 4,500 |
| **Standard Video**| 60 Hz | 16,666.67 | 2868 | 12 | 4 | 3,116 | 6,000 |
| **2:2 Pulldown** | 48 Hz | 20,833.33 | 2868 | 12 | 4 | 4,616 | 7,500 |
| **120Hz Divisor** | 40 Hz | 25,000.00 | 2868 | 12 | 4 | 6,116 | 9,000 |
| **Standard UI** | 30 Hz | 33,333.33 | 2868 | 12 | 4 | 9,116 | 12,000 |
| **Cinema Native** | 24 Hz | 41,666.67 | 2868 | 12 | 4 | 12,116 | 15,000 |
| **Static Low** | 20 Hz | 50,000.00 | 2868 | 12 | 4 | 15,116 | 18,000 |
| **Extended Low** | 15 Hz | 66,666.67 | 2868 | 12 | 4 | 21,116 | 24,000 |
| **Min Interactive**| 10 Hz | 100,000.00 | 2868 | 12 | 4 | 33,116 | 36,000 |
| **Always-On Sleep**| 1 Hz | 1,000,000.00| 2868 | 12 | 4 | 357,116 | 360,000 |

---

## 3. Software-Managed Pixel Refresh (SWMPR_v1) Arbitration State Machine

The DCP contains an autonomous software governor (`swmpr_v1.c` / `UPBlock_SWMPR_v1.cpp`) that dynamically switches refresh states based on three priority inputs:
1. **Touch Velocity & Phase**:
   - `UITouchPhaseBegan`: Triggers an instantaneous, single-VSYNC boost from 10Hz directly to 120Hz with zero latency.
   - `UITouchPhaseMoved`: Holds 120Hz as long as touch finger movement exceeds 0.5 points per frame.
   - `UITouchPhaseEnded`: Enters deceleration decay: transitions through 80Hz for 100ms, then 60Hz, step-decaying down to 10Hz if no subsequent frames are committed.
2. **Media Playback Hints**:
   - When AVFoundation plays a 24.000fps or 23.976fps video stream, the host driver passes a `cmsgSET_MEDIA_TIMING` descriptor. The SWMPR locks to 24Hz or 48Hz (2:2 pulldown) via Quick Media Switching (QMS), eliminating 3:2 pulldown judder.
3. **Always-On Display (AOD)**:
   - When the device is locked, Darwin signals sleep mode. The SWMPR transitions to `SWMPR_STATE_AOD_1HZ`, handing timing control over to `CBAOPEndpoint`.

---

## 4. Hardware Tearing Effect (Fast_TE) Synchronization

To ensure frame updates never tear during flexible back porch modulation, the DCP synchronizes with the panel via a dedicated hardware line: **Fast_TE** (Fast Tearing Effect).
- The Fast_TE signal is sampled using a high-precision 24 MHz hardware timer.
- If a frame swap request is submitted within 48 timer ticks ($\approx 2 \ \mu\text{s}$) of the TE edge, the DCP executes an atomic swap descriptor without dropping a frame.

This concludes Phase D2.
