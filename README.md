<p align="center">
  <h1 align="center">OSW</h1>
  <p align="center">Open Source Whisper — voice-to-text that stays out of your way.</p>
</p>

<p align="center">
  Press a shortcut. Speak. Press again. Text appears at your cursor.
</p>

---

I wanted something like Apple's dictation — but local, open, and on Linux. Every option I found was either cloud-dependent, paywalled, or abandoned. So I built it myself. No subscriptions, no telemetry, no profit motive. Just a tool that works. If that's what you're looking for too, this is for you.

---

**Local and private** — runs entirely on your machine. No cloud, no accounts, no data leaves your computer.

**Zero config** — launches into system tray, works immediately with your default microphone.

**Unobtrusive** — a small red dot appears while recording. That's it.

## Install

```bash
# Linux
sudo apt install portaudio19-dev
git clone https://github.com/Gustavjiversen01/OSW.git
cd OSW
pip install .

# Run
osw
```

## How it works

1. Press `Ctrl+Space` to start dictating
2. Speak naturally
3. Press `Ctrl+Space` to stop
4. Your words are typed into whatever app is focused

Right-click the tray icon to open **Settings**, where you can configure:

| Setting | Options |
|---|---|
| **Quality** | Fast, Balanced (default), Quality, Maximum |
| **Microphone** | Any connected input device, or system default |
| **Shortcut** | Click Record, then press any key combination |
| **Launch at login** | Auto-start with your desktop |

## Models

Models download automatically from HuggingFace on first use. Your clipboard is never touched.

| Label | Model | Size | Notes |
|---|---|---|---|
| Fast | [small.en](https://huggingface.co/Systran/faster-whisper-small.en) | ~500 MB | Lightweight, good quality |
| **Balanced** | [distil-medium.en](https://huggingface.co/Systran/faster-distil-whisper-medium.en) | **~800 MB** | **Default — best speed/quality tradeoff** |
| Quality | [distil-large-v3](https://huggingface.co/Systran/faster-distil-whisper-large-v3) | ~1.5 GB | High accuracy |
| Maximum | [large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) | ~3 GB | Best accuracy, slower |

Custom models: set `"model"` in `~/.config/osw/settings.json` to any [faster-whisper](https://github.com/SYSTRAN/faster-whisper) compatible model ID.

## Requirements

- Python 3.10+
- Linux (X11), Windows, macOS
- PortAudio (`portaudio19-dev` on Debian/Ubuntu)

## License

[MIT](LICENSE)
