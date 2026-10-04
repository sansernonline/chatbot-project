"""The bot: answer() and read_image() are shared by the website (/api/chat, /api/vision) and LINE (line.py).

answer: guard in → LightRAG → Typhoon → guard out.  read_image: typhoon-ocr reads the text → Typhoon turns it into JSON.
Request/response shapes of the two endpoints match the adapter in frontend/index.html (apiAnswer).
"""
import json
import re
from datetime import date

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from . import business, config, db, guard, llm, rag

router = APIRouter(prefix="/api", tags=["bot"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/png", "image/jpeg"}
HISTORY_TURNS = 8
HANDOFF = "คุยกับพนักงาน"
THAI_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


class ChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(default="", max_length=500)
    member_id: str | None = Field(default=None, max_length=20)  # demo: trusted from the site's verify step
    vision: dict | None = None


@router.post("/chat")
async def chat(body: ChatIn):
    if not body.message.strip() and not body.vision:
        raise HTTPException(422, "ข้อความว่าง")
    try:
        return await answer(body.message, body.session_id, body.member_id, body.vision)
    except llm.LLMError as e:
        raise HTTPException(502, str(e)) from e


@router.post("/vision")
async def vision(image: UploadFile = File(...)):
    if image.content_type not in IMAGE_TYPES:
        raise HTTPException(415, "รองรับเฉพาะภาพ JPG หรือ PNG")
    data = await image.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "ภาพใหญ่เกิน 5 MB")
    try:
        return await run_in_threadpool(read_image, data, image.content_type)
    except llm.LLMError as e:
        raise HTTPException(502, str(e)) from e


async def answer(text: str, session_id: str, member_id: str | None = None, vision: dict | None = None) -> dict:
    """{answer, sources, rules, actions[, slip_check]}. Raises llm.LLMError when RAG or the LLM fails."""
    text, vision = text.strip(), vision or {}
    if blocked := guard.check_input(text):
        return blocked
    try:
        context, sources = await rag.context(f"{text} {vision.get('type', '')} {vision.get('title', '')}".strip())
    except Exception as e:                          # LightRAG failed (embedding down, index missing…)
        raise llm.LLMError(f"ค้นคลังความรู้ไม่สำเร็จ: {e}") from e
    found = bool(sources)

    user, slip = text or "ช่วยดูภาพนี้ให้หน่อย", None
    if vision:
        user += f"\n\n[ข้อมูลที่อ่านได้จากภาพที่ลูกค้าส่ง]\n{json.dumps({k: v for k, v in vision.items() if k != 'raw_text'}, ensure_ascii=False)}"
        if vision.get("type") == "slip":
            slip = business.check_slip(vision, member_id)
            user += f"\n\n[ผลตรวจสลิปจากระบบ — แจ้งตามนี้]\n{json.dumps(slip, ensure_ascii=False)}"
            sources = list(dict.fromkeys(["KB-06", *sources]))

    system = prompt("system", today=today_th(), member=business.member_context(member_id), context=context)
    messages = [{"role": "system", "content": system}, *history(session_id, text), {"role": "user", "content": user}]
    reply, rules = guard.check_output((await run_in_threadpool(llm.chat, messages)).strip(), known=f"{system}\n{user}")

    needs_staff = (not vision and not found) or (slip is not None and not slip["ok"]) or reply == guard.SAFE_REPLY
    return {"answer": reply, "sources": sources, "rules": rules, "actions": [HANDOFF] if needs_staff else [],
            **({"slip_check": slip} if slip else {})}


def read_image(data: bytes, mime: str) -> dict:
    """typhoon-ocr reads the text (it fails when asked for JSON directly), then Typhoon structures it.
    OCR sometimes answers with an upstream error JSON instead of text: retry once, then raise."""
    for _ in range(2):
        seen = llm.vision(data, mime, prompt("ocr")).strip()
        if not seen.startswith('{"error"'):
            break
    else:
        raise llm.LLMError("อ่านภาพไม่สำเร็จ (โมเดลอ่านภาพขัดข้อง) ลองส่งใหม่อีกครั้ง")
    extracted = parse_json(llm.chat([{"role": "user", "content": prompt("vision", ocr_text=seen[:4000])}],
                                    max_tokens=600, temperature=0, json_mode=True))
    if not isinstance(extracted, dict) or "type" not in extracted:
        extracted = {"type": "other", "summary": seen[:200]}
    return {**extracted, "raw_text": seen[:1500]}


def prompt(name: str, **values) -> str:
    text = (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def today_th(d: date | None = None) -> str:
    """e.g. 'วันอาทิตย์ที่ 2026-10-04 (พ.ศ. 2569)' — weekday for the class schedule, both calendars for promo dates."""
    d = d or date.today()
    return f"วัน{THAI_DAYS[d.weekday()]}ที่ {d.isoformat()} (พ.ศ. {d.year + 543})"


def history(session_id: str, current: str) -> list[dict]:
    """Earlier turns of this chat from the conversation store (website and LINE log every message there)."""
    conv = db.get(session_id) if re.fullmatch(r"([A-Z][0-9]){5}", session_id) else None
    msgs = [m for m in (conv or {}).get("msgs", []) if m["from"] in ("user", "bot", "agent")]
    if msgs and msgs[-1]["from"] == "user" and msgs[-1]["text"].endswith(current):
        msgs = msgs[:-1]                            # the current message is logged before answer() runs
    return [{"role": "user" if m["from"] == "user" else "assistant", "content": m["text"]} for m in msgs[-HISTORY_TURNS:]]


def parse_json(text: str):
    """The first {...} in the text (models sometimes wrap JSON in ``` fences or a sentence)."""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
