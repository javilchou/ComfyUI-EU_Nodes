class TextConcatenator_Plus:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                # 默认只拼接前 2 行
                "combine_order": ("STRING", {"default": "1+2"}),
                "separator": ("STRING", {"default": ","})
            },
            "optional": {}
        }
        
        # 循环生成 20 行文本输入框
        for i in range(1, 21):
            # 默认前 2 行给点初始占位提示，剩下的 18 行默认留空
            default_val = f"文本 {i}" if i <= 2 else ""
            inputs["optional"][f"text{i}"] = ("STRING", {"multiline": False, "default": default_val})
            
        return inputs

    RETURN_TYPES = ("STRING",)
    FUNCTION = "combine_texts"
    CATEGORY = "Meeeyo/String"
    DESCRIPTION = "A powerful 20-row text concatenator with custom order."

    @classmethod
    def IS_CHANGED(cls): 
        return float("NaN")

    def combine_texts(self, combine_order, separator, **kwargs):
        try:
            # 1. 动态收集所有传进来的 text1 ~ text20
            text_map = {}
            for i in range(1, 21):
                text_map[str(i)] = kwargs.get(f"text{i}", "")

            # 2. 如果没有填写拼接顺序，则自动拼接所有非空行
            if not combine_order.strip():
                active_parts = [k for k, v in text_map.items() if v.strip()]
                combine_order = "+".join(active_parts)
                if not combine_order:
                    return ("",)

            # 3. 按 '+' 切割顺序并过滤
            parts = combine_order.split("+")
            valid_parts = []
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part in text_map:
                    valid_parts.append(part)
                else:
                    return (f"Error: Invalid input '{part}' in combine_order. Valid options are 1 to 20.",)
            
            # 4. 提取有效的非空文本
            non_empty_texts = [text_map[part] for part in valid_parts if text_map[part].strip()]
            
            # 5. 处理换行符转义
            if separator == '\\n':
                separator = '\n'
            
            # 6. 拼接输出
            result = separator.join(non_empty_texts) 
            return (result,)
            
        except Exception as e:
            return (f"Error: {str(e)}",)