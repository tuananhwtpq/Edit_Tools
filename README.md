# Edit_Tools

Personal tool to generate faceless AI videos for YouTube: script generation, TTS voiceover,
AI image generation, auto subtitles, and video assembly — all driven from one local Gradio UI.

## Pipeline

Topic -> Script (LLM) -> Voiceover (TTS) -> Subtitles (Whisper) -> Images (FLUX/ComfyUI or API) -> Video assembly (ffmpeg/moviepy)

## Setup

### macOS (Apple Silicon)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-mac.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY / FAL_KEY / HF_TOKEN if needed
python app.py
```

> macOS 26.x note: if you hit a `pyexpat` / `libexpat` symbol error with Homebrew's
> `python@3.12`, run `brew install expat` — `.venv/bin/activate` already exports
> `DYLD_LIBRARY_PATH` to point at it.

Set `image.backend: mlx` in `config.yaml` (default).

### Windows / Linux (NVIDIA GPU)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-cuda.txt
copy .env.example .env
python app.py
```

Set `image.backend: cuda` in `config.yaml`. Also needed:
- `ffmpeg` with libass/subtitle support (most prebuilt Windows binaries, e.g. from
  https://www.gyan.dev/ffmpeg/builds/, already include this — unlike the plain
  Homebrew `ffmpeg` formula on Mac) on PATH
- `espeak-ng` Windows installer (for Kokoro TTS phonemization):
  https://github.com/espeak-ng/espeak-ng/releases
- Ollama for Windows if using local script generation: https://ollama.com/download

The CUDA image backend ([modules/image_backends/cuda_backend.py](modules/image_backends/cuda_backend.py))
uses `diffusers` + 4-bit bitsandbytes quantization + CPU offload to fit FLUX.1-schnell
on consumer GPUs (~8GB+ VRAM). **Not yet verified on real NVIDIA hardware** — if you
hit an out-of-memory error, try `enable_sequential_cpu_offload()` instead of
`enable_model_cpu_offload()` in that file (slower, less VRAM), or lower
`image.width`/`image.height` in `config.yaml`.

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

### Image generation (buoi 5-6)

Uses [mflux](https://github.com/filipstrand/mflux) (MLX-native FLUX) to run
**FLUX.1-schnell** locally on Apple Silicon, 4-bit quantized. No API key needed for
inference, but the model repo on Hugging Face is gated (free, Apache-2.0, just
requires accepting terms):

1. Create a free account at https://huggingface.co/join
2. Visit https://huggingface.co/black-forest-labs/FLUX.1-schnell and click
   "Agree and access repository"
3. Create a Read token at https://huggingface.co/settings/tokens and set
   `HF_TOKEN=hf_...` in `.env`

First run downloads ~13GB of weights (needs ~45GB free disk space temporarily).
On an M4 Mac mini (16GB RAM, no discrete GPU): ~1 min/image at 512x512,
~4-5 min/image at 1024x1024. Style consistency across scenes is kept simple —
a shared `style_suffix` (see `config.yaml`) is appended to every prompt; no LoRA
character training (would need a training pipeline + reference images, out of
scope for now).

### Video assembly + thumbnail (buoi 7-8)

Pure `ffmpeg` subprocess pipeline (no moviepy, to avoid version-API drift):
Ken Burns zoom per scene image (`zoompan` filter) -> concat -> mux narration audio
-> burn subtitles (`subtitles` filter). Requires **`ffmpeg-full`** (not the plain
`ffmpeg` formula) because Homebrew's default `ffmpeg` ships without `libass`/
`libfreetype`, so it can't burn subtitles or draw text:

```bash
brew install ffmpeg-full
```

`modules/video_assembly.py` looks for `ffmpeg-full`'s binary at
`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` first and falls back to `ffmpeg` on PATH.

Optional background music: drop an `.mp3` into `assets/music/` and enable
"Them nhac nen" in the Video tab.

## Sticker Dialogue mode (buoi 9+)

A second, parallel mode alongside the narrator/ffmpeg pipeline above: 2 fixed
recurring characters (Host/Guest, configured in `config.yaml` -> `characters`)
have a back-and-forth dialogue instead of one narrator. Final assembly is meant
to go through CapCut (via `pycapcut`, added in buoi 12) instead of ffmpeg, to
keep the finishing/export step token-free.

- `modules/character_gen.py`: draws each character as a simple black-outline
  stick figure (round head, oval torso, jointed limbs) with 5 expressions
  (`neutral`, `talking`, `happy`, `surprised`, `angry`) using pure PIL — no AI,
  so every expression is pixel-consistent. A small colored necktie
  distinguishes Host vs Guest. Generate via the **6. Characters** tab.
- `modules/dialogue_script_gen.py`: generates a 2-character dialogue script
  (`mode: "dialogue"` in the JSON, `lines[]` per scene with `speaker` +
  `expression`), normalizing any expression/speaker the LLM gets wrong back to
  a valid one. Generate via the **7. Dialogue Script** tab.

- `modules/dialogue_tts_gen.py`: generates one Kokoro wav per line (voice picked
  per-speaker from `config.yaml` -> `characters`), concatenates to `full.wav`,
  and returns exact per-line + per-scene timing (no Whisper — the text is
  already known). Generate via **8. Dialogue Voice**.
- `modules/subtitle_gen.py` -> `generate_dialogue_srt()`: builds `subtitle.srt`
  directly from that timing.
- `modules/image_gen.py` -> `generate_dialogue_backgrounds()` / the "Generate anh
  nen" button in **8. Dialogue Voice**: one background image per scene (flat
  illustration style, no characters — characters are a separate sticker layer).
- `modules/capcut_export.py` (`pip install pycapcut`): assembles a CapCut draft
  `.json` with 5 tracks — Background, one video track per character (sticker
  swaps per line: speaking character shows their line's expression, the other
  shows `neutral`), Dialogue audio, Subtitle text (via `import_srt`). Generate
  via **9. Export CapCut** — writes `capcut_draft.json` into the project folder.
  **Not yet placed into an actual CapCut drafts folder** (CapCut isn't installed
  on this Mac to test against) — for now, manually import/open the generated
  `.json` in CapCut. Once we know which machine/CapCut install you'll actually
  use, this can auto-place the draft via `pycapcut`'s `DraftFolder` so it shows
  up directly in the CapCut project list.

## Project structure

- `app.py` - Gradio UI, orchestrates the pipeline
- `modules/` - one file per pipeline stage (script_gen, tts_gen, subtitle_gen, image_gen, video_assembly)
- `config.yaml` - provider/model choices per stage
- `projects/<slug>/` - per-video output (script.json, audio/, images/, subtitles, final mp4)
