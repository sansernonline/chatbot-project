"""Business data from data/db/*.json, and the checks that must be done in code rather than by the LLM."""
import json
from datetime import date, datetime
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


def check_slip(slip: dict, member_id: str | None) -> dict:
    """The 5 checks from KB-06. The result is preliminary: only staff can mark a payment as paid (never the bot)."""
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
        ("เลขบัญชีผู้รับลงท้าย 4521-0", _norm("4521-0") in _norm(slip.get("receiver_account_last") or slip.get("receiver_account"))),
        (f"ยอดเงินตรงกับยอดค้าง {due['amount']:,.2f} บาท", amount is not None and abs(amount - due["amount"]) < 0.01),
        ("วันที่โอนไม่เกิน 7 วันก่อนหรือหลังวันครบกำหนด", paid_on is not None and abs((paid_on - date.fromisoformat(due["due"])).days) <= 7),
        ("เลขอ้างอิงไม่เคยใช้มาก่อน", bool(slip.get("reference")) and slip["reference"] not in USED_SLIP_REFS),
    ]
    result = {"ok": all(ok for _, ok in checks), "payment_id": due["id"], "due_amount": due["amount"],
              "checks": [{"rule": r, "pass": ok} for r, ok in checks]}
    if amount is not None and amount < due["amount"]:
        result["short_by"] = round(due["amount"] - amount, 2)
    result["note"] = "ผ่านครบ 5 ข้อ สถานะเป็น 'รอพนักงานยืนยัน' (ยังไม่ใช่ชำระแล้ว)" if result["ok"] else "ไม่ผ่านบางข้อ ส่งต่อพนักงาน ห้ามบอกว่าชำระสำเร็จ"
    return result


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
