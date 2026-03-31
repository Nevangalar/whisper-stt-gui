"""Shared pytest fixtures for Whisper PTT unit tests."""
import sys
import types
import queue
import threading
import pytest

@pytest.fixture(autouse=True)
def mock_ptt_state(monkeypatch):
    """
    Provide a minimal ptt.state stub so unit tests never import
    sounddevice, tkinter, pynput, or faster-whisper.
    """
    state_mod = types.ModuleType("ptt.state")
    state_mod.cfg = {
        "ui_lang": "en",
        "language": None,
        "output_language": "same",
        "paste_mode": "clipboard",
        "sound_feedback": False,
        "hotkey": "ctrl+alt+space",
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "opacity": 1.0,
        "window_x": -1,
        "window_y": -1,
        "mic_device": -1,
        "beam_size": 5,
        "vad_filter": True,
        "vad_silence_ms": 500,
        "models_dir": "",
    }
    state_mod.recording = False
    state_mod.audio_chunks = []
    state_mod.current_volume = 0.0
    state_mod.whisper_model = None
    state_mod.openvino_pipe = None
    state_mod.ui_queue = queue.Queue()
    state_mod.MIC_OK = True
    state_mod._ptt_active = False
    state_mod._silent_count = 0
    state_mod._audio_stream = None
    state_mod._ptt_kb_listener = None
    state_mod._ptt_ms_listener = None

    state_mod.record_lock = threading.Lock()
    state_mod.model_load_lock = threading.Lock()
    state_mod.ptt_lock = threading.Lock()

    def _log(msg):
        state_mod.ui_queue.put(("log", msg))
    state_mod.log = _log

    # Stub heavy optional deps so imports don't fail
    for mod_name in [
        "sounddevice", "soundfile", "numpy", "pyperclip", "pyautogui",
        "pynput", "pynput.keyboard",
        "faster_whisper", "torch", "openvino",
    ]:
        if mod_name not in sys.modules:
            monkeypatch.setitem(sys.modules, mod_name, types.ModuleType(mod_name))
    # pynput.mouse needs a Button stub so hotkey.py can build MOUSE_BTN_NAMES at import
    ms_mod = types.ModuleType("pynput.mouse")
    ms_mod.Button = types.SimpleNamespace(
        left=object(), right=object(), middle=object()
    )
    if "pynput.mouse" not in sys.modules:
        monkeypatch.setitem(sys.modules, "pynput.mouse", ms_mod)

    monkeypatch.setitem(sys.modules, "ptt.state", state_mod)
    # Give ptt stub a __path__ so Python can locate ptt.* submodules on disk.
    import os as _os
    ptt_mod = types.ModuleType("ptt")
    ptt_mod.__path__ = [_os.path.join(_os.path.dirname(__file__), "..", "ptt")]
    ptt_mod.__package__ = "ptt"
    monkeypatch.setitem(sys.modules, "ptt", ptt_mod)
    return state_mod
