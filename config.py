from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


PLUGIN_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PLUGIN_DIR / "config.json"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunningHubConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 30.0


def load_config(path: Path = CONFIG_PATH) -> RunningHubConfig:
    if not path.exists():
        raise ConfigError(
            f"Missing {path.name}. Copy config.example.json to config.json and set your API key."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read {path.name}: {exc}") from exc

    base_url = str(raw.get("base_url", "")).strip().rstrip("/")
    api_key = str(raw.get("api_key", "")).strip()
    try:
        timeout = float(raw.get("timeout_seconds", 30))
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout_seconds must be a number") from exc

    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "www.runninghub.cn",
        "runninghub.cn",
        "www.runninghub.ai",
        "runninghub.ai",
    }:
        raise ConfigError("base_url must be an HTTPS runninghub.cn or runninghub.ai URL")
    if not api_key or api_key == "replace-with-your-runninghub-api-key":
        raise ConfigError("api_key is not configured")
    if not 1 <= timeout <= 300:
        raise ConfigError("timeout_seconds must be between 1 and 300")
    return RunningHubConfig(base_url=base_url, api_key=api_key, timeout_seconds=timeout)

