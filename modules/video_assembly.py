import shutil
import subprocess
from pathlib import Path

from modules.config import CONFIG

# Homebrew 'ffmpeg' (formula thuong) khong co libass/libfreetype -> khong burn duoc
# phu de/drawtext. 'ffmpeg-full' co day du. Uu tien ffmpeg-full neu co, fallback ffmpeg.
_FFMPEG_FULL = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")
FFMPEG = str(_FFMPEG_FULL) if _FFMPEG_FULL.exists() else (shutil.which("ffmpeg") or "ffmpeg")


def _run(cmd: list[str]):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Lenh ffmpeg loi:\n{' '.join(cmd)}\n--- stderr ---\n{result.stderr[-4000:]}")
    return result


def _make_scene_clip(image_path: str, out_path: Path, duration: float, width: int, height: int,
                      fps: int, zoom_max: float = 1.12):
    """Tao 1 doan video tu 1 anh tinh, co hieu ung Ken Burns (zoom nhe dan)."""
    n_frames = max(1, round(duration * fps))
    zoom_step = (zoom_max - 1.0) / n_frames
    vf = (
        f"scale={width * 2}:{height * 2},"
        f"zoompan=z='min(zoom+{zoom_step:.8f},{zoom_max})':d={n_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )
    _run([
        FFMPEG, "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(out_path),
    ])


def _concat_clips(clip_paths: list[Path], out_path: Path):
    list_file = out_path.parent / "_concat_list.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")
    _run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)])
    list_file.unlink()


def _add_audio(video_path: Path, audio_path: Path, out_path: Path, music_path: str | None,
                music_volume: float):
    if music_path:
        _run([
            FFMPEG, "-y", "-i", str(video_path), "-i", str(audio_path), "-stream_loop", "-1", "-i", music_path,
            "-filter_complex",
            f"[2:a]volume={music_volume}[music];[1:a][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_path),
        ])
    else:
        _run([
            FFMPEG, "-y", "-i", str(video_path), "-i", str(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_path),
        ])


def _burn_subtitles(video_path: Path, srt_path: Path, out_path: Path):
    srt_escaped = str(srt_path.resolve()).replace(":", r"\:").replace("'", r"\'")
    style = "FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Alignment=2,MarginV=60"
    _run([
        FFMPEG, "-y", "-i", str(video_path),
        "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
        "-c:a", "copy", str(out_path),
    ])


def assemble_video(scenes: list[dict], scene_timings: list[dict], images_dir: Path, audio_full_path: str,
                    out_path: Path, srt_path: Path | None = None, music_path: str | None = None,
                    progress_cb=None) -> str:
    cfg = CONFIG["video"]
    width, height = cfg["resolution"]
    fps = cfg["fps"]

    work_dir = out_path.parent / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    timing_by_id = {t["scene_id"]: t for t in scene_timings}

    clip_paths = []
    for i, scene in enumerate(scenes, start=1):
        t = timing_by_id[scene["scene_id"]]
        # Duration = toi truoc scene ke tiep (bao gom ca khoang lang giua cac scene)
        idx = scene_timings.index(t)
        next_start = scene_timings[idx + 1]["start_sec"] if idx + 1 < len(scene_timings) else t["end_sec"]
        duration = next_start - t["start_sec"]

        image_path = images_dir / f"scene_{scene['scene_id']:02d}.png"
        clip_path = work_dir / f"clip_{scene['scene_id']:02d}.mp4"
        if progress_cb:
            progress_cb(i, len(scenes), scene["scene_id"], "ken-burns")
        _make_scene_clip(image_path, clip_path, duration=duration, width=width, height=height, fps=fps)
        clip_paths.append(clip_path)

    if progress_cb:
        progress_cb(len(scenes), len(scenes), None, "concat")
    concatenated = work_dir / "concatenated.mp4"
    _concat_clips(clip_paths, concatenated)

    if progress_cb:
        progress_cb(len(scenes), len(scenes), None, "audio")
    with_audio = work_dir / "with_audio.mp4"
    _add_audio(concatenated, Path(audio_full_path), with_audio, music_path, cfg["background_music_volume"])

    final_source = with_audio
    if srt_path and Path(srt_path).exists():
        if progress_cb:
            progress_cb(len(scenes), len(scenes), None, "subtitle")
        with_subs = work_dir / "with_subs.mp4"
        _burn_subtitles(with_audio, Path(srt_path), with_subs)
        final_source = with_subs

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(final_source, out_path)
    shutil.rmtree(work_dir, ignore_errors=True)

    if progress_cb:
        progress_cb(len(scenes), len(scenes), None, "done")
    return str(out_path)


def assemble_dialogue_background(scene_timings: list[dict], images_dir: Path, out_path: Path,
                                  progress_cb=None) -> str:
    """Dung cho che do Sticker Dialogue: ghep cac anh nen (bg_scene_XX.png) thanh 1 video
    nen lien tuc (Ken Burns), khop chinh xac voi tong thoi luong audio. Khong co
    audio/subtitle - do la cac lop rieng nguoi dung tu keo vao CapCut."""
    cfg = CONFIG["video"]
    width, height = cfg["resolution"]
    fps = cfg["fps"]

    work_dir = out_path.parent / "_work_bg"
    work_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for i, scene in enumerate(scene_timings, start=1):
        next_start = scene_timings[i]["start_sec"] if i < len(scene_timings) else scene["end_sec"]
        duration = next_start - scene["start_sec"]
        image_path = images_dir / f"bg_scene_{scene['scene_id']:02d}.png"
        clip_path = work_dir / f"clip_{scene['scene_id']:02d}.mp4"
        if progress_cb:
            progress_cb(i, len(scene_timings), scene["scene_id"])
        _make_scene_clip(image_path, clip_path, duration=duration, width=width, height=height, fps=fps)
        clip_paths.append(clip_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _concat_clips(clip_paths, out_path)
    shutil.rmtree(work_dir, ignore_errors=True)
    return str(out_path)


def generate_thumbnail(image_path: str, out_path: Path, title: str):
    """Tao thumbnail tu 1 anh co san, resize ve chuan YouTube 1280x720 va overlay tieu de."""
    width, height = 1280, 720
    title_escaped = title.replace(":", r"\:").replace("'", r"\'")
    style = "fontsize=64:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=20:x=(w-text_w)/2:y=h-th-60"
    _run([
        FFMPEG, "-y", "-i", str(image_path),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
        f"drawtext=text='{title_escaped}':{style}",
        str(out_path),
    ])
    return str(out_path)
