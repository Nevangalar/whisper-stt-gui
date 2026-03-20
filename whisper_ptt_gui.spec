# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas_fw,  binaries_fw,  hi_fw  = collect_all('faster_whisper')
datas_ct2, binaries_ct2, hi_ct2 = collect_all('ctranslate2')
datas_ov,  binaries_ov,  hi_ov  = collect_all('openvino')
datas_ovg, binaries_ovg, hi_ovg = collect_all('openvino_genai')
datas_ovt, binaries_ovt, hi_ovt = collect_all('openvino_tokenizers')

a = Analysis(
    ['whisper_ptt_gui.py'],
    pathex=[],
    binaries  = binaries_fw + binaries_ct2 + binaries_ov + binaries_ovg + binaries_ovt,
    datas     = datas_fw + datas_ct2 + datas_ov + datas_ovg + datas_ovt,
    hiddenimports=[
        'faster_whisper', 'ctranslate2',
        'openvino', 'openvino_genai', 'openvino_tokenizers',
        'sounddevice', 'soundfile', '_sounddevice_data',
        'numpy', 'numpy.core._multiarray_umath',
        # pynput statt keyboard
        'pynput', 'pynput.keyboard', 'pynput.mouse',
        'pynput.keyboard._win32', 'pynput.mouse._win32',
        'pyperclip', 'pyautogui', 'pygetwindow',
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.font',
        'queue', 'threading', 'tempfile', 'json', 'pathlib',
        # Windows Mic-Berechtigung
        'winreg', 'ctypes', 'subprocess',
        'winrt', 'winrt.windows.media.capture',
    ] + hi_fw + hi_ct2 + hi_ov + hi_ovg + hi_ovt,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'PIL', 'PyQt5', 'PyQt6', 'wx',
              'IPython', 'jupyter', 'scipy'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='WhisperPTT',
    debug=False, strip=False, upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name='WhisperPTT',
)
