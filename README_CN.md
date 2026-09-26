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

![图片](./img/3a050c99-806e-4028-a5d2-2bb53145ec11.png)

1. 将 **ComfyUI-Fast-RH** 插件目录中的 `config.example.json` 复制为 `config.json`，填写 RunningHub API Key：

   ```json
   {
     "api_key": "在这里填写api_key"
   }
   ```

2. 在 **Fast-RH Settings** 节点中填写 `base_url`，使用与 API Key 所属站点一致的 RunningHub 地址；在 `workflowId_webappId` 中填写要执行的远程工作流或 Web App ID。
3. `config_path` 默认是插件目录下的 `config.json`。如果配置文件放在别处，可填写绝对路径；相对路径从插件目录（`node.py` 所在目录）开始计算。将节点输出的 `apiConfig`（`STRUCT`）连接到原来使用官方 **RH Settings** 输出的执行或上传节点。

API Key 由 ComfyUI 服务端从配置文件读取，不会保存在工作流中。修改 `config.json` 后，重新排队执行即可使用新密钥。

> **注意**
>
> 如果旧工作流曾使用官方 **RH Settings** 并填写过 API Key，请在分享前将其替换为 **Fast-RH Settings**。
>
> 已经生成的旧图片或旧工作流文件中可能仍然包含原始 API Key，替换节点不会自动清除历史文件中的信息。

## Fast-RH LoRA Stack

在远程的runninghub工作流提前创建好load lora的占位(随便选模型，strength_model设置为0)，就可以做到本地切换远程的模型。

![图片](./img/2a56a34d-0c7d-4a4f-b15a-3537018c9d1d.png)

### 使用方式

在 ComfyUI 中添加 **Fast-RH LoRA Stack**

1. 点击节点中的 **Click to choose a LoRA model…** ，打开模型弹窗。在**登录设置**中选择与网页登录一致的 RunningHub 站点，粘贴浏览器开发者工具 Cookies 中的 `Rh-Accesstoken`，点击**保存登录**。也可以粘贴完整 Cookie 字符串或 Bearer 令牌。
![图片](./img/fac64e27-0deb-4496-b9ff-3b94e9870a44.png)
![图片](./img/b3e7a312-e495-4520-8383-cb2203871682.png)
![图片](./img/3c12b9e2-ee36-4362-9356-3580dc999c9e.png)
2. 在弹窗中选择模型分类、搜索模型，并选定版本。点击该版本的封面，会自动把模型文件名填入当前 LoRA 条目。
3. 在同一条目中填写远程 LoRA 加载节点的 ID，按需设置模型强度和 CLIP 强度，并启用该条目。多个 LoRA 可分别添加条目，最多 16 个；每个启用的条目都需要对应的远程节点 ID。
![图片](./img/2b669a78-21a8-4de6-8aeb-57f63f5b1b79.png)
4. 将节点输出的 `nodeInfoList`（`ARRAY`）连接到 RunningHub 官方 **RH Execute Workflow** 的 `nodeInfoList` 输入。若已有其他参数节点，将它的 `ARRAY` 输出先连接到本节点的 `previousNodeInfoList`，再将本节点的输出接到执行节点。

模型列表显示旧内容时，点击**刷新列表**更新当前页；点击**清理缓存**可清除已缓存的列表。模型封面可用**设置封面**更换为本地图片，再用**恢复远程封面**撤销更换。登录令牌失效时，重新登录 RunningHub 并在**登录设置**中保存新令牌；**清除登录**可删除本地保存的令牌。

## Fast-RH Random Seed 节点

![图片](./img/62238ad2-ca72-4130-9377-d7933cee6781.png)

### 使用方式

1. 在远程工作流中找到需要修改 seed 的节点 ID，填入 `nodeId`，再设置 `seed`。
2. 在 seed 的 ComfyUI 执行后控制中选择 `randomize`，可在每次排队时使用新种子；选择 `fixed`，则保持输入框中的种子。
3. 将 `nodeInfoList` 输出连接到官方 **RH Execute Workflow** 的 `nodeInfoList` 输入。若还要传入其他节点参数，先将前一个参数节点的输出接到 `previousNodeInfoList`。

## Fast KSampler 节点

![图片](./img/8cb1e8f6-5608-4273-8c1e-206b2ba0622f.png)

### 使用方式

1. 在远程工作流中找到 KSampler 的节点 ID，填入 `nodeId`。设置 `seed`、`steps`、`cfg`、`sampler_name`、`scheduler` 和 `denoise`；需要每次使用新种子时，将 seed 的执行后控制设为 `randomize`。
2. 将本节点的 `nodeInfoList` 输出连接到官方 **RH Execute Workflow** 的 `nodeInfoList` 输入。若已使用 **RH Node Info List** 或其他参数节点，先将其 `ARRAY` 输出接到 `previousNodeInfoList`。

这些设置会改写远程 KSampler 的参数，本节点不会在本地执行采样。

## Fast Empty Latent Image 节点

![图片](./img/346bed77-f0df-449d-a77d-3e4df037aa67.png)

### 使用方式

1. 在远程工作流中找到 Empty Latent Image 的节点 ID，填入 `nodeId`。
2. 选择 `Preset` 从列表中选取宽高组合，或选择 `Custom` 分别填写 `width` 和 `height`。用 `Swap Width / Height ↔` 交换当前宽高，再设置 `batch_size`。宽高须为 16–16384 之间的 8 的倍数，`batch_size` 范围为 1–4096。
3. 将 `nodeInfoList` 输出连接到官方 **RH Execute Workflow** 的 `nodeInfoList` 输入。若已有其他参数节点，先将其 `ARRAY` 输出接到 `previousNodeInfoList`。

切换 `Preset` 和 `Custom` 时，两种模式会各自保留宽高设置。本节点只修改远程工作流参数，不会在本地创建 LATENT。
