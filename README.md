# Fast-RH LoRA

A ComfyUI custom node for selecting LoRAs available through RunningHub and producing slot-based `RH_LORA_CONFIG_LIST` values for a future Fast-RH submit node.

## Install

1. Place this directory under `ComfyUI/custom_nodes/` (the directory name can be `comfyui-fast-rh`).
2. Copy `config.example.json` to `config.json`.
3. Set `base_url`, `api_key`, and optionally `timeout_seconds`.
4. Restart ComfyUI and add **Fast-RH → Fast-RH LoRA**.

The API key remains server-side. `config.json` and the `cache/` directory are ignored by Git.

## Cache behavior

The first model-list request downloads the complete RunningHub `/object_info` response and stores it atomically under `cache/`. All later reads use that file forever. RunningHub is contacted again only when **刷新 RunningHub** is clicked, the cache is corrupt, or the configured site/API key changes.

If a manual refresh fails, the last valid cache file is retained.

## Output

The node outputs one `RH_LORA_CONFIG_LIST`. Each entry contains `slot`, `model`, `enabled`, `strength_model`, `strength_clip`, and `order`. It does not submit or rewrite a remote workflow by itself.
