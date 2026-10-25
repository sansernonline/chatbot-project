"""Back office: slip images staff can look at, status switches for payments / bookings / promotions, and dashboard numbers.

The business tables live in the database (loaded from data/db/*.json, test data included). Staff changes are written
to them and the bot reads them on every message, so switching a promotion off or confirming a payment shows in the
very next answer. "Reset test data" reloads the tables from data/db and forgets the slips.
"""
import json
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import auth, business, config, db

THAI = timezone(timedelta(hours=7))
EXT = {"image/png": "png", "image/jpeg": "jpg"}
STATUSES = {"payments": {"awaiting_slip", "pending_slip", "paid", "rejected"},
            "bookings": {"booked", "cancelled", "no_show"},
            "promotions": {"active", "inactive", "expired"},
            "members": {"pending", "active", "cancelled"}}   # a website sign-up: confirm (active) or turn down (cancelled)

router = APIRouter(prefix="/api/admin", tags=["back office"], dependencies=[Depends(auth.require_admin)])
web = APIRouter(prefix="/api", tags=["web data"])
PUBLIC = {"business": "business", "packages": "packages", "classes": "classes", "trainers": "trainers", "schedule": "schedule",
          "pt": "pt_packages", "products": "products", "promotions": "promotions", "rewards": "rewards"}   # website key → table


@web.get("/data", summary="ข้อมูลร้านสำหรับหน้าเว็บ จากฐานข้อมูล (ไม่มีข้อมูลสมาชิก) · รูปแบบเดียวกับ shared/db.js")
def web_data():
    return {key: business.table(name) for key, name in PUBLIC.items()}


@router.get("/data", summary="ข้อมูลที่หลังบ้านใช้: สมาชิก ผู้สนใจ (leads) และข้อมูลร้านทั้งหมด จากฐานข้อมูล")
def admin_data():
    return {**web_data(), "members": business.table("members"), "leads": business.table("leads")}



# ---------- slips the bot receives ----------

def save_upload(data: bytes, mime: str, conv_id: str | None) -> str:
    """Keep a slip image until answer() ties it to the member's payment. Returns the id the vision result carries."""
    _forget_old()
    upload_id = secrets.token_urlsafe(12)
    config.SLIPS_DIR.mkdir(parents=True, exist_ok=True)
    file = f"{upload_id}.{EXT.get(mime, 'png')}"
    (config.SLIPS_DIR / file).write_bytes(data)
    db.add_upload(upload_id, conv_id, file)
    return upload_id


def attach_slip(vision: dict, conv_id: str, member_id: str | None, check: dict) -> int | None:
    """After check_slip found the member's unpaid payment: the slip goes on that payment and it waits for staff.
    The image id must come from an upload in this same chat (the id in a vision result is sent by the browser)."""
    if not (member_id and check.get("payment_id") and vision.get("image_id")):
        return None
    file = db.take_upload(str(vision["image_id"]), conv_id)
    if not file:
        return None
    slip_id = db.add_slip(check["payment_id"], member_id, conv_id, file, vision.get("reference"), business._num(vision.get("amount")),
                          check["ok"], json.dumps(check.get("checks", []), ensure_ascii=False))
    db.set_status("payments", check["payment_id"], "pending_slip")
    return slip_id


def _forget_old() -> None:
    before = (datetime.now(timezone.utc) - timedelta(days=config.SLIP_KEEP_DAYS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    _delete_files(db.old_files(before))


def _delete_files(files: list[str]) -> None:
    for f in files:
        (config.SLIPS_DIR / f).unlink(missing_ok=True)


# ---------- admin API ----------

class Status(BaseModel):
    status: str


@router.get("/payments", summary="รายการชำระเงิน พร้อมสลิปของแต่ละรายการ")
def payments():
    held = db.slips()
    rows = []
    for p in business.table("payments"):
        m = business.member(p["member_id"]) or {}
        slips = [{"id": s["id"], "at": s["at"], "amount": s["amount"], "ok": bool(s["ok"]), "checks": json.loads(s["checks"]),
                  "url": f"/api/admin/slips/{s['id']}/image"} for s in held if s["payment_id"] == p["id"]]
        if p.get("slip_image"):   # seed data: a sample slip from qa/ (public, like the website's sample images)
            slips.insert(0, {"id": None, "sample": True, "url": f"/qa/{p['slip_image']}"})
        rows.append({**p, "member_name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(), "slips": slips})
    return rows


@router.get("/slips/{slip_id}/image", summary="ภาพสลิปที่ลูกค้าส่ง (เฉพาะผู้ดูแล)")
def slip_image(slip_id: int):
    s = db.slip(slip_id)
    path = (config.SLIPS_DIR / s["file"]).resolve() if s else None
    if not path or path.parent != config.SLIPS_DIR.resolve() or not path.exists():
        raise HTTPException(404, "ไม่พบภาพสลิป")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.get("/bookings", summary="การจองคลาส")
def bookings():
    return business.table("bookings")


@router.get("/promotions", summary="โปรโมชัน (สถานะที่บอทใช้อยู่)")
def promotions():
    return business.table("promotions")


@router.get("/members", summary="สมาชิกทั้งหมด รวมผู้สมัครจากหน้าเว็บที่รอยืนยัน (pending)")
def members():
    return business.table("members")


@router.patch("/members/{item_id}", summary="ผู้สมัครจากหน้าเว็บ: active = ยืนยันเป็นสมาชิก · cancelled = ไม่อนุมัติ · pending = ย้อนกลับ")
def set_member(item_id: str, body: Status):
    if body.status not in STATUSES["members"]:
        raise HTTPException(422, f"สถานะต้องเป็น {', '.join(sorted(STATUSES['members']))}")
    m = business.member(item_id)
    if not m:
        raise HTTPException(404, "ไม่พบสมาชิกนี้")
    if m["status"] not in STATUSES["members"]:   # frozen / expired members are changed at the counter, not here
        raise HTTPException(409, "เปลี่ยนสถานะได้เฉพาะผู้สมัครใหม่")
    db.set_status("members", item_id, body.status)
    return business.member(item_id)


@router.patch("/payments/{item_id}", summary="สถานะการชำระ: awaiting_slip · pending_slip · paid · rejected")
def set_payment(item_id: str, body: Status):
    return _set_status("payments", item_id, body)


@router.patch("/bookings/{item_id}", summary="เปิด/ปิดการจอง: booked · cancelled · no_show")
def set_booking(item_id: str, body: Status):
    return _set_status("bookings", item_id, body)


@router.patch("/promotions/{item_id}", summary="เปิด/ปิดโปร: active · inactive · expired (บอทใช้ค่าใหม่ทันที)")
def set_promotion(item_id: str, body: Status):
    return _set_status("promotions", item_id, body)


def _set_status(kind: str, item_id: str, body: Status):
    if body.status not in STATUSES[kind]:
        raise HTTPException(422, f"สถานะต้องเป็น {', '.join(sorted(STATUSES[kind]))}")
    if not db.set_status(kind, item_id, body.status):
        raise HTTPException(404, "ไม่พบรายการนี้")
    return next(x for x in business.table(kind) if x["id"] == item_id)


@router.post("/test-data/reset", status_code=204, summary="ล้างการเปลี่ยนแปลงและสลิปทั้งหมด กลับเป็นข้อมูลตั้งต้น")
def reset():
    _delete_files(db.reset_backoffice())


@router.get("/dashboard", summary="ตัวเลขหน้าภาพรวม จากข้อมูลจริง")
def dashboard():
    today = datetime.now(THAI).date()
    local = lambda iso: datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(THAI)
    convs = db.list_all()
    user_msgs = [local(m["at"]) for c in convs for m in c["msgs"] if m["from"] == "user"]
    hours = Counter(t.hour for t in user_msgs if t.date() == today)
    pays = business.table("payments")
    pending = [p for p in pays if p["status"] == "pending_slip"]
    members = business.table("members")
    books = business.table("bookings")
    slots = [s for s in business.table("schedule") if s["day"] == today.isoweekday()]
    return {
        "today": today.isoformat(),
        "chats_today": sum(any(m["from"] == "user" and local(m["at"]).date() == today for m in c["msgs"]) for c in convs),
        "chats_total": len(convs),
        "waiting": sum(c["status"] == "waiting" for c in convs),
        "messages_by_hour": [hours.get(h, 0) for h in range(24)],
        "handoff_topics": Counter(c["topic"] for c in convs if c["topic"]).most_common(6),
        "slips_pending": {"count": len(pending), "amount": sum(p["amount"] for p in pending)},
        "awaiting_slip": sum(p["status"] == "awaiting_slip" for p in pays),
        "members_active": sum(m["status"] == "active" for m in members),
        "members_total": len(members),
        "signups_pending": sum(m["status"] == "pending" for m in members),
        "bookings_upcoming": sum(b["status"] == "booked" and b["date"] >= today.isoformat() for b in books),
        "promotions_active": sum(p["status"] == "active" for p in business.table("promotions")),
        "classes_today": [{"slot_id": s["id"], "start": s["start"], "class_id": s["class_id"], "trainer_id": s["trainer_id"],
                           "booked": sum(b["slot_id"] == s["id"] and b["date"] == today.isoformat() and b["status"] == "booked" for b in books)}
                          for s in sorted(slots, key=lambda s: s["start"])],
    }
