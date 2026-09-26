# Fast-RH

简体中文 | [English](README.md)

Fast-RH 的目标是让用户可以在本地更方便地控制 RunningHub 图片生成工作流。

官方的节点 [ComfyUI_RH_APICall](https://github.com/HM-RunningHub/ComfyUI_RH_APICall) 不太好用，所以才封装了更方便的节点。

## 安装

- 将本仓库放到 `ComfyUI/custom_nodes/ComfyUI-Fast-RH`，也可以通过 ComfyUI Manager 的 Git URL 安装功能安装。

## Fast-RH Settings

官方 **RH Settings** 节点会将 `api_key` 作为节点参数填写并保存。在分享包含工作流信息的图片时，`api_key` 可能随 **metadata** 一同写入图片，从而造成泄露风险。

使用 **Fast-RH Settings** 替换官方 **RH Settings**。节点界面包含 `base_url`、`workflowId_webappId` 和 `config_path` 三个输入框，输出的 `STRUCT` 可直接连接 RunningHub 官方的执行、上传等节点，无需修改原有工作流结构。

### 配置方式

将插件目录中的：

`config.example.json`

复制并重命名为：

`config.json`

然后在 `config.json` 中填写 `api_key`。

``` json
{
  "api_key": "在这里填写api_key"
}
```

`base_url` 必须在 **Fast-RH Settings** 节点中填写，并与 API Key 所属的 RunningHub 站点一致。第三行 `config_path` 可直接填写配置文件地址，默认读取当前节点插件目录（`node.py` 所在目录）的 `config.json`。相对路径以该目录为基准，也可以填写绝对路径。配置文件只需包含 `api_key`；密钥仅由服务端读取，工作流只保存配置路径，不保存密钥。

`api_key` 仅在 **ComfyUI 服务端运行时**从配置文件读取，不会作为节点控件保存到工作流中，因此不会随工作流 metadata 一同分享。

修改 `config.json` 后无需修改节点，重新排队执行即可使用新的 API Key。

> **注意**
>
> 如果旧工作流曾使用官方 **RH Settings** 并填写过 API Key，请在分享前将其替换为 **Fast-RH Settings**。
>
> 已经生成的旧图片或旧工作流文件中可能仍然包含原始 API Key，替换节点不会自动清除历史文件中的信息。

## Fast-RH LoRA Stack

网站模型列表使用runninghub的登录令牌。令牌保存在插件目录的 `session.json` 中（本地明文），不会返回前端或写入工作流。粘贴完整 Cookie 时仅提取 `Rh-Accesstoken`，不保存其他 Cookie。共享 ComfyUI 实例的访问者使用同一个模型账号；此方式面向可信的本地环境。

打开模型弹窗时会调用 `/api/instance/access/auth` 验证当前令牌是否仍被 RunningHub 接受，并读取 JWT `exp` 显示 `Rh-Accesstoken` 的实际到期时间。接口返回的 `expire_in` 是该接口新签发的临时 `accessKey` 到期时间，不是网页登录令牌的期限；插件不会保存或使用这个 `accessKey`。目前未接入刷新令牌接口，因此不保存或使用 `Rh-Refreshtoken`。令牌失效时，在网站重新登录并更新令牌；**清除登录**可删除本地保存的令牌。

列表每页 30 条，按分类、页码和搜索词分别缓存在本地 24 小时；普通打开优先读取缓存，点击**刷新列表**会从 RunningHub 更新当前页。**清理缓存**只清除模型列表，不影响自定义封面。模型卡片默认显示 RunningHub 封面，可用**设置封面**选择本地 PNG、JPG 或 WebP 图片，之后可用**恢复远程封面**撤销自定义封面。这里只缓存列表和封面，不下载模型权重。多个版本分别保留文件名，选择时优先使用 `resourceStorageName`，移除 `models/loras/` 前缀但保留子目录。

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
