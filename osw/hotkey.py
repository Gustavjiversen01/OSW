import sys
import threading


def _parse_hotkey(hotkey_str: str) -> set[str]:
    return {k.strip().lower() for k in hotkey_str.split("+")}


if sys.platform == "linux":
    import evdev
    from evdev import ecodes

    _KEY_NAMES = {
        "ctrl": {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL},
        "shift": {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT},
        "alt": {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT},
        "super": {ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA},
        "space": {ecodes.KEY_SPACE},
    }

    def _resolve_keys(parts: set[str]) -> list[set[int]]:
        resolved = []
        for p in parts:
            if p in _KEY_NAMES:
                resolved.append(_KEY_NAMES[p])
            elif hasattr(ecodes, f"KEY_{p.upper()}"):
                resolved.append({getattr(ecodes, f"KEY_{p.upper()}")})
        return resolved

    def _find_keyboard() -> evdev.InputDevice:
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = dev.capabilities(verbose=False)
            if ecodes.EV_KEY in caps and ecodes.KEY_SPACE in caps[ecodes.EV_KEY]:
                return dev
        raise RuntimeError("No keyboard found")

    class HotkeyListener:
        def __init__(self, hotkey_str: str, on_press, on_release):
            self._on_press = on_press
            self._on_release = on_release
            self._active = False
            self._running = False
            self._thread = None
            self.update_hotkey(hotkey_str)

        def update_hotkey(self, hotkey_str: str):
            self._key_groups = _resolve_keys(_parse_hotkey(hotkey_str))

        def start(self):
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

        def stop(self):
            self._running = False

        def _loop(self):
            try:
                dev = _find_keyboard()
            except RuntimeError:
                return
            pressed = set()
            while self._running:
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.value == 1:  # key down
                            pressed.add(event.code)
                        elif event.value == 0:  # key up
                            pressed.discard(event.code)

                        combo_held = all(
                            bool(group & pressed) for group in self._key_groups
                        )
                        if combo_held and not self._active:
                            self._active = True
                            self._on_press()
                        elif not combo_held and self._active:
                            self._active = False
                            self._on_release()
                except BlockingIOError:
                    import time
                    time.sleep(0.01)

else:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode

    _PYNPUT_NAMES = {
        "ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt,
        "super": Key.cmd, "space": Key.space, "tab": Key.tab,
        "enter": Key.enter, "esc": Key.esc,
    }

    def _resolve_pynput(parts: set[str]) -> set:
        keys = set()
        for p in parts:
            if p in _PYNPUT_NAMES:
                keys.add(_PYNPUT_NAMES[p])
            elif len(p) == 1:
                keys.add(KeyCode.from_char(p))
        return keys

    def _canonicalize(key) -> Key | KeyCode:
        mapping = {
            Key.ctrl_l: Key.ctrl, Key.ctrl_r: Key.ctrl,
            Key.shift_l: Key.shift, Key.shift_r: Key.shift,
            Key.alt_l: Key.alt, Key.alt_r: Key.alt,
            Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
        }
        return mapping.get(key, key)

    class HotkeyListener:
        def __init__(self, hotkey_str: str, on_press, on_release):
            self._on_press = on_press
            self._on_release = on_release
            self._active = False
            self._pressed = set()
            self._listener = None
            self.update_hotkey(hotkey_str)

        def update_hotkey(self, hotkey_str: str):
            self._combo = _resolve_pynput(_parse_hotkey(hotkey_str))

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
            if self._pressed >= self._combo and not self._active:
                self._active = True
                self._on_press()

        def _on_key_release(self, key):
            self._pressed.discard(_canonicalize(key))
            if self._active and not (self._pressed >= self._combo):
                self._active = False
                self._on_release()
