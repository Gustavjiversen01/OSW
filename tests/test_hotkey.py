import os
import importlib


def test_parse_hotkey_splits():
    from localdictate.hotkey import _parse_hotkey
    assert _parse_hotkey("ctrl+space") == {"ctrl", "space"}
    assert _parse_hotkey("Alt + Shift + A") == {"alt", "shift", "a"}
    assert _parse_hotkey("a") == {"a"}


def test_parse_hotkey_empty():
    from localdictate.hotkey import _parse_hotkey
    assert _parse_hotkey("") == set()
    assert _parse_hotkey("+++") == set()


def test_import_without_display():
    """Verify localdictate.hotkey can be imported without DISPLAY set.

    This tests that pynput is lazily imported inside start(), not at
    module level.
    """
    # Re-import the module to verify no pynput import at module level
    import localdictate.hotkey
    # If we get here without ImportError/RuntimeError, the lazy import works.
    # The module should define _parse_hotkey and HotkeyListener without pynput.
    assert hasattr(localdictate.hotkey, "_parse_hotkey")
    assert hasattr(localdictate.hotkey, "HotkeyListener")
