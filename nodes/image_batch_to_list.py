class EU_ImageBatchToList:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "batch_to_list"
    CATEGORY = "EU Nodes/实用工具"
    OUTPUT_IS_LIST = (True,)
    DESCRIPTION = "Split an IMAGE batch into a ComfyUI execution list."

    def batch_to_list(self, images):
        if images is None:
            raise ValueError("EU_ImageBatchToList received no images.")

        if images.ndim == 3:
            images = images.unsqueeze(0)

        if images.ndim != 4:
            raise ValueError(
                "EU_ImageBatchToList expected IMAGE shape [B,H,W,C], "
                f"got {tuple(images.shape)}"
            )

        if images.shape[0] < 1:
            raise ValueError("EU_ImageBatchToList received an empty image batch.")

        return ([images[i:i + 1] for i in range(int(images.shape[0]))],)
