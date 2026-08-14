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
    full_prompt = f"{prompt}, {CONFIG['image']['style_suffix']}"
    image = flux.generate_image(
        seed=seed,
        prompt=full_prompt,
        width=width or CONFIG["image"]["width"],
        height=height or CONFIG["image"]["height"],
        num_inference_steps=steps or CONFIG["image"]["steps"],
    )
    image.save(path=str(out_path))
    return str(out_path)


def generate_scene_images(scenes: list[dict], out_dir, base_seed: int = 0,
                           width: int | None = None, height: int | None = None,
                           steps: int | None = None, progress_cb=None) -> list[dict]:
    """Sinh 1 anh cho moi scene. Dung base_seed + scene_id de giu tinh nhat quan
    tuong doi giua cac seed (cung mot 'nhanh' random) trong khi van khac nhau tung anh.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        seed = base_seed + scene["scene_id"]
        out_path = out_dir / f"scene_{scene['scene_id']:02d}.png"
        generate_image(scene["image_prompt"], out_path, seed=seed, width=width, height=height, steps=steps)
        results.append({"scene_id": scene["scene_id"], "path": str(out_path), "seed": seed})
        if progress_cb:
            progress_cb(i, total, scene["scene_id"])
    return results
