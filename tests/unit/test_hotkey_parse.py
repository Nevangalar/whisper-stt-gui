"""Tests for ptt/hotkey.py parse_hotkey() function."""
import pytest
import sys
import types


@pytest.fixture
def parse_hotkey(mock_ptt_state):
    """Import parse_hotkey with stubbed dependencies."""
    kb_mod = types.ModuleType("pynput.keyboard")
    ms_mod = types.ModuleType("pynput.mouse")
    ms_mod.Button = types.SimpleNamespace(
        left=object(), right=object(), middle=object()
    )
    sys.modules["pynput.keyboard"] = kb_mod
    sys.modules["pynput.mouse"] = ms_mod
    sys.modules["pynput"] = types.ModuleType("pynput")

    from ptt.hotkey import parse_hotkey as _ph
    return _ph


def test_parse_hotkey_simple_key(parse_hotkey):
    result = parse_hotkey("space")
    assert result["mods"] == set()
    assert result["key"] == "space"
    assert result["mouse"] is None


def test_parse_hotkey_with_modifiers(parse_hotkey):
    result = parse_hotkey("ctrl+alt+space")
    assert result["mods"] == {"ctrl", "alt"}
    assert result["key"] == "space"
    assert result["mouse"] is None


def test_parse_hotkey_mouse_only(parse_hotkey):
    result = parse_hotkey("mouse_x1")
    assert result["mods"] == set()
    assert result["key"] is None
    assert result["mouse"] == "mouse_x1"


def test_parse_hotkey_mouse_with_mods(parse_hotkey):
    result = parse_hotkey("ctrl+mouse_x1")
    assert result["mods"] == {"ctrl"}
    assert result["key"] is None
    assert result["mouse"] == "mouse_x1"


def test_parse_hotkey_invalid_string_no_key_no_mouse(parse_hotkey):
    # "+++" should produce no key and no mouse (not crash)
    result = parse_hotkey("+++")
    assert result["key"] is None
    assert result["mouse"] is None


def test_parse_hotkey_modifier_only(parse_hotkey):
    # "ctrl+" has no main key — key should be None
    result = parse_hotkey("ctrl+")
    assert result["key"] is None or result["key"] == ""
    assert result["mouse"] is None


def test_parse_hotkey_empty_string(parse_hotkey):
    result = parse_hotkey("")
    assert result["key"] is None
    assert result["mouse"] is None


def test_parse_hotkey_case_insensitive(parse_hotkey):
    result = parse_hotkey("CTRL+ALT+Space")
    assert "ctrl" in result["mods"]
    assert "alt" in result["mods"]
    assert result["key"] == "space"
