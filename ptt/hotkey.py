"""
ptt/hotkey.py – PTT hotkey listener (keyboard + optional mouse).

On Wayland, pynput/XRecord is blocked by the compositor.  When
XDG_SESSION_TYPE=wayland is detected we automatically switch to an evdev
backend that reads raw kernel input events.  This requires the user to be in
the 'input' group:
    sudo usermod -aG input $USER  # then re-login
"""

import os
import select as _select
import threading

from pynput import keyboard as pynput_kb
from pynput import mouse    as pynput_ms

import ptt.state as state

MOUSE_BTN_NAMES = {
    pynput_ms.Button.left:   "mouse_left",
    pynput_ms.Button.right:  "mouse_right",
    pynput_ms.Button.middle: "mouse_middle",
#    pynput_ms.Button.x1:     "mouse_x1",
#    pynput_ms.Button.x2:     "mouse_x2",
    pynput_ms.Button.button8: "mouse_x1",
    pynput_ms.Button.button9: "mouse_x2",
}

# Module-level evdev state (Wayland backend)
_evdev_stop   = None   # threading.Event
_evdev_thread = None   # threading.Thread

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
        ch = key.char
        if ch is None:
            raise AttributeError
        # On Linux/X11, holding Ctrl or Alt changes the character produced:
        #   Ctrl+Space  → '\x00' (NUL)
        #   Alt+Space   → '\xa0' (non-breaking space)
        #   Ctrl+a..z   → '\x01'..'\x1a'
        # Normalise these back to the base key name so hotkey matching works.
        if ch in ('\x00', '\xa0'):
            return 'space'
        if len(ch) == 1 and '\x01' <= ch <= '\x1a':
            return chr(ord('a') + ord(ch) - 1)  # ctrl+letter → letter
        return ch.lower()
    except AttributeError:
        name = str(key).replace("Key.", "").lower()
        for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                         ("alt_l","alt"),("alt_r","alt"),("alt_gr","alt"),
                         ("shift_l","shift"),("shift_r","shift"),
                         ("cmd_l","cmd"),("cmd_r","cmd")]:
            name = name.replace(old, new)
        return name

# ─── evdev backend (Wayland) ───────────────────────────────────────────────────

def _evdev_key_name(code: int) -> str:
    """Convert an evdev key code to the same name strings used by pynput paths."""
    try:
        from evdev import ecodes
        if code in (ecodes.KEY_LEFTCTRL,  ecodes.KEY_RIGHTCTRL):  return 'ctrl'
        if code in (ecodes.KEY_LEFTALT,   ecodes.KEY_RIGHTALT):   return 'alt'
        if code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT): return 'shift'
        if code in (ecodes.KEY_LEFTMETA,  ecodes.KEY_RIGHTMETA):  return 'cmd'
        if code == ecodes.KEY_SPACE:     return 'space'
        if code == ecodes.KEY_ENTER:     return 'enter'
        if code == ecodes.KEY_BACKSPACE: return 'backspace'
        if code == ecodes.KEY_TAB:       return 'tab'
        if code == ecodes.KEY_ESC:       return 'esc'
        # F-keys
        for n in range(1, 13):
            fk = getattr(ecodes, f'KEY_F{n}', None)
            if fk is not None and code == fk:
                return f'f{n}'
        # Alpha keys: KEY_A..KEY_Z → 'a'..'z'
        for c in 'abcdefghijklmnopqrstuvwxyz':
            ak = getattr(ecodes, f'KEY_{c.upper()}', None)
            if ak is not None and code == ak:
                return c
        # Digit keys: KEY_0..KEY_9
        for n in range(10):
            dk = getattr(ecodes, f'KEY_{n}', None)
            if dk is not None and code == dk:
                return str(n)
        # Fallback: use evdev name map
        names = ecodes.KEY.get(code, None)
        if isinstance(names, str):
            return names.replace('KEY_', '').lower()
        if isinstance(names, list) and names:
            return names[0].replace('KEY_', '').lower()
        return f'key_{code}'
    except Exception:
        return f'key_{code}'


_EVDEV_NORMALIZE = {
    # All Ctrl/Alt/Shift/Meta variants → canonical names used in parse_hotkey()
    "leftctrl": "ctrl",  "rightctrl": "ctrl",
    "leftalt":  "alt",   "rightalt":  "alt",   "altgr": "alt",
    "leftshift":"shift", "rightshift":"shift",
    "leftmeta": "cmd",   "rightmeta": "cmd",
    "ctrl_l":   "ctrl",  "ctrl_r":    "ctrl",
    "alt_l":    "alt",   "alt_r":     "alt",
    "shift_l":  "shift", "shift_r":   "shift",
    "meta_l":   "cmd",   "meta_r":    "cmd",
    "kp_space": "space",
}

def _evdev_normalize(name: str) -> str:
    return _EVDEV_NORMALIZE.get(name, name)


def _evdev_listener_thread(held_keys, on_press, on_release, stop_event):
    """Background thread: reads raw evdev events from all keyboard devices."""
    try:
        import evdev
        from evdev import ecodes
    except ImportError:
        state.log("❌ evdev not installed – run: pip install evdev")
        return

    all_paths = list(evdev.list_devices())
    if not all_paths:
        import grp, pwd, os as _os
        try:
            in_group = any(
                g.gr_name == "input"
                for g in grp.getgrall()
                if pwd.getpwuid(_os.getuid()).pw_name in g.gr_mem
                   or g.gr_gid == _os.getgid()
            )
            in_current = "input" in [grp.getgrgid(g).gr_name for g in _os.getgroups()]
        except Exception:
            in_group = in_current = False
        if in_group and not in_current:
            state.log(
                "❌ evdev: You are in the 'input' group (in /etc/group) but your\n"
                "   current graphical session does not have it yet.\n"
                "   ➜ Log out of your desktop (GNOME/KDE) completely and log back in.\n"
                "   Just closing terminals is not enough!"
            )
        else:
            state.log(
                "❌ evdev: no input devices accessible.\n"
                "   Add yourself to the 'input' group and re-login:\n"
                "   sudo usermod -aG input $USER"
            )
        return

    kb_devs = []
    for path in all_paths:
        try:
            dev = evdev.InputDevice(path)
            caps = dev.capabilities()
            # Only real keyboards: must have EV_KEY and KEY_A (mice don't have KEY_A)
            key_caps = caps.get(ecodes.EV_KEY, [])
            if ecodes.EV_KEY in caps and ecodes.KEY_A in key_caps:
                kb_devs.append(dev)
            else:
                dev.close()
        except Exception:
            pass

    if not kb_devs:
        state.log(
            "❌ evdev: no keyboard devices found.\n"
            "   Add yourself to the 'input' group and re-login:\n"
            "   sudo usermod -aG input $USER"
        )
        return

    names = ", ".join(d.name for d in kb_devs)
    state.log(f"⌨️  evdev listening on {len(kb_devs)} device(s): {names}")

    fds = {d.fd: d for d in kb_devs}
    while not stop_event.is_set():
        try:
            readable, _, _ = _select.select(list(fds.keys()), [], [], 0.2)
            for fd in readable:
                dev = fds.get(fd)
                if dev is None:
                    continue
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.value == 2:  # key-repeat; ignore
                            continue
                        name = _evdev_normalize(_evdev_key_name(event.code))
                        if event.value == 1:    # key down
                            on_press(name)
                        else:                   # key up
                            on_release(name)
                except OSError:
                    # Device disappeared (e.g. USB unplugged)
                    fds.pop(fd, None)
                except Exception as _e:
                    state.log(f"[evdev] read error: {_e}")
        except Exception:
            break

    for d in kb_devs:
        try:
            d.close()
        except Exception:
            pass


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


# ─── PTT listener lifecycle ────────────────────────────────────────────────────

def start_ptt_listener():
    global _evdev_stop, _evdev_thread
    stop_ptt_listener()

    hk       = parse_hotkey(state.cfg["hotkey"])
    mod_mods = hk["mods"]
    hk_key   = hk["key"]
    hk_mouse = hk["mouse"]
    held_keys = set()

    def mods_ok():
        return mod_mods.issubset(held_keys)

    def on_press(name: str):
        held_keys.add(name)
        if hk_key and name == hk_key:
            if mods_ok():
                _ptt_trigger_press()
            else:
                state.log(f"🔑 '{name}' pressed – held: {held_keys}, need mods: {mod_mods}")

    def on_release(name: str):
        if hk_key and name == hk_key:
            _ptt_trigger_release()
        held_keys.discard(name)

    # ── Wayland: try evdev backend ──────────────────────────────────────────
    if _is_wayland():
        state.log("🐧 Wayland session detected – using evdev keyboard backend")
        try:
            import evdev  # noqa: F401 – just check it's importable
            _evdev_stop   = threading.Event()
            _evdev_thread = threading.Thread(
                target=_evdev_listener_thread,
                args=(held_keys, on_press, on_release, _evdev_stop),
                daemon=True,
            )
            _evdev_thread.start()
            state.log(f"⌨️  PTT listener started (evdev): {state.cfg['hotkey']}")
        except ImportError:
            state.log(
                "⚠️  evdev not installed – falling back to pynput (may not work on Wayland).\n"
                "   Install: pip install evdev"
            )
            _start_pynput_listener(on_press, on_release, hk_mouse, mod_mods, held_keys)
        return

    # ── X11 / other: use pynput ─────────────────────────────────────────────
    _start_pynput_listener(on_press, on_release, hk_mouse, mod_mods, held_keys)


def _start_pynput_listener(on_press, on_release, hk_mouse, mod_mods, held_keys):
    def on_kb_press(key):
        on_press(_pynput_key_name(key))

    def on_kb_release(key):
        on_release(_pynput_key_name(key))

    try:
        state._ptt_kb_listener = pynput_kb.Listener(
            on_press=on_kb_press, on_release=on_kb_release, daemon=True)
        state._ptt_kb_listener.start()
        state.log(f"⌨️  PTT listener started (pynput): {state.cfg['hotkey']}")
    except Exception as e:
        state.log(f"❌ PTT keyboard listener failed: {e}")
        state._ptt_kb_listener = None

    if hk_mouse:
        target_btn = next((b for b, n in MOUSE_BTN_NAMES.items() if n == hk_mouse), None)
        def mods_ok():
            return mod_mods.issubset(held_keys)
        def on_ms_press(x, y, button, pressed):
            if button == target_btn:
                if pressed and mods_ok(): _ptt_trigger_press()
                elif not pressed:         _ptt_trigger_release()
        state._ptt_ms_listener = pynput_ms.Listener(on_click=on_ms_press, daemon=True)
        state._ptt_ms_listener.start()


def stop_ptt_listener():
    global _evdev_stop, _evdev_thread
    # Stop evdev backend
    if _evdev_stop is not None:
        _evdev_stop.set()
        _evdev_stop   = None
        _evdev_thread = None
    # Stop pynput listeners
    for lst in (state._ptt_kb_listener, state._ptt_ms_listener):
        if lst:
            try: lst.stop()
            except Exception: pass
    state._ptt_kb_listener = None
    state._ptt_ms_listener = None

# ─── PTT trigger callbacks ─────────────────────────────────────────────────────

def _ptt_trigger_press():
    from ptt.audio import start_recording
    with state.ptt_lock:
        if state._ptt_active:
            return
        if state.whisper_model is None and state.openvino_pipe is None:
            state.log("⏳ PTT pressed – model not ready yet, ignoring.")
            return
        state._ptt_active = True
    state.log("🎙️  PTT START – recording…")
    start_recording()

def _ptt_trigger_release():
    from ptt.audio import stop_recording
    from ptt.transcribe import transcribe_and_paste
    with state.ptt_lock:
        if not state._ptt_active:
            return
        state._ptt_active = False
    state.log("🔍 PTT STOP – transcribing…")
    stop_recording()
    threading.Thread(target=transcribe_and_paste, daemon=True).start()
