class DisplayText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "display_text"
    CATEGORY = "MiniCPM-V"

    def display_text(self, text):
        return {"ui": {"text": text}, "result": (text,)}
