"""
ptt/model_manager.py – Whisper model loading (faster-whisper + OpenVINO GenAI).
"""

import ptt.state as state
from ptt.constants import MODELS_OV
from ptt.config import T, get_models_dir
from ptt.hardware import resolve_device

# ─── OpenVINO model helpers ────────────────────────────────────────────────────

def _ov_model_dir(model_name: str):
    return get_models_dir() / f"{model_name}-ov"

def _download_ov_model(model_name: str, status_cb=None):
    """Download pre-converted OpenVINO Whisper model from HuggingFace if needed."""
    repo_id   = MODELS_OV.get(model_name, f"OpenVINO/whisper-{model_name}-fp16-ov")
    local_dir = _ov_model_dir(model_name)
    if not local_dir.exists() or not any(local_dir.glob("*.xml")):
        if status_cb: status_cb("loading", f"Downloading '{model_name}' (OV)...")
        state.log(f"⬇️  Downloading OV model: {repo_id}")
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*"],
        )
        state.log(f"✅ OV model saved to {local_dir}")
    return local_dir

# ─── Model loading ─────────────────────────────────────────────────────────────

def load_model(status_cb=None):
    state.whisper_model = None
    state.openvino_pipe = None
    if status_cb: status_cb("loading", f"Loading '{state.cfg['model']}'...")
    d, c = resolve_device(state.cfg["device"], state.cfg["compute_type"])

    # ── NPU path via OpenVINO GenAI ───────────────────────────────────────────
    if d == "npu":
        try:
            import openvino_genai
            model_dir = _download_ov_model(state.cfg["model"], status_cb)
            state.log("ℹ️  Compiling for NPU – first run may take ~1 min...")
            if status_cb: status_cb("loading", "Compiling for NPU...")
            state.openvino_pipe = openvino_genai.WhisperPipeline(str(model_dir), device="NPU")
            if status_cb: status_cb("ready", f"{T('ready')}  [NPU]")
            state.log("✅ Model loaded on NPU (OpenVINO)")
            return
        except Exception as e:
            state.log(f"⚠️  NPU failed: {e}")
            state.log("↩️  Falling back to CPU...")
            d, c = "cpu", "int8"

    # ── CPU / CUDA path via faster-whisper ────────────────────────────────────
    lbl = {"cuda": "CUDA (NVIDIA)", "cpu": "CPU"}.get(d, d)
    state.log(f"ℹ️  Device: {lbl} | Compute: {c} | Model: {state.cfg['model']}")
    try:
        from faster_whisper import WhisperModel
        state.whisper_model = WhisperModel(
            state.cfg["model"], device=d, compute_type=c,
            download_root=str(get_models_dir()),
        )
        if status_cb: status_cb("ready", f"{T('ready')}  [{lbl}]")
        state.log(f"✅ Model loaded on {lbl}")
    except Exception as e:
        state.log(f"⚠️  {lbl} failed: {e}")
        try:
            from faster_whisper import WhisperModel
            state.whisper_model = WhisperModel(
                state.cfg["model"], device="cpu", compute_type="int8",
                download_root=str(get_models_dir()),
            )
            if status_cb: status_cb("ready", f"{T('ready')}  [CPU Fallback]")
            state.log("✅ CPU fallback active")
        except Exception as e2:
            if status_cb: status_cb("error", T("load_error"))
            state.log(f"❌ Error: {e2}")
