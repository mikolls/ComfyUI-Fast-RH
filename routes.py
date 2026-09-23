from __future__ import annotations

import asyncio

from aiohttp import web
from server import PromptServer

from .cache import ObjectInfoError, ObjectInfoStore
from .config import ConfigError, PLUGIN_DIR, load_config


STORE = ObjectInfoStore(PLUGIN_DIR / "cache")


async def _response(refresh: bool) -> web.Response:
    try:
        config = load_config()
        result = await asyncio.to_thread(STORE.loras, config, refresh)
        return web.json_response({"ok": True, **result})
    except (ConfigError, ObjectInfoError) as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=502)
    except Exception:
        return web.json_response({"ok": False, "error": "Unexpected Fast-RH server error"}, status=500)


@PromptServer.instance.routes.get("/fast-rh/loras")
async def get_loras(_request: web.Request) -> web.Response:
    return await _response(refresh=False)


@PromptServer.instance.routes.post("/fast-rh/loras/refresh")
async def refresh_loras(_request: web.Request) -> web.Response:
    return await _response(refresh=True)


# Website login is independent of the legacy object_info API key.
from .resources import ResourceError, SESSION_PATH, check_session, list_resources, load_session, save_session

@PromptServer.instance.routes.get("/fast-rh/resources")
async def get_resources(request: web.Request) -> web.Response:
    try:
        result = await asyncio.to_thread(list_resources, request.query.get("source", "public"),
                                         int(request.query.get("page", "1")), request.query.get("q", ""))
        return web.json_response({"ok": True, **result})
    except (ResourceError, ValueError) as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=502)
    except Exception:
        return web.json_response({"ok": False, "error": "模型列表读取失败"}, status=500)

@PromptServer.instance.routes.get("/fast-rh/session")
async def session_status(_request: web.Request) -> web.Response:
    try:
        result = await asyncio.to_thread(check_session)
        return web.json_response({"ok": True, "configured": True, "authenticated": True, **result})
    except ResourceError as exc:
        configured = SESSION_PATH.exists()
        return web.json_response({"ok": True, "configured": configured, "authenticated": False,
                                  "error": str(exc) if configured else "请登录 RunningHub 并设置访问令牌"})

@PromptServer.instance.routes.post("/fast-rh/session")
async def update_session(request: web.Request) -> web.Response:
    if request.content_type != "application/json":
        return web.json_response({"ok": False, "error": "需要 JSON 请求"}, status=415)
    origin = request.headers.get("Origin")
    if origin and origin != f"{request.scheme}://{request.host}":
        return web.json_response({"ok": False, "error": "不允许跨站修改登录"}, status=403)
    try:
        body = await request.json()
        if body.get("clear") is True:
            SESSION_PATH.unlink(missing_ok=True)
        else:
            save_session(str(body.get("site", "")), str(body.get("credential", "")))
        return web.json_response({"ok": True})
    except (ResourceError, ValueError, AttributeError) as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    except OSError:
        return web.json_response({"ok": False, "error": "无法保存本地登录设置"}, status=500)
