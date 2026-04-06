"""Cross-platform autostart management for LocalDictate."""

import os
import sys
from pathlib import Path


def set_autostart(enabled: bool):
    """Enable or disable autostart. Platform failures are isolated."""
    if sys.platform == "linux":
        _linux_autostart(enabled)
    elif sys.platform == "win32":
        _windows_autostart(enabled)
    elif sys.platform == "darwin":
        _macos_autostart(enabled)


def cleanup_stale_osw():
    """Remove stale osw.desktop autostart entry from before the rename."""
    if sys.platform != "linux":
        return
    stale = Path.home() / ".config" / "autostart" / "osw.desktop"
    if stale.exists():
        try:
            stale.unlink()
        except OSError:
            pass


def _linux_autostart(enabled: bool):
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop_file = autostart_dir / "localdictate.desktop"
    if enabled:
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_file.write_text(
            "[Desktop Entry]\nType=Application\nName=LocalDictate\n"
            f"Exec={sys.executable} -m localdictate\nHidden=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
    elif desktop_file.exists():
        desktop_file.unlink()


def _windows_autostart(enabled: bool):
    try:
        import subprocess
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        cmd = subprocess.list2cmdline([sys.executable, "-m", "localdictate"])
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, "LocalDictate", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "LocalDictate")
                except FileNotFoundError:
                    pass
    except Exception:
        pass  # Windows-specific failure doesn't propagate


def _macos_autostart(enabled: bool):
    try:
        import plistlib
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_file = plist_dir / "com.gustavjiversen.localdictate.plist"
        if enabled:
            plist_dir.mkdir(parents=True, exist_ok=True)
            plist_data = {
                "Label": "com.gustavjiversen.localdictate",
                "ProgramArguments": [sys.executable, "-m", "localdictate"],
                "RunAtLoad": True,
            }
            with open(plist_file, "wb") as f:
                plistlib.dump(plist_data, f)
        elif plist_file.exists():
            plist_file.unlink()
    except Exception:
        pass  # macOS-specific failure doesn't propagate
