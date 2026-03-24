#!/usr/bin/env python3
"""
tests/test_audio.py – Standalone audio component test.
Run: python tests/test_audio.py

Tests:
  1. Lists all input devices
  2. Records 3 seconds from each working device
  3. Reports signal level and whether audio data is real
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile

RATE      = 16000
DURATION  = 3  # seconds


def list_devices():
    print("=== Input devices ===")
    devs = sd.query_devices()
    if isinstance(devs, dict):
        devs = [devs]
    inputs = []
    for i, d in enumerate(devs):
        if d.get("max_input_channels", 0) > 0:
            print(f"  [{i:2d}] {d['name']:<40s}  ch={d['max_input_channels']}  rate={d['default_samplerate']:.0f}")
            inputs.append(i)
    print()
    try:
        default = sd.query_devices(kind="input")
        print(f"  Default → {default['name']}")
    except Exception as e:
        print(f"  Default query failed: {e}")
    print()
    return inputs


def record_device(device_idx, label="device"):
    """Try to record DURATION seconds. Returns (rms, max_amp, samples) or None on error."""
    rates_to_try = [RATE, 44100, 48000]
    for rate in rates_to_try:
        try:
            print(f"  Recording {DURATION}s at {rate} Hz ...", end=" ", flush=True)
            data = sd.rec(
                int(DURATION * rate), samplerate=rate, channels=1,
                dtype="float32", device=device_idx
            )
            sd.wait()
            data = data.flatten()
            rms    = float(np.sqrt(np.mean(data ** 2)))
            maxamp = float(np.max(np.abs(data)))
            nonzero = int(np.sum(np.abs(data) > 0.0001))
            print(f"OK  rms={rms:.5f}  max={maxamp:.5f}  nonzero={nonzero}/{len(data)}")

            if nonzero < 100:
                print(f"  ⚠️  Almost all samples are zero – mic might be muted or wrong device")
            elif maxamp > 0.99:
                print(f"  ⚠️  Signal is clipping – gain too high or wrong device")
            else:
                print(f"  ✅ Signal looks healthy")

            # Save sample for inspection
            out = os.path.join(tempfile.gettempdir(), f"whisper_test_{label}_{rate}.wav")
            sf.write(out, data, rate)
            print(f"  Saved: {out}")
            return rms, maxamp, data
        except Exception as e:
            print(f"FAIL ({e})")
    return None


def test_default():
    print("=== Test 1: System default input device ===")
    result = record_device(None, "default")
    print()
    return result


def test_all_inputs():
    print("=== Test 2: All input devices (first working one) ===")
    devs = sd.query_devices()
    if isinstance(devs, dict):
        devs = [devs]
    for i, d in enumerate(devs):
        if d.get("max_input_channels", 0) > 0:
            print(f"  Device {i}: {d['name']}")
            record_device(i, f"dev{i}")
    print()


if __name__ == "__main__":
    print("Whisper PTT – Audio component test")
    print("Speak into your microphone during recording!\n")

    list_devices()
    result = test_default()

    if result and result[0] < 0.0001:
        print("→ Default device seems silent. Testing all devices...")
        test_all_inputs()

    print("Done. WAV files saved to /tmp/ for manual inspection.")
