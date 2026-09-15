from .node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web"

try:
    from . import routes as _routes  # noqa: F401
except ModuleNotFoundError as exc:
    # Allows the data/node modules to be imported outside ComfyUI (for tests).
    if exc.name != "server":
        raise

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

