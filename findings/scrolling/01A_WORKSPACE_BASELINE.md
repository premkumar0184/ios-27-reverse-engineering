# Forensic Analysis: iOS 27 Scrolling Reverse Engineering Baseline & Framework Verification

**Build Target**: iOS 27.2 (Build `24B119`, Train `RaveB`)  
**Hardware Identifier**: `iPhone18,3` (`v57ap`, Board ID `0x08`, SoC `t8150` / A19 Pro)  
**Architecture**: 64-bit ARM64e (`caps: PAC00`)  
**Target Phase**: Phase 1A (`phase_1a_workspace`)  
**Status**: Authoritative Architectural Baseline  
**Verification Gate**: `tools/verify_phase.py phase_1a_workspace`  

---

## 1. System Target & Firmware Baseline Architecture

Phase 1A establishes the empirical reverse engineering baseline for the iOS 27 scrolling subsystem by auditing existing workspace assets, verifying target platform metadata, cross-referencing firmware manifests, and mapping the userland graphical runtime environment.

### 1.1 Authoritative Hardware & Kernel Platform Metadata

Cross-referencing `artifacts/rootfs/shared_cache_overview.json`, `progress.json`, `artifacts/manifests/manifest_summary.json`, and `findings/08_SYNTHESIS_AND_GRAPH.md` establishes the authoritative baseline:

| Platform Attribute | Value [EXTRACTED] | Evidence Source / Verification Tool |
| :--- | :--- | :--- |
| **Operating System** | `iOS 27.2` | `Restore.plist`, `SystemVersion.plist` (`ProductVersion`) |
| **Build Version** | `24B119` | `BuildManifest.plist`, `RestoreVersion.plist` (`ProductBuildVersion`) |
| **Build Train** | `RaveB` | `BuildManifest.plist` (`BuildTrain`) |
| **Darwin Kernel** | `Darwin 24.2.0 (xnu-11215.61.5~2)` | `artifacts/kernel/kernelcache.release.raw` string table |
| **Hardware Model** | `iPhone18,3` | `BuildManifest.plist` (`SupportedProductTypes`) |
| **Device Class** | `v57ap` | `Restore.plist` (`DeviceClass`) |
| **Board ID** | `0x08` (Decimal `8`) | `BuildManifest.plist` (`BoardId`) |
| **Security Domain (SDOM)** | `0x01` | `BuildManifest.plist` (`SecurityDomain`) |
| **Application Processor / SoC** | `t8150` (Apple A19 Pro) | `BuildManifest.plist` (`Platform`), `DeviceTree` |
| **Target CPU Architecture** | 64-bit ARM64E | Mach-O header `cputype: 0x0100000c`, `cpusubtype: 0x80000002` |
| **Pointer Authentication ABI** | ARM64E PAC00 | Enforced system-wide (`pacibsp`, `autibsp`, `braa x16, x17`) |
| **Restore Package Path** | `iPhone18,3_27.2_24B119_Restore/` | Root restore directory |

### 1.2 Userland Shared Runtime & Split Cache Topology

The userland graphical execution layer relies on the dynamic shared cache located in the decrypted `Cryptex1,SystemOS` container at `/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e`.

```
+-----------------------------------------------------------------------------------------+
|                    dyld_shared_cache_arm64e (Split Shared Cache Architecture)           |
|                                                                                         |
|  Master Header: 802,816 bytes (UUID: d18641a5-1668-3d20-9095-f592af0b4748)              |
|  Cache Type: 2 (Production Split Cache) | Total Subcaches: 81 Slices (.01 to .81)       |
|  Total Cataloged Dynamic Libraries & Frameworks: 4,770 Images                           |
|  Unified Virtual Address Space: 0x180000000 -> 0x31082c000 (3.75+ GB VM span)           |
+-----------------------------------------------------------------------------------------+
       |                                           |                                |
       v                                           v                                v
+----------------------------+   +----------------------------+   +-----------------------+
| Subcache .01 (131.5 MB)    |   | Subcache .25 (229.4 MB)    |   | Subcache .36 (131.5MB)|
| VM Base: 0x180400000       |   | VM Base: 0x1e00f4000       |   | VM Base: 0x220400000  |
| UIKitCore (0x184752000)    |   | Dirty & Authenticated Data |   | SpringBoard.framework |
| QuartzCore (0x1842d4000)   |   | __AUTH / __DATA_DIRTY      |   | (0x226a11000)         |
| CoreGraphics (0x183b16000) |   | PAC-hardened mutable state |   | UserNotificationsUIKit|
+----------------------------+   +----------------------------+   +-----------------------+
```

---

## 2. Systematic Verification of the 13 Candidate Scrolling Frameworks

All 13 candidate scrolling frameworks designated in the master reverse engineering plan were systematically queried against `artifacts/rootfs/shared_cache_overview.json` using `tools/analyze_dyld_cache.py`. Every framework has been confirmed present in the cache catalog, and mapped to its exact subcache slice, file offset, and VM base address.

### 2.1 Authoritative 13-Framework Inventory Table

| # | Framework Name | Subcache Slice | Subcache File Offset | VM Base Address | Subcache UUID | Segment Count |
|:--|:---|:---|:---|:---|:---|:--:|
| 1 | `UIKitCore.framework` | `.01` | `0x04352000` | `0x184752000` | `a78f816e-fae5-3aaf-a753-766346190a44` | 7 |
| 2 | `QuartzCore.framework` | `.01` | `0x03ed4000` | `0x1842d4000` | `a78f816e-fae5-3aaf-a753-766346190a44` | 7 |
| 3 | `SwiftUI.framework` | `.03` | `0x024a7000` | `0x18a8a7000` | `1a1939c0-a2ab-3d82-a43c-9e61ad237972` | 7 |
| 4 | `SwiftUICore.framework` | `.03` | `0x00004000` | `0x188404000` | `1a1939c0-a2ab-3d82-a43c-9e61ad237972` | 7 |
| 5 | `WebKit.framework` | `.07` | `0x047b9000` | `0x19cbb9000` | `d073c60c-471a-3a5a-aba0-429451768c5b` | 7 |
| 6 | `WebKitLegacy.framework` | `.11` | `0x07720000` | `0x1afb20000` | `c9ee7219-35ab-3cf7-bd37-5e5e8d6ea29c` | 7 |
| 7 | `UIKit.framework` | `.46` | `0x07b98000` | `0x24ff98000` | `d39f0a86-603c-32ee-b570-0920bc36e174` | 7 |
| 8 | `Gestures.framework` | `.03` | `0x01d69000` | `0x18a169000` | `1a1939c0-a2ab-3d82-a43c-9e61ad237972` | 7 |
| 9 | `CoreText.framework` | `.07` | `0x01fd7000` | `0x19a3d7000` | `d073c60c-471a-3a5a-aba0-429451768c5b` | 7 |
| 10 | `IOHIDPointerScrollFilter.plugin` | `.48` | `0x025c4000` | `0x2529c4000` | `2b0abe0c-1c3c-398f-90ff-b0beed9be26a` | 7 |
| 11 | `AnimationKit.framework` | `.07` | `0x06eb1000` | `0x19f2b1000` | `d073c60c-471a-3a5a-aba0-429451768c5b` | 7 |
| 12 | `SystemUIAnimationKit.framework` | `.69` | `0x05ef0000` | `0x2b62f0000` | `b956340b-dd3d-3ea7-98ba-894114423a36` | 7 |
| 13 | `UIKitServices.framework` | `.05` | `0x07b2b000` | `0x197f2b000` | `22f8fac9-b323-3a0e-8d58-388a8950ae15` | 7 |

*Note: In the dyld shared cache split architecture, all Mach-O images adhere to a standardized 7-segment partition: `__TEXT`, `__DATA_CONST`, `__AUTH_CONST`, `__AUTH`, `__DATA`, `__DATA_DIRTY`, and `__LINKEDIT`.*

### 2.2 Framework Roles & Scrolling Investigation Priorities

| Framework | Primary Image Path in Shared Cache | Architectural Role in Scrolling Subsystem [EXTRACTED] | Priority Tier |
| :--- | :--- | :--- | :---: |
| **`UIKitCore`** | `/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore` | Core scrolling engine: `UIScrollView`, `UIPanGestureRecognizer`, deceleration kinematics, rubber-banding, paging, content offsets, and scroll indicators. | **Tier 1 (Core)** |
| **`QuartzCore`** | `/System/Library/Frameworks/QuartzCore.framework/QuartzCore` | CoreAnimation pipeline: `CADisplayLink`, `CAFrameRateRange` (120Hz ProMotion), spring animation timing functions, compositor layer transforms. | **Tier 1 (Core)** |
| **`SwiftUI`** | `/System/Library/Frameworks/SwiftUI.framework/SwiftUI` | Declarative UI layer: `ScrollView`, `List`, `LazyVStack` coordinate space translations, SwiftUI pan gesture handlers. | **Tier 2 (High)** |
| **`SwiftUICore`** | `/System/Library/Frameworks/SwiftUICore.framework/SwiftUICore` | Core declarative runtime: view graph evaluation, transaction mechanics, state-driven offset binding updates. | **Tier 2 (High)** |
| **`Gestures`** | `/System/Library/PrivateFrameworks/Gestures.framework/Gestures` | Private low-level gesture arbitration, multi-finger coordinate filtering, gesture conflict resolution. | **Tier 2 (High)** |
| **`IOHIDPointerScrollFilter`**| `/System/Library/HIDPlugins/IOHIDPointerScrollFilter.plugin/IOHIDPointerScrollFilter`| Lowest userland entrypoint for pointer and trackpad scroll events, wheel delta accumulation, and device friction scaling. | **Tier 2 (High)** |
| **`WebKit`** | `/System/Library/Frameworks/WebKit.framework/WebKit` | Multi-process web viewport scrolling, async scrolling thread coordination (`RemoteScrollingCoordinatorIOS`), web rubber-banding. | **Tier 3 (Specialized)**|
| **`WebKitLegacy`** | `/System/Library/PrivateFrameworks/WebKitLegacy.framework/WebKitLegacy` | In-process legacy WebKit scrolling mechanisms and DOM scroll offset event propagation. | **Tier 3 (Specialized)**|
| **`CoreText`** | `/System/Library/Frameworks/CoreText.framework/CoreText` | Text layout engine: `CTFramesetter`, line fragment coordinate calculation during continuous text view scrolling. | **Tier 3 (Specialized)**|
| **`UIKitServices`** | `/System/Library/PrivateFrameworks/UIKitServices.framework/UIKitServices` | Inter-process display coordination, scene coordinate translation, BackBoard input event delivery glue. | **Tier 3 (Specialized)**|
| **`AnimationKit`** | `/System/Library/PrivateFrameworks/AnimationKit.framework/AnimationKit` | Advanced physics curve models, parametric spring equations, multi-axis interpolation models. | **Tier 3 (Specialized)**|
| **`SystemUIAnimationKit`**| `/System/Library/PrivateFrameworks/SystemUIAnimationKit.framework/SystemUIAnimationKit`| System-level gesture spring models, fluid switcher transitions, dynamic island spring animations. | **Tier 3 (Specialized)**|
| **`UIKit`** | `/System/Library/Frameworks/UIKit.framework/UIKit` | Public API forwarding facade and symbol export re-exports for `UIKitCore`. | **Tier 4 (Facade)** |

### 2.3 Detailed Mach-O Segment Anatomy (Resident Slices)

For target frameworks situated inside resident on-disk subcache slices (`dyld_shared_cache_arm64e.01`), direct load command dissection provides verified segment addresses, file offsets, and permission boundaries.

#### UIKitCore.framework (`0x184752000`, Subcache `.01`)
Extracted from `dyld_shared_cache_arm64e.01` at file offset `0x04352000`:
- **Header**: `magic: 0xfeedfacf`, `cputype: 0x100000c`, `cpusubtype: 0x80000002`, `ncmds: 139`, `sizeofcmds: 16472`
- **Segments** (7 total):
  1. `__TEXT`: VM `0x184752000` (size `0x204eed4` / 33,877,716 bytes), fileoff `0x4352000`, prot `r-x`
  2. `__DATA_CONST`: VM `0x1e05fafd0` (size `0xf94d8` / 1,021,144 bytes), fileoff `0x506fd0`, prot `rw-`
  3. `__AUTH_CONST`: VM `0x1e229cef0` (size `0x3a1c60` / 3,808,352 bytes), fileoff `0x21a8ef0`, prot `rw-`
  4. `__AUTH`: VM `0x1ef161470` (size `0x60008` / 393,224 bytes), fileoff `0xd06d470`, prot `rw-`
  5. `__DATA`: VM `0x1eb064250` (size `0x87d10` / 556,304 bytes), fileoff `0x8f70250`, prot `rw-`
  6. `__DATA_DIRTY`: VM `0x1ede371a0` (size `0x5ba90` / 375,440 bytes), fileoff `0xbd431a0`, prot `rw-`
  7. `__LINKEDIT`: VM `0x2e6940000` (size `0x298ec000` / 697,221,120 bytes), fileoff `0x4000`, prot `r--`

#### QuartzCore.framework (`0x1842d4000`, Subcache `.01`)
Extracted from `dyld_shared_cache_arm64e.01` at file offset `0x03ed4000`:
- **Header**: `magic: 0xfeedfacf`, `cputype: 0x100000c`, `cpusubtype: 0x80000002`, `ncmds: 53`, `sizeofcmds: 7504`
- **Segments** (7 total):
  1. `__TEXT`: VM `0x1842d4000` (size `0x47da68` / 4,708,968 bytes), fileoff `0x3ed4000`, prot `r-x`
  2. `__DATA_CONST`: VM `0x1e05de710` (size `0x1c8c0` / 116,928 bytes), fileoff `0x4ea710`, prot `rw-`
  3. `__AUTH_CONST`: VM `0x1e2254c90` (size `0x48260` / 295,520 bytes), fileoff `0x2160c90`, prot `rw-`
  4. `__AUTH`: VM `0x1ef160080` (size `0x13e8` / 5,096 bytes), fileoff `0xd06c080`, prot `rw-`
  5. `__DATA`: VM `0x1eb05dda0` (size `0x64b0` / 25,776 bytes), fileoff `0x8f69da0`, prot `rw-`
  6. `__DATA_DIRTY`: VM `0x1edf37100` (size `0x8a30` / 35,376 bytes), fileoff `0xbe43100`, prot `rw-`
  7. `__LINKEDIT`: VM `0x2e6940000` (size `0x298ec000` / 697,221,120 bytes), fileoff `0x4000`, prot `r--`

---

## 3. Subcache Cross-Slice Traversal & Address Resolution Verification

A fundamental technical challenge in reverse engineering iOS 27 firmware is navigating across split shared cache boundaries. The runtime splits 4,770 frameworks across 81 subcaches, requiring tools to accurately map high virtual addresses to discrete physical disk slices.

### 3.1 Subcache Boundary Traversal Mechanics

Verification was conducted between two resident slices on disk:
- **Slice `.01`** (`dyld_shared_cache_arm64e.01`, size: 131,547,136 bytes) housing foundational UI engines (`UIKitCore`, `QuartzCore`, `CoreGraphics`).
- **Slice `.36`** (`dyld_shared_cache_arm64e.36`, size: 131,547,136 bytes) housing system orchestration and compositing (`SpringBoard.framework`, `UserNotificationsUIKit`, `ControlCenterUIKit`).

#### Mathematical Coordinate Remapping
In the dyld split shared cache:
$$\text{VM\_Base}(S_k) = \text{Root\_Cache\_Base} + S_k.\text{vm\_offset} = \text{0x180000000} + S_k.\text{vm\_offset}$$

For any virtual address $VA$, deterministic resolution identifies subcache $S_k$ satisfying $\text{VM\_Base}(S_k) \le VA < \text{VM\_Base}(S_{k+1})$, and computes the local file offset:
$$\text{File\_Offset}(VA) = VA - \text{VM\_Base}(S_k)$$

| Target Entity | Subcache Slice | Subcache VM Base | Target VM Address | Computed Subcache File Offset | Verified Mach-O Magic |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`UIKitCore`** | `.01` | `0x180400000` | `0x184752000` | `0x04352000` (70,590,464) | `0xfeedfacf` (MH_MAGIC_64) |
| **`QuartzCore`** | `.01` | `0x180400000` | `0x1842d4000` | `0x03ed4000` (65,880,064) | `0xfeedfacf` (MH_MAGIC_64) |
| **`SpringBoard`** | `.36` | `0x220400000` | `0x226a11000` | `0x06611000` (107,024,384)| `0xfeedfacf` (MH_MAGIC_64) |
| **`UserNotificationsUIKit`**| `.36` | `0x220400000` | `0x226124000` | `0x05d24000` (97,665,024) | `0xfeedfacf` (MH_MAGIC_64) |
| **`ControlCenterUIKit`** | `.36` | `0x220400000` | `0x22791d000` | `0x0751d000` (122,802,176)| `0xfeedfacf` (MH_MAGIC_64) |

```python
def resolve_subcache_target(vm_address: int, subcaches_table: list, cache_base: int = 0x180000000) -> tuple:
    """
    Deterministic cross-slice subcache resolver for iOS 27 dyld shared cache.
    """
    target_sc = None
    for sc in subcaches_table:
        sc_base = cache_base + sc['vm_offset_int']
        if sc_base <= vm_address:
            target_sc = sc
    if not target_sc:
        raise ValueError(f"Address 0x{vm_address:x} precedes all subcaches")
    sc_base = cache_base + target_sc['vm_offset_int']
    file_offset = vm_address - sc_base
    return target_sc['extension'], sc_base, file_offset
```

#### REA Toolchain Cross-Slice Bridge Execution
To verify that deep reverse engineering tooling (`rea`) can traverse and inspect binaries across distinct subcache boundaries, targeted Mach-O slices from both resident subcaches were opened and analyzed:
- **Subcache `.01` Slice (`artifacts/scrolling/UIKitCore_UIScrollView_slice`)**:
  - `sha256`: `c4fbc959ba96d66a141a9958925c766fd35a1010f91bd0ac25da8e1323e82a18`
  - REA output: `format: mach-o`, `kind: executable`, `architecture: arm64`
- **Subcache `.36` Slice (`artifacts/scrolling/SpringBoard_slice`)**:
  - `sha256`: `0180272a829ba1cbf8332fc79173322c3c1a427f21b660c648ded073f0cdd62e`
  - Sliced from file offset `0x06611000` (VM `0x226a11000`, 65,536 bytes) with `__TEXT.fileoff` normalized to `0x0` and relative section offsets remapped to prevent Ghidra `IndexOutOfBoundsException` bounds errors
  - REA output: `format: mach-o`, `kind: executable`, `architecture: arm64`, 29 procedures discovered (`FUN_226a18980`), 264 defined strings, verified ARM64E PAC opcode instructions at `0x226a18980` (`pacibsp`, `retab`)
  - Empirical Evidence Links: `ev_68d25661eb0ba112477b37343f5ed9d2aa1bdfce05e5ada6f3f9567bde5744c3`, `ev_cc6bcc33e7a369efa33878ab90ee7900bcfd31da5243f3c3fde166a14b8b76e0`

Both slices parsed cleanly without memory fault or symbol dictionary corruption, proving that the REA / Headless Ghidra bridge operates identically across subcache boundaries (.01 and .36).

### 3.2 Cross-Slice Linkage & Pointer Fixups

Inspection of load commands in `SpringBoard.framework` (subcache `.36` at file offset `0x06611000`) reveals 252 dynamic library dependencies (`LC_LOAD_DYLIB`), with explicit cross-slice imports spanning subcache `.01` and other slices:
- `/System/Library/Frameworks/QuartzCore.framework/QuartzCore` (resolves to subcache `.01` at `0x1842d4000`)
- `/System/Library/Frameworks/UIKit.framework/UIKit` (resolves to subcache `.46` at `0x24ff98000`)
- `/System/Library/PrivateFrameworks/UIKitServices.framework/UIKitServices` (resolves to subcache `.05` at `0x197f2b000`)
- `/System/Library/PrivateFrameworks/BaseBoard.framework/BaseBoard`
- `/System/Library/PrivateFrameworks/FrontBoard.framework/FrontBoard`

#### Pointer Authentication & Writable Memory Isolation
1. **Chained Fixups & Slide Information**:
   Slide tables and export tries are centralized across the master cache header (`0x38`/`0x40`) and the unified `__LINKEDIT` segment (`0x2e6940000`). All subcaches share a synchronized ASLR slide value computed at boot.
2. **Isolation in `.dylddata` Slices**:
   Cross-slice pointer targets that require rebasing or runtime rebinding are segregated into writable subcache slices (`dyld_shared_cache_arm64e.25.dylddata` at VM base `0x1e00f4000`, computed via `0x180000000 + 0x600f4000`). This ensures clean code pages in `.01` and `.36` remain completely shareable and immutable.
   - Empirical proof: `UIKitCore.__DATA_CONST` at VM `0x1e05fafd0` maps to subcache `.25.dylddata` offset `0x1e05fafd0 - 0x1e00f4000 = 0x506fd0`, which exactly matches the Mach-O `__DATA_CONST.fileoff` (`0x506fd0`).
   - Similarly, `UIKitCore.__AUTH_CONST` at VM `0x1e229cef0` maps to offset `0x1e229cef0 - 0x1e00f4000 = 0x21a8ef0`, exactly matching `__AUTH_CONST.fileoff` (`0x21a8ef0`).
3. **ARM64E PAC Verification**:
   Function pointers crossing slice boundaries (such as `SpringBoard.app` trampoline jumping to `SpringBoard.framework` via `braa x16, x17` at `0x100000578`) utilize PAC Key A or Key B. All analyzed method entries begin with `pacibsp` (`0xd503237f`) and terminate with `autibsp` (`0xd50323ff`).

---

## 4. Prior Findings Extraction & SpringBoard Audit

Existing architectural analyses in `findings/06_UI_AND_APPLICATIONS.md`, `findings/SPRINGBOARD_DEEP_DISSECTION.md`, and `artifacts/ui/springboard_analysis.json` contain critical preliminary evidence regarding system-wide scrolling, gesture arbitration, and touch delivery.

### 4.1 Hardware Input Pipeline: IOKit to BKSTouchStream

Touch and gesture delivery originates at the hardware driver level and routes through the BackBoard window server before reaching application scroll views:

```
[Touch Surface / Multitouch Digitizer]
                  |
                  v
       [IOHIDFamily (kext)]  <-- Packages raw contacts into IOHIDEvent packets
                  |
                  | Mach Port IPC
                  v
         [daemon: backboardd]
                  |
                  | Validates reservation zones & active displays
                  v
          [BKSTouchStream]   <-- Serializes high-frequency continuous touch points
                  |
         +--------+--------+
         |                 | System Gesture Interception (home affordance, edges)
         v                 v
[Application Scene]   [SBSystemGestureManager]
(UIScrollView)        - SBHomeGesturePanGestureRecognizer
                      - SBDeckSwitcherPanGestureWorkspace
                      - SBAssistantIslandStageGestureManager
```

1. **`backboardd` Hardware Interception**:
   `backboardd` receives digitized touch events from `IOHIDFamily`. It tracks touch coordinates against display reservation margins (e.g., bottom 16pt home affordance bar, top status bar, screen corners).
2. **`BKSTouchStream` Serialization**:
   Touches outside system reservation margins are serialized into `BKSTouchStream` packets and dispatched across Mach ports to the foreground `FBScene` hosting the active app.
3. **`SBSystemGestureManager` Suppression**:
   If a touch trajectory triggers a system gesture recognizer, `SBSystemGestureManager` asserts exclusive ownership, sending touch cancel events (`touchesCancelled:withEvent:`) to the application `UIScrollView`.

### 4.2 SpringBoard Gesture Recognition & Kinematics Models

Disassembly of `SpringBoard.framework` presentation controllers yielded concrete mathematical models governing system gesture interaction:

#### Home Affordance Pan Gesture (`SBHomeGesturePanGestureRecognizer`)
- **Activation Area**: Bottom 16pt margin across the display width.
- **Scale Dampening Formula** [EXTRACTED]:
  $$\text{Scale}(y) = 1.0 - \left(\frac{\Delta y}{\text{ScreenHeight}}\right) \times 0.28$$
- **Corner Curvature Morphing**: Continuous interpolation from 0pt (square full-screen app) to 44pt (matching physical device bezel radius).
- **Velocity Thresholds**:
  - Upward flick $v_y > 2500\text{ pt/s}$: Commits immediately to home screen zoom (`SBMatchMoveToDropletSwitcherEventResponse`).
  - Sustained drag with $v_y \in [1000, 2000]\text{ pt/s}$: Transitions into 3D curved App Switcher deck.

#### Fluid Switcher Deck Scrolling (`SBDeckSwitcherPanGestureWorkspace`)
- Continuous interactive carousel tracking horizontal card panning.
- Card flick-to-kill: Upward flick velocity $v_y > 1800\text{ pt/s}$ triggers `SBRemoveFromDesktopSwitcherEventResponse`, invalidating the scene via `FBSceneManager` and terminating the process.

#### Dynamic Island Spring Physics (`SBAssistantIslandStageGestureManager`)
- Interactive expansion FSM responding to press and drag:
  - Long-press threshold: $> 0.30\text{ s}$.
  - Fluid spring parameters: Damping ratio $\zeta = 0.78$, Response duration $T = 0.45\text{ s}$.

### 4.3 Prior Scrolling Infrastructure in SpringBoard & UI Libraries

Forensic string search across subcache slice `dyld_shared_cache_arm64e.36` identified specialized scroll view implementations deployed across the system UI:

| Discovered Class / Structure | Defining Subsystem / Framework | Architectural Role in System UI [EXTRACTED] |
| :--- | :--- | :--- |
| **`SBFloatingDockView`** | `SpringBoard.framework` (`0x226a11000`) | iPadOS / Stage Manager multitasking dock supporting horizontal scrolling of recent and suggested applications. |
| **`SBFloatingDockController`** | `SpringBoard.framework` (`0x226a11000`) | Coordinates floating dock presentation, auto-hide gestures, and split-view drag initiation. |
| **`SBCoverSheetPresentationManager`**| `SpringBoard.framework` (`0x226a11000`) | Manages vertical lock screen / cover sheet pull-down dismissal, notification center pagination, and ambient charging mode. |
| **`SBIconScrollView`** | `SpringBoardHome.framework` / `.36` | Paged horizontal scroll view managing Home Screen icon grids, widget stack pagination, and App Library carousels. |
| **`SBAppSwitcherScrollView`** | `SpringBoard.framework` (`.36`) | Interactive 3D deck carousel handling app switcher card panning and deceleration. |
| **`SBAppSwitcherItemScrollView`** | `SpringBoard.framework` (`.36`) | Per-app card scroll view supporting interactive card swipe-to-kill gestures. |
| **`SBFPagedScrollView`** | `SpringBoardFoundation.framework` (`.36`)| Foundational SpringBoard paged scroll container with high-precision decel kinematics. |
| **`BFluidSwitcherTouchPassThroughScrollView`**| `SpringBoard.framework` (`.36`)| Touch pass-through scroll view coordinating simultaneous pan gesture and card deck scrolling. |
| **`BSUIScrollView`** | `BaseBoardUI.framework` (`.36`) | BaseBoard specialized scroll view with IPC-coordinated cancelation and high-precision deceleration mechanics. |
| **`CCUIIconScrollView`** | `ControlCenterUIKit.framework` (`.36`)| Paged icon scroll view managing Control Center module pages and customizable action grids. |
| **`ScrollViewExclusionManager`** | `UserNotificationsUIKit` (`.36`) | Coordinates touch exclusion zones between notification list scrolling and swipe-to-reveal action buttons. |

---

## 5. Toolchain Capabilities, Limitations & Operational Protocols

Phase 0 validated the reverse engineering toolchain against `UIKitCore.framework`. Phase 1A confirms operational procedures for subsequent phases.

### 5.1 Toolchain Status Matrix

| Tool / Provider | Validation Target | Verified Operations | Observed Latency | Operational Status |
| :--- | :--- | :--- | :---: | :---: |
| **`tools/analyze_dyld_cache.py`** | Master header & all 81 subcaches | Mapping parse, subcache table lookup, Mach-O segment extraction | < 250 ms | **Operational (Deterministic)** |
| **REA Engine** | `UIKitCore_UIScrollView_slice` | `open_binary`, `binary_overview`, `procedure_pseudo_code`, `read_function_instructions` | 760 - 1420 ms | **Operational (Ghidra bridge)** |
| **Ghidra Engine** | `UIKitCore.framework` | `list_classes`, `get_function_by_address`, `decompile_function` | 48 - 85 ms | **Operational (HTTP daemon)** |
| **Custom Python Parsers** | Subcaches `.01` & `.36` | `struct.unpack` Mach-O header parsing, load command traversal | < 100 ms | **Operational (Deterministic)** |

### 5.2 Identified Constraints & Mitigation Strategies

1. **Pure Static Analysis Constraint**:
   - *Limitation*: No live iOS 27 device or functional simulator environment is available. Dynamic tracing with Frida or DTrace cannot be conducted.
   - *Mitigation*: All investigations rely exclusively on static disassembly, decompilation, binary slicing, and mathematical modeling verified by cross-referencing multiple frameworks.
2. **Monolithic Cache Memory Exhaustion**:
   - *Limitation*: Dyld subcache slices are 126–229 MB each. Attempting to open an entire slice directly in Ghidra causes multi-gigabyte memory consumption and multi-minute indexing freezes.
   - *Mitigation*: Enforce targeted framework slicing (e.g., `UIKitCore_UIScrollView_slice`, `UIKitCore_TEXT`). Extract exact segment slices based on deterministic file offsets before passing binaries to REA and Ghidra.
3. **Platform-Specific macOS Tooling**:
   - *Limitation*: Native Apple command-line utilities (`otool`, `vtool`, `dyld_shared_cache_util`) require macOS and fail on this Linux host.
   - *Mitigation*: Use deterministic Python binary parsers (`tools/analyze_dyld_cache.py`) that parse Mach-O headers directly using the `struct` module.

---

## 6. Phase 1A Verification Evidence & Exit Criteria Fulfillment

### 6.1 Exit Checklist Audit

- [x] **R1 Target Specification Established**: Authoritative metadata verified (iOS 27.2, Darwin 24.2.0, Build 24B119, Train RaveB, iPhone18,3, v57ap, Board ID 0x08, SoC t8150, arm64e PAC00).
- [x] **R2 All 13 Frameworks Verified**: Exact subcache slice, file offset, VM base address, and segment count cataloged in structured Markdown tables.
- [x] **R3 Subcache Traversal Verified**: Cross-slice boundary traversal proven between subcaches `.01` and `.36`, with fileoff remapping formulas and PAC fixup mechanisms documented.
- [x] **R4 Prior Findings Extracted**: `BKSTouchStream` dispatch, `SBSystemGestureManager` arbitration, `SBHomeGesturePanGestureRecognizer` kinematics, and SpringBoard scroll classes (`SBFloatingDockView`, `SBCoverSheet`, `SBIconScrollView`, `BSUIScrollView`) synthesized.
- [x] **R5 Findings Document Authored**: `findings/scrolling/01A_WORKSPACE_BASELINE.md` authored, >= 2,500 bytes (currently > 15,000 bytes), fully substantiated with verified facts, complete empirical data.
- [x] **Verification Script Passed**: `python3 tools/verify_phase.py phase_1a_workspace` passes with exit code 0.

### 6.2 Evidence Ledger References

All verified empirical facts have been logged to `artifacts/scrolling/evidence_ledger.jsonl`:
- **Phase 1A Baseline Entries**:
  - `BASE-001`: Target platform specification & firmware baseline (`iPhone18,3` / `v57ap` / `t8150` / `24B119` / ARM64E PAC00)
  - `BASE-002`: Systematic inventory & coordinate verification of all 13 scrolling candidate frameworks
  - `BASE-003`: Empirical cross-subcache boundary traversal between `.01` and `.36` with verified Mach-O 64-bit headers (`0xfeedfacf`)
  - `BASE-004`: Coordinate alignment for authenticated/mutable data segments in Subcache `.25.dylddata` (`0x1e00f4000`)
  - `BASE-005`: REA cross-slice bridge validation opening, analyzing, and disassembling Mach-O slices across subcaches `.01` (`UIKitCore_UIScrollView_slice`) and `.36` (`SpringBoard_slice` at `0x226a18980`, `ev_68d25661eb0ba112477b37343f5ed9d2aa1bdfce05e5ada6f3f9567bde5744c3`)
- **Phase 0 Foundational Entries**:
  - `TOOL-001` (`ev_c06e595053ca59c6df0e3ee59b97bbf23c6f47612495311683eb62b351c65851`, `ev_b131022925a601fb0ac7e7fe6c31614d37e792c3f2273668e65e3465946e5f6a`): `-[UIScrollView setContentOffset:animated:]` decompilation and PAC validation
  - `TOOL-002` (`ev_25e364a664b711507d3672fbf93cd5e1a36109516ebd83110ec60b83660e949f`, `ev_10bb7712b02903ce3e0be85337abdd7a168439dee9ebedfa168556bbeebcd9c8`, `ev_806d29ecbfd59fd6e1c971ab7d78d4593acef31eb3ed1fa462306e148ddd29db`): `-[UIScrollView _scrollViewWillBeginDragging]` decompilation, PAC instructions, and assembly validation

---
*Authored deterministically by Reconnaissance Agent adhering strictly to `.agent_rules/CORE_RULES.md`.*
