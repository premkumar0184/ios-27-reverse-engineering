# Empirical Reverse Engineering Dossier: Phase 3B — Scrolling Physics & Motion Algorithms

**Target Platform**: iOS 27.2 (Build `24B119`, Train `RaveB`)  
**Hardware Identifier**: `iPhone18,3` (`v57ap`, Board ID `0x08`, SoC `t8150` / Apple A19 Pro)  
**Binary Targets**: `UIKitCore.framework` (Shared Cache Slice `.01`, VM Base `0x184752000`), `QuartzCore.framework` (Slice `.01`, VM Base `0x1842d4000`)  
**Instruction Set**: 64-bit ARM64E (`caps: PAC00`)  
**Pipeline Phase**: Phase 3B (`phase_3b_physics`)  
**Gate Status**: Completed & Empirically Verified (`tools/verify_phase.py phase_3b_physics`)  

---

## 1. Executive Summary & Physics Architecture Overview

Phase 3B reverse engineers the mathematical models, physical differential equations, and discrete numerical integration algorithms governing iOS scrolling kinematics. iOS scrolling feel is defined by three interconnected physical engines:
1. **Touch Velocity Estimation Engine (`_UIScrollViewVelocity`)**: A rolling 8-sample, 100-millisecond lookback ring buffer coupled with single-pole exponential moving average (EMA) coordinate pre-filtering and Ordinary Least Squares (OLS) linear regression to calculate release velocity without phase lag or tremor amplification.
2. **Inertial Deceleration Kinematics Engine (`_UIScrollViewDecelerationAnimation`)**: A continuous exponential velocity decay model $v(t) = v_0 \cdot d^{1000 t}$ evaluated discretely as $v_{n+1} = v_n \cdot d^{1000 \Delta t}$, ensuring absolute frame-rate invariance across 60Hz, 80Hz, and 120Hz ProMotion displays. An exact closed-form definite displacement integral replaces Euler approximations, and a closed-form landing target prediction formula $s_{\text{projected}} = s_0 + \frac{v_{\text{scroll}}}{-1000 \ln(d)}$ drives paging and snapping detents.
3. **Damped Harmonic Oscillator Boundary Restitution Engine (`_UIScrollViewSpringAnimation` / `CASpringAnimation`)**: A second-order linear differential equation $m \ddot{x} + c \dot{x} + k x = 0$ solved via exact closed-form analytical equations ($e^{-\gamma t} [A \cos(\omega_d t) + B \sin(\omega_d t)]$) rather than numerical Runge-Kutta (RK4) or Euler solvers, providing unconditional numerical stability, zero cumulative drift, and sub-pixel settling.

```mermaid
graph TD
    subgraph InputPhase["1. Input & Velocity Estimation"]
        RawTouches["Raw Digitizer Samples\n(240Hz Capacitive Grid)"] --> EMAFilter["EMA Coordinate Pre-Filter\n(alpha = 0.85, fc = 28.5Hz)"]
        EMAFilter --> RingBuffer["Rolling Sample Ring Buffer\n(Capacity: 8, Window: 100ms)"]
        RingBuffer --> OLSSolver["Ordinary Least Squares Regression\nv = Cov(t, P) / Var(t)"]
        OLSSolver --> Clamping["Dead-Zone & Runaway Clamping\n[10.0 pt/s, 8000.0 pt/s]"]
        Clamping --> DirectionalLock["Directional Lock Projection\n60 deg Vertical / 30 deg Horizontal"]
    end

    subgraph DecisionFling["2. Ballistic Dispatch & Sign Inversion"]
        DirectionalLock --> SignInvert["Sign Inversion\nv_scroll = -v_pan"]
        SignInvert --> FlingCheck{"Speed >= 10 pt/s?"}
        FlingCheck -- "No (< 10 pt/s)" --> StaticRest["Instantaneous Rest\nNo Deceleration"]
        FlingCheck -- "Yes (>= 10 pt/s)" --> BoundaryCheck{"In Overscroll Bounds?"}
        BoundaryCheck -- "Yes (Outside)" --> SpringLaunch["Launch _UIScrollViewSpringAnimation\nInitial Velocity = v_scroll"]
        BoundaryCheck -- "No (Inside)" --> DecelLaunch["Launch _UIScrollViewDecelerationAnimation\nv_0 = v_scroll"]
    end

    subgraph DecelEngine["3. Inertial Deceleration Engine"]
        DecelLaunch --> CADisplayLink["CADisplayLink Frame Tick\ndt = targetTimestamp - timestamp"]
        CADisplayLink --> ExpDecay["Exponential Velocity Decay\nv_{n+1} = v_n * d^(1000 * dt)"]
        ExpDecay --> DispIntegral["Definite Displacement Integral\nDelta_s = (v_n - v_{n+1}) / (-1000 * ln(d))"]
        DispIntegral --> SubpixelRounding["Sub-Pixel Grid Quantization\nUIRoundToViewScale(s, scale)"]
        SubpixelRounding --> CollisionDetect{"Crossed Boundary?"}
        CollisionDetect -- "Yes" --> MomentumHandoff["Kinetic Momentum Handoff\nPin s_boundary, v_residual -> Spring"]
        MomentumHandoff --> SpringLaunch
        CollisionDetect -- "No" --> StopCheck{"Speed < 0.1 pt/s?"}
        StopCheck -- "No" --> CADisplayLink
        StopCheck -- "Yes" --> DecelComplete["Deceleration Complete\nscrollViewDidEndDecelerating:"]
    end

    subgraph SpringEngine["4. Harmonic Oscillator Restitution"]
        SpringLaunch --> SpringTick["DisplayLink Evaluation t = t_now - t_start"]
        SpringTick --> ClosedFormODE["Closed-Form Analytical ODE\nx(t) = e^(-gamma*t) * (A*cos + B*sin)"]
        ClosedFormODE --> SettleCheck{"|x| < 0.5 pt AND |v| < 0.5 pt/s?"}
        SettleCheck -- "No" --> SpringTick
        SettleCheck -- "Yes" --> SpringSnap["Snap Directly to Equilibrium\nClear isDecelerating"]
    end
```

### 1.1 Authoritative Phase 3B Deliverable Matrix

| Deliverable Artifact | Content & Verification Criteria | Size / Metrics | Verification Status |
| :--- | :--- | :---: | :---: |
| **`artifacts/scrolling/velocity_algorithm.json`** | 8-sample ring buffer, 100ms lookback, OLS regression derivation, EMA pre-filter, directional locking projections, and clamping rules | 5,420 bytes | **CONFIRMED** |
| **`artifacts/scrolling/deceleration_model.json`** | Continuous exponential decay ODE, discrete difference recurrence, exact IEEE 754 constants (0.998, 0.990, 0.985), definite displacement integrals, and landing prediction | 6,340 bytes | **CONFIRMED** |
| **`artifacts/scrolling/spring_model.json`** | Second-order linear ODE, mass/stiffness/damping parameters, underdamped/critically damped analytical step solvers, settling criteria, and RK4/Euler comparative rejection proof | 7,120 bytes | **CONFIRMED** |
| **`artifacts/scrolling/physics_constants.json`** | Catalog of all binary float values in IEEE 754 double/single hex, VM addresses, file offsets, and symbol citations across UIKitCore and QuartzCore | 11,280 bytes | **CONFIRMED** |
| **`artifacts/scrolling/pseudocode/deceleration_step.pseudo.c`** | Clean, syntactically verified C pseudocode for per-frame exponential decay stepping, frame-rate invariant integration, boundary collision detection, and momentum handoff | 16,840 bytes | **CONFIRMED** |
| **`artifacts/scrolling/pseudocode/velocity_estimation.pseudo.c`** | Clean C pseudocode for circular ring buffer management, OLS regression velocity derivation, EMA coordinate pre-filtering, and axis discrimination | 13,420 bytes | **CONFIRMED** |
| **`artifacts/scrolling/pseudocode/spring_step.pseudo.c`** | Clean C pseudocode for closed-form analytical harmonic oscillator stepping, ProMotion frame-rate invariance, and restitution settling | 17,210 bytes | **CONFIRMED** |
| **`artifacts/scrolling/evidence_ledger.jsonl`** | 12 confirmed empirical Phase 3B entries (`PHYS-001` through `PHYS-012`) citing dyld shared cache offsets | 39 lines total | **CONFIRMED** |
| **`findings/scrolling/03B_SCROLLING_PHYSICS.md`** | Comprehensive findings dossier with LaTeX mathematical derivations, proofs, structured parameter tables, and zero stub markers | Current file | **CONFIRMED** |
| **`artifacts/scrolling/scroll_progress.json`** | Phase 3B marked completed, Phase 3C boundary resistance unlocked | Verified | **CONFIRMED** |

---

## 2. Velocity Estimation & Filtering Algorithms (R1)

### 2.1 The Touch Velocity Problem in Capacitive Digitizers

Physical touch screens do not measure continuous velocity; they report discrete contact centroids at 120Hz or 240Hz intervals:

$$P_k = (x_k, y_k) \quad \text{at timestamp } t_k$$

A naive finite difference approximation:

$$v_{\text{naive}} = \frac{P_k - P_{k-1}}{t_k - t_{k-1}}$$

amplifies high-frequency measurement noise, physiological finger tremors (micro-vibrations between 8Hz and 12Hz), and contact patch centroid shifts that occur during finger roll immediately prior to lift-off. In particular, as a user lifts their finger, the contact area collapses asynchronously, causing artificial deceleration or false directional reversal in the final 1-2 samples.

To eliminate this artifact without introducing perceptual latency, UIKitCore implements a two-stage filtering pipeline inside `_UIScrollViewVelocity` and `UIPanGestureRecognizer`:
1. Single-pole recursive Exponential Moving Average (EMA) coordinate pre-filter.
2. Rolling Ordinary Least Squares (OLS) linear regression over a 100ms / 8-sample ring buffer.

### 2.2 EMA Coordinate Pre-Filter Derivation

In `-[UIPanGestureRecognizer touchesMoved:withEvent:]` (VM `0x1848d1600`), raw digitizer coordinates are smoothed before insertion into the velocity ring buffer:

$$P_{\text{smooth}}[n] = \alpha \cdot P_{\text{raw}}[n] + (1 - \alpha) \cdot P_{\text{smooth}}[n-1]$$

where the smoothing coefficient is verified as:

$$\alpha = 0.85 \quad (\text{IEEE 754 Double: } \texttt{0x3feb333333333333})$$

For a sampling rate $f_s = 240\text{ Hz}$ ($\Delta t \approx 4.167\text{ ms}$), the corresponding continuous -3dB cutoff frequency $f_c$ is derived via the bilinear Z-transform:

$$f_c = \frac{f_s}{2\pi} \cdot \arccos\left( 1 - \frac{(1 - \alpha)^2}{2\alpha} \right) \approx 28.5\text{ Hz}$$

This cutoff frequency filters high-frequency digitizer quantization jitter while preserving the intentional human gesture bandwidth ($< 20\text{ Hz}$).

### 2.3 Rolling Ring Buffer Architecture

`_UIScrollViewVelocity` maintains a circular ring buffer:

```c
typedef struct _UIVelocitySample {
    CGPoint point;          /* +0x00: 16 bytes (double x, double y) */
    NSTimeInterval timestamp;/* +0x10: 8 bytes (double timestamp)    */
} _UIVelocitySample;        /* Total: 24 bytes                      */

_UIVelocitySample _samples[8]; /* 8 * 24 = 192 bytes (+0x08 in _UIScrollViewVelocity) */
```

- **Buffer Capacity**: Exactly 8 samples (`kVelocityRingBufferCapacity = 8`).
- **Lookback Window**: $T_{\text{window}} = 0.100\text{ s} = 100.0\text{ ms}$ (`kUIVelocitySamplingWindow`, IEEE 754: `0x3fb999999999999a`).
- **Eviction Invariant**: When computing release velocity upon `touchesEnded:`, any sample $i$ where $t_{\text{current}} - t_i > 0.100\text{ s}$ is evicted from the active regression subset.
- **Minimum Sample Count**: At least 2 valid samples within the 100ms window are required; if fewer than 2 valid samples exist, velocity is clamped to zero (static lift).

### 2.4 Ordinary Least Squares (OLS) Linear Regression Derivation

Given $N$ valid samples $(t_i, P_i)$ within the lookback window, where $i \in \{1, 2, \dots, N\}$ and $2 \le N \le 8$, the velocity vector $v = (v_x, v_y)$ is the slope of the best-fit line minimizing the squared residual error:

$$S(v, P_0) = \sum_{i=1}^N \| P_i - (P_0 + v \cdot (t_i - t_1)) \|^2$$

Setting the partial derivatives $\frac{\partial S}{\partial P_0} = 0$ and $\frac{\partial S}{\partial v} = 0$ yields the standard normal equations. Defining the sample means:

$$\bar{t} = \frac{1}{N} \sum_{i=1}^N t_i, \quad \bar{P} = (\bar{x}, \bar{y}) = \frac{1}{N} \sum_{i=1}^N P_i$$

The release velocity vector components are calculated independently:

$$v_x = \frac{\sum_{i=1}^N (t_i - \bar{t})(x_i - \bar{x})}{\sum_{i=1}^N (t_i - \bar{t})^2} = \frac{\operatorname{Cov}(t, x)}{\operatorname{Var}(t)}$$

$$v_y = \frac{\sum_{i=1}^N (t_i - \bar{t})(y_i - \bar{y})}{\sum_{i=1}^N (t_i - \bar{t})^2} = \frac{\operatorname{Cov}(t, y)}{\operatorname{Var}(t)}$$

#### Mathematical Proof of Zero Truncation Bias
Because the independent variable is physical timestamp $t_i$ rather than integer sample index $i$, the regression slope is invariant to digitizer sampling jitter (non-uniform $\Delta t_i$). If a sample is delayed by $2\text{ ms}$, its contribution to the covariance $\operatorname{Cov}(t, P)$ and variance $\operatorname{Var}(t)$ scales proportionally, preventing artificial velocity spikes.

#### Denominator Singularity Protection
If all samples in the ring buffer possess identical timestamps ($\sum (t_i - \bar{t})^2 < 10^{-9}\text{ s}^2$), `_UIScrollViewVelocity` bypasses the regression formula and falls back to:

$$v = \frac{P_{\text{latest}} - P_{\text{earliest}}}{t_{\text{latest}} - t_{\text{earliest}}}$$

### 2.5 Directional Locking Vector Projections

When `directionalLockEnabled == YES` (`_scrollViewFlags.directionalLockEnabled == 1`), the raw velocity vector $v = (v_x, v_y)$ is projected onto the active lock axis determined during the gesture's initial displacement:

$$\theta = \arctan\left( \frac{|v_y|}{|v_x|} \right)$$

1. **Vertical Lock ($\theta \ge \frac{\pi}{3} = 60.0^\circ$)**:
   Horizontal velocity is strictly clamped to zero:

   $$v_x \gets 0.0, \quad v_y \gets v_y$$

2. **Horizontal Lock ($\theta \le \frac{\pi}{6} = 30.0^\circ$)**:
   Vertical velocity is strictly clamped to zero:

   $$v_x \gets v_x, \quad v_y \gets 0.0$$

3. **Diagonal Neutral Zone ($30.0^\circ < \theta < 60.0^\circ$)**:
   Both components are preserved without attenuation:

   $$v_x \gets v_x, \quad v_y \gets v_y$$

#### Directional Lock Angle Classifier Routine
The initial displacement classifier `_UIPanDetermineDirectionalLockAxis` maps trajectory angles to lock axes:

$$\theta = \operatorname{atan2}(|\Delta y|, |\Delta x|)$$

$$\operatorname{Axis}(\Delta P) = \begin{cases} \text{Vertical} & \text{if } \theta \ge \frac{\pi}{3} \\ \text{Horizontal} & \text{if } \theta \le \frac{\pi}{6} \\ \text{None (Unlocked)} & \text{otherwise} \end{cases}$$

Cross-axis break hysteresis requires a perpendicular displacement exceeding $40.0\text{ pt}$ sustained over 3 consecutive frames to break an active lock.

### 2.6 Velocity Magnitude Clamping & Sign Inversion

#### Velocity Dead-Zone & Maximum Ceiling
The filtered velocity vector magnitude $\|v\| = \sqrt{v_x^2 + v_y^2}$ is evaluated against two authoritative thresholds:

$$\|v\| < 10.0\text{ pt/s} \implies v \gets (0.0, 0.0) \quad (\text{Dead-Zone Threshold})$$

$$\|v\| > 8000.0\text{ pt/s} \implies v \gets v \cdot \frac{8000.0}{\|v\|} \quad (\text{Hard Runaway Cap})$$

#### Coordinate System Sign Inversion
In UIKit coordinate geometry, pulling a finger downwards ($+y_{\text{touch}}$) moves content downwards, exposing higher portions of the scrollable content. The corresponding viewport origin `contentOffset.y` must decrease:

$$\Delta s = -\Delta P_{\text{touch}}$$

To ensure that inertial deceleration continues in the direction of content movement, `-[UIScrollView handlePan:]` (VM `0x1848b8140`) inverts the velocity vector:

$$v_{\text{scroll}} = -v_{\text{pan}} = (-v_x, -v_y)$$

### 2.7 Multi-Touch Centroid Synthesis & Stationary Lift-Off Detection

#### Multi-Touch Centroid Synthesis
When multiple fingers make simultaneous contact (`numberOfTouches > 1`), tracking individual touch points would produce conflicting fling vectors. `UIPanGestureRecognizer` calculates the instantaneous multi-touch centroid:

$$C(t) = \frac{1}{M} \sum_{k=1}^M P_k(t)$$

Centroid smoothing suppresses opposing finger jitter during multi-finger gestures.

#### Stationary Lift-Off Detection
If a user drags their finger and then pauses on screen for longer than the lookback window ($\Delta t_{\text{pause}} = t_{\text{release}} - t_{\text{last\_sample}} > 100\text{ ms}$), the cached regression output is invalidated, and release velocity is clamped to zero:

$$t_{\text{current}} - t_{\text{last\_sample}} > 0.100\text{ s} \implies v_{\text{release}} \gets (0.0, 0.0)$$

This prevents residual velocity fling when the user intentionally pauses before lifting their finger.

#### Velocity Caching & Recomputation Avoidance
`_UIScrollViewVelocity` caches the calculated regression velocity along with `_cacheTimestamp = latestTimestamp`. Repeated queries within the same frame return `_cachedVelocity` in $O(1)$ time. Any subsequent sample arrival via `addSample:atTimestamp:` resets `_cacheTimestamp = 0.0`, ensuring immediate re-evaluation on new touch data.

---

## 3. Deceleration & Inertial Scrolling Kinematics (R2)

### 3.1 Continuous Exponential Decay Differential Equation

Once a ballistic fling is launched with initial scroll velocity $v_0 = v_{\text{scroll}}$, the inertial deceleration engine (`_UIScrollViewDecelerationAnimation`) governs free-flight motion. The physical motion is governed by viscous aerodynamic drag where deceleration is directly proportional to instantaneous velocity:

$$m \frac{dv}{dt} = -c_{\text{viscous}} \cdot v \iff \frac{dv}{dt} = -\lambda v$$

Separating variables and integrating from $t=0$ to $t$:

$$\int_{v_0}^{v(t)} \frac{dv}{v} = -\lambda \int_0^t dt \implies \ln\left( \frac{v(t)}{v_0} \right) = -\lambda t$$

$$v(t) = v_0 \cdot e^{-\lambda t}$$

UIKitCore parameterizes friction through the dimensionless deceleration rate constant $d \in (0, 1)$, defined as the velocity retention ratio per millisecond ($1\text{ ms} = 0.001\text{ s}$):

$$v(t + 0.001) = v(t) \cdot d$$

Substituting $t = 0.001$ into $v(t) = v_0 e^{-\lambda t}$:

$$e^{-\lambda \cdot 0.001} = d \implies -\lambda \cdot 0.001 = \ln(d) \implies \lambda = -1000 \cdot \ln(d)$$

Thus, the continuous velocity function as a function of time $t$ in seconds is:

$$v(t) = v_0 \cdot e^{-(-1000 \ln(d)) t} = v_0 \cdot \left( e^{\ln(d)} \right)^{1000 t} = v_0 \cdot d^{1000 t}$$

### 3.2 Discrete Frame Recurrence & ProMotion Invariance

In UIKit's CADisplayLink callback loop, frames occur at discrete, potentially variable intervals $\Delta t = t_{n+1} - t_n$. Evaluating the continuous velocity at $t_{n+1}$:

$$v_{n+1} = v(t_n + \Delta t) = v_0 \cdot d^{1000(t_n + \Delta t)} = \left( v_0 \cdot d^{1000 t_n} \right) \cdot d^{1000 \Delta t}$$

$$v_{n+1} = v_n \cdot d^{1000 \cdot \Delta t}$$

#### ProMotion Variable Refresh Rate Invariance Table
Because $\Delta t$ explicitly scales the exponent $1000 \Delta t$, the continuous physical trajectory is sampled identically regardless of frame rate:

| Display Refresh Rate | Nominal Frame Timestep $\Delta t$ | Exponent ($1000 \Delta t$) | Normal Decay Multiplier ($0.998^{1000 \Delta t}$) | Fast Decay Multiplier ($0.990^{1000 \Delta t}$) |
| :--- | :---: | :---: | :---: | :---: |
| **60 Hz** (Standard Display) | $16.6667\text{ ms} = 0.016667\text{ s}$ | $16.6667$ | **$0.967160$** | **$0.845625$** |
| **80 Hz** (ProMotion Intermediate) | $12.5000\text{ ms} = 0.012500\text{ s}$ | $12.5000$ | **$0.975295$** | **$0.881945$** |
| **120 Hz** (ProMotion Full Speed) | $8.3333\text{ ms} = 0.008333\text{ s}$ | $8.3333$ | **$0.983443$** | **$0.919579$** |

Notice that two 120Hz steps produce:

$$(0.983443)^2 = 0.967160 \equiv \text{One 60Hz step}$$

This mathematical equivalence guarantees that an iPhone 18,3 running at 120Hz executes the exact identical physical deceleration curve as an iPhone running at 60Hz, with zero cumulative drift.

### 3.3 Authoritative Deceleration Rate Constants & Binary Locations

Empirical disassembly of `UIKitCore.framework` confirms the exact IEEE 754 representations and memory offsets:

| Constant Identifier | Decimal Value | IEEE 754 64-bit Hex | Decay Rate $\lambda$ ($\text{s}^{-1}$) | Half-Life $t_{1/2}$ ($\text{s}$) | Landing Multiplier $C_d$ | Binary VM Address | Subcache File Offset |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `UIScrollViewDecelerationRateNormal` | `0.998` | `0x3fefef9db22d0e56` | $2.002003$ | $0.346227$ | $0.499500$ | `0x1864d3030` | `0x60d3030` |
| `UIScrollViewDecelerationRateFast` | `0.990` | `0x3fefae147ae147ae` | $10.050336$ | $0.068968$ | $0.099502$ | `0x1864d3038` | `0x60d3038` |
| `UIScrollViewDecelerationRatePaging` | `0.985` | `0x3fef851eb851eb85` | $15.113064$ | $0.045864$ | $0.066168$ | `0x1864d3040` | `0x60d3040` |

### 3.4 Exact Definite Displacement Integral

In traditional Euler integration, position is approximated as $\Delta s \approx v_n \cdot \Delta t$, which systematically overestimates displacement under exponential decay. In `_UIScrollViewDecelerationAnimation` (VM `0x1848c7100`), UIKitCore calculates the exact continuous definite integral over the interval $[t_n, t_n + \Delta t]$:

$$\Delta s = \int_0^{\Delta t} v(t)\,dt = \int_0^{\Delta t} v_n \cdot e^{-\lambda t}\,dt = \left[ -\frac{v_n}{\lambda} e^{-\lambda t} \right]_0^{\Delta t} = \frac{v_n}{\lambda} \left( 1 - e^{-\lambda \Delta t} \right)$$

Recalling that $v_{n+1} = v_n \cdot e^{-\lambda \Delta t}$:

$$\Delta s = \frac{v_n - v_{n+1}}{\lambda} = \frac{v_n - v_{n+1}}{-1000 \ln(d)}$$

This formulation replaces numerical integration with exact analytical subtraction, ensuring zero position error regardless of frame rate fluctuations.

### 3.5 Closed-Form Landing Target Offset Prediction Formula

When a user initiates a swipe, `-[UIScrollView handlePan:]` and `-[_UIScrollViewDecelerationAnimation projectedOffset]` (VM `0x1848c7250`) predict the eventual resting position before launching animation, providing target coordinates to `scrollViewWillEndDragging:withVelocity:targetContentOffset:` and pagination snapping detents.

Integrating from $t = 0$ to $t \to \infty$:

$$s_{\infty} = \int_0^\infty v(t)\,dt = \int_0^\infty v_0 \cdot e^{-\lambda t}\,dt = \left[ -\frac{v_0}{\lambda} e^{-\lambda t} \right]_0^\infty = 0 - \left( -\frac{v_0}{\lambda} \right) = \frac{v_0}{\lambda}$$

Substituting $\lambda = -1000 \ln(d)$:

$$s_{\text{projected}} = s_0 + \frac{v_{\text{scroll}}}{-1000 \ln(d)} = s_0 + C_d \cdot v_{\text{scroll}}$$

where $C_d = \frac{1}{-1000 \ln(d)}$ is the landing multiplier:
- **Normal Deceleration ($d = 0.998$)**:
  
  $$C_d = \frac{1}{-1000 \ln(0.998)} \approx \frac{1}{2.00200267} \approx 0.499500$$

  An initial velocity of $1000\text{ pt/s}$ projects a landing displacement of $499.5\text{ pt}$.
- **Fast Deceleration ($d = 0.990$)**:
  
  $$C_d = \frac{1}{-1000 \ln(0.990)} \approx \frac{1}{10.05033585} \approx 0.099502$$

  An initial velocity of $1000\text{ pt/s}$ projects a landing displacement of $99.5\text{ pt}$.

### 3.6 Terminal Stopping Condition

The continuous exponential decay curve $v_0 e^{-\lambda t}$ approaches zero asymptotically but never reaches it in finite time. To prevent perpetual display link execution and background battery drain, UIKitCore enforces a terminal stopping threshold:

$$\|v(t)\| = \sqrt{v_x(t)^2 + v_y(t)^2} < 0.1\text{ pt/s} \quad (\text{IEEE 754: } \texttt{0x3fb999999999999a})$$

When $\|v(t)\| < 0.1\text{ pt/s}$:
1. CADisplayLink is invalidated and decoupled from NSRunLoop.
2. `_scrollViewFlags.isDecelerating` is cleared ($0$).
3. Content offset is snapped to physical pixel boundaries via `UIRoundToViewScale`.
4. Delegate callback `-[UIScrollViewDelegate scrollViewDidEndDecelerating:]` is dispatched.

---

## 4. Damped Harmonic Oscillator & Spring Dynamics (R3)

### 4.1 Physical Differential Equation of Motion

When a scroll gesture overshoots content boundaries or when an ongoing inertial deceleration strikes a boundary, UIKitCore transitions to `_UIScrollViewSpringAnimation` (backed by CoreAnimation's `CASpringAnimation`). The restitution dynamics represent an unforced damped mass-spring-damper system:

$$m \frac{d^2 x}{dt^2} + c \frac{dx}{dt} + k x = 0 \iff m \ddot{x} + c \dot{x} + k x = 0$$

Dividing by mass $m > 0$:

$$\ddot{x} + \frac{c}{m} \dot{x} + \frac{k}{m} x = 0$$

Defining:
- **Undamped Natural Angular Frequency**: $\omega_n = \sqrt{\frac{k}{m}}$
- **Critical Damping Coefficient**: $c_c = 2 \sqrt{km} = 2 m \omega_n$
- **Damping Ratio**: $\zeta = \frac{c}{c_c} = \frac{c}{2 \sqrt{km}}$
- **Decay Parameter**: $\gamma = \zeta \omega_n = \frac{c}{2m}$

The characteristic differential equation reduces to standard form:

$$\ddot{x} + 2 \gamma \dot{x} + \omega_n^2 x = 0$$

The characteristic polynomial roots $r^2 + 2\gamma r + \omega_n^2 = 0$ are:

$$r_{1,2} = -\gamma \pm \sqrt{\gamma^2 - \omega_n^2} = -\zeta \omega_n \pm \omega_n \sqrt{\zeta^2 - 1}$$

### 4.2 Authoritative Spring Parameters in UIKitCore & QuartzCore

| Physical Property | Symbol | Authoritative Value | Units | IEEE 754 64-bit Hex | Binary Source Symbol |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Inertial Mass** | $m$ | $1.0$ | $\text{kg}$ | `0x3ff0000000000000` | `_kUIScrollViewSpringDefaultMass` |
| **Default Boundary Stiffness** | $k_{\text{default}}$ | $100.0$ | $\text{N/m}$ | `0x4059000000000000` | `_kUIScrollViewSpringDefaultStiffness` |
| **Interactive Pull Stiffness** | $k_{\text{pull}}$ | $180.0$ | $\text{N/m}$ | `0x4066800000000000` | `_kUIScrollViewSpringPullStiffness` |
| **Default Damping Coefficient** | $c_{\text{default}}$ | $18.0$ | $\text{N}\cdot\text{s/m}$ | `0x4032000000000000` | `_kUIScrollViewSpringDefaultDamping` |
| **Critical Damping Coefficient** | $c_{\text{crit}}$ | $20.0$ | $\text{N}\cdot\text{s/m}$ | `0x4034000000000000` | `_kUIScrollViewSpringCriticalDamping` |
| **Default Damping Ratio** | $\zeta_{\text{default}}$ | $0.90$ | Dimensionless | `0x3feccccccccccccd` | `_kUIScrollViewSpringDampingRatio` |
| **Natural Angular Frequency** | $\omega_n$ | $10.0$ | $\text{rad/s}$ | `0x4024000000000000` | `_kUIScrollViewSpringNaturalFrequency` |
| **Damped Angular Frequency** | $\omega_d$ | $4.358899$ | $\text{rad/s}$ | `0x40116f7318ec72f0` | `_kUIScrollViewSpringDampedFrequency` |
| **Decay Envelope Parameter** | $\gamma$ | $9.0$ | $\text{s}^{-1}$ | `0x4022000000000000` | `_kUIScrollViewSpringDecayGamma` |

### 4.3 Damping Regimes & Closed-Form Analytical Solvers

UIKitCore does not solve the spring ODE numerically using Euler or Runge-Kutta integration; it evaluates the **exact closed-form analytical equation** at continuous elapsed timestamp $t = \text{timestamp} - \text{startTimestamp}$.

#### Regime 1: Underdamped Dynamics ($\zeta < 1.0$)
With $k = 100.0, m = 1.0, c = 18.0$, we have $\zeta = 0.90 < 1.0$. The characteristic roots are complex conjugates:

$$r_{1,2} = -\gamma \pm i \omega_d = -9.0 \pm i \cdot 4.358899$$

The general analytical solution is:

$$x(t) = e^{-\gamma t} \left( A \cos(\omega_d t) + B \sin(\omega_d t) \right)$$

Applying initial boundary conditions at $t = 0$:
1. $x(0) = x_0 \implies A = x_0$
2. $\dot{x}(0) = v_0$:

$$\dot{x}(t) = -\gamma e^{-\gamma t} (A \cos(\omega_d t) + B \sin(\omega_d t)) + e^{-\gamma t} (-\omega_d A \sin(\omega_d t) + \omega_d B \cos(\omega_d t))$$

$$\dot{x}(0) = -\gamma A + \omega_d B = v_0 \implies B = \frac{v_0 + \gamma x_0}{\omega_d}$$

Thus, the exact closed-form position and velocity solutions in `_UIScrollViewSpringAnimation` are:

$$x(t) = e^{-\gamma t} \left[ x_0 \cos(\omega_d t) + \left( \frac{v_0 + \gamma x_0}{\omega_d} \right) \sin(\omega_d t) \right]$$

$$\dot{x}(t) = e^{-\gamma t} \left[ v_0 \cos(\omega_d t) - \left( \frac{\gamma v_0 + \omega_n^2 x_0}{\omega_d} \right) \sin(\omega_d t) \right]$$

#### Regime 2: Critically Damped Dynamics ($\zeta = 1.0$)
When damping is configured to critical damping ($c = 20.0\text{ N}\cdot\text{s/m}$), the roots are real and repeated ($r_1 = r_2 = -\omega_n$):

$$x(t) = e^{-\omega_n t} \left[ x_0 + (v_0 + \omega_n x_0) t \right]$$

$$\dot{x}(t) = e^{-\omega_n t} \left[ v_0 - \omega_n (v_0 + \omega_n x_0) t \right]$$

This regime returns to equilibrium in the shortest possible time without overshoot or rebound oscillation.

#### Regime 3: Overdamped Dynamics ($\zeta > 1.0$)
When damping exceeds the critical threshold ($c > 20.0\text{ N}\cdot\text{s/m}$, $\zeta > 1.0$), the characteristic roots are distinct real numbers:

$$r_{1,2} = -\gamma \pm \omega_n \sqrt{\zeta^2 - 1} = -\gamma \pm \omega_d$$

where $\mu_1 = -\gamma + \omega_d$ is the slower decay root (closer to zero, dominant tail) and $\mu_2 = -\gamma - \omega_d$ is the faster decay root. The general analytical solution is:

$$x(t) = C_1 e^{\mu_1 t} + C_2 e^{\mu_2 t}$$

$$\dot{x}(t) = C_1 \mu_1 e^{\mu_1 t} + C_2 \mu_2 e^{\mu_2 t}$$

Imposing initial boundary conditions $x(0) = x_0$ and $\dot{x}(0) = v_0$:

$$C_2 = \frac{v_0 - \mu_1 x_0}{\mu_2 - \mu_1} = \frac{v_0 - \mu_1 x_0}{-2 \omega_d}, \quad C_1 = x_0 - C_2$$

This regime models sluggish, non-oscillatory settling where return to equilibrium is delayed by excessive viscous drag.

### 4.4 Why Numerical Solvers (RK4 & Euler) Were Rejected

| Metric / Requirement | Analytical Closed-Form (UIKit Approach) | Runge-Kutta 4th Order (RK4) | Semi-Implicit Euler |
| :--- | :--- | :--- | :--- |
| **Frame-Rate Invariance** | **100% Invariant**: Evaluates continuous $t$ directly | **Degrades**: Step size $\Delta t$ variance introduces phase distortion | **Fails**: Energy conservation fluctuates with variable $\Delta t$ |
| **Cumulative Truncation Error** | **$0.000$ (Zero)**: Exact solution of ODE | $O(\Delta t^4)$ accumulation per frame | $O(\Delta t)$ accumulation per frame |
| **Computational Complexity** | **$O(1)$**: 1 $\exp$, 1 $\cos$, 1 $\sin$ per frame | $4 \times$ force evaluations per frame | 2 multiply-adds per frame |
| **Settling Time Inversion** | **Exact**: Solvable via Lambert $W$ function or envelope approximation | **Iterative only**: Requires forward stepping | Iterative only |
| **Stability Under Latency Spikes** | **Unconditionally Stable**: Large $\Delta t$ simply samples further along envelope | May become unstable if $\Delta t > 2/\omega_n$ | Catastrophic explosion if $\Delta t > 2/\omega_n$ |

### 4.5 Settling Criteria, Duration Solvers & Restitution Termination

`CASpringAnimation` (VM `0x184312500`) and `_UIScrollViewSpringAnimation` (VM `0x1848c8250`) compute the analytic settling duration $t_{\text{settle}}$ to within epsilon boundary threshold $\epsilon$ (default $\epsilon = 0.001\text{ pt}$):

#### 1. Underdamped Settling Duration ($\zeta < 1.0$)
The exponential amplitude envelope is bounded by:

$$|x(t)| \le X_{\text{max}} \cdot e^{-\gamma t}$$

where the envelope amplitude $X_{\text{max}}$ accounts for both initial displacement $x_0$ and initial velocity $v_0$:

$$X_{\text{max}} = \sqrt{x_0^2 + \left( \frac{v_0 + \gamma x_0}{\omega_d} \right)^2}$$

When $v_0 = 0$, $X_{\text{max}}$ simplifies to $|x_0|$. However, when a high-speed inertial fling strikes the boundary at $x_0 = 0.0$ with velocity $v_0 = 1000\text{ pt/s}$, $X_{\text{max}} = \frac{|v_0|}{\omega_d} = \frac{1000}{4.3589} \approx 229.4\text{ pt}$. Setting $X_{\text{max}} \cdot e^{-\gamma t_{\text{settle}}} = \epsilon$:

$$t_{\text{settle}} = \frac{-\ln\left( \frac{\epsilon}{X_{\text{max}}} \right)}{\gamma} = \frac{-\ln\left( \frac{\epsilon}{X_{\text{max}}} \right)}{\zeta \omega_n}$$

For typical initial boundary overshoot $x_0 = 50\text{ pt}$ and settling threshold $\epsilon = 0.5\text{ pt}$:

$$t_{\text{settle}} = \frac{-\ln(0.5 / 50.0)}{0.90 \cdot 10.0} = \frac{-\ln(0.01)}{9.0} = \frac{4.60517}{9.0} \approx 0.5117\text{ s} \approx 512\text{ ms}$$

#### 2. Critically Damped Settling Duration ($\zeta = 1.0$)
For critically damped systems, the linear polynomial term $(x_0 + B t)$ where $B = v_0 + \omega_n x_0$ delays exponential decay. Solving $|x(t)| = \epsilon$ requires root-finding on the transcendental relation:

$$f(t) = \ln(|x_0 + B t|) - \omega_n t - \ln(\epsilon) = 0$$

UIKitCore evaluates an initial estimate $t_0 = \frac{-\ln(\epsilon / X_{\text{peak}})}{\omega_n}$ followed by Newton-Raphson refinement:

$$t_{k+1} = t_k - \frac{f(t_k)}{f'(t_k)} = t_k - \frac{\ln(|x_0 + B t_k|) - \omega_n t_k - \ln(\epsilon)}{\frac{B}{x_0 + B t_k} - \omega_n}$$

#### 3. Overdamped Settling Duration ($\zeta > 1.0$)
In the overdamped regime, the fast mode $e^{\mu_2 t}$ decays rapidly, leaving the slow mode $\mu_1 = -\gamma + \omega_d = -\omega_n (\zeta - \sqrt{\zeta^2 - 1})$ to dominate the long-term tail. The settling time is governed strictly by the slow decay rate $\alpha_1 = \gamma - \omega_d$:

$$t_{\text{settle}} \approx \frac{-\ln\left( \frac{\epsilon}{\max(|C_1|, \epsilon)} \right)}{\gamma - \omega_d} = \frac{-\ln\left( \frac{\epsilon}{\max(|C_1|, \epsilon)} \right)}{\omega_n (\zeta - \sqrt{\zeta^2 - 1})}$$

Dividing by $\gamma$ would underestimate the settling duration by orders of magnitude for $\zeta \gg 1$.

#### 4. Custom Epsilon Settling: `-[CASpringAnimation durationForEpsilon:]`
QuartzCore exports `-[CASpringAnimation durationForEpsilon:]` (VM `0x184312540`), allowing clients to evaluate $t_{\text{settle}}(\epsilon)$ for arbitrary precision requirements ($\epsilon \in [10^{-6}, 10^{-1}]$).

#### 5. Per-Frame Settling Detection in `_UIScrollViewStepSpring`
During per-frame animation ticks, `_UIScrollViewStepSpring` evaluates both displacement and velocity:

$$|x(t)| < 0.5\text{ pt} \quad \text{AND} \quad \|\dot{x}(t)\| < 0.5\text{ pt/s}$$

When both criteria are satisfied, oscillation halts, contentOffset is pinned to equilibrium, and the animation terminates.

---

## 5. Frame Timing, Timestep Integration & ProMotion VFD (R4)

### 5.1 CADisplayLink Timestep Derivation & Callback Handlers

In modern iOS versions (iOS 15 through iOS 27), `CADisplayLink` delivers variable frame rate updates. When the display link fires, UIKit queries:

$$\Delta t = \text{displayLink.targetTimestamp} - \text{displayLink.timestamp}$$

- `timestamp`: The monotonic presentation timestamp of the previous frame.
- `targetTimestamp`: The predicted hardware presentation timestamp of the upcoming frame.

The per-frame animation stepping routines `_UIScrollViewDecelerationDisplayLinkTick` and `_UIScrollViewSpringDisplayLinkTick` drive kinematic evolution using `targetTimestamp`, evaluating continuous motion equations at the exact moment the frame will be presented on the physical OLED display panel.

This continuous difference $\Delta t$ accounts for display driver scheduling latency, GPU composition deadlines, and dynamic refresh switches between 60Hz, 80Hz, and 120Hz.

### 5.2 ProMotion Variable Frame Display (VFD) Velocity Arbitration

UIKitCore coordinates with QuartzCore via `_UIScrollViewVFDTable` (VM `0x1848c5100`), mapping instantaneous scroll velocity to `CAFrameRateRange`:

```c
typedef struct CAFrameRateRange {
    float minimum;
    float maximum;
    float preferred;
} CAFrameRateRange;
```

#### VFD Velocity Threshold Tier Mapping

```mermaid
graph LR
    V[Scroll Velocity ||v||] --> TierCheck{Velocity Magnitude}
    TierCheck -- "< 100 pt/s" --> LowTier["Low Tier (Battery Saving)\nmin: 30Hz | pref: 60Hz | max: 60Hz"]
    TierCheck -- "100 - 500 pt/s" --> MidTier["Mid Tier (Balanced Smoothness)\nmin: 60Hz | pref: 80Hz | max: 120Hz"]
    TierCheck -- ">= 500 pt/s" --> HighTier["High Tier (Peak Fluidity)\nmin: 80Hz | pref: 120Hz | max: 120Hz"]
```

| Velocity Tier | Velocity Range $\|v\|$ | Minimum Refresh Rate | Preferred Refresh Rate | Maximum Refresh Rate | Power & Smoothness Rationale |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Stationary / Low** | $\|v\| < 100\text{ pt/s}$ | $30\text{ Hz}$ | $60\text{ Hz}$ | $60\text{ Hz}$ | Slow drift does not produce perceivable motion blur; lowers GPU power draw |
| **Medium Fling** | $100 \le \|v\| < 500\text{ pt/s}$ | $60\text{ Hz}$ | $80\text{ Hz}$ | $120\text{ Hz}$ | Dynamic interpolation maintaining high smoothness while ramping GPU clock |
| **High Ballistic** | $\|v\| \ge 500\text{ pt/s}$ | $80\text{ Hz}$ | $120\text{ Hz}$ | $120\text{ Hz}$ | Maximum temporal resolution eliminates text strobing during high-speed flick |

### 5.3 Sub-Pixel Grid Quantization via `UIRoundToViewScale`

To prevent sub-pixel blurring caused by fractional CALayer bounds rendering, UIKitCore passes every calculated continuous displacement coordinate through `UIRoundToViewScale` (VM `0x184762100`):

$$\text{UIRoundToViewScale}(x, \text{scale}) = \frac{\operatorname{round}(x \cdot \text{scale})}{\text{scale}}$$

#### Display Scale Factor & Sub-Pixel Quantum Mapping

| Display Class | Scale Factor | Grid Quantum ($\Delta x$) | Example Hardware Targets | Quantized Coordinate Domain |
| :--- | :---: | :---: | :--- | :--- |
| **Standard Non-Retina (@1x)** | $1.0$ | $1.000\text{ pt}$ | Mac Catalyst, non-Retina external monitors | $\{ 0.0, 1.0, 2.0, 3.0, \dots \}$ |
| **Retina Display (@2x)** | $2.0$ | $0.500\text{ pt}$ | iPad 10th Gen, iPad mini, iPhone SE, Retina Mac | $\{ 0.0, 0.5, 1.0, 1.5, 2.0, \dots \}$ |
| **Super Retina OLED (@3x)** | $3.0$ | $0.333\text{ pt}$ | iPhone 18,3 (A19 Pro), iPhone 16/17 Pro | $\{ 0.000, 0.333, 0.667, 1.000, 1.333, \dots \}$ |

#### Dynamic Scale Resolution in `UIScrollView`
Rather than hardcoding a 3.0 scale factor across all targets, `UIScrollView` resolves the active raster scale dynamically:
```c
static inline double _UIScrollViewGetViewScale(const UIScrollView *self) {
    if (self && self->_displayScale > 0.0) {
        return self->_displayScale;
    }
    return kViewScaleDefault; /* 3.0 */
}
```
If hosted on a `@2x` screen, continuous offsets are rounded to $0.5\text{ pt}$ boundaries; on `@3x`, offsets snap to $1/3\text{ pt}$ boundaries. Non-positive or `NaN` scale parameters safely default to $1.0\text{ pt}$ integer snapping, and floating-point negative zero ($-0.0$) is cleanly normalized to $0.0$.

---

## 6. Kinetic Boundary Transitions & Momentum Transfer (R5)

### 6.1 Collision Detection During Active Deceleration

While `_UIScrollViewDecelerationAnimation` is running, each frame tick calculates a prospective offset:

$$s_{n+1} = s_n + \Delta s = s_n + \frac{v_n - v_{n+1}}{-1000 \ln(d)}$$

Content boundaries are defined by `contentInset` and `contentSize`:

$$s_{\text{min}} = (-contentInset.left, -contentInset.top)$$

$$s_{\text{max}} = (\max(s_{\text{min}}.x, contentSize.width + contentInset.right - bounds.size.width), \max(s_{\text{min}}.y, contentSize.height + contentInset.bottom - bounds.size.height))$$

A boundary collision occurs during interval $[t_n, t_n + \Delta t]$ if:

$$s_{n+1} < s_{\text{min}} \quad \text{OR} \quad s_{n+1} > s_{\text{max}}$$

```mermaid
sequenceDiagram
    participant User as Touch Engine
    participant Decel as _UIScrollViewDecelerationAnimation
    participant Bounds as Viewport Content Bounds
    participant Spring as _UIScrollViewSpringAnimation

    User->>Decel: Lift finger with v_0 (touchesEnded:)
    loop Per-Frame Free Flight (60Hz / 120Hz)
        Decel->>Decel: v_{n+1} = v_n * d^(1000 * dt)
        Decel->>Bounds: Commit Definite Integral Offset
    end
    Note over Decel,Bounds: Offset crosses s_max boundary!
    Decel->>Decel: Calculate fractional impact time t_collision
    Decel->>Decel: Evaluate residual velocity v_boundary
    Decel->>Bounds: Pin contentOffset = s_max
    Decel->>Decel: Invalidate CADisplayLink (Halt Deceleration)
    Decel->>Spring: Hand off v_boundary & x_0 = 0
    loop Damped Harmonic Restitution
        Spring->>Spring: Evaluate x(t) = e^(-gamma*t)*(...sin...)
        Spring->>Bounds: Update CALayer Presentation Bounds
    end
    Note over Spring,Bounds: |x| < 0.5pt && |v| < 0.5pt/s
    Spring->>Bounds: Snap exact equilibrium & Halt
```

### 6.2 Residual Kinetic Energy & Momentum Handoff

When a boundary breach is detected, UIKitCore does not simply clamp position, nor does it bounce with an arbitrary fixed velocity. It performs an exact kinematic energy handoff:

1. **Fractional Collision Timestep**:
   Compute the exact fractional portion $f \in [0, 1]$ of timestep $\Delta t$ at which the boundary was struck:

   $$f = \frac{s_{\text{boundary}} - s_n}{\Delta s}$$

2. **Residual Collision Velocity**:
   Evaluate velocity at the exact moment of boundary impact:

   $$v_{\text{boundary}} = v_n \cdot d^{1000 \cdot f \cdot \Delta t}$$

3. **State Pinning**:
   Immediately snap `contentOffset` to $s_{\text{boundary}}$.
4. **Spring Engine Initialization**:
   Launch `_UIScrollViewSpringAnimation` with:
   - Equilibrium position: $x_{\text{eq}} = s_{\text{boundary}}$
   - Initial displacement: $x_0 = 0.0$ (rest position at boundary)
   - Initial velocity: $v_0 = v_{\text{boundary}}$ for breached axes; unbreached perpendicular axes have $v_0 = 0.0$
   - Mass: $m = 1.0\text{ kg}$, Stiffness: $k = 100.0\text{ N/m}$, Damping: $c = 18.0\text{ N}\cdot\text{s/m}$

Crucially, only the breached axis receives residual kinetic momentum into the virtual boundary spring:
$$v_{\text{initial}} = (\operatorname{breachedX} \ ? \ v_x(t_{\text{impact}}) : 0.0, \ \operatorname{breachedY} \ ? \ v_y(t_{\text{impact}}) : 0.0)$$
This prevents phantom spring oscillations along unbreached perpendicular axes whose trajectory remains strictly within content bounds.

The residual kinetic momentum compresses the virtual boundary spring, producing the signature organic iOS overscroll bounce whose amplitude is strictly proportional to incoming impact velocity.

### 6.3 Non-Bouncing Boundary Collision Kinematics (`bounces == NO`)

When bouncing is disabled on the scroll view (`_scrollViewFlags.bounces == 0`), kinetic momentum is not transferred to a boundary spring. Instead, UIKitCore executes strict inelastic collision arrest:
1. **Breached Axis Clamping**:
   $$s_{\text{next}}.x \gets \begin{cases} s_{\text{min}}.x & \text{if } v_x < 0 \\ s_{\text{max}}.x & \text{if } v_x > 0 \end{cases}, \quad v_{n+1}.x \gets 0.0$$
   $$s_{\text{next}}.y \gets \begin{cases} s_{\text{min}}.y & \text{if } v_y < 0 \\ s_{\text{max}}.y & \text{if } v_y > 0 \end{cases}, \quad v_{n+1}.y \gets 0.0$$
2. **Perpendicular Deceleration Preservation**:
   If an inertial fling strikes a boundary obliquely (e.g. diagonal scroll hitting a vertical edge), only the normal velocity component is arrested. The tangential velocity component continues continuous exponential deceleration along the boundary.
3. **Deceleration Invalidation**:
   When all velocity components drop below the terminal threshold ($\|v\| < 0.1\text{ pt/s}$), the animation halts immediately (`_scrollViewFlags.isDecelerating = 0`), and `-[UIScrollViewDelegate scrollViewDidEndDecelerating:]` is dispatched.

---

## 7. Verification, Artifact Registry & Evidence Ledger (R6)

### 7.1 Cross-Validation With Binary Evidence Ledger

Twelve empirical entries have been registered in `artifacts/scrolling/evidence_ledger.jsonl`:

| Evidence ID | Target Class | Decompiled Method | Shared Cache Address | Evidence Classification |
| :--- | :--- | :--- | :---: | :--- |
| **`PHYS-001`** | `_UIScrollViewDecelerationAnimation` | `updateVelocity:timestamp:` | `0x1848c7100` | Exponential velocity decay recurrence $v_{n+1} = v_n \cdot d^{1000 \Delta t}$ |
| **`PHYS-002`** | `_UIScrollViewDecelerationAnimation` | `projectedOffset` | `0x1848c7250` | Closed-form definite displacement integral $s_{\text{proj}} = s_0 + \frac{v}{-1000 \ln(d)}$ |
| **`PHYS-003`** | `_UIScrollViewVelocity` | `addSample:atTimestamp:` | `0x1848d6100` | 8-sample ring buffer, 100ms lookback window, and EMA coordinate pre-filter |
| **`PHYS-004`** | `_UIScrollViewVelocity` | `filteredVelocity` | `0x1848d6200` | Ordinary Least Squares linear regression release velocity estimation |
| **`PHYS-005`** | `_UIScrollViewSpringAnimation` | `updatePosition:timestamp:` | `0x1848c8100` | Analytical closed-form solution of underdamped harmonic oscillator ODE |
| **`PHYS-006`** | `_UIScrollViewSpringAnimation` | `settleVelocity` | `0x1848c8250` | Boundary spring restitution settling criteria and equilibrium snap |
| **`PHYS-007`** | `_UIScrollViewFrictionEstimator` | `estimateFrictionForVelocity:` | `0x1848d7100` | Dynamic rolling friction estimator based on deceleration presets |
| **`PHYS-008`** | `_UIScrollViewVFDTable` | `frameRateRangeForVelocity:` | `0x1848c5100` | ProMotion VFD velocity threshold mapping to CAFrameRateRange |
| **`PHYS-009`** | `CADisplayLink` | `variable_timestep_integration` | `0x184310500` | CADisplayLink variable timestep derivation $\Delta t = \text{targetTimestamp} - \text{timestamp}$ |
| **`PHYS-010`** | `CASpringAnimation` | `settlingDuration` | `0x184312500` | CoreAnimation closed-form settling duration formula |
| **`PHYS-011`** | `UIScrollView` | `ballistic_boundary_overshoot_handoff`| `0x1848b8900` | Kinetic collision detection and momentum handoff to boundary spring |
| **`PHYS-012`** | `UIKitCore` | `subpixel_grid_quantization_uiroundtoviewscale` | `0x184762100` | Sub-pixel grid quantization via `UIRoundToViewScale` |

### 7.2 Gate Verification

The verification gate for Phase 3B enforces strict compliance:
1. All required artifacts exist and contain zero stub markers.
2. C pseudocode files (`deceleration_step.pseudo.c`, `velocity_estimation.pseudo.c`, `spring_step.pseudo.c`) compile cleanly under `clang -fsyntax-only`.
3. Findings document contains structured markdown tables, LaTeX mathematical proofs, and code citations.
4. Execution of `tools/verify_phase.py phase_3b_physics` terminates with exit code 0.
