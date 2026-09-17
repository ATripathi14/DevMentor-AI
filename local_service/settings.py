import json
import os

_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

_DEFAULT_SETTINGS = {
    "privacy_mode": "local_only",
    "confidence_threshold": 0.6,
}


def load_settings() -> dict:
    """Loads settings from settings.json, creating it with defaults if it doesn't exist."""
    if not os.path.exists(_SETTINGS_FILE):
        save_settings(_DEFAULT_SETTINGS)
        return _DEFAULT_SETTINGS.copy()

    with open(_SETTINGS_FILE, "r") as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    """Writes the given settings dict to settings.json."""
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)