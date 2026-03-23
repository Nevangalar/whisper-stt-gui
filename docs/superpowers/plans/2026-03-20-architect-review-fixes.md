# Architect Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all issues identified in the senior architect review of Whisper PTT v0.8.1.

**Architecture:** 18 targeted fixes across 8 files, grouped by severity. No new modules created. All changes are backwards-compatible — no settings format changes, no API changes. Version bumps to 0.8.2.

**Tech Stack:** Python 3.10+, tkinter, threading, pynput, sounddevice, faster-whisper, PyInstaller

---

## Files Modified

| File | Changes |
|------|---------|
| `ptt/constants.py` | Remove `pynput` import + `MOUSE_BTN_NAMES` |
| `ptt/hotkey.py` | Add `MOUSE_BTN_NAMES` dict, import `_pynput_key_name` from here |
| `ptt/state.py` | Add `model_load_lock`, `ptt_lock` |
| `ptt/audio.py` | Add lock in `audio_callback`, fix `subprocess shell=True` |
| `ptt/transcribe.py` | Clear `audio_chunks` after snapshot |
| `ptt/model_manager.py` | Remove duplicate `faster_whisper` import |
| `ptt/config.py` | Surface `save_settings` error to UI |
| `ptt/ui/settings.py` | Fix `_detect_hw` thread safety, de-dup `_key_name`, fix geometry, Beam Size i18n |
| `ptt/ui/app.py` | Fix `_poll_queue` except, fix `_loading_model` lock, fix `_copy_recog` except, cap `_clean_texts` |
| `ptt/ui/helpers.py` | Remove dead event bindings |
| `requirements.txt` | New file — pinned dependencies |
| `whisper_ptt_gui.spec` | Disable UPX on ML binaries |
| `ptt/constants.py` | VERSION → 0.8.2, add Beam Size i18n key |
| `CHANGELOG.md` | Add [0.8.2] entry |

---

## Task 1: Move MOUSE_BTN_NAMES out of constants.py [CRITICAL]

**Files:**
- Modify: `ptt/constants.py` — remove pynput import + MOUSE_BTN_NAMES
- Modify: `ptt/hotkey.py` — add MOUSE_BTN_NAMES locally
- Modify: `ptt/ui/settings.py` — update import to get MOUSE_BTN_NAMES from hotkey

- [ ] Remove `from pynput import mouse as pynput_ms` from `constants.py`
- [ ] Remove `MOUSE_BTN_NAMES` dict from `constants.py`
- [ ] Add `MOUSE_BTN_NAMES` to `hotkey.py` using already-imported `pynput_ms`
- [ ] Update `settings.py` import: `from ptt.hotkey import MOUSE_BTN_NAMES, _pynput_key_name`
- [ ] Remove `MOUSE_BTN_NAMES` from `settings.py` constants import

---

## Task 2: Add threading locks to state.py [HIGH]

**Files:**
- Modify: `ptt/state.py` — add `model_load_lock`, `ptt_lock`

- [ ] Add `model_load_lock = threading.Lock()` for model loading guard
- [ ] Add `ptt_lock = threading.Lock()` for PTT active flag guard

---

## Task 3: Fix audio_callback missing lock [HIGH]

**Files:**
- Modify: `ptt/audio.py:32`

- [ ] Wrap `state.audio_chunks.append(indata.copy())` in `with state.record_lock:`

---

## Task 4: Fix _loading_model TOCTOU race [HIGH]

**Files:**
- Modify: `ptt/ui/app.py` — `_load_model_async`, `_on_settings_saved`

- [ ] In `_load_model_async`: guard check-and-set with `state.model_load_lock`
- [ ] In `_on_settings_saved`: guard check-and-set with `state.model_load_lock`
- [ ] Reset `_loading_model` inside finally block (already done, verify)

---

## Task 5: Fix _ptt_active TOCTOU race [MEDIUM]

**Files:**
- Modify: `ptt/hotkey.py` — `_ptt_trigger_press`, `_ptt_trigger_release`

- [ ] Wrap check-and-set of `state._ptt_active` in `with state.ptt_lock:` in both functions

---

## Task 6: Fix _detect_hw widget updates from background thread [HIGH]

**Files:**
- Modify: `ptt/ui/settings.py:382-395`

- [ ] Replace direct `.config()` calls with `self.win.after(0, lambda: ...)` in `_detect_hw`

---

## Task 7: Fix _poll_queue bare except [HIGH]

**Files:**
- Modify: `ptt/ui/app.py:234-254`

- [ ] Change outer `except Exception: pass` to `except queue.Empty: pass`
- [ ] Add `import queue` at top if not already present
- [ ] Wrap inner dispatch block in its own try/except that logs errors

---

## Task 8: Fix transcribe.py chunk snapshot [MEDIUM]

**Files:**
- Modify: `ptt/transcribe.py:34-35`

- [ ] After snapshotting chunks, clear `state.audio_chunks` under the same lock

---

## Task 9: Remove duplicate _key_name [MEDIUM]

**Files:**
- Modify: `ptt/hotkey.py` — export `_pynput_key_name` (already public enough)
- Modify: `ptt/ui/settings.py` — remove `_key_name`, use imported `_pynput_key_name`

- [ ] Import `_pynput_key_name` from `ptt.hotkey` in `settings.py`
- [ ] Replace `self._key_name(key)` calls with `_pynput_key_name(key)` in settings.py
- [ ] Remove `_key_name` static method from `SettingsWindow`

---

## Task 10: Fix model_manager double import [MEDIUM]

**Files:**
- Modify: `ptt/model_manager.py:58-71`

- [ ] Hoist `from faster_whisper import WhisperModel` to top of `load_model()` function
- [ ] Remove duplicate import in the except block

---

## Task 11: Fix config.py save_settings error visibility [LOW]

**Files:**
- Modify: `ptt/config.py:31-36`

- [ ] Replace `print(f"Settings error: {e}")` with `state.ui_queue.put(("log", f"⚠️ Settings save error: {e}"))`

---

## Task 12: Fix subprocess shell=True in audio.py [LOW]

**Files:**
- Modify: `ptt/audio.py:78`

- [ ] Replace `subprocess.Popen(["ms-settings:..."], shell=True, ...)` with `os.startfile("ms-settings:privacy-microphone")`

---

## Task 13: Fix bare except in _copy_recog [LOW]

**Files:**
- Modify: `ptt/ui/app.py:184`

- [ ] Change `except:` to `except tk.TclError:`

---

## Task 14: Cap _clean_texts list [LOW]

**Files:**
- Modify: `ptt/ui/app.py:297`

- [ ] After appending, trim: `if len(self._clean_texts) > 50: self._clean_texts = self._clean_texts[-50:]`

---

## Task 15: Remove dead event bindings in helpers.py [LOW]

**Files:**
- Modify: `ptt/ui/helpers.py:62-64`

- [ ] Remove the three no-op `txt.bind(...)` lines

---

## Task 16: Fix settings window height for small screens [MEDIUM]

**Files:**
- Modify: `ptt/ui/settings.py:52`

- [ ] Cap geometry height to `min(720, screen_height - 80)`

---

## Task 17: Add Beam Size i18n [LOW]

**Files:**
- Modify: `ptt/constants.py` — add `beam_size_label` translation key
- Modify: `ptt/ui/settings.py` — use `T("beam_size_label")` instead of hardcoded string

- [ ] Add `"beam_size_label"` to TRANSLATIONS with all 4 languages
- [ ] Replace hardcoded `"Beam Size:"` label in settings.py with `T("beam_size_label")`

---

## Task 18: Add requirements.txt + fix UPX [MEDIUM]

**Files:**
- Create: `requirements.txt`
- Modify: `whisper_ptt_gui.spec`

- [ ] Create `requirements.txt` with core dependencies (unpinned ranges)
- [ ] Set `upx=False` in PyInstaller spec to prevent ML binary corruption

---

## Task 19: Version bump + CHANGELOG [BOOKKEEPING]

- [ ] Bump `VERSION = "0.8.2"` in `ptt/constants.py`
- [ ] Add `[0.8.2]` section to `CHANGELOG.md`
- [ ] Update version history table
- [ ] Commit on `feat/v0.8.1-spinner` branch (already active)
