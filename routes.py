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

