# 12. Lexicon Architecture, Linguistic Assets & Storage Schemas

- **Target Build**: iOS 27.2 (Build `24B119`)
- **Hardware Platform**: `iPhone18,3` (SoC: Apple Silicon `t8150`)
- **Total Cataloged Assets**: 2,053 resources indexed in `05_RESOURCE_INVENTORY.csv`
- **Primary Asset Locations**: `/System/Library/TextInput/`, `/System/Library/LinguisticData/`, `/System/Library/PrivateFrameworks/`

---

## 1. Asset Catalog Topography & Classification

The 2,053 non-executable assets that power the iOS 27 keyboard ecosystem span four distinct structural categories:

```
[ Master Asset Hierarchy (2,053 Indexed Items) ]
  |
  +-- 1. Declarative Layout Bundles (98 bundles / 710 plists)
  |      Located in /System/Library/TextInput/TextInput_*.bundle/
  |      InputMode_*.plist, Keyboard-*.plist, LayoutDefinitions
  |
  +-- 2. CoreUI Compiled Asset Catalogs (Assets.car)
  |      UIKitCore Artwork.bundle (1,058 renditions, 3.31 MB)
  |      TextInputUI Assets.car (300 renditions, 1.17 MB)
  |      CarPlay Artwork.bundle (209 KB)
  |
  +-- 3. Linguistic Data & Dictionaries (755 bundle items)
  |      Located in /System/Library/LinguisticData/
  |      sys.dic (Double-Array Tries), lm.dat (N-Gram LMs), fst.dat
  |      Mecabra CJK Lexical Databases (zh_Hans, zh_Hant, ja)
  |
  +-- 4. SQLite Persistent Stores & Dynamic Schemas
         ~/Library/Keyboard/rejections.sqlite (Autocorrection memory)
         ~/Library/Keyboard/shape_store.sqlite (Glide typing paths)
         ~/Library/Keyboard/CoreData (CloudKit text replacements)
```

---

## 2. Declarative Keyboard Layout Bundles (`TextInput_*.bundle`)

### 2.1 Directory Structure
Each language plugin in `/System/Library/TextInput/` contains structured metadata defining key geometry and input rules:
- **`InputMode_*.plist`**: Declares supported input modes, default layout identifiers, hardware keyboard physical mappings, and multi-language clustering.
- **`Keyboard-*.plist`**: Defines the physical keyplane geometry, key dimensions, touch padded bounds, and alternate character popups.

### 2.2 Reconstructed Schema: `Keyboard-Default.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>UIKBTreeType</key>
    <string>UIKBTreeTypeKeyboard</string>
    <key>Name</key>
    <string>en_US-QWERTY</string>
    <key>VisualStyling</key>
    <string>UIKBVisualStylingDefault</string>
    <key>Subtrees</key>
    <array>
        <!-- Keyplane: Lowercase Letters -->
        <dict>
            <key>UIKBTreeType</key>
            <string>UIKBTreeTypeKeyplane</string>
            <key>Name</key>
            <string>letters-default</string>
            <key>SupportsContinuousPath</key>
            <true/>
            <key>Subtrees</key>
            <array>
                <!-- Row 1: q w e r t y u i o p -->
                <dict>
                    <key>UIKBTreeType</key>
                    <string>UIKBTreeTypeRow</string>
                    <key>Frame</key>
                    <string>{{0, 0}, {393, 54}}</string>
                    <key>Subtrees</key>
                    <array>
                        <dict>
                            <key>UIKBTreeType</key>
                            <string>UIKBTreeTypeKey</string>
                            <key>RepresentedString</key>
                            <string>q</string>
                            <key>DisplayString</key>
                            <string>q</string>
                            <key>Frame</key>
                            <string>{{3, 6}, {33, 42}}</string>
                            <key>PaddedFrame</key>
                            <string>{{0, 0}, {39, 54}}</string>
                            <key>PopupVariants</key>
                            <array>
                                <string>1</string>
                            </array>
                        </dict>
                        <!-- Additional keys: w, e, r, t, y, u, i, o, p -->
                    </array>
                </dict>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

---

## 3. Linguistic Data Architecture (`/System/Library/LinguisticData/`)

The linguistic data subsystem houses language models and dictionaries for 78 supported languages across 755 package bundles:

### 3.1 Lexical Trie Architecture (`sys.dic`)
- **Data Structure**: Compact Double-Array Trie (DAT) with Base and Check integer arrays.
- **Search Complexity**: $O(L)$ where $L$ is the input word length, independent of total vocabulary size (typically 120,000–350,000 words).
- **Embedded Attributes**:
  - Unigram log-probability cost.
  - Part-of-speech (POS) tags.
  - Capitalization flags (lowercase, initial capital, all caps).
  - Common misspelling pointers for high-speed single-step autocorrection.

### 3.2 Statistical Language Models (`lm.dat` & `fst.dat`)
- **Format**: Weighted Finite-State Transducers (WFST) and smoothed Kneser-Ney 3-gram backoff models.
- **Role**: Computes transition probabilities $P(w_i \mid w_{i-1}, w_{i-2})$ given surrounding document context extracted via `RTIDocumentState`.

### 3.3 Indic Script Complex Text Layout Engines
For Indic writing systems (Devanagari, Tamil, Telugu, Bengali, Gurmukhi, Gujarati, Malayalam, Kannada), `TextInputCore` implements contextual ligature shaping rules:
- **Virama (Halant) Chaining**: Converts consonant + virama + consonant into half-form ligatures (e.g. क् + ष -> क्ष).
- **Matra Reordering**: Pre-base vowel signs (e.g. Devanagari short 'i' [ि]) automatically reorder visually before the consonant cluster during typing.
- **Nukta Placement**: Diacritic marks correctly attach to base consonants without corrupting phonetic trie traversal.

---

## 4. CoreUI Asset Catalogs (`Assets.car`)

Extraction of `System/Library/PrivateFrameworks/UIKitCore.framework/Artwork.bundle/Assets.car` (3,308,040 bytes) and `TextInputUI.framework/Assets.car` (1,168,296 bytes) reveals **1,358 total image renditions**:

| Rendition Category | Asset Types Included | Appearance Variants | Resolution Scales |
|---|---|---|---|
| **Keycap Glyphs** | Shift, CapsLock, Delete, Return, Globe, Dictation, EmojiIcon, Undo, Redo | Light, Dark, High-Contrast Accessibility | `@2x` (Retina), `@3x` (Super Retina OLED) |
| **Backdrop Slices** | Padded keycap rectangles, popup balloon stems, candidate cell rounded pills | Vibrant Light, Vibrant Dark, Tinted Glass | `@2x`, `@3x` |
| **Dictation Waveforms** | Animated audio visualizer bars, processing spinner rings | System Tint Dynamic Color | Vector PDF / Multiresolution PNG |
| **Genmoji Framing** | Vector expression templates, dynamic lighting masks | Standard Dynamic Range, HDR | CoreAnimation CAML vector documents |

---

## 5. SQLite Persistent Storage Specifications

### 5.1 Rejection Store Schema (`rejections.sqlite`)
Located in user storage at `/private/var/mobile/Library/Keyboard/rejections.sqlite`:
- **Page Size**: 4096 bytes.
- **Journal Mode**: WAL (Write-Ahead Logging).
- **Tables**: `rejections` (autocorrection rejections), `inline_completion_rejections` (ghost text rejections).
- **Forensic Utility**: Demonstrates Apple's on-device reinforcement learning mechanism: when a user repeatedly overrides an autocorrection suggestion, the system exponentially penalizes that candidate's score until automatic substitution ceases.

### 5.2 Swipe Shape Store (`shape_store.sqlite`)
Located in user storage at `/private/var/mobile/Library/Keyboard/shape_store.sqlite`:
- Stores normalized gesture path vectors and user-specific inflection point tendencies to adapt continuous-path glide typing accuracy over time.
