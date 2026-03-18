"""
ptt/transcribe.py – Speech-to-text transcription and paste logic.
"""

import os
import time
import tempfile
import threading

import numpy as np
import soundfile as sf
import pyperclip
import pyautogui

import ptt.state as state
from ptt.constants import SILENT_THRESHOLD
from ptt.config import T

# ─── Paste ─────────────────────────────────────────────────────────────────────

def _do_paste(text: str):
    time.sleep(0.15)
    if state.cfg["paste_mode"] == "clipboard":
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.01)

# ─── Transcription ─────────────────────────────────────────────────────────────

def transcribe_and_paste():
    from ptt.audio import restart_audio_stream

    with state.record_lock:
        chunks = list(state.audio_chunks)
    if not chunks:
        state.ui_queue.put(("status", "ready", T("ready"))); return

    audio_data = np.concatenate(chunks, axis=0).flatten().astype(np.float32)

    if float(np.max(np.abs(audio_data))) < 0.001:
        state._silent_count += 1
        state.log(f"⚠️  {T('log_no_signal')} ({state._silent_count}/{SILENT_THRESHOLD})")
        if state._silent_count >= SILENT_THRESHOLD:
            state._silent_count = 0
            state.log(T("log_restarting"))
            state.ui_queue.put(("status", "error", T("mic_error")))
            threading.Thread(target=restart_audio_stream, daemon=True).start()
        state.ui_queue.put(("status", "ready", T("ready"))); return
    else:
        state._silent_count = 0

    if len(audio_data) / 16000 < 0.3:
        state.ui_queue.put(("status", "ready", T("ready")))
        state.log(T("log_too_short")); return

    t0       = time.time()
    in_lang  = state.cfg["language"] or None
    out_lang = state.cfg.get("output_language", "same")
    task     = "translate" if (out_lang == "en" and in_lang != "en") else "transcribe"
    if task == "translate":
        state.log("🌐 Translation mode: → English")

    try:
        if state.openvino_pipe is not None:
            # ── OpenVINO GenAI (NPU) ──────────────────────────────────────────
            config = state.openvino_pipe.get_generation_config()
            if in_lang:
                config.language = f"<|{in_lang}|>"
            if task == "translate":
                config.task = "translate"
            result = state.openvino_pipe.generate(audio_data, config)
            text   = " ".join(t.strip() for t in result.texts).strip()
        else:
            # ── faster-whisper (CPU / CUDA) ───────────────────────────────────
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            sf.write(tmp_path, audio_data, 16000)
            try:
                seg, _ = state.whisper_model.transcribe(
                    tmp_path,
                    language=in_lang, task=task,
                    beam_size=state.cfg["beam_size"],
                    vad_filter=state.cfg["vad_filter"],
                    vad_parameters=dict(min_silence_duration_ms=state.cfg["vad_silence_ms"]),
                    condition_on_previous_text=False,
                )
                text = " ".join(s.text.strip() for s in seg).strip()
            finally:
                try: os.unlink(tmp_path)
                except Exception: pass

        elapsed = time.time() - t0
        if not text:
            state.log(T("log_no_text"))
            state.ui_queue.put(("status", "ready", T("ready"))); return

        state.ui_queue.put(("recognized", text))
        state.ui_queue.put(("status", "ready", f"{T('ready')}  ({elapsed:.1f}s)"))
        _do_paste(text)
    except Exception as e:
        state.log(f"❌ Error: {e}")
        state.ui_queue.put(("status", "ready", T("ready")))
