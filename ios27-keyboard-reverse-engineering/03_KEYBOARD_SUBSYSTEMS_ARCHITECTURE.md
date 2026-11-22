# 03. Keyboard Subsystems Architecture Deep Dive

- **Target Build**: iOS 27.2 (Build `24B119`)
- **Hardware Target**: `iPhone18,3` (SoC: Apple Silicon `t8150` / A19 Pro family)
- **Architecture**: `arm64e` (Pointer Authentication: `PAC00`, Page Size: 16 KB)
- **Classification**: Master Subsystems Reverse Engineering Specification

---

## 1. System Overview & Multi-Subsystem Decomposition

The iOS 27 Keyboard Ecosystem is an event-driven, multi-process client-server architecture balancing low-latency touch dispatch, hardware-isolated text processing, predictive language modeling, and privileged system UI presentation.

```
+-----------------------------------------------------------------------------------------+
|                                    USER DIGITIZER TOUCH                                 |
+-----------------------------------------------------------------------------------------+
                                             |
                                    [IOHIDEventSystem]
                                             |
                                       (backboardd)
                                             |
                            BKSHIDEventDeferring (Fast-Path)
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
         [Foreground App Process]                        [InputUI Host Scene]
           (MobileSafari / SMS)                           (Window Level 100.0)
                     |                                               |
           RTIInputSystemClient                           UIKeyboardLayoutStar
           (RTIDocumentState)                             (UIKBTree Layout)
                     \                                               /
                      \                                             /
                       \---> RemoteTextInput IPC (BSService) <-----/
                                             |
                                  _UIKeyboardArbiter
                                (Focus & Presentation)
                                             |
                                   com.apple.TextInput
                                             |
                                     (kbd Daemon)
                                    [8MB Hard Jetsam]
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
             TextInputCore                                      TextInputCJK
         (Autocorrection Engine)                            (Mecabra C++ IME)
         (Favonius Quality Filter)                          (Pinyin / Kana Flick)
                     |                                               |
             LinguisticData                                   libmecabra.dylib
          (sys.dic, lm.dat, fst)                            (Multilingual Tries)
```

The system is decomposed into five coordinated subsystems:
1. **UI and Rendering Subsystem (`UIKitCore` + `TextInputUI.framework`)**
2. **Input Handling & Remote Text IPC (`TextInput.framework` + `RemoteTextInput.framework`)**
3. **Language Modeling & Predictive Engine (`kbd` + `TextInputCore.framework`)**
4. **CJK, Multilingual & Emoji/Stickers (`TextInputCJK` + `CoreEmoji` + `StickersSearchCore`)**
5. **System Arbiters & Security Integration (`KeyboardArbiter` + `KeyboardServices` + `BKSHIDEventDeferring`)**

---

## 2. Subsystem 1: UI & Rendering Architecture

### 2.1 Component Topography
- **`UIKitCore.framework`**: Embedded in `dyld_shared_cache_arm64e.01` at VM `0x184752000` (file offset `0x04352000`).
- **`TextInputUI.framework`**: Embedded in `dyld_shared_cache_arm64e.03` at VM `0x18fa93000` (file offset `0x07693000`).
- **`TextInputUI.axbundle`**: Embedded in `dyld_shared_cache_arm64e.03` at VM `0x18c342000` (file offset `0x03f42000`).

### 2.2 Structural Hierarchy: The `UIKBTree`
The software keyboard layout is modeled as an immutable hierarchical N-ary tree (`UIKBTree`):
1. **Keyboard Root (`UIKBTreeTypeKeyboard`)**: Holds global device geometry, screen orientation bounds, and active keyplane references.
2. **Keyplane (`UIKBTreeTypeKeyplane`)**: Represents a specific layout variant (e.g. `letters-default`, `letters-shift`, `numbers-symbols`, `alternate-symbols`).
3. **Row (`UIKBTreeTypeRow`)**: Horizontal slice bounding a sequence of keys.
4. **Key (`UIKBTreeTypeKey`)**: Individual interactive atom containing visual representation, alternate popup variants, touch padded frames, and action types.

#### UIKBTree Attribute Matrix
| Property Name | Property Type | Role & Description |
|---|---|---|
| `UIKBTreePropertyShape` | `UIKBGeometry` | Defines physical bounds, padding, corner radii, and drop-shadow insets. |
| `UIKBTreePropertyGeometry` | `CGRect` | Frame relative to enclosing keyplane coordinate space. |
| `UIKBTreePropertyKeyUnionFrame` | `CGRect` | Convex bounding box encompassing key and its adjacent touch slop zones. |
| `UIKBTreePropertyKeyUnionPaddedFrame` | `CGRect` | Expanded touch-receptive rectangle used during Gaussian spatial hit-testing. |
| `UIKBTreePropertyRepresentedString` | `NSString` | Output Unicode string emitted when the key is committed. |
| `UIKBTreePropertyDisplayString` | `NSString` | Label rendered on the key surface (supports glyph substitution). |
| `UIKBTreePropertySplitMode` | `NSInteger` | Governs floating iPad keyboard, thumb-split keyboard, and one-handed iPhone mode. |

### 2.3 Modular UI: `TextInputUI`
`TextInputUI` provides modern out-of-process user interface components presented in the `InputUI` system scene:
- **`TUIAssistantButtonBarView`**: Hosts quick-action buttons (Undo, Redo, Paste, Dictation, Format) flanking the candidate ribbon.
- **`TUICandidateCell` & `TUIPredictionViewCell`**: High-performance collection view cells rendering autocompletion suggestions, emoji recents, and Apple Intelligence predictive cards.
- **Continuous-Path Metal Shaders (`PathPipeline`)**: Metal-accelerated particle pipeline rendering dynamic glow ribbons along the user's continuous glide trail (`UIKeyboardContinuousPathEffectGlow`).
- **Apple Intelligence Genmoji Vector Shaders**: Dynamic vector animation layers loaded from CoreAnimation CAML archives (`document.caml`).

---

## 3. Subsystem 2: Input Handling & Remote Text IPC Architecture

### 3.1 RTI Oneness: The Remote Text Protocol
iOS 27 unifies all text input via the Remote Text Input (`RTI`) framework (`RemoteTextInput.framework` in subcache `.23`, VM `0x1dcd80000`). The architecture completely decouples the application process from the keyboard process:

```
[ App Process: MobileSafari ]                   [ Keyboard Host: InputUI ]
           |                                                |
  RTIInputSystemClient                               RTIInputSystemService
           |                                                |
           |--- beginRemoteTextInputSessionWithID: -------->|
           |    (RTIDocumentTraits, RTIDocumentState)       |
           |                                                |
           |<-- performTextOperations: (Insert "Hello") ----|
           |    (RTITextOperations)                         |
           |                                                |
           |--- syncDocumentState: ------------------------>|
           |    (contextBefore, selection, contextAfter)    |
```

### 3.2 Wire Payload Formats

#### `RTIDocumentTraits`
- Encapsulates text field properties: `autocapitalizationType`, `autocorrectionType`, `spellCheckingType`, `keyboardType`, `returnKeyType`, `enablesReturnKeyAutomatically`, `secureTextEntry`, `textContentType` (e.g. `username`, `oneTimeCode`, `password`).

#### `RTIDocumentState`
- Wire serialization of text surroundings:
  - `contextBeforeInput`: String of preceding characters (up to 1,024 UTF-16 code units).
  - `selectedText`: Highlighted text range.
  - `contextAfterInput`: String of succeeding characters.
  - `markedText`: Uncommitted composition buffer (essential for CJK Pinyin and Japanese Kana).

#### `RTITextOperations`
- Transactional batch instruction:
  - `backspaceCount`: Number of delete backward operations to execute.
  - `textToAssert`: New string to insert at cursor position.
  - `customInfo`: Extension dictionary carrying telemetry and animation tokens.

---

## 4. Subsystem 3: Language Modeling & Predictive Engine Architecture

### 4.1 The `kbd` Daemon Architecture
- **Location**: Standalone binary on decrypted rootfs at `/System/Library/TextInput/kbd` (292,688 bytes, `arm64e PAC00`).
- **Process Attributes**: Runs under UID `501` (`mobile`), POSIX spawn type `App`.
- **Memory Ceiling**: Enforced by kernel Jetsam at **8,192 KB** (8 MB). Exceeding this boundary triggers immediate `SIGKILL` termination.
- **MachServices**: Registers 17 discrete Mach services via `launchd` (`com.apple.TextInput.kbd.plist`), primarily `com.apple.TextInput`.

### 4.2 Candidate Generation & Scoring: The Favonius Engine
When a typing atom (`TIKeyboardInput`) arrives, `TextInputCore` executes the Favonius candidate quality filter:

$$\text{CompositeScore}(w) = \alpha \cdot \log P_{\text{LM}}(w \mid C) + \beta \cdot \log P_{\text{spatial}}(T \mid w) - \gamma \cdot \text{EditDist}(I, w) - \delta \cdot \text{CaseMismatch}(I, w) - R(I, w)$$

Where:
- $\alpha = 1.20$: Language model context probability weight.
- $\beta = 0.95$: Digitizer spatial Gaussian likelihood weight.
- $\gamma = 1.80$: Levenshtein edit distance penalty factor.
- $\delta = 0.75$: Capitalization mismatch penalty.
- $R(I, w)$: User rejection penalty queried from `rejections.sqlite`.

### 4.3 Autocorrection Rejection Ledger (`rejections.sqlite`)
Maintained on user storage at `~/Library/Keyboard/rejections.sqlite`. Uses SQLite WAL mode:
- **`rejections` table**: Tracks `typed`, `correction`, `performed_count`, `soft_rejections` (candidate bar bypass), and `hard_rejections` (backspaced within 1.5 seconds of correction).
- **`inline_completion_rejections` table**: Tracks machine-suggested ghost text completions rejected by the user.

---

## 5. Subsystem 4: Multilingual, CJK & Emoji / Stickers

### 5.1 CJK Phonetic Processing (`TextInputCJK.framework` + `libmecabra.dylib`)
- `TextInputCJK` (subcache `.69`, VM `0x2b710b000`) mediates between `TIKeyboardInputManager` and the low-level C++ engine `/usr/lib/libmecabra.dylib`.
- **Pinyin Segmentation**: Greedy maximal substring segmenter resolving ambiguous syllable streams (e.g., distinguishing `f-a-n-g-a-n` into `fang'an` [方案] vs `fan'gan` [反感]).
- **Mecabra C++ Lattice**: Converts phonetic syllables into a directed acyclic word lattice weighted by transition costs from `/System/Library/LinguisticData/RequiredAssets_zh_Hans.bundle/`.

### 5.2 Japanese 12-Key Kana Flick Matrix
- `TextInput_ja.bundle` (subcache `.73`, VM `0x2c591f000`) implements the standard Japanese 12-key matrix:
  - Cardinal directions: Center (`a`), Left (`i`), Up (`u`), Right (`e`), Down (`o`).
  - Voiced / Semi-Voiced toggle button (Key 10): cycles Kana through Dakuten (゛), Handakuten (゜), and small forms (っ, ゃ, ゅ, ょ).

### 5.3 Emoji & Stickers Search
- **`CoreEmoji.framework`** (VM `0x1c153a000`) & **`EmojiFoundation.framework`** (VM `0x1c1db9000`): Full Unicode 16.0 emoji catalog, skin tone modifiers, multi-person combination builders.
- **`StickersSearchCore.framework`** (VM `0x2b7130000`): Vector search index over installed sticker packs and user-generated Memoji/Genmoji assets.
- **`stickersd`**: Standalone daemon hosting sticker indexing and image delivery.

---

## 6. Subsystem 5: System Integration, Arbiters & Security Architecture

### 6.1 `KeyboardArbiter.framework`
- Embedded in subcache `.36` at VM `0x226550000` (file offset `0x06150000`).
- **Focus Arbitration**: Manages active client scene tokens (`_UIKeyboardArbiterClientHandle`). Resolves focus competition between split-screen apps (Medusa), Slide Over, and System Aperture (Dynamic Island).
- **Window Level**: Forces the keyboard canvas to `UIWindowLevelAlert` (100.0), guaranteeing the software keyboard floats above all application scenes.
- **Hardware Keyboard Detection**: Monitors IOKit keyboard connect events; upon connection, commands `UIKeyboardImpl` to hide the software keyplane while retaining the auxiliary candidate bar.

### 6.2 Low-Latency Touch Routing: `BKSHIDEventDeferring`
- Capacitive digitizer touch events are received by the kernel `IOHIDEventSystem` and surfaced to `backboardd`.
- Rather than hopping through the SpringBoard application main runloop, `BKSHIDEventDeferring` registers a direct kernel event deferral predicate matching `BKSHIDEventDeferringToken`.
- Touch streams (`BKSTouchStream`) are forwarded directly to the `InputUI` keyboard scene PID, achieving an end-to-end touch-to-render latency under **8.0 milliseconds**.

### 6.3 CloudKit Text Replacement Sync: `KeyboardServices.framework`
- Embedded in subcache `.59` at VM `0x28eee4000`.
- Manages user-defined text replacements (e.g. `omw` -> `On my way!`).
- Backed by an encrypted CoreData SQLite database, synchronized across devices via CloudKit private database containers and awakened via Apple Push Notification service (`com.apple.keyboardServices.textReplacementServer.aps`).
