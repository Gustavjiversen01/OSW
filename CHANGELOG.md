# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-06

### Added

- System-tray application with global hotkey (`Ctrl+Space`) for push-to-toggle dictation.
- Whisper-based speech-to-text via faster-whisper with five quality presets
  (Fast, Balanced, Quality, High, Maximum).
- Automatic one-time model download from HuggingFace with tray status indicator.
- Settings dialog: quality level, microphone selection, custom hotkey, launch-at-login.
- Text injection via `xdotool` (X11), `wtype`/`ydotool` (Wayland), or `pynput` (macOS/Windows).
- Clipboard-paste fallback when direct text injection is unavailable.
- Auto-detect CPU/CUDA with graceful GPU-to-CPU fallback.
- Migration from legacy `osw` config directory.
- 28 passing tests covering engine, settings, hotkey, and controller logic.

[0.1.0]: https://github.com/Gustavjiversen01/localdictate/releases/tag/v0.1.0
