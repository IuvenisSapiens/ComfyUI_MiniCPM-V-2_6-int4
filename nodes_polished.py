import os
import torch
import folder_paths
from transformers import AutoTokenizer, AutoModel
from torchvision.transforms.v2 import ToPILImage
from decord import VideoReader, cpu  # pip install decord
from PIL import Image


class MiniCPM_VQA_Polished:
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
                "keep_model_loaded": ("BOOLEAN", {"default": False}),
                "top_p": (
                    "FLOAT",
                    {
                        "default": 0.8,
                    },
                ),
                "top_k": (
                    "INT",
                    {
                        "default": 100,
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0, "max": 1, "step": 0.1},
                ),
                "repetition_penalty": (
                    "FLOAT",
                    {
                        "default": 1.05,
                    },
                ),
                "max_new_tokens": (
                    "INT",
                    {
                        "default": 2048,
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
                "seed": ("INT", {"default": -1}),  # add seed parameter, default is -1
            },
            "optional": {
                "source_video_path": ("PATH",),
                "source_image_path": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "inference"
    CATEGORY = "Comfyui_MiniCPM-V-2_6-int4"

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
        keep_model_loaded,
        top_p,
        top_k,
        temperature,
        repetition_penalty,
        max_new_tokens,
        video_max_num_frames,
        video_max_slice_nums,
        seed=-1,  # add seed parameter, default is -1
        source_image_path=None,
        source_video_path=None,
    ):
        if seed != -1:
            torch.manual_seed(seed)
        model_id = f"openbmb/{model}"
        self.model_checkpoint = os.path.join(
            folder_paths.models_dir, "prompt_generator", os.path.basename(model_id)
        )

        if not os.path.exists(self.model_checkpoint):
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=model_id,
                local_dir=self.model_checkpoint,
                local_dir_use_symlinks=False,
            )

        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

        if self.model is None:
            self.model = AutoModel.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                attn_implementation="sdpa",
                torch_dtype=torch.bfloat16 if self.bf16_support else torch.float16,
            )

        with torch.no_grad():
            if source_video_path:
                print("source_video_path:", source_video_path)
                frames = self.encode_video(source_video_path, video_max_num_frames)
                msgs = [{"role": "user", "content": frames + [text]}]
            elif source_image_path is not None:
                images = source_image_path.permute([0, 3, 1, 2])
                images = [ToPILImage()(img).convert("RGB") for img in images]
                msgs = [{"role": "user", "content": images + [text]}]
            else:
                msgs = [{"role": "user", "content": [text]}]
                # raise ValueError("Either image or video must be provided")

            params = {"use_image_id": False, "max_slice_nums": video_max_slice_nums}

            # offload model to CPU
            # self.model = self.model.to(torch.device("cpu"))
            # self.model.eval()

            result = self.model.chat(
                image=None,
                msgs=msgs,
                tokenizer=self.tokenizer,
                sampling=True,
                top_k=top_k,
                top_p=top_p,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                max_new_tokens=max_new_tokens,
                **params,
            )
            # offload model to GPU
            # self.model = self.model.to(torch.device("cpu"))
            # self.model.eval()
            if not keep_model_loaded:
                del self.tokenizer  # release tokenizer memory
                del self.model  # release model memory
                self.tokenizer = None  # set tokenizer to None
                self.model = None  # set model to None
                torch.cuda.empty_cache()  # release GPU memory
                torch.cuda.ipc_collect()

            return (result,)
