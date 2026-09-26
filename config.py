from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PLUGIN_DIR / "config.json"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunningHubConfig:
    api_key: str


def resolve_config_path(value: str) -> Path:
    location = str(value).strip()
    if not location:
        raise ConfigError("config_path is required")
    path = Path(location).expanduser()
    return path if path.is_absolute() else PLUGIN_DIR / path


def load_config(path: Path = CONFIG_PATH) -> RunningHubConfig:
    if not path.exists():
        raise ConfigError(
            f"Missing {path.name}. Copy config.example.json to config.json and set your API key."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read {path.name}: {exc}") from exc

    api_key = str(raw.get("api_key", "")).strip()
    if not api_key or api_key == "replace-with-your-runninghub-api-key":
        raise ConfigError("api_key is not configured")
    return RunningHubConfig(api_key=api_key)
