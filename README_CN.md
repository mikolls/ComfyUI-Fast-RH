# Fast-RH

简体中文 | [English](README.md)

Fast-RH 是一套 ComfyUI 自定义节点，目标是让用户可以在本地更方便地控制 RunningHub 图片生成工作流。目前包含 **Fast-RH LoRA**、**Fast-RH Random Seed**、**Fast KSampler** 和 **Fast Empty Latent Image**。

## 功能

- 使用 RunningHub 网站模型接口，分为公共模型、我上传的、我的收藏。
- 深色卡片弹窗展示封面、基础模型、文件名和收藏状态，支持搜索、分页、版本切换及点击选择。
- 每个 LoRA 槽位可填写远程工作流里预建的 `nodeId`，并随模型配置一并输出。
- 模型列表缓存 24 小时，可手动刷新或清理；每个模型版本可以设置本地封面，默认使用 RunningHub 封面。
- 单个节点支持 1–16 条 LoRA 配置，默认显示 1 条，每行展示封面缩略图并支持点击放大。
- 每条配置包含稳定的槽位名称、启用状态、模型强度和 CLIP 强度。
- 输出兼容官方 RunningHub 节点的 `ARRAY`（`nodeInfoList`）。
- RunningHub API Key 只保存在 ComfyUI 服务端，不会写入工作流文件。
- **Fast-RH Random Seed** 可为指定远程节点生成随机或自定义 seed，并直接输出兼容 RH Node Info List 的 ARRAY。
- **Fast-RH Settings** 输出与官方设置节点兼容的 `STRUCT`，API Key 从本地配置读取。

Fast-RH LoRA 目前只生成 LoRA 配置，不会自行提交或改写远程工作流。

## 安装

1. 将本仓库放到 `ComfyUI/custom_nodes/ComfyUI-Fast-RH`，也可以通过 ComfyUI Manager 的 Git URL 安装功能安装。
2. 重启 ComfyUI，并刷新浏览器页面。
3. 添加 **Fast-RH → Fast-RH LoRA**，点击任意一行的 **选择模型**。
4. 打开 **登录设置**，选择与网页登录一致的 `.ai` 或 `.cn` 站点。
5. 在 RunningHub 网站登录后，从浏览器开发者工具的 Application / Cookies 中复制 `Rh-Accesstoken` 的值，粘贴并保存。也可以粘贴完整 Cookie 字符串或 `Bearer …`。
6. 在公共模型、我上传的、我的收藏中搜索模型，选择版本后点击封面，文件名会自动填回节点。
7. 在该 LoRA 行填写远程工作流里对应 LoRA 加载节点的 `nodeId`。

## Fast-RH Settings 节点

使用 **Fast-RH Settings** 替换官方 **RH Settings**。节点界面只有 `base_url` 和 `workflowId_webappId`，输出的 `STRUCT` 可以直接连接官方执行和上传节点。

将插件目录中的 `config.example.json` 复制为 `config.json`，在其中填写 `api_key`。此文件不会提交到 Git。节点地址应与 API Key 所属站点一致；有配置时默认使用配置中的地址。API Key 只在 ComfyUI 服务端运行时读取，不会成为工作流控件。修改配置后重新排队执行即可使用新 Key。分享旧工作流前请替换原来的 **RH Settings** 节点，因为旧文件可能已包含原始 API Key。

## 登录与模型列表

网站模型列表使用登录令牌，不需要 OpenAPI 的 API Key。令牌保存在插件目录的 `session.json` 中（本地明文、已被 Git 忽略），不会返回前端或写入工作流。粘贴完整 Cookie 时仅提取 `Rh-Accesstoken`，不保存其他 Cookie。共享 ComfyUI 实例的访问者使用同一个模型账号；此方式面向可信的本地环境。

打开模型弹窗时会调用 `/api/instance/access/auth` 验证当前令牌是否仍被 RunningHub 接受，并读取 JWT `exp` 显示 `Rh-Accesstoken` 的实际到期时间。接口返回的 `expire_in` 是该接口新签发的临时 `accessKey` 到期时间，不是网页登录令牌的期限；插件不会保存或使用这个 `accessKey`。目前未接入刷新令牌接口，因此不保存或使用 `Rh-Refreshtoken`。令牌失效时，在网站重新登录并更新令牌；**清除登录**可删除本地保存的令牌。网站登录 Cookie 无法由本地 ComfyUI 页面直接跨域读取。

列表每页 30 条，按分类、页码和搜索词分别缓存在本地 24 小时；普通打开优先读取缓存，点击**刷新列表**会从 RunningHub 更新当前页。**清理缓存**只清除模型列表，不影响自定义封面。模型卡片默认显示 RunningHub 封面，可用**设置封面**选择本地 PNG、JPG 或 WebP 图片，之后可用**恢复远程封面**撤销自定义封面。这里只缓存列表和封面，不下载模型权重。多个版本分别保留文件名，选择时优先使用 `resourceStorageName`，移除 `models/loras/` 前缀但保留子目录。

旧的 `/fast-rh/loras` 和 `/fast-rh/loras/refresh` 接口保留供兼容调用，仍使用 `config.json` 中的 `base_url`、`api_key`、`timeout_seconds` 和 `cache/`；新弹窗不再读取完整 `/object_info`。

## 输出约定

节点输出一个 `ARRAY`。每个启用的 LoRA 按界面顺序生成三条 `nodeInfoList` 参数：

```text
{nodeId, fieldName: "lora_name", fieldValue: "model filename"}
{nodeId, fieldName: "strength_model", fieldValue: "model strength"}
{nodeId, fieldName: "strength_clip", fieldValue: "CLIP strength"}
```

同一个节点内的槽位名称不能为空或重复，启用的行必须填写模型和远程节点 ID。官方上传节点输出的 STRING 文件名可接入 RH Node Info List 的 fieldValue，再将其 ARRAY 输出接到本节点的 previousNodeInfoList。模型强度和 CLIP 强度允许范围为 `-100` 到 `100`，默认值均为 `1.0`。

## 开发测试

在仓库根目录运行不依赖第三方测试框架的测试：

```bash
python -m unittest discover -s tests -v
```

## Random Seed 节点

填写远程工作流中需要改写 seed 的 `nodeId` 和 `seed`。seed 使用 ComfyUI 原生的执行后控制，可选择 `randomize` 在每次排队时随机，或选择 `fixed` 使用输入框中的固定值来复现结果。

节点固定写入 `fieldName: "seed"`，输出与 RunningHub 的 **RH Node Info List** 相同的 `ARRAY` 格式，可以直接连接原先使用该节点输出的位置。可选输入 `previousNodeInfoList` 用于和其他参数继续串联。

## Fast KSampler 节点

填写远程工作流中 KSampler 的 `nodeId`，即可控制 seed、steps、cfg、sampler_name、scheduler 和 denoise。seed 支持 ComfyUI 原生的执行后随机化。节点只构造远程参数，不在本地执行采样。

输出类型为官方 RH Node Info List / RH Execute Workflow 可接收的 `ARRAY`。可将已有的官方 Node Info List 输出接到 `previousNodeInfoList`，再将 Fast KSampler 的 `nodeInfoList` 接到官方执行节点。远程工作流中的 KSampler 必须有对应的节点 ID。

## Fast Empty Latent Image 节点

填写远程工作流中 Empty Latent Image 的 `nodeId`，设置 width、height 和 batch_size。宽高范围为 16–16384，按 8 的倍数调整；批次数量范围为 1–4096。节点只生成远程参数，不在本地创建 LATENT。

输出与官方 RH Node Info List 和 RH Execute Workflow 兼容的 `ARRAY`，每次附加 width、height、batch_size 三条参数。可将前一个参数节点接入 `previousNodeInfoList` 继续串联。

界面提供“预设 / 自定义”模式。预设下拉框一次选择宽高组合；自定义模式可单独编辑宽和高。切换时两种模式各自保留数值，底部“交换宽高”按钮可翻转当前分辨率的方向。