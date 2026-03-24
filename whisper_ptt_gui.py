#!/usr/bin/env python3
"""
Whisper PTT – entry point
=========================
Thin launcher: devnull redirect (PyInstaller) + main().
All application logic lives in the ptt/ package.
"""

import os
import sys
import signal
import threading
import tkinter as tk

# PyInstaller windowed builds set sys.stdout/stderr to None; redirect to devnull
# so that third-party libraries (openvino_genai, tqdm, …) don't crash on .write()
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from ptt import state
from ptt.config import load_settings
from ptt.audio import start_audio_stream
from ptt.ui.app import WhisperPTTApp
from ptt.constants import SETTINGS_FILE


def main():
    # On Linux, Ctrl+C sends SIGINT and would kill the process even while the
    # tkinter window has focus. Ignore it so the user can copy text normally.
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    load_settings()
    
    # Show first-time setup dialog if no settings.json exists
    if not SETTINGS_FILE.exists():
        from ptt.ui.setup import show_first_setup
        if not show_first_setup():
            # User cancelled setup
            return

    root = tk.Tk()
    root.withdraw()  # Hide until app is ready
    app  = WhisperPTTApp(root)  # noqa: F841

    threading.Thread(target=start_audio_stream, daemon=True).start()

    root.deiconify()  # Show after app initialization
    root.mainloop()

    if state._audio_stream is not None:
        try: state._audio_stream.stop(); state._audio_stream.close()
        except Exception: pass


if __name__ == "__main__":
    main()
