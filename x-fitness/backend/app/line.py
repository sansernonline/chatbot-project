"""LINE Official Account channel: the same bot as the website, through the LINE Messaging API.

LINE → POST /api/line/webhook (signature checked) → 200 at once → in the background: answer → reply API.
Every LINE chat is a normal conversation (id derived from the LINE user id), so it shows in the admin inbox;
"คุยกับพนักงาน" hands it to staff, and staff replies from the inbox are pushed back to LINE (push()).
"""
import base64
import hashlib
import hmac
import json
import logging
import re

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import business, chat, config, db, llm

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/line", tags=["LINE"])
API = "https://api.line.me/v2/bot"
VERIFY = re.compile(r"FN\s*-?\s*(\d{5})\D+(\d{4})(?!\d)", re.I)       # "FN-10003 5531"
STAFF_BUSY = ("waiting", "agent")                                     # staff has the chat: bot stays quiet
ERROR_REPLY = {"answer": f"ขออภัยค่ะ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง หรือพิมพ์ \"{chat.HANDOFF}\"", "actions": [chat.HANDOFF]}


@router.post("/webhook")
async def webhook(request: Request, tasks: BackgroundTasks, x_line_signature: str = Header(default="")):
    if not config.LINE_CHANNEL_SECRET:
        raise HTTPException(503, "ยังไม่ได้ตั้งค่า LINE_CHANNEL_SECRET")
    body = await request.body()
    expected = base64.b64encode(hmac.new(config.LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected, x_line_signature):          # no valid signature = not from LINE
        raise HTTPException(401, "invalid signature")
    for event in json.loads(body).get("events", []):
        tasks.add_task(handle, event)
    return {}


async def handle(event: dict) -> None:
    """One LINE event: log it, answer it, reply. Only 1:1 messages are handled (no groups)."""
    if event.get("type") != "message" or event.get("source", {}).get("type") != "user":
        return
    user_id, msg = event["source"]["userId"], event["message"]
    cid = ticket(user_id)
    db.link_line_user(cid, user_id)
    conv = db.get(cid)
    if not conv["name"]:
        db.patch(cid, {"name": "ลูกค้า LINE"}, touch=False)

    db.add_message(cid, "user", msg["text"][:500] if msg["type"] == "text" else "[ส่งรูปภาพ]" if msg["type"] == "image" else f"[{msg['type']}]")
    if conv["status"] in STAFF_BUSY:
        return
    try:
        if msg["type"] == "text":
            result = await on_text(cid, user_id, msg["text"].strip()[:500], conv)
        elif msg["type"] == "image":
            loading(user_id)
            vision = await run_in_threadpool(chat.read_image, *download(msg["id"]))
            result = await chat.answer("", cid, conv["member_id"], vision)
        else:
            result = {"answer": "ตอนนี้เอ็กซ์อ่านได้เฉพาะข้อความและรูปภาพค่ะ", "actions": []}
    except ValueError as e:                                            # image too big / wrong type
        result = {"answer": str(e), "actions": []}
    except (llm.LLMError, httpx.HTTPError) as e:
        log.warning("LINE answer failed: %s", e)
        result = ERROR_REPLY
    db.add_message(cid, "bot", result["answer"])
    send("message/reply", {"replyToken": event["replyToken"], "messages": [message(result["answer"], result.get("actions", []))]})


async def on_text(cid: str, user_id: str, text: str, conv: dict) -> dict:
    if chat.HANDOFF in text:
        db.handoff(cid, "ขอคุยกับพนักงาน (LINE)", conv["name"], conv["member_id"])
        return {"answer": "ส่งเรื่องให้พนักงานแล้วค่ะ พนักงานตอบทุกวัน 09:00–20:00 น. ภายในประมาณ 15 นาที "
                          "ระหว่างนี้พิมพ์รายละเอียดเพิ่มได้เลยค่ะ", "actions": []}
    if m := VERIFY.search(text):                                       # LINE has no verify form: member types it
        member = business.verify(f"FN-{m.group(1)}", m.group(2))
        if not member:
            return {"answer": "รหัสสมาชิกหรือเบอร์โทร 4 ตัวท้ายไม่ตรงกันค่ะ ลองพิมพ์ใหม่ เช่น FN-10003 5531", "actions": []}
        db.patch(cid, {"member_id": member["member_id"]})
        return {"answer": f"ยืนยันตัวตนแล้วค่ะ คุณ{member['first_name']} ถามเรื่องแต้ม ยอดค้างชำระ หรือส่งสลิปได้เลยค่ะ",
                "actions": ["แต้มของฉัน", "ยอดค้างชำระ"]}
    loading(user_id)
    return await chat.answer(text, cid, conv["member_id"])


def push(cid: str, text: str) -> None:
    """Send a staff reply from the admin inbox to the customer's LINE (no-op for website chats)."""
    if user_id := db.line_user(cid):
        send("message/push", {"to": user_id, "messages": [message(text, [])]})


def ticket(user_id: str) -> str:
    """LINE user id → conversation id in the website's ticket format (letter + digit ×5), always the same per user."""
    h = hashlib.sha256(user_id.encode()).digest()
    return "".join(chr(65 + h[i] % 26) + str(h[i + 1] % 10) for i in range(0, 10, 2))


def message(text: str, actions: list[str]) -> dict:
    msg = {"type": "text", "text": text[:5000]}
    if actions:
        msg["quickReply"] = {"items": [{"type": "action", "action": {"type": "message", "label": a[:20], "text": a}} for a in actions]}
    return msg


def download(message_id: str) -> tuple[bytes, str]:
    r = httpx.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=_auth(), timeout=20)
    r.raise_for_status()
    mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
    if mime not in chat.IMAGE_TYPES or len(r.content) > chat.MAX_IMAGE_BYTES:
        raise ValueError("รองรับเฉพาะภาพ JPG หรือ PNG ขนาดไม่เกิน 5 MB ค่ะ")
    return r.content, mime


def loading(user_id: str) -> None:
    """Typing indicator in LINE while the bot works (the 'processing' state on this channel)."""
    send("chat/loading/start", {"chatId": user_id, "loadingSeconds": 20})


def send(path: str, payload: dict) -> None:
    """POST to the Messaging API; failures are logged, never raised (the customer message is already saved)."""
    try:
        r = httpx.post(f"{API}/{path}", json=payload, headers=_auth(), timeout=10)
        if r.status_code >= 300:
            log.warning("LINE %s → HTTP %s %s", path, r.status_code, r.text[:200])
    except httpx.HTTPError as e:
        log.warning("LINE %s failed: %s", path, e)


def _auth() -> dict:
    return {"Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"}
