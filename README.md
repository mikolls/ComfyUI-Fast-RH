# Fast-RH

[简体中文](README_CN.md) | English

Fast-RH is a ComfyUI custom-node suite designed to make RunningHub image-generation workflows easier to control locally. It currently includes **Fast-RH LoRA** and **Fast-RH Random Seed**.

## Features

- Loads the LoRA names available to your RunningHub account through the native ComfyUI `/object_info` endpoint.
- Provides a searchable model picker with manual refresh.
- Supports 1–16 LoRA entries in one node, with four entries by default.
- Configures a stable slot name, enabled state, model strength, and CLIP strength for every entry.
- Outputs an ordered `RH_LORA_CONFIG_LIST` for a future Fast-RH workflow submission node.
- Keeps the RunningHub API key on the ComfyUI server and out of workflow files.

Fast-RH LoRA does not submit or rewrite remote workflows by itself yet.

## Installation

1. Put this repository in `ComfyUI/custom_nodes/ComfyUI-Fast-RH`, or install it from its Git URL with ComfyUI Manager.
2. Copy `config.example.json` to `config.json`.
3. Set your RunningHub `base_url` and `api_key`. Adjust `timeout_seconds` if needed.
4. Restart ComfyUI.
5. Add **Fast-RH → Fast-RH LoRA** to your workflow.

Example configuration:

```json
{
  "base_url": "https://www.runninghub.cn",
  "api_key": "your-runninghub-api-key",
  "timeout_seconds": 30
}
```

Both `https://www.runninghub.cn` and `https://www.runninghub.ai` are supported. `config.json` is ignored by Git and must never be committed.

## Model cache

The first model-list request downloads the complete RunningHub `/object_info` response and saves it atomically under `cache/`. Later searches and ComfyUI restarts always use that local JSON file—there is no automatic expiration or background refresh.

RunningHub is contacted again only when:

- you click **刷新 RunningHub** in the model picker;
- the cache is missing or corrupt; or
- the configured site or API key changes.

If a manual refresh fails, the last valid cache remains available. Cache files contain only an API-key fingerprint, never the API key itself.

## Output contract

The node returns one `RH_LORA_CONFIG_LIST`. Each ordered entry contains:

```text
slot
model
enabled
strength_model
strength_clip
order
```

Slots must be non-empty and unique within the node. A model must be selected before execution. Both strengths accept values from `-100` to `100` and default to `1.0`.

## Development

Run the dependency-free test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

## Fast-RH Random Seed

Set the target remote workflow `nodeId`, then select `random` to generate a fresh seed on every queued run or `custom` to use the value in the `seed` field. The node outputs the same `ARRAY` contract as RunningHub's **RH Node Info List**, fixes `fieldName` to `seed`, and supports chaining through the optional `previousNodeInfoList` input.
