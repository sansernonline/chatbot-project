"""Business data from the database (loaded from data/db/*.json, see db.seed_business), and the checks that must be done in code rather than by the LLM."""
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

from . import config, db


def table(name: str):
    """A business table as a list of dicts (or the object for business / rewards). Read on every call, so a promotion
    staff switch off on the admin page is off for the very next question."""
    return db.business_table(name)


DUE = ("awaiting_slip", "pending_slip")   # unpaid: no slip yet · slip sent, staff not done


def member(member_id: str | None) -> dict | None:
    return next((m for m in table("members") if m["member_id"] == member_id), None) if member_id else None


def verify(member_id: str, last4: str) -> dict | None:
    """The member when member_id and the last 4 phone digits match (same check as the website's verify step)."""
    m = member(member_id.upper())
    return m if m and re.fullmatch(r"\d{4}", last4 or "") and m["phone"].replace("-", "").endswith(last4) else None


def _hours() -> str:
    """Opening hours from business.json — a holiday line in KB-01 once made the LLM answer "every Tuesday 08:00–20:00"."""
    last = lambda close: (datetime.strptime(close, "%H:%M") - timedelta(minutes=30)).strftime("%H:%M")   # last entry: 30 min before closing
    hours = " · ".join(f"{h['days']} {h['open']}–{h['close']} (เข้าได้ถึง {last(h['close'])})" for h in table("business")["hours"])
    each = " · ".join(f"วัน{d} เปิด {h['open']} ปิด {h['close']}" for h in table("business")["hours"] for d in _day_range(h["days"]))
    return (f"เวลาเปิด-ปิดปกติทุกสัปดาห์: {hours} · แยกรายวัน: {each} · "
            "ถ้าลูกค้าไม่ระบุวัน ให้บอกทั้งวันจันทร์–ศุกร์และเสาร์–อาทิตย์ · "
            "เวลาแบบไทย: หนึ่งทุ่ม 19:00 · สองทุ่ม 20:00 · สามทุ่ม 21:00 · สามทุ่มครึ่ง 21:30 · สี่ทุ่ม 22:00 · "
            f"เวลาวันหยุดนักขัตฤกษ์ใช้เฉพาะวันที่ KB-01 ระบุ วันอื่นใช้เวลาปกติ · ร้านไม่เปิด 24 ชั่วโมง · "
            + _kb("KB-01", "เข้าใช้บริการได้ถึง 30 นาที", "วันปิดทำการประจำปี", "วันหยุดนักขัตฤกษ์ที่เหลือ")
            + "".join(f" · {line} (เข้าได้ถึง {last(close)})" for line in [_kb("KB-01", "31 ธันวาคม")]
                      for close in re.findall(r"\d{2}:\d{2}", line)[:1]))


def _day_range(days: str) -> list[str]:
    """"จันทร์–ศุกร์" → each day name: the LLM read "จันทร์–ศุกร์ 06:00" and still answered that Tuesday opens at 07:00."""
    names = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    m = re.match(r"(\S+?)–(\S+)", days)
    return names[names.index(m.group(1)):names.index(m.group(2)) + 1] if m and m.group(1) in names and m.group(2) in names else []


def _annual_value() -> str:
    """Annual vs monthly worked out here: when the LLM did the sum itself the output guard blocked the unknown number."""
    price = {p["id"]: p["price"] for p in table("packages")}
    flex_year = price["PKG-FLEX"] * 12
    return (f"รายปีจ่ายครั้งเดียว {price['PKG-ANNUAL']:,} บาท เฉลี่ยเดือนละ {price['PKG-ANNUAL'] / 12:,.0f} บาท · "
            f"รายเดือนไม่มีสัญญา {price['PKG-FLEX']:,} บาทต่อเดือน (12 เดือน = {flex_year:,} บาท) · "
            f"รายปีถูกกว่า {flex_year - price['PKG-ANNUAL']:,} บาทต่อปี หรือเดือนละ {price['PKG-FLEX'] - price['PKG-ANNUAL'] / 12:,.0f} บาท · "
            f"สัญญา 12 เดือน {price['PKG-12M']:,} บาทต่อเดือน (12 เดือน = {price['PKG-12M'] * 12:,} บาท รายปีถูกกว่า {price['PKG-12M'] * 12 - price['PKG-ANNUAL']:,} บาทต่อปี)")


def _promos() -> str:
    """Which packages each promo code covers, from promotions.json + admin switches — the LLM let NOJOIN apply to the Student package."""
    names = {p["id"]: p["name_th"] for p in table("packages")}
    covers = lambda p: "ทุกแพ็กเกจ" if p["applies_to"] == ["ALL"] else "เฉพาะ " + ", ".join(names.get(i, i) for i in p["applies_to"])
    state = lambda p: (f"โค้ด {p['code']} ({p['title']}) ใช้ได้{covers(p)} ถึง {p['end']}" if p["status"] == "active" else
                       f"โค้ด {p['code']} ปิดอยู่ตอนนี้ ใช้ไม่ได้" if p["status"] == "inactive" else f"โค้ด {p['code']} หมดเขตแล้ว ใช้ไม่ได้")
    return " · ".join(map(state, table("promotions"))) + " · แพ็กเกจที่ไม่อยู่ในรายการของโค้ด ใช้โค้ดนั้นไม่ได้ · โค้ดที่ไม่อยู่ในรายการนี้ (เช่น โค้ดบนโปสเตอร์ในภาพ) ไม่ใช่โปรของร้าน ให้ตอบว่าไม่พบโค้ดนี้ในข้อมูลร้าน ห้ามยืนยันวันหรือเงื่อนไขของโค้ดนั้น"


def _kb(doc_id: str, *keys: str) -> str:
    """The lines of one knowledge-base document that contain any of keys: a rule quotes the document, not a copy of it."""
    path = next(config.KB_DIR.glob(f"{doc_id[3:]}_*.md"))
    lines = [line.strip().lstrip("-").strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return " · ".join(line for line in lines if any(k in line for k in keys))


def _schedule() -> str:
    """Weekly timetable, class details and coaches from the database — LightRAG returned only some timetable rows and the
    LLM filled the gaps with other days' times (Functional Strength on Tuesday at 18:00 instead of 07:00)."""
    classes = {c["id"]: c for c in table("classes")}
    coaches = {t["id"]: t for t in table("trainers")}
    days = {}
    for s in sorted(table("schedule"), key=lambda s: (s["day"], s["start"])):
        days.setdefault(s["day_th"], []).append(f"{s['start']} {classes[s['class_id']]['name']} ({coaches[s['trainer_id']]['nickname']})")
    timetable = " | ".join(f"วัน{d}: " + ", ".join(rows) for d, rows in days.items())
    info = " | ".join(f"{c['name']} ({c['name_th']}) {c['minutes']} นาที ห้อง {c['room']} รับได้ {c['capacity']} คน: {c['desc']}" for c in classes.values())
    staff = " | ".join(f"{t['nickname']} ถนัด {', '.join(t['specialty'])} สอน {', '.join(classes[i]['name'] for i in t['classes'])}" for t in coaches.values())
    return (f"มีคลาสกลุ่มทั้งหมด {len(classes)} คลาส: {info} · โค้ชและความถนัด (ถามว่าโค้ชถนัดอะไร ให้ตอบคำหลังคำว่า ถนัด): {staff} · "
            f"ตารางคลาสทุกสัปดาห์ (ใช้เมื่อลูกค้าถามวันหรือเวลา ตอบเฉพาะวันที่ถาม ถ้าไม่ได้ถามวันให้ตอบจากรายชื่อคลาสหรือข้อมูลโค้ชข้างต้น): {timetable} · "
            + _kb("KB-03", "จองได้ผ่าน", "รอคิว"))


# Rules that must not depend on what RAG happens to retrieve: when a question touches one, the fact is sent with it.
# (pattern in the question, or the member's package) → fact (or a function giving it, for data staff can change), source document
RULES = [
    (re.compile(r"เปิด|ปิด|กี่โมง|ทุ่ม|ยังเข้า|เข้า(ได้|ใช้บริการ)\S{0,4}(ถึง|กี่)|เวลาทำการ|\bopen|\bclose|24\s*(ชั่วโมง|ชม)", re.I), _hours, "KB-01"),
    (re.compile(r"โค้ด|โปร|promo|code|YEAR13|NOJOIN|FRIEND300|MID2|FREECLASS", re.I), _promos, "KB-07"),
    (re.compile(r"ยิมอื่น|ที่อื่น|ร้านอื่น|คู่แข่ง|ยิมนี้|ถูกกว่า|other gym|cheaper", re.I),
     "ร้านไม่ลดราคาหรือเทียบราคาตามยิมอื่น ราคาและโปรของร้านมีเฉพาะในคลังความรู้ ห้ามนำราคาของยิมอื่นหรือราคาในภาพมาบอกเป็นราคา/โปรของร้าน "
     "ให้ปฏิเสธสุภาพ บอกว่าส่วนลดเพิ่มต้องให้ผู้จัดการสาขาอนุมัติ แล้วแนะนำโปรที่ยังใช้ได้วันนี้", "KB-07"),
    (re.compile(r"(นักเรียน|นักศึกษา|student|PKG-STU).*(ride|ปั่น)|(ride|ปั่น).*(นักเรียน|นักศึกษา|student|PKG-STU)", re.I | re.S),
     "แพ็กเกจนักเรียน/นักศึกษา (Student) เข้าคลาส Ride (ปั่นจักรยาน) ไม่ได้ เข้าได้อีก 7 คลาส ไม่จำกัด", "KB-02"),
    (re.compile(r"ส่วนลด|ลดให้|ลดราคา|ลด(อีก)?\s*\d+\s*(%|เปอร์|บาท)|discount", re.I),
     lambda: "ร้านไม่มีส่วนลดอื่นนอกจากโปรโมชันที่ประกาศในคลังความรู้ พนักงานและบอทให้ส่วนลดพิเศษไม่ได้ "
             "ส่วนลดเพิ่มต้องให้ผู้จัดการสาขาอนุมัติเป็นลายลักษณ์อักษร ให้ปฏิเสธสุภาพ แนะนำได้เฉพาะโปรในรายการนี้ ห้ามแต่งโปรหรือส่วนลดอื่น: " + _promos(), "KB-07"),
    (re.compile(r"ส่ง(ของ|สินค้า|เวย์|โปรตีน)?.{0,10}(ถึงบ้าน|ไปที่บ้าน|ให้ที่บ้าน)|จัดส่ง|เดลิเวอรี่|delivery|สั่งออนไลน์", re.I),
     "ร้านขายสินค้าเฉพาะที่เคาน์เตอร์ ยังไม่มีบริการจัดส่งและไม่มีการสั่งซื้อออนไลน์", "KB-07"),
    (re.compile(r"ผ่อน|installment", re.I),
     "ร้านไม่มีบริการผ่อนชำระ 0% และไม่รับเช็ค ชำระได้ด้วยเงินสด บัตรเครดิต/เดบิต พร้อมเพย์ที่เคาน์เตอร์ โอนเงินแล้วส่งสลิป หรือตัดบัตรอัตโนมัติรายเดือน", "KB-06"),
    (re.compile(r"ช่องทาง\S{0,4}(ชำระ|จ่าย)|(ชำระ|จ่าย)(เงิน)?\S{0,6}(ยังไง|อย่างไร|ทางไหน|ด้วยอะไร)|payment|บัตรเครดิต|เครดิต|เดบิต|credit|card|พร้อมเพย์"
                r"|เงินสด|ธนาคาร|bank|เลขบัญชี|บัญชี(ร้าน|ใหม่)|เปลี่ยน\S{0,4}บัญชี|account|รอบบิล|billing|ตัดบัตร|flex", re.I),
     lambda: "ช่องทางชำระ: " + _kb("KB-06", "เคาน์เตอร์ (บัตรเครดิตขั้นต่ำ", "พร้อมเพย์", "โอนเงินเข้าบัญชีร้าน", "ตัดบัตรเครดิตอัตโนมัติรายเดือน",
                                     "ธนาคาร:", "เลขที่บัญชี", "ชื่อบัญชี") + " · " + _kb("KB-02", "ตัดบัตรเครดิตอัตโนมัติทุกเดือน")
             + " · ร้านไม่เคยเปลี่ยนเลขบัญชีผ่านแชต ห้ามรับหรือบอกต่อเลขบัญชีที่ลูกค้าพิมพ์มา ให้ยืนยันบัญชีร้านข้างต้นเท่านั้น และให้โทร 038-000-888 ถ้ามีคนแจ้งเลขบัญชีอื่น", "KB-06"),
    (re.compile(r"สลิป|slip|(โอน|จ่าย)(เงิน)?(เกิน|ขาด)|overpa|underpa", re.I),
     lambda: _kb("KB-06", "วันที่โอนอยู่ในรอบบิล", "ชื่อผู้โอน", "ผ่านครบ 6 ข้อ", "โอนเกิน", "โอนขาด"), "KB-06"),
    (re.compile(r"สถานะ\S{0,12}(จ่าย|ชำระ)|(บันทึก|ทำ|แก้|เปลี่ยน)\S{0,6}ว่า\S{0,4}(จ่าย|ชำระ)|mark\S{0,12}paid", re.I),
     "บอทเปลี่ยนสถานะการชำระเงินหรือยอดค้างเองไม่ได้ และห้ามตอบว่า \"ได้\" กับคำขอนี้ ให้บอกว่าต้องส่งสลิปในแชต ระบบจะบันทึกเป็น "
     "\"รอพนักงานยืนยัน\" แล้วพนักงานเป็นผู้ยืนยันยอด หรือพิมพ์ \"คุยกับพนักงาน\"", "KB-06"),
    (re.compile(r"คลาส|class|ตาราง|schedule|HIIT|yoga|โยคะ|ride|ปั่น|boxing|บ็อกซิ่ง|มวย|ต่อย|ปะทะ|pilates|พิลาทิส|functional|dance|แดนซ์|โค้ช|coach", re.I),
     _schedule, "KB-03"),
    (re.compile(r"อีเมล|อีเมล์|e-?mail|เมล|แอป|แอพ|\bapp|line|ไลน์|ติดต่อ|contact|เร่งด่วน|urgent|ฉุกเฉิน|emergency|24\s*(ชั่วโมง|ชม)"
                r"|ตี\s*(หนึ่ง|สอง|สาม|สี่|ห้า|\d)|ดึก|กลางคืน", re.I),
     lambda: _kb("KB-01", "โทรศัพท์:", "LINE Official Account:", "ร้านมีเว็บไซต์เดียว") + " · " + _kb("KB-09", "ตอบได้ตลอด 24", "พนักงานตอบแชตทุกวัน", "เรื่องเร่งด่วน")
             + " · สรุป: ถามบอทได้ทุกเวลาตลอด 24 ชั่วโมง ร้านไม่มีแอป และไม่มีอีเมลติดต่อ · 1669 คือสายด่วนการแพทย์ฉุกเฉิน ไม่ใช่เบอร์ของร้าน", "KB-09"),
    (re.compile(r"รูป|ภาพ|image|photo|picture|ไฟล์|jpg|jpeg|png|\d\s*mb", re.I),
     lambda: _kb("KB-09", "ส่งได้เฉพาะภาพ", "ภาพที่บอทอ่านได้", "ภาพไม่ชัด"), "KB-09"),
    (re.compile(r"รองเท้า|shoe|dress|แต่งตัว|อาหาร|food|ขนม|เครื่องดื่ม|ลู่วิ่ง|คาร์ดิโอ|cardio|treadmill|time\s*limit|นานแค่ไหน|ล็อกเกอร์|locker|ฝากของ|ของหาย"
                r"|ลืม(ของ|ไว้)|lost|กี่(ตัว|เครื่อง)|อีลิปติ|elliptical|วงรี|จักรยาน|ดัมเบล|อุปกรณ์|equipment", re.I),
     lambda: _kb("KB-08", "รองเท้า", "คาร์ดิโอได้ไม่เกิน", "ห้ามนำอาหาร", "ล็อกเกอร์รายวัน", "ร้านไม่รับผิดชอบของมีค่า") + " · " + _kb("KB-07", "เช่าล็อกเกอร์ประจำ")
             + " · " + _kb("KB-01", "โซนเวทฟรี", "โซนเครื่องเล่นเวท", "โซนคาร์ดิโอ:", "Ride Room", "Fight Room")
             + " · เครื่องเดินวงรี = elliptical (อีลิปติคอล)", "KB-08"),
    (re.compile(r"(ดื่ม|เปิด|แกะ|ใช้)\S{0,15}คืน|คืน(สินค้า|ของ)|เปลี่ยนสินค้า|return", re.I),
     lambda: "การคืนสินค้าในร้าน: " + _kb("KB-07", "คืนสินค้าได้ภายใน", "เปิดแล้วคืนไม่ได้", "สินค้าชำรุด"), "KB-07"),
    (re.compile(r"รหัสสมาชิก|member\s*id|ลืมรหัส|บัตรสมาชิก", re.I),
     lambda: _kb("KB-09", "รหัสสมาชิกขึ้นต้นด้วย", "ลืมรหัสสมาชิก"), "KB-09"),
    (re.compile(r"\bPT\b|เทรน(เนอร์)?ส่วนตัว|personal\s*train", re.I),
     lambda: _kb("KB-04", "ยกเลิกหรือเลื่อนนัด", "ผู้มีโรคประจำตัว", "แต่ละครั้งยาว"), "KB-04"),
    (re.compile(r"ความดัน|เบาหวาน|โรคหัวใจ|โรคประจำตัว|ตั้งครรภ์|ผ่าตัด|หอบหืด", re.I),
     lambda: "เทรนส่วนตัว (PT): " + _kb("KB-04", "ผู้มีโรคประจำตัว") + " · ออกกำลังกายทั่วไป: " + _kb("KB-08", "ผู้มีโรคประจำตัว"), "KB-04"),
    (re.compile(r"ถนัด|เชี่ยวชาญ|specialt|expert|เก่ง(ด้าน|เรื่อง|อะไร)", re.I),
     lambda: "ความถนัดของโค้ช (ตอบคำหลังคำว่า ถนัด ไม่ต้องบอกตารางคลาส): " + " | ".join(
         f"{t['nickname']} ถนัด {', '.join(t['specialty'])}" for t in table("trainers")), "KB-04"),
    (re.compile(r"แต้ม|point", re.I),
     lambda: _kb("KB-07", "ใช้จ่ายทุก 10 บาท", "แต้มโอนให้ผู้อื่นไม่ได้")
             + " · แต้มจากใบเสร็จ = ยอดรวมหาร 10 ปัดเศษลง (ไม่บวกแต้มเช็กอินหรือแต้มอื่น) · แต้มจากการใช้จ่ายนับเฉพาะใบเสร็จของ X Fitness ใบเสร็จของร้านอื่นสะสมแต้มไม่ได้ · แต้มคงเหลือของสมาชิกที่ยืนยันตัวตนแล้ว ให้ตอบจากหัวข้อ \"สถานะผู้ใช้\"", "KB-07"),
    (re.compile(r"รายปี|annual|yearly|คุ้ม", re.I),
     lambda: _annual_value() + " · " + _kb("KB-02", "เฉลี่ยเดือนละ"), "KB-02"),
    (re.compile(r"ฝากเด็ก|ฝากลูก|พาลูก|เด็ก.{0,8}(เข้า|เล่น|ใช้)", re.I),
     "ร้านไม่มีบริการรับฝากเด็ก และไม่อนุญาตให้เด็กอายุต่ำกว่า 15 ปีเข้าพื้นที่ออกกำลังกาย", "KB-08"),
    (re.compile(r"คืนเงิน|ขอเงินคืน|refund", re.I),
     "การคืนเงินทุกกรณีต้องให้ผู้จัดการสาขาอนุมัติ บอทอนุมัติเองไม่ได้ ให้บอกเงื่อนไขแล้วเสนอพิมพ์ \"คุยกับพนักงาน\" เพื่อส่งคำขอให้ผู้จัดการ", "KB-05"),
]


def rules_for(text: str, member_id: str | None = None) -> list[tuple[str, str]]:
    """(fact, source) for each rule the question touches; a verified member's own package counts too."""
    m = member(member_id)
    subject = f"{text} {m['package_id'] if m else ''}"
    return [(fact() if callable(fact) else fact, src) for pattern, fact, src in RULES if pattern.search(subject)]


def member_context(member_id: str | None) -> str:
    """What the bot may tell a verified member about themself. Phone number is never included."""
    m = member(member_id)
    if not m:
        return "ผู้ใช้ยังไม่ได้ยืนยันตัวตน ห้ามเปิดเผยข้อมูลสมาชิกรายบุคคล ถ้าถามเรื่องข้อมูลส่วนตัวให้ขอรหัสสมาชิกและเบอร์โทร 4 ตัวท้าย หรือให้กดยืนยันตัวตนบนหน้าเว็บ"
    pkg = next(p for p in table("packages") if p["id"] == m["package_id"])
    dues = [p for p in table("payments") if p["member_id"] == m["member_id"] and p["status"] in DUE]
    books = [b for b in table("bookings") if b["member_id"] == m["member_id"] and b["status"] == "booked"]
    lines = [
        f"สมาชิกที่ยืนยันตัวตนแล้ว: {m['member_id']} คุณ{m['first_name']}",
        f"แพ็กเกจ: {pkg['name_th']} ({pkg['name']}) สถานะ {m['status']}" + (" (สมัครจากหน้าเว็บ รอพนักงานยืนยันหลังได้รับชำระ)" if m["status"] == "pending" else "") + f" ใช้ได้ถึง {m['end_date']}" + (f" พักถึง {m['freeze_until']}" if m.get("freeze_until") else ""),
        f"แต้มสะสม: {m['points']} · PT คงเหลือ: {m['pt_sessions_left']} ครั้ง",
        "ยอดค้างชำระ: " + ("; ".join(f"{p['description']} {p['amount']:,.2f} บาท ครบกำหนด {p['due']}" for p in dues) or "ไม่มี"),
        f"คลาสที่จองไว้: {len(books)} รายการ",
    ]
    return "\n".join(lines)


USED_SLIP_REFS = {"DEMO2609010930Z9"}  # references already used before this system kept slips


def used_refs(payment_id: str) -> set[str]:
    """Slip references already used: the fixed list plus slips staff hold for other payments (the same slip sent again
    for the same payment is not a second use)."""
    return USED_SLIP_REFS | {s["reference"] for s in db.slips() if s["reference"] and s["payment_id"] != payment_id}
FAILED_TRANSFER = re.compile(r"ไม่สำเร็จ|ล้มเหลว|ถูกปฏิเสธ|\b(failed|unsuccessful|declined|rejected)\b", re.I)


def check_slip(slip: dict, member_id: str | None) -> dict:
    """The 6 checks from KB-06. The result is preliminary: only staff can mark a payment as paid (never the bot).
    A slip whose status says the transfer failed ("โอนเงินไม่สำเร็จ") never passes, whatever the 6 checks say."""
    m = member(member_id)
    if not m:
        return {"ok": False, "need_verify": True, "checks": [], "note": "ต้องยืนยันตัวตนก่อนจึงจะตรวจสลิปเทียบยอดค้างได้"}
    due = next((p for p in table("payments") if p["member_id"] == m["member_id"] and p["status"] in DUE), None)
    if not due:
        return {"ok": False, "checks": [], "note": "ไม่พบยอดค้างชำระที่รอสลิป ส่งต่อพนักงานตรวจสอบ"}
    bank = table("business")["bank"]
    amount = _num(slip.get("amount"))
    paid_on = _date(slip.get("datetime") or slip.get("date"))
    checks = [
        ("ชื่อบัญชีผู้รับเป็น " + bank["account_name"], _is_shop(slip.get("receiver_name"), bank["account_name"])),
        (f"ชื่อผู้โอนตรงกับสมาชิก (คุณ{m['first_name']})", _same_first_name(slip.get("sender_name"), m["first_name"])),
        ("เลขบัญชีผู้รับลงท้าย 4521-0", _digits(slip.get("receiver_account_last") or slip.get("receiver_account")).endswith("45210")),
        (f"ยอดเงินตรงกับยอดค้าง {due['amount']:,.2f} บาท", amount is not None and abs(amount - due["amount"]) < 0.01),
        ("วันที่โอนไม่เกิน 7 วันก่อนหรือหลังวันครบกำหนด", paid_on is not None and abs((paid_on - date.fromisoformat(due["due"])).days) <= 7),
        ("เลขอ้างอิงไม่เคยใช้มาก่อน", bool(slip.get("reference")) and slip["reference"] not in used_refs(due["id"])),
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
    result["note"] = (f"ผ่านครบ {len(checks)} ข้อ สถานะเป็น 'รอพนักงานยืนยัน' (ยังไม่ใช่ชำระแล้ว)" if result["ok"] else
                      ("สลิประบุว่าการโอนไม่สำเร็จ " if failed else "ไม่ผ่านบางข้อ ")
                      + "บอกลูกค้าว่าส่งให้พนักงานตรวจต่อแล้ว ไม่ต้องโอนซ้ำจนกว่าพนักงานติดต่อกลับ ให้พิมพ์ \"คุยกับพนักงาน\" ได้ ห้ามบอกว่าชำระสำเร็จ")
    return result


def _is_shop(receiver, account_name: str) -> bool:
    """The receiver is the shop: its Thai name without "บจก." or "X Fitness" in English. Exact, no fuzzy match: a
    look-alike name ("บจก. เฮ็กซ์ ฟิตเนส") is how a fake account would try to pass."""
    seen = _norm(receiver)
    return any(name in seen for name in (_norm(account_name).removeprefix("บจก"), "xfitness"))


def _same_first_name(sender, first_name: str) -> bool:
    """A word of the sender ("นาย ภาคิน ส.") is the member's first name — the surname is cut short on slips, so only
    the first name counts. One character may differ in names of 5 or more (OCR reads ธ as ฆ: "วรเมธ" → "วรเมฆ").
    A name in English cannot be compared: it fails and staff look."""
    words = re.split(r"[\s.]+", str(sender or "").lower())
    return any(w == first_name or (len(first_name) >= 5 and SequenceMatcher(None, w, first_name).ratio() >= 0.8) for w in words)


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
