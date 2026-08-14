import json
import re
import unicodedata

from modules.config import PROJECTS_DIR


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:max_len].strip("-") or "video"


def project_dir(slug: str):
    d = PROJECTS_DIR / slug
    (d / "audio").mkdir(parents=True, exist_ok=True)
    (d / "images").mkdir(parents=True, exist_ok=True)
    return d


def save_script(slug: str, script: dict) -> str:
    d = project_dir(slug)
    path = d / "script.json"
    with open(path, "w") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    return str(path)


def load_script(slug: str) -> dict:
    path = project_dir(slug) / "script.json"
    with open(path, "r") as f:
        return json.load(f)


def save_audio_meta(slug: str, meta: dict) -> str:
    d = project_dir(slug)
    path = d / "audio_meta.json"
    with open(path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return str(path)


def load_audio_meta(slug: str) -> dict:
    path = project_dir(slug) / "audio_meta.json"
    with open(path, "r") as f:
        return json.load(f)


def list_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir())
