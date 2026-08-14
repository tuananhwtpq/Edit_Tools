"""Xuat goi asset cho che do Sticker Dialogue de nguoi dung tu keo vao CapCut.

Thay vi co gang tao thang draft noi bo cua CapCut (dinh dang doi lien tuc, khong
on dinh giua cac ban CapCut - da thu 2 thu vien khac nhau deu that bai), huong nay
dung ffmpeg (da co san, dang tin cay) de dung san:
  - background.mp4   : video nen Ken Burns, khop dung tong thoi luong
  - <Ten>_overlay.mov : video trong suot (alpha, codec qtrle) cho tung nhan vat,
                        sticker da duoc dat dung vi tri tren man hinh va tu doi
                        bieu cam theo dung luc nhan vat do noi
  - full.wav          : audio day du (co san tu buoi 11)
  - subtitle.srt       : phu de (co san tu buoi 11, CapCut co the Import Captions
                        truc tiep tu file .srt nay, khong can dung code tu tao)

Nguoi dung chi can keo 4 file nay vao 4 track + import srt - khong phai dat tay
tung doan nho, va khong phu thuoc dinh dang draft noi bo hay doi cua CapCut.
"""

import shutil
from pathlib import Path

from modules.config import CONFIG, ASSETS_DIR
from modules.video_assembly import FFMPEG, _run, _concat_clips, assemble_dialogue_background
from modules.character_gen import CANVAS_SIZE

CHAR_DISPLAY_HEIGHT_RATIO = 0.7  # ty le chieu cao nhan vat / chieu cao video
CHAR_ASPECT = CANVAS_SIZE[0] / CANVAS_SIZE[1]


def _char_position(side: str, canvas_w: int, canvas_h: int) -> tuple[int, int, int, int]:
    disp_h = round(canvas_h * CHAR_DISPLAY_HEIGHT_RATIO)
    disp_w = round(disp_h * CHAR_ASPECT)
    disp_w += disp_w % 2
    disp_h += disp_h % 2
    cx = canvas_w * (0.25 if side == "left" else 0.75)
    x = round(cx - disp_w / 2)
    y = canvas_h - disp_h - round(canvas_h * 0.03)
    return disp_w, disp_h, x, y


def _sticker_clip(sticker_path: Path, out_path: Path, duration: float, disp_w: int, disp_h: int,
                   x: int, y: int, canvas_w: int, canvas_h: int):
    vf = f"scale={disp_w}:{disp_h},pad={canvas_w}:{canvas_h}:{x}:{y}:color=black@0.0"
    _run([
        FFMPEG, "-y", "-loop", "1", "-i", str(sticker_path),
        "-vf", vf, "-t", f"{duration:.3f}", "-r", str(CONFIG["video"]["fps"]),
        "-c:v", "qtrle",
        str(out_path),
    ])


def build_character_overlay(character: dict, line_timings: list[dict], out_path: Path,
                             progress_cb=None) -> str:
    cfg = CONFIG["video"]
    width, height = cfg["resolution"]
    disp_w, disp_h, x, y = _char_position(character.get("side", "left"), width, height)

    work_dir = out_path.parent / f"_work_{character['name']}"
    work_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for i, line in enumerate(line_timings, start=1):
        expression = line["expression"] if line["speaker"] == character["name"] else "neutral"
        sticker_path = ASSETS_DIR / "characters" / character["name"] / f"{expression}.png"
        # Duration = toi truoc line ke tiep (bao gom ca khoang lang) de tong do dai
        # khop chinh xac voi background/audio, giong cach tinh scene duration.
        next_start = line_timings[i]["start_sec"] if i < len(line_timings) else line["end_sec"]
        duration = next_start - line["start_sec"]
        clip_path = work_dir / f"line_{line['line_id']:03d}.mov"
        if progress_cb:
            progress_cb(i, len(line_timings), character["name"])
        _sticker_clip(sticker_path, clip_path, duration, disp_w, disp_h, x, y, width, height)
        clip_paths.append(clip_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _concat_clips(clip_paths, out_path)
    shutil.rmtree(work_dir, ignore_errors=True)
    return str(out_path)


GUIDE_TEMPLATE = """# Huong dan ghep video trong CapCut

Project: {title}
Tong thoi luong: {duration}s

## Cac file da dung san (trong thu muc nay)

- `background.mp4`   - video nen (Ken Burns), keo vao track duoi cung
- {overlay_lines}
- `audio/full.wav`   - audio hoi thoai day du, keo vao track am thanh
- `subtitle.srt`     - phu de, dung tinh nang "Captions > Import" cua CapCut (khong
                       keo nhu video/audio thuong, tim trong menu Text/Captions)

## Cac buoc

1. Mo CapCut, tao project moi (hoac keo truc tiep vao 1 project trong)
2. Keo `background.mp4` vao track video duoi cung (track 1)
3. Keo tung file `*_overlay.mov` vao 1 track video rieng, phia tren track nen
   (cac file nay co nen trong suot san, khong che mat nhau)
4. Keo `audio/full.wav` vao track am thanh - tat ca da dung timing san, khop voi
   video, khong can chinh gi them
5. Vao Text/Captions > Import (hoac tuong tu) > chon file `subtitle.srt`
6. Xem lai, chinh sua neu can (doi font, mau, vi tri chu, effect...), roi Export

Tat ca file da dung dung thoi luong tu dau, chi can keo dung thu tu la khop, khong
phai dat tay tung doan nho.
"""


def export_dialogue_package(script: dict, audio_meta: dict, images_dir: Path, out_dir: Path,
                             characters: list[dict] | None = None, progress_cb=None) -> dict:
    characters = characters or CONFIG["characters"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if progress_cb:
        progress_cb("background", 0, 1)
    bg_path = assemble_dialogue_background(audio_meta["scene_timings"], images_dir, out_dir / "background.mp4")

    overlay_paths = {}
    for char in characters:
        if progress_cb:
            progress_cb(f"overlay:{char['name']}", 0, 1)
        overlay_path = build_character_overlay(
            char, audio_meta["line_timings"], out_dir / f"{char['name']}_overlay.mov",
        )
        overlay_paths[char["name"]] = overlay_path

    overlay_lines = "\n".join(f"- `{Path(p).name}` - overlay nhan vat {name} (trong suot)"
                               for name, p in overlay_paths.items())
    guide = GUIDE_TEMPLATE.format(
        title=script.get("title", ""),
        duration=audio_meta["total_duration_sec"],
        overlay_lines=overlay_lines,
    )
    guide_path = out_dir / "HUONG_DAN_CAPCUT.md"
    with open(guide_path, "w") as f:
        f.write(guide)

    return {
        "background": bg_path,
        "overlays": overlay_paths,
        "guide": str(guide_path),
    }
