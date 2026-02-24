"""
ptt/ui/app.py – Main overlay window (WhisperPTTApp class).
"""

import time
import threading
import tkinter as tk
from tkinter import messagebox

import pyperclip
import pyautogui

import ptt.state as state
from ptt.constants import C
from ptt.config import T, save_settings
from ptt.audio import restart_audio_stream
from ptt.hotkey import start_ptt_listener, stop_ptt_listener
from ptt.model_manager import load_model
from ptt.ui.helpers import _flat_btn, _make_text_widget
from ptt.ui.settings import SettingsWindow


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Overlay
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperPTTApp:

    STATUS_COLORS = {
        "idle":    C["idle"],    "loading": C["process"],
        "ready":   C["ready"],   "record":  C["record"],
        "process": C["process"], "error":   C["record"],
    }

    def __init__(self, root: tk.Tk):
        self.root          = root
        self._minimized    = False
        self._settings_win = None
        self._clean_texts  = []

        self._build_window()
        self._build_ui()
        self._poll_queue()
        self._animate_meter()

        threading.Thread(
            target=load_model,
            args=(lambda s, m: state.ui_queue.put(("status", s, m)),),
            daemon=True,
        ).start()
        threading.Thread(target=start_ptt_listener, daemon=True).start()

    def _build_window(self):
        self.root.title("Whisper PTT")
        self.root.configure(bg=C["bg"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", state.cfg["opacity"])
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.update_idletasks()
        if state.cfg["window_x"] >= 0:
            self.root.geometry(f"+{state.cfg['window_x']}+{state.cfg['window_y']}")
        else:
            sw = self.root.winfo_screenwidth()
            self.root.geometry(f"+{sw - 370}+20")

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=C["bg"],
                         highlightbackground=C["sep"], highlightthickness=1)
        outer.pack(fill="both", expand=True)

        # Title bar – drag only here
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

        # Content – no drag
        self.content = tk.Frame(outer, bg=C["bg"], padx=10, pady=8)
        self.content.pack(fill="both", expand=True)

        # Status row
        row = tk.Frame(self.content, bg=C["bg"])
        row.pack(fill="x", pady=(0, 5))

        self.dot_cv = tk.Canvas(row, width=14, height=14, bg=C["bg"],
                                highlightthickness=0)
        self.dot_cv.pack(side="left")
        self._dot = self.dot_cv.create_oval(2, 2, 12, 12, fill=C["idle"], outline="")

        self.status_lbl = tk.Label(row, text=T("initializing"),
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=(6, 0))

        gear = tk.Label(row, text="⚙", bg=C["bg"], fg=C["dim"],
                        font=("Segoe UI", 13), cursor="hand2")
        gear.pack(side="right")
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>",    lambda e: gear.config(fg=C["text"]))
        gear.bind("<Leave>",    lambda e: gear.config(fg=C["dim"]))

        self.mic_btn = tk.Label(row, text="🎤↺", bg=C["bg"], fg=C["dim"],
                                font=("Segoe UI", 11), cursor="hand2")
        self.mic_btn.pack(side="right", padx=(0, 2))
        self.mic_btn.bind("<Button-1>", lambda e: self._retry_mic())
        self.mic_btn.bind("<Enter>",    lambda e: self.mic_btn.config(fg=C["process"]))
        self.mic_btn.bind("<Leave>",    lambda e: self.mic_btn.config(fg=C["dim"]))

        self.hotkey_lbl = tk.Label(row, text=state.cfg["hotkey"],
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 8))
        self.hotkey_lbl.pack(side="right", padx=(0, 4))

        # Voice meter
        tk.Label(self.content, text=T("microphone"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.meter_cv = tk.Canvas(self.content, height=16, bg=C["bg3"],
                                  highlightthickness=1, highlightbackground=C["sep"])
        self.meter_cv.pack(fill="x", pady=(2, 8))
        self._mbar = self.meter_cv.create_rectangle(0, 0, 0, 16,
                                                    fill=C["meter_low"], outline="")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # Panel 1: Recognized text
        tk.Label(self.content, text=T("recognized_text"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.recog_txt = _make_text_widget(self.content, height=5)

        br1 = tk.Frame(self.content, bg=C["bg"])
        br1.pack(fill="x", pady=(0, 6))
        _flat_btn(br1, "btn_copy",  C["btn_copy"],  self._copy_recog ).pack(side="left", padx=(0,4))
        _flat_btn(br1, "btn_paste", C["btn_paste"], self._paste_recog).pack(side="left", padx=(0,4))
        _flat_btn(br1, "btn_clear", C["btn_clear"], self._clear_recog).pack(side="right")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # Panel 2: Debug / Log
        tk.Label(self.content, text=T("debug_log"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.debug_txt = _make_text_widget(self.content, height=4)
        self.debug_txt.config(fg=C["dim"])

        br2 = tk.Frame(self.content, bg=C["bg"])
        br2.pack(fill="x", pady=(0, 0))
        _flat_btn(br2, "btn_clear_log", C["btn_clear"], self._clear_debug).pack(side="right")

    # ── Drag (title bar only) ──────────────────────────────────────────────────

    def _drag_start(self, e): self._dx = e.x; self._dy = e.y
    def _drag_motion(self, e):
        x = self.root.winfo_x() + (e.x - self._dx)
        y = self.root.winfo_y() + (e.y - self._dy)
        self.root.geometry(f"+{x}+{y}")
    def _drag_end(self, e):
        state.cfg["window_x"] = self.root.winfo_x()
        state.cfg["window_y"] = self.root.winfo_y()
        save_settings()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _copy_recog(self):
        try:    text = self.recog_txt.get("sel.first", "sel.last")
        except: text = self._clean_texts[-1] if self._clean_texts else \
                        self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self._flash(T("flash_copied"))

    def _paste_recog(self):
        text = self._clean_texts[-1] if self._clean_texts else \
               self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self.root.after(150, lambda: pyautogui.hotkey("ctrl", "v"))
            self._flash(T("flash_pasted"))

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

    def _retry_mic(self):
        self.mic_btn.config(fg=C["process"])
        self._set_status("process", T("mic_restart"))
        threading.Thread(target=restart_audio_stream, daemon=True).start()

    def _toggle_min(self):
        self._minimized = not self._minimized
        if self._minimized: self.content.pack_forget()
        else:               self.content.pack(fill="both", expand=True)

    def _on_close(self):
        state.cfg["window_x"] = self.root.winfo_x()
        state.cfg["window_y"] = self.root.winfo_y()
        save_settings()
        stop_ptt_listener()
        if state._audio_stream is not None:
            try: state._audio_stream.stop(); state._audio_stream.close()
            except Exception: pass
        self.root.destroy()

    # ── Queue polling ──────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                msg = state.ui_queue.get_nowait()
                if msg[0] == "status":
                    self._set_status(msg[1], msg[2])
                elif msg[0] == "recognized":
                    self._append_recognized(msg[1])
                elif msg[0] == "log":
                    self._append_log(msg[1])
                elif msg[0] == "mic_ok":
                    self.mic_btn.config(fg=C["dim"])
                elif msg[0] in ("mic_error", "mic_stream_error"):
                    self.mic_btn.config(fg=C["record"])
                    self._append_log(f"🎤 Mic error: {msg[1]}")
                elif msg[0] == "mic_permission_dialog":
                    self._show_permission_hint()
        except Exception:
            pass
        self.root.after(50, self._poll_queue)

    def _show_permission_hint(self):
        messagebox.showinfo(T("mic_perm_title"), T("mic_perm_msg"), parent=self.root)

    def _set_status(self, state_key, text):
        color = self.STATUS_COLORS.get(state_key, C["idle"])
        self.dot_cv.itemconfig(self._dot, fill=color)
        self.status_lbl.config(text=text,
                               fg=color if state_key not in ("ready","idle") else C["dim"])
        if state_key == "record": self._pulse(color)

    def _pulse(self, color, step=0):
        if not state.recording:
            self.dot_cv.itemconfig(self._dot, fill=color); return
        self.dot_cv.itemconfig(self._dot, fill=color if step%2==0 else C["bg2"])
        self.root.after(400, lambda: self._pulse(color, step+1))

    def _append_recognized(self, text: str):
        self._clean_texts.append(text)
        self.recog_txt.config(state="normal")
        if self.recog_txt.index("end-1c") != "1.0":
            self.recog_txt.insert("end", "\n─────\n")
        self.recog_txt.insert("end", text)
        self.recog_txt.see("end")

    def _append_log(self, text: str):
        self.debug_txt.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.debug_txt.insert("end", f"[{ts}] {text}\n")
        self.debug_txt.see("end")

    def _animate_meter(self):
        try:
            w  = self.meter_cv.winfo_width() or 300
            bw = int(w * state.current_volume)
            lv = state.current_volume
            c  = C["meter_low"] if lv < 0.5 else C["meter_mid"] if lv < 0.8 else C["meter_high"]
            self.meter_cv.coords(self._mbar, 0, 0, bw, 16)
            self.meter_cv.itemconfig(self._mbar, fill=c)
        except Exception: pass
        self.root.after(40, self._animate_meter)

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self):
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
        self._settings_win = None

    def _on_settings_saved(self, need_model_reload: bool):
        self._settings_win = None
        self.hotkey_lbl.config(text=state.cfg["hotkey"])
        self.root.attributes("-alpha", state.cfg["opacity"])
        threading.Thread(target=start_ptt_listener, daemon=True).start()
        if need_model_reload:
            threading.Thread(
                target=load_model,
                args=(lambda s, m: state.ui_queue.put(("status", s, m)),),
                daemon=True,
            ).start()
