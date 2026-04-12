# Roadmap

Planned features, roughly grouped by milestone. Priorities may shift based on
user feedback.

## v0.2

- **Wayland-native global hotkeys** -- remove the X11 dependency for hotkey
  capture on Wayland compositors.
- **macOS / Windows verification** -- test and fix platform-specific issues
  on macOS and Windows (currently marked experimental/unverified).
- **PyPI publishing** -- `pip install localdictate` from PyPI instead of
  requiring a git install.

## v0.3

- **Multilingual improvements** -- better language auto-detection, per-session
  language selection in the settings dialog.
- **Custom model support in UI** -- allow selecting arbitrary faster-whisper
  compatible models from the settings dialog (currently requires manual
  `settings.json` editing).
- **Streaming transcription** -- show partial results while still recording,
  rather than waiting for the recording to finish.
