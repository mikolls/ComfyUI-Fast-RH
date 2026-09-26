# Fast-RH

[简体中文](README_CN.md) | English

Fast-RH is a ComfyUI custom-node suite designed to make RunningHub image-generation workflows easier to control locally. It currently includes **Fast-RH LoRA**, **Fast-RH Random Seed**, and **Fast KSampler**.

## Features

- Browses RunningHub public, uploaded, and collected LoRAs through its website APIs.
- Shows searchable, paginated model cards with covers, base models, real filenames, and a version selector.
- Maps each selected LoRA to a pre-created remote workflow node by its `nodeId`.
- Caches catalog pages for 24 hours and supports per-model local cover overrides.
- Supports 1–16 LoRA entries in one node, with four entries by default.
- Configures a stable slot name, enabled state, model strength, and CLIP strength for every entry.
- Outputs an `ARRAY` compatible with the official RunningHub RH Node Info List and workflow executor.
- Keeps the RunningHub API key on the ComfyUI server and out of workflow files.

Fast-RH LoRA does not submit or rewrite remote workflows by itself yet.

## Installation

1. Put this repository in `ComfyUI/custom_nodes/ComfyUI-Fast-RH`, or install it from its Git URL with ComfyUI Manager.
2. Restart ComfyUI and refresh the browser.
3. Add **Fast-RH → Fast-RH LoRA** and click a model selector.
4. Open **登录设置** (Login settings), choose the site matching your website login, and paste your `Rh-Accesstoken` from the browser's Application / Cookies panel. A Cookie string or Bearer value also works.
5. Save, browse a category, select a version, and click its cover to fill the node's model filename.
6. Enter the pre-created remote LoRA loader node ID in the same row.

## Website login and catalog

The new picker uses website authentication, independently of your OpenAPI key. It stores only the access token and site in local plaintext `session.json`, ignored by Git. Credentials are never returned to the frontend or serialized in workflows. A pasted Cookie string is reduced to its access token. All users of a shared ComfyUI server share this account; this is intended for a trusted local instance.

Opening the picker calls `/api/instance/access/auth` to verify that RunningHub still accepts the token, then reads the JWT `exp` claim to display the actual `Rh-Accesstoken` expiration. The endpoint’s `expire_in` is the expiry of its newly issued temporary `accessKey`, not the website login token; the plugin neither stores nor uses that `accessKey`. Token renewal is not implemented because the refresh endpoint has not been verified. `Rh-Refreshtoken` is not stored or used. If login expires, sign in on the website again and update the access token. **清除登录** removes the local token. The local ComfyUI page cannot read the website's cookies across origins.

The picker caches each 30-model page by category, page, and search query for 24 hours. Normal browsing reads local cache; **Refresh list** fetches the current page again. **Clear cache** removes model-list pages while preserving custom covers. Each model version uses its RunningHub cover by default. **Set cover** selects a local PNG, JPG, or WebP image; **Restore remote cover** removes that override. The picker caches metadata and selected cover images, never model weights. Each version retains its own filename, preferring `resourceStorageName` and removing only the `models/loras/` prefix.

Legacy `/fast-rh/loras` and `/fast-rh/loras/refresh` routes remain available using `config.json` (`base_url`, `api_key`, `timeout_seconds`) and `cache/`. The new picker no longer downloads full `/object_info`.

## Output contract

The node returns an `ARRAY`. Each enabled LoRA creates three official `nodeInfoList` entries:

```text
{nodeId, fieldName: "lora_name", fieldValue: "model filename"}
{nodeId, fieldName: "strength_model", fieldValue: "model strength"}
{nodeId, fieldName: "strength_clip", fieldValue: "CLIP strength"}
```

Slots must be non-empty and unique within the node. Enabled rows need a model and remote node ID. The official upload node returns a STRING filename; connect it to RH Node Info List fieldValue, then connect that ARRAY to this node's previousNodeInfoList. Both strengths accept values from `-100` to `100` and default to `1.0`.

## Development

Run the dependency-free test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

## Fast-RH Random Seed

Set the target remote workflow `nodeId` and `seed`. The seed uses ComfyUI's native control-after-generate menu: choose `randomize` for a new value on each queued run or `fixed` to reuse the entered value. The node outputs the same `ARRAY` contract as RunningHub's **RH Node Info List**, fixes `fieldName` to `seed`, and supports chaining through the optional `previousNodeInfoList` input.

## Fast KSampler

Set the remote workflow KSampler `nodeId` and edit seed, steps, cfg, sampler_name, scheduler, and denoise. Seed supports ComfyUI's native control-after-generate menu. This node builds remote overrides; it does not run a sampler locally.

The output is an `ARRAY` accepted by the official RH Node Info List / RH Execute Workflow nodes. Chain an existing official Node Info List into `previousNodeInfoList`, then connect Fast KSampler's `nodeInfoList` to the official executor. The remote workflow must contain the specified KSampler node ID.