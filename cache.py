from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import RunningHubConfig


class ObjectInfoError(RuntimeError):
    pass


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _identity(config: RunningHubConfig) -> tuple[str, str]:
    return config.base_url.lower(), _fingerprint(config.api_key)


def fetch_object_info(config: RunningHubConfig) -> dict[str, Any]:
    url = f"{config.base_url}/proxy/{config.api_key}/object_info"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        raise ObjectInfoError(f"RunningHub returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ObjectInfoError(f"Unable to reach RunningHub: {exc.reason if isinstance(exc, URLError) else exc}") from exc
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObjectInfoError("RunningHub returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ObjectInfoError("RunningHub object_info response must be a JSON object")
    return result


def extract_loras(object_info: dict[str, Any]) -> list[str]:
    try:
        spec = object_info["LoraLoader"]["input"]["required"]["lora_name"]
    except (KeyError, TypeError) as exc:
        raise ObjectInfoError("LoraLoader.input.required.lora_name is missing from object_info") from exc

    options: Any = spec
    if isinstance(spec, list) and spec and isinstance(spec[0], list):
        options = spec[0]
    if not isinstance(options, list):
        raise ObjectInfoError("LoraLoader lora_name options have an unsupported format")
    return sorted({item for item in options if isinstance(item, str) and item.strip()}, key=str.casefold)


class ObjectInfoStore:
    def __init__(
        self,
        cache_dir: Path,
        fetcher: Callable[[RunningHubConfig], dict[str, Any]] = fetch_object_info,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.fetcher = fetcher
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _cache_path(self, config: RunningHubConfig) -> Path:
        site, key_fp = _identity(config)
        return self.cache_dir / f"object_info_{_fingerprint(site)}_{key_fp}.json"

    def _lock_for(self, path: Path) -> threading.Lock:
        key = str(path)
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _read(self, path: Path, config: RunningHubConfig) -> dict[str, Any]:
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ObjectInfoError(f"Cached object_info is unreadable: {exc}") from exc
        expected_site, expected_fp = _identity(config)
        if envelope.get("base_url", "").lower() != expected_site or envelope.get("api_key_fingerprint") != expected_fp:
            raise ObjectInfoError("Cached object_info belongs to a different RunningHub configuration")
        if not isinstance(envelope.get("object_info"), dict):
            raise ObjectInfoError("Cached object_info is invalid")
        return envelope

    def _write(self, path: Path, config: RunningHubConfig, object_info: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "base_url": config.base_url,
            "api_key_fingerprint": _fingerprint(config.api_key),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "object_info": object_info,
        }
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=self.cache_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(envelope, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return envelope

    def get(self, config: RunningHubConfig, refresh: bool = False) -> tuple[dict[str, Any], str]:
        path = self._cache_path(config)
        with self._lock_for(path):
            if not refresh and path.exists():
                try:
                    return self._read(path, config), "cache"
                except ObjectInfoError:
                    # A corrupt cache cannot be used; recover it with one remote request.
                    pass
            object_info = self.fetcher(config)
            return self._write(path, config, object_info), "remote"

    def loras(self, config: RunningHubConfig, refresh: bool = False) -> dict[str, Any]:
        envelope, source = self.get(config, refresh=refresh)
        return {
            "loras": extract_loras(envelope["object_info"]),
            "fetched_at": envelope["fetched_at"],
            "source": source,
        }

