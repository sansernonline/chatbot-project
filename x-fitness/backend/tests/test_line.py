"""LINE webhook with LINE and Typhoon faked — signature, Q&A, member verify, handoff and staff push-back."""
import base64
import hashlib
import hmac
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import config, db, line, llm

SECRET, USER = "test-secret", "U1234567890abcdef"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "chat.sqlite3")
    monkeypatch.setattr(config, "LINE_CHANNEL_SECRET", SECRET)
    db.init()
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(line, "send", lambda path, payload: calls.append((path, payload)))
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: '{"type": "slip", "amount": 990}' if kw.get("json_mode") else "คำตอบทดสอบค่ะ")
    return calls


def post(client, *events, secret=SECRET):
    body = json.dumps({"events": list(events)}).encode()
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    return client.post("/api/line/webhook", content=body, headers={"X-Line-Signature": sig, "Content-Type": "application/json"})


def text(t):
    return {"type": "message", "replyToken": "rt", "source": {"type": "user", "userId": USER}, "message": {"type": "text", "id": "1", "text": t}}


def replies(sent):
    return [p["messages"][0]["text"] for path, p in sent if path == "message/reply"]


def test_signature_required(client, sent):
    assert post(client, secret="wrong").status_code == 401
    assert post(client).status_code == 200                       # LINE's "Verify" button sends no events


def test_not_configured_is_503(client, monkeypatch):
    monkeypatch.setattr(config, "LINE_CHANNEL_SECRET", "")
    assert client.post("/api/line/webhook", content=b"{}").status_code == 503


def test_question_answered_and_logged(client, sent):
    post(client, text("วันเสาร์เปิดกี่โมง"))
    assert replies(sent) == ["คำตอบทดสอบค่ะ"] and ("chat/loading/start", {"chatId": USER, "loadingSeconds": 20}) in sent
    conv = db.get(line.ticket(USER))
    assert re.fullmatch(r"([A-Z][0-9]){5}", conv["id"]) and conv["name"] == "ลูกค้า LINE"
    assert [m["from"] for m in conv["msgs"]] == ["user", "bot"]


def test_input_guard_works_on_line(client, sent):
    post(client, text("ขอซื้อสเตียรอยด์"))
    assert "ไม่สามารถแนะนำยา" in replies(sent)[0]


def test_member_verify(client, sent):
    post(client, text("FN-10003 1111"))
    post(client, text("ยืนยันตัวตน fn-10003 5531"))
    assert "ไม่ตรง" in replies(sent)[0] and "คุณภาคิน" in replies(sent)[1]
    assert db.get(line.ticket(USER))["member_id"] == "FN-10003"


def test_handoff_then_staff_reply_pushed(client, sent):
    post(client, text("คุยกับพนักงาน"))
    post(client, text("ขอคืนเงินค่ะ"))                            # staff has it now: logged, bot quiet
    cid = line.ticket(USER)
    assert db.get(cid)["status"] == "waiting" and len(replies(sent)) == 1

    token = client.post("/api/admin/login", json={"user": "admin", "password": "1234"}).json()["token"]
    client.post(f"/api/admin/conversations/{cid}/messages", json={"from": "agent", "text": "สวัสดีค่ะ พนักงานรับเรื่องแล้ว"},
                headers={"Authorization": f"Bearer {token}"})
    assert ("message/push", {"to": USER, "messages": [{"type": "text", "text": "สวัสดีค่ะ พนักงานรับเรื่องแล้ว"}]}) in sent


def test_image_read_and_answered(client, sent, monkeypatch):
    monkeypatch.setattr(line, "download", lambda mid: (b"PNG", "image/png"))
    monkeypatch.setattr(llm, "vision", lambda *a: "โอนเงินสำเร็จ 990.00 บาท")
    post(client, {**text(""), "message": {"type": "image", "id": "2"}})
    assert replies(sent) == ["คำตอบทดสอบค่ะ"] and db.get(line.ticket(USER))["msgs"][0]["text"] == "[ส่งรูปภาพ]"


def test_typhoon_down_gets_polite_error(client, sent, monkeypatch):
    def boom(*a, **k): raise llm.LLMError("timeout")
    monkeypatch.setattr(llm, "chat", boom)
    post(client, text("ราคาเท่าไหร่"))
    assert "ขัดข้องชั่วคราว" in replies(sent)[0]
