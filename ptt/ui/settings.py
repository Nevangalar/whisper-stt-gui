"""
ptt/ui/settings.py – Settings dialog (SettingsWindow class).
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput import keyboard as pynput_kb
from pynput import mouse    as pynput_ms

import ptt.state as state
from ptt.constants import (
    C, DEFAULTS, TRANSLATIONS, UI_LANGUAGES, MODELS,
    DEVICES, COMPUTE_TYPES, MOUSE_BTN_NAMES, _recog_lang_labels,
)
from ptt.config import T, save_settings, get_models_dir
from ptt.hardware import detect_devices
from ptt.ui.helpers import _lighten, _section, _flat_btn, _scrollable_tab


# ═══════════════════════════════════════════════════════════════════════════════
#  Settings Window
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsWindow:

    def __init__(self, parent, on_save_cb, on_close_cb):
        self.parent            = parent
        self.on_save_cb        = on_save_cb
        self.on_close_cb       = on_close_cb
        self._rec_kb_listener  = None
        self._rec_ms_listener  = None
        self._recording_hotkey = False
        self._held_kb          = set()
        self._held_ms          = set()
        self._model_snapshot   = (
            state.cfg["model"], state.cfg["device"], state.cfg["compute_type"],
            state.cfg.get("models_dir", "")
        )

        self.win = tk.Toplevel(parent)
        self.win.title(T("settings_win_title"))
        self.win.configure(bg=C["bg"])
        self.win.attributes("-topmost", True)
        self.win.resizable(False, True)
        self.win.minsize(460, 480)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        px, py = parent.winfo_x(), parent.winfo_y()
        self.win.geometry(f"460x720+{max(0, px-470)}+{py}")

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

        tk.Label(main, text=T("settings_title"),
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

        t1 = ttk.Frame(nb); nb.add(t1, text=T("tab_general"))
        t2 = ttk.Frame(nb); nb.add(t2, text=T("tab_audio"))
        t3 = ttk.Frame(nb); nb.add(t3, text=T("tab_advanced"))

        self._tab_general(t1)
        self._tab_audio(t2)
        self._tab_advanced(t3)

        bot = tk.Frame(main, bg=C["bg"])
        bot.pack(fill="x")

        self.hw_info_lbl = tk.Label(bot, text=T("checking_hw"),
                                    bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 7), wraplength=240)
        self.hw_info_lbl.pack(side="left")

        tk.Button(bot, text=T("btn_cancel"),
                  bg=C["btn_clear"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9),
                  command=self._on_close).pack(side="right", padx=(4,0))

        tk.Button(bot, text=T("btn_save"),
                  bg=C["btn_paste"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_paste"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9, "bold"),
                  command=self._save).pack(side="right")

    # ── Tab 1: General ─────────────────────────────────────────────────────────

    def _tab_general(self, frame):
        p = _scrollable_tab(frame)

        # Hotkey recorder
        _section(p, "sec_hotkey")
        tk.Label(p, text=T("hotkey_hint"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        hk_row = tk.Frame(p, bg=C["bg"])
        hk_row.pack(fill="x", pady=(6,0))

        self.hotkey_var = tk.StringVar(value=state.cfg["hotkey"])
        tk.Entry(hk_row, textvariable=self.hotkey_var,
                 bg=C["bg3"], fg=C["ready"],
                 font=("Consolas", 11, "bold"),
                 insertbackground=C["text"], relief="flat", bd=6,
                 width=20, state="readonly").pack(side="left")

        self.rec_btn = tk.Button(
            hk_row, text=T("btn_record"),
            bg=C["record"], fg=C["text"], relief="flat",
            activebackground=_lighten(C["record"]), activeforeground=C["text"],
            cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8, "bold"),
            command=self._toggle_recorder,
        )
        self.rec_btn.pack(side="left", padx=6)

        tk.Button(hk_row, text="↺", bg=C["btn_set"], fg=C["dim"], relief="flat",
                  activebackground=_lighten(C["btn_set"]), activeforeground=C["text"],
                  cursor="hand2", padx=6, pady=4, font=("Segoe UI", 10),
                  command=lambda: self.hotkey_var.set(DEFAULTS["hotkey"])
                  ).pack(side="left")

        self.hk_hint = tk.Label(p, text="", bg=C["bg"], fg=C["process"],
                                font=("Segoe UI", 8))
        self.hk_hint.pack(anchor="w", pady=(4,0))

        # UI language
        _section(p, "sec_ui_lang")
        self.ui_lang_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.ui_lang_var,
                     values=list(UI_LANGUAGES.keys()), state="readonly", width=20,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("ui_lang_note"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        # Recognition language (input)
        _section(p, "sec_rec_lang")
        self.lang_var = tk.StringVar()
        self._recog_labels = _recog_lang_labels(state.cfg["ui_lang"])
        ttk.Combobox(p, textvariable=self.lang_var,
                     values=list(self._recog_labels.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,0))

        # Output language / translation
        _section(p, "sec_output_lang")
        self.out_lang_var = tk.StringVar()
        self._out_lang_options = {
            "same": T("output_same"),
            "en":   _recog_lang_labels(state.cfg["ui_lang"])["en"],
        }
        ttk.Combobox(p, textvariable=self.out_lang_var,
                     values=list(self._out_lang_options.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("output_lang_note"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        # Paste mode
        _section(p, "sec_paste")
        self.paste_var = tk.StringVar()
        for v, key in [("clipboard","paste_clipboard"), ("type","paste_type")]:
            tk.Radiobutton(p, text=T(key), variable=self.paste_var, value=v,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Segoe UI", 9)).pack(anchor="w")

        # Appearance
        _section(p, "sec_appearance")
        self.sound_var = tk.BooleanVar()
        tk.Checkbutton(p, text=T("sound_feedback"), variable=self.sound_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w")

        op_row = tk.Frame(p, bg=C["bg"])
        op_row.pack(fill="x", pady=(6,0))
        tk.Label(op_row, text=T("transparency"), bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.opacity_var = tk.DoubleVar()
        self.opacity_lbl = tk.Label(op_row, text="", bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 9), width=4)
        self.opacity_lbl.pack(side="right")
        tk.Scale(op_row, variable=self.opacity_var,
                 from_=0.4, to=1.0, resolution=0.05, orient="horizontal", length=180,
                 bg=C["bg"], fg=C["text"], troughcolor=C["bg3"],
                 highlightthickness=0, bd=0, showvalue=False,
                 command=lambda v: self.opacity_lbl.config(text=f"{float(v):.0%}")
                 ).pack(side="left", padx=6)

    # ── Tab 2: Audio / AI ──────────────────────────────────────────────────────

    def _tab_audio(self, frame):
        p = _scrollable_tab(frame)

        _section(p, "sec_device")
        self.device_var = tk.StringVar()
        dev_labels = list(DEVICES.values())
        ttk.Combobox(p, textvariable=self.device_var,
                     values=dev_labels, state="readonly", width=30,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        self.dev_lbl = tk.Label(p, text="", bg=C["bg"], fg=C["ready"],
                                font=("Segoe UI", 8), wraplength=390, justify="left")
        self.dev_lbl.pack(anchor="w", pady=(0,8))

        _section(p, "sec_compute")
        self.compute_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.compute_var,
                     values=list(COMPUTE_TYPES.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("compute_note"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8)).pack(anchor="w")

        _section(p, "sec_model")
        model_desc_keys = {
            "tiny": "model_tiny", "base": "model_base", "small": "model_small",
            "medium": "model_medium", "large-v2": "model_large_v2", "large-v3": "model_large_v3",
        }
        self.model_var = tk.StringVar()
        for m in MODELS:
            row = tk.Frame(p, bg=C["bg"])
            row.pack(fill="x", pady=1)
            tk.Radiobutton(row, text=m, variable=self.model_var, value=m,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Consolas", 9, "bold"), width=9, anchor="w").pack(side="left")
            tk.Label(row, text=T(model_desc_keys.get(m,"")), bg=C["bg"], fg=C["dim"],
                     font=("Segoe UI", 8)).pack(side="left")

    # ── Tab 3: Advanced ────────────────────────────────────────────────────────

    def _tab_advanced(self, frame):
        p = _scrollable_tab(frame)

        _section(p, "sec_vad")
        self.vad_var = tk.BooleanVar()
        tk.Checkbutton(p, text=T("vad_enable"), variable=self.vad_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4,4))

        vad_row = tk.Frame(p, bg=C["bg"])
        vad_row.pack(anchor="w")
        tk.Label(vad_row, text=T("vad_threshold"), bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.vad_ms_var = tk.IntVar()
        tk.Spinbox(vad_row, textvariable=self.vad_ms_var,
                   from_=100, to=2000, increment=50, width=6,
                   bg=C["bg3"], fg=C["text"], buttonbackground=C["accent"],
                   insertbackground=C["text"], relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Label(vad_row, text="ms", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 9)).pack(side="left")

        _section(p, "sec_beam")
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
        tk.Label(beam_row, text=T("beam_hint"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8)).pack(side="left")

        _section(p, "sec_models_dir")
        self.models_dir_var = tk.StringVar()
        dir_row = tk.Frame(p, bg=C["bg"])
        dir_row.pack(fill="x", anchor="w", pady=(4,0))
        tk.Entry(dir_row, textvariable=self.models_dir_var, width=32,
                 bg=C["bg3"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)
        tk.Button(dir_row, text=T("btn_browse"), relief="flat", cursor="hand2",
                  bg=C["accent"], fg=C["text"], activebackground=_lighten(C["accent"]),
                  activeforeground=C["text"], padx=6, pady=2, font=("Segoe UI", 9),
                  command=self._browse_models_dir).pack(side="left", padx=(6,0))
        tk.Label(p, text=T("models_dir_hint"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(2,0))

        _section(p, "")
        tk.Button(p, text=T("btn_reset"),
                  bg=C["btn_clear"], fg=C["dim"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8),
                  command=self._reset).pack(anchor="w", pady=(10,0))

    # ── Load values ────────────────────────────────────────────────────────────

    def _load_values(self):
        self.hotkey_var.set(state.cfg["hotkey"])
        self.paste_var.set(state.cfg["paste_mode"])
        self.sound_var.set(state.cfg["sound_feedback"])
        self.opacity_var.set(state.cfg["opacity"])
        self.opacity_lbl.config(text=f"{state.cfg['opacity']:.0%}")
        self.model_var.set(state.cfg["model"])
        self.vad_var.set(state.cfg["vad_filter"])
        self.vad_ms_var.set(state.cfg["vad_silence_ms"])
        self.beam_var.set(state.cfg["beam_size"])

        # UI language
        ui_lbl = next((k for k,v in UI_LANGUAGES.items() if v==state.cfg.get("ui_lang","en")), "English")
        self.ui_lang_var.set(ui_lbl)

        # Recognition language (input)
        rl = _recog_lang_labels(state.cfg["ui_lang"])
        rec_code = state.cfg.get("language") or "auto"
        self.lang_var.set(rl.get(rec_code, rl["auto"]))

        # Output language
        out_opts = {"same": T("output_same"), "en": rl["en"]}
        out_code = state.cfg.get("output_language", "same")
        self.out_lang_var.set(out_opts.get(out_code, out_opts["same"]))

        # Device – map legacy "dml" to "npu"
        dev_cfg = "npu" if state.cfg.get("device") == "dml" else state.cfg.get("device", "auto")
        self.device_var.set(DEVICES.get(dev_cfg, "Auto"))

        # Compute type
        self.compute_var.set(COMPUTE_TYPES.get(state.cfg["compute_type"], "Auto"))

        # Models directory
        self.models_dir_var.set(state.cfg.get("models_dir", ""))

    def _browse_models_dir(self):
        chosen = filedialog.askdirectory(
            title=T("sec_models_dir"),
            initialdir=self.models_dir_var.get() or str(get_models_dir()),
            parent=self.win,
        )
        if chosen:
            self.models_dir_var.set(chosen)

    def _detect_hw(self):
        devs  = detect_devices()
        na    = T("hw_not_available")
        av    = T("hw_available")
        parts = [
            f"{'✅' if devs['cuda'] else '❌'} CUDA: {devs['cuda_name'] or na}",
            f"{'✅' if devs['npu']  else '❌'} NPU:  {devs.get('npu_name','') or (av if devs['npu'] else na)}",
        ]
        text = "   |   ".join(parts)
        try:
            self.dev_lbl.config(text=text)
            self.hw_info_lbl.config(text=text)
        except Exception:
            pass

    # ── Hotkey recorder ────────────────────────────────────────────────────────

    def _toggle_recorder(self):
        if self._recording_hotkey: self._stop_recorder()
        else:                      self._start_recorder()

    def _start_recorder(self):
        self._recording_hotkey = True
        self._held_kb.clear(); self._held_ms.clear()
        self.rec_btn.config(text=T("btn_stop_record"), bg=C["process"])
        self.hotkey_var.set(T("recorder_prompt"))
        self.hk_hint.config(text=T("recorder_hint"))

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
            if any(k not in {"ctrl","alt","shift","cmd","windows"}
                   for k in (self._held_kb | self._held_ms)):
                try: self.hotkey_var.set(combo)
                except Exception: pass
                self.win.after(0, self._stop_recorder)
            self._held_kb.discard(kn)

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
            on_press=on_kb_press, on_release=on_kb_release, daemon=True)
        self._rec_ms_listener = pynput_ms.Listener(on_click=on_ms_click, daemon=True)
        self._rec_kb_listener.start()
        self._rec_ms_listener.start()

    def _stop_recorder(self):
        self._recording_hotkey = False
        for lst in (self._rec_kb_listener, self._rec_ms_listener):
            if lst:
                try: lst.stop()
                except Exception: pass
        self._rec_kb_listener = None; self._rec_ms_listener = None
        try:
            self.rec_btn.config(text=T("btn_record"), bg=C["record"])
            self.hk_hint.config(text="")
        except Exception: pass

    @staticmethod
    def _key_name(key) -> str:
        try: return key.char.lower()
        except AttributeError:
            name = str(key).replace("Key.", "").lower()
            for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                             ("alt_l","alt"),("alt_r","alt"),("alt_gr","alt"),
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

    # ── Save ───────────────────────────────────────────────────────────────────

    def _save(self):
        self._stop_recorder()
        hk = self.hotkey_var.get()
        if "▶" in hk or not hk: hk = DEFAULTS["hotkey"]
        state.cfg["hotkey"]         = hk
        state.cfg["ui_lang"]        = UI_LANGUAGES.get(self.ui_lang_var.get(), "en")

        # Resolve recognition language (label → code)
        rl      = _recog_lang_labels(state.cfg["ui_lang"])
        sel_lbl = self.lang_var.get()
        state.cfg["language"] = next((code for code, lbl in rl.items() if lbl == sel_lbl), None)

        # Resolve output language (label → code)
        out_opts = {"same": T("output_same"), "en": rl["en"]}
        sel_out  = self.out_lang_var.get()
        state.cfg["output_language"] = next(
            (code for code, lbl in out_opts.items() if lbl == sel_out), "same")

        state.cfg["paste_mode"]     = self.paste_var.get()
        state.cfg["sound_feedback"] = self.sound_var.get()
        state.cfg["opacity"]        = round(self.opacity_var.get(), 2)
        state.cfg["model"]          = self.model_var.get()
        state.cfg["device"]         = next(
            (k for k,v in DEVICES.items() if v==self.device_var.get()), "auto")
        state.cfg["compute_type"]   = next(
            (k for k,v in COMPUTE_TYPES.items() if v==self.compute_var.get()), "auto")
        state.cfg["vad_filter"]     = self.vad_var.get()
        state.cfg["vad_silence_ms"] = self.vad_ms_var.get()
        state.cfg["beam_size"]      = self.beam_var.get()
        state.cfg["models_dir"]     = self.models_dir_var.get().strip()
        save_settings()
        need_reload = (
            state.cfg["model"], state.cfg["device"], state.cfg["compute_type"],
            state.cfg.get("models_dir", "")
        ) != self._model_snapshot
        self.on_save_cb(need_reload)
        self.win.destroy()

    def _reset(self):
        if messagebox.askyesno(T("reset_confirm_title"), T("reset_confirm_msg"),
                               parent=self.win):
            state.cfg.update(DEFAULTS)
            self._load_values()
