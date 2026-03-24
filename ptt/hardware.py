"""
ptt/hardware.py – Hardware detection and device resolution.
"""

import subprocess
import sounddevice as sd

# ─── Hardware detection ────────────────────────────────────────────────────────

_device_cache: dict | None = None  # cached after first call; invalidate by setting to None

def detect_devices() -> dict:
    global _device_cache
    if _device_cache is not None:
        return _device_cache
    r = {"cuda": False, "npu": False, "cuda_name": "", "npu_name": ""}
    try:
        import torch
        if torch.cuda.is_available():
            r["cuda"] = True; r["cuda_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    # Primary NPU detection via OpenVINO (official method)
    try:
        import openvino as ov
        core  = ov.Core()
        avail = core.available_devices
        npu_devs = [d for d in avail if "NPU" in d]
        if npu_devs:
            r["npu"] = True
            try:
                r["npu_name"] = core.get_property(npu_devs[0], "FULL_DEVICE_NAME")
            except Exception:
                r["npu_name"] = npu_devs[0]
    except Exception:
        pass
    # Fallback: Windows PnP device list (works without openvino installed)
    if not r["npu"]:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-PnpDevice | Where-Object {$_.FriendlyName} | "
                 "ForEach-Object {$_.FriendlyName}"],
                capture_output=True, text=True, timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
            for line in out.splitlines():
                ln = line.strip()
                if ln and any(kw in ln.upper() for kw in
                              ("NPU", "NEURAL", "AI BOOST", "VPU")):
                    r["npu"] = True
                    r["npu_name"] = ln
                    break
        except Exception:
            pass
    _device_cache = r
    return r

def resolve_device(dev_cfg, compute_cfg):
    av = detect_devices()
    if dev_cfg == "auto":
        if av["cuda"]:  d, c = "cuda", "float16"
        elif av["npu"]: d, c = "npu",  "int8"
        else:           d, c = "cpu",  "int8"
    elif dev_cfg == "cuda":         d, c = "cuda", "float16"
    elif dev_cfg in ("npu", "dml"): d, c = "npu",  "int8"   # dml = legacy alias
    else:                           d, c = "cpu",  "int8"
    if compute_cfg != "auto": c = compute_cfg
    return d, c

# ─── Microphone detection ──────────────────────────────────────────────────────

def get_mic_devices() -> dict:
    """
    Get available microphone input devices.
    Returns dict: {device_index: "Device Name", ...}
    -1 is always included as the first entry (system default device).
    """
    # -1 = let sounddevice use the OS default; always offer this option first
    default_label = "Default (system default)"
    try:
        default_dev = sd.query_devices(kind="input")
        default_name = default_dev.get("name", "").strip()
        if default_name:
            default_label = f"Default  [{default_name}]"
    except Exception:
        pass

    devices = {-1: default_label}
    try:
        devs = sd.query_devices()
        if isinstance(devs, dict):
            devs = [devs]
        for i, dev in enumerate(devs):
            if dev.get("max_input_channels", 0) > 0:
                name = dev.get("name", f"Device {i}").strip()
                devices[i] = name
    except Exception:
        pass

    return devices
