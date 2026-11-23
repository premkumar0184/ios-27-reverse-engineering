# Apple Rose 2 / Rose 3 (U2 / U3) Angle-of-Arrival (AoA) & PDoA Localization
**Exhaustive Mathematical Derivation of Phase Difference of Arrival Interferometry, Spatial Anti-Aliasing & DeviceTree Q16.16 Spherical Calibration**

**Target Silicon:** Apple Rose 2 / Rose 3 Ultra-Wideband (UWB) Subsystem (`r2p1` / `hammerfest`)  
**Host Platform:** Apple Silicon A19 Pro (`t8150`) / iPhone 18,3 (`v57ap`) / iOS 27.2 (`24B119`)  
**Antenna Architecture:** 3-Element Orthogonal Planar Array (Rx0 Upper Left, Rx1 Vertex/Reference, Rx2 Lower Center)  
**Baseline Geometry:** Horizontal $d_h = 15.5 \text{ mm}$, Vertical $d_v = 14.8 \text{ mm}$ ($\lambda_{\text{Ch9}} = 37.534 \text{ mm}$)  
**Calibration Source:** DeviceTree `/arm-io/rose` Q16.16 Radian Boundaries at binary offset `0x1c900`  

---

## 1. Principles of Phase Difference of Arrival (PDoA) Interferometry

While Time-of-Flight (ToF) resolves the scalar distance between two devices, spatial positioning requires determining the 3D unit vector pointing toward the target in spherical coordinates $(\rho, \theta, \phi)$:
- Distance $\rho$ (meters): Derived from DS-TWR picosecond ToF.
- Azimuth $\theta$ (degrees): Horizontal angle in the plane of the device display.
- Elevation $\phi$ (degrees): Vertical angle perpendicular to the horizontal plane.

The Apple Rose 2 silicon derives bearing angles through **Phase Difference of Arrival (PDoA)** interferometry across a multi-element antenna array. When a planar electromagnetic wavefront impinges upon two separated antennas, the path length difference creates a measurable phase shift in the received carrier wave.

```mermaid
graph TD
    subgraph PDoA_Interferometry_Concept["Wavefront Phase Difference Geometry"]
        WAVE["Incoming Planar Wavefront (Angle theta)"]
        ANT0["Rx0 / Rx2 Antenna"]
        ANT1["Rx1 Reference Antenna"]
        DELAY["Extra Travel Distance: Delta L = d * sin(theta)"]
    end

    WAVE --> ANT1
    WAVE --> DELAY
    DELAY --> ANT0
```

---

## 2. iPhone 18,3 Physical Antenna Array Geometry

The antenna array integrated into the iPhone 18,3 (`v57ap`) chassis forms an **L-shaped orthogonal 2D planar interferometric array** consisting of three antenna elements:
1. **Rx1 (Vertex / Reference Element):** Centrally located reference antenna shared between azimuth and elevation interferometers.
2. **Rx0 (Upper Left Element):** Displaced horizontally from Rx1 by baseline distance $d_h$.
3. **Rx2 (Lower Center Element):** Displaced vertically from Rx1 by baseline distance $d_v$.

```mermaid
graph TD
    subgraph Antenna_Array_Layout["iPhone 18,3 Physical Chassis Antenna Array"]
        RX0["Rx0 (Upper Left Antenna)"]
        RX1["Rx1 (Reference / Vertex Antenna)"]
        RX2["Rx2 (Lower Center Antenna)"]

        RX0 ---|Horizontal Baseline d_h = 15.5 mm| RX1
        RX1 ---|Vertical Baseline d_v = 14.8 mm| RX2
    end
```

### 2.1 Spatial Anti-Aliasing Invariant & Channel 9 Physics

In any interferometric phase system, the phase difference $\Delta\psi$ is periodic over $2\pi$ radians ($[-\pi, +\pi]$). If the physical antenna separation $d$ exceeds half a wavelength ($\frac{\lambda}{2}$), a single measured phase difference maps to multiple candidate angles in space, introducing catastrophic spatial grating lobes (phase wrap ambiguity).

For Apple's primary UWB Channel 9 ($f_c = 7987.2 \text{ MHz}$):

$$\lambda = \frac{c}{f_c} = \frac{299,792,458 \text{ m/s}}{7987.2 \times 10^6 \text{ s}^{-1}} = 37.534 \text{ mm}$$

$$\frac{\lambda}{2} = \frac{37.534 \text{ mm}}{2} = 18.767 \text{ mm}$$

The physical measurements of the iPhone 18,3 array strictly satisfy:

$$d_h = 15.5 \text{ mm} < \frac{\lambda}{2} = 18.767 \text{ mm} \quad \left(\frac{d_h}{\lambda} \approx 0.413\right)$$

$$d_v = 14.8 \text{ mm} < \frac{\lambda}{2} = 18.767 \text{ mm} \quad \left(\frac{d_v}{\lambda} \approx 0.394\right)$$

Because both physical baselines are strictly less than $\frac{\lambda}{2}$, the maximum possible physical phase difference across the forward hemispherical field of view ($-\frac{\pi}{2} \le \theta \le +\frac{\pi}{2}$) cannot exceed:

$$|\Delta\psi_{\text{max}}| = \frac{2\pi d_h}{\lambda} \sin\left(\frac{\pi}{2}\right) = 2\pi (0.413) \approx 0.826\pi \text{ radians} < \pi \text{ radians}$$

This mathematical inequality **completely eliminates $2\pi$ phase ambiguity**, ensuring that every measured PDoA value maps uniquely to a single bearing angle without requiring multi-baseline disambiguation filters.

---

## 3. Mathematical Derivations of Azimuth and Elevation

Let the received carrier signal at antenna element $k$ be modeled as:

$$s_k(t) = A_k \exp\left(j\left(2\pi f_c t + \psi_k(t)\right)\right)$$

The MMS32 Vector DSP computes the relative phase across the two orthogonal pairs:
- Horizontal pair $(Rx0, Rx1)$: $\Delta\psi_{01} = \psi_{\text{Rx0}} - \psi_{\text{Rx1}}$
- Vertical pair $(Rx1, Rx2)$: $\Delta\psi_{12} = \psi_{\text{Rx1}} - \psi_{\text{Rx2}}$

### 3.1 Geometric Phase-to-Angle Relationship

The physical path delay $\Delta L$ corresponding to an incident angle $\theta$ is $\Delta L = d \sin(\theta)$. The phase shift across the baseline is given by:

$$\Delta\psi = \frac{2\pi}{\lambda} \Delta L = \frac{2\pi d}{\lambda} \sin(\theta)$$

Solving for the incident angle:

$$\sin(\theta) = \frac{\lambda \cdot \Delta\psi}{2\pi d}$$

$$\theta = \arcsin\left(\frac{\lambda \cdot \Delta\psi}{2\pi d}\right)$$

Applying the physical parameters of the iPhone 18,3 array:

### 3.2 Closed-Form Azimuth Equation

$$\theta_{\text{azimuth}} = \arcsin\left(\frac{37.534 \text{ mm} \cdot \Delta\psi_{01}}{2\pi \cdot 15.5 \text{ mm}}\right) = \arcsin\left(\frac{37.534}{97.389} \cdot \Delta\psi_{01}\right) \approx \arcsin\left(0.3854 \cdot \Delta\psi_{01}\right)$$

### 3.3 Closed-Form Elevation Equation

$$\phi_{\text{elevation}} = \arcsin\left(\frac{37.534 \text{ mm} \cdot \Delta\psi_{12}}{2\pi \cdot 14.8 \text{ mm}}\right) = \arcsin\left(\frac{37.534}{92.991} \cdot \Delta\psi_{12}\right) \approx \arcsin\left(0.4036 \cdot \Delta\psi_{12}\right)$$

### 3.4 Carrier Frequency Offset (CFO) Phase Drift Compensation

During the reception of the ranging frame, any residual frequency offset $\Delta f_{\text{CFO}}$ between the sender and receiver oscillators causes linear phase rotation over time:

$$\psi_{\text{drift}}(t) = 2\pi \cdot \Delta f_{\text{CFO}} \cdot t$$

The MMS32 DSP estimates $\Delta f_{\text{CFO}}$ from the preamble repetition pattern and rotates the received I/Q vectors by $-\psi_{\text{drift}}(t)$ prior to phase extraction, preventing temporal phase drift from corrupting the spatial PDoA measurement.

---

## 4. DeviceTree Spherical Calibration Architecture

In production hardware, the metallic chassis, display panel, glass back, and battery introduce localized electromagnetic refraction and phase distortion. Apple compensates for these distortions via the **DeviceTree Spherical Calibration** node located at `/arm-io/rose` in `artifacts/dcp/devicetree_unpacked.raw`.

### 4.1 Q16.16 Fixed-Point Numeric Format

Angles in the devicetree are formatted in signed **Q16.16 fixed-point radians**, where:

$$\text{Radian Value} = \frac{\text{Raw Integer Value}}{65536.0}$$

$$\text{Degree Value} = \text{Radian Value} \times \frac{180.0}{\pi}$$

### 4.2 Comprehensive Extracted Calibration Parameters

Extracted directly from offset `0x1c900` of `artifacts/dcp/devicetree_unpacked.raw`:

| Property Name | Raw Hex | Signed Int | Decoded Radians | Decoded Degrees | Functional Calibration Purpose |
|:---|:---:|:---:|:---:|:---:|:---|
| `theta-attach-high-cal` | `0x0002f851` | `194641` | **2.970108 rad** | **170.174°** | Maximum azimuth boundary to attach/lock directional tracking |
| `theta-attach-low-cal` | `0x00000000` | `0` | **0.000000 rad** | **0.000°** | Minimum azimuth boundary for tracking attachment |
| `theta-detach-high-cal` | `0x000323d7` | `205783` | **3.139999 rad** | **179.914°** | Maximum azimuth boundary before detaching directional tracking |
| `theta-detach-low-cal` | `0x00002b85` | `11141` | **0.170000 rad** | **9.740°** | Minimum azimuth boundary before detaching directional tracking |
| `phi-attach-high-cal` | `0xfffd9c29` | `-156631` | **-2.389999 rad** | **-136.936°** | Maximum negative elevation for tracking attachment |
| `phi-attach-low-cal` | `0x0001851e` | `99614` | **1.519989 rad** | **87.089°** | Maximum positive elevation for tracking attachment |
| `phi-detach-high-cal` | `0x0000c000` | `49152` | **0.750000 rad** | **42.972°** | Upper elevation threshold to break tracking lock |
| `phi-detach-low-cal` | `0xfffe6148` | `-106168` | **-1.619995 rad** | **-92.819°** | Lower elevation threshold to break tracking lock |
| `phi-ignore-high-cal` | `0x0002b5c2` | `177602` | **2.709991 rad** | **155.271°** | Elevation sector ignored due to camera bump reflection |
| `phi-ignore-low-cal` | `0x000070a3` | `28835` | **0.439987 rad** | **25.210°** | Elevation sector ignored due to chassis boundary reflection |
| `std-dev-x-cal` | `0x00430000` | `4390912` | Scaled: **67.0** | N/A | X-axis angular covariance measurement noise |
| `std-dev-y-cal` | `0x00410000` | `4259840` | Scaled: **65.0** | N/A | Y-axis angular covariance measurement noise |
| `std-dev-z-cal` | `0x001e0000` | `1966080` | Scaled: **30.0** | N/A | Z-axis range covariance measurement noise |
| `magnitude-cal` | `0x03070000` | `50790400` | Raw: `50790400` | N/A | Front-end AGC magnitude normalization baseline |

```mermaid
stateDiagram-v2
    [*] --> Detached_State: Boot / Target Out of View
    
    Detached_State --> Attached_Tracking: Bearing crosses Attach Cone [0.0° to 170.2°]
    Attached_Tracking --> Detached_State: Bearing exits Detach Cone [<9.7° or >179.9°]
    
    state Attached_Tracking {
        Active_Guidance: Render UI Arrow (Find My / SharePlay)
        ARKit_Fusion: Blend UWB Vector with VIO Coordinate Frame
    }

    state Detached_State {
        Search_Mode: Render "Move Around" Pulse UI
        Coarse_Distance_Only: Stream ToF Distance without Bearing
    }
```

### 4.3 Attach vs Detach Hysteresis Cone Mechanics

Notice the deliberate difference between the **Attach** and **Detach** thresholds:
- Azimuth Attach High: $170.174^\circ$, but Azimuth Detach High: $179.914^\circ$
- Azimuth Attach Low: $0.000^\circ$, but Azimuth Detach Low: $9.740^\circ$

This design establishes a **$9.7^\circ$ angular hysteresis window**. In practice, when an iPhone user points their phone toward an AirTag, the directional guidance arrow locks onto the target as soon as the angle enters the inner attach cone. As the user walks or tilts the phone, small hand tremors or multipath fluctuations will not cause the arrow to flicker or break lock unless the angle exits the wider detach envelope. This hysteresis guarantees fluid, rock-solid UI rendering in Find My Precision Finding.

---

## 5. DSP Execution Pipeline (`ALGO _run_toa_aoa_algo_r2`)

When a ranging packet arrives, the Cortex-M microkernel hands the CIR buffers to the MMS32 DSP coprocessor via the routine `ALGO _run_toa_aoa_algo_r2`. As logged in `_osl.bin`:
`GR0S DSP completed: azi = %hd, ele = %hd pdoa = %hd %hd`
`GR3M DSP completed: GD_Bulk = %u, sts_valid = %u, aoa_unc = %x`

1. **PDoA Extraction:** Measures raw horizontal and vertical phase differences (`raw_pdoa_h`, `raw_pdoa_v`).
2. **Arcsin Trigonometric Solver:** Evaluates the closed-form azimuth and elevation equations.
3. **Centidegree Output Conversion:** Formats angles as 16-bit signed integers in hundredths of a degree (e.g., $1762 \to 17.62^\circ$).
4. **Covariance Matrix (`aoa_unc`):** Synthesizes angular uncertainty using the devicetree standard deviation scalars (`std_dev_x`, `std_dev_y`, `std_dev_z`) and feeds the resulting 3D vector to host `nearbyd`.

---

## 6. Verification Cross-Reference Table

| Calibration / Equation Parameter | Extracted Value | Target File | Verification Gate |
|:---|:---:|:---|:---:|
| Horizontal Baseline $d_h$ | `15.5 mm` | `aoa_pdoa_localization_spec.json` | Gate 5 |
| Vertical Baseline $d_v$ | `14.8 mm` | `rose_aoa_pdoa.h` | Gate 5 |
| Channel 9 $\lambda$ | `37.534 mm` | `pseudocode/rose_aoa_pdoa.h` | Gate 5 |
| Spatial Anti-Aliasing | $d < \lambda / 2$ | `cross_validation_matrix.json` | Gate 5 |
| Azimuth Formula | Analytical Arcsin | `verify_rose_uwb_extraction.py` | Gate 5 |
| `theta-attach-high-cal` | `194641 (2.970 rad)` | `artifacts/dcp/devicetree_unpacked.raw` | Gate 6 |
| `theta-detach-high-cal` | `205783 (3.140 rad)` | `artifacts/dcp/devicetree_unpacked.raw` | Gate 6 |
| `phi-attach-high-cal` | `-156631 (-2.390 rad)` | `artifacts/dcp/devicetree_unpacked.raw` | Gate 6 |
| Logging Symbol | `GR0S DSP completed` | `artifacts/rose/decompressed/_osl.bin` | Gate 6 |
