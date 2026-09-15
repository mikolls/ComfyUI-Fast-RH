from __future__ import annotations

import json
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


NODE_CLASS_MAPPINGS = {"FastRHLoRA": FastRHLoRA}
NODE_DISPLAY_NAME_MAPPINGS = {"FastRHLoRA": "Fast-RH LoRA"}

