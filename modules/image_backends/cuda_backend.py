"""Backend sinh anh dung diffusers + PyTorch CUDA - danh cho may Windows/Linux co GPU NVIDIA.

Dung 4-bit quantization (bitsandbytes) cho transformer va text_encoder_2 (T5) de vua
duoc trong VRAM han che (~8GB+) cua GPU gaming pho thong, ket hop model CPU offload.
Neu van OOM tren GPU VRAM rat thap (<=6GB), thu enable_sequential_cpu_offload() thay
cho enable_model_cpu_offload() trong _get_pipeline() (cham hon nhung it VRAM hon).
"""

import torch

from modules.config import CONFIG

MODEL_ID = "black-forest-labs/FLUX.1-schnell"

_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        from diffusers import FluxPipeline, FluxTransformer2DModel
        from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
        from transformers import T5EncoderModel
        from transformers import BitsAndBytesConfig as TransformersBitsAndBytesConfig

        text_encoder_2 = T5EncoderModel.from_pretrained(
            MODEL_ID,
            subfolder="text_encoder_2",
            quantization_config=TransformersBitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16),
            torch_dtype=torch.bfloat16,
        )
        transformer = FluxTransformer2DModel.from_pretrained(
            MODEL_ID,
            subfolder="transformer",
            quantization_config=DiffusersBitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16),
            torch_dtype=torch.bfloat16,
        )
        _pipe = FluxPipeline.from_pretrained(
            MODEL_ID,
            transformer=transformer,
            text_encoder_2=text_encoder_2,
            torch_dtype=torch.bfloat16,
        )
        _pipe.enable_model_cpu_offload()
    return _pipe


def generate_image(prompt: str, out_path, seed: int, width: int | None = None,
                    height: int | None = None, steps: int | None = None,
                    style_suffix: str | None = None) -> str:
    pipe = _get_pipeline()
    cfg = CONFIG["image"]
    full_prompt = f"{prompt}, {style_suffix if style_suffix is not None else cfg['style_suffix']}"
    generator = torch.Generator("cpu").manual_seed(seed)
    image = pipe(
        prompt=full_prompt,
        width=width or cfg["width"],
        height=height or cfg["height"],
        num_inference_steps=steps or cfg["steps"],
        max_sequence_length=256,
        generator=generator,
    ).images[0]
    image.save(str(out_path))
    return str(out_path)
