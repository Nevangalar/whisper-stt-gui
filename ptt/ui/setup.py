"""
ptt/ui/setup.py – First-time setup dialog for model directory selection.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import ptt.state as state
from ptt.constants import C, MODEL_CACHE_DIR, DEFAULTS
from ptt.config import T, save_settings


def show_first_setup():
    """
    Show initial setup dialog if no settings.json exists.
    User can:
    1. Use default models/ directory
    2. Browse to existing models folder
    3. Create new folder
    Returns True if setup completed, False if user cancelled.
    """
    root = tk.Tk()
    root.title("Whisper PTT – First Setup")
    root.geometry("500x300")
    root.configure(bg=C["bg"])
    root.resizable(False, False)
    
    # Make it modal
    root.attributes("-topmost", True)
    
    result = {"done": False}
    
    # Title
    tk.Label(
        root,
        text="🎤 Whisper PTT – First Setup",
        bg=C["accent"],
        fg=C["text"],
        font=("Segoe UI", 12, "bold"),
        pady=10,
    ).pack(fill="x")
    
    # Content
    content = tk.Frame(root, bg=C["bg"], padx=20, pady=20)
    content.pack(fill="both", expand=True)
    
    tk.Label(
        content,
        text="Where should Whisper models be stored?\n\n"
        "Models are large (~1-3 GB per model) and downloaded on first use.",
        bg=C["bg"],
        fg=C["text"],
        font=("Segoe UI", 10),
        justify="left",
    ).pack(fill="x", pady=(0, 20))
    
    selected_dir = {"path": MODEL_CACHE_DIR}
    
    # Get exe directory (for portable installs, or app directory if running from source)
    exe_dir = os.path.dirname(sys.executable)
    if not os.path.exists(exe_dir) or exe_dir == "":
        exe_dir = os.getcwd()  # Fallback to current working directory
    
    def _use_default():
        selected_dir["path"] = MODEL_CACHE_DIR
        state.cfg["models_dir"] = ""
        save_settings()
        result["done"] = True
        root.destroy()
    
    def _browse():
        path = filedialog.askdirectory(
            title="Select or create models directory",
            initialdir=exe_dir,
        )
        if path:
            selected_dir["path"] = path
            state.cfg["models_dir"] = path
            save_settings()
            result["done"] = True
            root.destroy()
    
    def _create_new():
        path = filedialog.askdirectory(
            title="Choose location for new models directory",
            initialdir=exe_dir,
        )
        if path:
            new_path = Path(path) / "whisper-models"
            try:
                new_path.mkdir(parents=True, exist_ok=True)
                selected_dir["path"] = str(new_path)
                state.cfg["models_dir"] = str(new_path)
                save_settings()
                messagebox.showinfo(
                    "Success",
                    f"Models directory created:\n{new_path}",
                )
                result["done"] = True
                root.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory:\n{e}")
    
    # Buttons
    btn_frame = tk.Frame(content, bg=C["bg"])
    btn_frame.pack(fill="x", pady=(20, 0))
    
    btn_default = tk.Button(
        btn_frame,
        text=f"📁 Use Default\n({MODEL_CACHE_DIR})",
        command=_use_default,
        bg=C["btn_set"],
        fg=C["text"],
        font=("Segoe UI", 9),
        padx=10,
        pady=8,
        relief="flat",
        cursor="hand2",
    )
    btn_default.pack(side="left", padx=5, fill="both", expand=True)
    
    btn_browse = tk.Button(
        btn_frame,
        text="🔍 Browse\nExisting Folder",
        command=_browse,
        bg=C["btn_set"],
        fg=C["text"],
        font=("Segoe UI", 9),
        padx=10,
        pady=8,
        relief="flat",
        cursor="hand2",
    )
    btn_browse.pack(side="left", padx=5, fill="both", expand=True)
    
    btn_new = tk.Button(
        btn_frame,
        text="➕ Create New\nFolder",
        command=_create_new,
        bg=C["btn_set"],
        fg=C["text"],
        font=("Segoe UI", 9),
        padx=10,
        pady=8,
        relief="flat",
        cursor="hand2",
    )
    btn_new.pack(side="left", padx=5, fill="both", expand=True)
    
    root.mainloop()
    return result["done"]
