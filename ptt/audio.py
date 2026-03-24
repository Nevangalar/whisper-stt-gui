"""
ptt/audio.py – Microphone input, recording control, and stream management.
"""

import os
import sys
import time
import contextlib

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
    # NOTE: audio_chunks.append() is not guarded by record_lock here because
    # PortAudio callbacks must be non-blocking. CPython's GIL makes list.append()
    # effectively atomic, so this is safe in practice on CPython.
    data = np.clip(indata, -1.0, 1.0)  # guard against out-of-range values from some ALSA devices
    state.current_volume = min(float(np.sqrt(np.mean(data ** 2))) * 8.0, 1.0)
    if status:
        state.ui_queue.put(("mic_stream_error", str(status)))
    if state.recording:
        state.audio_chunks.append(data.copy())

# ─── Recording control ─────────────────────────────────────────────────────────

def start_recording():
    with state.record_lock:
        state.audio_chunks.clear(); state.recording = True
    state.ui_queue.put(("status", "record", T("recording")))
    if state.cfg["sound_feedback"]: _beep(660, 0.08)

def stop_recording():
    with state.record_lock:
        state.recording = False
    state.ui_queue.put(("status", "process", T("processing")))
    if state.cfg["sound_feedback"]: _beep(880, 0.10)

# ─── Windows mic permission ────────────────────────────────────────────────────

def request_windows_mic_permission():
    import sys
    if sys.platform != "win32":
        return False  # Windows-only; skip silently on Linux/macOS
    state.log("🔑 Requesting microphone permission...")
    try:
        import winrt.windows.media.capture as wmc
        import asyncio
        async def _req():
            cap = wmc.MediaCapture()
            s   = wmc.MediaCaptureInitializationSettings()
            try:
                s.stream_type = wmc.StreamingCaptureMode.AUDIO
            except AttributeError:
                pass  # older winrt API does not have stream_type
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
        os.startfile("ms-settings:privacy-microphone")
        state.log("ℹ️  Windows mic settings opened.")
        state.ui_queue.put(("mic_permission_dialog", None))
    except Exception:
        pass
    return False

# ─── Stream lifecycle ──────────────────────────────────────────────────────────

@contextlib.contextmanager
def _suppress_alsa_errors():
    """Redirect C-level stderr to /dev/null to silence PortAudio/ALSA noise."""
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stderr  = os.dup(2)
        os.dup2(devnull_fd, 2)
        os.close(devnull_fd)
        try:
            yield
        finally:
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
    except Exception:
        yield  # if fd ops fail just run without suppression

def _open_input_stream(device, samplerate=16000, suppress_errors=False):
    """Open an sd.InputStream and start it. Raises on failure."""
    ctx = _suppress_alsa_errors() if suppress_errors else contextlib.nullcontext()
    with ctx:
        stream = sd.InputStream(
            samplerate=samplerate, channels=1, dtype="float32",
            callback=audio_callback, blocksize=512,
            device=device,
        )
        stream.start()
    return stream

def start_audio_stream() -> bool:
    if state._audio_stream is not None:
        try: state._audio_stream.stop(); state._audio_stream.close()
        except Exception: pass
        state._audio_stream = None

    device = state.cfg.get("mic_device", -1)
    if device == -1:
        device = None  # let sounddevice use the OS default

    # Try requested device first; if ALSA rejects 16 kHz, fall back to system default.
    attempts = [(device, 16000)]
    if device is not None:
        attempts.append((None, 16000))   # system default always supports resampling

    last_err = None
    for i, (dev, rate) in enumerate(attempts):
        is_fallback = (i > 0)
        try:
            # Suppress C-level ALSA noise for non-final attempts that we expect may fail
            state._audio_stream = _open_input_stream(dev, rate, suppress_errors=not is_fallback and len(attempts) > 1)
            if is_fallback:
                state.log(f"⚠️  Selected mic unsupported at {rate} Hz – using system default.")
            state._silent_count = 0; state.MIC_OK = True
            state.log("✅ Audio stream started.")
            state.ui_queue.put(("mic_ok", None))
            return True
        except Exception as e:
            last_err = e

    state.MIC_OK = False
    state.log(f"❌ Audio stream error: {last_err}")
    state.ui_queue.put(("mic_error", str(last_err)))
    return False

def restart_audio_stream():
    state.log("🔄 Restarting microphone...")
    request_windows_mic_permission()
    time.sleep(0.5)
    if start_audio_stream():
        state.ui_queue.put(("status", "ready", T("ready")))
    else:
        state.ui_queue.put(("status", "error", T("mic_error")))
