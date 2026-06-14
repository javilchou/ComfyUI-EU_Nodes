class TextConcatenator_Plus:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "separator": ("STRING", {"default": ","}),
                "换行": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
                "跳过空行": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
            },
            "optional": {},
        }

        for i in range(1, 21):
            inputs["optional"][f"text{i}"] = ("STRING", {"multiline": False, "default": ""})

        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "combine_texts"
    CATEGORY = "EU Nodes/Text"
    DESCRIPTION = "Concatenate up to 20 text rows with optional separator, newline, and empty-row behavior."

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    def combine_texts(self, separator, 换行, 跳过空行, **kwargs):
        texts = [kwargs.get(f"text{i}", "") or "" for i in range(1, 21)]
        joiner = f"{separator}\n" if 换行 else separator

        if 跳过空行:
            return (joiner.join(text for text in texts if text.strip()),)

        result = ""
        pending_joiner = False
        for text in texts:
            if not text.strip():
                pending_joiner = False
                continue

            if result and pending_joiner:
                result += joiner

            result += text
            pending_joiner = True

        return (result,)
