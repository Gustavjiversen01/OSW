import json
from pathlib import Path

from platformdirs import user_config_dir

MODELS = {
    "Fast": "small.en",
    "Balanced": "distil-medium.en",
    "Quality": "distil-large-v3",
    "Maximum": "large-v3",
}

DEFAULTS = {
    "model": "distil-medium.en",
    "hotkey": "ctrl+space",
    "autostart": False,
    "onboarding_shown": False,
}

_config_dir = Path(user_config_dir("osw"))
_config_file = _config_dir / "settings.json"


def load() -> dict:
    if _config_file.exists():
        with open(_config_file) as f:
            stored = json.load(f)
        return {**DEFAULTS, **stored}
    return dict(DEFAULTS)


def save(settings: dict):
    _config_dir.mkdir(parents=True, exist_ok=True)
    with open(_config_file, "w") as f:
        json.dump(settings, f, indent=2)


def label_for_model(model_id: str) -> str:
    for label, mid in MODELS.items():
        if mid == model_id:
            return label
    return model_id


def model_for_label(label: str) -> str:
    return MODELS.get(label, label)
