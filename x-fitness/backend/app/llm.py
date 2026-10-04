"""Typhoon chat/completions client (OpenAI-compatible) — plain httpx, no SDK."""
import base64

import httpx

from . import config


class LLMError(Exception):
    """Typhoon unreachable, timed out, or answered with an error."""


def _post(payload: dict) -> str:
    if not config.TYPHOON_API_KEY:
        raise LLMError("ยังไม่ได้ตั้งค่า TYPHOON_API_KEY ใน backend/.env")
    try:
        r = httpx.post(f"{config.TYPHOON_BASE_URL}/chat/completions", json=payload, timeout=config.LLM_TIMEOUT_S,
                       headers={"Authorization": f"Bearer {config.TYPHOON_API_KEY}"})
    except httpx.TimeoutException as e:
        raise LLMError("Typhoon ตอบช้าเกินกำหนด") from e
    except httpx.HTTPError as e:
        raise LLMError(f"เชื่อมต่อ Typhoon ไม่ได้: {e}") from e
    if r.status_code != 200:
        raise LLMError(f"Typhoon ตอบกลับ HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"] or ""


def chat(messages: list[dict], max_tokens: int = 700, temperature: float = 0.1, json_mode: bool = False) -> str:
    payload = {"model": config.CHAT_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return _post(payload)


def vision(image: bytes, mime: str, prompt: str) -> str:
    """Ask the vision model about an image (sent inline as a base64 data URL); returns its text answer."""
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    return _post({"model": config.VISION_MODEL, "max_tokens": 2000, "temperature": 0.1, "messages": [
        {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": url}}]}]})
