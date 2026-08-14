# Edit_Tools

Personal tool to generate faceless AI videos for YouTube: script generation, TTS voiceover,
AI image generation, auto subtitles, and video assembly — all driven from one local Gradio UI.

## Pipeline

Topic -> Script (LLM) -> Voiceover (TTS) -> Subtitles (Whisper) -> Images (FLUX/ComfyUI or API) -> Video assembly (ffmpeg/moviepy)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY / FAL_KEY if needed
python app.py
```

> macOS 26.x note: if you hit a `pyexpat` / `libexpat` symbol error with Homebrew's
> `python@3.12`, run `brew install expat` — `.venv/bin/activate` already exports
> `DYLD_LIBRARY_PATH` to point at it.

## Project structure

- `app.py` - Gradio UI, orchestrates the pipeline
- `modules/` - one file per pipeline stage (script_gen, tts_gen, subtitle_gen, image_gen, video_assembly)
- `config.yaml` - provider/model choices per stage
- `projects/<slug>/` - per-video output (script.json, audio/, images/, subtitles, final mp4)
