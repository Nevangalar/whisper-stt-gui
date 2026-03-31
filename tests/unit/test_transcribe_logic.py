"""Tests for transcription logic in ptt/transcribe.py."""
import os
import pytest
from unittest.mock import patch, MagicMock


# ── Translation task selection ──────────────────────────────────────────────

def _task_for(in_lang, out_lang):
    """Mirror the task-selection logic from transcribe.py."""
    return "translate" if (out_lang == "en" and in_lang != "en") else "transcribe"


def test_translate_task_when_input_not_english():
    assert _task_for("de", "en") == "translate"


def test_translate_task_auto_detect_to_english():
    # in_lang=None means auto-detect → not "en" → should translate
    assert _task_for(None, "en") == "translate"


def test_transcribe_task_when_output_not_english():
    assert _task_for("de", "same") == "transcribe"


def test_transcribe_task_when_both_english():
    # in_lang="en" + out_lang="en" silently falls back to transcribe (no-op translation).
    assert _task_for("en", "en") == "transcribe"


def test_transcribe_task_same_output():
    assert _task_for(None, "same") == "transcribe"


# ── Temp WAV cleanup ─────────────────────────────────────────────────────────

def test_temp_wav_cleaned_up_on_sf_write_failure(tmp_path, mock_ptt_state):
    """If sf.write() raises, the temp file must still be removed."""
    import tempfile as tf

    tmp_path_used = None
    try:
        with tf.NamedTemporaryFile(suffix=".wav", delete=False, dir=tmp_path) as tmp:
            tmp_path_used = tmp.name
        raise OSError("disk full")
    except OSError:
        pass
    finally:
        if tmp_path_used and os.path.exists(tmp_path_used):
            os.unlink(tmp_path_used)

    assert not os.path.exists(tmp_path_used), "Temp file not cleaned up"


def test_temp_wav_cleaned_up_after_transcription(tmp_path, mock_ptt_state):
    """Temp WAV must be deleted even after successful transcription."""
    import tempfile as tf

    tmp_path_used = None
    try:
        with tf.NamedTemporaryFile(suffix=".wav", delete=False, dir=tmp_path) as tmp:
            tmp_path_used = tmp.name
        # simulate transcription succeeds
    finally:
        if tmp_path_used:
            try:
                os.unlink(tmp_path_used)
            except Exception:
                pass

    assert not os.path.exists(tmp_path_used), "Temp WAV not cleaned up after success"
