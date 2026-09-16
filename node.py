from __future__ import annotations

import json
import secrets
from typing import Any


DEFAULT_ROWS = [
    {
        "slot": f"lora_{index + 1}",
        "model": "",
        "enabled": False,
        "strength_model": 1.0,
        "strength_clip": 1.0,
    }
    for index in range(4)
]


class FastRHLoRA:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "configs_json": (
                    "STRING",
                    {"default": json.dumps(DEFAULT_ROWS), "multiline": False},
                )
            }
        }

    RETURN_TYPES = ("RH_LORA_CONFIG_LIST",)
    RETURN_NAMES = ("lora_configs",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Select cached RunningHub LoRAs and build slot-based remote overrides."

    def build(self, configs_json: str):
        try:
            rows: Any = json.loads(configs_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Fast-RH LoRA configuration is not valid JSON") from exc
        if not isinstance(rows, list) or not 1 <= len(rows) <= 16:
            raise ValueError("Fast-RH LoRA requires between 1 and 16 entries")

        result = []
        slots: set[str] = set()
        for order, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"LoRA entry {order + 1} is invalid")
            slot = str(row.get("slot", "")).strip()
            model = str(row.get("model", "")).strip()
            if not slot:
                raise ValueError(f"LoRA entry {order + 1} has an empty slot")
            if slot in slots:
                raise ValueError(f"Duplicate LoRA slot: {slot}")
            if not model:
                raise ValueError(f"LoRA slot '{slot}' has no model selected")
            slots.add(slot)
            try:
                strength_model = float(row.get("strength_model", 1.0))
                strength_clip = float(row.get("strength_clip", 1.0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"LoRA slot '{slot}' has an invalid strength") from exc
            if not -100.0 <= strength_model <= 100.0 or not -100.0 <= strength_clip <= 100.0:
                raise ValueError(f"LoRA slot '{slot}' strength must be between -100 and 100")
            result.append(
                {
                    "slot": slot,
                    "model": model,
                    "enabled": bool(row.get("enabled", True)),
                    "strength_model": strength_model,
                    "strength_clip": strength_clip,
                    "order": order,
                }
            )
        return (result,)


class FastRHRandomSeed:
    """Build a RunningHub-compatible seed override, optionally chained."""

    MAX_SEED = 0xFFFFFFFFFFFFFFFF

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "nodeId": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                "mode": (["random", "custom"], {"default": "random"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": cls.MAX_SEED, "step": 1}),
            },
            "optional": {"previousNodeInfoList": ("ARRAY", {"default": []})},
        }

    RETURN_TYPES = ("ARRAY",)
    RETURN_NAMES = ("nodeInfoList",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Create a random or custom seed override compatible with RH Node Info List."

    @classmethod
    def IS_CHANGED(cls, nodeId, mode, seed, previousNodeInfoList=None):
        if mode == "random":
            return float("nan")
        return (nodeId, mode, seed, repr(previousNodeInfoList))

    def build(self, nodeId: int, mode: str, seed: int, previousNodeInfoList=None):
        if mode not in {"random", "custom"}:
            raise ValueError(f"Unsupported seed mode: {mode}")
        selected_seed = secrets.randbelow(self.MAX_SEED + 1) if mode == "random" else int(seed)
        if not 0 <= selected_seed <= self.MAX_SEED:
            raise ValueError(f"Seed must be between 0 and {self.MAX_SEED}")
        node_info_list = list(previousNodeInfoList or [])
        node_info_list.append({"nodeId": int(nodeId), "fieldName": "seed", "fieldValue": str(selected_seed)})
        return (node_info_list,)


NODE_CLASS_MAPPINGS = {"FastRHLoRA": FastRHLoRA, "FastRHRandomSeed": FastRHRandomSeed}
NODE_DISPLAY_NAME_MAPPINGS = {
    "FastRHLoRA": "Fast-RH LoRA",
    "FastRHRandomSeed": "Fast-RH Random Seed",
}

