# ComfyUI-EU_Nodes

个人自用的 ComfyUI 易用节点包。

## Nodes

### EU_基础潜空间

生成空 latent，可替代 ComfyUI 原生 `Empty Latent Image`。  
支持常用分辨率预设、自定义宽高、锁定纵横比、尺寸对齐和批次设置。

### EU_图片筛选暂停

用于批量流程中的人工筛选闸门。

连接上游 `IMAGE` 后，工作流执行到该节点会暂停，并在前端弹出图片选择窗口。选择需要保留的图片后点击 `继续所选`，节点只把选中的图片 batch 继续传给下游。

适合流程：

```text
上游批量生成图片 -> EU_图片筛选暂停 -> 后续处理
```

### EU_文本替换Plus

根据多行替换规则批量替换文本。

规则格式：

```text
old text == new text
cat == 猫
blue dress == 蓝色裙子
```

## Installation

Clone this repository into your ComfyUI `custom_nodes` directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_NAME/ComfyUI-EU_Nodes.git
```

Restart ComfyUI after installation.

## Requirements

This node pack uses dependencies already included with a normal ComfyUI install:

- torch
- numpy
- Pillow
- aiohttp

No extra model files are required.

## Notes

- `EU_图片筛选暂停` blocks the current workflow while waiting for user selection.
- If the timeout is reached, or the user cancels, the node raises an error and the downstream workflow will not continue.
- The browser page may need a hard refresh after updating frontend JavaScript.

