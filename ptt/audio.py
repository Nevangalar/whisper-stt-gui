"""
ptt/audio.py – Microphone input, recording control, and stream management.
"""

import time
import subprocess

import numpy as np
import sounddevice as sd

import ptt.state as state
from ptt.constants import SILENT_THRESHOLD
from ptt.config import T

# ─── Beep ──────────────────────────────────────────────────────────────────────

def _beep(freq=880, dur=0.08, vol=0.3):
    try:
        t    = np.linspace(0, dur, int(16000 * dur), False)
        wave = (np.sin(2 * np.pi * freq * t) * vol * 32767).astype(np.int16)
        sd.play(wave, 16000)
    except Exception:
        pass

# ─── Audio callback ────────────────────────────────────────────────────────────

def audio_callback(indata, frames, time_info, status):
    state.current_volume = min(float(np.sqrt(np.mean(indata ** 2))) * 8.0, 1.0)
    if status:
        state.ui_queue.put(("mic_stream_error", str(status)))
    if state.recording:
        state.audio_chunks.append(indata.copy())

# ─── Recording control ─────────────────────────────────────────────────────────

def start_recording():
    with state.record_lock:
        state.audio_chunks = []; state.recording = True
    state.ui_queue.put(("status", "record", T("recording")))
    if state.cfg["sound_feedback"]: _beep(660, 0.08)

def stop_recording():
    with state.record_lock:
        state.recording = False
    state.ui_queue.put(("status", "process", T("processing")))
    if state.cfg["sound_feedback"]: _beep(880, 0.10)

# ─── Windows mic permission ────────────────────────────────────────────────────

def request_windows_mic_permission():
    state.log("🔑 Requesting microphone permission...")
    try:
        import winrt.windows.media.capture as wmc
        import asyncio
        async def _req():
            cap = wmc.MediaCapture()
            s   = wmc.MediaCaptureInitializationSettings()
            s.stream_type = wmc.StreamingCaptureMode.AUDIO
            await cap.initialize_async(s)
            await cap.close_async()
        asyncio.run(_req())
        state.log("✅ Mic permission granted via winrt.")
        return True
    except ImportError:
        pass
    except Exception as e:
        state.log(f"⚠️  winrt failed: {e}")
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Value", 0, winreg.REG_SZ, "Allow")
        state.log("✅ Mic permission set via registry.")
        return True
    except Exception as e:
        state.log(f"⚠️  Registry fix failed: {e}")
    try:
        subprocess.Popen(["ms-settings:privacy-microphone"],
                         shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        state.log("ℹ️  Windows mic settings opened.")
        state.ui_queue.put(("mic_permission_dialog", None))
    except Exception:
        pass
    return False

# ─── Stream lifecycle ──────────────────────────────────────────────────────────

def start_audio_stream() -> bool:
    if state._audio_stream is not None:
        try: state._audio_stream.stop(); state._audio_stream.close()
        except Exception: pass
        state._audio_stream = None
    try:
        device = state.cfg.get("mic_device", -1)
        # -1 means default device
        if device == -1:
            device = None
        state._audio_stream = sd.InputStream(
            samplerate=16000, channels=1, dtype="float32",
            callback=audio_callback, blocksize=512,
            device=device,
        )
        state._audio_stream.start()
        state._silent_count = 0; state.MIC_OK = True
        state.log("✅ Audio stream started.")
        state.ui_queue.put(("mic_ok", None))
        return True
    except Exception as e:
        state.MIC_OK = False
        state.log(f"❌ Audio stream error: {e}")
        state.ui_queue.put(("mic_error", str(e)))
        return False

def restart_audio_stream():
    state.log("🔄 Restarting microphone...")
    request_windows_mic_permission()
    time.sleep(0.5)
    if start_audio_stream():
        state.ui_queue.put(("status", "ready", T("ready")))
    else:
        state.ui_queue.put(("status", "error", T("mic_error")))
