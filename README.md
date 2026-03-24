# 🎤 Whisper PTT

**Push-to-talk speech recognition with a local Whisper model – always-on-top overlay for Windows and Linux**

Hold a hotkey (or a mouse button), speak, release – the recognized text is automatically pasted into whatever window is currently active. Runs entirely **locally** on your GPU, NPU, or CPU with no cloud API, no internet connection required, and no data leaving your machine.

![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue)
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
- **Microphone device selection** – choose which microphone to use (auto-detects all input devices)
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
- **First-time setup** – dialog on first launch to choose models directory (default, browse, or create new)
- Reset all settings to defaults
- All settings are saved persistently in `settings.json`

---

## 📋 Requirements

### Windows
- **Windows 10 / 11** (64-bit)
- **Python 3.10 or newer** → [python.org](https://www.python.org/downloads/)
- **NVIDIA GPU** with CUDA support (recommended) **or** Intel NPU **or** CPU only
- A working microphone

### Linux
- **Ubuntu 22.04 / 24.04** or any modern distro with PipeWire or PulseAudio
- **Python 3.10 or newer**
- **Wayland or X11** (both supported)
- A working microphone
- System packages: `sudo apt install portaudio19-dev wtype wl-clipboard ydotool`

---

## 🚀 Installation

### Windows

#### 1. Clone the repository

```bash
git clone https://github.com/Nevangalar/whisper-stt-gui.git
cd whisper-stt-gui
```

#### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Install dependencies

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

#### 4. Run

```bash
python whisper_ptt_gui.py
```

---

### Linux (Wayland / X11)

#### 1. Clone the repository

```bash
git clone https://github.com/Nevangalar/whisper-stt-gui.git
cd whisper-stt-gui
```

#### 2. Install system packages

```bash
sudo apt install portaudio19-dev wl-clipboard wtype ydotool
```

#### 3. Add yourself to the `input` group (required for Wayland hotkeys)

```bash
sudo usermod -aG input $USER
```

> ⚠️ **You must fully log out of your desktop session and log back in** (not just close terminals) for the group change to take effect. Verify with `groups` – `input` must appear in the list.

#### 4. Create a virtual environment and install dependencies

**NVIDIA GPU (CUDA):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui evdev
```

**CPU only:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui evdev
```

#### 5. Run

```bash
source venv/bin/activate
python3 whisper_ptt_gui.py
```

#### Linux notes

| Feature | How it works on Linux |
|---|---|
| **Hotkey (Wayland)** | `evdev` reads `/dev/input/event*` directly – requires `input` group |
| **Hotkey (X11)** | `pynput` as on Windows |
| **Default hotkey** | `ctrl+space` (avoids compositor grab of `ctrl+alt` combos) |
| **Auto-paste (GNOME Wayland)** | `ydotool type` via `/dev/uinput` |
| **Auto-paste (KDE/wlroots)** | `wtype` |
| **Auto-paste (X11)** | `pyautogui` as on Windows |
| **Clipboard** | `wl-copy` on Wayland, tkinter + pyperclip on X11 |

> **Note:** On first launch, the Whisper model (~150 MB for `base`) will be downloaded automatically and cached in the `models/` folder. After that, everything runs offline.

---

## 📦 Build as .exe (optional)

To create a standalone executable that runs without a Python installation:

```bash
build_exe.bat
```

That's it! The script will:
1. Create a virtual environment (if needed)
2. Install all dependencies
3. Check your hardware (GPU/NPU)
4. Build the executable with PyInstaller

The finished application will be located at `dist\WhisperPTT\WhisperPTT.exe`.

> ⚠️ **Copy the entire `dist\WhisperPTT\` folder** – not just the `.exe`. The application requires the DLLs and data files alongside it. 
> 
> **First Launch:** On first launch, you'll see a setup dialog to choose where to store models (default `models/` folder, or browse/create a custom path). After setup, the `settings.json` will be created automatically next to the `.exe`.

### Why the whole folder?
- `WhisperPTT.exe` – the application launcher
- `_internal/` – bundled Python, libraries, and DLLs
- `models/` – where Whisper models are cached (created on first run)
- `settings.json` – your configuration (created on first launch)

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
| `mic_device` | `-1`, `0`, `1`, ... | Microphone device index (`-1` = system default) |
| `models_dir` | path string | Directory to cache Whisper models (empty = `models/` next to executable) |
| `ui_lang` | `en`, `de`, `fr`, `es` | Interface language |
| `sound_feedback` | `true` / `false` | Audio beep on start/stop |
| `window_x`, `window_y` | pixel coordinates | Window position (auto-saved) |

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

### Python packages

| Package | Platform | Purpose |
|---|---|---|
| `faster-whisper` | all | Local Whisper transcription (CTranslate2) |
| `torch` | all | PyTorch (CUDA backend for GPU acceleration) |
| `sounddevice` | all | Microphone recording |
| `soundfile` | all | WAV file writing / reading |
| `numpy` | all | Audio data processing |
| `pynput` | all | Global hotkeys (X11 / Windows); mouse button support |
| `pyperclip` | all | Clipboard access fallback |
| `pyautogui` | all | Keyboard simulation on X11 / Windows |
| `evdev` | Linux only | Raw kernel input events for Wayland hotkeys |
| `tkinter` | all | GUI (included in Python standard library) |

### System packages (Linux)

| Package | Purpose |
|---|---|
| `portaudio19-dev` | PortAudio headers (required by `sounddevice`) |
| `wl-clipboard` (`wl-copy`) | Wayland clipboard management |
| `ydotool` | Simulate keystrokes via `/dev/uinput` on GNOME Wayland |
| `wtype` | Simulate keystrokes on KDE / wlroots Wayland |

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
Check the default recording device in Windows Sound Settings / PipeWire/PulseAudio settings on Linux.

**Model doesn't download / setup hangs:**
On first launch, you'll see a setup dialog. If it doesn't appear or the dialog gets stuck:
1. Check your internet connection
2. Make sure `settings.json` doesn't exist yet (or delete it to reset)
3. If behind a corporate proxy, set the environment variable:
```bash
# Windows
set HTTPS_PROXY=http://proxy.company.com:8080
# Linux
export HTTPS_PROXY=http://proxy.company.com:8080
python whisper_ptt_gui.py
```

**Model download fails on first start:**
An internet connection (~150 MB) is required for the initial model download. After that the app runs fully offline.

**Auto-paste doesn't work in certain applications:**
Switch the paste mode to `Direct typing` in the Settings menu.

**[Linux] Hotkey not working on Wayland:**
The app uses `evdev` to read keyboard events directly. Make sure:
1. You are in the `input` group: `groups` must list `input`
2. If not: `sudo usermod -aG input $USER` then **fully log out of your desktop and log back in**
3. `evdev` is installed: `pip install evdev`

**[Linux] Auto-paste not working on GNOME Wayland:**
GNOME does not support the virtual keyboard protocol used by `wtype`. Install `ydotool` instead:
```bash
sudo apt install ydotool
```
The app will use `ydotool type` automatically on GNOME Wayland.

**[Linux] ALSA errors at startup:**
```
Expression 'PaAlsaStream_Configure...' failed
```
These are harmless. The app automatically falls back to the system default audio device.
If audio still doesn't work: `sudo apt install portaudio19-dev` and reinstall `sounddevice`.

---

## 📄 License

MIT License – see [LICENSE](LICENSE)

---

## 🙏 Credits

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) – Optimized Whisper implementation via CTranslate2
- [OpenAI Whisper](https://github.com/openai/whisper) – Original speech recognition model by OpenAI
- [pynput](https://github.com/moses-palmer/pynput) – Cross-platform input control library
