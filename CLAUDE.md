# CLAUDE.md – Whisper PTT

Instructions for Claude Code when working on this project.
Read this file before making any changes.

---

## Project Overview

**Whisper PTT** is a Windows desktop push-to-talk overlay that transcribes speech
locally using OpenAI Whisper (via `faster-whisper`) and pastes the result into
whatever window is currently active.

- **Entry point:** `whisper_ptt_gui.py` – thin launcher (~35 lines), imports `ptt/`
- **Package:** `ptt/` – all application logic, split into 11 modules
- **Build:** `build_exe.bat` → PyInstaller → `dist/WhisperPTT/WhisperPTT.exe`
- **Config:** `settings.json` next to the `.exe` (auto-created on first run)
- **Models:** `models/` directory (auto-downloaded on first run)

---

## Architecture

```
main()  [whisper_ptt_gui.py]
 ├── config.load_settings()       # reads settings.json → state.cfg
 ├── WhisperPTTApp(root)          # main overlay window (tkinter)
 │    ├── _build_ui()             # always-on-top frameless window
 │    ├── _poll_queue()           # 50ms loop: reads state.ui_queue → updates widgets
 │    └── SettingsWindow          # modal settings dialog (ttk.Notebook, 3 tabs)
 ├── audio.start_audio_stream()   # sd.InputStream with audio_callback
 └── hotkey.start_ptt_listener()  # pynput keyboard + mouse global listeners
      ├── _ptt_trigger_press()    → audio.start_recording()
      └── _ptt_trigger_release()  → audio.stop_recording()
                                  → Thread: transcribe.transcribe_and_paste()
                                       └── state.whisper_model.transcribe()
                                       └── transcribe._do_paste()
```

### Module overview

```
ptt/
├── constants.py      ← VERSION, DEFAULTS, C, TRANSLATIONS, MODELS, DEVICES, …
├── state.py          ← global runtime vars (cfg, recording, whisper_model, …) + log()
├── config.py         ← T(), load_settings(), save_settings(), get_models_dir()
├── hardware.py       ← detect_devices(), resolve_device()
├── model_manager.py  ← load_model(), _ov_model_dir(), _download_ov_model()
├── audio.py          ← audio_callback, start/stop_recording, _beep,
│                        request_windows_mic_permission, start/restart_audio_stream
├── hotkey.py         ← parse_hotkey(), start/stop_ptt_listener(), trigger funcs
├── transcribe.py     ← transcribe_and_paste(), _do_paste()
└── ui/
    ├── helpers.py    ← _lighten, _section, _flat_btn, _make_text_widget, _scrollable_tab
    ├── settings.py   ← class SettingsWindow
    └── app.py        ← class WhisperPTTApp
```

### Import order (no circular imports)

```
constants.py      ← no local imports
state.py          ← no local imports
config.py         ← constants, state
hardware.py       ← (no local imports)
model_manager.py  ← constants, state, config, hardware
audio.py          ← constants, state, config
hotkey.py         ← constants, state  (+ audio/transcribe via deferred imports)
transcribe.py     ← constants, state, config  (+ audio via deferred import)
ui/helpers.py     ← constants, config
ui/settings.py    ← constants, state, config, hardware, ui/helpers
ui/app.py         ← constants, state, config, audio, hotkey, model_manager, ui/*
whisper_ptt_gui.py← state, config, audio, ui/app
```

### Thread model

| Thread | Purpose |
|--------|---------|
| Main (tkinter) | UI event loop |
| `audio_callback` | sounddevice PortAudio callback – appends to `state.audio_chunks` |
| `_ptt_kb_listener` | pynput keyboard global listener |
| `_ptt_ms_listener` | pynput mouse global listener (only when hotkey uses mouse) |
| `load_model` | loads faster-whisper model on startup / settings change |
| `transcribe_and_paste` | runs after each PTT release |
| `start_audio_stream` | mic init + Windows permission request |

**Thread-safety:** All UI updates go through `state.ui_queue` (stdlib `queue.Queue`).
Never update tkinter widgets from a non-main thread directly.

### Global state

All runtime variables live in `ptt/state.py`. Other modules access them as:

```python
import ptt.state as state
state.cfg              # dict – current settings (mirrors settings.json)
state.whisper_model    # WhisperModel instance (None until loaded)
state.recording        # bool – True while PTT is held
state.audio_chunks     # list of np.ndarray – accumulated during recording
state.current_volume   # float 0.0–1.0 – updated in audio_callback
state._audio_stream    # sd.InputStream instance
state._ptt_active      # bool – True while hotkey is physically held
state._silent_count    # int – counts consecutive silent recordings (mic watchdog)
```

---

## Key Design Decisions

### Translations / i18n
All UI strings go through `T(key)` (`ptt/config.py`) which looks up
`TRANSLATIONS[key][state.cfg["ui_lang"]]`.
- Supported UI languages: `en` (default), `de`, `fr`, `es`
- `cfg["ui_lang"]` = interface language code
- `cfg["language"]` = Whisper recognition / input language code (separate setting)
- `cfg["output_language"]` = `"same"` (transcribe only) or `"en"` (translate to English)
- **When adding new UI strings:** add the key to `TRANSLATIONS` in `ptt/constants.py`
  with all 4 languages.
- Recognition language labels are generated dynamically by `_recog_lang_labels(ui)`
  in `ptt/constants.py`.

### Settings persistence
- `state.cfg` is the single source of truth (global dict in `ptt/state.py`).
- `config.load_settings()` merges `settings.json` over `DEFAULTS` at startup.
- `config.save_settings()` writes `state.cfg` to `settings.json`.
- `DEFAULTS` in `ptt/constants.py` defines every key with a safe fallback value.
- **When adding a new setting:** add it to `DEFAULTS`, handle it in `_load_values()`,
  `_save()`, and wire up the widget in the appropriate tab.

### Mic Watchdog
After `SILENT_THRESHOLD` (=3) consecutive silent recordings:
1. `audio.restart_audio_stream()` is called in a background thread
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
- The `ptt/` package is discovered automatically by PyInstaller's import analysis

---

## File Structure

```
whisper-stt-gui/
├── whisper_ptt_gui.py     # ← thin entry point (~35 lines)
├── ptt/                   # ← application package (edit modules here)
│   ├── __init__.py
│   ├── constants.py
│   ├── state.py
│   ├── config.py
│   ├── hardware.py
│   ├── model_manager.py
│   ├── audio.py
│   ├── hotkey.py
│   ├── transcribe.py
│   └── ui/
│       ├── __init__.py
│       ├── helpers.py
│       ├── settings.py
│       └── app.py
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
- **Package structure** – one concern per module; keep `whisper_ptt_gui.py` as a
  thin launcher only
- **Error handling:** all background threads must catch exceptions and log
  via `state.log()` or push to `state.ui_queue`; never let a thread crash silently
- **Imports:** stdlib first, then third-party, then local (`ptt.*`)
- **Constants in CAPS:** `DEFAULTS`, `TRANSLATIONS`, `MODELS`, `C` (colors), etc.
  All in `ptt/constants.py`
- **Private functions/methods** prefixed with `_`
- **State access:** always `import ptt.state as state` and use `state.cfg`,
  `state.recording`, etc. – never copy references into local module globals

### Adding a new setting

1. Add key + default to `DEFAULTS` in `ptt/constants.py`
2. Add entry to `TRANSLATIONS` in `ptt/constants.py` if the label needs i18n
3. Add widget in the appropriate `_tab_*()` method of `SettingsWindow`
   in `ptt/ui/settings.py`
4. Load in `_load_values()`
5. Save in `_save()`
6. Wire up behavior in the relevant module
7. Document in `CHANGELOG.md`

### Adding a new UI language

1. Add the language code + label to `UI_LANGUAGES` in `ptt/constants.py`
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

Current version: **0.7.0**
Version constant in code: `VERSION = "0.7.0"` (`ptt/constants.py`)

Versioning scheme: `MAJOR.MINOR.PATCH`
- **MAJOR** – breaking changes (config format, complete rewrites)
- **MINOR** – new features (new settings, new languages, new UI panels)
- **PATCH** – bug fixes, small improvements

When releasing a new version:
1. Bump `VERSION` in `ptt/constants.py`
2. Add entry to `CHANGELOG.md`
3. Tag the git commit: `git tag v0.7.0`
