"""
ptt/hardware.py – Hardware detection and device resolution.
"""

import subprocess

# ─── Hardware detection ────────────────────────────────────────────────────────

def detect_devices() -> dict:
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
