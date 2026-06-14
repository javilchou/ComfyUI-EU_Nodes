"""
EU 节点包 - 易用基础节点包
"""

from .nodes.base_latent import EU_Base_Latent
from .nodes.image_select_gate import EU_ImageSelectGate
from .nodes.TextConcatenator_Plus import TextConcatenator_Plus
from .nodes.text_replace_plus import EU_TextReplacePlus

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "EU_Base_Latent": EU_Base_Latent,
    "EU_ImageSelectGate": EU_ImageSelectGate,
    "EU_TextConcatenatorPlus": TextConcatenator_Plus,
    "EU_TextReplacePlus": EU_TextReplacePlus,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EU_Base_Latent": "EU_基础潜空间",
    "EU_ImageSelectGate": "EU_图片筛选",
    "EU_TextConcatenatorPlus": "EU_文本拼接Plus",
    "EU_TextReplacePlus": "EU_文本替换Plus",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
