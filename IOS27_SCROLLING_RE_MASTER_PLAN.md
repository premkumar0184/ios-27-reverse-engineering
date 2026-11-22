# iOS 27 — Scrolling Reverse Engineering: Master Execution Plan

> **Status**: PLANNING — No phase has been executed yet.
> **Created**: 2026-11-09
> **Target**: iPhone18,3 / iOS 27.2 / Build 24B119 / arm64e

---

## 0. Prompt Analysis & Justifiable Changes

### What the original prompt gets right

The prompt is exceptionally well-structured. It correctly:

1. **Prioritizes binary evidence over documentation** — this is the single most important design decision.
2. **Separates investigation from implementation** — the deliverable is a research report, not code.
3. **Demands confidence classification** — Confirmed / Strongly inferred / Tentative / Unknown.
4. **Requires mathematical precision** — recover actual equations, not textbook substitutes.
5. **Acknowledges system-wide scope** — scrolling is not just `UIScrollView`.
6. **Demands reproducibility** — addresses, UUIDs, binary identifiers.
7. **Structures phases from reconnaissance → deep investigation → cross-validation → synthesis**.

### Changes made and why

| # | Change | Rationale |
|---|--------|-----------|
| 1 | **Split Phase 1 into 1A (workspace audit) and 1B (scrolling symbol discovery)** | The workspace is already mature (8 prior phases completed, shared cache extracted, tooling proven). A full workspace audit would duplicate existing `progress.json` and `shared_cache_overview.json`. Instead, 1A reuses existing inventory and 1B immediately starts scrolling-specific reconnaissance. |
| 2 | **Added explicit "shared cache extraction check" step** | Only `.36` subcache + main header are visible. The split cache has 81 subcaches but only 2 files are on disk. This may mean subcaches are embedded in the `.36` file, or they're missing. This must be resolved before any framework analysis. |
| 3 | **Added Phase 0: Tooling Validation** | The keyboard RE project proved REA and Ghidra work on this cache. But scrolling analysis requires opening UIKitCore (~50MB+ in cache), QuartzCore, SwiftUI — the largest frameworks. We need to confirm the tools can handle them before committing to a multi-phase plan. |
| 4 | **Moved "Reusable Implementation Specification" (report §16) to a dedicated Phase 8** | The original prompt places it as a report section, but it's actually the most valuable deliverable. It deserves its own focused investigation phase where the engineering spec is derived from confirmed findings, not written as an afterthought during report assembly. |
| 5 | **Added explicit "Evidence Ledger" as a living document** | The prompt mentions maintaining research notes but doesn't specify format. An evidence ledger (structured JSON/Markdown) ensures findings persist across sessions and agents. |
| 6 | **Scoped Phase 3 into 3A-3D sub-phases** | "Deep investigation of core mechanisms" covers 12 different subsystems. Attempting all 12 in one phase will produce superficial results. Sub-phases with explicit entry/exit criteria prevent this. |
| 7 | **Added Phase 3E: IOHIDPointerScrollFilter investigation** | The shared cache contains `IOHIDPointerScrollFilter.plugin/IOHIDPointerScrollFilter` — a HID-level scroll filter that processes trackpad/mouse scroll events before they reach UIKit. The original prompt mentions trackpad/mouse scrolling but doesn't call out this specific binary, which is likely the lowest-level scroll processing we can access. |
| 8 | **Removed "Dynamic analysis" as a gating concern** | The workspace has no iOS device or simulator. The keyboard RE project confirmed this. All dynamic analysis sections are marked as static-only from the start, avoiding repeated "we couldn't do dynamic analysis" blockers. |
| 9 | **Added the `Gestures.framework` as a primary target** | Found in the shared cache: `/System/Library/PrivateFrameworks/Gestures.framework/Gestures`. This private framework likely contains gesture recognition infrastructure that's separate from UIKit's public gesture API. |

### What was NOT changed

- The 7-phase research structure is preserved (renumbered 0-8 to accommodate additions).
- The 18-section final report structure is preserved exactly.
- All evidence standards, confidence classifications, and quality requirements are preserved.
- The completion criteria are preserved.
- The "depth over breadth" principle is preserved and reinforced in the sub-phase design.

---

## 1. Workspace Context (From Reconnaissance)

### What we have

| Asset | Status | Location |
|-------|--------|----------|
| IPSW contents | Extracted | `iPhone18,3_27.2_24B119_Restore/` |
| dyld shared cache (arm64e) | Extracted | `artifacts/rootfs/shared_cache/.../dyld_shared_cache_arm64e` + `.36` + `.atlas` |
| Shared cache image count | 4,770 frameworks/dylibs | Cataloged in `shared_cache_overview.json` |
| Root filesystem (partial) | Extracted from 3 unencrypted DMGs | `artifacts/rootfs/` |
| Prior RE work (8 phases) | Completed | `findings/`, `artifacts/`, `progress.json` |
| Keyboard RE | Completed | `ios27-keyboard-reverse-engineering/` |
| Knowledge graph | Built | `graphify-out/` |

### Primary binary targets (confirmed present in shared cache)

| Framework | Path in Cache | Relevance |
|-----------|--------------|-----------|
| **UIKitCore** | `/System/Library/PrivateFrameworks/UIKitCore.framework/UIKitCore` | Core scrolling: UIScrollView, pan gesture, velocity, rubber-banding |
| **QuartzCore** | `/System/Library/Frameworks/QuartzCore.framework/QuartzCore` | Core Animation: CADisplayLink, animation timing, compositing |
| **SwiftUI** | `/System/Library/Frameworks/SwiftUI.framework/SwiftUI` | SwiftUI ScrollView, List, gesture infrastructure |
| **SwiftUICore** | `/System/Library/Frameworks/SwiftUICore.framework/SwiftUICore` | SwiftUI core infrastructure |
| **WebKit** | `/System/Library/Frameworks/WebKit.framework/WebKit` | Web content scrolling |
| **WebKitLegacy** | `/System/Library/PrivateFrameworks/WebKitLegacy.framework/WebKitLegacy` | Legacy web scrolling |
| **UIKit** | `/System/Library/Frameworks/UIKit.framework/UIKit` | Public UIKit API surface |
| **Gestures** | `/System/Library/PrivateFrameworks/Gestures.framework/Gestures` | Private gesture framework |
| **CoreText** | `/System/Library/Frameworks/CoreText.framework/CoreText` | Text layout/scrolling |
| **IOHIDPointerScrollFilter** | `/System/Library/HIDPlugins/IOHIDPointerScrollFilter.plugin/...` | HID-level scroll event processing |
| **AnimationKit** | `/System/Library/PrivateFrameworks/AnimationKit.framework/AnimationKit` | Animation infrastructure |
| **SystemUIAnimationKit** | `/System/Library/PrivateFrameworks/SystemUIAnimationKit.framework/SystemUIAnimationKit` | System UI animations |
| **UIKitServices** | `/System/Library/PrivateFrameworks/UIKitServices.framework/UIKitServices` | UIKit service layer |

### Tools available

| Tool | Access | Proven? |
|------|--------|---------|
| REA MCP (186 tools) | ✅ Full access | ✅ Used successfully in keyboard RE |
| Ghidra MCP (29 tools) | ✅ Full access | ✅ Used successfully in keyboard RE |
| `objdump`, `nm`, `strings` | ✅ System tools | ✅ |
| Python3 + custom parsers | ✅ `tools/` | ✅ |
| Graphify | ✅ Knowledge graph | ✅ |
| Frida (runtime) | ❌ No device | N/A |
| iOS Simulator | ❌ Not available | N/A |

### Known limitations

1. **No dynamic analysis** — no device, no simulator, no Frida. All findings are static-analysis only.
2. **4 AEA-encrypted DMGs** — ~10.3 GB of content is inaccessible. May contain additional UI resources.
3. **Shared cache split** — must verify all subcaches are accessible via REA/Ghidra.
4. **Symbol stripping** — some internal functions will have stripped symbols (observed in keyboard RE).
5. **arm64e PAC** — pointer authentication complicates some disassembly patterns.
6. **No runtime constants** — some animation parameters may be set at runtime and won't appear in static analysis.

---

## 2. Phase Architecture

```
Phase 0: Tooling Validation (GATE)
    ↓ pass
Phase 1A: Workspace Audit (reuse existing + verify)
    ↓
Phase 1B: Scrolling Symbol Discovery & Inventory
    ↓
Phase 2: Architecture Mapping
    ↓
Phase 3A: Input Pipeline & Gesture Recognition
    ↓
Phase 3B: Scrolling Physics & Motion (CRITICAL)
    ↓
Phase 3C: Rubber-banding, Boundaries & Bounce
    ↓
Phase 3D: Snapping, Paging & Positioning
    ↓
Phase 3E: Low-Level Input (IOHIDPointerScrollFilter)
    ↓
Phase 4: Specialized Implementations (SwiftUI, WebKit, etc.)
    ↓
Phase 5: Rendering & Frame Scheduling
    ↓
Phase 6: Cross-Validation
    ↓
Phase 7: Nested Scrolling & Complex Interfaces
    ↓
Phase 8: Reusable Implementation Specification
    ↓
Phase 9: Final Report Synthesis
```

---

## 3. Detailed Phase Definitions

### Phase 0 — Tooling Validation (GATE)

> **Purpose**: Confirm that REA and Ghidra can open and analyze the scroll-relevant frameworks within the shared cache before committing to the full investigation.

**Entry criteria**: Workspace exists, shared cache is on disk.

**Tasks**:
1. Use REA `open_binary` on the dyld shared cache path to establish a session.
2. Attempt to search for `UIScrollView` classes via `get_objc_classes` with filter.
3. Attempt to search procedures matching `*scroll*`, `*Scroll*`, `*decelerat*`, `*rubberBand*`.
4. Attempt to decompile one known UIScrollView method (e.g., `setContentOffset:animated:`).
5. Verify Ghidra can also connect and search the same binary.
6. Document any tool limitations, errors, or performance issues.

**Exit criteria**: At least one scrolling-related method has been successfully decompiled from UIKitCore within the shared cache. If this fails, document the blocker and propose alternatives before proceeding.

**Artifacts**:
- `artifacts/scrolling/phase0_tooling_validation.json`

**Estimated effort**: Small (1 agent, 1 session).

---

### Phase 1A — Workspace Audit (Reuse & Verify)

> **Purpose**: Establish the scrolling investigation's baseline by reusing existing workspace inventory and verifying relevant assets.

**Entry criteria**: Phase 0 passed.

**Tasks**:
1. Read existing `progress.json`, `shared_cache_overview.json`, and `findings/08_SYNTHESIS_AND_GRAPH.md`.
2. Verify the iOS build metadata: version 27.2, build 24B119, arm64e, iPhone18,3.
3. Confirm all 4,770 shared cache images are accessible.
4. Verify the 13 primary scroll-related frameworks are present (table in §1 above).
5. Verify subcache accessibility — can REA read across subcache boundaries?
6. Check for any scroll-related content in existing findings (SpringBoard analysis, UI assets, etc.).
7. Produce the scrolling investigation's baseline context document.

**Exit criteria**: Baseline document produced with confirmed framework inventory and tool accessibility.

**Artifacts**:
- `findings/scrolling/01A_WORKSPACE_BASELINE.md`

**Estimated effort**: Small (1 agent, 1 session).

---

### Phase 1B — Scrolling Symbol Discovery & Inventory

> **Purpose**: Build a comprehensive inventory of every scrolling-related class, protocol, method, and symbol across all relevant frameworks. This is the foundation for all subsequent investigation.

**Entry criteria**: Phase 1A complete.

**Tasks**:
1. **UIKitCore symbol sweep**:
   - `get_objc_classes` with filters: `*Scroll*`, `*scroll*`, `*Decelerat*`, `*Momentum*`, `*RubberBand*`, `*Bounce*`, `*PanGesture*`, `*Velocity*`, `*ContentOffset*`, `*Indicator*`, `*Paging*`
   - For each discovered class: extract methods, ivars, protocols via `get_objc_classes` with `include_methods: true, include_ivars: true, include_protocols: true`
   - `search_procedures` with patterns: `*scroll*`, `*Scroll*`, `*decelerat*`, `*rubberBand*`, `*bounce*`, `*velocity*`, `*momentum*`, `*contentOffset*`, `*panGesture*`, `*indicator*`, `*snapping*`, `*paging*`
   - `search_strings` for scroll-related constants and log messages

2. **QuartzCore symbol sweep**:
   - `get_objc_classes` for `*DisplayLink*`, `*Animation*`, `*Spring*`, `*Timing*`
   - `search_procedures` for `*displayLink*`, `*spring*`, `*animation*`

3. **SwiftUI symbol sweep**:
   - `analyze_swift_types` with filter `*Scroll*`, `*scroll*`, `*List*`, `*Gesture*`
   - `get_objc_classes` for SwiftUI bridge classes

4. **Gestures.framework sweep**:
   - Full `get_objc_classes` (likely small framework)
   - `list_procedures` to catalog all functions

5. **IOHIDPointerScrollFilter sweep**:
   - Full `get_objc_classes` and `list_procedures`

6. **Cross-framework search**:
   - `search_strings` across all targets for: `deceleration`, `rubber`, `bounce`, `momentum`, `velocity`, `scroll`, `friction`, `damping`, `spring`

7. **Produce structured inventory**:
   - CSV: Class name, Framework, Method count, Ivar count, Protocol conformances
   - JSON: Full class metadata for scroll-related classes
   - Markdown: Annotated inventory with initial classification (core vs. specialized)

**Exit criteria**: 
- ≥50 scroll-related classes identified and cataloged with full metadata
- ≥200 scroll-related methods identified
- ≥10 frameworks assessed for scrolling relevance
- Inventory documents on disk

**Artifacts**:
- `artifacts/scrolling/scroll_class_inventory.json`
- `artifacts/scrolling/scroll_class_inventory.csv`
- `artifacts/scrolling/scroll_method_inventory.json`
- `artifacts/scrolling/scroll_string_inventory.json`
- `findings/scrolling/01B_SYMBOL_DISCOVERY.md`

**Estimated effort**: Medium (1-2 agents, likely 2-3 sessions due to large search space).

---

### Phase 2 — Architecture Mapping

> **Purpose**: From the symbol inventory, reconstruct the scrolling architecture — class hierarchies, framework boundaries, protocol relationships, and execution flow from input to rendering.

**Entry criteria**: Phase 1B complete with populated inventories.

**Tasks**:
1. **Class hierarchy reconstruction**:
   - For each scroll-related class, determine superclass chain
   - Map UIScrollView's full inheritance tree
   - Map UITableView/UICollectionView relationship to UIScrollView
   - Identify internal/private superclasses or mix-in classes

2. **Protocol mapping**:
   - `get_objc_protocols` for `*Scroll*`, `*Delegate*`, `*Gesture*`
   - Map which classes adopt which protocols
   - Identify private/internal protocols not in public headers

3. **Framework dependency mapping**:
   - Determine which frameworks import which (via `inspect_macho` load commands)
   - Build framework-level dependency graph for scrolling subsystem

4. **Execution path tracing** (high-level):
   - Use `get_call_graph` on key entry points:
     - `UIScrollView setContentOffset:animated:`
     - `UIScrollView _scrollViewWillBeginDragging`
     - `UIPanGestureRecognizer` action methods
   - Build preliminary input→gesture→scroll→animation→render flow diagram

5. **State container identification**:
   - Identify the main data structures that hold scroll state (position, velocity, deceleration params)
   - Map ivar layouts for UIScrollView, internal animation controllers, etc.

6. **SwiftUI bridge mapping**:
   - Determine how SwiftUI ScrollView connects to UIKit scrolling
   - Identify bridge classes, hosting controllers, etc.

**Exit criteria**:
- Complete class hierarchy diagram for UIScrollView and related classes
- Framework dependency graph
- Preliminary execution flow diagram (input → render)
- Protocol adoption map
- State container identification

**Artifacts**:
- `findings/scrolling/02_ARCHITECTURE_MAP.md` (with Mermaid diagrams)
- `artifacts/scrolling/class_hierarchy.json`
- `artifacts/scrolling/framework_dependencies.json`
- `artifacts/scrolling/execution_flow_preliminary.json`

**Estimated effort**: Medium-Large (2-3 agents, 2-4 sessions).

---

### Phase 3A — Input Pipeline & Gesture Recognition

> **Purpose**: Reverse engineer the complete input-to-scroll pipeline: from touch events through gesture recognition to the point where scrolling motion begins.

**Entry criteria**: Phase 2 complete with architecture map.

**Tasks**:
1. **Pan gesture recognizer internals**:
   - Decompile `UIPanGestureRecognizer` key methods: `touchesBegan:`, `touchesMoved:`, `touchesEnded:`, `_updateGestureState`
   - Identify state machine (Possible → Began → Changed → Ended/Cancelled/Failed)
   - Extract touch slop / movement threshold constants
   - Determine directional locking logic

2. **UIScrollView's gesture setup**:
   - Decompile `UIScrollView`'s pan gesture recognizer configuration
   - Identify `_UIScrollViewPanGestureRecognizer` (likely private subclass)
   - Determine how UIScrollView's pan recognizer differs from standard UIPanGestureRecognizer
   - Extract gesture delay / recognition threshold values

3. **Gesture arbitration**:
   - Investigate `UIGestureRecognizerDelegate` methods on UIScrollView
   - Determine how simultaneous gesture recognition is configured
   - Investigate gesture failure requirements (e.g., pan requires swipe to fail)
   - Trace how tap, long-press, and pan interact in scroll context

4. **Touch tracking**:
   - Investigate how UIScrollView tracks touch movement during dragging
   - Determine how content offset is updated during finger movement
   - Identify any filtering or smoothing of touch coordinates

5. **Scroll interruption**:
   - Determine how an ongoing momentum scroll is interrupted by a new touch
   - Trace the cancellation → restart path

6. **Direction detection**:
   - Investigate `directionalLockEnabled` implementation
   - Determine how initial direction is detected
   - Investigate horizontal vs. vertical discrimination

**Evidence requirements**: For each discovered threshold/constant, record:
- Binary location (framework, function, offset)
- Actual value
- Context of use
- Confidence level

**Exit criteria**:
- Pan gesture state machine reconstructed with transitions and thresholds
- Touch slop and movement threshold values recovered
- Directional locking algorithm documented
- Gesture arbitration rules documented
- Content offset tracking during drag documented

**Artifacts**:
- `findings/scrolling/03A_INPUT_GESTURE_PIPELINE.md`
- `artifacts/scrolling/gesture_state_machine.json`
- `artifacts/scrolling/input_constants.json`
- `artifacts/scrolling/pseudocode/UIPanGestureRecognizer_*.pseudo.c`
- `artifacts/scrolling/pseudocode/UIScrollView_gesture_*.pseudo.c`

**Estimated effort**: Large (2-3 agents, 3-5 sessions). This is one of the deepest investigation areas.

---

### Phase 3B — Scrolling Physics & Motion (CRITICAL)

> **Purpose**: This is the most important phase. Reverse engineer the actual mathematical models used for finger tracking, velocity estimation, inertial scrolling, deceleration, and spring physics.

**Entry criteria**: Phase 3A complete (understand how gestures feed into scrolling).

**Tasks**:
1. **Velocity estimation**:
   - Identify the class/method responsible for calculating release velocity
   - Determine the sampling strategy (how many touch points? time window?)
   - Identify velocity filtering (exponential moving average? last N samples?)
   - Extract velocity clamping (min/max velocity thresholds)
   - Reconstruct the velocity calculation algorithm with exact formula

2. **Deceleration / inertial scrolling**:
   - Identify the animation class driving inertial scroll (likely `_UIScrollViewDecelerationAnimation` or similar)
   - Decompile its `stepAnimation` / per-frame update method
   - Determine the deceleration model:
     - Is it exponential decay? `v(t) = v₀ · rᵗ`
     - Is it linear friction? `v(t) = v₀ - f·t`
     - Is it something else entirely?
   - Extract the deceleration rate constant(s):
     - `UIScrollViewDecelerationRateNormal` = 0.998 (publicly documented)
     - `UIScrollViewDecelerationRateFast` = 0.99 (publicly documented)
     - Are these the actual values used internally?
   - Determine the integration method (Euler? Verlet? RK4? Fixed timestep?)
   - Identify the termination condition (minimum velocity threshold)
   - Document per-frame position update formula

3. **Spring physics**:
   - Identify spring animation classes (`_UIScrollViewSpringAnimation`, `CASpringAnimation`, etc.)
   - Decompile the spring step function
   - Determine spring model:
     - Underdamped mass-spring-damper?
     - Critically damped?
     - Some other model?
   - Extract spring parameters:
     - Mass
     - Stiffness
     - Damping ratio
     - Natural frequency
   - Determine how spring parameters relate to `UISpringTimingParameters`

4. **Content offset tracking during drag**:
   - Is content offset exactly 1:1 with finger movement?
   - Is there any filtering or prediction?
   - How are fractional pixel positions handled?

5. **Animation coordination**:
   - How do deceleration and spring animations interact?
   - What happens when deceleration reaches a boundary (transition to rubber-band spring)?
   - How are animations interrupted and restarted?

6. **Frame timing integration**:
   - How is the per-frame timestep determined?
   - `CADisplayLink` callback structure
   - Handling of variable frame rates (ProMotion)

**Mathematical reconstruction requirements**:
For each recovered algorithm, produce:
1. Mathematical formula in LaTeX
2. Variable definitions
3. Constant values with binary locations
4. Pseudocode implementation
5. Input/output specification
6. Confidence assessment

**Exit criteria**:
- Velocity estimation algorithm reconstructed with formula
- Deceleration model identified and reconstructed with formula
- Deceleration rate constants recovered with binary locations
- Spring model identified and reconstructed with formula
- Spring parameters recovered
- Termination conditions identified
- Per-frame update formula documented
- Integration method identified

**Artifacts**:
- `findings/scrolling/03B_SCROLLING_PHYSICS.md`
- `artifacts/scrolling/velocity_algorithm.json`
- `artifacts/scrolling/deceleration_model.json`
- `artifacts/scrolling/spring_model.json`
- `artifacts/scrolling/physics_constants.json`
- `artifacts/scrolling/pseudocode/velocity_*.pseudo.c`
- `artifacts/scrolling/pseudocode/deceleration_*.pseudo.c`
- `artifacts/scrolling/pseudocode/spring_*.pseudo.c`

**Estimated effort**: Very Large (3-4 agents, 5-8 sessions). This is the hardest and most valuable phase.

---

### Phase 3C — Rubber-banding, Boundaries & Bounce

> **Purpose**: Reverse engineer the overscroll resistance, rubber-band formula, and bounce-back behavior.

**Entry criteria**: Phase 3B complete (understand the base physics).

**Tasks**:
1. **Rubber-band during drag**:
   - Identify the function that applies rubber-band resistance during dragging past content bounds
   - Determine the resistance formula:
     - `x_rubber = (1 - 1/(x/d * c + 1)) * d` (one common approximation)
     - Or is it a different formula?
   - Extract the rubber-band constant(s)
   - Determine what `d` (dimension) refers to — viewport height? content size?
   - Is resistance symmetric (top vs. bottom, left vs. right)?

2. **Rubber-band during momentum**:
   - How does inertial scroll behave when it hits a boundary?
   - Does it switch to a different deceleration model?
   - Does it immediately transition to a spring animation?

3. **Bounce-back animation**:
   - What animation drives the bounce back to bounds?
   - Is it the same spring model from Phase 3B?
   - What are the spring parameters for bounce-back specifically?
   - How is the initial velocity for the bounce-back determined?

4. **Boundary detection**:
   - How does UIScrollView determine it's at a content boundary?
   - How do `contentInset`, `adjustedContentInset`, `safeAreaInsets` affect boundary calculation?
   - What is the boundary calculation formula?

5. **Horizontal vs. vertical**:
   - Are horizontal and vertical rubber-banding identical?
   - Different constants? Different formulas?

6. **Edge cases**:
   - Content smaller than viewport
   - `alwaysBounceHorizontal` / `alwaysBounceVertical`
   - Zero content size

**Exit criteria**:
- Rubber-band formula reconstructed with constants
- Bounce-back spring parameters recovered
- Boundary calculation formula documented
- Drag vs. momentum boundary behavior distinguished

**Artifacts**:
- `findings/scrolling/03C_RUBBER_BANDING_BOUNCE.md`
- `artifacts/scrolling/rubber_band_formula.json`
- `artifacts/scrolling/bounce_parameters.json`
- `artifacts/scrolling/pseudocode/rubberBand_*.pseudo.c`

**Estimated effort**: Large (2-3 agents, 3-5 sessions).

---

### Phase 3D — Snapping, Paging & Positioning

> **Purpose**: Reverse engineer how iOS determines the final resting position of a scroll after a gesture.

**Entry criteria**: Phase 3B complete.

**Tasks**:
1. **Paging mode**:
   - Decompile `UIScrollView` paging implementation
   - How is page size determined?
   - How is the target page selected based on velocity and position?
   - What is the minimum velocity for page advancement?

2. **Target content offset**:
   - Decompile `targetContentOffsetForProposedContentOffset:withScrollingVelocity:`
   - How does the default implementation work when no delegate overrides it?
   - How does deceleration interact with target offsets?

3. **Scroll-to-top**:
   - Trace the status bar tap → scroll-to-top path
   - What animation is used? Duration? Curve?

4. **Programmatic scrolling**:
   - `setContentOffset:animated:` and `scrollRectToVisible:animated:`
   - What animation type and duration is used?
   - How is an ongoing deceleration interrupted?

5. **Scroll position restoration**:
   - How does iOS save and restore scroll positions across app state transitions?

6. **UICollectionView/UITableView specifics**:
   - `scrollToItemAtIndexPath:` implementation
   - Cell-based snapping behavior

**Exit criteria**:
- Paging algorithm reconstructed
- Target content offset calculation documented
- Programmatic scrolling animation parameters recovered
- Scroll-to-top implementation traced

**Artifacts**:
- `findings/scrolling/03D_SNAPPING_POSITIONING.md`
- `artifacts/scrolling/paging_algorithm.json`
- `artifacts/scrolling/pseudocode/paging_*.pseudo.c`

**Estimated effort**: Medium (1-2 agents, 2-3 sessions).

---

### Phase 3E — Low-Level Input (IOHIDPointerScrollFilter)

> **Purpose**: Investigate the HID-level scroll event processing for trackpad and mouse input, which is a separate pipeline from touch-based scrolling.

**Entry criteria**: Phase 3A complete.

**Tasks**:
1. Open `IOHIDPointerScrollFilter` binary in REA
2. Catalog all classes and methods
3. Determine how scroll wheel events are filtered/transformed
4. Identify any scroll acceleration curves for trackpad/mouse
5. Determine how continuous vs. discrete scroll events are handled
6. Identify interaction with UIKit scroll events

**Exit criteria**:
- IOHIDPointerScrollFilter architecture documented
- Scroll event transformation pipeline identified
- Acceleration curve(s) recovered if present

**Artifacts**:
- `findings/scrolling/03E_IOHID_SCROLL_FILTER.md`
- `artifacts/scrolling/iohid_scroll_filter.json`

**Estimated effort**: Small-Medium (1 agent, 1-2 sessions).

---

### Phase 4 — Specialized Implementations

> **Purpose**: Investigate scrolling implementations outside UIKit's core — SwiftUI, WebKit, text, documents, accessibility, etc.

**Entry criteria**: Phases 3A-3C complete (core UIKit scrolling understood).

**Tasks**:
1. **SwiftUI ScrollView**:
   - Open SwiftUI/SwiftUICore framework
   - Trace `ScrollView` → UIKit bridge
   - Determine which behavior is delegated to UIScrollView vs. reimplemented
   - Investigate `scrollTargetBehavior`, `scrollPosition`, SwiftUI-specific modifiers

2. **WebKit scrolling**:
   - Open WebKit framework
   - Identify `WKScrollView` (likely UIScrollView subclass)
   - Determine how web content scrolling differs
   - Investigate overscroll-behavior CSS property implementation
   - Investigate scroll event throttling for JavaScript

3. **UITextView/UITextKit scrolling**:
   - How does UITextView integrate with UIScrollView?
   - Text-specific scrolling behavior (scroll to cursor, etc.)

4. **UICollectionView/UITableView**:
   - Prefetching during scroll
   - Cell recycling interaction with scroll state
   - `UICollectionViewCompositionalLayout` scrolling behavior

5. **Accessibility scrolling**:
   - VoiceOver scroll gestures
   - `accessibilityScroll:` implementation
   - Accessibility-driven page navigation

6. **Keyboard-driven scrolling**:
   - Arrow key scrolling in scroll views
   - Page Up/Page Down
   - Home/End

7. **Map scrolling (MapKit)**:
   - Does MapKit use UIScrollView or its own implementation?

**Exit criteria**:
- For each specialized context: documented whether it reuses UIScrollView, wraps it, or implements independent scrolling
- Key implementation differences noted
- Bridge classes identified

**Artifacts**:
- `findings/scrolling/04_SPECIALIZED_IMPLEMENTATIONS.md`
- `artifacts/scrolling/swiftui_scroll.json`
- `artifacts/scrolling/webkit_scroll.json`
- `artifacts/scrolling/specialized_inventory.json`

**Estimated effort**: Large (3-4 agents working in parallel, each taking 1-2 specialized contexts).

---

### Phase 5 — Rendering & Frame Scheduling

> **Purpose**: Understand how scroll position changes become visible on the display.

**Entry criteria**: Phase 3B complete.

**Tasks**:
1. **CADisplayLink integration**:
   - How does UIScrollView's animation system hook into the display link?
   - Identify the display link callback chain during scrolling
   - Determine frame timing and priority

2. **Content offset → layer position**:
   - How does `contentOffset` translate to layer/sublayer positioning?
   - Identify the compositing path

3. **ProMotion / variable refresh rate**:
   - How does scrolling interact with variable refresh rates?
   - Is there scroll-driven refresh rate boosting?
   - What frame rate does scrolling target? (120Hz on ProMotion devices)

4. **Scroll indicators**:
   - Identify scroll indicator classes
   - Determine indicator size calculation (proportional to content vs. viewport)
   - Determine indicator position calculation
   - Identify indicator fade animation parameters (delay, duration, curve)
   - Investigate interactive scrollbar (dragging the indicator)

5. **Presentation layer vs. model layer**:
   - During scrolling, which layer tree is authoritative?
   - How does hit-testing work during scroll animation?

**Exit criteria**:
- Display link callback chain documented
- Content offset → visual rendering path traced
- Scroll indicator implementation documented
- ProMotion interaction documented

**Artifacts**:
- `findings/scrolling/05_RENDERING_FRAME_SCHEDULING.md`
- `findings/scrolling/05_SCROLL_INDICATORS.md`
- `artifacts/scrolling/rendering_pipeline.json`
- `artifacts/scrolling/indicator_parameters.json`

**Estimated effort**: Medium (1-2 agents, 2-3 sessions).

---

### Phase 6 — Cross-Validation

> **Purpose**: Cross-check discoveries across related implementations to find inconsistencies, confirm shared behavior, and identify implementation differences.

**Entry criteria**: Phases 3A-5 complete.

**Tasks**:
1. Compare UIKit deceleration behavior with SwiftUI deceleration behavior
2. Compare rubber-banding parameters across UIScrollView, WKScrollView, and UITextView
3. Compare gesture handling between standalone scroll views and nested scroll views
4. Compare scroll indicator behavior across different scroll view types
5. Compare paging behavior between UIScrollView.isPagingEnabled and UICollectionView with paging layout
6. Verify recovered constants are used consistently across related implementations
7. Identify any contradictions and document them

**Exit criteria**:
- Cross-validation matrix produced
- Contradictions documented and explained
- Confirmed shared constants listed
- Implementation differences cataloged

**Artifacts**:
- `findings/scrolling/06_CROSS_VALIDATION.md`
- `artifacts/scrolling/cross_validation_matrix.json`

**Estimated effort**: Medium (1-2 agents, 2-3 sessions).

---

### Phase 7 — Nested Scrolling & Complex Interfaces

> **Purpose**: Investigate how multiple scrolling regions coordinate.

**Entry criteria**: Phases 3A, 3B, 3C complete.

**Tasks**:
1. **Nested scroll view gesture handling**:
   - How does a child scroll view interact with a parent scroll view?
   - When does the child consume the gesture vs. pass it to the parent?
   - How is gesture ownership transferred?

2. **UINavigationController scroll interaction**:
   - Large title collapsing on scroll
   - Toolbar hiding on scroll
   - How do these coordinate with the scroll view?

3. **UISheetPresentationController**:
   - Scroll-to-dismiss in sheets
   - How does sheet drag gesture interact with content scroll?

4. **Momentum transfer**:
   - Can momentum transfer from a child scroll view to a parent?
   - What conditions trigger transfer?

5. **Simultaneous scrolling**:
   - Horizontal inside vertical (e.g., carousel in a vertical list)
   - How is axis locking coordinated between parent and child?

**Exit criteria**:
- Nested gesture arbitration rules documented
- Momentum transfer mechanism identified or confirmed absent
- Navigation/toolbar scroll interaction documented
- Sheet scroll interaction documented

**Artifacts**:
- `findings/scrolling/07_NESTED_SCROLLING.md`
- `artifacts/scrolling/nested_gesture_arbitration.json`

**Estimated effort**: Medium-Large (2-3 agents, 3-4 sessions).

---

### Phase 8 — Reusable Implementation Specification

> **Purpose**: Translate confirmed reverse-engineering findings into an engineering specification for implementing iOS-like scrolling in independent applications.

**Entry criteria**: Phases 3A-7 complete with confirmed findings.

**Tasks**:
1. **Essential mechanisms** — Rank all discovered mechanisms by importance for a convincing iOS-like scroll feel
2. **Algorithm specifications** — For each confirmed algorithm, write an implementation-ready specification with:
   - Input/output contract
   - State variables
   - Mathematical formula
   - Constants (confirmed values vs. suggested defaults)
   - Pseudocode
3. **Architecture recommendation** — Propose a component architecture for a reusable scrolling engine
4. **Parameter tables** — All confirmed constants in a single reference table
5. **Interaction specifications** — Which mechanisms must interact and how
6. **Uncertainty documentation** — What couldn't be confirmed and what an implementer should tune empirically
7. **Test criteria** — How an implementer can verify their implementation matches iOS behavior

**Exit criteria**:
- Implementation-ready specification produced
- All confirmed algorithms have pseudocode
- All confirmed constants have values
- Uncertainty is explicitly documented

**Artifacts**:
- `findings/scrolling/08_IMPLEMENTATION_SPECIFICATION.md`
- `artifacts/scrolling/parameter_reference.json`

**Estimated effort**: Medium (1-2 agents, 2-3 sessions). Primarily synthesis, not binary analysis.

---

### Phase 9 — Final Report Synthesis

> **Purpose**: Consolidate all findings into the final report `IOS_27_SCROLLING_REVERSE_ENGINEERING.md` with all 18 sections.

**Entry criteria**: All previous phases complete.

**Tasks**:
1. Assemble the 18-section report from phase findings
2. Create Mermaid diagrams for architecture, call graphs, state machines
3. Create LaTeX equations for all recovered formulas
4. Build the evidence appendix with binary references
5. Write the executive summary
6. Review for consistency, completeness, and honest uncertainty
7. Final quality check against completion criteria

**Exit criteria**: All 18 report sections populated with real findings. No placeholders. Evidence appendix complete.

**Artifacts**:
- `IOS_27_SCROLLING_REVERSE_ENGINEERING.md` (master report)
- `findings/scrolling/09_UNRESOLVED_QUESTIONS.md`
- `artifacts/scrolling/evidence_appendix.json`

**Estimated effort**: Large (1-2 agents, 3-4 sessions for assembly and quality review).

---

## 4. Agent Assignment Strategy

### Agent Types

| Agent Role | Primary Skills | Key MCP / CLI Tools | Assigned Phases |
|------------|----------------|---------------------|-----------------|
| **Orchestrator** | `agency-multi-agent-systems-architect`, `agency-evidence-collector` | `graphify`, `python3`, `tools/verify_phase.py` | All phases (governance & lifecycle) |
| **Tooling & Recon Specialist** | `investigate-codebase`, `rea` | `rea` (`open_binary`, `get_objc_classes`), `tools/analyze_dyld_cache.py` | Phase 0, Phase 1A |
| **UIKit & Symbol Mining Agent** | `rea`, `agency-evidence-collector` | `rea` (`search_procedures`, `search_strings`, `get_objc_classes`) | Phase 1B, Phase 2 |
| **Input & Gesture RE Agent** | `rea`, `ponytail-review`, `agency-evidence-collector` | `rea` (`procedure_pseudo_code`, `analyze_function`), `ghidra` | Phase 3A, Phase 7 |
| **Kinematics & Physics RE Agent** | `rea`, `agency-statistician`, `ponytail-review` | `rea` (`procedure_pseudo_code`, `read_bytes`), `ghidra` (`decompile_function`) | Phase 3B (CRITICAL), Phase 3C |
| **Positioning & Snapping RE Agent** | `rea`, `investigate-codebase` | `rea` (`procedure_pseudo_code`, `analyze_function`) | Phase 3D |
| **HID Subsystems Agent** | `rea`, `investigate-codebase` | `rea` (`open_binary`, `procedure_pseudo_code`, `inspect_macho`) | Phase 3E |
| **Specialized Frameworks Team** | `rea`, `agency-research-synthesist` | `rea` (`analyze_swift_types`, `procedure_pseudo_code`) | Phase 4 (SwiftUI, WebKit, TextKit, a11y) |
| **CoreAnimation & Compositing Agent**| `rea`, `investigate-codebase` | `rea` (`procedure_pseudo_code`, `find_xrefs_to_name`) | Phase 5 |
| **Drift & Consistency Auditor** | `agency-codebase-archaeologist`, `agency-evidence-collector` | `tools/verify_phase.py`, evidence ledger analysis | Phase 6 (and post-Phase 3/5 checkpoints) |
| **Clean-Room Specification Architect**| `agency-research-synthesist`, `ponytail`, `mobile-android-design` | Python, Markdown compilers | Phase 8 |
| **Synthesis & Master Dossier Lead** | `agency-research-synthesist`, `agency-statistician`, `agency-evidence-collector`| `tools/verify_phase.py`, LaTeX/Markdown synthesis | Phase 9 |

### Phase-to-Skills & Tooling Execution Matrix

| Phase | Phase Name | Primary Skill(s) | Primary MCP / System Tool(s) |
| :--- | :--- | :--- | :--- |
| **0** | Tooling Validation Gate | `rea`, `investigate-codebase` | `rea` (`open_binary`, `procedure_pseudo_code`), `ghidra`, `tools/analyze_dyld_cache.py` |
| **1A** | Workspace Baseline Verification | `investigate-codebase`, `graphify` | `tools/analyze_dyld_cache.py`, `graphify query` |
| **1B** | Scrolling Symbol Discovery | `rea`, `agency-evidence-collector` | `rea` (`get_objc_classes`, `search_procedures`, `search_strings`, `analyze_swift_types`) |
| **2** | Architecture Mapping | `rea`, `graphify`, `agency-multi-agent-systems-architect` | `rea` (`inspect_macho`, `get_objc_protocols`, `get_call_graph`, `trace_call_path`) |
| **3A** | Input Pipeline & Gestures | `rea`, `ponytail-review`, `agency-evidence-collector` | `rea` (`procedure_pseudo_code`, `analyze_function`), `ghidra` |
| **3B** | Physics & Motion Math (CRITICAL) | `rea`, `agency-statistician`, `ponytail-review` | `rea` (`procedure_pseudo_code`, `analyze_function`, `read_bytes`), `ghidra` (`decompile_function`) |
| **3C** | Rubber-Banding & Bounce Mechanics | `rea`, `agency-statistician`, `ponytail-review` | `rea` (`procedure_pseudo_code`, `analyze_function`), `ghidra` |
| **3D** | Snapping, Paging & Positioning | `rea`, `investigate-codebase` | `rea` (`procedure_pseudo_code`, `analyze_function`) |
| **3E** | Low-Level HID Input Filter | `rea`, `investigate-codebase` | `rea` (`open_binary`, `procedure_pseudo_code`, `inspect_macho`) |
| **4** | Specialized Implementations | `rea`, `agency-research-synthesist` | `rea` (`open_binary`, `analyze_swift_types`, `procedure_pseudo_code`) |
| **5** | Rendering & Frame Scheduling | `rea`, `investigate-codebase` | `rea` (`procedure_pseudo_code`, `find_xrefs_to_name`) |
| **6** | Cross-Validation & Drift Audit | `agency-codebase-archaeologist`, `agency-research-synthesist` | `tools/verify_phase.py`, evidence ledger diffing |
| **7** | Nested Scrolling & Coordination | `rea`, `ponytail-review` | `rea` (`procedure_pseudo_code`, `get_call_graph`) |
| **8** | Reusable Implementation Spec | `agency-research-synthesist`, `ponytail`, `mobile-android-design` | Markdown / Math / Pseudocode generators |
| **9** | Master Report Synthesis | `agency-research-synthesist`, `agency-evidence-collector`, `agency-statistician` | `tools/verify_phase.py`, LaTeX/Markdown synthesis |

### Process-Wide Governance Skills (Always Active)
- **`agency-multi-agent-systems-architect`**: Governs inter-agent trust, ensures context windows are not flooded, and enforces strict subagent task scopes.
- **`agency-evidence-collector`**: Enforces the Anti-Hallucination & Zero-Placeholder rule across every phase report.
- **`graphify`**: Acts as the project knowledge index (`graphify query`, `graphify path`), preventing expensive and unbounded recursive disk searches.
- **`tools/verify_phase.py`**: Mechanical gating check executed at the conclusion of every phase before updating `scroll_progress.json`.


### Parallelization Opportunities

```
Phase 3A ──→ Phase 3B ──→ Phase 3C
                 ↓
Phase 3A ──→ Phase 3E (can run parallel with 3B)
                 
Phase 3B ──→ Phase 5 (can run parallel with 3C/3D)

Phase 4 sub-tasks (SwiftUI, WebKit, Text, Accessibility) 
  can ALL run in parallel once Phase 3A-3C are complete
```

---

## 5. Rules for All Agents

### Absolute Rules (inherited from existing workspace + additions)

1. **Sequential phase execution** — Do not skip ahead. Each phase has explicit entry criteria.
2. **Zero placeholders** — Never write "TODO", "TBD", or speculative content as findings.
3. **Evidence citations required** — Every claim must cite: framework, function/class, address/offset, tool used.
4. **Confidence tags mandatory** — Every finding gets one of: `[CONFIRMED]`, `[STRONGLY_INFERRED]`, `[TENTATIVE]`, `[UNKNOWN]`.
5. **No fabricated constants** — If a value cannot be recovered, state "unknown". Do not substitute textbook values.
6. **No documentation-based claims as binary findings** — Clearly separate what is publicly documented from what was discovered in binaries.
7. **Anti-hallucination verification** — For critical findings (physics equations, constants), cross-validate using at least 2 methods (e.g., decompilation + disassembly, or caller analysis + callee analysis).
8. **Persistent on-disk state** — All findings go to `findings/scrolling/`, all artifacts to `artifacts/scrolling/`.
9. **Progress tracking** — Update `artifacts/scrolling/scroll_progress.json` after each phase.
10. **Depth over breadth** — It is better to thoroughly investigate 3 functions than to superficially list 30.

### Scrolling-Specific Rules

11. **Mathematical rigor** — Every recovered equation must include:
    - LaTeX formula
    - Variable definitions
    - Units
    - Constant values (or explicit "unknown")
    - Binary location where the equation was observed
    - Pseudocode equivalent
12. **State machine documentation** — Every state machine must include:
    - State names
    - Transition triggers
    - Guard conditions
    - Actions on transition
13. **Constant recovery protocol** — When a floating-point constant is found:
    - Record its exact IEEE 754 representation
    - Record its hex encoding in the binary
    - Record its address/offset
    - Record the function that uses it
    - Record what it's compared against or multiplied with
14. **No premature unification** — Do not assume UIKit scrolling, SwiftUI scrolling, and WebKit scrolling use the same algorithms until binary evidence confirms it.
15. **Algorithm first, then constants** — Understand what the algorithm does before trying to extract its parameters. A wrong algorithm with right constants is more misleading than a right algorithm with approximate constants.

---

## 6. Progress Tracking

### Progress File

`artifacts/scrolling/scroll_progress.json`

```json
{
  "project": "iOS 27 Scrolling Reverse Engineering",
  "target": "iPhone18,3_27.2_24B119",
  "created_at": "2026-11-09",
  "overall_status": "planning",
  "phases": {
    "phase_0_tooling": { "status": "pending", "entry_criteria_met": false },
    "phase_1a_workspace": { "status": "pending", "entry_criteria_met": false },
    "phase_1b_discovery": { "status": "pending", "entry_criteria_met": false },
    "phase_2_architecture": { "status": "pending", "entry_criteria_met": false },
    "phase_3a_input_gesture": { "status": "pending", "entry_criteria_met": false },
    "phase_3b_physics": { "status": "pending", "entry_criteria_met": false },
    "phase_3c_rubber_band": { "status": "pending", "entry_criteria_met": false },
    "phase_3d_snapping": { "status": "pending", "entry_criteria_met": false },
    "phase_3e_iohid": { "status": "pending", "entry_criteria_met": false },
    "phase_4_specialized": { "status": "pending", "entry_criteria_met": false },
    "phase_5_rendering": { "status": "pending", "entry_criteria_met": false },
    "phase_6_cross_validation": { "status": "pending", "entry_criteria_met": false },
    "phase_7_nested": { "status": "pending", "entry_criteria_met": false },
    "phase_8_specification": { "status": "pending", "entry_criteria_met": false },
    "phase_9_report": { "status": "pending", "entry_criteria_met": false }
  }
}
```

### Evidence Ledger

`artifacts/scrolling/evidence_ledger.jsonl`

Each line is a JSON object:
```json
{
  "id": "EVD-001",
  "phase": "3B",
  "framework": "UIKitCore",
  "class": "_UIScrollViewDecelerationAnimation",
  "method": "_stepAnimation",
  "address": "0x...",
  "finding": "Deceleration uses exponential decay with rate 0.998",
  "confidence": "CONFIRMED",
  "evidence_type": "decompilation",
  "tool": "REA procedure_pseudo_code",
  "cross_validated_with": ["Ghidra decompile_function"],
  "timestamp": "2026-11-XX"
}
```

### Progress Reports

After each phase completion, produce a brief progress report:
- What was investigated
- Key discoveries (bulleted)
- Confidence levels
- Blockers encountered
- Updated question list
- Next phase recommendation

---

## 7. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| REA cannot open UIKitCore from shared cache | Low (keyboard RE worked) | **Critical** — blocks everything | Phase 0 gate check; fallback to Ghidra only |
| Key scrolling functions have stripped symbols | Medium | High — algorithms harder to find | Use xref tracing from known public API entry points; trace backward from known constants |
| Deceleration/spring logic is in CoreAnimation, not UIKit | Medium | Medium — need to analyze additional framework | Phase 2 architecture mapping will reveal this; QuartzCore is in target list |
| Mathematical constants are set at runtime | Medium | High — cannot recover exact values | Document as `[UNKNOWN]` with observed behavior description; check for default values in binary data sections |
| Shared cache subcaches are incomplete | Low-Medium | High — may miss frameworks | Phase 0 verification; check `.36` subcache coverage |
| SwiftUI has its own scrolling engine (not wrapping UIScrollView) | Low | Medium — doubles investigation scope | Phase 4 will determine this; allocate contingency effort |
| Investigation scope creep | High | Medium — delays completion | Strict phase entry/exit criteria; "depth over breadth" rule |
| Context window exhaustion during deep decompilation | High | Medium — agent loses context | Persist all findings immediately; use evidence ledger; split into focused sub-sessions |

---

## 8. Estimated Timeline

| Phase | Estimated Sessions | Can Parallelize? | Cumulative |
|-------|-------------------|-----------------|------------|
| Phase 0 | 1 | No (gate) | 1 |
| Phase 1A | 1 | No | 2 |
| Phase 1B | 2-3 | No | 4-5 |
| Phase 2 | 2-4 | No | 6-9 |
| Phase 3A | 3-5 | No | 9-14 |
| Phase 3B | 5-8 | After 3A | 14-22 |
| Phase 3C | 3-5 | After 3B | 17-27 |
| Phase 3D | 2-3 | With 3C | 17-27 |
| Phase 3E | 1-2 | With 3B | 15-24 |
| Phase 4 | 3-5 (parallel) | After 3A-3C | 20-32 |
| Phase 5 | 2-3 | With Phase 4 | 20-32 |
| Phase 6 | 2-3 | After all above | 22-35 |
| Phase 7 | 3-4 | With Phase 6 | 22-35 |
| Phase 8 | 2-3 | After 6,7 | 24-38 |
| Phase 9 | 3-4 | After all | 27-42 |

**Total estimated: 27-42 agent sessions** (with parallelization reducing wall-clock time).

---

## 9. Success Criteria (from original prompt, preserved)

The investigation is not complete merely because a report exists. Before declaring completion:

- [ ] Relevant binaries and frameworks inventoried
- [ ] Primary scrolling architecture reconstructed
- [ ] Major input-to-scroll execution paths traced
- [ ] Core physics and motion mechanisms investigated with mathematical precision
- [ ] Rubber-banding, deceleration, and bounce investigated independently
- [ ] Nested scrolling and gesture arbitration investigated
- [ ] Rendering and frame scheduling investigated
- [ ] Major specialized scrolling systems assessed
- [ ] Important mathematical parameters recovered or explicitly marked unknown
- [ ] Major claims have traceable binary evidence
- [ ] Reusable implementation specification derived from actual discoveries
- [ ] Remaining gaps and limitations documented

**Ultimate test**: Can another engineer use the final report to understand Apple's scrolling architecture and make technically informed decisions when reproducing its scrolling behavior?

---

## 10. Directory Structure (to be created)

```
artifacts/scrolling/
├── phase0_tooling_validation.json
├── scroll_class_inventory.json
├── scroll_class_inventory.csv
├── scroll_method_inventory.json
├── scroll_string_inventory.json
├── class_hierarchy.json
├── framework_dependencies.json
├── execution_flow_preliminary.json
├── gesture_state_machine.json
├── input_constants.json
├── velocity_algorithm.json
├── deceleration_model.json
├── spring_model.json
├── physics_constants.json
├── rubber_band_formula.json
├── bounce_parameters.json
├── paging_algorithm.json
├── iohid_scroll_filter.json
├── swiftui_scroll.json
├── webkit_scroll.json
├── specialized_inventory.json
├── rendering_pipeline.json
├── indicator_parameters.json
├── cross_validation_matrix.json
├── nested_gesture_arbitration.json
├── parameter_reference.json
├── evidence_appendix.json
├── scroll_progress.json
├── evidence_ledger.jsonl
└── pseudocode/
    ├── UIPanGestureRecognizer_*.pseudo.c
    ├── UIScrollView_gesture_*.pseudo.c
    ├── UIScrollView_*.pseudo.c
    ├── velocity_*.pseudo.c
    ├── deceleration_*.pseudo.c
    ├── spring_*.pseudo.c
    ├── rubberBand_*.pseudo.c
    └── paging_*.pseudo.c

findings/scrolling/
├── 01A_WORKSPACE_BASELINE.md
├── 01B_SYMBOL_DISCOVERY.md
├── 02_ARCHITECTURE_MAP.md
├── 03A_INPUT_GESTURE_PIPELINE.md
├── 03B_SCROLLING_PHYSICS.md
├── 03C_RUBBER_BANDING_BOUNCE.md
├── 03D_SNAPPING_POSITIONING.md
├── 03E_IOHID_SCROLL_FILTER.md
├── 04_SPECIALIZED_IMPLEMENTATIONS.md
├── 05_RENDERING_FRAME_SCHEDULING.md
├── 05_SCROLL_INDICATORS.md
├── 06_CROSS_VALIDATION.md
├── 07_NESTED_SCROLLING.md
├── 08_IMPLEMENTATION_SPECIFICATION.md
└── 09_UNRESOLVED_QUESTIONS.md

IOS_27_SCROLLING_REVERSE_ENGINEERING.md  ← Final deliverable
```
