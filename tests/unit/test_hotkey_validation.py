"""Tests for hotkey validation logic extracted from settings._save()."""
import sys
import types
import pytest


def _is_valid_hotkey(hk: str) -> bool:
    """Mirror the validation logic added to settings._save()."""
    kb_mod = types.ModuleType("pynput.keyboard")
    ms_mod = types.ModuleType("pynput.mouse")
    ms_mod.Button = types.SimpleNamespace(
        left=object(), right=object(), middle=object()
    )
    sys.modules.setdefault("pynput.keyboard", kb_mod)
    sys.modules.setdefault("pynput.mouse", ms_mod)
    sys.modules.setdefault("pynput", types.ModuleType("pynput"))

    from ptt.hotkey import parse_hotkey
    if not hk or "▶" in hk:
        return False
    parsed = parse_hotkey(hk)
    return bool(parsed["key"] or parsed["mouse"])


def test_valid_keyboard_hotkey(mock_ptt_state):
    assert _is_valid_hotkey("ctrl+alt+space") is True


def test_valid_mouse_hotkey(mock_ptt_state):
    assert _is_valid_hotkey("ctrl+mouse_x1") is True


def test_invalid_empty(mock_ptt_state):
    assert _is_valid_hotkey("") is False


def test_invalid_prompt_placeholder(mock_ptt_state):
    assert _is_valid_hotkey("▶ Press a key…") is False


def test_invalid_modifier_only(mock_ptt_state):
    assert _is_valid_hotkey("ctrl+") is False


def test_invalid_triple_plus(mock_ptt_state):
    assert _is_valid_hotkey("+++") is False


def test_single_key_without_modifiers_is_valid(mock_ptt_state):
    assert _is_valid_hotkey("f9") is True
