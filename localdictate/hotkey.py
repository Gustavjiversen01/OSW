"""Global hotkey listener with lazy pynput import for headless compatibility."""

import threading


def _parse_hotkey(hotkey_str: str) -> set[str]:
    """Parse a hotkey string into a set of lowercase key names. Pure string ops."""
    return {k.strip().lower() for k in hotkey_str.split("+") if k.strip()}


class HotkeyListener:
    """Stateless hotkey listener — emits 'triggered' on each combo press.

    Does not track recording state; that lives in the controller (__main__.py).
    pynput is imported lazily inside start() for headless/CI compatibility.
    """

    def __init__(self, hotkey_str: str, on_triggered):
        self._on_triggered = on_triggered
        self._hotkey_str = hotkey_str
        self._pressed = set()
        self._combo_was_held = False
        self._combo = set()  # resolved pynput keys, populated in start()
        self._lock = threading.Lock()
        self._listener = None
        # pynput types, set after start()
        self._Key = None
        self._KeyCode = None
        self._keyboard = None

    def start(self) -> bool:
        """Import pynput and start listening. Returns True on success."""
        try:
            from pynput import keyboard
            from pynput.keyboard import Key, KeyCode
            self._keyboard = keyboard
            self._Key = Key
            self._KeyCode = KeyCode
            self._combo = self._resolve(_parse_hotkey(self._hotkey_str))
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._listener.daemon = True
            self._listener.start()
            return True
        except Exception:
            return False

    def stop(self):
        if self._listener:
            self._listener.stop()

    def update_hotkey(self, hotkey_str: str):
        """Update the hotkey combo. Thread-safe."""
        self._hotkey_str = hotkey_str
        with self._lock:
            self._pressed.clear()
            self._combo_was_held = False
            if self._Key is not None:  # pynput loaded
                self._combo = self._resolve(_parse_hotkey(hotkey_str))

    def _resolve(self, parts: set[str]) -> set:
        """Resolve string key names to pynput key objects."""
        Key = self._Key
        KeyCode = self._KeyCode
        key_names = {
            "ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt,
            "super": Key.cmd, "space": Key.space, "tab": Key.tab,
            "enter": Key.enter, "esc": Key.esc,
        }
        keys = set()
        for p in parts:
            if p in key_names:
                keys.add(key_names[p])
            elif len(p) == 1:
                keys.add(KeyCode.from_char(p))
        return keys

    def _canonicalize(self, key):
        Key = self._Key
        mapping = {
            Key.ctrl_l: Key.ctrl, Key.ctrl_r: Key.ctrl,
            Key.shift_l: Key.shift, Key.shift_r: Key.shift,
            Key.alt_l: Key.alt, Key.alt_r: Key.alt,
            Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
        }
        return mapping.get(key, key)

    def _on_key_press(self, key):
        canon = self._canonicalize(key)
        should_trigger = False
        with self._lock:
            self._pressed.add(canon)
            if self._pressed >= self._combo and not self._combo_was_held:
                self._combo_was_held = True
                should_trigger = True
        if should_trigger:
            self._on_triggered()

    def _on_key_release(self, key):
        canon = self._canonicalize(key)
        with self._lock:
            self._pressed.discard(canon)
            if not (self._pressed >= self._combo):
                self._combo_was_held = False
