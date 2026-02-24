#!/usr/bin/env python3
"""
Whisper PTT – entry point
=========================
Thin launcher: devnull redirect (PyInstaller) + main().
All application logic lives in the ptt/ package.
"""

import os
import sys
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


def main():
    load_settings()

    root = tk.Tk()
    app  = WhisperPTTApp(root)  # noqa: F841

    threading.Thread(target=start_audio_stream, daemon=True).start()

    root.mainloop()

    if state._audio_stream is not None:
        try: state._audio_stream.stop(); state._audio_stream.close()
        except Exception: pass


if __name__ == "__main__":
    main()
