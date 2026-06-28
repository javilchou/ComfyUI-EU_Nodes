# ComfyUI-EU_Nodes

个人自用的 ComfyUI 易用节点包，主要放一些日常工作流里会反复用到的小工具节点。

当前节点包偏实用向：快速创建 latent、批量流程中人工筛图、提示词文本拼接和批量替换。

## 节点列表

### EU_基础潜空间

一个更顺手的空 latent 创建节点，可替代 ComfyUI 原生 `Empty Latent Image`。

适合用在文生图、图生图前置 latent、快速搭建测试工作流等场景。节点会根据选择的分辨率和批次数创建 latent，同时额外输出最终 `width` 和 `height`，方便接到其他需要宽高参数的节点。

输入参数：

- `预设`：常用分辨率列表，包含方图、横图、竖图和多种比例。
- `自定义`：开启后使用手动输入的宽高。
- `锁定纵横比`：自定义宽高时，按当前预设比例自动计算另一边。
- `锁定基准`：锁定比例时，以宽度或高度作为计算基准。
- `自动对齐`：可将尺寸对齐到 8、16、32、64 的倍数。
- `对齐方向`：尺寸对齐时选择向上或向下取整。
- `宽度` / `高度`：自定义尺寸。
- `批次`：生成 latent batch 数量。

输出：

- `latent`：生成好的空 latent。
- `width`：最终宽度。
- `height`：最终高度。

常见用法：

```text
EU_基础潜空间 -> KSampler
EU_基础潜空间.width / height -> 需要尺寸输入的其他节点
```

### EU_图片筛选

一个用于批量流程中的人工筛选闸门。可以直接筛选 `IMAGE`，也可以接入 `LATENT + VAE`，节点内部解码出预览图给你挑选，但下游仍可输出选中的原始 latent。

工作流执行到该节点会暂停，并在 ComfyUI 前端弹出图片选择窗口。你选择需要保留的图片后点击 `继续所选`，节点只把选中的 batch 继续传给下游。

适合流程：

```text
上游批量生成图片 -> EU_图片筛选 -> 后续放大 / 修脸 / 保存 / 二次处理
上游 latent + VAE -> EU_图片筛选 -> 二次采样 / turbo 精修
```

输入参数：

- `images`：可选，上游传入的图片 batch。接入后直接用这些图片做预览和图片输出。
- `latent`：可选，上游传入的 latent batch。接入后会按选择索引输出对应 latent。
- `vae`：可选，配合 `latent` 使用。没有接入 `images` 时，节点会用 VAE 将 latent 解码成预览图。
- `timeout_sec`：等待选择的最长时间，默认 600 秒。
- `取消等待时间`：开启后不再倒计时，节点会一直等待，直到点击 `继续所选` 或 `取消筛选`。
- `取消或超时释放缓存`：开启后，点击 `取消筛选` 或等待超时时，会尝试卸载模型并清理内存/显存缓存。

输出：

- `images`：筛选后的图片 batch。
- `latent`：筛选后的 latent batch。只有输入接入了 `latent` 时才有实际内容。
- `selection_info`：本次选择信息，例如选中了几张、对应原始索引。

前端操作：

- `全选`：选中当前 batch 的所有图片。
- `全不选`：清空当前选择。
- `反选`：把已选和未选状态互换。
- `- / 滑块 / +`：缩小或放大弹窗中的图片预览尺寸。
- `取消筛选`：确认后中止当前流程，节点会报错并阻止下游继续执行。
- `继续所选`：确认选择并继续执行下游节点。

注意：

- 这个节点会阻塞当前工作流，直到你点击继续、取消筛选，或者等待超时。
- 开启 `取消等待时间` 后不会自动超时，会一直阻塞直到你做出操作。
- 只接 `latent + vae` 时，解码图只用于弹窗预览；输出的 `latent` 仍是原始 latent 按索引筛选后的结果，适合二次采样前筛选。
- 同时接入 `images` 和 `latent` 时，两者 batch 数必须一致，节点会用图片预览，并按同一索引筛选 latent。
- `取消或超时释放缓存` 会尽力调用 ComfyUI/torch 的模型卸载和缓存清理接口，但实际释放量仍取决于 ComfyUI 当前执行器和其他节点引用。
- 没有选择任何图片时会报错，避免空 batch 继续往下游传。
- 更新前端 JS 后，如果 ComfyUI 页面没变化，通常需要浏览器强制刷新。

### EU_文本拼接Plus

一个提示词文本拼接节点，默认只显示 4 行文本输入。填满或连接第 4 行后会显示第 5 行，继续填满或连接最后一行会继续展开，最多支持 20 行。

输入参数：

- `separator`：拼接符，默认 `,`。留空时会直接拼接文本。
- `换行`：开启后在拼接符后额外加换行；如果 `separator` 为空，则只使用换行。
- `跳过空行`：开启后忽略空行，并用拼接符/换行连接剩余文本。
- `text1` 到 `text20`：需要拼接的文本，节点会按编号顺序拼接；可见行支持手填，也支持接入 `STRING`。

空行逻辑：

- 开启 `跳过空行` 时，空行不会参与输出。
- 关闭 `跳过空行` 时，空行会同时跳过它所在位置的拼接符和换行。

示例：

```text
separator = ,
换行 = 关闭
跳过空行 = 关闭
text1 = aaa
text2 = bbb
text3 = ccc
text4 = ddd
text5 =
text6 = fff
text7 = ggg

输出：
aaa,bbb,ccc,dddfff,ggg
```

常见用法：

```text
多段提示词文本 -> EU_文本拼接Plus -> CLIP Text Encode
```

### EU_文本替换Plus

一个提示词文本批量替换节点，用多行规则对输入文本进行替换。

适合把固定提示词模板快速换词，比如中英文替换、角色词替换、服装词替换、风格词批量调整等。

输入参数：

- `text`：需要处理的原始文本，支持从上游接线输入。
- `rules`：替换规则，每行一条。

输出：

- `text`：替换后的文本。

规则格式：

```text
old text == new text
cat == 猫
blue dress == 蓝色裙子
"closed eyes" == "闭眼"
```

更贴近提示词翻译/替换的写法：

```text
"calm expression" == "平静表情"
"confused expression" == "困惑表情"
"painful expression" == "痛苦表情"
"seductive smile expression" == "诱惑笑表情"
"looking at viewer" == "看向镜头"
"look to the side" == "看向侧面"
```

规则说明：

- 每行使用 `==` 分隔左侧原词和右侧新词。
- 空行会被忽略。
- 不包含 `==` 的行会被忽略。
- 左右两侧首尾空格会自动去掉。
- 左右两侧包裹的单引号或双引号会自动去掉。
- 节点会按原词长度从长到短替换，减少短词先替换导致长词被破坏的问题。

常见用法：

```text
提示词文本 -> EU_文本替换Plus -> CLIP Text Encode
```

## 安装

进入 ComfyUI 的 `custom_nodes` 目录，然后克隆本仓库：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/javilchou/ComfyUI-EU_Nodes.git
```

安装后重启 ComfyUI。

## 依赖

本节点包使用 ComfyUI 常规环境中已有的依赖：

- torch
- numpy
- Pillow
- aiohttp

不需要额外模型文件。

## 目录结构

```text
ComfyUI-EU_Nodes/
  __init__.py
  nodes/
    base_latent.py
    image_select_gate.py
    TextConcatenator_Plus.py
    text_replace_plus.py
  web/
    image_select_gate.js
    text_concatenator_plus.js
  requirements.txt
```

## 备注

- 当前主要是个人自用节点，接口可能会继续调整。
- `EU_图片筛选` 适合人工参与的工作流，不适合完全无人值守的批量任务。
- 如果节点列表里没有出现新节点，重启 ComfyUI 后再刷新浏览器页面。
