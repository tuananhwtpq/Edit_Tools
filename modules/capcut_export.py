"""Xuat draft CapCut tu dialogue script + audio timing + anh nen + sticker nhan vat,
dung thu vien pycapcut. Ghi thang vao thu muc drafts cua CapCut de mo app la thay
project ngay, khong can import thu cong. Khong render video - nguoi dung mo CapCut
de chinh sua/hoan thien/export, tiet kiem token thay vi render qua ffmpeg.
"""

import os
import platform
from pathlib import Path

import pycapcut as cc

from modules.config import CONFIG, ASSETS_DIR


def _sec(value: float) -> str:
    return f"{value}s"


def default_capcut_drafts_dir() -> Path | None:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    if system == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return Path(local_appdata) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return None


def _build_tracks(draft: "cc.ScriptFile", scene_timings: list[dict], line_timings: list[dict],
                   backgrounds_dir: Path, srt_path: Path, characters: list[dict]):
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


def build_dialogue_draft(scene_timings: list[dict], line_timings: list[dict], backgrounds_dir: Path,
                          srt_path: Path, draft_name: str, fallback_out_path: Path,
                          characters: list[dict] | None = None, drafts_dir: Path | None = None) -> dict:
    characters = characters or CONFIG["characters"]
    width, height = CONFIG["video"]["resolution"]
    fps = CONFIG["video"]["fps"]

    drafts_dir = drafts_dir or default_capcut_drafts_dir()
    if drafts_dir and drafts_dir.exists():
        folder = cc.DraftFolder(str(drafts_dir))
        draft = folder.create_draft(draft_name, width, height, fps, allow_replace=True)
        _build_tracks(draft, scene_timings, line_timings, backgrounds_dir, srt_path, characters)
        draft.save()
        return {
            "location": "capcut_drafts_folder",
            "path": str(drafts_dir / draft_name),
            "message": f"Da ghi truc tiep vao thu muc CapCut. Mo CapCut, project '{draft_name}' se hien san trong danh sach.",
        }

    draft = cc.ScriptFile(width, height, fps)
    _build_tracks(draft, scene_timings, line_timings, backgrounds_dir, srt_path, characters)
    fallback_out_path.parent.mkdir(parents=True, exist_ok=True)
    draft.dump(str(fallback_out_path))
    return {
        "location": "file",
        "path": str(fallback_out_path),
        "message": (
            f"Khong tim thay thu muc drafts cua CapCut, da xuat ra file rieng: {fallback_out_path}. "
            "Ban can tu import file nay vao CapCut."
        ),
    }
