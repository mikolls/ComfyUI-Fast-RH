import json
import unittest

from _bootstrap import load_plugin_package

load_plugin_package()

from fast_rh_test_package.node import FastRHLoRA, FastRHRandomSeed, FastRHKSampler


class NodeTests(unittest.TestCase):
    def test_lora_outputs_official_node_info_list_and_chains(self):
        rows = [
            {"slot": "face", "model": "face.safetensors", "nodeId": 12, "enabled": True, "strength_model": 0.8, "strength_clip": 0.7},
            {"slot": "style", "model": "", "enabled": False},
        ]
        previous = [{"nodeId": 3, "fieldName": "image", "fieldValue": "uploaded.png"}]
        result = FastRHLoRA().build(json.dumps(rows), previous)[0]
        self.assertEqual(previous, [{"nodeId": 3, "fieldName": "image", "fieldValue": "uploaded.png"}])
        self.assertEqual(result, previous + [
            {"nodeId": 12, "fieldName": "lora_name", "fieldValue": "face.safetensors"},
            {"nodeId": 12, "fieldName": "strength_model", "fieldValue": "0.8"},
            {"nodeId": 12, "fieldName": "strength_clip", "fieldValue": "0.7"},
        ])
        self.assertEqual(FastRHLoRA.RETURN_TYPES, ("ARRAY",))
        self.assertEqual(FastRHLoRA.INPUT_TYPES()["optional"]["previousNodeInfoList"][0], "ARRAY")

    def test_enabled_lora_validation(self):
        cases = [
            ([{"slot": "", "model": "x"}], "empty slot"),
            ([{"slot": "a"}, {"slot": "a"}], "Duplicate"),
            ([{"slot": "a", "enabled": True, "model": ""}], "no model"),
            ([{"slot": "a", "enabled": True, "model": "x", "nodeId": 0}], "nodeId"),
            ([{"slot": "a", "enabled": True, "model": "x", "nodeId": 2, "strength_model": 101}], "between -100 and 100"),
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


class KSamplerNodeTests(unittest.TestCase):
    def test_maps_all_remote_ksampler_fields_and_chains(self):
        previous = [{"nodeId": 2, "fieldName": "image", "fieldValue": "uploaded.png"}]
        result = FastRHKSampler().build(
            7, 489890933660723, 30, 4.0, "euler_ancestral", "simple", 1.0,
            previous,
        )[0]
        self.assertEqual(len(previous), 1)
        self.assertEqual(result, previous + [
            {"nodeId": 7, "fieldName": "seed", "fieldValue": "489890933660723"},
            {"nodeId": 7, "fieldName": "steps", "fieldValue": "30"},
            {"nodeId": 7, "fieldName": "cfg", "fieldValue": "4.0"},
            {"nodeId": 7, "fieldName": "sampler_name", "fieldValue": "euler_ancestral"},
            {"nodeId": 7, "fieldName": "scheduler", "fieldValue": "simple"},
            {"nodeId": 7, "fieldName": "denoise", "fieldValue": "1.0"},
        ])
        self.assertEqual(FastRHKSampler.RETURN_TYPES, ("ARRAY",))
        self.assertEqual(
            FastRHKSampler.INPUT_TYPES()["optional"]["previousNodeInfoList"][0],
            "ARRAY",
        )
        self.assertTrue(
            FastRHKSampler.INPUT_TYPES()["required"]["seed"][1]["control_after_generate"]
        )

    def test_rejects_invalid_remote_values(self):
        args = [7, 1, 30, 4.0, "euler", "simple", 1.0]
        for index, value, message in [
            (0, 0, "nodeId"),
            (1, -1, "Seed"),
            (2, 0, "steps"),
            (3, float("nan"), "cfg"),
            (4, "", "sampler"),
            (6, 1.2, "denoise"),
        ]:
            with self.subTest(index=index):
                invalid = args.copy()
                invalid[index] = value
                with self.assertRaisesRegex(ValueError, message):
                    FastRHKSampler().build(*invalid)
