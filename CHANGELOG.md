# Changelog – Whisper PTT

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.6.0] – 2026-02-22

### Added
- **Output language / translation** – separate dropdown for input and output language
  in Settings → General
  - `"Same as input (no translation)"` – transcribes in the spoken language (previous behaviour)
  - `"English"` – activates Whisper's built-in translation: speak any language,
    receive English text → no cloud API, fully local
- **`output_language` setting** in `settings.json` and `DEFAULTS`
  (`"same"` = no translation, `"en"` = translate to English)
- `task="translate"` passed to `whisper_model.transcribe()` when output language is
  English and input language is not English
- Log message `🌐 Translation mode: → English` shown when translation is active
- Translation strings for `sec_output_lang`, `output_same`, `output_lang_note`
  added to `TRANSLATIONS` (all 4 UI languages: en/de/fr/es)

### Changed
- Recognition language section label renamed to **"Recognition Language (Input)"**
  to distinguish it clearly from the new output language setting
- Settings window height increased from 640 px to 700 px to accommodate new section
- `VERSION` bumped to `"0.6.0"`

### Notes
- Whisper's built-in `task="translate"` only supports **English as the output language**.
  This limitation is noted in the UI. Translation to other languages would require
  an additional post-processing step (out of scope for this release).

---

## [0.5.0] – 2026-02-22

### Added
- **Multilingual UI** – interface language selector in Settings → General
  - Supported languages: English (default), Deutsch, Français, Español
  - All UI strings, buttons, labels, status messages and dialogs translated
  - Recognition language labels adapt to the selected UI language
- **`T(key)` translation system** – central `TRANSLATIONS` dict covers all UI strings
- **`UI_LANGUAGES` dict** – maps display names to language codes (`en/de/fr/es`)
- **`_recog_lang_labels(ui)`** – returns recognition language dropdown labels
  localized to the current UI language
- **`ui_lang` setting** in `settings.json` and `DEFAULTS`
- **`VERSION` constant** (`"0.5.0"`) at the top of `whisper_ptt_gui.py`

### Changed
- `LANGUAGES`, `DEVICES`, `COMPUTE_TYPES` dicts refactored: keys are now
  language codes / device codes, values are display labels (reversed from v0.4)
- `_section()` and `_flat_btn()` now accept translation keys directly
- Settings window title and all tab labels now use `T()` translations
- Model descriptions in Audio tab now use translation keys (`model_tiny`, etc.)
- Hardware detection strings ("not available", "available") now translated
- `_detect_hw()` uses `T("hw_not_available")` / `T("hw_available")`

### Fixed
- Recognition language code correctly resolved from localized label on save
- Device and compute-type values correctly resolved from display labels on save

---

## [0.4.0] – 2026-02-22

### Added
- **Microphone watchdog** – detects silent/empty inputs after Windows reboot
- **`start_audio_stream()` / `restart_audio_stream()`** – manages `sd.InputStream`
  lifecycle with clean stop/start
- **Windows mic permission request** with three fallback strategies:
  1. `winrt.windows.media.capture.MediaCapture` (UWP API)
  2. Windows Registry `ConsentStore\microphone` → `"Allow"` (winreg)
  3. Open `ms-settings:privacy-microphone` + show instruction dialog
- **`_silent_count` counter** – after `SILENT_THRESHOLD` (3) consecutive
  silent recordings → triggers automatic mic restart
- **`🎤↺` retry button** in the overlay status row:
  - Normally dimmed, turns red when a mic problem is detected
  - Manual trigger for `restart_audio_stream()`
- **`mic_ok` / `mic_error` / `mic_stream_error` / `mic_permission_dialog`**
  messages in `ui_queue` for thread-safe UI updates
- **`_show_permission_hint()`** – shows instruction dialog when Windows
  privacy settings are opened automatically
- `subprocess`, `ctypes` added to imports (used by permission strategies)
- `winrt-Windows.Media.Capture` added as optional dependency in `build_exe.bat`
- `winreg`, `ctypes`, `subprocess` added to PyInstaller hidden imports

### Changed
- `audio_callback` now checks `status` parameter from PortAudio and pushes
  `mic_stream_error` to `ui_queue` when the stream reports an error
- `main()` no longer uses `with stream:` context manager; stream is managed
  via `start_audio_stream()` + explicit cleanup on exit
- `_on_close()` now explicitly stops and closes `_audio_stream`

### Fixed
- Stream errors after reboot (broken device handle) are now caught and recovered

---

## [0.3.0] – 2026-02-22

### Added
- **Separate "Recognized Text" panel** – clean text only, no timestamps
- **Separate "Debug / Log" panel** – system messages with `[HH:MM:SS]` timestamps
- **`_clean_texts` list** – stores recognized text without timestamps for copy
- **📋 Copy** button – copies selection or last recognized text (no timestamp)
- **📌 Paste** button – manually pastes last recognized text into active window
- **🗑️ Clear** button per panel (recognized text + log independently clearable)
- **`_flash(msg)`** – temporary status message with auto-revert
- **`_append_recognized(text)`** – inserts into recognized text panel with `─────` separator
- **`_append_log(text)`** – inserts timestamped message into debug panel

### Fixed
- **Settings window does not reopen** – `_settings_win` reference now cleared
  via `on_close_cb` callback; `_on_settings_closed()` sets it to `None`
- **Mouse buttons not recognized in hotkey recorder** – replaced `keyboard` library
  with `pynput` for both keyboard and mouse support
  - Thumb buttons (`mouse_x1`, `mouse_x2`), middle click, etc. now work
- **Copy includes timestamp** – fixed by separating storage (`_clean_texts`)
  from display (text widget with separators)
- **Window drags instead of allowing text selection** – drag bindings moved
  exclusively to title bar (`self._bar`); content area has no drag bindings
- `keyboard` dependency removed; `pynput` replaces it for all input handling

### Changed
- PTT listener rebuilt with `pynput` (keyboard + optional mouse listener)
- `start_ptt_listener()` / `stop_ptt_listener()` use `pynput.keyboard.Listener`
  and `pynput.mouse.Listener`
- `MOUSE_BTN_NAMES` dict maps `pynput.mouse.Button` → string names
- Hotkey recorder in Settings also uses pynput (separate listener pair)
- `_make_text_widget()` now uses `cursor="xterm"` to signal text is selectable

---

## [0.2.0] – 2026-02-21

### Added
- **Settings dialog** (⚙ button) with `ttk.Notebook` tabs:
  - **General tab:** hotkey recorder, recognition language, paste mode,
    sound feedback toggle, transparency slider
  - **Audio/AI tab:** device selector with live hardware detection,
    compute type, Whisper model selection with size/speed info
  - **Advanced tab:** VAD toggle + silence threshold, beam size, reset button
- **Hotkey recorder** – click "Record", press any key combination → saved
- **Persistent settings** – `settings.json` saved next to executable
- **NPU / DirectML support** alongside NVIDIA CUDA and CPU fallback
- **`detect_devices()`** – auto-detects CUDA (torch), Intel NPU (OpenVINO),
  AMD/Qualcomm NPU (ONNX Runtime DmlExecutionProvider)
- **`resolve_device()`** – selects optimal device + compute type
- **Live hardware detection** in Settings (runs async, updates label when done)
- **`settings.json`** schema with all configurable keys
- **`on_settings_saved()` callback** – reloads hotkey listener + model after save
- **Window position persistence** (`window_x`, `window_y` in settings)
- **Transparency setting** applied live via `-alpha` attribute

### Changed
- Model loading respects `cfg["device"]` and `cfg["compute_type"]`
- Hotkey now configurable (was hardcoded `ctrl+alt+space`)
- Language now configurable (was hardcoded `de`)

---

## [0.1.0] – 2026-02-20

### Added
- **Always-on-top overlay** window (frameless, `overrideredirect`)
- **Voice meter** – real-time microphone level visualization (canvas bar)
- **Status dot** with color-coded states and blinking animation during recording
- **Push-to-talk** with `keyboard` library (hardcoded `ctrl+alt+space`)
- **Local transcription** via `faster-whisper` (CUDA or CPU)
- **Auto-paste** via clipboard (Ctrl+V) or direct typing (`pyautogui`)
- **Audio feedback** beeps on start/stop
- **Drag to reposition** via title bar
- **Minimize** button (─) collapses content area
- **Debug log** area (single panel at this stage)
- **`ui_queue`** for thread-safe communication between audio/transcription
  threads and the tkinter main thread
- **`load_model()`** runs in background thread on startup
- **PyInstaller build** via `build_exe.bat` and `whisper_ptt_gui.spec`

---

## Version History Summary

| Version | Date       | Highlights |
|---------|------------|------------|
| 0.6.0   | 2026-02-22 | Output language / translation (speak DE → paste EN) |
| 0.5.0   | 2026-02-22 | Multilingual UI (EN/DE/FR/ES), T() translation system |
| 0.4.0   | 2026-02-22 | Mic watchdog, Windows permission request, auto-restart |
| 0.3.0   | 2026-02-22 | Dual text panels, pynput (mouse buttons), settings fix |
| 0.2.0   | 2026-02-21 | Settings dialog, NPU support, persistent config |
| 0.1.0   | 2026-02-20 | Initial release, basic overlay + PTT transcription |
