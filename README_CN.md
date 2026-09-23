# Fast-RH

简体中文 | [English](README.md)

Fast-RH 是一套 ComfyUI 自定义节点，目标是让用户可以在本地更方便地控制 RunningHub 图片生成工作流。目前包含 **Fast-RH LoRA** 和 **Fast-RH Random Seed**。

## 功能

- 使用 RunningHub 网站模型接口，分为公共模型、我上传的、我的收藏。
- 深色卡片弹窗展示封面、基础模型、文件名和收藏状态，支持搜索、分页、版本切换及点击选择。
- 单个节点支持 1–16 条 LoRA 配置，默认显示 4 条。
- 每条配置包含稳定的槽位名称、启用状态、模型强度和 CLIP 强度。
- 输出有序的 `RH_LORA_CONFIG_LIST`，供后续 Fast-RH 工作流提交节点使用。
- RunningHub API Key 只保存在 ComfyUI 服务端，不会写入工作流文件。
- **Fast-RH Random Seed** 可为指定远程节点生成随机或自定义 seed，并直接输出兼容 RH Node Info List 的 ARRAY。

Fast-RH LoRA 目前只生成 LoRA 配置，不会自行提交或改写远程工作流。

## 安装

1. 将本仓库放到 `ComfyUI/custom_nodes/ComfyUI-Fast-RH`，也可以通过 ComfyUI Manager 的 Git URL 安装功能安装。
2. 重启 ComfyUI，并刷新浏览器页面。
3. 添加 **Fast-RH → Fast-RH LoRA**，点击任意一行的 **选择模型**。
4. 打开 **登录设置**，选择与网页登录一致的 `.ai` 或 `.cn` 站点。
5. 在 RunningHub 网站登录后，从浏览器开发者工具的 Application / Cookies 中复制 `Rh-Accesstoken` 的值，粘贴并保存。也可以粘贴完整 Cookie 字符串或 `Bearer …`。
6. 在公共模型、我上传的、我的收藏中搜索模型，选择版本后点击封面，文件名会自动填回节点。

## 登录与模型列表

网站模型列表使用登录令牌，不需要 OpenAPI 的 API Key。令牌保存在插件目录的 `session.json` 中（本地明文、已被 Git 忽略），不会返回前端或写入工作流。粘贴完整 Cookie 时仅提取 `Rh-Accesstoken`，不保存其他 Cookie。共享 ComfyUI 实例的访问者使用同一个模型账号；此方式面向可信的本地环境。

打开模型弹窗时会调用 `/api/instance/access/auth` 验证当前令牌是否仍被 RunningHub 接受，并读取 JWT `exp` 显示 `Rh-Accesstoken` 的实际到期时间。接口返回的 `expire_in` 是该接口新签发的临时 `accessKey` 到期时间，不是网页登录令牌的期限；插件不会保存或使用这个 `accessKey`。目前未接入刷新令牌接口，因此不保存或使用 `Rh-Refreshtoken`。令牌失效时，在网站重新登录并更新令牌；**清除登录**可删除本地保存的令牌。网站登录 Cookie 无法由本地 ComfyUI 页面直接跨域读取。

列表每次按需请求当前页（30 条）；搜索由 RunningHub 服务端执行，切换分类回到第一页。点击刷新重新获取当前页。只读取模型元数据和封面，不下载模型权重。多个版本分别保留文件名，选择时优先使用 `resourceStorageName`，移除 `models/loras/` 前缀但保留子目录。

旧的 `/fast-rh/loras` 和 `/fast-rh/loras/refresh` 接口保留供兼容调用，仍使用 `config.json` 中的 `base_url`、`api_key`、`timeout_seconds` 和 `cache/`；新弹窗不再读取完整 `/object_info`。

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

填写远程工作流中需要改写 seed 的 `nodeId` 和 `seed`。seed 使用 ComfyUI 原生的执行后控制，可选择 `randomize` 在每次排队时随机，或选择 `fixed` 使用输入框中的固定值来复现结果。

节点固定写入 `fieldName: "seed"`，输出与 RunningHub 的 **RH Node Info List** 相同的 `ARRAY` 格式，可以直接连接原先使用该节点输出的位置。可选输入 `previousNodeInfoList` 用于和其他参数继续串联。