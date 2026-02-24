"""
ptt/state.py – Global runtime variables shared across all modules.

Other modules do ``import ptt.state as state`` and access e.g. ``state.cfg``,
``state.recording``, ``state.whisper_model``, etc.
"""

import threading
import queue

# ─── Recording state ───────────────────────────────────────────────────────────

recording    = False
audio_chunks = []
record_lock  = threading.Lock()

# ─── Model handles ─────────────────────────────────────────────────────────────

whisper_model  = None   # faster_whisper.WhisperModel  (CPU / CUDA)
openvino_pipe  = None   # openvino_genai.WhisperPipeline (NPU)

# ─── Audio / UI state ──────────────────────────────────────────────────────────

current_volume = 0.0
ui_queue       = queue.Queue()
cfg            = {}     # populated by config.load_settings()

# ─── PTT listener handles ──────────────────────────────────────────────────────

_ptt_kb_listener = None
_ptt_ms_listener = None
_ptt_active      = False

# ─── Mic watchdog ──────────────────────────────────────────────────────────────

_silent_count = 0
MIC_OK        = True
_audio_stream = None   # sd.InputStream instance

# ─── Logging helper ────────────────────────────────────────────────────────────

def log(msg: str):
    """Thread-safe log: push message to ui_queue for display in the main thread."""
    ui_queue.put(("log", msg))
