"""Guardrails checked in code, before and after the LLM — the system prompt is never the only safety layer.

Input rules answer with a fixed reply and the LLM is never called (same wording as the rules in frontend/index.html).
Output rules repair or replace an LLM answer that breaks a rule the prompt asked it to keep.
Rule codes (N-xx, D-xx) are the ones in docs/03_bot-rules.md; G-xx are output checks with no rule code there.
"""
import re

from . import business, keyword_search

QUICK = ["ราคาสมาชิก", "ตารางคลาส"]

# (rule codes, pattern, fixed reply, quick replies)
INPUT_RULES = [
    (["N-07", "N-08"], re.compile(r"(ignore|disregard|forget).{0,20}(instruction|previous|above)|ลืม.{0,10}(คำสั่ง|กฎ)|ไม่ต้องสน.{0,10}(คำสั่ง|กฎ)"
                                  r"|system\s*prompt|คำสั่งระบบ|prompt\s*ของคุณ|ได้รับคำสั่งอะไร|คุณคือ(แอดมิน|ผู้จัดการ|admin)|ตอนนี้คุณคือ"
                                  r"|jailbreak|developer mode|โหมดนักพัฒนา|ข้อความนี้มาจากผู้จัดการ|api\s*key", re.I),
     "ขออภัยค่ะ เอ็กซ์ไม่สามารถเปิดเผยหรือเปลี่ยนคำสั่งการทำงานได้ และไม่รับคำสั่งที่อ้างว่ามาจากผู้ดูแลผ่านแชต ถ้าต้องการสอบถามเรื่องสมาชิกหรือคลาส ยินดีช่วยค่ะ", QUICK),
    (["D-07", "N-06"], re.compile(r"เจ็บหน้าอก|แน่นหน้าอก|หน้ามืด|เวียนหัว|หายใจไม่ออก"),
     "ถ้ามีอาการเจ็บหน้าอก เวียนศีรษะ หรือหายใจไม่ออก ให้หยุดออกกำลังกายทันทีและพบแพทย์ค่ะ กรณีฉุกเฉินโทร 1669 "
     "ในยิมมีเครื่อง AED ที่เคาน์เตอร์ และพนักงานผ่านการอบรมปฐมพยาบาล", []),
    (["N-06"], re.compile(r"สเตียรอยด์|steroid|ฮอร์โมน|ยาลด|ยาเผาผลาญ|ยากระตุ้น|ยาชุด|sarm|clen|ฉีด", re.I),
     "เอ็กซ์ไม่สามารถแนะนำยา สเตียรอยด์ ฮอร์โมน หรือสารเสริมประสิทธิภาพได้ค่ะ เพราะอาจเป็นอันตรายต่อสุขภาพ กรุณาปรึกษาแพทย์ "
     "ถ้าอยากเพิ่มกล้ามเนื้ออย่างปลอดภัย โค้ชตั้มถนัดด้านเวทเทรนนิ่งค่ะ", ["ราคา PT 10 ครั้ง"]),
    (["N-06"], re.compile(r"กินอะไร|แผนอาหาร|คุมอาหาร|ลด.{0,6}\d+\s*(กิโล|kg).{0,10}(อาทิตย์|สัปดาห์|วัน)|อดอาหาร|ควรกินกี่แคล", re.I),
     "เอ็กซ์ไม่สามารถกำหนดแผนอาหารหรือเป้าลดน้ำหนักเร่งด่วนได้ค่ะ แนะนำปรึกษาแพทย์หรือนักกำหนดอาหาร "
     "ส่วนการออกกำลังกาย โค้ชเก่งถนัดโปรแกรมลดไขมันค่ะ", ["คลาสเผาผลาญเยอะ", "ราคา PT"]),
    (["N-04"], re.compile(r"(เบอร์|วันหมดอายุ|แต้ม|ที่อยู่|ยอดค้าง).{0,15}(ของ(?!ฉัน|ผม|หนู|เรา|ร้าน|ตัวเอง)|สมาชิก\s*FN)|ใครเป็นสมาชิก|รายชื่อสมาชิก|(แฟน|เพื่อน|พี่|น้อง).{0,20}เป็นสมาชิก(ที่นี่)?(ไหม|หรือเปล่า|รึเปล่า|มั้ย)", re.I),
     "ขออภัยค่ะ เอ็กซ์ไม่สามารถเปิดเผยหรือยืนยันข้อมูลของสมาชิกคนอื่นได้ รวมถึงไม่บอกว่าใครเป็นสมาชิกหรือไม่ "
     "ถ้าเป็นข้อมูลของคุณเอง กรุณายืนยันตัวตนด้วยรหัสสมาชิกและเบอร์โทร 4 ตัวท้ายค่ะ", []),
    (["N-10"], re.compile(r"หุ้น|คริปโต|bitcoin|การเมือง|เลือกตั้ง|หวย|การบ้าน|เขียนโค้ด|แปลภาษา|ดูดวง", re.I),
     "ขออภัยค่ะ เอ็กซ์ตอบได้เฉพาะเรื่องของ X Fitness เช่น แพ็กเกจ คลาส เทรนเนอร์ และโปรโมชันค่ะ", QUICK),
]

PAID_CLAIM = re.compile(r"ชำระ(เงิน)?(สำเร็จ|เรียบร้อย(แล้ว)?|แล้ว)")              # N-05: only staff marks a payment as paid
PROMPT_LEAK = re.compile(r"## (ต้องทำ|ห้ามทำ|สถานะผู้ใช้|ข้อมูลอ้างอิง)")           # N-07: answer quotes the system prompt
HEALTH_VERDICT = re.compile(r"\s*\(?\s*(ซึ่ง)?(อยู่ใน|สูงกว่า|ต่ำกว่า|เกิน)\s*เกณฑ์(ปกติ|มาตรฐาน)?\s*\)?")   # N-06: no medical judgement
PHONE = re.compile(r"(?<!\d)0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}(?!\d)")
BANK_ACCOUNT = re.compile(r"(?<!\d)\d{3}-\d-\d{5}-\d(?!\d)")
MONEY = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*บาท")
SAFE_REPLY = "ขออภัยค่ะ เอ็กซ์ตอบเรื่องนี้ไม่ได้ พิมพ์ \"คุยกับพนักงาน\" หรือโทร 038-000-888 ได้เลยค่ะ"


def check_input(text: str) -> dict | None:
    """A fixed reply when the message breaks an input rule, else None (go on to the LLM)."""
    for rules, pattern, answer, quick in INPUT_RULES:
        if pattern.search(text):
            return {"answer": answer, "sources": [], "rules": rules, "actions": quick}
    return None


def check_output(answer: str, known: str = "") -> tuple[str, list[str]]:
    """The answer with rule-breaking parts fixed, plus the codes of the rules that fired.

    known = what the LLM was given (member data, slip check, …). Every baht amount in the answer must appear there
    or anywhere in the knowledge base, otherwise the LLM made the number up (G-NUM)."""
    shop = business.table("business")
    if PROMPT_LEAK.search(answer):
        return SAFE_REPLY, ["N-07"]
    if known and any(_num(n) not in _numbers(known) | _kb_numbers() for n in MONEY.findall(answer)):
        return SAFE_REPLY, ["G-NUM"]
    if any(acc != shop["bank"]["account_no"] for acc in BANK_ACCOUNT.findall(answer)):
        return SAFE_REPLY, ["G-BANK"]                                       # not the shop's account: never send it
    rules = []
    if PAID_CLAIM.search(answer):
        answer, rules = PAID_CLAIM.sub("รอพนักงานยืนยันการชำระ", answer), rules + ["N-05"]
    if HEALTH_VERDICT.search(answer):
        answer, rules = HEALTH_VERDICT.sub("", answer), rules + ["N-06"]
    masked = PHONE.sub(lambda m: m.group(0) if m.group(0) == shop["phone"] else "0xx-xxx-xxxx", answer)
    if masked != answer:
        answer, rules = masked, rules + ["N-04"]
    return answer, rules


def _num(text: str) -> str:
    """'1,290.00' → '1290' so the same amount written differently still matches."""
    n = text.replace(",", "")
    return n.split(".")[0] if n.endswith((".0", ".00")) else n


def _numbers(text: str) -> set[str]:
    return {_num(n) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def _kb_numbers() -> set[str]:
    return _numbers(" ".join(c.text for c in keyword_search.index().chunks))   # index() is cached, cleared on reindex
