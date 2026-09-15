import json
import unittest

from _bootstrap import load_plugin_package

load_plugin_package()

from fast_rh_test_package.node import FastRHLoRA


class NodeTests(unittest.TestCase):
    def test_node_builds_ordered_contract(self):
        rows = [
            {"slot": "face", "model": "face.safetensors", "enabled": True, "strength_model": 0.8, "strength_clip": 0.7},
            {"slot": "style", "model": "style.safetensors", "enabled": False, "strength_model": 1, "strength_clip": 1},
        ]
        result = FastRHLoRA().build(json.dumps(rows))[0]
        self.assertEqual(result[0], {"slot": "face", "model": "face.safetensors", "enabled": True, "strength_model": 0.8, "strength_clip": 0.7, "order": 0})
        self.assertFalse(result[1]["enabled"])
        self.assertEqual(result[1]["order"], 1)

    def test_node_validation(self):
        cases = [
            ([{"slot": "", "model": "x"}], "empty slot"),
            ([{"slot": "a", "model": "x"}, {"slot": "a", "model": "y"}], "Duplicate"),
            ([{"slot": "a", "model": ""}], "no model"),
            ([{"slot": "a", "model": "x", "strength_model": 101}], "between -100 and 100"),
        ]
        for rows, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                FastRHLoRA().build(json.dumps(rows))
