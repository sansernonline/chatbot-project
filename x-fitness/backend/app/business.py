"""Business data from data/db/*.json, and the checks that must be done in code rather than by the LLM."""
import json
import re
from datetime import date, datetime, timedelta
from functools import lru_cache

from . import config


@lru_cache(maxsize=None)
def table(name: str):
    """data/db/<name>.json → its 'items' list (or the whole object when it has no items)."""
    d = json.loads((config.DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return d.get("items", d) if isinstance(d, dict) else d


def member(member_id: str | None) -> dict | None:
    return next((m for m in table("members") if m["member_id"] == member_id), None) if member_id else None


def verify(member_id: str, last4: str) -> dict | None:
    """The member when member_id and the last 4 phone digits match (same check as the website's verify step)."""
    m = member(member_id.upper())
    return m if m and m["phone"].replace("-", "").endswith(last4) else None


def _hours() -> str:
    """Opening hours from business.json — a holiday line in KB-01 once made the LLM answer "every Tuesday 08:00–20:00"."""
    last = lambda close: (datetime.strptime(close, "%H:%M") - timedelta(minutes=30)).strftime("%H:%M")   # last entry: 30 min before closing
    hours = " · ".join(f"{h['days']} {h['open']}–{h['close']} (เข้าได้ถึง {last(h['close'])})" for h in table("business")["hours"])
    return f"เวลาเปิด-ปิดปกติทุกสัปดาห์: {hours} · เวลาวันหยุดนักขัตฤกษ์ใช้เฉพาะวันที่ KB-01 ระบุ วันอื่นใช้เวลาปกติ · ร้านไม่เปิด 24 ชั่วโมง"


def _promos() -> str:
    """Which packages each promo code covers, from promotions.json — the LLM let NOJOIN apply to the Student package."""
    names = {p["id"]: p["name_th"] for p in table("packages")}
    covers = lambda p: "ทุกแพ็กเกจ" if p["applies_to"] == ["ALL"] else "เฉพาะ " + ", ".join(names.get(i, i) for i in p["applies_to"])
    return " · ".join(f"โค้ด {p['code']} ({p['title']}) ใช้ได้{covers(p)} ถึง {p['end']}" if p["status"] == "active"
                      else f"โค้ด {p['code']} หมดเขตแล้ว ใช้ไม่ได้" for p in table("promotions")) + " · แพ็กเกจที่ไม่อยู่ในรายการของโค้ด ใช้โค้ดนั้นไม่ได้"


# Rules that must not depend on what RAG happens to retrieve: when a question touches one, the fact is sent with it.
# (pattern in the question, or the member's package) → fact, source document
RULES = [
    (re.compile(r"เปิด|ปิด|กี่โมง|กี่ทุ่ม|เวลาทำการ|\bopen|\bclose|24\s*(ชั่วโมง|ชม)", re.I), _hours(), "KB-01"),
    (re.compile(r"โค้ด|โปร|promo|code|YEAR13|NOJOIN|FRIEND300|MID2", re.I), _promos(), "KB-07"),
    (re.compile(r"ยิมอื่น|ที่อื่น|ร้านอื่น|คู่แข่ง|ยิมนี้|ถูกกว่า|other gym|cheaper", re.I),
     "ร้านไม่ลดราคาหรือเทียบราคาตามยิมอื่น ราคาและโปรของร้านมีเฉพาะในคลังความรู้ ห้ามนำราคาของยิมอื่นหรือราคาในภาพมาบอกเป็นราคา/โปรของร้าน "
     "ให้ปฏิเสธสุภาพ บอกว่าส่วนลดเพิ่มต้องให้ผู้จัดการสาขาอนุมัติ แล้วแนะนำโปรที่ยังใช้ได้วันนี้", "KB-07"),
    (re.compile(r"(นักเรียน|นักศึกษา|student|PKG-STU).*(ride|ปั่น)|(ride|ปั่น).*(นักเรียน|นักศึกษา|student|PKG-STU)", re.I | re.S),
     "แพ็กเกจนักเรียน/นักศึกษา (Student) เข้าคลาส Ride (ปั่นจักรยาน) ไม่ได้ เข้าได้อีก 7 คลาส ไม่จำกัด", "KB-02"),
    (re.compile(r"ส่วนลด|ลดให้|ลดราคา|ลด(อีก)?\s*\d+\s*(%|เปอร์|บาท)|discount", re.I),
     "ร้านไม่มีส่วนลดอื่นนอกจากโปรโมชันที่ประกาศในคลังความรู้ พนักงานและบอทให้ส่วนลดพิเศษไม่ได้ "
     "ส่วนลดเพิ่มต้องให้ผู้จัดการสาขาอนุมัติเป็นลายลักษณ์อักษร ให้ปฏิเสธสุภาพแล้วแนะนำโปรที่ยังใช้ได้วันนี้", "KB-07"),
    (re.compile(r"ส่ง(ของ|สินค้า|เวย์|โปรตีน)?.{0,10}(ถึงบ้าน|ไปที่บ้าน|ให้ที่บ้าน)|จัดส่ง|เดลิเวอรี่|delivery|สั่งออนไลน์", re.I),
     "ร้านขายสินค้าเฉพาะที่เคาน์เตอร์ ยังไม่มีบริการจัดส่งและไม่มีการสั่งซื้อออนไลน์", "KB-07"),
    (re.compile(r"ผ่อน|installment", re.I),
     "ร้านไม่มีบริการผ่อนชำระ 0% และไม่รับเช็ค ชำระได้ด้วยเงินสด บัตรเครดิต/เดบิต พร้อมเพย์ที่เคาน์เตอร์ โอนเงินแล้วส่งสลิป หรือตัดบัตรอัตโนมัติรายเดือน", "KB-06"),
    (re.compile(r"ฝากเด็ก|ฝากลูก|พาลูก|เด็ก.{0,8}(เข้า|เล่น|ใช้)", re.I),
     "ร้านไม่มีบริการรับฝากเด็ก และไม่อนุญาตให้เด็กอายุต่ำกว่า 15 ปีเข้าพื้นที่ออกกำลังกาย", "KB-08"),
    (re.compile(r"คืนเงิน|ขอเงินคืน|refund", re.I),
     "การคืนเงินทุกกรณีต้องให้ผู้จัดการสาขาอนุมัติ บอทอนุมัติเองไม่ได้ ให้บอกเงื่อนไขแล้วเสนอพิมพ์ \"คุยกับพนักงาน\" เพื่อส่งคำขอให้ผู้จัดการ", "KB-05"),
]


def rules_for(text: str, member_id: str | None = None) -> list[tuple[str, str]]:
    """(fact, source) for each rule the question touches; a verified member's own package counts too."""
    m = member(member_id)
    subject = f"{text} {m['package_id'] if m else ''}"
    return [(fact, src) for pattern, fact, src in RULES if pattern.search(subject)]


def member_context(member_id: str | None) -> str:
    """What the bot may tell a verified member about themself. Phone number is never included."""
    m = member(member_id)
    if not m:
        return "ผู้ใช้ยังไม่ได้ยืนยันตัวตน ห้ามเปิดเผยข้อมูลสมาชิกรายบุคคล ถ้าถามเรื่องข้อมูลส่วนตัวให้ขอรหัสสมาชิกและเบอร์โทร 4 ตัวท้าย หรือให้กดยืนยันตัวตนบนหน้าเว็บ"
    pkg = next(p for p in table("packages") if p["id"] == m["package_id"])
    dues = [p for p in table("payments") if p["member_id"] == m["member_id"] and p["status"] != "paid"]
    books = [b for b in table("bookings") if b["member_id"] == m["member_id"] and b["status"] == "booked"]
    lines = [
        f"สมาชิกที่ยืนยันตัวตนแล้ว: {m['member_id']} คุณ{m['first_name']}",
        f"แพ็กเกจ: {pkg['name_th']} ({pkg['name']}) สถานะ {m['status']} ใช้ได้ถึง {m['end_date']}" + (f" พักถึง {m['freeze_until']}" if m.get("freeze_until") else ""),
        f"แต้มสะสม: {m['points']} · PT คงเหลือ: {m['pt_sessions_left']} ครั้ง",
        "ยอดค้างชำระ: " + ("; ".join(f"{p['description']} {p['amount']:,.2f} บาท ครบกำหนด {p['due']}" for p in dues) or "ไม่มี"),
        f"คลาสที่จองไว้: {len(books)} รายการ",
    ]
    return "\n".join(lines)


USED_SLIP_REFS = {"DEMO2609010930Z9"}  # references already used — the real system reads these from its payments table
FAILED_TRANSFER = re.compile(r"ไม่สำเร็จ|ล้มเหลว|ถูกปฏิเสธ|\b(failed|unsuccessful|declined|rejected)\b", re.I)


def check_slip(slip: dict, member_id: str | None) -> dict:
    """The 5 checks from KB-06. The result is preliminary: only staff can mark a payment as paid (never the bot).
    A slip whose status says the transfer failed ("โอนเงินไม่สำเร็จ") never passes, whatever the 5 checks say."""
    m = member(member_id)
    if not m:
        return {"ok": False, "need_verify": True, "checks": [], "note": "ต้องยืนยันตัวตนก่อนจึงจะตรวจสลิปเทียบยอดค้างได้"}
    due = next((p for p in table("payments") if p["member_id"] == m["member_id"] and p["status"] == "pending_slip"), None)
    if not due:
        return {"ok": False, "checks": [], "note": "ไม่พบยอดค้างชำระที่รอสลิป ส่งต่อพนักงานตรวจสอบ"}
    bank = table("business")["bank"]
    amount = _num(slip.get("amount"))
    paid_on = _date(slip.get("datetime") or slip.get("date"))
    checks = [
        ("ชื่อบัญชีผู้รับเป็น " + bank["account_name"], _norm(bank["account_name"]) in _norm(slip.get("receiver_name"))),
        ("เลขบัญชีผู้รับลงท้าย 4521-0", _digits(slip.get("receiver_account_last") or slip.get("receiver_account")).endswith("45210")),
        (f"ยอดเงินตรงกับยอดค้าง {due['amount']:,.2f} บาท", amount is not None and abs(amount - due["amount"]) < 0.01),
        ("วันที่โอนไม่เกิน 7 วันก่อนหรือหลังวันครบกำหนด", paid_on is not None and abs((paid_on - date.fromisoformat(due["due"])).days) <= 7),
        ("เลขอ้างอิงไม่เคยใช้มาก่อน", bool(slip.get("reference")) and slip["reference"] not in USED_SLIP_REFS),
    ]
    failed = bool(FAILED_TRANSFER.search(str(slip.get("status") or "")))
    result = {"ok": all(ok for _, ok in checks) and not failed, "payment_id": due["id"], "due_amount": due["amount"],
              "checks": [{"rule": r, "pass": ok} for r, ok in checks]}
    if failed:
        result["transfer_failed"] = True
    if amount is not None and amount < due["amount"]:
        result["short_by"] = round(due["amount"] - amount, 2)
    if amount is not None and amount > due["amount"]:
        result["over_by"] = round(amount - due["amount"], 2)       # the LLM states the difference: give it the number
    result["note"] = ("ผ่านครบ 5 ข้อ สถานะเป็น 'รอพนักงานยืนยัน' (ยังไม่ใช่ชำระแล้ว)" if result["ok"] else
                      ("สลิประบุว่าการโอนไม่สำเร็จ " if failed else "ไม่ผ่านบางข้อ ")
                      + "บอกลูกค้าว่าส่งให้พนักงานตรวจต่อแล้ว ไม่ต้องโอนซ้ำจนกว่าพนักงานติดต่อกลับ ให้พิมพ์ \"คุยกับพนักงาน\" ได้ ห้ามบอกว่าชำระสำเร็จ")
    return result


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _norm(s) -> str:
    return "".join(str(s or "").split()).replace(".", "").lower()


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _date(v) -> date | None:
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except (TypeError, ValueError):
        return None
