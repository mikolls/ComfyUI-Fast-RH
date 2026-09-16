# Fast-RH

简体中文 | [English](README.md)

Fast-RH 是一套 ComfyUI 自定义节点，目标是让用户可以在本地更方便地控制 RunningHub 图片生成工作流。目前包含 **Fast-RH LoRA** 和 **Fast-RH Random Seed**。

## 功能

- 通过 RunningHub 原生 ComfyUI `/object_info` 接口读取当前账号可用的 LoRA 名称。
- 提供可搜索的模型选择弹窗和手动刷新功能。
- 单个节点支持 1–16 条 LoRA 配置，默认显示 4 条。
- 每条配置包含稳定的槽位名称、启用状态、模型强度和 CLIP 强度。
- 输出有序的 `RH_LORA_CONFIG_LIST`，供后续 Fast-RH 工作流提交节点使用。
- RunningHub API Key 只保存在 ComfyUI 服务端，不会写入工作流文件。
- **Fast-RH Random Seed** 可为指定远程节点生成随机或自定义 seed，并直接输出兼容 RH Node Info List 的 ARRAY。

Fast-RH LoRA 目前只生成 LoRA 配置，不会自行提交或改写远程工作流。

## 安装

1. 将本仓库放到 `ComfyUI/custom_nodes/ComfyUI-Fast-RH`，也可以通过 ComfyUI Manager 的 Git URL 安装功能安装。
2. 将 `config.example.json` 复制为 `config.json`。
3. 在 `config.json` 中填写 RunningHub 的 `base_url` 和 `api_key`，按需调整 `timeout_seconds`。
4. 重启 ComfyUI。
5. 在工作流中添加 **Fast-RH → Fast-RH LoRA** 或 **Fast-RH → Fast-RH Random Seed**。

配置示例：

```json
{
  "base_url": "https://www.runninghub.cn",
  "api_key": "你的-RunningHub-API-Key",
  "timeout_seconds": 30
}
```

插件同时支持 `https://www.runninghub.cn` 和 `https://www.runninghub.ai`。`config.json` 已被 Git 忽略，请勿将真实密钥提交到仓库。

## 模型缓存

首次获取模型列表时，插件会下载完整的 RunningHub `/object_info` 响应，并以原子方式保存到 `cache/`。后续搜索和重启 ComfyUI 都直接读取本地 JSON；缓存不会自动过期，也不会在后台刷新。

只有以下情况会再次访问 RunningHub：

- 用户在模型选择弹窗中点击 **刷新 RunningHub**；
- 缓存不存在或已经损坏；
- 配置的站点或 API Key 发生变化。

手动刷新失败不会覆盖最后一份有效缓存。缓存只保存 API Key 指纹，不会保存 API Key 本身。

## 输出约定

节点输出一个 `RH_LORA_CONFIG_LIST`。其中每条配置按界面顺序包含：

```text
slot
model
enabled
strength_model
strength_clip
order
```

同一个节点内的槽位名称不能为空或重复，执行前必须为每条配置选择模型。模型强度和 CLIP 强度允许范围为 `-100` 到 `100`，默认值均为 `1.0`。

## 开发测试

在仓库根目录运行不依赖第三方测试框架的测试：

```bash
python -m unittest discover -s tests -v
```

## Random Seed 节点

填写远程工作流中需要改写 seed 的 `nodeId`，然后选择模式：

- `random`：每次排队执行时生成新的 0–18446744073709551615 随机种子，并绕过 ComfyUI 执行缓存。
- `custom`：使用 `seed` 输入框中的固定值，方便复现结果。

节点固定写入 `fieldName: "seed"`，输出与 RunningHub 的 **RH Node Info List** 相同的 `ARRAY` 格式，可以直接连接原先使用该节点输出的位置。可选输入 `previousNodeInfoList` 用于和其他参数继续串联。