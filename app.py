import json

import gradio as gr

from modules.config import CONFIG, PROJECTS_DIR
from modules.project import slugify, save_script, load_script, save_audio_meta, project_dir, list_projects
from modules.script_gen import generate_script
from modules.tts_gen import generate_scene_audio
from modules.subtitle_gen import generate_srt
from modules.image_gen import generate_image

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

    with gr.Tab("Projects"):
        refresh_btn = gr.Button("Refresh danh sach project")
        projects_out = gr.Textbox(label="Cac project da tao", lines=10)
        refresh_btn.click(lambda: "\n".join(list_projects()), outputs=[projects_out])

if __name__ == "__main__":
    demo.launch()
