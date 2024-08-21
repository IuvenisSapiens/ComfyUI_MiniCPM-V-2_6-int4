import os
import folder_paths
current_dir = os.path.dirname(os.path.abspath(__file__))
input_dir = folder_paths.get_input_directory()
output_dir = folder_paths.get_output_directory()

class LoadVideo:
    @classmethod
    def INPUT_TYPES(s):
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and f.split('.')[-1] in ["mp4", "mkv", "mov", "avi", "flv", "wmv", "webm", "m4v"]]
        return {"required":{
            "video":(files,),
        }}
    
    CATEGORY = "Comfyui_MiniCPM-V-2_6-int4"
    DESCRIPTION = "Load Video"

    RETURN_TYPES = ("VIDEO",)

    OUTPUT_NODE = False

    FUNCTION = "load_video"

    def load_video(self, video):
        video_path = os.path.join(input_dir,video)
        return (video_path,)

class PreviewVideo:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":{
            "video":("VIDEO",),
        }}
    
    CATEGORY = "Comfyui_MiniCPM-V-2_6-int4"
    DESCRIPTION = "Load Video"

    RETURN_TYPES = ()

    OUTPUT_NODE = True

    FUNCTION = "load_video"

    def load_video(self, video):
        video_name = os.path.basename(video)
        video_path_name = os.path.basename(os.path.dirname(video))
        return {"ui":{"video":[video_name,video_path_name]}}
