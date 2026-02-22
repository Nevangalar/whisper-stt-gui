# 🎤 Whisper PTT

**Push-to-talk speech recognition with a local Whisper model – always-on-top overlay for Windows**

Hold a hotkey (or a mouse button), speak, release – the recognized text is automatically pasted into whatever window is currently active. Runs entirely **locally** on your GPU, NPU, or CPU with no cloud API, no internet connection required, and no data leaving your machine.

![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### Core functionality
- **Push-to-talk** – hold hotkey to record, release to transcribe and auto-paste into the active window
- **Fully local** – no API key, no cloud, no cost, no data sharing
- **Fast** – powered by `faster-whisper` with CUDA, significantly faster than original Whisper

### Overlay UI
- Always-on-top, freely positionable window (position is saved across sessions)
- Collapsible to a minimal title bar when not in use
- Adjustable transparency (40–100 %)
- Drag to reposition by the title bar

### Status display
- **Color-coded status dot** with animation:
  - ⚫ Grey – Ready / Idle
  - 🔴 Red blinking – Recording
  - 🟠 Orange – Processing
  - 🟢 Green – Done (shows transcription time)
- **Real-time voice meter** – displays microphone level in color (green → orange → red)
- Optional audio beep on start / stop of recording

### Recognized text panel
- Dedicated text field showing **only the recognized text** – no timestamps
- Text can be freely selected and partially copied
- **📋 Copy** – copies selection or the last recognized text to the clipboard
- **📌 Paste** – manually pastes the last text into the active window (useful if auto-paste missed)
- **🗑️ Clear** – clears the text field

### Debug / Log panel
- Separate log panel with timestamps for system messages
- Shows loaded device, model, errors, and processing times
- Dedicated clear button

### Settings (⚙ button)
- **Hotkey recorder** – capture any key combination or mouse button:
  - Keyboard combos: `Ctrl+Alt+Space`, `F9`, `Shift+F12`, etc.
  - Mouse buttons: thumb back/forward (`mouse_x1` / `mouse_x2`), middle click, etc.
  - Modifier + mouse button: `Ctrl+mouse_x1`, etc.
- **Recognition language (input)**: German, English, French, Spanish, Italian, Dutch, Polish, Russian, Chinese, Japanese, Turkish, Auto-detect
- **Output language / translation**: speak in any language and receive English text — powered by Whisper's built-in translation, fully local, no API required
- **Paste mode**: Clipboard (Ctrl+V) or direct typing
- **Device selection** with live hardware detection:
  - NVIDIA CUDA
  - Intel NPU / AMD DirectML
  - CPU fallback
- **Whisper model**: tiny / base / small / medium / large-v2 / large-v3
- **Compute type**: Auto / float16 / int8 / float32
- **Voice Activity Detection (VAD)** – ignores silence, configurable threshold
- **Beam size** – quality vs. speed trade-off (1–10)
- Reset all settings to defaults
- All settings are saved persistently in `settings.json`

---

## 📋 Requirements

- **Windows 10 / 11** (64-bit)
- **Python 3.10 or newer** → [python.org](https://www.python.org/downloads/)
- **NVIDIA GPU** with CUDA support (recommended) **or** Intel NPU **or** CPU only
- A working microphone

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/whisper-ptt.git
cd whisper-ptt
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

**NVIDIA GPU (CUDA 12.1):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui
```

**CPU only (no GPU):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui
```

**Intel NPU (OpenVINO):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui openvino
```

> **Note:** On first launch, the Whisper model (~150 MB for `base`) will be downloaded automatically and cached in the `models/` folder. After that, everything runs offline.

### 4. Run

```bash
python whisper_ptt_gui.py
```

---

## 📦 Build as .exe (optional)

To create a standalone executable that runs without a Python installation:

```bash
pip install pyinstaller
```

```bash
build_exe.bat
```

The finished application will be located at `dist\WhisperPTT\WhisperPTT.exe`.

> ⚠️ **Copy the entire `dist\WhisperPTT\` folder** – not just the `.exe`. The application requires the DLLs and data files alongside it. The `settings.json` will be created automatically next to the `.exe` on first launch.

---

## 📁 Project structure

```
whisper-ptt/
├── whisper_ptt_gui.py       # Main application
├── whisper_ptt_gui.spec     # PyInstaller build configuration
├── build_exe.bat            # Automated setup + build script
├── models/                  # Whisper models (auto-downloaded on first run)
├── settings.json            # Saved settings (created automatically)
└── README.md
```

---

## ⚙️ Configuration

All settings are configured via the ⚙ menu in the overlay and saved automatically to `settings.json`. The file can also be edited manually:

```json
{
  "hotkey": "ctrl+alt+space",
  "language": "de",
  "output_language": "same",
  "model": "base",
  "device": "auto",
  "compute_type": "auto",
  "paste_mode": "clipboard",
  "vad_filter": true,
  "vad_silence_ms": 300,
  "sound_feedback": true,
  "opacity": 0.95,
  "beam_size": 5,
  "window_x": -1,
  "window_y": -1
}
```

| Parameter | Values | Description |
|---|---|---|
| `hotkey` | e.g. `ctrl+alt+space`, `mouse_x1` | Recording hotkey |
| `language` | `de`, `en`, `fr`, ... , `null` | Recognition / input language (`null` = auto-detect) |
| `output_language` | `same`, `en` | Output language: `same` = no translation, `en` = translate to English |
| `model` | `tiny` `base` `small` `medium` `large-v2` `large-v3` | Whisper model |
| `device` | `auto` `cuda` `dml` `cpu` | Compute device |
| `compute_type` | `auto` `float16` `int8` `float32` | Compute type |
| `paste_mode` | `clipboard` `type` | How text is inserted |
| `vad_filter` | `true` / `false` | Voice Activity Detection |
| `vad_silence_ms` | `100`–`2000` | Silence threshold in ms |
| `beam_size` | `1`–`10` | Quality vs. speed |
| `opacity` | `0.4`–`1.0` | Window transparency |

---

## 🖥️ Model recommendations

| Model | Size | VRAM | Speed | Use case |
|---|---|---|---|---|
| `tiny` | ~75 MB | < 1 GB | Very fast | Simple dictation, maximum speed |
| `base` | ~150 MB | ~1 GB | Fast | **Best for everyday use** ⭐ |
| `small` | ~500 MB | ~2 GB | Medium | Better accuracy, technical terms |
| `medium` | ~1.5 GB | ~5 GB | Slow | High accuracy |
| `large-v3` | ~3 GB | ~10 GB | Very slow | Maximum accuracy |

---

## 🔧 Dependencies

| Package | Purpose |
|---|---|
| `faster-whisper` | Local Whisper transcription (optimized via CTranslate2) |
| `torch` | PyTorch (CUDA backend for GPU acceleration) |
| `sounddevice` | Microphone recording |
| `soundfile` | WAV file writing / reading |
| `numpy` | Audio data processing |
| `pynput` | Global hotkeys including mouse button support |
| `pyperclip` | Clipboard access |
| `pyautogui` | Keyboard simulation (Ctrl+V) |
| `tkinter` | GUI (included in Python standard library) |

---

## ❓ Troubleshooting

**CUDA not detected:**
```bash
python -c "import torch; print(torch.cuda.is_available())"
```
If `False`: check your CUDA version with `nvidia-smi` and install the matching PyTorch build → [pytorch.org](https://pytorch.org/get-started/locally/)

**No microphone / audio device not found:**
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Check the default recording device in Windows Sound Settings.

**Model download fails on first start:**
An internet connection (~150 MB) is required for the initial model download. After that the app runs fully offline. If you're behind a corporate proxy, set the environment variable before launching:
```bash
set HTTPS_PROXY=http://proxy.company.com:8080
python whisper_ptt_gui.py
```

**Auto-paste doesn't work in certain applications:**
Switch the paste mode to `Direct typing` in the Settings menu.

**Settings window doesn't open a second time:**
This was a known bug fixed in v3. Make sure you're running the latest version.

---

## 📄 License

MIT License – see [LICENSE](LICENSE)

---

## 🙏 Credits

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) – Optimized Whisper implementation via CTranslate2
- [OpenAI Whisper](https://github.com/openai/whisper) – Original speech recognition model by OpenAI
- [pynput](https://github.com/moses-palmer/pynput) – Cross-platform input control library
