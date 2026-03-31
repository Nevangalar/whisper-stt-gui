"""Tests for ptt/config.py – settings load/save logic."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_settings_corrupt_json_logs_error(tmp_path, mock_ptt_state):
    """Corrupt settings.json must log an error instead of silently swallowing it."""
    bad_file = tmp_path / "settings.json"
    bad_file.write_text("{invalid json", encoding="utf-8")

    from ptt import config
    with patch.object(config, "SETTINGS_FILE", bad_file), \
         patch.object(config, "state", mock_ptt_state):
        config.load_settings()

    messages = []
    while not mock_ptt_state.ui_queue.empty():
        messages.append(mock_ptt_state.ui_queue.get_nowait())
    log_msgs = [m[1] for m in messages if m[0] == "log"]
    assert any("settings" in m.lower() or "error" in m.lower() or "failed" in m.lower()
               for m in log_msgs), f"No error logged. Got: {log_msgs}"


def test_load_settings_missing_file_uses_defaults(tmp_path, mock_ptt_state):
    """Missing settings.json must silently use DEFAULTS (no error)."""
    missing = tmp_path / "nonexistent.json"

    from ptt import config
    with patch.object(config, "SETTINGS_FILE", missing), \
         patch.object(config, "state", mock_ptt_state):
        config.load_settings()

    # No error logged for missing file
    messages = []
    while not mock_ptt_state.ui_queue.empty():
        messages.append(mock_ptt_state.ui_queue.get_nowait())
    log_msgs = [m[1] for m in messages if m[0] == "log"]
    assert not any("error" in m.lower() or "failed" in m.lower() for m in log_msgs)


def test_load_settings_valid_file_overrides_defaults(tmp_path, mock_ptt_state):
    """Valid settings.json values override DEFAULTS."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"hotkey": "alt+x", "model": "small"}),
                              encoding="utf-8")

    from ptt import config
    with patch.object(config, "SETTINGS_FILE", settings_file), \
         patch.object(config, "state", mock_ptt_state):
        config.load_settings()

    assert mock_ptt_state.cfg["hotkey"] == "alt+x"
    assert mock_ptt_state.cfg["model"] == "small"
