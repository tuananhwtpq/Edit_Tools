from faster_whisper import WhisperModel

from modules.config import CONFIG

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(CONFIG["subtitle"]["model_size"], device="cpu", compute_type="int8")
    return _model


def _format_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _group_words(words: list[dict], max_words_per_line: int = 7) -> list[dict]:
    lines = []
    current = []
    for w in words:
        current.append(w)
        ends_sentence = w["word"].strip().endswith((".", "?", "!"))
        if len(current) >= max_words_per_line or ends_sentence:
            lines.append(current)
            current = []
    if current:
        lines.append(current)

    entries = []
    for i, line in enumerate(lines, start=1):
        entries.append({
            "index": i,
            "start": line[0]["start"],
            "end": line[-1]["end"],
            "text": "".join(w["word"] for w in line).strip(),
        })
    return entries


def generate_srt(audio_path: str, out_srt_path, max_words_per_line: int = 7) -> list[dict]:
    model = _get_model()
    segments, _info = model.transcribe(str(audio_path), word_timestamps=True, language="en")

    words = []
    for seg in segments:
        for w in seg.words:
            words.append({"word": w.word, "start": w.start, "end": w.end})

    entries = _group_words(words, max_words_per_line=max_words_per_line)

    with open(out_srt_path, "w") as f:
        for e in entries:
            f.write(
                f"{e['index']}\n"
                f"{_format_timestamp(e['start'])} --> {_format_timestamp(e['end'])}\n"
                f"{e['text']}\n\n"
            )

    return entries
