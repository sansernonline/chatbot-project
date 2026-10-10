"""Chat conversation endpoints.

Customer (the chat widget) can read its own conversation, add user/bot messages and ask for a human.
Admin (the inbox) can list everything, reply as an agent, change status and delete — needs a login token.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from . import auth, db, line

TICKET = r"^([A-Z][0-9]){5}$"   # customer ticket, e.g. K3M8P2Q7R5
ConvId = Path(pattern=TICKET)


class Message(BaseModel):
    sender: Literal["user", "bot", "agent", "system"] = Field(alias="from")
    text: str = Field(min_length=1, max_length=2000)
    by: str | None = Field(default=None, max_length=60)
    notify: bool = False
    at: str | None = None


class Handoff(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    name: str | None = Field(default=None, max_length=120)
    member_id: str | None = Field(default=None, max_length=20)


class Patch(BaseModel):
    name: str | None = None
    member_id: str | None = None
    topic: str | None = None
    status: Literal["bot", "waiting", "agent", "closed"] | None = None
    agent: str | None = None
    seen_admin: int | None = Field(default=None, ge=0)
    touch: bool = True


class Login(BaseModel):
    user: str
    password: str


customer = APIRouter(prefix="/api/conversations", tags=["customer chat"])
admin = APIRouter(prefix="/api/admin", tags=["admin inbox"])
admin_only = [Depends(auth.require_admin)]


@customer.get("/{cid}", summary="ลูกค้าอ่านแชตของตัวเอง (ticket 10 ตัว เช่น K3M8P2Q7R5)")
def get_own(cid: str = ConvId):
    return _found(db.get(cid))


@customer.post("/{cid}/messages", summary="บันทึกข้อความลูกค้าหรือบอทลงแชต")
def customer_message(m: Message, cid: str = ConvId):
    if m.sender == "agent":
        raise HTTPException(403, "ลูกค้าส่งข้อความในนามพนักงานไม่ได้")
    return db.add_message(cid, m.sender, m.text, notify=False)


@customer.post("/{cid}/handoff", summary="ลูกค้าขอคุยกับพนักงาน → แชตเข้ากล่องหลังบ้าน")
def customer_handoff(h: Handoff, cid: str = ConvId):
    return db.handoff(cid, h.topic, h.name, h.member_id)


@admin.post("/login", summary="ล็อกอินผู้ดูแล ได้ token ไปใส่ปุ่ม Authorize (Bearer)")
def admin_login(body: Login):
    token = auth.login(body.user, body.password)
    if not token:
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return {"token": token}


@admin.get("/conversations", dependencies=admin_only, summary="ทุกแชต พร้อมข้อความ (กล่องแชตหลังบ้าน)")
def admin_list():
    return db.list_all()


@admin.post("/conversations/{cid}/messages", dependencies=admin_only, summary="พนักงานตอบแชต (ส่งเข้า LINE ด้วยถ้าแชตมาจาก LINE)")
def admin_message(m: Message, cid: str = ConvId):
    conv = db.add_message(cid, m.sender, m.text, m.by, m.notify, m.at)
    if m.sender == "agent":
        line.push(cid, m.text)                      # chat came from LINE: deliver the staff reply there too
    return conv


@admin.patch("/conversations/{cid}", dependencies=admin_only, summary="เปลี่ยนสถานะแชต: bot · waiting · agent · closed")
def admin_patch(p: Patch, cid: str = ConvId):
    return db.patch(cid, p.model_dump(exclude_unset=True, exclude={"touch"}), p.touch)


@admin.delete("/conversations/{cid}", dependencies=admin_only, status_code=204, summary="ลบแชตเดียว")
def admin_delete(cid: str = ConvId):
    db.delete(cid)


@admin.delete("/conversations", dependencies=admin_only, status_code=204, summary="ลบแชตทั้งหมด")
def admin_delete_all():
    db.delete()


def _found(conv):
    if not conv:
        raise HTTPException(404, "ไม่พบแชตนี้")
    return conv
