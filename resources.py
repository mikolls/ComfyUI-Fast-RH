"""RunningHub website catalog, separate from the OpenAPI key."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import threading
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .config import PLUGIN_DIR

RESOURCE_CACHE_DIR = PLUGIN_DIR / "resource_cache"
COVERS_DIR = PLUGIN_DIR / "covers"
RESOURCE_CACHE_TTL = 24 * 60 * 60
_CACHE_LOCK = threading.RLock()
MAX_COVER_BYTES = 12 * 1024 * 1024

SESSION_PATH = PLUGIN_DIR / "session.json"
SITES = {"https://www.runninghub.ai", "https://www.runninghub.cn"}

class ResourceError(RuntimeError):
    pass

def save_session(site: str, credential: str, path: Path = SESSION_PATH) -> None:
    if site not in SITES:
        raise ResourceError("Choose the RunningHub .ai or .cn site")
    token = credential.strip()
    if "Rh-Accesstoken=" in token:
        token = token.split("Rh-Accesstoken=", 1)[1].split(";", 1)[0].strip()
    elif token.lower().startswith("bearer "):
        token = token[7:].strip()
    if len(token) > 16384 or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
        raise ResourceError("Paste a Rh-Accesstoken value, Bearer token, or Cookie string")
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"site": site, "access_token": token}, handle)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def load_session(path: Path = SESSION_PATH) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("site") not in SITES or not value.get("access_token"):
            raise ValueError()
        return value
    except (OSError, ValueError, AttributeError):
        raise ResourceError("Open Login Settings and import your RunningHub website login first") from None

def build_query(source: str, page: int, query: str) -> tuple[str, dict]:
    if source not in {"public", "uploaded", "favorites"} or not 1 <= page <= 100000:
        raise ResourceError("Invalid model source or page number")
    body = dict(size=30, current=page, resourceType="LORA", resourceName=query[:200],
                tags=None, baseModels=[], point="")
    if source == "favorites":
        body["operateType"] = 2
        return "/api/likeOrCollect/resource/list", body
    body.update(systemResource=source == "public", choiceModel=True)
    return "/api/resource/list", body

def _image(value) -> str:
    return value if isinstance(value, str) and urlparse(value).scheme == "https" else ""

def normalize_record(record: dict) -> dict:
    versions = []
    for version in record.get("versions") or []:
        name = version.get("resourceStorageName") or version.get("versionResourceName")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.replace("\\", "/")
        if name.startswith("models/loras/"):
            name = name[len("models/loras/"):]
        posters = version.get("posterInfos") or []
        poster = posters[0] if posters else {}
        versions.append(dict(id=str(version.get("id", "")), model=name,
                             version=version.get("version") or "Default version",
                             base_model=version.get("baseModel") or "",
                             image=_image(poster.get("thumbnailUrl") or poster.get("posterUrl"))))
    return dict(id=str(record.get("id", "")), title=record.get("resourceName") or
                (versions[0]["model"] if versions else "Unnamed model"),
                image=_image(record.get("thumbnailUrl") or record.get("posterUrl")),
                collected=record.get("collect") is True, versions=versions)

def check_session(path: Path = SESSION_PATH) -> dict:
    """Ask RunningHub whether the website login is valid and read its signed-key expiry."""
    session = load_session(path)
    try:
        encoded_payload = session["access_token"].split(".")[1]
        padding = "=" * (-len(encoded_payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(encoded_payload + padding))
        token_exp = int(claims["exp"])
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ResourceError("Cannot read the Rh-Accesstoken expiration. Import it again") from None
    if token_exp <= int(time.time()):
        raise ResourceError("Rh-Accesstoken has expired. Update it in Login Settings")
    request = Request(session["site"] + "/api/instance/access/auth", data=b"{}", headers={
        "Authorization": "Bearer " + session["access_token"], "client": "WEB",
        "Content-Type": "application/json", "Accept": "application/json",
        "Origin": session["site"], "Referer": session["site"] + "/",
        "user-language": "zh_CN", "x-rh-lang": "zh",
    })
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ResourceError("RunningHub login has expired. Update Rh-Accesstoken in Login Settings") from None
        raise ResourceError(f"RunningHub login check returned HTTP {exc.code}") from None
    except (URLError, OSError, ValueError):
        raise ResourceError("Cannot check RunningHub login status. Check your network and retry") from None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("code") not in (0, "0") or not isinstance(data, dict):
        message = payload.get("msg") if isinstance(payload, dict) else None
        raise ResourceError("RunningHub login has expired. Update Rh-Accesstoken" + (f" ({message[:100]})" if isinstance(message, str) and message else ""))
    try:
        expires_at = int(data["expire_in"])
    except (KeyError, TypeError, ValueError):
        raise ResourceError("RunningHub login check returned no valid expiration") from None
    if expires_at <= int(__import__("time").time() * 1000):
        raise ResourceError("RunningHub login signature has expired. Update Rh-Accesstoken")
    return {"site": session["site"], "token_expires_at": token_exp * 1000,
            "access_key_expires_at": expires_at}


def fetch_resources(source: str, page: int, query: str) -> dict:
    session = load_session()
    endpoint, body = build_query(source, page, query)
    request = Request(session["site"] + endpoint, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + session["access_token"], "client": "WEB",
        "Content-Type": "application/json", "Accept": "application/json",
        "Origin": session["site"], "Referer": session["site"] + "/",
        "user-language": "zh_CN", "x-rh-lang": "zh",
    })
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ResourceError("Login has expired or access was denied. Update Rh-Accesstoken in Login Settings") from None
        raise ResourceError(f"RunningHub returned HTTP {exc.code}") from None
    except (URLError, OSError, ValueError):
        raise ResourceError("Cannot load the RunningHub model list. Retry later") from None
    if not isinstance(payload, dict) or payload.get("code") not in (0, "0"):
        raise ResourceError("RunningHub rejected the request. Check your login and selected site")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ResourceError("RunningHub list format changed; no model records found")
    return dict(items=[normalize_record(r) for r in data["records"]], page=page,
                total=int(data.get("total") or 0), has_next=data.get("hasNext") is True)


def model_key(model: str) -> str:
    return hashlib.sha256(model.encode("utf-8")).hexdigest()


def _cover_path(key: str) -> Path | None:
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ResourceError("Invalid LoRA file identifier")
    for extension in ("png", "jpg", "webp"):
        path = COVERS_DIR / f"{key}.{extension}"
        if path.is_file():
            return path
    return None


def add_local_covers(items: list[dict]) -> list[dict]:
    for item in items:
        for version in item.get("versions") or []:
            key = model_key(version["model"])
            version["local_cover"] = f"/fast-rh/covers/{key}" if _cover_path(key) else ""
    return items


def list_resources(source: str, page: int, query: str, refresh: bool = False) -> dict:
    build_query(source, page, query)
    session = load_session()
    account_key = hashlib.sha256(session["access_token"].encode("utf-8")).hexdigest()
    cache_key = hashlib.sha256(json.dumps([session["site"], account_key, source, page, query.casefold()], ensure_ascii=False).encode("utf-8")).hexdigest()
    cache_path = RESOURCE_CACHE_DIR / f"{cache_key}.json"
    with _CACHE_LOCK:
        if not refresh:
            try:
                envelope = json.loads(cache_path.read_text(encoding="utf-8"))
                age = time.time() - float(envelope["fetched_at"])
                if age < RESOURCE_CACHE_TTL and isinstance(envelope.get("result"), dict):
                    result = dict(envelope["result"])
                    result["items"] = add_local_covers(result["items"])
                    result["source"] = "cache"
                    result["cached_at"] = envelope["fetched_at"]
                    return result
            except (OSError, ValueError, KeyError, TypeError):
                pass
        result = fetch_resources(source, page, query)
        fetched_at = time.time()
        RESOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=RESOURCE_CACHE_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"fetched_at": fetched_at, "result": result}, handle, ensure_ascii=False)
            os.replace(temporary, cache_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        result = dict(result)
        result["items"] = add_local_covers(result["items"])
        result["source"] = "remote"
        result["cached_at"] = fetched_at
        return result


def clear_resource_cache() -> int:
    removed = 0
    with _CACHE_LOCK:
        if RESOURCE_CACHE_DIR.exists():
            for path in RESOURCE_CACHE_DIR.glob("*.json"):
                path.unlink(missing_ok=True)
                removed += 1
    return removed


def save_model_cover(key: str, content_type: str, data: bytes) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ResourceError("Invalid LoRA file identifier")
    if not data or len(data) > MAX_COVER_BYTES:
        raise ResourceError("Cover must be nonempty and no larger than 12 MB")
    signatures = {
        "image/png": ("png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
        "image/jpeg": ("jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
        "image/webp": ("webp", lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    }
    specification = signatures.get(content_type.lower())
    if not specification or not specification[1](data):
        raise ResourceError("Cover must be a PNG, JPG, or WebP image")
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    extension = specification[0]
    for old_extension in ("png", "jpg", "webp"):
        if old_extension != extension:
            (COVERS_DIR / f"{key}.{old_extension}").unlink(missing_ok=True)
    destination = COVERS_DIR / f"{key}.{extension}"
    fd, temporary = tempfile.mkstemp(dir=COVERS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination.name


def delete_model_cover(key: str) -> bool:
    path = _cover_path(key)
    if path is None:
        return False
    path.unlink(missing_ok=True)
    return True
