"""
ptt/config.py – Translation helper, settings load/save, model directory resolver.
"""

import json
from pathlib import Path

import ptt.state as state
from ptt.constants import DEFAULTS, SETTINGS_FILE, MODEL_CACHE_DIR, TRANSLATIONS

# ─── Translation helper ────────────────────────────────────────────────────────

def T(key: str, lang: str = None) -> str:
    """Return translated string for current UI language."""
    l = lang or state.cfg.get("ui_lang", "en")
    entry = TRANSLATIONS.get(key, {})
    return entry.get(l, entry.get("en", key))

# ─── Settings ──────────────────────────────────────────────────────────────────

def load_settings():
    state.cfg.clear()
    state.cfg.update(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                state.cfg.update(json.load(f))
        except Exception:
            pass

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(state.cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Settings error: {e}")

# ─── Model directory ───────────────────────────────────────────────────────────

def get_models_dir() -> Path:
    """Return the effective model cache directory (from cfg or default)."""
    d = state.cfg.get("models_dir", "").strip()
    return Path(d) if d else Path(MODEL_CACHE_DIR)
