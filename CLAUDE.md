# CLAUDE.md – Whisper PTT

Instructions for Claude Code when working on this project.
Read this file before making any changes.

---

## Project Overview

**Whisper PTT** is a Windows desktop push-to-talk overlay that transcribes speech
locally using OpenAI Whisper (via `faster-whisper`) and pastes the result into
whatever window is currently active.

- **Main file:** `whisper_ptt_gui.py` – single-file application (~1600 lines)
- **Entry point:** `main()` at the bottom of the file
- **Build:** `build_exe.bat` → PyInstaller → `dist/WhisperPTT/WhisperPTT.exe`
- **Config:** `settings.json` next to the `.exe` (auto-created on first run)
- **Models:** `models/` directory (auto-downloaded on first run)

---

## Architecture

```
main()
 ├── load_settings()              # reads settings.json → global cfg dict
 ├── WhisperPTTApp(root)          # main overlay window (tkinter)
 │    ├── _build_ui()             # always-on-top frameless window
 │    ├── _poll_queue()           # 50ms loop: reads ui_queue → updates widgets
 │    └── SettingsWindow          # modal settings dialog (ttk.Notebook, 3 tabs)
 ├── start_audio_stream()         # sd.InputStream with audio_callback
 └── start_ptt_listener()         # pynput keyboard + mouse global listeners
      ├── _ptt_trigger_press()    → start_recording()
      └── _ptt_trigger_release()  → stop_recording()
                                  → Thread: transcribe_and_paste()
                                       └── whisper_model.transcribe()
                                       └── _do_paste()
```

### Thread model

| Thread | Purpose |
|--------|---------|
| Main (tkinter) | UI event loop |
| `audio_callback` | sounddevice PortAudio callback – appends to `audio_chunks` |
| `_ptt_kb_listener` | pynput keyboard global listener |
| `_ptt_ms_listener` | pynput mouse global listener (only when hotkey uses mouse) |
| `load_model` | loads faster-whisper model on startup / settings change |
| `transcribe_and_paste` | runs after each PTT release |
| `start_audio_stream` | mic init + Windows permission request |

**Thread-safety:** All UI updates go through `ui_queue` (stdlib `queue.Queue`).
Never update tkinter widgets from a non-main thread directly.

### Global state

```python
cfg              # dict – current settings (mirrors settings.json)
whisper_model    # WhisperModel instance (None until loaded)
recording        # bool – True while PTT is held
audio_chunks     # list of np.ndarray – accumulated during recording
current_volume   # float 0.0–1.0 – updated in audio_callback
_audio_stream    # sd.InputStream instance
_ptt_active      # bool – True while hotkey is physically held
_silent_count    # int – counts consecutive silent recordings (mic watchdog)
```

---

## Key Design Decisions

### Translations / i18n
All UI strings go through `T(key)` which looks up `TRANSLATIONS[key][cfg["ui_lang"]]`.
- Supported UI languages: `en` (default), `de`, `fr`, `es`
- `cfg["ui_lang"]` = interface language code
- `cfg["language"]` = Whisper recognition / input language code (separate setting)
- `cfg["output_language"]` = `"same"` (transcribe only) or `"en"` (translate to English)
- **When adding new UI strings:** add the key to `TRANSLATIONS` dict with all 4 languages.
- Recognition language labels are generated dynamically by `_recog_lang_labels(ui)`.

### Settings persistence
- `cfg` is the single source of truth (global dict).
- `load_settings()` merges `settings.json` over `DEFAULTS` at startup.
- `save_settings()` writes `cfg` to `settings.json`.
- `DEFAULTS` defines every key with a safe fallback value.
- **When adding a new setting:** add it to `DEFAULTS`, handle it in `_load_values()`,
  `_save()`, and wire up the widget in the appropriate tab.

### Mic Watchdog
After `SILENT_THRESHOLD` (=3) consecutive silent recordings:
1. `restart_audio_stream()` is called in a background thread
2. It tries `request_windows_mic_permission()` first:
   - Strategy 1: winrt UWP MediaCapture
   - Strategy 2: Windows Registry (`ConsentStore\microphone`)
   - Strategy 3: Open `ms-settings:privacy-microphone` + show dialog
3. Then restarts `sd.InputStream`

### Hotkey system
Hotkeys are stored as strings like `ctrl+alt+space` or `mouse_x1` or `ctrl+mouse_x1`.
- `parse_hotkey(str)` → `{mods: set, key: str|None, mouse: str|None}`
- PTT: two pynput listeners (keyboard + optional mouse)
- Recorder: separate pynput listeners active only while recording in Settings

### Build
- PyInstaller one-folder build (not one-file – faster startup)
- `build_exe.bat` uses absolute paths (`%~dp0venv\Scripts\python.exe`)
  to avoid venv breakage when folder is renamed
- `winrt` is optional – gracefully falls back if not installed

---

## File Structure

```
whisper-ptt/
├── whisper_ptt_gui.py     # ← main application (edit this)
├── whisper_ptt_gui.spec   # PyInstaller spec
├── build_exe.bat          # setup + build script
├── CLAUDE.md              # ← this file
├── CHANGELOG.md           # version history
├── README.md              # user-facing documentation
├── models/                # Whisper model cache (gitignored)
├── settings.json          # user config (gitignored)
└── dist/                  # build output (gitignored)
```

---

## Development Workflow

### Running locally
```bash
# One-time setup
python -m venv venv
venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui

# Run
python whisper_ptt_gui.py
```

### Building the .exe
```bat
build_exe.bat
```

### Testing without GPU
```bash
# Set device to CPU in settings.json before running:
# "device": "cpu", "compute_type": "int8"
python whisper_ptt_gui.py
```

---

## Coding Conventions

- **Python 3.10+** – use match/case, `|` union types where appropriate
- **No external UI framework** – tkinter only, no PyQt/wx
- **Single file** – keep everything in `whisper_ptt_gui.py`
- **Error handling:** all background threads must catch exceptions and log
  via `_log()` or push to `ui_queue`; never let a thread crash silently
- **Imports:** stdlib first, then third-party, then local (none currently)
- **Constants in CAPS:** `DEFAULTS`, `TRANSLATIONS`, `MODELS`, `C` (colors), etc.
- **Private methods** prefixed with `_`

### Adding a new setting

1. Add key + default to `DEFAULTS`
2. Add entry to `TRANSLATIONS` if the label needs i18n
3. Add widget in the appropriate `_tab_*()` method of `SettingsWindow`
4. Load in `_load_values()`
5. Save in `_save()`
6. Wire up behavior in the relevant function
7. Document in `CHANGELOG.md`

### Adding a new UI language

1. Add the language code + label to `UI_LANGUAGES`
2. Add translations for **every key** in `TRANSLATIONS`
3. Add the language to `_recog_lang_labels()` with all recognition language labels
4. Test: set `"ui_lang": "<code>"` in `settings.json` and restart

---

## Known Issues / Limitations

- UI language change requires a restart (tkinter widgets are not rebuilt live)
- `winrt` package may not be installable on all Python versions – gracefully ignored
- Mouse listener captures all mouse clicks during PTT (pynput limitation)
- `pyautogui.write()` (direct typing mode) is slow for long texts and does not
  handle special characters well on non-US keyboard layouts → prefer clipboard mode
- Translation (`output_language = "en"`) only works with Whisper's native `task="translate"`,
  which supports English as the sole target language; other target languages are not yet
  supported without an external translation library

---

## Version

Current version: **0.6.0**
Version constant in code: `VERSION = "0.6.0"` (top of `whisper_ptt_gui.py`)

Versioning scheme: `MAJOR.MINOR.PATCH`
- **MAJOR** – breaking changes (config format, complete rewrites)
- **MINOR** – new features (new settings, new languages, new UI panels)
- **PATCH** – bug fixes, small improvements

When releasing a new version:
1. Bump `VERSION` in `whisper_ptt_gui.py`
2. Add entry to `CHANGELOG.md`
3. Tag the git commit: `git tag v0.6.0`
