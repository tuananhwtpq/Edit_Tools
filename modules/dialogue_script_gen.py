import json
import os
import re

import requests

from modules.config import CONFIG
from modules.character_gen import EXPRESSIONS

SYSTEM_PROMPT_TEMPLATE = """Ban la nguoi viet kich ban video hoi thoai 2 nhan vat dang "sticker/chibi"
cho YouTube Shorts/TikTok. Video co 2 nhan vat co dinh noi chuyen qua lai, giong podcast/debate
vui, ngan gon, nhieu nang luong, dung nguon phong cach "hook nhanh, giu nguoi xem lai".

Nhan vat:
{characters_desc}

Bieu cam duoc phep dung cho tung cau thoai (chon dung 1 trong danh sach nay): {expressions}

Luon tra ve DUY NHAT mot JSON object, khong giai thich gi them, dung format:
{{
  "mode": "dialogue",
  "title": "tieu de video bang tieng Anh, hap dan, chuan SEO YouTube/Shorts",
  "characters": [{character_names}],
  "scenes": [
    {{
      "scene_id": 1,
      "background_prompt": "mo ta bang tieng Anh cho AI sinh anh nen scene nay (khong co nhan vat trong anh, phong cach flat illustration don gian, khong chu)",
      "lines": [
        {{"line_id": 1, "speaker": "{first_char}", "text": "cau thoai tieng Anh, ngan gon tu nhien", "expression": "neutral"}},
        {{"line_id": 2, "speaker": "{second_char}", "text": "...", "expression": "happy"}}
      ]
    }}
  ],
  "outro_cta": "cau chot cuoi video, keu goi subscribe/comment, dung giong 1 trong 2 nhan vat"
}}

Yeu cau:
- Moi cau thoai (line) ngan, 1-2 cau, giong van noi tu nhien nhu doi thoai that, KHONG doc van ban dai.
- line_id danh so lien tuc tu 1 tang dan xuyen suot toan bo video (khong reset lai o moi scene).
- Xen ke hop ly giua 2 nhan vat, tranh 1 nguoi noi qua nhieu cau lien tiep.
- expression phai khop voi cam xuc/noi dung cau noi do.
- background_prompt doi theo tung scene de tao su thay doi hinh anh, nhung KHONG mo ta nhan vat trong do.
- Tong so scene va line phu hop do dai video yeu cau."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Khong tim thay JSON trong output:\n{text[:500]}")
    return json.loads(match.group(0))


def _build_system_prompt(characters: list[dict]) -> str:
    characters_desc = "\n".join(
        f"- {c['name']}: {c.get('personality', 'no specific personality')}" for c in characters
    )
    character_names = ", ".join(f'"{c["name"]}"' for c in characters)
    return SYSTEM_PROMPT_TEMPLATE.format(
        characters_desc=characters_desc,
        expressions=", ".join(EXPRESSIONS),
        character_names=character_names,
        first_char=characters[0]["name"],
        second_char=characters[1]["name"] if len(characters) > 1 else characters[0]["name"],
    )


def _build_user_prompt(topic: str, target_duration_min: float) -> str:
    target_sec = int(target_duration_min * 60)
    return (
        f"Chu de video: {topic}\n"
        f"Do dai mong muon: khoang {target_duration_min} phut (~{target_sec} giay thoai).\n"
        f"Hay viet kich ban hoi thoai day du theo dung JSON schema da mo ta."
    )


def _generate_anthropic(system_prompt: str, user_prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=CONFIG["script"]["model"],
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _extract_json(message.content[0].text)


def _generate_ollama(system_prompt: str, user_prompt: str) -> dict:
    host = CONFIG["script"]["ollama_host"]
    model = CONFIG["script"]["ollama_model"]
    resp = requests.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
        },
        timeout=300,
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"]
    return _extract_json(content)


EXPRESSION_FALLBACK = {
    "curious": "surprised", "skeptical": "neutral", "smartass": "happy",
    "enthusiastic": "happy", "excited": "happy", "confused": "surprised",
    "sad": "angry", "annoyed": "angry", "shocked": "surprised", "worried": "neutral",
}


def _normalize_script(script: dict, characters: list[dict]) -> dict:
    """LLM (dac biet model local nho) khong luon tuan thu dung danh sach expression/speaker
    cho phep. Chuan hoa lai de cac buoi sau (voice, sticker swap) khong bi vo vi thieu asset.
    """
    valid_names = {c["name"] for c in characters}
    default_speaker = characters[0]["name"]

    for scene in script.get("scenes", []):
        for line in scene.get("lines", []):
            if line.get("speaker") not in valid_names:
                line["speaker"] = default_speaker
            expr = line.get("expression", "neutral")
            if expr not in EXPRESSIONS:
                line["expression"] = EXPRESSION_FALLBACK.get(expr, "neutral")
    return script


def generate_dialogue_script(topic: str, target_duration_min: float = 2.0,
                              provider: str | None = None, characters: list[dict] | None = None) -> dict:
    characters = characters or CONFIG["characters"]
    provider = provider or CONFIG["script"]["provider"]
    system_prompt = _build_system_prompt(characters)
    user_prompt = _build_user_prompt(topic, target_duration_min)

    if provider == "anthropic":
        script = _generate_anthropic(system_prompt, user_prompt)
    elif provider == "ollama":
        script = _generate_ollama(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown script provider: {provider}")

    return _normalize_script(script, characters)
