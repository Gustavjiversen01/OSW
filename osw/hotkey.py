from pynput import keyboard
from pynput.keyboard import Key, KeyCode


def _parse_hotkey(hotkey_str: str) -> set[str]:
    return {k.strip().lower() for k in hotkey_str.split("+")}


_KEY_NAMES = {
    "ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt,
    "super": Key.cmd, "space": Key.space, "tab": Key.tab,
    "enter": Key.enter, "esc": Key.esc,
}


def _resolve(parts: set[str]) -> set:
    keys = set()
    for p in parts:
        if p in _KEY_NAMES:
            keys.add(_KEY_NAMES[p])
        elif len(p) == 1:
            keys.add(KeyCode.from_char(p))
    return keys


def _canonicalize(key):
    mapping = {
        Key.ctrl_l: Key.ctrl, Key.ctrl_r: Key.ctrl,
        Key.shift_l: Key.shift, Key.shift_r: Key.shift,
        Key.alt_l: Key.alt, Key.alt_r: Key.alt,
        Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
    }
    return mapping.get(key, key)


class HotkeyListener:
    """Toggle mode: first press starts, second press stops."""

    def __init__(self, hotkey_str: str, on_toggle):
        self._on_toggle = on_toggle
        self._recording = False
        self._pressed = set()
        self._combo_was_held = False
        self._listener = None
        self.update_hotkey(hotkey_str)

    def update_hotkey(self, hotkey_str: str):
        self._combo = _resolve(_parse_hotkey(hotkey_str))

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_key_press(self, key):
        self._pressed.add(_canonicalize(key))
        if self._pressed >= self._combo and not self._combo_was_held:
            self._combo_was_held = True
            self._recording = not self._recording
            self._on_toggle(self._recording)

    def _on_key_release(self, key):
        self._pressed.discard(_canonicalize(key))
        if not (self._pressed >= self._combo):
            self._combo_was_held = False
