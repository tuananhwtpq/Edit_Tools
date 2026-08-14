"""Xuat draft CapCut (.json) tu dialogue script + audio timing + anh nen + sticker
nhan vat, dung thu vien pycapcut. Khong render video - nguoi dung mo file draft nay
trong CapCut de chinh sua/hoan thien/export, tiet kiem token thay vi render qua ffmpeg.
"""

from pathlib import Path

import pycapcut as cc

from modules.config import CONFIG, ASSETS_DIR


def _sec(value: float) -> str:
    return f"{value}s"


def build_dialogue_draft(scene_timings: list[dict], line_timings: list[dict], backgrounds_dir: Path,
                          srt_path: Path, out_path: Path, characters: list[dict] | None = None) -> str:
    characters = characters or CONFIG["characters"]
    width, height = CONFIG["video"]["resolution"]
    fps = CONFIG["video"]["fps"]

    draft = cc.ScriptFile(width, height, fps)
    draft.add_track(cc.TrackType.video, "Background")
    for char in characters:
        draft.add_track(cc.TrackType.video, char["name"])
    draft.add_track(cc.TrackType.audio, "Dialogue")
    draft.add_track(cc.TrackType.text, "Subtitle")

    for scene in scene_timings:
        bg_path = backgrounds_dir / f"bg_scene_{scene['scene_id']:02d}.png"
        duration = scene["end_sec"] - scene["start_sec"]
        seg = cc.VideoSegment(str(bg_path), cc.trange(_sec(scene["start_sec"]), _sec(duration)))
        draft.add_segment(seg, "Background")

    side_x = {"left": -0.45, "right": 0.45}
    for line in line_timings:
        duration = line["end_sec"] - line["start_sec"]
        for char in characters:
            expression = line["expression"] if char["name"] == line["speaker"] else "neutral"
            sticker_path = ASSETS_DIR / "characters" / char["name"] / f"{expression}.png"
            clip = cc.ClipSettings(
                scale_x=0.55, scale_y=0.55,
                transform_x=side_x.get(char.get("side"), 0.0),
                transform_y=-0.35,
            )
            seg = cc.VideoSegment(
                str(sticker_path), cc.trange(_sec(line["start_sec"]), _sec(duration)), clip_settings=clip,
            )
            draft.add_segment(seg, char["name"])

    for line in line_timings:
        duration = line["end_sec"] - line["start_sec"]
        seg = cc.AudioSegment(line["wav_path"], cc.trange(_sec(line["start_sec"]), _sec(duration)))
        draft.add_segment(seg, "Dialogue")

    if srt_path and Path(srt_path).exists():
        draft.import_srt(str(srt_path), "Subtitle")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    draft.dump(str(out_path))
    return str(out_path)
