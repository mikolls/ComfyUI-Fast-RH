# Fast-RH

[简体中文](README_CN.md) | English

Fast-RH is a ComfyUI custom-node suite designed to make RunningHub image-generation workflows easier to control locally. It currently includes **Fast-RH LoRA** and **Fast-RH Random Seed**.

## Features

- Browses RunningHub public, uploaded, and collected LoRAs through its website APIs.
- Shows searchable, paginated model cards with covers, base models, real filenames, and a version selector.
- Supports 1–16 LoRA entries in one node, with four entries by default.
- Configures a stable slot name, enabled state, model strength, and CLIP strength for every entry.
- Outputs an ordered `RH_LORA_CONFIG_LIST` for a future Fast-RH workflow submission node.
- Keeps the RunningHub API key on the ComfyUI server and out of workflow files.

Fast-RH LoRA does not submit or rewrite remote workflows by itself yet.

## Installation

1. Put this repository in `ComfyUI/custom_nodes/ComfyUI-Fast-RH`, or install it from its Git URL with ComfyUI Manager.
2. Restart ComfyUI and refresh the browser.
3. Add **Fast-RH → Fast-RH LoRA** and click a model selector.
4. Open **登录设置** (Login settings), choose the site matching your website login, and paste your `Rh-Accesstoken` from the browser's Application / Cookies panel. A Cookie string or Bearer value also works.
5. Save, browse a category, select a version, and click its cover to fill the node's model filename.

## Website login and catalog

The new picker uses website authentication, independently of your OpenAPI key. It stores only the access token and site in local plaintext `session.json`, ignored by Git. Credentials are never returned to the frontend or serialized in workflows. A pasted Cookie string is reduced to its access token. All users of a shared ComfyUI server share this account; this is intended for a trusted local instance.

Opening the picker calls `/api/instance/access/auth` to verify that RunningHub still accepts the token, then reads the JWT `exp` claim to display the actual `Rh-Accesstoken` expiration. The endpoint’s `expire_in` is the expiry of its newly issued temporary `accessKey`, not the website login token; the plugin neither stores nor uses that `accessKey`. Token renewal is not implemented because the refresh endpoint has not been verified. `Rh-Refreshtoken` is not stored or used. If login expires, sign in on the website again and update the access token. **清除登录** removes the local token. The local ComfyUI page cannot read the website's cookies across origins.

Each request loads one page of 30 models. Search runs on RunningHub; switching categories resets pagination. Refresh reloads the current page. The picker fetches metadata and covers, never model weights. Each version retains its own filename, preferring `resourceStorageName` and removing only the `models/loras/` prefix.

Legacy `/fast-rh/loras` and `/fast-rh/loras/refresh` routes remain available using `config.json` (`base_url`, `api_key`, `timeout_seconds`) and `cache/`. The new picker no longer downloads full `/object_info`.

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

Set the target remote workflow `nodeId` and `seed`. The seed uses ComfyUI's native control-after-generate menu: choose `randomize` for a new value on each queued run or `fixed` to reuse the entered value. The node outputs the same `ARRAY` contract as RunningHub's **RH Node Info List**, fixes `fieldName` to `seed`, and supports chaining through the optional `previousNodeInfoList` input.
