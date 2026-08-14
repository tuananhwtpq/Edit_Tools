import gradio as gr

from modules.config import CONFIG, PROJECTS_DIR

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

with gr.Blocks(title="Faceless AI Video Studio") as demo:
    gr.Markdown("# Faceless AI Video Studio")
    gr.Markdown(
        f"Moi truong da san sang. Script provider: **{CONFIG['script']['provider']}**, "
        f"TTS: **{CONFIG['tts']['provider']}**, Image: **{CONFIG['image']['provider']}**."
    )

if __name__ == "__main__":
    demo.launch()
