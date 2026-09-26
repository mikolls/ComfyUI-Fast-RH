from __future__ import annotations

import asyncio
import re

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
from .resources import MAX_COVER_BYTES, ResourceError, SESSION_PATH, check_session, clear_resource_cache, delete_model_cover, list_resources, load_session, model_key, save_model_cover, save_session

@PromptServer.instance.routes.get("/fast-rh/resources")
async def get_resources(request: web.Request) -> web.Response:
    try:
        result = await asyncio.to_thread(list_resources, request.query.get("source", "public"),
                                         int(request.query.get("page", "1")), request.query.get("q", ""),
                                         request.query.get("refresh") == "1")
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


@PromptServer.instance.routes.post("/fast-rh/resources/cache/clear")
async def clear_resource_cache_route(request: web.Request) -> web.Response:
    if request.content_type != "application/json":
        return web.json_response({"ok": False, "error": "需要 JSON 请求"}, status=415)
    origin = request.headers.get("Origin")
    if origin and origin != f"{request.scheme}://{request.host}":
        return web.json_response({"ok": False, "error": "不允许跨站清理缓存"}, status=403)
    removed = await asyncio.to_thread(clear_resource_cache)
    return web.json_response({"ok": True, "removed": removed})


def _cover_origin_allowed(request: web.Request) -> bool:
    origin = request.headers.get("Origin")
    return not origin or origin == f"{request.scheme}://{request.host}"


@PromptServer.instance.routes.post("/fast-rh/covers")
async def upload_model_cover(request: web.Request) -> web.Response:
    if not _cover_origin_allowed(request):
        return web.json_response({"ok": False, "error": "不允许跨站修改封面"}, status=403)
    if request.content_type != "multipart/form-data":
        return web.json_response({"ok": False, "error": "需要上传图片文件"}, status=415)
    try:
        reader = await request.multipart()
        model_field = await reader.next()
        if model_field is None or model_field.name != "model":
            raise ResourceError("没有指定 LoRA 模型")
        model = (await model_field.text()).strip()
        if not model or len(model) > 1024:
            raise ResourceError("LoRA 文件名无效")
        field = await reader.next()
        content_type = field.headers.get("Content-Type", "") if field is not None else ""
        if field is None or field.name != "image" or not content_type:
            raise ResourceError("没有选择封面图片")
        data = await field.read_chunk(size=65536)
        chunks = [data]
        size = len(data)
        while size <= MAX_COVER_BYTES:
            data = await field.read_chunk(size=65536)
            if not data:
                break
            size += len(data)
            if size > MAX_COVER_BYTES:
                raise ResourceError("封面不能超过 12 MB")
            chunks.append(data)
        key = model_key(model)
        filename = await asyncio.to_thread(save_model_cover, key, content_type, b"".join(chunks))
        return web.json_response({"ok": True, "filename": filename, "url": f"/fast-rh/covers/{key}"})
    except ResourceError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    except (ValueError, AssertionError):
        return web.json_response({"ok": False, "error": "封面文件无效"}, status=400)


@PromptServer.instance.routes.get("/fast-rh/covers/{key}")
async def get_model_cover(request: web.Request) -> web.StreamResponse:
    from .resources import _cover_path
    try:
        path = _cover_path(request.match_info["key"])
    except ResourceError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    if path is None:
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "no-cache"})


@PromptServer.instance.routes.delete("/fast-rh/covers")
async def remove_model_cover(request: web.Request) -> web.Response:
    if not _cover_origin_allowed(request):
        return web.json_response({"ok": False, "error": "不允许跨站修改封面"}, status=403)
    try:
        model = request.query.get("model", "")
        if not model or len(model) > 1024:
            raise ResourceError("LoRA 文件名无效")
        removed = await asyncio.to_thread(delete_model_cover, model_key(model))
        return web.json_response({"ok": True, "removed": removed})
    except ResourceError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
