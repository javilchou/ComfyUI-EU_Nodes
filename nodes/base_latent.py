"""
EU_Base_Latent - 易用基础潜空间节点
提供常用分辨率的下拉选择，返回latent、width和height
"""

import torch
import comfy.model_management

class EU_Base_Latent:
    """
    EU_Base_Latent - 易用基础潜空间节点
    """
    
    # 常用分辨率预设 (名称: (宽度, 高度))
    RESOLUTIONS = {
        "512x512 (1:1) (方形)": (512, 512),
        "768x768 (1:1) (方形)": (768, 768),
        "1024x1024 (1:1) (方形)": (1024, 1024),
        "800x600 (4:3) (横屏)": (800, 600),
        "1024x768 (4:3) (横屏)": (1024, 768),
        "1440x1080 (4:3) (横屏)": (1440, 1080),
        "854x480 (16:9) (横屏)": (854, 480),
        "1280x720 (16:9) (横屏)": (1280, 720),
        "1920x1080 (16:9) (横屏)": (1920, 1080),
        "768x512 (3:2) (横屏)": (768, 512),
        "960x640 (3:2) (横屏)": (960, 640),
        "1536x1024 (3:2) (横屏)": (1536, 1024),
        "3072x2048 (3:2) (横屏)": (3072, 2048),
        "1152x896 (9:7) (横屏)": (1152, 896),
        "896x512 (7:4) (横屏)": (896, 512),
        "1344x768 (7:4) (横屏)": (1344, 768),
        "1216x832 (19:13) (横屏)": (1216, 832),
        "832x480 (5.2:3) (横屏)": (832, 480),
        "600x800 (3:4) (竖屏)": (600, 800),
        "768x1024 (3:4) (竖屏)": (768, 1024),
        "1080x1440 (3:4) (竖屏)": (1080, 1440),
        "480x854 (9:16) (竖屏)": (480, 854),
        "720x1280 (9:16) (竖屏)": (720, 1280),
        "1080x1920 (9:16) (竖屏)": (1080, 1920),
        "512x768 (2:3) (竖屏)": (512, 768),
        "640x960 (2:3) (竖屏)": (640, 960),
        "1024x1536 (2:3) (竖屏)": (1024, 1536),
        "2048x3072 (2:3) (竖屏)": (2048, 3072),
        "512x896 (4:7) (竖屏)": (512, 896),
        "768x1344 (4:7) (竖屏)": (768, 1344),
        "896x1152 (7:9) (竖屏)": (896, 1152),
        "832x1216 (13:19) (竖屏)": (832, 1216),
        "480x832 (3:5.2) (竖屏)": (480, 832),
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        resolution_keys = list(cls.RESOLUTIONS.keys())
        
        return {
            "required": {
                "预设": (resolution_keys, {"default": "1024x1024 (1:1) (方形)"}),
                "自定义": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
                "锁定纵横比": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
                "锁定基准": (["宽度", "高度"], {"default": "宽度"}),
                "自动对齐": (["无", "8倍", "16倍", "32倍", "64倍"], {"default": "无"}),
                "对齐方向": (["向上", "向下"], {"default": "向上"}),
                "宽度": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "高度": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "批次": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
            }
        }
    
    RETURN_TYPES = ("LATENT", "INT", "INT")
    RETURN_NAMES = ("latent", "width", "height")
    FUNCTION = "get_resolution"
    CATEGORY = "EU Nodes/Utils"
    
    def get_resolution(self, 预设, 自定义, 锁定纵横比, 锁定基准, 自动对齐, 对齐方向, 宽度, 高度, 批次):
        # 获取预设的宽高和比例
        preset_width, preset_height = self.RESOLUTIONS.get(预设, (1024, 1024))
        aspect_ratio = preset_width / preset_height
        
        # 计算原始尺寸
        if not 自定义:
            original_width = preset_width
            original_height = preset_height
        else:
            if 锁定纵横比:
                if 锁定基准 == "宽度":
                    original_width = 宽度
                    original_height = int(宽度 / aspect_ratio)
                else:
                    original_width = int(高度 * aspect_ratio)
                    original_height = 高度
            else:
                original_width = 宽度
                original_height = 高度
        
        # 根据选择的对齐倍数进行调整
        align_map = {
            "无": 1,
            "8倍": 8,
            "16倍": 16,
            "32倍": 32,
            "64倍": 64,
        }

        align_value = align_map.get(自动对齐, 1)

        if align_value > 1:
            if 对齐方向 == "向上":
                final_width = ((original_width + align_value - 1) // align_value) * align_value
                final_height = ((original_height + align_value - 1) // align_value) * align_value
            else:  # 向下
                final_width = (original_width // align_value) * align_value
                final_height = (original_height // align_value) * align_value
        else:
            final_width = original_width
            final_height = original_height
        
        # 生成 latent（使用对齐后的尺寸）
        device = comfy.model_management.intermediate_device()
        latent = torch.zeros([批次, 4, final_height // 8, final_width // 8], device=device)
        
        return ({"samples": latent}, final_width, final_height)