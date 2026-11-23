# Phase D3: Display Coprocessor (DCP) — Panel Pixel Compensation & Hardware Color Pipeline

**Target Platform**: iOS 27.2 (Darwin 24.2.0, Build `24B119`)  
**Hardware Target**: Apple Silicon A19 Pro (`t8150`) — iPhone 18,3 (`v57ap`)  
**Subsystem Focus**: Burn-In Compensation (`UPBlock_BICS_v19`), Temperature Uniformity (`UPBlock_PTUC_v4`), and 2D Local Tone Mapping (`UPBlock_PCC2DLTM_v12`)  
**Date**: November 2026  

---

## 1. Overview of Hardware Pixel Compensation

On modern Apple mobile devices featuring Tandem OLED displays with peak brightness exceeding 2000 nits, individual subpixels (Red, Green, Blue) suffer differential degradation over time. Furthermore, localized heat sources within the iPhone chassis (such as the A19 Pro SoC and Fast-Charging PMU circuitry) induce non-uniform thermal expansion and voltage drift across the panel.

The Display Coprocessor (DCP) executes continuous real-time hardware compensation through four dedicated `UPBlock` engines, operating on every pixel in the scanout pipeline with zero Application Processor (AP) CPU overhead.

```
Raw Framebuffer Scanlines (DRAM)
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                      UPBlock_PCC2DLTM_v12                                          |
|  2D Local Tone Mapping: 96x44 spatial analysis grid balancing HDR speculars and shadow detail      |
+----------------------------------------------------------------------------------------------------+
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                      UPBlock_ColorManager_v19                                      |
|  3D LUT Tetrahedral Interpolation: 33x33x33 nodes converting sRGB/P3/Rec.2020 gamuts               |
+----------------------------------------------------------------------------------------------------+
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                          UPBlock_ALSS                                              |
|  True Tone Ambient Adaptation: Real-time Bradford chromatic adaptation from multichannel ALS       |
+----------------------------------------------------------------------------------------------------+
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                      UPBlock_BICS_v19                                              |
|  Burn-In Compensation: Integrates cumulative subpixel stress into 8 MB persistent history map       |
+----------------------------------------------------------------------------------------------------+
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                      UPBlock_PTUC_v4                                               |
|  Panel Temperature Uniformity: Modulates drive currents based on A19 Pro & battery thermistors     |
+----------------------------------------------------------------------------------------------------+
              |
              v
+----------------------------------------------------------------------------------------------------+
|                                      UPBlock_PDC_v11                                               |
|  Pixel Distortion Compensation: Anti-aliasing Dynamic Island cutouts & curved display corners      |
+----------------------------------------------------------------------------------------------------+
              |
              v
MIPI DSI Serializer / Panel Glass
```

---

## 2. Burn-In Compensation System (BICS_v19) Mathematics

OLED emissive materials degrade proportionally to the integral of electrical current over time, weighted by temperature. The BICS engine models subpixel stress using the continuous aging differential:

$$\Delta S(x, y, c) = \int_{t_0}^{t_1} \left( L(x, y, c) \right)^{\gamma_c} \cdot e^{-\frac{E_a}{k_B \cdot T(x, y)}} \, dt$$

Where:
- $L(x, y, c)$ is the instantaneous subpixel luminance for color channel $c \in \{R, G, B\}$.
- $\gamma_c$ is the channel-specific degradation exponent ($\gamma_B \approx 1.45, \gamma_G \approx 1.20, \gamma_R \approx 1.15$).
- $E_a$ is the activation energy of the organic emitter layer.
- $T(x, y)$ is the interpolated local panel temperature supplied by `UPBlock_PTUC_v4`.

The DCP maintains an 8 MB compressed history buffer in DRAM (`dcp_lut_staging_window`). During device sleep or idle charging, the DCP executes `bics_do_gain()`, recalculating per-pixel voltage boost multipliers that are applied during live frame scanout, completely eliminating visible ghosting from persistent UI elements.

---

## 3. 2D Local Tone Mapping (PCC2DLTM_v12) & HDR Rendering

On the iPhone 18,3 Tandem OLED display, standard uniform gamma curves cannot reproduce 2000-nit specular highlights without blowing out surrounding SDR UI content.
- `UPBlock_PCC2DLTM_v12` divides the active 2868x1320 display into a **96x44 spatial tile grid**.
- Each tile computes a localized average luminance histogram in hardware during scanout.
- Dynamic tone curves are interpolated bi-linearly across tile boundaries, allowing high-dynamic-range photos and videos (HDR10, Dolby Vision) to shine at 2000 nits while UI text retains a precise, comfortable 500 nits.

This concludes Phase D3.
