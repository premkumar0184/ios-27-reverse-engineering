# 09. Android Clean-Room Porting Blueprint & Architectural Specification

- **Target Build Source**: iOS 27.2 (Build `24B119`, Architecture `arm64e`, SoC `t8150`)
- **Target Platform**: Android Open Source Project (AOSP / Android 15 & 16, API Levels 35–36)
- **Target Runtime**: Android `InputMethodService` + Android NDK (C++20) + Vulkan / RenderNode Graphics
- **Porting Methodology**: Strict Clean-Room Functional Re-Implementation (Zero proprietary Apple binary code)

---

## 1. Master Subsystem Cross-Platform Mapping Matrix

| Architectural Layer | iOS 27 Proprietary Primitive | AOSP Clean-Room Replacement Primitive | Functional Mapping & Semantic Strategy |
|---|---|---|---|
| **Root IME Service** | `UIKeyboardImpl` + `InputUI` system scene | `android.inputmethodservice.InputMethodService` | Central keyboard service managing lifecycle, view inflation, and client focus. |
| **View Presentation** | `UIWindow` at `UIWindowLevelAlert` (100.0) | `WindowManager.LayoutParams.TYPE_INPUT_METHOD` | Dedicated system overlay window floating above client applications. |
| **Text Protocol** | `RemoteTextInput.framework` (`RTIInputSystemClient`) | `android.view.inputmethod.InputConnection` | Standardized bidirectional RPC interface for text queries and mutation. |
| **Document State** | `RTIDocumentState` (context, selection, marked) | `InputConnection.getSurroundingText()` / `getTextBeforeCursor()` | Synchronous / asynchronous snapshot of editor context surrounding caret. |
| **Text Mutation Batch** | `RTITextOperations` (insert, delete, attribute) | `InputConnection.commitText()` + `deleteSurroundingText()` | Atomic text edits executed on consumer application's text buffer. |
| **Focus Arbitration** | `_UIKeyboardArbiter` (Mach service `com.apple.KeyboardArbiter`) | Android `InputMethodManager` + `WindowManager` | System-level focus routing; handles split-screen, picture-in-picture, and desktop modes. |
| **Low-Latency Touch** | `BKSHIDEventDeferring` (`BKSTouchStream` < 8ms) | Android `View.onTouchEvent()` + NDK `AMotionEvent` | Direct touchscreen dispatch; optimized using `Choreographer` vsync alignment. |
| **Layout Tree** | `UIKBTree` (Keyboard -> Keyplane -> Row -> Key) | Declarative XML Keyboards / Jetpack Compose Keyboard Layouts | Hierarchical layout descriptor defining key frames, padded bounds, and alternate popups. |
| **Touch Hit-Testing** | Gaussian spatial probability (`UIKBPerformSpatialHitTest`) | Clean-room C++ Bivariate Gaussian Centroid Scorer | Resolves finger touch pad ambiguity and velocity leads during high-speed typing. |
| **Candidate Engine** | `kbd` daemon + `TextInputCore.framework` | Embedded NDK Shared Library (`libkeyboard_engine.so`) | In-process native C++ predictive engine eliminating cross-process Mach IPC latency. |
| **Quality Filter** | `FavoniusCandQualityFilter` | Log-Likelihood Composite Ranker (LM + Spatial + EditDist) | Balances language model probability against spatial touch distance and edit costs. |
| **Rejection Store** | `rejections.sqlite` (`rejections_database_schema.sql`) | Android Room / SQLite Database (`rejections.db`) | Persists user soft/hard autocorrection rejections to dampen repeat mistakes. |
| **CJK Engine** | `TextInputCJK` + `/usr/lib/libmecabra.dylib` | AOSP Pinyin / Mozc / LibPinyin / Marisa-Trie | Syllable segmentation, word lattice construction, and Viterbi dynamic programming. |
| **Continuous Path** | Metal `PathPipeline` + `InputTranscoder.framework` | Android Vulkan / RenderNode Particle Trail + Gesture Decoder | Glide typing particle visualizer and inflection-point gesture word search. |
| **Hardware Keyboard** | GSEvent / `UIKeyboardImpl.setHardWareKeyboardAttached:` | `onKeyDown` / `onKeyUp` + `Configuration.KEYBOARD_QWERTY` | Detects physical USB/Bluetooth keyboard and minimizes on-screen software canvas. |

---

## 2. Component Implementation Architecture

### 2.1 Clean-Room Android Service Lifecycle (`KeyboardInputMethodService.kt`)
The root service subclasses Android's `InputMethodService`, managing view creation, editor lifecycle transitions, and document synchronization:

```kotlin
package com.cleanroom.keyboard.service

import android.inputmethodservice.InputMethodService
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection
import com.cleanroom.keyboard.engine.NativeKeyboardEngine
import com.cleanroom.keyboard.ui.KeyboardView

class KeyboardInputMethodService : InputMethodService() {
    private lateinit var keyboardView: KeyboardView
    private val nativeEngine = NativeKeyboardEngine()
    
    override fun onCreate() {
        super.onCreate()
        // Initialize NDK language models and SQLite rejection store
        nativeEngine.initialize(applicationContext.filesDir.absolutePath)
    }

    override fun onCreateInputView(): View {
        keyboardView = KeyboardView(this, nativeEngine)
        return keyboardView
    }

    override fun onStartInputView(info: EditorInfo, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        // Replaces iOS updateKeyboardStateForInputMode:
        val inputType = info.inputType
        val isPassword = (inputType and EditorInfo.TYPE_TEXT_VARIATION_PASSWORD) != 0
        keyboardView.configureForEditor(info, isPassword)
        
        // Synchronize initial document state
        syncDocumentContext()
    }

    fun syncDocumentContext() {
        val ic: InputConnection? = currentInputConnection ?: return
        val surroundingText = ic.getSurroundingText(1024, 1024, 0)
        if (surroundingText != null) {
            val before = surroundingText.text.subSequence(0, surroundingText.selectionStart).toString()
            val selected = surroundingText.text.subSequence(surroundingText.selectionStart, surroundingText.selectionEnd).toString()
            val after = surroundingText.text.subSequence(surroundingText.selectionEnd, surroundingText.text.length).toString()
            nativeEngine.updateDocumentState(before, selected, after)
        }
    }

    fun commitTextFromEngine(text: String, backspaces: Int) {
        val ic: InputConnection? = currentInputConnection ?: return
        if (backspaces > 0) {
            ic.deleteSurroundingText(backspaces, 0)
        }
        if (text.isNotEmpty()) {
            ic.commitText(text, 1)
        }
        syncDocumentContext()
    }

    override fun onEvaluateFullscreenMode(): Boolean {
        // Equivalent to iOS behavior: never occlude the entire application in landscape
        return false
    }

    override fun onDestroy() {
        super.onDestroy()
        nativeEngine.destroy()
    }
}
```

---

### 2.2 Clean-Room Native Predictive Engine (`NativeKeyboardEngine.cpp`)
To match the performance of iOS's `TextInputCore` and `kbd` while adhering to Android memory constraints, the predictive engine executes in native C++ via JNI:

```cpp
#include <jni.h>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>
#include <sqlite3.h>

struct KeyCentroid {
    char character;
    float center_x;
    float center_y;
    float width;
    float height;
};

class CleanRoomPredictiveEngine {
private:
    sqlite3* rejection_db_ = nullptr;
    std::vector<KeyCentroid> active_layout_;
    std::string context_before_;
    
public:
    void Initialize(const std::string& storage_path) {
        std::string db_file = storage_path + "/rejections.sqlite";
        sqlite3_open(db_file.c_str(), &rejection_db_);
        
        const char* schema = 
            "CREATE TABLE IF NOT EXISTS rejections ("
            "  typed TEXT, correction TEXT, performed_count INT, soft_rejections INT, hard_rejections INT,"
            "  PRIMARY KEY(typed, correction));";
        sqlite3_exec(rejection_db_, schema, nullptr, nullptr, nullptr);
    }
    
    // Equivalent to iOS UIKBPerformSpatialHitTest
    char ResolveSpatialTouch(float touch_x, float touch_y, float velocity_x, float velocity_y) {
        // Adjust for finger roll velocity lead
        float adj_x = touch_x - (velocity_x * 0.008f);
        float adj_y = touch_y - (velocity_y * 0.008f);
        
        char best_char = '\0';
        float min_dist_sq = 1e9f;
        
        for (const auto& key : active_layout_) {
            // Direct interior hit check
            if (adj_x >= (key.center_x - key.width * 0.5f) && adj_x <= (key.center_x + key.width * 0.5f) &&
                adj_y >= (key.center_y - key.height * 0.5f) && adj_y <= (key.center_y + key.height * 0.5f)) {
                return key.character;
            }
            
            // Centroid Gaussian proximity scoring
            float dx = (adj_x - key.center_x) / (key.width * 0.45f);
            float dy = (adj_y - key.center_y) / (key.height * 0.45f);
            float dist_sq = dx * dx + dy * dy;
            
            if (dist_sq < min_dist_sq) {
                min_dist_sq = dist_sq;
                best_char = key.character;
            }
        }
        return best_char;
    }

    // Equivalent to FavoniusCandQualityFilter
    double ScoreCandidate(const std::string& candidate, const std::string& typed, double lm_prob, double spatial_prob) {
        int edit_dist = ComputeLevenshtein(candidate, typed);
        double edit_penalty = edit_dist * 1.80;
        
        // Query SQLite rejection penalty
        double rejection_penalty = QueryRejectionPenalty(typed, candidate);
        
        return (1.20 * lm_prob) + (0.95 * spatial_prob) - edit_penalty - rejection_penalty;
    }

    int ComputeLevenshtein(const std::string& s1, const std::string& s2) {
        int m = s1.length(), n = s2.length();
        std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1));
        for (int i = 0; i <= m; i++) dp[i][0] = i;
        for (int j = 0; j <= n; j++) dp[0][j] = j;
        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                int cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;
                dp[i][j] = std::min({dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost});
            }
        }
        return dp[m][n];
    }

    double QueryRejectionPenalty(const std::string& typed, const std::string& candidate) {
        if (!rejection_db_) return 0.0;
        sqlite3_stmt* stmt = nullptr;
        const char* query = "SELECT soft_rejections, hard_rejections FROM rejections WHERE typed = ? AND correction = ?;";
        if (sqlite3_prepare_v2(rejection_db_, query, -1, &stmt, nullptr) == SQLITE_OK) {
            sqlite3_bind_text(stmt, 1, typed.c_str(), -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 2, candidate.c_str(), -1, SQLITE_STATIC);
            if (sqlite3_step(stmt) == SQLITE_ROW) {
                int soft = sqlite3_column_int(stmt, 0);
                int hard = sqlite3_column_int(stmt, 1);
                sqlite3_finalize(stmt);
                return (soft * 1.5) + (hard * 3.5);
            }
            sqlite3_finalize(stmt);
        }
        return 0.0;
    }
};
```

---

## 3. Replacement Strategy for Privileged iOS Services

### 3.1 `KeyboardArbiter` Replacement
- **iOS Primitive**: `_UIKeyboardArbiter` tracks active application PID scene tokens via `BSServiceConnection`, preventing multiple apps from competing for the software keyboard.
- **Android Replacement**:
  - The Android framework internally implements this via `InputMethodManagerService` (IMMS).
  - The clean-room implementation leverages `InputMethodService.onWindowShown()` and `onWindowHidden()` to observe presentation states.
  - Multi-Window / Split-Screen (equivalent to iOS Medusa): The clean-room service tracks `displayId` and applies `Configuration.windowConfiguration.bounds` to position floating keyboards on large-screen tablets and foldables.

### 3.2 Low-Latency Touch Routing (`BKSHIDEventDeferring` Replacement)
- **iOS Primitive**: `BKSHIDEventDeferring` bypasses SpringBoard by configuring direct kernel event deferral from `IOHIDEventSystem` to the `InputUI` scene token.
- **Android Replacement**:
  - In Android, all touches dispatched to the `TYPE_INPUT_METHOD` window are routed directly by `InputDispatcher` to the IME view hierarchy without traversing the target application window.
  - Optimization: Use NDK `AMotionEvent` via `InputQueue` inside an `NativeActivity` or custom SurfaceView if sub-8ms touch latency is required.
  - Ensure hardware acceleration is enabled in `AndroidManifest.xml`: `android:hardwareAccelerated="true"`.

### 3.3 Hardware Keyboard Replacement (`detachHardwareKeyboard`)
- **iOS Primitive**: `UIKeyboardImpl.setHardWareKeyboardAttached:` suppresses the software keyboard ribbon when a Smart Keyboard or Bluetooth peripheral connects.
- **Android Replacement**:
  - Override `InputMethodService.onEvaluateInputViewShown()`:
    ```kotlin
    override fun onEvaluateInputViewShown(): Boolean {
        val config = resources.configuration
        val isHardwareKeyboard = (config.keyboard == Configuration.KEYBOARD_QWERTY) &&
                                 (config.hardKeyboardHidden == Configuration.HARDKEYBOARDHIDDEN_NO)
        // If physical keyboard is active, hide main keys but retain candidate suggestion bar
        return !isHardwareKeyboard
    }
    ```

---

## 4. Resource & Linguistic Asset Migration Pipeline

1. **Layout Matrix Transformation**:
   - Write a migration utility (`tools/plist_to_android_xml.py`) to convert iOS `Keyboard-*.plist` key dimensions and alternate popups into Android declarative JSON or XML keyplane models.
2. **Lexicon Extraction**:
   - The double-array trie structure from `/System/Library/LinguisticData/` (`sys.dic`) maps directly to Marisa-Trie or Dawg formats used by open-source AOSP input engines.
3. **SQLite Persistence**:
   - The `rejections_database_schema.sql` schema is 100% standard ANSI SQL and executes natively on Android SQLite3 without modification.
