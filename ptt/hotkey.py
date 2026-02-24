"""
ptt/hotkey.py – PTT hotkey listener (keyboard + optional mouse).
"""

import threading

from pynput import keyboard as pynput_kb
from pynput import mouse    as pynput_ms

import ptt.state as state
from ptt.constants import MOUSE_BTN_NAMES

# ─── Hotkey parsing ────────────────────────────────────────────────────────────

def parse_hotkey(hk_str: str) -> dict:
    parts   = [p.strip().lower() for p in hk_str.split("+")]
    mod_set = {"ctrl", "alt", "shift", "cmd"}
    mods, main, mouse = set(), None, None
    for p in parts:
        if p in mod_set:             mods.add(p)
        elif p.startswith("mouse_"): mouse = p
        else:                        main = p
    return {"mods": mods, "key": main, "mouse": mouse}

def _pynput_key_name(key) -> str:
    try:
        return key.char.lower()
    except AttributeError:
        name = str(key).replace("Key.", "").lower()
        for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                         ("alt_l","alt"),("alt_r","alt"),("alt_gr","alt"),
                         ("shift_l","shift"),("shift_r","shift"),
                         ("cmd_l","cmd"),("cmd_r","cmd")]:
            name = name.replace(old, new)
        return name

# ─── PTT listener lifecycle ────────────────────────────────────────────────────

def start_ptt_listener():
    stop_ptt_listener()
    hk       = parse_hotkey(state.cfg["hotkey"])
    mod_mods = hk["mods"]
    hk_key   = hk["key"]
    hk_mouse = hk["mouse"]
    held_keys = set()

    def mods_ok():
        return mod_mods.issubset(held_keys)

    def on_kb_press(key):
        kn = _pynput_key_name(key)
        held_keys.add(kn)
        if hk_key and kn == hk_key and mods_ok():
            _ptt_trigger_press()

    def on_kb_release(key):
        kn = _pynput_key_name(key)
        if hk_key and kn == hk_key:
            _ptt_trigger_release()
        held_keys.discard(kn)

    state._ptt_kb_listener = pynput_kb.Listener(
        on_press=on_kb_press, on_release=on_kb_release, daemon=True)
    state._ptt_kb_listener.start()

    if hk_mouse:
        target_btn = next((b for b, n in MOUSE_BTN_NAMES.items() if n == hk_mouse), None)
        def on_ms_press(x, y, button, pressed):
            if button == target_btn:
                if pressed and mods_ok(): _ptt_trigger_press()
                elif not pressed:         _ptt_trigger_release()
        state._ptt_ms_listener = pynput_ms.Listener(on_click=on_ms_press, daemon=True)
        state._ptt_ms_listener.start()

def stop_ptt_listener():
    for lst in (state._ptt_kb_listener, state._ptt_ms_listener):
        if lst:
            try: lst.stop()
            except Exception: pass
    state._ptt_kb_listener = None
    state._ptt_ms_listener = None

# ─── PTT trigger callbacks ─────────────────────────────────────────────────────

def _ptt_trigger_press():
    from ptt.audio import start_recording
    if not state._ptt_active and (state.whisper_model is not None or state.openvino_pipe is not None):
        state._ptt_active = True
        start_recording()

def _ptt_trigger_release():
    from ptt.audio import stop_recording
    from ptt.transcribe import transcribe_and_paste
    if state._ptt_active:
        state._ptt_active = False
        stop_recording()
        threading.Thread(target=transcribe_and_paste, daemon=True).start()
