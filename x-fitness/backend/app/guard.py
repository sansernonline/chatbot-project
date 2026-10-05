"""Guardrails checked in code, before and after the LLM — the system prompt is never the only safety layer.

Input rules answer with a fixed reply and the LLM is never called (same wording as the rules in frontend/index.html).
Output rules repair or replace an LLM answer that breaks a rule the prompt asked it to keep.
Rule codes (N-xx, D-xx) are the ones in docs/03_bot-rules.md; G-xx are output checks with no rule code there.
"""
import re
from functools import lru_cache

from . import business, config, keyword_search

QUICK = ["ราคาสมาชิก", "ตารางคลาส"]

# (rule codes, pattern, fixed reply, quick replies)
INPUT_RULES = [
    (["N-07", "N-08"], re.compile(r"(ignore|disregard|forget).{0,20}(instruction|previous|above)|ลืม.{0,10}(คำสั่ง|กฎ)|ไม่ต้องสน.{0,10}(คำสั่ง|กฎ)"
                                  r"|system\s*prompt|คำสั่งระบบ|prompt\s*ของคุณ|ได้รับคำสั่งอะไร|คุณคือ(แอดมิน|ผู้จัดการ|admin)|ตอนนี้คุณคือ"
                                  r"|jailbreak|developer mode|โหมดนักพัฒนา|ข้อความนี้มาจากผู้จัดการ|api\s*key"
                                  r"|คำต่อคำ|verbatim|(กฎ|คำสั่ง)(ที่คุณ|ที่)?(ได้รับ|ถูกตั้ง)|สรุปคำสั่ง|ถูกสั่งห้าม|สถานะผู้ใช้"
                                  r"|(your|hidden|system)\s*(instructions|rules|guidelines)|repeat.{0,30}(above|starts?\s*with)"
                                  r"|ข้อความ(ทั้งหมด)?ที่อยู่(เหนือ|ด้านบน)", re.I),
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
    (["N-10"], re.compile(r"หุ้น|คริปโต|bitcoin|การเมือง|เลือกตั้ง|หวย|การบ้าน|เขียนโค้ด|แปลภาษา|ดูดวง"
                          r"|ทำพาสปอร์ต|ทำวีซ่า|ขอวีซ่า|ราคาทอง|ราคาน้ำมัน|ค่าเงินบาท|พยากรณ์อากาศ|ผลบอล|แต่งกลอน|เรียงความ|สูตรอาหาร"
                          r"|^[\s\d.,]+(คูณ|หาร|บวก|ลบ|[x×*/+\-])[\s\d.,]+(ได้)?\s*(เท่า(ไหร่|ไร))?\s*(คะ|ครับ|ค่ะ)?\s*[?=]?\s*$", re.I),
     "ขออภัยค่ะ เอ็กซ์ตอบได้เฉพาะเรื่องของ X Fitness เช่น แพ็กเกจ คลาส เทรนเนอร์ และโปรโมชันค่ะ", QUICK),
]

PAID_CLAIM = re.compile(r"ชำระ(เงิน)?(สำเร็จ|เรียบร้อย(แล้ว)?|แล้ว)")              # N-05: only staff marks a payment as paid
PROMPT_LEAK = re.compile(r"## (ต้องทำ|ห้ามทำ|สถานะผู้ใช้|ข้อมูลอ้างอิง)")           # N-07: answer quotes the system prompt
HEALTH_VERDICT = re.compile(r"\s*\(?\s*(ซึ่ง)?(ถือว่า)?(อยู่ใน|สูงกว่า|ต่ำกว่า|เกิน)\s*(ค่า)?\s*(เกณฑ์|มาตรฐาน)(ปกติ|มาตรฐาน)?\s*\)?"
                            r"|ถือว่า(อ้วน|ผอม|ปกติ|น่าเป็นห่วง)|ควรอยู่(ที่|ระหว่าง)")   # N-06: no medical judgement
MEASURE = re.compile(r"(?<![\d,.])(\d[\d,]*(?:\.\d+)?)\s*(?:%|เปอร์เซ็นต์|kg\b|กก\.?|กิโลกรัม|kcal|กิโลแคลอรี)", re.I)
PHONE = re.compile(r"(?<!\d)0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}(?!\d)")
BANK_ACCOUNT = re.compile(r"(?<!\d)\d{3}-\d-\d{5}-\d(?!\d)")
MONEY = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*บาท")
URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"']+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|co\.th|in\.th|th|io|app)\b", re.I)
TIME = re.compile(r"(?<![\d,.])([01]?\d|2[0-3])[:.]([0-5]\d)(?![\d.])")
SAFE_REPLY = "ขออภัยค่ะ เอ็กซ์ตอบเรื่องนี้ไม่ได้ พิมพ์ \"คุยกับพนักงาน\" หรือโทร 038-000-888 ได้เลยค่ะ"


def check_input(text: str) -> dict | None:
    """A fixed reply when the message breaks an input rule, else None (go on to the LLM).
    Also checked with the spaces taken out: "s y s t e m p r o m p t" slipped past the patterns."""
    squeezed = re.sub(r"\s+", "", text)
    for rules, pattern, answer, quick in INPUT_RULES:
        if pattern.search(text) or pattern.search(squeezed):
            return {"answer": answer, "sources": [], "rules": rules, "actions": quick}
    return None


def check_output(answer: str, known: str = "") -> tuple[str, list[str]]:
    """The answer with rule-breaking parts fixed, plus the codes of the rules that fired.

    known = what the LLM was given (member data, slip check, …). Every baht amount in the answer must appear there
    or anywhere in the knowledge base, otherwise the LLM made the number up (G-NUM). Same for web addresses (G-URL)
    and clock times (G-TIME): the LLM invented a shop website and a 05:00 opening time."""
    shop = business.table("business")
    if PROMPT_LEAK.search(answer) or _leaked(answer):
        return SAFE_REPLY, ["N-07"]
    if known and any(_num(n) not in _numbers(known) | _kb_numbers() for n in MONEY.findall(answer) + MEASURE.findall(answer)):
        return SAFE_REPLY, ["G-NUM"]                                        # baht, %, kg, kcal: a body scan once came back invented
    if known and any(_url(u) not in _url(known + " " + _kb_text()) for u in URL.findall(answer)):
        return SAFE_REPLY, ["G-URL"]
    if known and any(_time(m) not in _times(known + " " + _kb_text()) for m in TIME.findall(answer)):
        return SAFE_REPLY, ["G-TIME"]
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


def _leaked(answer: str) -> bool:
    """The answer repeats two or more sentences of the system prompt (paraphrased lists slipped past PROMPT_LEAK).

    A sentence counts as repeated when 60% of its 12-character runs appear in the answer. One sentence alone is not a leak:
    a refusal may echo "ห้ามเปิดเผยข้อมูลของสมาชิกคนอื่น"."""
    text = _squeeze(answer)
    runs = {text[i:i + 12] for i in range(len(text) - 11)}
    return sum(len(grams & runs) >= 0.6 * len(grams) for grams in _secret_sentences()) >= 2


@lru_cache(maxsize=1)
def _secret_sentences() -> list[set[str]]:
    """12-character runs of each sentence of the system prompt and of the not-verified notice, quoted replies left out
    (the bot is meant to say "เอ็กซ์ยังไม่มีข้อมูลเรื่องนี้ค่ะ" and "คุยกับพนักงาน")."""
    system = (config.PROMPTS_DIR / "system.md").read_text(encoding="utf-8").split("## ข้อมูลอ้างอิง")[0]
    text = re.sub(r'"[^"]*"|\{\w+\}', " ", system + "\n" + business.member_context(None))
    sentences = [_squeeze(s) for s in re.split(r"\s{1,}", text)]
    return [{s[i:i + 12] for i in range(len(s) - 11)} for s in sentences if len(s) >= 16]


def _squeeze(text: str) -> str:
    return re.sub(r"[\s\"'“”()\-–:·,.]+", "", text.lower())


def _num(text: str) -> str:
    """'1,290.00' → '1290' so the same amount written differently still matches."""
    n = text.replace(",", "")
    return n.split(".")[0] if n.endswith((".0", ".00")) else n


def _numbers(text: str) -> set[str]:
    return {_num(n) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def _kb_text() -> str:
    return " ".join(c.text for c in keyword_search.index().chunks)            # index() is cached, cleared on reindex


def _kb_numbers() -> set[str]:
    return _numbers(_kb_text())


def _url(text: str) -> str:
    """'https://www.X.com/.' → 'x.com/' so a link written with or without scheme/www still matches."""
    return re.sub(r"https?://|www\.", "", text.lower()).rstrip(".,")


def _time(hm: tuple[str, str]) -> str:
    return f"{int(hm[0]):02d}:{hm[1]}"


def _times(text: str) -> set[str]:
    return {_time(m) for m in TIME.findall(text)}
