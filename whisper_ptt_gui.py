#!/usr/bin/env python3
"""
Whisper PTT – GUI Edition v3
==============================
Fixes gegenüber v2:
  • Settings-Fenster öffnet immer wieder korrekt
  • Maustasten (Daumentaste etc.) werden im Hotkey-Recorder erkannt (pynput)
  • Kopieren gibt nur den erkannten Text OHNE Zeitstempel aus
  • Getrennte Felder: "Erkannter Text" und "Debug / Log"
  • Texte im Textfeld können markiert und teilweise kopiert werden
    (Drag gilt nur auf der Titelleiste, nicht im Content-Bereich)
"""

import os, sys, time, json, tempfile, threading, queue
import numpy as np
import sounddevice as sd
import soundfile as sf
import pyperclip
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# pynput für keyboard + mouse (Maustasten-Support)
from pynput import keyboard as pynput_kb
from pynput import mouse    as pynput_ms

# ─── Pfade ─────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
SETTINGS_FILE   = BASE_DIR / "settings.json"
MODEL_CACHE_DIR = str(BASE_DIR / "models")

# ─── Defaults ──────────────────────────────────────────────────────────────────

DEFAULTS = {
    "hotkey":          "ctrl+alt+space",
    "language":        "de",
    "model":           "base",
    "device":          "auto",
    "compute_type":    "auto",
    "paste_mode":      "clipboard",
    "vad_filter":      True,
    "vad_silence_ms":  300,
    "sound_feedback":  True,
    "opacity":         0.95,
    "beam_size":       5,
    "window_x":        -1,
    "window_y":        -1,
}

# ─── Farben ────────────────────────────────────────────────────────────────────

C = {
    "bg":         "#1a1a2e", "bg2": "#16213e", "bg3": "#0d0d1a",
    "accent":     "#0f3460", "accent2": "#1a4a8a",
    "idle":       "#4a4a6a", "record": "#e94560",
    "process":    "#f5a623", "ready": "#00d4aa",
    "text":       "#e0e0e0", "dim": "#888899",
    "meter_low":  "#00d4aa", "meter_mid": "#f5a623", "meter_high": "#e94560",
    "btn_copy":   "#0f3460", "btn_paste": "#1a6b3c",
    "btn_clear":  "#3d1a1a", "btn_set": "#2a2a4a", "sep": "#333355",
}

LANGUAGES = {
    "Automatisch": None, "Deutsch": "de", "Englisch": "en",
    "Franzoesisch": "fr", "Spanisch": "es", "Italienisch": "it",
    "Niederlaendisch": "nl", "Polnisch": "pl", "Russisch": "ru",
    "Chinesisch": "zh", "Japanisch": "ja", "Tuerkisch": "tr",
}
MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
DEVICES = {
    "Auto-Erkennung": "auto", "NVIDIA CUDA": "cuda",
    "NPU / DirectML": "dml", "CPU": "cpu",
}
COMPUTE_TYPES = {
    "Auto": "auto", "float16 (GPU)": "float16",
    "int8 (schnell)": "int8", "float32 (CPU)": "float32",
}

# ─── Maustasten-Mapping ────────────────────────────────────────────────────────
# pynput Button → lesbarer Name (für hotkey-String)

MOUSE_BTN_NAMES = {
    pynput_ms.Button.left:    "mouse_left",
    pynput_ms.Button.right:   "mouse_right",
    pynput_ms.Button.middle:  "mouse_middle",
    pynput_ms.Button.x1:      "mouse_x1",   # Daumentaste zurück
    pynput_ms.Button.x2:      "mouse_x2",   # Daumentaste vor
}
MOUSE_BTN_LABELS = {
    "mouse_left":   "Maus Links",
    "mouse_right":  "Maus Rechts",
    "mouse_middle": "Maus Mitte",
    "mouse_x1":     "Daumentaste Zurück",
    "mouse_x2":     "Daumentaste Vor",
}

# ─── Globaler State ─────────────────────────────────────────────────────────────

recording      = False
audio_chunks   = []
record_lock    = threading.Lock()
whisper_model  = None
current_volume = 0.0
ui_queue       = queue.Queue()
cfg            = dict(DEFAULTS)

# Aktiver PTT-Listener (pynput)
_ptt_kb_listener  = None
_ptt_ms_listener  = None
_ptt_active       = False   # True = Hotkey gerade gedrückt

# ─── Settings ──────────────────────────────────────────────────────────────────

def load_settings():
    global cfg
    cfg = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _log(f"Settings-Fehler: {e}")

# ─── Hardware-Erkennung ────────────────────────────────────────────────────────

def detect_devices() -> dict:
    r = {"cuda": False, "dml": False, "cuda_name": "", "npu_name": ""}
    try:
        import torch
        if torch.cuda.is_available():
            r["cuda"] = True; r["cuda_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    try:
        import openvino as ov
        devs = ov.Core().available_devices
        if any("NPU" in d for d in devs):
            r["dml"] = True; r["npu_name"] = next(d for d in devs if "NPU" in d)
    except Exception:
        pass
    try:
        import onnxruntime as ort
        if "DmlExecutionProvider" in ort.get_available_providers():
            r["dml"] = True; r["npu_name"] = r["npu_name"] or "DirectML"
    except Exception:
        pass
    return r

def resolve_device(dev_cfg, compute_cfg):
    av = detect_devices()
    if dev_cfg == "auto":
        if av["cuda"]: d, c = "cuda", "float16"
        elif av["dml"]: d, c = "dml", "int8"
        else: d, c = "cpu", "int8"
    elif dev_cfg == "cuda": d, c = "cuda", "float16"
    elif dev_cfg == "dml":  d, c = "dml",  "int8"
    else:                   d, c = "cpu",  "int8"
    if compute_cfg != "auto": c = compute_cfg
    return d, c

# ─── Modell laden ──────────────────────────────────────────────────────────────

def load_model(status_cb=None):
    global whisper_model
    if status_cb: status_cb("loading", f"Lade '{cfg['model']}'...")
    d, c = resolve_device(cfg["device"], cfg["compute_type"])
    lbl  = {"cuda": "CUDA", "dml": "NPU/DirectML", "cpu": "CPU"}.get(d, d)
    _log(f"ℹ️  Gerät: {lbl} | Compute: {c} | Modell: {cfg['model']}")
    try:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel(cfg["model"], device=d, compute_type=c,
                                     download_root=MODEL_CACHE_DIR)
        if status_cb: status_cb("ready", f"Bereit  [{lbl}]")
        _log(f"✅ Modell geladen auf {lbl}")
    except Exception as e:
        _log(f"⚠️  {lbl} fehlgeschlagen: {e}")
        try:
            from faster_whisper import WhisperModel
            whisper_model = WhisperModel(cfg["model"], device="cpu", compute_type="int8",
                                         download_root=MODEL_CACHE_DIR)
            if status_cb: status_cb("ready", "Bereit  [CPU Fallback]")
            _log("✅ CPU-Fallback aktiv")
        except Exception as e2:
            if status_cb: status_cb("error", "Ladefehler!")
            _log(f"❌ Fehler: {e2}")

def _log(msg):
    ui_queue.put(("log", msg))

# ─── Hotkey-Parser ─────────────────────────────────────────────────────────────

def parse_hotkey(hk_str: str) -> dict:
    """
    Zerlegt einen Hotkey-String in Modifier-Keys und Haupttaste.
    Beispiele:
      "ctrl+alt+space"    → {mods: {"ctrl","alt"}, key: "space", mouse: None}
      "ctrl+mouse_x1"     → {mods: {"ctrl"},        key: None,   mouse: "mouse_x1"}
      "mouse_x2"          → {mods: set(),           key: None,   mouse: "mouse_x2"}
    """
    parts   = [p.strip().lower() for p in hk_str.split("+")]
    mod_set = {"ctrl", "alt", "shift", "cmd"}
    mods    = set()
    main    = None
    mouse   = None

    for p in parts:
        if p in mod_set:
            mods.add(p)
        elif p.startswith("mouse_"):
            mouse = p
        else:
            main = p

    return {"mods": mods, "key": main, "mouse": mouse}

def _pynput_key_name(key) -> str:
    """pynput Key-Objekt → lesbarer String (passt zu parse_hotkey)."""
    try:
        # Normale Zeichen-Taste
        return key.char.lower()
    except AttributeError:
        # Sonder-/Modifier-Taste
        name = str(key).replace("Key.", "").lower()
        # Normalisierungen
        name = name.replace("ctrl_l", "ctrl").replace("ctrl_r", "ctrl")
        name = name.replace("alt_l",  "alt" ).replace("alt_r",  "alt" )
        name = name.replace("shift",  "shift")
        name = name.replace("cmd",    "cmd"  )
        return name

# ─── PTT-Listener (pynput – unterstützt Keyboard + Mouse) ─────────────────────

def start_ptt_listener():
    """Startet den globalen PTT-Listener. Unterstützt keyboard- und mouse-Hotkeys."""
    global _ptt_kb_listener, _ptt_ms_listener
    stop_ptt_listener()

    hk        = parse_hotkey(cfg["hotkey"])
    mod_mods  = hk["mods"]
    hk_key    = hk["key"]
    hk_mouse  = hk["mouse"]
    held_keys = set()   # aktuell gedrückte Modifier

    def mods_ok():
        return mod_mods.issubset(held_keys)

    # ── Keyboard-Listener ─────────────────────────────────────────────────────

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

    _ptt_kb_listener = pynput_kb.Listener(
        on_press=on_kb_press, on_release=on_kb_release, daemon=True
    )
    _ptt_kb_listener.start()

    # ── Mouse-Listener (nur wenn Hotkey eine Maustaste enthält) ───────────────

    if hk_mouse:
        target_btn = next(
            (b for b, n in MOUSE_BTN_NAMES.items() if n == hk_mouse), None
        )

        def on_ms_press(x, y, button, pressed):
            if button == target_btn:
                if pressed and mods_ok():
                    _ptt_trigger_press()
                elif not pressed:
                    _ptt_trigger_release()

        _ptt_ms_listener = pynput_ms.Listener(on_click=on_ms_press, daemon=True)
        _ptt_ms_listener.start()

def stop_ptt_listener():
    global _ptt_kb_listener, _ptt_ms_listener
    for lst in (_ptt_kb_listener, _ptt_ms_listener):
        if lst:
            try: lst.stop()
            except Exception: pass
    _ptt_kb_listener = None
    _ptt_ms_listener = None

def _ptt_trigger_press():
    global _ptt_active
    if not _ptt_active and whisper_model is not None:
        _ptt_active = True
        start_recording()

def _ptt_trigger_release():
    global _ptt_active
    if _ptt_active:
        _ptt_active = False
        stop_recording()
        threading.Thread(target=transcribe_and_paste, daemon=True).start()

# ─── Audio ─────────────────────────────────────────────────────────────────────

def audio_callback(indata, frames, time_info, status):
    global current_volume
    current_volume = min(float(np.sqrt(np.mean(indata ** 2))) * 8.0, 1.0)
    if recording:
        audio_chunks.append(indata.copy())

def start_recording():
    global recording, audio_chunks
    with record_lock:
        audio_chunks = []; recording = True
    ui_queue.put(("status", "record", "Aufnahme..."))
    if cfg["sound_feedback"]: _beep(660, 0.08)

def stop_recording():
    global recording
    with record_lock:
        recording = False
    ui_queue.put(("status", "process", "Verarbeite..."))
    if cfg["sound_feedback"]: _beep(880, 0.10)

def _beep(freq=880, dur=0.08, vol=0.3):
    try:
        t    = np.linspace(0, dur, int(16000 * dur), False)
        wave = (np.sin(2 * np.pi * freq * t) * vol * 32767).astype(np.int16)
        sd.play(wave, 16000)
    except Exception:
        pass

# ─── Transkription ─────────────────────────────────────────────────────────────

def transcribe_and_paste():
    with record_lock:
        chunks = list(audio_chunks)
    if not chunks:
        ui_queue.put(("status", "ready", "Bereit")); return

    audio_data = np.concatenate(chunks, axis=0).flatten().astype(np.float32)
    if len(audio_data) / 16000 < 0.3:
        ui_queue.put(("status", "ready", "Bereit"))
        _log("⚠️  Aufnahme zu kurz – ignoriert."); return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        sf.write(tmp_path, audio_data, 16000)

    try:
        t0 = time.time()
        seg, _ = whisper_model.transcribe(
            tmp_path,
            language=cfg["language"] or None,
            beam_size=cfg["beam_size"],
            vad_filter=cfg["vad_filter"],
            vad_parameters=dict(min_silence_duration_ms=cfg["vad_silence_ms"]),
        )
        text    = " ".join(s.text.strip() for s in seg).strip()
        elapsed = time.time() - t0

        if not text:
            _log("⚠️  Kein Text erkannt.")
            ui_queue.put(("status", "ready", "Bereit")); return

        # Erkannten Text separat senden (ohne Timestamp → für Copy)
        ui_queue.put(("recognized", text))
        ui_queue.put(("status", "ready", f"Bereit  ({elapsed:.1f}s)"))
        _do_paste(text)
    except Exception as e:
        _log(f"❌ Fehler: {e}")
        ui_queue.put(("status", "ready", "Bereit"))
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass

def _do_paste(text: str):
    time.sleep(0.15)
    if cfg["paste_mode"] == "clipboard":
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.01)

# ─── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _lighten(hex_c: str, f=1.3) -> str:
    h = hex_c.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(255,int(r*f)), min(255,int(g*f)), min(255,int(b*f)))

def _section(parent, text):
    if text:
        tk.Label(parent, text=text, bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(10,0))
    tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", pady=(2,4))

def _flat_btn(parent, text, color, cmd, padx=8, pady=4):
    f = tk.Frame(parent, bg=color, cursor="hand2")
    l = tk.Label(f, text=text, bg=color, fg=C["text"],
                 font=("Segoe UI", 8, "bold"), padx=padx, pady=pady, cursor="hand2")
    l.pack()
    def click(e): cmd()
    def enter(e): b=_lighten(color); f.config(bg=b); l.config(bg=b)
    def leave(e): f.config(bg=color); l.config(bg=color)
    for w in (f, l):
        w.bind("<Button-1>", click)
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)
    return f

def _make_text_widget(parent, height=5):
    """Erstellt ein Text-Widget, das Markieren erlaubt ohne Fenster zu verschieben."""
    tf = tk.Frame(parent, bg=C["bg2"], highlightthickness=1,
                  highlightbackground=C["sep"])
    tf.pack(fill="both", expand=True, pady=(2,4))

    sb = tk.Scrollbar(tf, bg=C["bg"], troughcolor=C["bg2"],
                      relief="flat", bd=0, width=10)
    sb.pack(side="right", fill="y")

    txt = tk.Text(
        tf, height=height, width=36,
        bg=C["bg2"], fg=C["text"],
        insertbackground=C["text"],
        selectbackground=C["accent2"], selectforeground=C["text"],
        font=("Consolas", 9), wrap="word", relief="flat", bd=4,
        yscrollcommand=sb.set, cursor="xterm",
    )
    txt.pack(side="left", fill="both", expand=True)
    sb.config(command=txt.yview)

    # WICHTIG: Maus-Events auf dem Text-Widget NICHT an Root weiterleiten
    # → verhindert Fenster-Drag beim Markieren von Text
    txt.bind("<ButtonPress-1>",   lambda e: "break" if False else None)
    txt.bind("<B1-Motion>",       lambda e: None)   # normale Selektion erlaubt
    txt.bind("<ButtonRelease-1>", lambda e: None)

    return txt

# ═══════════════════════════════════════════════════════════════════════════════
#  Haupt-Overlay
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperPTTApp:

    STATUS_COLORS = {
        "idle":    C["idle"],   "loading": C["process"],
        "ready":   C["ready"],  "record":  C["record"],
        "process": C["process"],"error":   C["record"],
    }

    def __init__(self, root: tk.Tk):
        self.root          = root
        self._minimized    = False
        self._settings_win = None
        self._clean_texts  = []     # Nur erkannter Text, ohne Timestamps

        self._build_window()
        self._build_ui()
        self._poll_queue()
        self._animate_meter()

        threading.Thread(
            target=load_model,
            args=(lambda s, m: ui_queue.put(("status", s, m)),),
            daemon=True,
        ).start()
        threading.Thread(target=start_ptt_listener, daemon=True).start()

    # ── Fenster ────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.root.title("Whisper PTT")
        self.root.configure(bg=C["bg"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", cfg["opacity"])
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.update_idletasks()
        if cfg["window_x"] >= 0:
            self.root.geometry(f"+{cfg['window_x']}+{cfg['window_y']}")
        else:
            sw = self.root.winfo_screenwidth()
            self.root.geometry(f"+{sw - 370}+20")

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=C["bg"],
                         highlightbackground=C["sep"], highlightthickness=1)
        outer.pack(fill="both", expand=True)

        # Titelleiste – NUR hier ist Drag aktiviert
        self._bar = tk.Frame(outer, bg=C["accent"], height=30)
        self._bar.pack(fill="x")
        self._bar.bind("<ButtonPress-1>",   self._drag_start)
        self._bar.bind("<B1-Motion>",       self._drag_motion)
        self._bar.bind("<ButtonRelease-1>", self._drag_end)

        tk.Label(self._bar, text="🎤  Whisper PTT",
                 bg=C["accent"], fg=C["text"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=8, pady=5)

        for sym, cmd in [("✕", self._on_close), ("─", self._toggle_min)]:
            lb = tk.Label(self._bar, text=sym, bg=C["accent"], fg=C["dim"],
                          font=("Segoe UI", 11), cursor="hand2", padx=6)
            lb.pack(side="right")
            lb.bind("<Button-1>", lambda e, c=cmd: c())
            lb.bind("<Enter>",    lambda e, l=lb: l.config(fg=C["text"]))
            lb.bind("<Leave>",    lambda e, l=lb: l.config(fg=C["dim"]))

        # Content – KEIN Drag hier
        self.content = tk.Frame(outer, bg=C["bg"], padx=10, pady=8)
        self.content.pack(fill="both", expand=True)

        # Status-Zeile
        row = tk.Frame(self.content, bg=C["bg"])
        row.pack(fill="x", pady=(0, 5))

        self.dot_cv = tk.Canvas(row, width=14, height=14, bg=C["bg"],
                                highlightthickness=0)
        self.dot_cv.pack(side="left")
        self._dot = self.dot_cv.create_oval(2, 2, 12, 12, fill=C["idle"], outline="")

        self.status_lbl = tk.Label(row, text="Initialisiere...",
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=(6, 0))

        gear = tk.Label(row, text="⚙", bg=C["bg"], fg=C["dim"],
                        font=("Segoe UI", 13), cursor="hand2")
        gear.pack(side="right")
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>",    lambda e: gear.config(fg=C["text"]))
        gear.bind("<Leave>",    lambda e: gear.config(fg=C["dim"]))

        self.hotkey_lbl = tk.Label(row, text=cfg["hotkey"],
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 8))
        self.hotkey_lbl.pack(side="right", padx=(0, 4))

        # Voice-Meter
        tk.Label(self.content, text="MIKROFON", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.meter_cv = tk.Canvas(self.content, height=16, bg=C["bg3"],
                                  highlightthickness=1, highlightbackground=C["sep"])
        self.meter_cv.pack(fill="x", pady=(2, 8))
        self._mbar = self.meter_cv.create_rectangle(0, 0, 0, 16,
                                                    fill=C["meter_low"], outline="")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # ── Feld 1: Erkannter Text ─────────────────────────────────────────────
        tk.Label(self.content, text="ERKANNTER TEXT", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")

        self.recog_txt = _make_text_widget(self.content, height=5)

        # Buttons für erkannten Text
        br1 = tk.Frame(self.content, bg=C["bg"])
        br1.pack(fill="x", pady=(0, 6))
        _flat_btn(br1, "📋 Kopieren", C["btn_copy"],  self._copy_recog ).pack(side="left", padx=(0,4))
        _flat_btn(br1, "📌 Einfügen", C["btn_paste"], self._paste_recog).pack(side="left", padx=(0,4))
        _flat_btn(br1, "🗑️ Leeren",  C["btn_clear"], self._clear_recog).pack(side="right")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # ── Feld 2: Debug / Log ────────────────────────────────────────────────
        tk.Label(self.content, text="DEBUG / LOG", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")

        self.debug_txt = _make_text_widget(self.content, height=4)
        self.debug_txt.config(fg=C["dim"])   # etwas gedimmter

        br2 = tk.Frame(self.content, bg=C["bg"])
        br2.pack(fill="x", pady=(0, 0))
        _flat_btn(br2, "🗑️ Log leeren", C["btn_clear"], self._clear_debug).pack(side="right")

    # ── Drag (nur Titelleiste) ─────────────────────────────────────────────────

    def _drag_start(self, e):
        self._dx = e.x; self._dy = e.y

    def _drag_motion(self, e):
        x = self.root.winfo_x() + (e.x - self._dx)
        y = self.root.winfo_y() + (e.y - self._dy)
        self.root.geometry(f"+{x}+{y}")

    def _drag_end(self, e):
        cfg["window_x"] = self.root.winfo_x()
        cfg["window_y"] = self.root.winfo_y()
        save_settings()

    # ── Aktionen: Erkannter Text ───────────────────────────────────────────────

    def _copy_recog(self):
        """Kopiert Selektion ODER den saubersten verfügbaren Text – KEIN Timestamp."""
        try:
            text = self.recog_txt.get("sel.first", "sel.last")
        except tk.TclError:
            # Keine Selektion → letzten erkannten Text aus _clean_texts
            text = self._clean_texts[-1] if self._clean_texts else \
                   self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self._flash("📋 Kopiert!")

    def _paste_recog(self):
        """Fügt letzten erkannten Text in aktives Fenster ein."""
        text = self._clean_texts[-1] if self._clean_texts else \
               self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self.root.after(150, lambda: pyautogui.hotkey("ctrl", "v"))
            self._flash("📌 Eingefügt!")

    def _clear_recog(self):
        self._clean_texts.clear()
        self.recog_txt.config(state="normal")
        self.recog_txt.delete("1.0", "end")

    def _clear_debug(self):
        self.debug_txt.config(state="normal")
        self.debug_txt.delete("1.0", "end")

    def _flash(self, msg, ms=1500):
        old = self.status_lbl.cget("text")
        self.status_lbl.config(text=msg, fg=C["ready"])
        self.root.after(ms, lambda: self.status_lbl.config(text=old, fg=C["dim"]))

    # ── Minimize / Close ───────────────────────────────────────────────────────

    def _toggle_min(self):
        self._minimized = not self._minimized
        if self._minimized: self.content.pack_forget()
        else:               self.content.pack(fill="both", expand=True)

    def _on_close(self):
        cfg["window_x"] = self.root.winfo_x()
        cfg["window_y"] = self.root.winfo_y()
        save_settings()
        stop_ptt_listener()
        self.root.destroy()

    # ── Queue-Polling ──────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                msg = ui_queue.get_nowait()
                if msg[0] == "status":
                    self._set_status(msg[1], msg[2])
                elif msg[0] == "recognized":
                    self._append_recognized(msg[1])
                elif msg[0] == "log":
                    self._append_log(msg[1])
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)

    def _set_status(self, state, text):
        color = self.STATUS_COLORS.get(state, C["idle"])
        self.dot_cv.itemconfig(self._dot, fill=color)
        self.status_lbl.config(text=text,
                               fg=color if state not in ("ready","idle") else C["dim"])
        if state == "record": self._pulse(color)

    def _pulse(self, color, step=0):
        if not recording:
            self.dot_cv.itemconfig(self._dot, fill=color); return
        self.dot_cv.itemconfig(self._dot, fill=color if step%2==0 else C["bg2"])
        self.root.after(400, lambda: self._pulse(color, step+1))

    def _append_recognized(self, text: str):
        """Fügt erkannten Text ins obere Feld ein – NUR Text, kein Timestamp."""
        self._clean_texts.append(text)
        self.recog_txt.config(state="normal")
        # Trennlinie wenn schon Inhalt vorhanden
        if self.recog_txt.index("end-1c") != "1.0":
            self.recog_txt.insert("end", "\n─────\n")
        self.recog_txt.insert("end", text)
        self.recog_txt.see("end")

    def _append_log(self, text: str):
        """Fügt Debug-Nachricht mit Timestamp ins untere Feld ein."""
        self.debug_txt.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.debug_txt.insert("end", f"[{ts}] {text}\n")
        self.debug_txt.see("end")

    # ── Meter-Animation ────────────────────────────────────────────────────────

    def _animate_meter(self):
        try:
            w  = self.meter_cv.winfo_width() or 300
            bw = int(w * current_volume)
            lv = current_volume
            c  = C["meter_low"] if lv < 0.5 else C["meter_mid"] if lv < 0.8 else C["meter_high"]
            self.meter_cv.coords(self._mbar, 0, 0, bw, 16)
            self.meter_cv.itemconfig(self._mbar, fill=c)
        except Exception: pass
        self.root.after(40, self._animate_meter)

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self):
        # Fix: Fenster immer neu öffnen / nach vorne bringen
        if self._settings_win is not None:
            try:
                if self._settings_win.win.winfo_exists():
                    self._settings_win.win.lift()
                    self._settings_win.win.focus_force()
                    return
            except Exception:
                pass
            self._settings_win = None

        self._settings_win = SettingsWindow(
            self.root,
            on_save_cb=self._on_settings_saved,
            on_close_cb=self._on_settings_closed,
        )

    def _on_settings_closed(self):
        """Callback wenn Settings-Fenster geschlossen wird."""
        self._settings_win = None

    def _on_settings_saved(self):
        self._settings_win = None
        self.hotkey_lbl.config(text=cfg["hotkey"])
        self.root.attributes("-alpha", cfg["opacity"])
        threading.Thread(target=start_ptt_listener, daemon=True).start()
        threading.Thread(
            target=load_model,
            args=(lambda s, m: ui_queue.put(("status", s, m)),),
            daemon=True,
        ).start()


# ═══════════════════════════════════════════════════════════════════════════════
#  Settings-Fenster
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsWindow:

    def __init__(self, parent, on_save_cb, on_close_cb):
        self.parent             = parent
        self.on_save_cb         = on_save_cb
        self.on_close_cb        = on_close_cb
        self._rec_kb_listener   = None
        self._rec_ms_listener   = None
        self._recording_hotkey  = False
        self._held_kb           = set()
        self._held_ms           = set()

        self.win = tk.Toplevel(parent)
        self.win.title("Einstellungen – Whisper PTT")
        self.win.configure(bg=C["bg"])
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        px, py = parent.winfo_x(), parent.winfo_y()
        self.win.geometry(f"450x600+{max(0, px-460)}+{py}")

        self._build()
        self._load_values()
        threading.Thread(target=self._detect_hw, daemon=True).start()

    def _on_close(self):
        self._stop_recorder()
        self.on_close_cb()
        self.win.destroy()

    # ── Notebook ───────────────────────────────────────────────────────────────

    def _build(self):
        main = tk.Frame(self.win, bg=C["bg"], padx=14, pady=10)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="⚙  Einstellungen",
                 bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        style = ttk.Style(self.win)
        style.theme_use("clam")
        style.configure("TNotebook",     background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=C["accent"], foreground=C["text"],
                        padding=(12,4), font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", C["accent2"])],
                  foreground=[("selected", C["text"])])
        style.configure("TFrame", background=C["bg"])

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True, pady=(0,10))

        t1 = ttk.Frame(nb); nb.add(t1, text="  Allgemein  ")
        t2 = ttk.Frame(nb); nb.add(t2, text="  Audio / KI  ")
        t3 = ttk.Frame(nb); nb.add(t3, text="  Erweitert  ")

        self._tab_general(t1)
        self._tab_audio(t2)
        self._tab_advanced(t3)

        bot = tk.Frame(main, bg=C["bg"])
        bot.pack(fill="x")

        self.hw_info_lbl = tk.Label(bot, text="Prüfe Hardware...",
                                    bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 7), wraplength=240)
        self.hw_info_lbl.pack(side="left")

        tk.Button(bot, text="Abbrechen",
                  bg=C["btn_clear"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9),
                  command=self._on_close).pack(side="right", padx=(4,0))

        tk.Button(bot, text="✔  Speichern",
                  bg=C["btn_paste"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_paste"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9, "bold"),
                  command=self._save).pack(side="right")

    # ── Tab 1: Allgemein ───────────────────────────────────────────────────────

    def _tab_general(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        # ── Hotkey-Recorder ───────────────────────────────────────────────────
        _section(p, "Tastenkürzel / Maustaste (Hotkey)")
        tk.Label(p, text="Keyboard-Tasten UND Maustasten (z.B. Daumentaste) werden erkannt.",
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=380, justify="left").pack(anchor="w")

        hk_row = tk.Frame(p, bg=C["bg"])
        hk_row.pack(fill="x", pady=(6,0))

        self.hotkey_var = tk.StringVar(value=cfg["hotkey"])
        tk.Entry(
            hk_row, textvariable=self.hotkey_var,
            bg=C["bg3"], fg=C["ready"],
            font=("Consolas", 11, "bold"),
            insertbackground=C["text"], relief="flat", bd=6,
            width=20, state="readonly",
        ).pack(side="left")

        self.rec_btn = tk.Button(
            hk_row, text="🔴 Aufnehmen",
            bg=C["record"], fg=C["text"], relief="flat",
            activebackground=_lighten(C["record"]), activeforeground=C["text"],
            cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8, "bold"),
            command=self._toggle_recorder,
        )
        self.rec_btn.pack(side="left", padx=6)

        tk.Button(
            hk_row, text="↺", bg=C["btn_set"], fg=C["dim"], relief="flat",
            activebackground=_lighten(C["btn_set"]), activeforeground=C["text"],
            cursor="hand2", padx=6, pady=4, font=("Segoe UI", 10),
            command=lambda: self.hotkey_var.set(DEFAULTS["hotkey"]),
        ).pack(side="left")

        self.hk_hint = tk.Label(p, text="", bg=C["bg"], fg=C["process"],
                                font=("Segoe UI", 8))
        self.hk_hint.pack(anchor="w", pady=(4,0))

        # Sprache
        _section(p, "Erkennungssprache")
        self.lang_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.lang_var,
                     values=list(LANGUAGES.keys()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,0))

        # Einfügemodus
        _section(p, "Text einfügen via")
        self.paste_var = tk.StringVar()
        for v, lbl in [("clipboard","Zwischenablage (Ctrl+V)  ← empfohlen"),
                       ("type",     "Direkt tippen (kein Clipboard, aber langsamer)")]:
            tk.Radiobutton(p, text=lbl, variable=self.paste_var, value=v,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Segoe UI", 9)).pack(anchor="w")

        # Sound + Transparenz
        _section(p, "Erscheinungsbild")
        self.sound_var = tk.BooleanVar()
        tk.Checkbutton(p, text="Audio-Feedback (Beep bei Start/Stop)",
                       variable=self.sound_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w")

        op_row = tk.Frame(p, bg=C["bg"])
        op_row.pack(fill="x", pady=(6,0))
        tk.Label(op_row, text="Transparenz:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.opacity_var = tk.DoubleVar()
        self.opacity_lbl = tk.Label(op_row, text="", bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 9), width=4)
        self.opacity_lbl.pack(side="right")
        tk.Scale(op_row, variable=self.opacity_var,
                 from_=0.4, to=1.0, resolution=0.05,
                 orient="horizontal", length=180,
                 bg=C["bg"], fg=C["text"], troughcolor=C["bg3"],
                 highlightthickness=0, bd=0, showvalue=False,
                 command=lambda v: self.opacity_lbl.config(text=f"{float(v):.0%}")
                 ).pack(side="left", padx=6)

    # ── Tab 2: Audio / KI ─────────────────────────────────────────────────────

    def _tab_audio(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        _section(p, "Berechnungsgerät")
        self.device_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.device_var,
                     values=list(DEVICES.keys()), state="readonly", width=30,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        self.dev_lbl = tk.Label(p, text="", bg=C["bg"], fg=C["ready"],
                                font=("Segoe UI", 8), wraplength=380, justify="left")
        self.dev_lbl.pack(anchor="w", pady=(0,8))

        _section(p, "Compute-Typ")
        self.compute_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.compute_var,
                     values=list(COMPUTE_TYPES.keys()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text="'Auto' wählt automatisch den optimalen Typ je nach Gerät.",
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8)).pack(anchor="w")

        _section(p, "Whisper-Modell")
        model_desc = {
            "tiny":     "~75 MB   | sehr schnell | einfacher Text",
            "base":     "~150 MB  | schnell      | gut für Alltag  ★",
            "small":    "~500 MB  | mittel       | bessere Genauigkeit",
            "medium":   "~1.5 GB  | langsam      | hohe Genauigkeit",
            "large-v2": "~3 GB    | sehr langsam | maximale Genauigkeit",
            "large-v3": "~3 GB    | sehr langsam | neueste Version",
        }
        self.model_var = tk.StringVar()
        for m in MODELS:
            row = tk.Frame(p, bg=C["bg"])
            row.pack(fill="x", pady=1)
            tk.Radiobutton(row, text=m, variable=self.model_var, value=m,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Consolas", 9, "bold"), width=9, anchor="w").pack(side="left")
            tk.Label(row, text=model_desc.get(m,""), bg=C["bg"], fg=C["dim"],
                     font=("Segoe UI", 8)).pack(side="left")

    # ── Tab 3: Erweitert ───────────────────────────────────────────────────────

    def _tab_advanced(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        _section(p, "Voice Activity Detection (VAD)")
        self.vad_var = tk.BooleanVar()
        tk.Checkbutton(p, text="VAD aktivieren (ignoriert Stille automatisch)",
                       variable=self.vad_var, bg=C["bg"], fg=C["text"],
                       selectcolor=C["bg3"], activebackground=C["bg"],
                       activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4,4))

        vad_row = tk.Frame(p, bg=C["bg"])
        vad_row.pack(anchor="w")
        tk.Label(vad_row, text="Stille-Schwelle:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.vad_ms_var = tk.IntVar()
        tk.Spinbox(vad_row, textvariable=self.vad_ms_var,
                   from_=100, to=2000, increment=50, width=6,
                   bg=C["bg3"], fg=C["text"], buttonbackground=C["accent"],
                   insertbackground=C["text"], relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Label(vad_row, text="ms", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 9)).pack(side="left")

        _section(p, "Beam Size  (Qualität vs. Geschwindigkeit)")
        beam_row = tk.Frame(p, bg=C["bg"])
        beam_row.pack(anchor="w", pady=(4,0))
        tk.Label(beam_row, text="Beam Size:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.beam_var = tk.IntVar()
        tk.Spinbox(beam_row, textvariable=self.beam_var,
                   from_=1, to=10, increment=1, width=4,
                   bg=C["bg3"], fg=C["text"], buttonbackground=C["accent"],
                   insertbackground=C["text"], relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Label(beam_row, text="(1=schnell, 5=Standard, 10=genau)",
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8)).pack(side="left")

        _section(p, "")
        tk.Button(p, text="↺  Alle Einstellungen auf Standard zurücksetzen",
                  bg=C["btn_clear"], fg=C["dim"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8),
                  command=self._reset).pack(anchor="w", pady=(10,0))

    # ── Werte laden ────────────────────────────────────────────────────────────

    def _load_values(self):
        self.hotkey_var.set(cfg["hotkey"])
        self.paste_var.set(cfg["paste_mode"])
        self.sound_var.set(cfg["sound_feedback"])
        self.opacity_var.set(cfg["opacity"])
        self.opacity_lbl.config(text=f"{cfg['opacity']:.0%}")
        self.model_var.set(cfg["model"])
        self.vad_var.set(cfg["vad_filter"])
        self.vad_ms_var.set(cfg["vad_silence_ms"])
        self.beam_var.set(cfg["beam_size"])
        self.lang_var.set(next((k for k,v in LANGUAGES.items() if v==cfg["language"]), "Automatisch"))
        self.device_var.set(next((k for k,v in DEVICES.items() if v==cfg["device"]), "Auto-Erkennung"))
        self.compute_var.set(next((k for k,v in COMPUTE_TYPES.items() if v==cfg["compute_type"]), "Auto"))

    def _detect_hw(self):
        devs  = detect_devices()
        parts = []
        parts.append(f"{'✅' if devs['cuda'] else '❌'} CUDA: {devs['cuda_name'] or 'nicht verfügbar'}")
        parts.append(f"{'✅' if devs['dml']  else '❌'} NPU/DirectML: {devs.get('npu_name','') or ('verfügbar' if devs['dml'] else 'nicht verfügbar')}")
        text = "   |   ".join(parts)
        try:
            self.dev_lbl.config(text=text)
            self.hw_info_lbl.config(text=text)
        except Exception: pass

    # ── Hotkey-Recorder (pynput – erkennt Keyboard + Maustasten) ──────────────

    def _toggle_recorder(self):
        if self._recording_hotkey:
            self._stop_recorder()
        else:
            self._start_recorder()

    def _start_recorder(self):
        self._recording_hotkey = True
        self._held_kb.clear()
        self._held_ms.clear()
        self.rec_btn.config(text="⏹  Stoppen", bg=C["process"])
        self.hotkey_var.set("▶  Tasten / Maustaste drücken ...")
        self.hk_hint.config(text="Modifier (Ctrl/Alt) + Taste ODER Maustaste")

        # Keyboard-Listener
        def on_kb_press(key):
            if not self._recording_hotkey: return
            kn = self._key_name(key)
            self._held_kb.add(kn)
            try: self.hotkey_var.set(self._build_combo())
            except Exception: pass

        def on_kb_release(key):
            if not self._recording_hotkey: return
            kn = self._key_name(key)
            combo = self._build_combo()
            # Wenn mindestens 1 nicht-modifier Taste oder Maustaste dabei
            if any(k not in {"ctrl","alt","shift","cmd","windows"} for k in (self._held_kb | self._held_ms)):
                try: self.hotkey_var.set(combo)
                except Exception: pass
                self.win.after(0, self._stop_recorder)
            self._held_kb.discard(kn)

        # Mouse-Listener
        def on_ms_click(x, y, button, pressed):
            if not self._recording_hotkey: return
            btn_name = MOUSE_BTN_NAMES.get(button, f"mouse_{button}")
            if pressed:
                self._held_ms.add(btn_name)
                try: self.hotkey_var.set(self._build_combo())
                except Exception: pass
            else:
                combo = self._build_combo()
                try: self.hotkey_var.set(combo)
                except Exception: pass
                self._held_ms.discard(btn_name)
                self.win.after(0, self._stop_recorder)

        self._rec_kb_listener = pynput_kb.Listener(
            on_press=on_kb_press, on_release=on_kb_release, daemon=True
        )
        self._rec_ms_listener = pynput_ms.Listener(
            on_click=on_ms_click, daemon=True
        )
        self._rec_kb_listener.start()
        self._rec_ms_listener.start()

    def _stop_recorder(self):
        self._recording_hotkey = False
        for lst in (self._rec_kb_listener, self._rec_ms_listener):
            if lst:
                try: lst.stop()
                except Exception: pass
        self._rec_kb_listener = None
        self._rec_ms_listener = None
        try:
            self.rec_btn.config(text="🔴 Aufnehmen", bg=C["record"])
            self.hk_hint.config(text="")
        except Exception: pass

    @staticmethod
    def _key_name(key) -> str:
        try:
            return key.char.lower()
        except AttributeError:
            name = str(key).replace("Key.", "").lower()
            for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                             ("alt_l","alt"),("alt_r","alt"),
                             ("alt_gr","alt"),
                             ("shift_l","shift"),("shift_r","shift"),
                             ("cmd_l","cmd"),("cmd_r","cmd")]:
                name = name.replace(old, new)
            return name

    def _build_combo(self) -> str:
        priority = ["ctrl","alt","shift","cmd","windows"]
        kb_mods  = [k for k in priority if k in self._held_kb]
        kb_other = [k for k in self._held_kb if k not in priority]
        ms_keys  = sorted(self._held_ms)
        return "+".join(kb_mods + kb_other + ms_keys)

    # ── Speichern ──────────────────────────────────────────────────────────────

    def _save(self):
        self._stop_recorder()
        hk = self.hotkey_var.get()
        if "▶" in hk or not hk:
            hk = DEFAULTS["hotkey"]
        cfg["hotkey"]         = hk
        cfg["language"]       = LANGUAGES.get(self.lang_var.get())
        cfg["paste_mode"]     = self.paste_var.get()
        cfg["sound_feedback"] = self.sound_var.get()
        cfg["opacity"]        = round(self.opacity_var.get(), 2)
        cfg["model"]          = self.model_var.get()
        cfg["device"]         = DEVICES.get(self.device_var.get(), "auto")
        cfg["compute_type"]   = COMPUTE_TYPES.get(self.compute_var.get(), "auto")
        cfg["vad_filter"]     = self.vad_var.get()
        cfg["vad_silence_ms"] = self.vad_ms_var.get()
        cfg["beam_size"]      = self.beam_var.get()
        save_settings()
        self.on_save_cb()
        self.win.destroy()

    def _reset(self):
        if messagebox.askyesno("Zurücksetzen",
                               "Alle Einstellungen zurücksetzen?",
                               parent=self.win):
            cfg.update(DEFAULTS)
            self._load_values()

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_settings()

    stream = sd.InputStream(
        samplerate=16000, channels=1, dtype="float32",
        callback=audio_callback, blocksize=512,
    )

    root = tk.Tk()
    app  = WhisperPTTApp(root)

    with stream:
        root.mainloop()

if __name__ == "__main__":
    main()
