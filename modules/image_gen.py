from modules.config import CONFIG

_backend = None


def _get_backend():
    global _backend
    if _backend is None:
        name = CONFIG["image"]["backend"]
        if name == "mlx":
            from modules.image_backends import mlx_backend as _backend_module
        elif name == "cuda":
            from modules.image_backends import cuda_backend as _backend_module
        else:
            raise ValueError(f"Unknown image backend: {name} (chon 'mlx' hoac 'cuda' trong config.yaml)")
        _backend = _backend_module
    return _backend


def generate_image(prompt: str, out_path, seed: int, width: int | None = None,
                    height: int | None = None, steps: int | None = None,
                    style_suffix: str | None = None) -> str:
    backend = _get_backend()
    return backend.generate_image(prompt, out_path, seed=seed, width=width, height=height, steps=steps,
                                   style_suffix=style_suffix)


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


DIALOGUE_BG_STYLE = "flat vector illustration background, minimalist, soft colors, no people, no characters, no text"


def generate_dialogue_backgrounds(scenes: list[dict], out_dir, width: int | None = None,
                                   height: int | None = None, steps: int | None = None,
                                   progress_cb=None) -> list[dict]:
    """Sinh 1 anh nen cho moi scene cua che do dialogue (khong co nhan vat trong anh,
    nhan vat la lop sticker rieng do CapCut ghep)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        out_path = out_dir / f"bg_scene_{scene['scene_id']:02d}.png"
        generate_image(scene["background_prompt"], out_path, seed=scene["scene_id"], width=width,
                        height=height, steps=steps, style_suffix=DIALOGUE_BG_STYLE)
        results.append({"scene_id": scene["scene_id"], "path": str(out_path)})
        if progress_cb:
            progress_cb(i, total, scene["scene_id"])
    return results
