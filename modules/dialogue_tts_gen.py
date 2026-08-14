import numpy as np
import soundfile as sf

from modules.config import CONFIG
from modules.tts_gen import synthesize_text


def _voice_for_speaker(speaker: str, characters: list[dict]) -> str:
    for c in characters:
        if c["name"] == speaker:
            return c["voice"]
    return CONFIG["tts"]["voice"]


def generate_dialogue_audio(script: dict, out_dir, characters: list[dict] | None = None,
                             gap_sec: float = 0.3) -> dict:
    """Sinh 1 file wav rieng cho moi cau thoai (giong theo tung nhan vat), ghep thanh
    full.wav, va tra ve timing chinh xac cho tung line + tung scene (dung cho subtitle
    va export CapCut, khong can doan lai bang Whisper vi text da biet truoc)."""
    characters = characters or CONFIG["characters"]
    out_dir.mkdir(parents=True, exist_ok=True)

    all_samples = []
    sample_rate = None
    line_timings = []
    scene_timings = []
    cursor = 0.0

    for scene in script["scenes"]:
        scene_start = cursor
        for line in scene["lines"]:
            voice = _voice_for_speaker(line["speaker"], characters)
            samples, sr = synthesize_text(line["text"], voice=voice)
            sample_rate = sr

            path = out_dir / f"line_{line['line_id']:03d}.wav"
            sf.write(str(path), samples, sr)

            duration = len(samples) / sr
            line_timings.append({
                "line_id": line["line_id"],
                "scene_id": scene["scene_id"],
                "speaker": line["speaker"],
                "text": line["text"],
                "expression": line["expression"],
                "start_sec": round(cursor, 3),
                "end_sec": round(cursor + duration, 3),
                "wav_path": str(path),
            })
            cursor += duration + gap_sec

            all_samples.append(samples)
            all_samples.append(np.zeros(int(gap_sec * sr), dtype=samples.dtype))

        scene_timings.append({
            "scene_id": scene["scene_id"],
            "start_sec": round(scene_start, 3),
            "end_sec": round(cursor - gap_sec, 3),
        })

    full_samples = np.concatenate(all_samples[:-1]) if all_samples else np.zeros(0, dtype=np.float32)
    full_path = out_dir / "full.wav"
    sf.write(str(full_path), full_samples, sample_rate or 24000)

    return {
        "full_path": str(full_path),
        "line_timings": line_timings,
        "scene_timings": scene_timings,
        "total_duration_sec": round(max(cursor - gap_sec, 0.0), 3),
    }
