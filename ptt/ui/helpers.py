"""
ptt/ui/helpers.py – Reusable tkinter widget factory functions.
"""

import tkinter as tk

from ptt.constants import C, TRANSLATIONS
from ptt.config import T

# ─── Color helper ──────────────────────────────────────────────────────────────

def _lighten(hex_c: str, f=1.3) -> str:
    h = hex_c.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(255,int(r*f)), min(255,int(g*f)), min(255,int(b*f)))

# ─── Section header ────────────────────────────────────────────────────────────

def _section(parent, key):
    text = T(key) if key in TRANSLATIONS else key
    if text:
        tk.Label(parent, text=text, bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(10,0))
    tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", pady=(2,4))

# ─── Flat button ───────────────────────────────────────────────────────────────

def _flat_btn(parent, key, color, cmd, padx=8, pady=4):
    text = T(key) if key in TRANSLATIONS else key
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

# ─── Text widget ───────────────────────────────────────────────────────────────

def _make_text_widget(parent, height=5):
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
    txt.bind("<ButtonPress-1>",   lambda e: None)
    txt.bind("<B1-Motion>",       lambda e: None)
    txt.bind("<ButtonRelease-1>", lambda e: None)
    return txt

# ─── Scrollable tab frame ──────────────────────────────────────────────────────

def _scrollable_tab(frame):
    """Return an inner Frame inside a scrollable Canvas for a ttk.Notebook tab."""
    canvas = tk.Canvas(frame, bg=C["bg"], highlightthickness=0, bd=0)
    vsb    = tk.Scrollbar(frame, orient="vertical", command=canvas.yview,
                          bg=C["bg"], troughcolor=C["bg2"], relief="flat", bd=0, width=10)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner  = tk.Frame(canvas, bg=C["bg"], padx=14, pady=8)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_canvas_resize(e):
        canvas.itemconfig(win_id, width=e.width)
    canvas.bind("<Configure>", _on_canvas_resize)

    def _on_inner_resize(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_resize)

    def _wheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _wheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return inner
