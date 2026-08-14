from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def load_config() -> dict:
    with open(ROOT_DIR / "config.yaml", "r") as f:
        return yaml.safe_load(f)


CONFIG = load_config()
PROJECTS_DIR = ROOT_DIR / CONFIG["paths"]["projects_dir"]
ASSETS_DIR = ROOT_DIR / CONFIG["paths"]["assets_dir"]
