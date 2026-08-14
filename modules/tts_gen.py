import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from modules.config import CONFIG, ROOT_DIR

_MODEL_PATH = ROOT_DIR / "models" / "kokoro-v1.0.onnx"
_VOICES_PATH = ROOT_DIR / "models" / "voices-v1.0.bin"

_kokoro = None


def _get_kokoro() -> Kokoro:
    global _kokoro
    if _kokoro is None:
        if not _MODEL_PATH.exists() or not _VOICES_PATH.exists():
            raise FileNotFoundError(
                f"Khong tim thay model Kokoro tai {_MODEL_PATH} / {_VOICES_PATH}. "
                "Xem README de tai model."
            )
        _kokoro = Kokoro(str(_MODEL_PATH), str(_VOICES_PATH))
    return _kokoro


def synthesize_text(text: str, voice: str | None = None, speed: float | None = None) -> tuple[np.ndarray, int]:
    kokoro = _get_kokoro()
    voice = voice or CONFIG["tts"]["voice"]
    speed = speed or CONFIG["tts"]["speed"]
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    return samples, sample_rate


def generate_scene_audio(scenes: list[dict], out_dir, voice: str | None = None,
                          speed: float | None = None, gap_sec: float = 0.4) -> dict:
    """Sinh audio cho tung scene, luu file rieng + ghep thanh 1 file full.wav.

    Tra ve dict: {"scene_files": [...], "full_path": str, "scene_timings": [{"scene_id", "start_sec", "end_sec"}]}
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_files = []
    all_samples = []
    sample_rate = None
    timings = []
    cursor = 0.0

    for scene in scenes:
        samples, sr = synthesize_text(scene["narration"], voice=voice, speed=speed)
        sample_rate = sr
        scene_path = out_dir / f"scene_{scene['scene_id']:02d}.wav"
        sf.write(str(scene_path), samples, sr)
        scene_files.append(str(scene_path))

        duration = len(samples) / sr
        timings.append({
            "scene_id": scene["scene_id"],
            "start_sec": round(cursor, 3),
            "end_sec": round(cursor + duration, 3),
        })
        cursor += duration + gap_sec

        all_samples.append(samples)
        if scene is not scenes[-1]:
            all_samples.append(np.zeros(int(gap_sec * sr), dtype=samples.dtype))

    full_samples = np.concatenate(all_samples)
    full_path = out_dir / "full.wav"
    sf.write(str(full_path), full_samples, sample_rate)

    return {
        "scene_files": scene_files,
        "full_path": str(full_path),
        "scene_timings": timings,
        "total_duration_sec": round(cursor - gap_sec, 3),
    }
