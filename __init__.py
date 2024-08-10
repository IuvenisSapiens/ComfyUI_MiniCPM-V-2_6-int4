from .nodes import MiniCPM_VQA
from .util_nodes import LoadVideo,PreViewVideo
from .display_text_nodes import DisplayText
WEB_DIRECTORY = "./web"
# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "LoadVideo": LoadVideo,
    "PreViewVideo": PreViewVideo,
    "MiniCPM_VQA": MiniCPM_VQA,
    "DisplayText": DisplayText,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadVideo": "Load Video",
    "PreViewVideo": "PreView Video",
    "MiniCPM_VQA": "MiniCPM VQA",
    "DisplayText": "Display Text",
}