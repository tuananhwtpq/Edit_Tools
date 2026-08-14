"""Backend sinh anh dung mflux (MLX native FLUX) - chi chay tren macOS Apple Silicon."""

from modules.config import CONFIG

_flux = None


def _get_flux():
    global _flux
    if _flux is None:
        from mflux.models.common.config.model_config import ModelConfig
        from mflux.models.flux.variants.txt2img.flux import Flux1

        model_config = ModelConfig.from_name(CONFIG["image"]["model"])
        _flux = Flux1(model_config=model_config, quantize=CONFIG["image"]["quantize"])
    return _flux


def generate_image(prompt: str, out_path, seed: int, width: int | None = None,
                    height: int | None = None, steps: int | None = None) -> str:
    flux = _get_flux()
    cfg = CONFIG["image"]
    full_prompt = f"{prompt}, {cfg['style_suffix']}"
    image = flux.generate_image(
        seed=seed,
        prompt=full_prompt,
        width=width or cfg["width"],
        height=height or cfg["height"],
        num_inference_steps=steps or cfg["steps"],
    )
    image.save(path=str(out_path))
    return str(out_path)
