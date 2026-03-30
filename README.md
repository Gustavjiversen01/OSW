# OSW

Open Source Whisper -- lightweight voice-to-text dictation.
Hold a hotkey, speak, release. Text appears at your cursor.

- Local and offline -- powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- Push-to-hold dictation with configurable hotkey (default: `Ctrl+Space`)
- System tray with minimal settings UI
- GPU (CUDA) with automatic CPU fallback
- Linux (X11 + Wayland), Windows, macOS
- Python 3.10+

## Install

```bash
pip install git+https://github.com/Gustavjiversen01/OSW.git
```

On Linux, install PortAudio and add yourself to the `input` group (re-login required):

```bash
sudo apt install portaudio19-dev
sudo usermod -aG input $USER
```

For development:

```bash
git clone https://github.com/Gustavjiversen01/OSW.git
cd OSW
pip install -e .
```

## Usage

```
osw
```

Hold `Ctrl+Space`, speak, release. Right-click the tray icon to open Settings.

## Models

Models are **not bundled** -- they download automatically from HuggingFace on first use.

| Label | Model | Size | Notes |
|---|---|---|---|
| Fast | [small.en](https://huggingface.co/Systran/faster-whisper-small.en) | ~500 MB | CPU-friendly, good quality |
| Balanced | [distil-medium.en](https://huggingface.co/Systran/faster-distil-whisper-medium.en) | ~800 MB | Default. Best speed/quality tradeoff |
| Quality | [distil-large-v3](https://huggingface.co/Systran/faster-distil-whisper-large-v3) | ~1.5 GB | High accuracy, benefits from GPU |
| Maximum | [large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) | ~3 GB | Best accuracy, needs GPU for real-time |

To use a custom model, edit `~/.config/osw/settings.json` and set `"model"` to any HuggingFace model ID compatible with faster-whisper.

## Troubleshooting

**Linux (Wayland)** -- Requires `input` group membership for evdev-based hotkey detection. For text paste, install `ydotool` or `wtype`. On X11, `xdotool` works.

**No GPU** -- OSW falls back to CPU automatically with int8 quantization.

**macOS** -- Grant accessibility permissions when prompted for global hotkey detection.

## License

[MIT](LICENSE)
