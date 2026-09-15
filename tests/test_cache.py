import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _bootstrap import load_plugin_package

load_plugin_package()

from fast_rh_test_package.cache import ObjectInfoError, ObjectInfoStore, extract_loras
from fast_rh_test_package.config import RunningHubConfig


CONFIG = RunningHubConfig("https://www.runninghub.cn", "secret", 10)
OBJECT_INFO = {
    "LoraLoader": {"input": {"required": {"lora_name": [["z.safetensors", "A.safetensors", "A.safetensors"], {}]}}}
}


class CacheTests(unittest.TestCase):
    def test_first_access_fetches_once_then_uses_cache(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            calls = []
            store = ObjectInfoStore(path, lambda config: calls.append(config) or OBJECT_INFO)
            first = store.loras(CONFIG)
            second = store.loras(CONFIG)
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["source"], "remote")
            self.assertEqual(second["source"], "cache")
            self.assertEqual(second["loras"], ["A.safetensors", "z.safetensors"])
            cache_text = next(path.glob("*.json")).read_text(encoding="utf-8")
            self.assertNotIn("secret", cache_text)

    def test_refresh_replaces_cache_only_after_success(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            values = iter([OBJECT_INFO, ObjectInfoError("offline")])

            def fetch(_config):
                value = next(values)
                if isinstance(value, Exception):
                    raise value
                return value

            store = ObjectInfoStore(path, fetch)
            store.loras(CONFIG)
            before = next(path.glob("*.json")).read_bytes()
            with self.assertRaisesRegex(ObjectInfoError, "offline"):
                store.loras(CONFIG, refresh=True)
            self.assertEqual(next(path.glob("*.json")).read_bytes(), before)
            self.assertEqual(store.loras(CONFIG)["source"], "cache")

    def test_different_site_or_key_uses_another_cache(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            calls = []
            store = ObjectInfoStore(path, lambda config: calls.append(config) or OBJECT_INFO)
            store.loras(CONFIG)
            store.loras(RunningHubConfig("https://www.runninghub.ai", "secret", 10))
            store.loras(RunningHubConfig("https://www.runninghub.cn", "other", 10))
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(list(path.glob("*.json"))), 3)

    def test_corrupt_cache_recovers_with_remote_fetch(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            calls = []
            store = ObjectInfoStore(path, lambda config: calls.append(1) or OBJECT_INFO)
            store.loras(CONFIG)
            next(path.glob("*.json")).write_text("not-json", encoding="utf-8")
            self.assertEqual(store.loras(CONFIG)["source"], "remote")
            self.assertEqual(len(calls), 2)

    def test_extract_loras_reports_missing_loader(self):
        with self.assertRaisesRegex(ObjectInfoError, "LoraLoader"):
            extract_loras({})
