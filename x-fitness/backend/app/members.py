"""Sign-up from the website: a new member waits for staff (status pending) with a first payment awaiting its slip.

The new member gets a member code at once, so they can verify on the website or in chat and send the slip like any
member. Staff confirm or turn down the sign-up on the admin Members page (backoffice.set_member). A phone number that
already belongs to a member (not a turned-down sign-up) is refused with a request to use another number: the owner chose
this over rule N-04 (not saying who is a member), so the per-IP sign-up limit, counted before any check, slows guessing.
"""
import re
from calendar import monthrange
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import backoffice, business, chat, config, db, limits

SIGNUPS_PER_HOUR = 5        # per IP: enough for a family at one counter, too few to flood the members table
NOT_ONLINE = {"PKG-DAY"}    # the day pass is bought at the counter only (KB-02)
EXTRA_MONTHS = {"YEAR13": 1}            # promotions that lengthen the membership; NOJOIN drops the joining fee
NO_JOINING_FEE = {"NOJOIN"}
NAME = re.compile(r"^[^\x00-\x1f<>]{1,40}$")
PHONE_TAKEN = "เบอร์นี้ใช้สมัครสมาชิกไว้แล้ว กรุณาใช้เบอร์อื่น หรือถ้าเคยสมัครแล้วติดต่อเคาน์เตอร์ โทร 038-000-888"
TOO_MANY = "สมัครจากเครื่องนี้หลายครั้งแล้วครับ รอสักครู่ หรือสมัครที่เคาน์เตอร์ โทร 038-000-888"
NO_MATCH = "ข้อมูลไม่ตรงกับระบบ กรุณาตรวจสอบรหัสสมาชิกและเบอร์โทร 4 ตัวท้าย"
PUBLIC_FIELDS = ("member_id", "first_name", "last_name", "phone_last4", "package_id", "start_date", "end_date", "status",
                 "freeze_until", "points", "pt_sessions_left")   # never the full phone number

router = APIRouter(prefix="/api/members", tags=["members"])


class SignupIn(BaseModel):
    first_name: str = Field(max_length=40)
    last_name: str = Field(max_length=40)
    phone: str = Field(max_length=20)
    package_id: str = Field(max_length=20)
    promo_code: str | None = Field(default=None, max_length=20)
    consent: bool


class VerifyIn(BaseModel):
    member_id: str = Field(max_length=20)
    phone_last4: str = Field(pattern=r"^\d{4}$")


@router.post("/signup", status_code=201, summary="สมัครสมาชิกจากหน้าเว็บ: ได้รหัสสมาชิก สถานะรอพนักงานยืนยัน พร้อมยอดที่ต้องโอน")
def signup(body: SignupIn, request: Request):
    if not limits.allow("signup:" + limits.client_ip(request), SIGNUPS_PER_HOUR, 3600):
        raise HTTPException(429, TOO_MANY)
    first, last = body.first_name.strip(), body.last_name.strip()
    if not (NAME.match(first) and NAME.match(last)):
        raise HTTPException(422, "กรุณากรอกชื่อและนามสกุล (ไม่เกิน 40 ตัวอักษร)")
    digits = re.sub(r"[\s-]", "", body.phone)
    if not re.fullmatch(r"0\d{9}", digits):
        raise HTTPException(422, "เบอร์โทรต้องเป็นตัวเลข 10 หลัก ขึ้นต้นด้วย 0")
    if any(re.sub(r"\D", "", m["phone"]) == digits and m["status"] != "cancelled" for m in business.table("members")):
        raise HTTPException(409, PHONE_TAKEN)
    if not body.consent:
        raise HTTPException(422, "กรุณายินยอมให้ร้านเก็บข้อมูลเพื่อการสมัครสมาชิก")
    pkg = next((p for p in business.table("packages") if p["id"] == body.package_id and p["id"] not in NOT_ONLINE), None)
    if not pkg:
        raise HTTPException(422, "ไม่พบแพ็กเกจนี้ หรือแพ็กเกจนี้สมัครได้ที่เคาน์เตอร์เท่านั้น")
    code = (body.promo_code or "").strip().upper()
    if code:
        error = promo_error(code, pkg["id"])
        if error:
            raise HTTPException(422, error)

    today = datetime.now(backoffice.THAI).date()
    months = (12 if pkg["unit"] == "ปี" else pkg["contract_months"] or 1) + EXTRA_MONTHS.get(code, 0)
    fee = 0 if code in NO_JOINING_FEE else pkg["joining_fee"]
    member = {"first_name": first, "last_name": last, "phone": f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", "phone_last4": digits[-4:],
              "package_id": pkg["id"], "start_date": today.isoformat(), "end_date": _add_months(today, months).isoformat(),
              "status": "pending", "points": 0, "pt_sessions_left": 0}
    payment = {"description": f"ค่าสมัครสมาชิก {pkg['name_th']}" + (" + ค่าแรกเข้า" if fee else "") + (f" · โค้ด {code}" if code else ""),
               "amount": float(pkg["price"] + fee), "due": today.isoformat(), "status": "awaiting_slip"}
    member_id, payment_id = db.add_signup(member, payment, today.strftime("%y%m"))
    return {"member_id": member_id, "status": "pending", "package_id": pkg["id"], "start_date": member["start_date"], "end_date": member["end_date"],
            "payment": {"id": payment_id, "description": payment["description"], "amount": payment["amount"]},
            "bank": business.table("business")["bank"]}


@router.post("/verify", summary="ยืนยันตัวตนบนหน้าเว็บ (รหัสสมาชิก + เบอร์ 4 ตัวท้าย) · ได้ข้อมูลสมาชิกที่ไม่มีเบอร์เต็ม")
def verify(body: VerifyIn, request: Request):
    if not limits.allow("chat:" + limits.client_ip(request), config.RATE_LIMIT_PER_MIN):
        raise HTTPException(429, limits.TOO_FAST)
    m = chat.verified(body.member_id, body.phone_last4)
    if not m:
        raise HTTPException(404, chat.VERIFY_LOCKED if limits.verify_locked(body.member_id) else NO_MATCH)   # same answer whether the code exists or not
    return {k: m[k] for k in PUBLIC_FIELDS if k in m}


def promo_error(code: str, package_id: str) -> str | None:
    """Why the code cannot be used for this package (same wording as the website's checkPromo), or None."""
    p = next((x for x in business.table("promotions") if x["code"] == code), None)
    today = datetime.now(backoffice.THAI).date().isoformat()
    if not p:
        return f"ไม่พบโค้ด {code} ในระบบ"
    if p["status"] == "inactive":
        return f"โค้ด {code} ปิดใช้ชั่วคราว"
    if p["status"] == "expired" or today > p["end"]:
        return f"โค้ด {code} หมดเขตแล้ว"
    if today < p["start"]:
        return f"โค้ด {code} ยังไม่เริ่มใช้"
    if p["applies_to"][0] != "ALL" and package_id not in p["applies_to"]:
        return f"โค้ด {code} ใช้กับแพ็กเกจนี้ไม่ได้"
    return None


def _add_months(d, months: int):
    """Same day `months` later, the day before (a 12-month membership from 5 Jan ends 4 Jan), like the seed members."""
    y, m = divmod(d.month - 1 + months, 12)
    end = d.replace(year=d.year + y, month=m + 1, day=1)
    return end.replace(day=min(d.day, monthrange(end.year, end.month)[1])) - timedelta(days=1)
