import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _bootstrap import load_plugin_package

load_plugin_package()
from fast_rh_test_package.config import ConfigError, load_config, resolve_config_path


class ConfigPathTests(unittest.TestCase):
    def test_relative_and_absolute_config_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_file = root / "config.alt.json"
            config_file.write_text(json.dumps({"api_key": "private-key"}), encoding="utf-8")
            with patch("fast_rh_test_package.config.PLUGIN_DIR", root):
                self.assertEqual(resolve_config_path("config.alt.json"), config_file)
                self.assertEqual(resolve_config_path(str(config_file)), config_file)
                self.assertEqual(load_config(resolve_config_path("config.alt.json")).api_key, "private-key")
                with self.assertRaisesRegex(ConfigError, "config_path"):
                    resolve_config_path("")
