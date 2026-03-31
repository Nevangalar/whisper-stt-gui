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
        "pynput", "pynput.keyboard", "pynput.mouse",
        "faster_whisper", "torch", "openvino",
    ]:
        if mod_name not in sys.modules:
            monkeypatch.setitem(sys.modules, mod_name, types.ModuleType(mod_name))

    monkeypatch.setitem(sys.modules, "ptt.state", state_mod)
    # ptt parent is an empty stub; tests import submodules (ptt.config etc.) directly via patch()
    monkeypatch.setitem(sys.modules, "ptt", types.ModuleType("ptt"))
    return state_mod
