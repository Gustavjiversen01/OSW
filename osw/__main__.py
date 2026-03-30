import subprocess
import sys
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenu

from . import settings
from .engine import Engine
from .hotkey import HotkeyListener
from .ui import SettingsDialog, TrayIcon


class Bridge(QObject):
    recording_started = Signal()
    recording_stopped = Signal()
    transcription_done = Signal(str)
    error_occurred = Signal(str)


def _inject_text(text: str):
    app = QApplication.instance()
    clipboard = app.clipboard()
    old = clipboard.text()
    clipboard.setText(text)
    time.sleep(0.05)

    if sys.platform == "darwin":
        _simulate_paste_pynput("cmd")
    elif sys.platform == "linux":
        session = __import__("os").environ.get("XDG_SESSION_TYPE", "x11")
        if session == "wayland":
            try:
                subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                    timeout=5, check=True,
                )
            except FileNotFoundError:
                subprocess.run(
                    ["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"],
                    timeout=5, check=True,
                )
        else:
            try:
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                    timeout=5, check=True,
                )
            except FileNotFoundError:
                _simulate_paste_pynput("ctrl")
    else:
        _simulate_paste_pynput("ctrl")

    time.sleep(0.05)
    clipboard.setText(old)


def _simulate_paste_pynput(modifier: str):
    from pynput.keyboard import Controller, Key
    kb = Controller()
    mod = Key.cmd if modifier == "cmd" else Key.ctrl
    kb.press(mod)
    kb.press("v")
    kb.release("v")
    kb.release(mod)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    cfg = settings.load()
    bridge = Bridge()
    engine = Engine(
        on_transcription=bridge.transcription_done.emit,
        on_error=bridge.error_occurred.emit,
    )

    # Tray icon
    tray = TrayIcon()

    menu = QMenu()
    settings_action = menu.addAction("Settings...")
    menu.addSeparator()
    quit_action = menu.addAction("Quit")
    tray.setContextMenu(menu)
    tray.show()

    # Settings dialog
    dialog_ref = [None]

    def open_settings():
        if dialog_ref[0] and dialog_ref[0].isVisible():
            dialog_ref[0].raise_()
            return
        dialog_ref[0] = SettingsDialog(settings.load(), on_settings_changed)
        dialog_ref[0].show()

    def on_settings_changed(new_cfg):
        nonlocal cfg
        cfg = new_cfg
        hotkey_listener.update_hotkey(cfg["hotkey"])
        tray._update_icon()

    settings_action.triggered.connect(open_settings)
    quit_action.triggered.connect(app.quit)

    # Hotkey callbacks (run on listener thread — emit signals only!)
    def on_hotkey_press():
        bridge.recording_started.emit()

    def on_hotkey_release():
        bridge.recording_stopped.emit()

    # Signal handlers (run on main thread — safe to touch everything)
    def handle_recording_started():
        tray.set_state(TrayIcon.RECORDING)
        engine.start_recording()

    def handle_recording_stopped():
        tray.set_state(TrayIcon.PROCESSING)
        engine.stop_and_transcribe(cfg["model"])

    def handle_transcription(text: str):
        tray.set_state(TrayIcon.IDLE)
        _inject_text(text)

    def handle_error(msg: str):
        tray.set_state(TrayIcon.IDLE)
        tray.showMessage("OSW", msg, TrayIcon.MessageIcon.Warning, 3000)

    bridge.recording_started.connect(handle_recording_started)
    bridge.recording_stopped.connect(handle_recording_stopped)
    bridge.transcription_done.connect(handle_transcription)
    bridge.error_occurred.connect(handle_error)

    # Hotkey listener
    hotkey_listener = HotkeyListener(cfg["hotkey"], on_hotkey_press, on_hotkey_release)
    hotkey_listener.start()

    # Onboarding
    if not cfg.get("onboarding_shown"):
        tray.showMessage(
            "OSW", f"Ready. Hold {cfg['hotkey'].replace('+', ' + ').title()} to dictate.",
            TrayIcon.MessageIcon.Information, 4000,
        )
        cfg["onboarding_shown"] = True
        settings.save(cfg)

    # Cleanup
    def cleanup():
        hotkey_listener.stop()
        engine.cancel()
        engine.unload()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
