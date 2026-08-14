import json
import os
import re

import requests

from modules.config import CONFIG

SYSTEM_PROMPT = """Ban la mot nguoi viet kich ban video faceless YouTube chuyen nghiep.
Nhiem vu: viet kich ban tieng Anh (narration bang tieng Anh, tu nhien, hap dan, giu nguoi xem o lai)
va chia thanh cac scene ngan de minh hoa bang anh AI.

Luon tra ve DUY NHAT mot JSON object, khong giai thich gi them, dung format:
{
  "title": "tieu de video bang tieng Anh, hap dan, chuan SEO YouTube",
  "hook": "1-2 cau mo dau gay to mo trong 5 giay dau",
  "scenes": [
    {
      "scene_id": 1,
      "narration": "doan van ban se duoc doc thanh giong noi (tieng Anh)",
      "image_prompt": "mo ta chi tiet bang tieng Anh cho AI sinh anh minh hoa scene nay, phong cach cinematic",
      "duration_estimate_sec": 12
    }
  ],
  "outro_cta": "cau keu goi hanh dong o cuoi video (subscribe, comment...)"
}

Yeu cau:
- Moi scene narration dai khoang 2-4 cau, du de doc trong 8-15 giay.
- image_prompt phai cu the ve boi canh, anh sang, goc may, phong cach, KHONG chua text/chu viet trong anh.
- Tong so scene phu hop voi do dai video yeu cau.
- Giu van phong nhat quan xuyen suot video, phu hop niche va tone duoc yeu cau."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Khong tim thay JSON trong output:\n{text[:500]}")
    return json.loads(match.group(0))


def _build_user_prompt(topic: str, style: str, target_duration_min: float) -> str:
    target_sec = int(target_duration_min * 60)
    return (
        f"Chu de video: {topic}\n"
        f"Tone/style: {style}\n"
        f"Do dai mong muon: khoang {target_duration_min} phut (~{target_sec} giay narration).\n"
        f"Hay viet kich ban day du theo dung JSON schema da mo ta."
    )


def _generate_anthropic(topic: str, style: str, target_duration_min: float) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=CONFIG["script"]["model"],
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(topic, style, target_duration_min)}],
    )
    return _extract_json(message.content[0].text)


def _generate_ollama(topic: str, style: str, target_duration_min: float) -> dict:
    host = CONFIG["script"]["ollama_host"]
    model = CONFIG["script"]["ollama_model"]
    resp = requests.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(topic, style, target_duration_min)},
            ],
            "stream": False,
            "format": "json",
        },
        timeout=300,
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"]
    return _extract_json(content)


def generate_script(topic: str, style: str = "engaging, conversational", target_duration_min: float = 3.0,
                     provider: str | None = None) -> dict:
    provider = provider or CONFIG["script"]["provider"]
    if provider == "anthropic":
        return _generate_anthropic(topic, style, target_duration_min)
    if provider == "ollama":
        return _generate_ollama(topic, style, target_duration_min)
    raise ValueError(f"Unknown script provider: {provider}")
