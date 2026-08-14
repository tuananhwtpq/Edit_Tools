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

### Script generation (buoi 2)

- Local/free: `brew install ollama && ollama pull qwen2.5:7b` (default provider in `config.yaml`)
- Higher quality: set `ANTHROPIC_API_KEY` in `.env` and switch `script.provider: anthropic`

### Voice generation (buoi 3)

Uses [Kokoro-82M](https://github.com/thewh1teagle/kokoro-onnx) locally (free, no API key).

```bash
brew install espeak-ng
mkdir -p models
curl -L -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Default voice: `af_heart`.

### Subtitle generation (buoi 4)

Uses `faster-whisper` (model `base.en` by default, downloads automatically from
Hugging Face on first run) to transcribe `audio/full.wav` with word-level timestamps
and produce `subtitle.srt`.

## Project structure

- `app.py` - Gradio UI, orchestrates the pipeline
- `modules/` - one file per pipeline stage (script_gen, tts_gen, subtitle_gen, image_gen, video_assembly)
- `config.yaml` - provider/model choices per stage
- `projects/<slug>/` - per-video output (script.json, audio/, images/, subtitles, final mp4)
