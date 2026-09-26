from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from .config import resolve_config_path, load_config


DEFAULT_ROWS = [
    {
        "slot": f"lora_{index + 1}",
        "model": "",
        "nodeId": 0,
        "enabled": False,
        "strength_model": 1.0,
        "strength_clip": 1.0,
        "include_strength_clip": False,
    }
    for index in range(1)
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
            },
            "optional": {"previousNodeInfoList": ("ARRAY", {"default": []})},
        }

    RETURN_TYPES = ("ARRAY",)
    RETURN_NAMES = ("nodeInfoList",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Select a RunningHub LoRA, map it to a remote loader nodeId, and build an RH Node Info List for the official workflow executor."

    def build(self, configs_json: str, previousNodeInfoList=None):
        try:
            rows: Any = json.loads(configs_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Fast-RH LoRA configuration is not valid JSON") from exc
        if not isinstance(rows, list) or not 1 <= len(rows) <= 16:
            raise ValueError("Fast-RH LoRA requires between 1 and 16 entries")

        result = list(previousNodeInfoList or [])
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
            if not row.get("enabled", False):
                slots.add(slot)
                continue
            if not model:
                raise ValueError(f"LoRA slot '{slot}' has no model selected")
            raw_node_id = row.get("nodeId", 0)
            if isinstance(raw_node_id, float) and not raw_node_id.is_integer():
                raise ValueError(f"LoRA slot '{slot}' has an invalid nodeId")
            try:
                node_id = int(raw_node_id)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"LoRA slot '{slot or order + 1}' has an invalid nodeId") from exc
            if isinstance(raw_node_id, bool) or not 1 <= node_id <= 2147483647:
                raise ValueError(f"LoRA slot '{slot}' nodeId must be between 1 and 2147483647")
            slots.add(slot)
            try:
                strength_model = float(row.get("strength_model", 1.0))
                strength_clip = float(row.get("strength_clip", 1.0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"LoRA slot '{slot}' has an invalid strength") from exc
            if not -100.0 <= strength_model <= 100.0 or not -100.0 <= strength_clip <= 100.0:
                raise ValueError(f"LoRA slot '{slot}' strength must be between -100 and 100")
            result.extend([
                {"nodeId": node_id, "fieldName": "lora_name", "fieldValue": model},
                {"nodeId": node_id, "fieldName": "strength_model", "fieldValue": str(strength_model)},
            ])
            if row.get("include_strength_clip", False):
                result.append({"nodeId": node_id, "fieldName": "strength_clip", "fieldValue": str(strength_clip)})
        return (result,)


class FastRHRandomSeed:
    """Build a RunningHub-compatible seed override, optionally chained."""

    MAX_SEED = 0xFFFFFFFFFFFFFFFF

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "nodeId": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": cls.MAX_SEED,
                        "step": 1,
                        "control_after_generate": True,
                    },
                ),
            },
            "optional": {"previousNodeInfoList": ("ARRAY", {"default": []})},
        }

    RETURN_TYPES = ("ARRAY",)
    RETURN_NAMES = ("nodeInfoList",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Create a seed override compatible with RH Node Info List."

    def build(self, nodeId: int, seed: int, previousNodeInfoList=None):
        selected_seed = int(seed)
        if not 0 <= selected_seed <= self.MAX_SEED:
            raise ValueError(f"Seed must be between 0 and {self.MAX_SEED}")
        node_info_list = list(previousNodeInfoList or [])
        node_info_list.append({"nodeId": int(nodeId), "fieldName": "seed", "fieldValue": str(selected_seed)})
        return (node_info_list,)


class FastRHKSampler:
    """Map KSampler widgets to a remote RunningHub KSampler node."""

    MAX_SEED = 0xFFFFFFFFFFFFFFFF

    @classmethod
    def INPUT_TYPES(cls):
        try:
            from comfy.samplers import KSampler as ComfyKSampler
            samplers = ComfyKSampler.SAMPLERS
            schedulers = ComfyKSampler.SCHEDULERS
        except ImportError:
            # Allows the node contract to be tested without a ComfyUI installation.
            samplers = ("euler_ancestral", "euler", "dpmpp_2m")
            schedulers = ("simple", "normal", "karras")
        return {
            "required": {
                "nodeId": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": cls.MAX_SEED,
                                 "step": 1, "control_after_generate": True}),
                "steps": ("INT", {"default": 30, "min": 1, "max": 10000, "step": 1}),
                "cfg": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 100.0,
                                  "step": 0.1, "round": 0.01}),
                "sampler_name": (samplers, {"default": "euler_ancestral"}),
                "scheduler": (schedulers, {"default": "simple"}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0,
                                      "step": 0.01, "round": 0.01}),
            },
            "optional": {"previousNodeInfoList": ("ARRAY", {"default": []})},
        }

    RETURN_TYPES = ("ARRAY",)
    RETURN_NAMES = ("nodeInfoList",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Override a remote KSampler through the official RunningHub nodeInfoList."

    def build(self, nodeId: int, seed: int, steps: int, cfg: float,
              sampler_name: str, scheduler: str, denoise: float,
              previousNodeInfoList=None):
        import math

        if isinstance(nodeId, bool) or not isinstance(nodeId, int) or not 1 <= nodeId <= 999999:
            raise ValueError("Remote KSampler nodeId must be between 1 and 999999")
        if isinstance(seed, bool) or not 0 <= int(seed) <= self.MAX_SEED:
            raise ValueError(f"Seed must be between 0 and {self.MAX_SEED}")
        if isinstance(steps, bool) or not 1 <= int(steps) <= 10000:
            raise ValueError("KSampler steps must be between 1 and 10000")
        cfg_value = float(cfg)
        denoise_value = float(denoise)
        if not math.isfinite(cfg_value) or not 0.0 <= cfg_value <= 100.0:
            raise ValueError("KSampler cfg must be between 0 and 100")
        if not math.isfinite(denoise_value) or not 0.0 <= denoise_value <= 1.0:
            raise ValueError("KSampler denoise must be between 0 and 1")
        if not str(sampler_name).strip() or not str(scheduler).strip():
            raise ValueError("KSampler sampler and scheduler cannot be empty")

        node_info_list = list(previousNodeInfoList or [])
        for field, value in (
            ("seed", str(int(seed))),
            ("steps", str(int(steps))),
            ("cfg", str(cfg_value)),
            ("sampler_name", str(sampler_name)),
            ("scheduler", str(scheduler)),
            ("denoise", str(denoise_value)),
        ):
            node_info_list.append({
                "nodeId": int(nodeId), "fieldName": field, "fieldValue": value,
            })
        return (node_info_list,)


class FastRHEmptyLatentImage:
    """Map Empty Latent Image dimensions to a remote RunningHub workflow."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "nodeId": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                "width": ("INT", {"default": 1024, "min": 16, "max": 16384, "step": 8}),
                "height": ("INT", {"default": 1920, "min": 16, "max": 16384, "step": 8}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096, "step": 1}),
            },
            "optional": {"previousNodeInfoList": ("ARRAY", {"default": []})},
        }

    RETURN_TYPES = ("ARRAY",)
    RETURN_NAMES = ("nodeInfoList",)
    FUNCTION = "build"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Override a remote Empty Latent Image node through the official RunningHub nodeInfoList."

    def build(self, nodeId: int, width: int, height: int, batch_size: int,
              previousNodeInfoList=None):
        if isinstance(nodeId, bool) or not isinstance(nodeId, int) or not 1 <= nodeId <= 999999:
            raise ValueError("Remote Empty Latent Image nodeId must be between 1 and 999999")
        for field, value in (("width", width), ("height", height)):
            if isinstance(value, bool) or not isinstance(value, int) or not 16 <= value <= 16384 or value % 8:
                raise ValueError(f"Empty Latent Image {field} must be a multiple of 8 between 16 and 16384")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 4096:
            raise ValueError("Empty Latent Image batch_size must be between 1 and 4096")

        node_info_list = list(previousNodeInfoList or [])
        for field, value in (("width", width), ("height", height), ("batch_size", batch_size)):
            node_info_list.append({
                "nodeId": int(nodeId), "fieldName": field, "fieldValue": str(int(value)),
            })
        return (node_info_list,)


class FastRHSettings:
    """Build the official RH Settings STRUCT using a server-side API key."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": ""}),
                "workflowId_webappId": ("STRING", {"default": ""}),
                "config_path": ("STRING", {"default": "config.json"}),
            },
        }

    RETURN_TYPES = ("STRUCT",)
    RETURN_NAMES = ("apiConfig",)
    FUNCTION = "process"
    CATEGORY = "Fast-RH"
    DESCRIPTION = "Set the RunningHub base_url and the path to a server-side JSON file containing api_key."

    @classmethod
    def IS_CHANGED(cls, base_url, workflowId_webappId, config_path="config.json"):
        try:
            return (config_path, resolve_config_path(config_path).stat().st_mtime_ns)
        except OSError:
            return float("nan")

    def process(self, base_url: str, workflowId_webappId: str, config_path: str = "config.json"):
        config = load_config(resolve_config_path(config_path))
        site = str(base_url).strip().rstrip("/")
        parsed = urlparse(site)
        if (parsed.scheme != "https" or parsed.hostname not in {
            "www.runninghub.cn", "runninghub.cn",
            "www.runninghub.ai", "runninghub.ai",
        } or parsed.username or parsed.password or parsed.port
                or parsed.path or parsed.query or parsed.fragment):
            raise ValueError("base_url must be an HTTPS RunningHub .cn or .ai site URL")
        workflow_id = str(workflowId_webappId).strip()
        if not workflow_id:
            raise ValueError("workflowId_webappId is required")
        api_key = config.api_key
        return ({
            "base_url": site,
            "apiKey": api_key,
            "workflowId_webappId": workflow_id,
        },)


NODE_CLASS_MAPPINGS = {"FastRHLoRA": FastRHLoRA, "FastRHRandomSeed": FastRHRandomSeed, "FastRHKSampler": FastRHKSampler, "FastRHEmptyLatentImage": FastRHEmptyLatentImage, "FastRHSettings": FastRHSettings}
NODE_DISPLAY_NAME_MAPPINGS = {
    "FastRHLoRA": "Fast-RH LoRA Stack",
    "FastRHRandomSeed": "Fast-RH Random Seed",
    "FastRHKSampler": "Fast KSampler",
    "FastRHEmptyLatentImage": "Fast Empty Latent Image",
    "FastRHSettings": "Fast-RH Settings",
}
