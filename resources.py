"""RunningHub website catalog, separate from the OpenAPI key."""
from __future__ import annotations
import base64
import json
import os
import re
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .config import PLUGIN_DIR

SESSION_PATH = PLUGIN_DIR / "session.json"
SITES = {"https://www.runninghub.ai", "https://www.runninghub.cn"}

class ResourceError(RuntimeError):
    pass

def save_session(site: str, credential: str, path: Path = SESSION_PATH) -> None:
    if site not in SITES:
        raise ResourceError("请选择 RunningHub .ai 或 .cn 站点")
    token = credential.strip()
    if "Rh-Accesstoken=" in token:
        token = token.split("Rh-Accesstoken=", 1)[1].split(";", 1)[0].strip()
    elif token.lower().startswith("bearer "):
        token = token[7:].strip()
    if len(token) > 16384 or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
        raise ResourceError("请粘贴 Rh-Accesstoken 的值、Bearer token 或 Cookie 字符串")
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
        raise ResourceError("请先点击「登录设置」导入 RunningHub 网站登录信息") from None

def build_query(source: str, page: int, query: str) -> tuple[str, dict]:
    if source not in {"public", "uploaded", "favorites"} or not 1 <= page <= 100000:
        raise ResourceError("模型来源或页码无效")
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
                             version=version.get("version") or "默认版本",
                             base_model=version.get("baseModel") or "",
                             image=_image(poster.get("thumbnailUrl") or poster.get("posterUrl"))))
    return dict(id=str(record.get("id", "")), title=record.get("resourceName") or
                (versions[0]["model"] if versions else "未命名模型"),
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
        raise ResourceError("无法读取 Rh-Accesstoken 的过期时间，请重新导入") from None
    if token_exp <= int(time.time()):
        raise ResourceError("Rh-Accesstoken 已过期，请在「登录设置」更新令牌")
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
            raise ResourceError("RunningHub 登录已过期，请在「登录设置」更新 Rh-Accesstoken") from None
        raise ResourceError(f"RunningHub 登录检查返回 HTTP {exc.code}") from None
    except (URLError, OSError, ValueError):
        raise ResourceError("无法检查 RunningHub 登录状态，请检查网络后重试") from None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("code") not in (0, "0") or not isinstance(data, dict):
        message = payload.get("msg") if isinstance(payload, dict) else None
        raise ResourceError("RunningHub 登录已过期，请更新 Rh-Accesstoken" + (f"（{message[:100]}）" if isinstance(message, str) and message else ""))
    try:
        expires_at = int(data["expire_in"])
    except (KeyError, TypeError, ValueError):
        raise ResourceError("RunningHub 登录检查未返回有效的过期时间") from None
    if expires_at <= int(__import__("time").time() * 1000):
        raise ResourceError("RunningHub 登录签名已过期，请更新 Rh-Accesstoken")
    return {"site": session["site"], "token_expires_at": token_exp * 1000,
            "access_key_expires_at": expires_at}


def list_resources(source: str, page: int, query: str) -> dict:
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
            raise ResourceError("登录已失效或无访问权限，请在登录设置中更新 Rh-Accesstoken") from None
        raise ResourceError(f"RunningHub 返回 HTTP {exc.code}") from None
    except (URLError, OSError, ValueError):
        raise ResourceError("无法读取 RunningHub 模型列表，请稍后重试") from None
    if not isinstance(payload, dict) or payload.get("code") not in (0, "0"):
        raise ResourceError("RunningHub 拒绝了请求，请检查登录是否过期以及站点是否匹配")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ResourceError("RunningHub 列表格式发生变化，未找到模型记录")
    return dict(items=[normalize_record(r) for r in data["records"]], page=page,
                total=int(data.get("total") or 0), has_next=data.get("hasNext") is True)
