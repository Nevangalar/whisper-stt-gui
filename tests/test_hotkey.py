#!/usr/bin/env python3
"""
tests/test_hotkey.py – Standalone hotkey/pynput component test.
Run: python tests/test_hotkey.py

Shows exactly what key names pynput sees for each keypress.
Press Ctrl+C (in a separate terminal) or wait 30s to stop.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pynput import keyboard as pynput_kb
from ptt.hotkey import _pynput_key_name

print("pynput key listener – press keys to see what names are detected.")
print("Test your hotkey combination now. Ctrl+C in another terminal to stop.\n")

held = set()

def on_press(key):
    name = _pynput_key_name(key)
    held.add(name)
    print(f"  PRESS   raw={key!r:<30s}  name={name!r:<15s}  held={sorted(held)}")

def on_release(key):
    name = _pynput_key_name(key)
    held.discard(name)
    print(f"  RELEASE raw={key!r:<30s}  name={name!r}")

try:
    with pynput_kb.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()
except KeyboardInterrupt:
    print("\nStopped.")
