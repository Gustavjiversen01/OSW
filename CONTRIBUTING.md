# Contributing to LocalDictate

Thanks for your interest in contributing. This document covers the basics.

## Dev setup

```bash
git clone https://github.com/Gustavjiversen01/localdictate.git
cd localdictate
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Debian/Ubuntu you also need the PortAudio header:

```bash
sudo apt install portaudio19-dev
```

## Running tests

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

The `QT_QPA_PLATFORM=offscreen` variable lets PySide6 run without a display
server, which is required in CI and headless environments.

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and
formatting. CI will reject PRs that fail `ruff check` or `ruff format --check`.

To check locally:

```bash
pip install ruff
ruff check .
ruff format --check .
```

To auto-fix most issues:

```bash
ruff check --fix .
ruff format .
```

## Commit sign-off (DCO)

All commits must carry a `Signed-off-by` line (the
[Developer Certificate of Origin](https://developercertificate.org/)):

```bash
git commit -s -m "fix: describe the change"
```

## Pull request checklist

Before opening a PR, verify:

- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q` passes
- [ ] CHANGELOG.md is updated (if user-facing)
- [ ] Commit(s) are signed off (`git commit -s`)
