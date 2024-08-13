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
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )
        self.bf16_support = (
            torch.cuda.is_available()
            and torch.cuda.get_device_capability(self.device)[0] >= 8
        )

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
                "model": (["MiniCPM-V-2_6-int4"],),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                    },
                ),
                "video_max_num_frames": (
                    "INT",
                    {
                        "default": 64,
                    },
                ),  # if cuda OOM set a smaller number
                "video_max_slice_nums": (
                    "INT",
                    {
                        "default": 2,
                    },
                ),  # use 1 if cuda OOM and video resolution >  448*448
            },
            "optional": {
                "source_video_path": ("VIDEO",),
                "source_image_path_1st": ("IMAGE",),
                "source_image_path_2nd": ("IMAGE",),
                "source_image_path_3rd": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "inference"
    CATEGORY = "MiniCPM-V"

    def encode_video(self, source_video_path, MAX_NUM_FRAMES):
        def uniform_sample(l, n):  # noqa: E741
            gap = len(l) / n
            idxs = [int(i * gap + gap / 2) for i in range(n)]
            return [l[i] for i in idxs]

        vr = VideoReader(source_video_path, ctx=cpu(0))
        total_frames = len(vr) + 1
        print("Total frames:", total_frames)
        avg_fps = vr.get_avg_fps()
        print("Get average FPS(frame per second):", avg_fps)
        sample_fps = round(avg_fps / 1)  # FPS 
        duration = len(vr) / avg_fps
        print("Total duration:", duration, "seconds")
        width = vr[0].shape[1] 
        height = vr[0].shape[0] 
        print("Video resolution(width x height):", width, "x", height)
        
        frame_idx = [i for i in range(0, len(vr), sample_fps)]
        if len(frame_idx) > MAX_NUM_FRAMES:
            frame_idx = uniform_sample(frame_idx, MAX_NUM_FRAMES)
        frames = vr.get_batch(frame_idx).asnumpy()
        frames = [Image.fromarray(v.astype("uint8")) for v in frames]
        print("num frames:", len(frames))
        return frames

    def inference(
        self,
        text,
        model,
        temperature,
        video_max_num_frames,
        video_max_slice_nums,
        source_image_path_1st=None,
        source_image_path_2nd=None,
        source_image_path_3rd=None,
        source_video_path=None,
    ):
        model_id = f"openbmb/{model}"
        model_checkpoint = os.path.join(
            folder_paths.models_dir, "prompt_generator", os.path.basename(model_id)
        )

        if not os.path.exists(model_checkpoint):
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=model_id,
                local_dir=model_checkpoint,
                local_dir_use_symlinks=False,
            )

        if self.model_checkpoint != model_checkpoint:
            self.model_checkpoint = model_checkpoint
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_checkpoint, trust_remote_code=True
            )
            self.model = AutoModel.from_pretrained(
                model_checkpoint, trust_remote_code=True, torch_dtype=torch.bfloat16
            )

        with torch.no_grad():
            if source_video_path:
                frames = self.encode_video(source_video_path, video_max_num_frames)
                msgs = [{"role": "user", "content": frames + [text]}]
            elif (
                source_image_path_1st is not None
                and source_image_path_2nd is not None
                and source_image_path_3rd is not None
            ):
                image1 = ToPILImage()(
                    source_image_path_1st.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                image2 = ToPILImage()(
                    source_image_path_2nd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                image3 = ToPILImage()(
                    source_image_path_3rd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image1, image2, image3, text]}]
            elif (
                source_image_path_1st is not None
                and source_image_path_2nd is not None
                and source_image_path_3rd is None
            ):
                image1 = ToPILImage()(
                    source_image_path_1st.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                image2 = ToPILImage()(
                    source_image_path_2nd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image1, image2, text]}]
            elif (
                source_image_path_1st is not None
                and source_image_path_2nd is None
                and source_image_path_3rd is not None
            ):
                image1 = ToPILImage()(
                    source_image_path_1st.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                image3 = ToPILImage()(
                    source_image_path_3rd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image1, image3, text]}]
            elif (
                source_image_path_1st is None
                and source_image_path_2nd is not None
                and source_image_path_3rd is not None
            ):
                image2 = ToPILImage()(
                    source_image_path_2nd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                image3 = ToPILImage()(
                    source_image_path_3rd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image2, image3, text]}]
            elif (
                source_image_path_1st is not None
                and source_image_path_2nd is None
                and source_image_path_3rd is None
            ):
                image = ToPILImage()(
                    source_image_path_1st.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image, text]}]
            elif (
                source_image_path_1st is None
                and source_image_path_2nd is not None
                and source_image_path_3rd is None
            ):
                image = ToPILImage()(
                    source_image_path_2nd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image, text]}]
            elif (
                source_image_path_1st is None
                and source_image_path_2nd is None
                and source_image_path_3rd is not None
            ):
                image = ToPILImage()(
                    source_image_path_3rd.permute([0, 3, 1, 2])[0]
                ).convert("RGB")
                msgs = [{"role": "user", "content": [image, text]}]
            else:
                msgs = [{"role": "user", "content": [text]}]
                # raise ValueError("Either image or video must be provided")

            params = {"use_image_id": False, "max_slice_nums": video_max_slice_nums}

            result = self.model.chat(
                image=None,
                msgs=msgs,
                tokenizer=self.tokenizer,
                sampling=True,
                temperature=temperature,
                **params,
            )
            return (result,)
