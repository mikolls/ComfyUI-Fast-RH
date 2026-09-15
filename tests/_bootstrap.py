from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_plugin_package():
    """Load the plugin under a stable test-only name, regardless of its folder name."""
    package_name = "fast_rh_test_package"
    if package_name in sys.modules:
        return package_name

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        package_name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Fast-RH plugin package")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return package_name

