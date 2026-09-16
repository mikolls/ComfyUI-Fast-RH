import json
import unittest

from _bootstrap import load_plugin_package

load_plugin_package()

from fast_rh_test_package.node import FastRHLoRA, FastRHRandomSeed


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


class RandomSeedNodeTests(unittest.TestCase):
    def test_seed_matches_rh_node_info_list_format(self):
        result = FastRHRandomSeed().build(4, 489861153661777)[0]
        self.assertEqual(result, [{"nodeId": 4, "fieldName": "seed", "fieldValue": "489861153661777"}])

    def test_chains_without_mutating_previous_list(self):
        previous = [{"nodeId": 1, "fieldName": "text", "fieldValue": "hello"}]
        result = FastRHRandomSeed().build(4, 123, previous)[0]
        self.assertEqual(len(previous), 1)
        self.assertEqual(result[-1]["fieldValue"], "123")

    def test_seed_uses_comfyui_control_after_generate(self):
        seed_options = FastRHRandomSeed.INPUT_TYPES()["required"]["seed"][1]
        self.assertTrue(seed_options["control_after_generate"])
