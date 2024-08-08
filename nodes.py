import os
import torch
import folder_paths
from transformers import AutoTokenizer, AutoModel
from torchvision.transforms.v2 import ToPILImage
from decord import VideoReader, cpu  # pip install decord
from PIL import Image



class MiniCPM_VQA:
    def __init__(self):
        self.model_checkpoint = None
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.bf16_support = torch.cuda.is_available() and torch.cuda.get_device_capability(self.device)[0] >= 8

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"default": '', "multiline": True}),
                "model": (["MiniCPM-V-2_6-int4"],),
                "temperature": ("FLOAT", {"default": 0.7,}),
            },
            "optional": {
                "source_image_path": ("IMAGE",),
                "source_video_path": ("VIDEO",),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "inference"
    CATEGORY = "MiniCPM-V"

    def encode_video(self, source_video_path):
        MAX_NUM_FRAMES = 64  # if cuda OOM set a smaller number

        def uniform_sample(l, n):  # noqa: E741
            gap = len(l) / n
            idxs = [int(i * gap + gap / 2) for i in range(n)]
            return [l[i] for i in idxs]

        vr = VideoReader(source_video_path, ctx=cpu(0))
        sample_fps = round(vr.get_avg_fps() / 1)  # FPS
        frame_idx = [i for i in range(0, len(vr), sample_fps)]
        if len(frame_idx) > MAX_NUM_FRAMES:
            frame_idx = uniform_sample(frame_idx, MAX_NUM_FRAMES)
        frames = vr.get_batch(frame_idx).asnumpy()
        frames = [Image.fromarray(v.astype('uint8')) for v in frames]
        print('num frames:', len(frames))
        return frames

    def inference(self, text, model, temperature, source_image_path=None, source_video_path=None):
        model_id = f"openbmb/{model}"
        model_checkpoint = os.path.join(folder_paths.models_dir, 'prompt_generator', os.path.basename(model_id))

        if not os.path.exists(model_checkpoint):
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=model_id, local_dir=model_checkpoint, local_dir_use_symlinks=False)

        if self.model_checkpoint != model_checkpoint:
            self.model_checkpoint = model_checkpoint
            self.tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(model_checkpoint, trust_remote_code=True, torch_dtype=torch.bfloat16)

        with torch.no_grad():
            if source_video_path:
                frames = self.encode_video(source_video_path)
                msgs = [{'role': 'user', 'content': frames + [text]}]
            elif source_image_path is not None:
                image = ToPILImage()(source_image_path.permute([0,3,1,2])[0]).convert("RGB")
                msgs = [{'role': 'user', 'content': [image, text]}]
            else:
                raise ValueError("Either image or source_video_path must be provided")

            params = {
                "use_image_id": False,
                "max_slice_nums": 2  # use 1 if cuda OOM and video resolution >  448*448
            }

            result = self.model.chat(
                image=None,
                msgs=msgs,
                tokenizer=self.tokenizer,
                sampling=True,
                temperature=temperature,
                **params
            )
            return (result,)

