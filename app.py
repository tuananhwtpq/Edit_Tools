import json

import gradio as gr

from modules.config import CONFIG, PROJECTS_DIR
from modules.project import slugify, save_script, list_projects
from modules.script_gen import generate_script

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


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

    with gr.Tab("Projects"):
        refresh_btn = gr.Button("Refresh danh sach project")
        projects_out = gr.Textbox(label="Cac project da tao", lines=10)
        refresh_btn.click(lambda: "\n".join(list_projects()), outputs=[projects_out])

if __name__ == "__main__":
    demo.launch()
