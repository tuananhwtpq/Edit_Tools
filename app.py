import json

import gradio as gr

from modules.config import CONFIG, PROJECTS_DIR, ASSETS_DIR
from modules.project import slugify, save_script, load_script, save_audio_meta, load_audio_meta, project_dir, list_projects
from modules.script_gen import generate_script
from modules.tts_gen import generate_scene_audio
from modules.subtitle_gen import generate_srt
from modules.image_gen import generate_image, DIALOGUE_BG_STYLE
from modules.video_assembly import assemble_video, generate_thumbnail
from modules.character_gen import generate_all_characters, EXPRESSIONS
from modules.dialogue_script_gen import generate_dialogue_script
from modules.dialogue_tts_gen import generate_dialogue_audio
from modules.subtitle_gen import generate_dialogue_srt
from modules.capcut_export import build_dialogue_draft

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

KOKORO_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah",
    "am_adam", "am_michael", "am_onyx",
    "bf_emma", "bm_george",
]


def on_generate_script(topic, style, duration_min, provider):
    if not topic.strip():
        return "", "Vui long nhap chu de.", gr.update()
    script = generate_script(
        topic=topic,
        style=style,
        target_duration_min=duration_min,
        provider=provider,
    )
    slug = slugify(script.get("title", topic))
    script_str = json.dumps(script, indent=2, ensure_ascii=False)
    return script_str, f"Da tao script cho project: **{slug}**", slug


def on_save_script(script_str, slug):
    if not slug:
        return "Chua co project slug, hay Generate truoc."
    try:
        script = json.loads(script_str)
    except json.JSONDecodeError as e:
        return f"JSON khong hop le: {e}"
    path = save_script(slug, script)
    return f"Da luu: {path}"


def on_load_script_for_voice(slug):
    if not slug:
        return "Chua chon project.", ""
    try:
        script = load_script(slug)
    except FileNotFoundError:
        return f"Khong tim thay script.json cho project '{slug}'.", ""
    lines = [f"[{s['scene_id']}] {s['narration']}" for s in script.get("scenes", [])]
    return f"Da load {len(lines)} scene tu project **{slug}**.", "\n\n".join(lines)


def on_generate_voice(slug, voice, speed):
    if not slug:
        return None, "Chua chon project."
    try:
        script = load_script(slug)
    except FileNotFoundError:
        return None, f"Khong tim thay script.json cho project '{slug}'."
    d = project_dir(slug)
    result = generate_scene_audio(script["scenes"], d / "audio", voice=voice, speed=speed)
    save_audio_meta(slug, result)
    return result["full_path"], (
        f"Da sinh audio cho {len(result['scene_files'])} scene, "
        f"tong thoi luong {result['total_duration_sec']}s. Luu tai: {result['full_path']}"
    )


def on_generate_subtitle(slug, max_words):
    if not slug:
        return "", "Chua chon project."
    d = project_dir(slug)
    audio_path = d / "audio" / "full.wav"
    if not audio_path.exists():
        return "", f"Chua co audio full.wav cho project '{slug}'. Hay sang tab Voice generate truoc."
    out_path = d / "subtitle.srt"
    entries = generate_srt(audio_path, out_path, max_words_per_line=int(max_words))
    with open(out_path, "r") as f:
        srt_content = f.read()
    return srt_content, f"Da sinh {len(entries)} dong phu de. Luu tai: {out_path}"


def on_load_gallery(slug):
    if not slug:
        return []
    img_dir = project_dir(slug) / "images"
    paths = sorted(img_dir.glob("scene_*.png"))
    return [(str(p), p.stem) for p in paths]


def on_generate_images(slug, base_seed, width, height):
    if not slug:
        yield [], "Chua chon project."
        return
    try:
        script = load_script(slug)
    except FileNotFoundError:
        yield [], f"Khong tim thay script.json cho project '{slug}'."
        return

    img_dir = project_dir(slug) / "images"
    scenes = script["scenes"]
    gallery = []
    for i, scene in enumerate(scenes, start=1):
        yield gallery, f"Dang sinh anh {i}/{len(scenes)} (scene {scene['scene_id']})... co the mat 1-5 phut/anh."
        seed = int(base_seed) + scene["scene_id"]
        out_path = img_dir / f"scene_{scene['scene_id']:02d}.png"
        generate_image(scene["image_prompt"], out_path, seed=seed, width=int(width), height=int(height))
        gallery.append((str(out_path), f"Scene {scene['scene_id']}"))
        yield gallery, f"Da xong {i}/{len(scenes)} anh."
    yield gallery, f"Hoan tat! Da sinh {len(scenes)} anh cho project '{slug}'."


def on_assemble_video(slug, use_subtitle, use_music):
    if not slug:
        yield None, "Chua chon project."
        return
    d = project_dir(slug)
    try:
        script = load_script(slug)
        audio_meta = load_audio_meta(slug)
    except FileNotFoundError as e:
        yield None, f"Thieu du lieu: {e}"
        return

    images_dir = d / "images"
    missing = [s["scene_id"] for s in script["scenes"] if not (images_dir / f"scene_{s['scene_id']:02d}.png").exists()]
    if missing:
        yield None, f"Thieu anh cho scene: {missing}. Hay sang tab 4. Images generate truoc."
        return

    def progress(i, total, scene_id, stage):
        pass

    stages = {"ken-burns": "Dang tao hieu ung Ken Burns tung scene...", "concat": "Dang ghep cac scene...",
              "audio": "Dang ghep am thanh...", "subtitle": "Dang burn phu de...", "done": "Da xong."}
    yield None, stages["ken-burns"]

    srt_path = d / "subtitle.srt"
    music_files = list((ASSETS_DIR / "music").glob("*.mp3")) if use_music else []

    out_path = assemble_video(
        scenes=script["scenes"],
        scene_timings=audio_meta["scene_timings"],
        images_dir=images_dir,
        audio_full_path=audio_meta["full_path"],
        out_path=d / "output.mp4",
        srt_path=srt_path if use_subtitle and srt_path.exists() else None,
        music_path=str(music_files[0]) if music_files else None,
        progress_cb=lambda i, total, sid, stage: None,
    )
    yield out_path, f"Hoan tat! Video luu tai: {out_path}"


def on_generate_thumbnail(slug, scene_choice):
    if not slug:
        return None, "Chua chon project."
    d = project_dir(slug)
    try:
        script = load_script(slug)
    except FileNotFoundError:
        return None, f"Khong tim thay script.json cho project '{slug}'."
    img_path = d / "images" / f"scene_{int(scene_choice):02d}.png"
    if not img_path.exists():
        return None, f"Chua co anh cho scene {scene_choice}."
    out_path = d / "thumbnail.png"
    generate_thumbnail(img_path, out_path, script["title"])
    return str(out_path), f"Da tao thumbnail: {out_path}"


def on_generate_characters():
    paths = generate_all_characters()
    gallery = []
    for char_name, exprs in paths.items():
        for expr, p in exprs.items():
            gallery.append((p, f"{char_name} - {expr}"))
    names = ", ".join(paths.keys())
    return gallery, f"Da sinh sticker cho: {names} ({len(EXPRESSIONS)} bieu cam moi nguoi)."


def on_generate_dialogue(topic, duration_min, provider):
    if not topic.strip():
        return "", "Vui long nhap chu de.", ""
    script = generate_dialogue_script(topic=topic, target_duration_min=duration_min, provider=provider)
    slug = slugify(script.get("title", topic))
    script_str = json.dumps(script, indent=2, ensure_ascii=False)
    return script_str, f"Da tao dialogue script cho project: **{slug}**", slug


def on_generate_dialogue_voice(slug):
    if not slug:
        return None, "Chua chon project."
    try:
        script = load_script(slug)
    except FileNotFoundError:
        return None, f"Khong tim thay script.json cho project '{slug}'."
    d = project_dir(slug)
    result = generate_dialogue_audio(script, d / "audio")
    save_audio_meta(slug, result)
    generate_dialogue_srt(result["line_timings"], d / "subtitle.srt")
    return result["full_path"], (
        f"Da sinh voice cho {len(result['line_timings'])} cau thoai, "
        f"tong thoi luong {result['total_duration_sec']}s. Subtitle da luu tai subtitle.srt."
    )


def on_generate_dialogue_bg(slug, width, height):
    if not slug:
        yield [], "Chua chon project."
        return
    try:
        script = load_script(slug)
    except FileNotFoundError:
        yield [], f"Khong tim thay script.json cho project '{slug}'."
        return

    img_dir = project_dir(slug) / "images"
    scenes = script["scenes"]
    gallery = []
    for i, scene in enumerate(scenes, start=1):
        yield gallery, f"Dang sinh nen {i}/{len(scenes)} (scene {scene['scene_id']})..."
        out_path = img_dir / f"bg_scene_{scene['scene_id']:02d}.png"
        generate_image(scene["background_prompt"], out_path, seed=scene["scene_id"],
                        width=int(width), height=int(height), style_suffix=DIALOGUE_BG_STYLE)
        gallery.append((str(out_path), f"Scene {scene['scene_id']}"))
        yield gallery, f"Da xong {i}/{len(scenes)} anh nen."
    yield gallery, f"Hoan tat! Da sinh {len(scenes)} anh nen cho project '{slug}'."


def on_export_capcut(slug):
    if not slug:
        return "Chua chon project."
    d = project_dir(slug)
    try:
        audio_meta = load_audio_meta(slug)
    except FileNotFoundError:
        return "Chua co audio. Hay sang tab 8. Dialogue Voice generate truoc."

    missing_bg = [
        s["scene_id"] for s in audio_meta["scene_timings"]
        if not (d / "images" / f"bg_scene_{s['scene_id']:02d}.png").exists()
    ]
    if missing_bg:
        return f"Thieu anh nen cho scene: {missing_bg}. Hay generate o phan tren truoc."

    draft_path = build_dialogue_draft(
        scene_timings=audio_meta["scene_timings"],
        line_timings=audio_meta["line_timings"],
        backgrounds_dir=d / "images",
        srt_path=d / "subtitle.srt",
        out_path=d / "capcut_draft.json",
    )
    return f"Da xuat draft CapCut: {draft_path}\n\nMo CapCut, dung tinh nang import/mo draft de tiep tuc chinh sua."


with gr.Blocks(title="Faceless AI Video Studio") as demo:
    gr.Markdown("# Faceless AI Video Studio")

    with gr.Tab("1. Script"):
        with gr.Row():
            with gr.Column(scale=1):
                topic_in = gr.Textbox(label="Chu de video", placeholder="Vi du: The Lost City of Atlantis")
                style_in = gr.Textbox(
                    label="Tone / style",
                    value="engaging, conversational, documentary-style",
                )
                duration_in = gr.Slider(label="Do dai mong muon (phut)", minimum=0.5, maximum=15, value=3, step=0.5)
                provider_in = gr.Radio(
                    label="Script provider",
                    choices=["ollama", "anthropic"],
                    value=CONFIG["script"]["provider"] if CONFIG["script"]["provider"] in ("ollama", "anthropic") else "ollama",
                )
                generate_btn = gr.Button("Generate script", variant="primary")
                status_out = gr.Markdown()
            with gr.Column(scale=2):
                script_out = gr.Textbox(label="Script (JSON, co the sua tay)", lines=30)
                slug_state = gr.State("")
                save_btn = gr.Button("Save script vao project")
                save_status = gr.Markdown()

        generate_btn.click(
            on_generate_script,
            inputs=[topic_in, style_in, duration_in, provider_in],
            outputs=[script_out, status_out, slug_state],
        )
        save_btn.click(
            on_save_script,
            inputs=[script_out, slug_state],
            outputs=[save_status],
        )

    with gr.Tab("2. Voice"):
        with gr.Row():
            with gr.Column(scale=1):
                voice_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                voice_refresh_btn = gr.Button("Refresh danh sach project")
                load_script_btn = gr.Button("Load script")
                voice_load_status = gr.Markdown()
                voice_select_in = gr.Dropdown(label="Kokoro voice", choices=KOKORO_VOICES, value=CONFIG["tts"]["voice"])
                speed_in = gr.Slider(label="Toc do doc", minimum=0.5, maximum=1.5, value=CONFIG["tts"]["speed"], step=0.05)
                generate_voice_btn = gr.Button("Generate voice", variant="primary")
                voice_status = gr.Markdown()
            with gr.Column(scale=2):
                scenes_preview = gr.Textbox(label="Noi dung scene (tu script da luu)", lines=15, interactive=False)
                audio_out = gr.Audio(label="Audio full (tat ca scene ghep lai)", type="filepath")

        voice_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[voice_project_in])
        load_script_btn.click(
            on_load_script_for_voice,
            inputs=[voice_project_in],
            outputs=[voice_load_status, scenes_preview],
        )
        generate_voice_btn.click(
            on_generate_voice,
            inputs=[voice_project_in, voice_select_in, speed_in],
            outputs=[audio_out, voice_status],
        )

    with gr.Tab("3. Subtitle"):
        with gr.Row():
            with gr.Column(scale=1):
                sub_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                sub_refresh_btn = gr.Button("Refresh danh sach project")
                max_words_in = gr.Slider(label="So tu toi da moi dong phu de", minimum=3, maximum=12, value=7, step=1)
                generate_sub_btn = gr.Button("Generate subtitle (tu audio/full.wav)", variant="primary")
                sub_status = gr.Markdown()
            with gr.Column(scale=2):
                sub_out = gr.Textbox(label="Subtitle .srt", lines=25)

        sub_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[sub_project_in])
        generate_sub_btn.click(
            on_generate_subtitle,
            inputs=[sub_project_in, max_words_in],
            outputs=[sub_out, sub_status],
        )

    with gr.Tab("4. Images"):
        with gr.Row():
            with gr.Column(scale=1):
                img_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                img_refresh_btn = gr.Button("Refresh danh sach project")
                load_gallery_btn = gr.Button("Xem anh da co (neu co)")
                seed_in = gr.Number(label="Base seed", value=0, precision=0)
                width_in = gr.Dropdown(label="Chieu rong", choices=[512, 768, 1024], value=CONFIG["image"]["width"])
                height_in = gr.Dropdown(label="Chieu cao", choices=[512, 768, 1024], value=CONFIG["image"]["height"])
                gr.Markdown(
                    "Luu y: chay local tren Mac M4 (khong GPU roi), moi anh mat ~1 phut (512x512) "
                    "den ~4-5 phut (1024x1024). Sinh 4-8 anh co the mat 10-30 phut."
                )
                generate_img_btn = gr.Button("Generate images (tat ca scene)", variant="primary")
                img_status = gr.Markdown()
            with gr.Column(scale=2):
                gallery_out = gr.Gallery(label="Anh minh hoa theo scene", columns=2, object_fit="contain")

        img_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[img_project_in])
        load_gallery_btn.click(on_load_gallery, inputs=[img_project_in], outputs=[gallery_out])
        generate_img_btn.click(
            on_generate_images,
            inputs=[img_project_in, seed_in, width_in, height_in],
            outputs=[gallery_out, img_status],
        )

    with gr.Tab("5. Video"):
        with gr.Row():
            with gr.Column(scale=1):
                vid_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                vid_refresh_btn = gr.Button("Refresh danh sach project")
                use_subtitle_in = gr.Checkbox(label="Burn phu de", value=True)
                use_music_in = gr.Checkbox(label="Them nhac nen (neu co file .mp3 trong assets/music/)", value=False)
                assemble_btn = gr.Button("Ghep video hoan chinh", variant="primary")
                vid_status = gr.Markdown()
                gr.Markdown("---")
                thumb_scene_in = gr.Number(label="Sinh thumbnail tu scene so", value=1, precision=0)
                thumb_btn = gr.Button("Generate thumbnail")
                thumb_status = gr.Markdown()
            with gr.Column(scale=2):
                video_out = gr.Video(label="Video hoan chinh")
                thumb_out = gr.Image(label="Thumbnail")

        vid_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[vid_project_in])
        assemble_btn.click(
            on_assemble_video,
            inputs=[vid_project_in, use_subtitle_in, use_music_in],
            outputs=[video_out, vid_status],
        )
        thumb_btn.click(
            on_generate_thumbnail,
            inputs=[vid_project_in, thumb_scene_in],
            outputs=[thumb_out, thumb_status],
        )

    with gr.Tab("7. Dialogue Script"):
        gr.Markdown("Che do **Sticker Dialogue**: kich ban hoi thoai 2 nhan vat co dinh (Host/Guest).")
        with gr.Row():
            with gr.Column(scale=1):
                dlg_topic_in = gr.Textbox(label="Chu de video", placeholder="Vi du: Is a hot dog a sandwich?")
                dlg_duration_in = gr.Slider(label="Do dai mong muon (phut)", minimum=0.5, maximum=10, value=1.5, step=0.5)
                dlg_provider_in = gr.Radio(
                    label="Script provider", choices=["ollama", "anthropic"],
                    value=CONFIG["script"]["provider"] if CONFIG["script"]["provider"] in ("ollama", "anthropic") else "ollama",
                )
                dlg_generate_btn = gr.Button("Generate dialogue script", variant="primary")
                dlg_status_out = gr.Markdown()
            with gr.Column(scale=2):
                dlg_script_out = gr.Textbox(label="Dialogue script (JSON, co the sua tay)", lines=30)
                dlg_slug_state = gr.State("")
                dlg_save_btn = gr.Button("Save script vao project")
                dlg_save_status = gr.Markdown()

        dlg_generate_btn.click(
            on_generate_dialogue,
            inputs=[dlg_topic_in, dlg_duration_in, dlg_provider_in],
            outputs=[dlg_script_out, dlg_status_out, dlg_slug_state],
        )
        dlg_save_btn.click(on_save_script, inputs=[dlg_script_out, dlg_slug_state], outputs=[dlg_save_status])

    with gr.Tab("8. Dialogue Voice"):
        with gr.Row():
            with gr.Column(scale=1):
                dv_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                dv_refresh_btn = gr.Button("Refresh danh sach project")
                dv_generate_voice_btn = gr.Button("Generate voice tung cau + subtitle", variant="primary")
                dv_voice_status = gr.Markdown()
                gr.Markdown("---")
                dv_width_in = gr.Dropdown(label="Chieu rong nen", choices=[512, 768, 1024], value=768)
                dv_height_in = gr.Dropdown(label="Chieu cao nen", choices=[512, 768, 1024], value=768)
                dv_generate_bg_btn = gr.Button("Generate anh nen tung scene")
                dv_bg_status = gr.Markdown()
            with gr.Column(scale=2):
                dv_audio_out = gr.Audio(label="Audio hoi thoai day du", type="filepath")
                dv_gallery_out = gr.Gallery(label="Anh nen theo scene", columns=2, object_fit="contain")

        dv_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[dv_project_in])
        dv_generate_voice_btn.click(on_generate_dialogue_voice, inputs=[dv_project_in],
                                     outputs=[dv_audio_out, dv_voice_status])
        dv_generate_bg_btn.click(on_generate_dialogue_bg, inputs=[dv_project_in, dv_width_in, dv_height_in],
                                  outputs=[dv_gallery_out, dv_bg_status])

    with gr.Tab("9. Export CapCut"):
        gr.Markdown(
            "Xuat draft CapCut (`.json`) tu du lieu da co (voice, subtitle, anh nen, sticker nhan vat). "
            "Khong render video o day - mo file draft trong CapCut de tiep tuc chinh sua va export."
        )
        with gr.Row():
            with gr.Column(scale=1):
                ex_project_in = gr.Dropdown(label="Project", choices=list_projects(), allow_custom_value=True)
                ex_refresh_btn = gr.Button("Refresh danh sach project")
                ex_export_btn = gr.Button("Export draft CapCut", variant="primary")
            with gr.Column(scale=2):
                ex_status = gr.Textbox(label="Ket qua", lines=6)

        ex_refresh_btn.click(lambda: gr.update(choices=list_projects()), outputs=[ex_project_in])
        ex_export_btn.click(on_export_capcut, inputs=[ex_project_in], outputs=[ex_status])

    with gr.Tab("6. Characters"):
        gr.Markdown(
            "Nhan vat co dinh cho che do **Sticker Dialogue** (dinh nghia trong `config.yaml` -> `characters`). "
            "Ve bang code (khong AI) de dam bao nhat quan tuyet doi giua cac bieu cam."
        )
        char_status = gr.Markdown()
        generate_char_btn = gr.Button("Generate / Regenerate characters", variant="primary")
        char_gallery = gr.Gallery(label="Nhan vat x bieu cam", columns=5, object_fit="contain")
        generate_char_btn.click(on_generate_characters, outputs=[char_gallery, char_status])

    with gr.Tab("Projects"):
        refresh_btn = gr.Button("Refresh danh sach project")
        projects_out = gr.Textbox(label="Cac project da tao", lines=10)
        refresh_btn.click(lambda: "\n".join(list_projects()), outputs=[projects_out])

if __name__ == "__main__":
    demo.launch()
