class EU_TextReplacePlus:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {

                # 输入数据（支持接线）
                "text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "forceInput": True
                }),

                # 替换规则
                "rules": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    FUNCTION = "replace"

    CATEGORY = "EU Nodes/Text"

    def replace(self, text, rules):

        parsed_rules = []

        # 读取规则
        for line in rules.splitlines():

            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 必须包含 ==
            if "==" not in line:
                continue

            try:
                # 分割左右
                left, right = line.split("==", 1)

                # 去空格 + 去引号
                left = left.strip().strip('"').strip("'")
                right = right.strip().strip('"').strip("'")

                # 跳过空 key
                if not left:
                    continue

                parsed_rules.append((left, right))

            except:
                pass

        # 长词优先，避免：
        # closed eyes -> 闭眼
        # 污染 half-closed eyes
        parsed_rules.sort(
            key=lambda x: len(x[0]),
            reverse=True
        )

        # 执行替换
        for left, right in parsed_rules:
            text = text.replace(left, right)

        return (text,)