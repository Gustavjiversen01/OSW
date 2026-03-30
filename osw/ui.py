import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QLineEdit,
    QMenu, QSystemTrayIcon,
)

from . import settings


def _make_icon(color: str, filled: bool = False, opacity: float = 1.0) -> QIcon:
    dpr = QApplication.instance().devicePixelRatio()
    size = int(22 * dpr)
    pm = QPixmap(size, size)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setOpacity(opacity)

    rect = pm.rect()
    cx, cy = rect.width() / dpr / 2, rect.height() / dpr / 2

    if filled:
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx - 8), int(cy - 8), 16, 16)
    else:
        p.setPen(QColor(color))
        p.setBrush(Qt.NoBrush)
        # Microphone shape: rounded rect body + stand
        p.drawRoundedRect(int(cx - 4), int(cy - 8), 8, 12, 3, 3)
        p.drawArc(int(cx - 6), int(cy - 2), 12, 12, 0, -180 * 16)
        p.drawLine(int(cx), int(cy + 4), int(cx), int(cy + 7))
        p.drawLine(int(cx - 3), int(cy + 7), int(cx + 3), int(cy + 7))

    p.end()
    icon = QIcon(pm)
    icon.setIsMask(not filled)
    return icon


class TrayIcon(QSystemTrayIcon):
    IDLE, RECORDING, PROCESSING = range(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.IDLE
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_opacity = 1.0
        self._pulse_dir = -1
        self._update_icon()

    def set_state(self, state: int):
        self._state = state
        if state == self.RECORDING:
            self._pulse_opacity = 1.0
            self._pulse_timer.start(66)  # ~15fps
        else:
            self._pulse_timer.stop()
        self._update_icon()

    def _pulse_tick(self):
        self._pulse_opacity += self._pulse_dir * 0.08
        if self._pulse_opacity <= 0.3:
            self._pulse_dir = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_dir = -1
        self._update_icon()

    def _update_icon(self):
        tooltips = {
            self.IDLE: "OSW — Hold Ctrl+Space to dictate",
            self.RECORDING: "Recording...",
            self.PROCESSING: "Transcribing...",
        }
        self.setToolTip(tooltips.get(self._state, ""))

        if self._state == self.IDLE:
            self.setIcon(_make_icon("#888888", filled=False))
        elif self._state == self.RECORDING:
            self.setIcon(_make_icon("#e74c3c", filled=True, opacity=self._pulse_opacity))
        elif self._state == self.PROCESSING:
            self.setIcon(_make_icon("#e67e22", filled=True))


class SettingsDialog(QDialog):
    def __init__(self, current_settings: dict, on_changed, parent=None):
        super().__init__(parent)
        self._settings = dict(current_settings)
        self._on_changed = on_changed
        self.setWindowTitle("OSW")
        self.setFixedSize(320, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Quality dropdown
        self._quality = QComboBox()
        labels = list(settings.MODELS.keys())
        self._quality.addItems(labels)
        current_label = settings.label_for_model(self._settings["model"])
        if current_label in labels:
            self._quality.setCurrentText(current_label)
        self._quality.currentTextChanged.connect(self._on_quality_changed)
        layout.addRow("Quality", self._quality)

        # Shortcut
        self._shortcut = QLineEdit(self._settings["hotkey"])
        self._shortcut.editingFinished.connect(self._on_shortcut_changed)
        layout.addRow("Shortcut", self._shortcut)

        # Launch at login
        self._autostart = QCheckBox()
        self._autostart.setChecked(self._settings.get("autostart", False))
        self._autostart.toggled.connect(self._on_autostart_changed)
        layout.addRow("Launch at login", self._autostart)

    def _on_quality_changed(self, label: str):
        self._settings["model"] = settings.model_for_label(label)
        self._save()

    def _on_shortcut_changed(self):
        text = self._shortcut.text().strip().lower()
        if text:
            self._settings["hotkey"] = text
            self._save()

    def _on_autostart_changed(self, checked: bool):
        self._settings["autostart"] = checked
        self._apply_autostart(checked)
        self._save()

    def _save(self):
        settings.save(self._settings)
        self._on_changed(self._settings)

    def _apply_autostart(self, enabled: bool):
        if sys.platform != "linux":
            return
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / "osw.desktop"
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file.write_text(
                "[Desktop Entry]\nType=Application\nName=OSW\n"
                f"Exec={sys.executable} -m osw\nHidden=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
        elif desktop_file.exists():
            desktop_file.unlink()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_W and event.modifiers() & Qt.ControlModifier:
            self.close()
        else:
            super().keyPressEvent(event)
