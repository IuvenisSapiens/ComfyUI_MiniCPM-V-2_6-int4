import os
import torch
import folder_paths
from transformers import AutoTokenizer, AutoModel
from torchvision.transforms.v2 import ToPILImage
from decord import VideoReader, cpu  # pip install decord
from PIL import Image


class MiniCPM_Chat:
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
                "model": (
                    ["MiniCPM-V-2_6-int4", "MiniCPM-Llama3-V-2_5-int4"],
                    {"default": "MiniCPM-V-2_6-int4"},
                ),
                "keep_model_loaded": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": -1}),  # add seed parameter, default is -1
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "inference"
    CATEGORY = "Comfyui_MiniCPM-V-2_6-int4"

    def inference(
        self,
        text,
        model,
        keep_model_loaded,
        seed,
    ):
        top_p = 0.8
        top_k = 100
        temperature = 0.7
        repetition_penalty = 1.05
        max_new_tokens = 2048

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
            image = Image.new('RGB', (100, 100), color = 'white')
            msgs = [{"role": "user", "content": [image, text]}]

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

            return {"ui": {"text": (result,)}, "result": (result,)}
