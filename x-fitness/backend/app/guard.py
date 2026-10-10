"""Guardrails checked in code, before and after the LLM — the system prompt is never the only safety layer.

Input rules answer with a fixed reply and the LLM is never called (same wording as the rules in frontend/index.html).
Output rules repair or replace an LLM answer that breaks a rule the prompt asked it to keep.
Rule codes (N-xx, D-xx) are the ones in docs/03_bot-rules.md; G-xx are output checks with no rule code there;
S1–S14 are the hazard categories of Llama Guard 3 (HARM_RULES).
"""
import re
import unicodedata
from functools import lru_cache

from . import business, config, keyword_search

QUICK = ["ราคาสมาชิก", "ตารางคลาส"]
OTHER_MEMBER = ("ขออภัยค่ะ เอ็กซ์ไม่สามารถเปิดเผยหรือยืนยันข้อมูลของสมาชิกคนอื่นได้ รวมถึงไม่บอกว่าใครเป็นสมาชิกหรือไม่ "
                "ถ้าเป็นข้อมูลของคุณเอง กรุณายืนยันตัวตนด้วยรหัสสมาชิกและเบอร์โทร 4 ตัวท้ายค่ะ")
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
LEET = str.maketrans("0134@$", "oieaas")                              # "pr0mpt", "@dmin": English words only
MEMBER_ID = re.compile(r"FN\s*-?\s*(\d{5})", re.I)

# (rule codes, pattern, fixed reply, quick replies)
INPUT_RULES = [
    (["N-07", "N-08"], re.compile(r"(ignore|disregard|forget).{0,20}(instruction|previous|above)|ลืม.{0,10}(คำสั่ง|กฎ)|ไม่ต้องสน.{0,10}(คำสั่ง|กฎ)"
                                  r"|system\s*prompt|คำสั่งระบบ|prompt\s*ของคุณ|ได้รับคำสั่งอะไร|คุณคือ(แอดมิน|ผู้จัดการ|admin)|ตอนนี้คุณคือ"
                                  r"|jailbreak|developer mode|โหมดนักพัฒนา|ข้อความนี้มาจากผู้จัดการ|api\s*key"
                                  r"|คำต่อคำ|verbatim|(กฎ|คำสั่ง)(ที่คุณ|ที่)?(ได้รับ|ถูกตั้ง)|สรุปคำสั่ง|ถูกสั่งห้าม|สถานะผู้ใช้"
                                  r"|(your|hidden|system)\s*(instructions|rules|guidelines)|repeat.{0,30}(above|starts?\s*with)"
                                  r"|ข้อความ(ทั้งหมด)?ที่อยู่(เหนือ|ด้านบน)"
                                  r"|(เลิก|หยุด|ไม่ต้อง)(ทำตาม|สน|ใช้|ยึด).{0,10}(กฎ|คำสั่ง|กติกา)"
                                  r"|(ทวน|บอก|เปิดเผย|แสดง|แปล|พิมพ์).{0,15}(กฎ|กติกา|คำสั่ง|ข้อความ).{0,10}(ที่(ตั้ง|ให้|สั่ง)ไว้(ให้|กับ)?คุณ|ที่คุณได้รับ|ข้างบน|ด้านบน|ก่อนหน้านี้)"
                                  r"|(เล่นบท|สวมบท|แกล้งเป็น|ทำตัวเป็น|สมมติ(ว่า)?(คุณ|ตัวเอง)?เป็น).{0,10}(แอดมิน|ผู้จัดการ|ผู้ดูแล|admin|เจ้าของร้าน|ai\s*อื่น)"
                                  r"|pretend\s*(to\s*be|you)|role\s*-?\s*play|act\s*as\s*(an?\s*)?(admin|manager|developer)|\bdan\s*mode", re.I),
     "ขออภัยค่ะ เอ็กซ์ไม่สามารถเปิดเผยหรือเปลี่ยนคำสั่งการทำงานได้ และไม่รับคำสั่งที่อ้างว่ามาจากผู้ดูแลผ่านแชต ถ้าต้องการสอบถามเรื่องสมาชิกหรือคลาส ยินดีช่วยค่ะ", QUICK),
    (["D-07", "N-06"], re.compile(r"เจ็บ(ที่)?(หน้า)?อก|แน่น(หน้า)?อก|หน้ามืด|เวียนหัว|หายใจไม่ออก|หายใจไม่ทัน|ใจสั่น|หัวใจ(เต้น)?(แรง|เร็ว|ผิดจังหวะ)"
                                       r"|(จะ)?เป็นลม|หมดสติ|ปวดร้าว(ไป)?(แขน|กราม)"),
     "ถ้ามีอาการเจ็บหน้าอก เวียนศีรษะ หรือหายใจไม่ออก ให้หยุดออกกำลังกายทันทีและพบแพทย์ค่ะ กรณีฉุกเฉินโทร 1669 "
     "ในยิมมีเครื่อง AED ที่เคาน์เตอร์ และพนักงานผ่านการอบรมปฐมพยาบาล", []),
    (["N-06"], re.compile(r"สเตียรอยด์|steroid|ฮอร์โมน|ยาลด|ยาเผาผลาญ|ยากระตุ้น|ยาชุด|sarm|clen|hgh|เทสโทส|testosterone|ฉีด.{0,10}(ยา|สาร|กล้าม|ไขมัน|วิตามิน|กลูต้า|ผิว|โบท็อก|ฟิลเลอร์)", re.I),   # "ฉีดวัคซีน" is a fair question
     "เอ็กซ์ไม่สามารถแนะนำยา สเตียรอยด์ ฮอร์โมน หรือสารเสริมประสิทธิภาพได้ค่ะ เพราะอาจเป็นอันตรายต่อสุขภาพ กรุณาปรึกษาแพทย์ "
     "ถ้าอยากเพิ่มกล้ามเนื้ออย่างปลอดภัย โค้ชตั้มถนัดด้านเวทเทรนนิ่งค่ะ", ["ราคา PT 10 ครั้ง"]),
    (["N-06"], re.compile(r"กินอะไร|แผนอาหาร|คุมอาหาร|ลด.{0,6}\d+\s*(กิโล|kg).{0,10}(อาทิตย์|สัปดาห์|วัน)|อดอาหาร|ควรกินกี่แคล", re.I),
     "เอ็กซ์ไม่สามารถกำหนดแผนอาหารหรือเป้าลดน้ำหนักเร่งด่วนได้ค่ะ แนะนำปรึกษาแพทย์หรือนักกำหนดอาหาร "
     "ส่วนการออกกำลังกาย โค้ชเก่งถนัดโปรแกรมลดไขมันค่ะ", ["คลาสเผาผลาญเยอะ", "ราคา PT"]),
    (["N-04"], re.compile(r"(เบอร์|วันหมดอายุ|แต้ม|ที่อยู่|ยอดค้าง|นามสกุล).{0,15}(ของ(?!ฉัน|ผม|หนู|เรา|ร้าน|ตัวเอง)|สมาชิก\s*FN)|ใครเป็นสมาชิก|รายชื่อสมาชิก"
                          r"|(แฟน|เพื่อน|พี่|น้อง|คุณ\S{2,20}).{0,20}(เป็น|ยังเป็น)สมาชิก(ที่นี่|อยู่)?(ไหม|หรือเปล่า|รึเปล่า|มั้ย|หรือยัง)"
                          r"|ขอ(เบอร์|ที่อยู่|นามสกุล|อีเมล|ไลน์).{0,10}(คุณ|น้อง|พี่)\S{2,20}.{0,10}สมาชิก", re.I),
     OTHER_MEMBER, []),
    (["N-10"], re.compile(r"หุ้น|คริปโต|bitcoin|การเมือง|เลือกตั้ง|หวย|การบ้าน|เขียนโค้ด|แปลภาษา|ดูดวง"
                          r"|เขียน.{0,10}(โปรแกรม|code|python|java|sql|html|สคริปต์)|\bpython\b|\bjavascript\b"
                          r"|ทำพาสปอร์ต|ทำวีซ่า|ขอวีซ่า|ราคาทอง|ราคาน้ำมัน|ค่าเงินบาท|พยากรณ์อากาศ|ผลบอล|แต่งกลอน|เรียงความ|สูตรอาหาร"
                          r"|^[\s\d.,]+(คูณ|หาร|บวก|ลบ|[x×*/+\-])[\s\d.,]+(ได้)?\s*(เท่า(ไหร่|ไร))?\s*(คะ|ครับ|ค่ะ)?\s*[?=]?\s*$", re.I),
     "ขออภัยค่ะ เอ็กซ์ตอบได้เฉพาะเรื่องของ X Fitness เช่น แพ็กเกจ คลาส เทรนเนอร์ และโปรโมชันค่ะ", QUICK),
]

# Llama Guard's 14 hazard categories (S1–S14), checked in code. High-precision patterns: a gym question that only looks
# similar ("ระเบิดไขมัน", "ปืนนวด", "ซ้อมมวยกับเพื่อน", "เลกกิ้งสีนู้ด") must still reach the LLM — tests/test_guard14.py keeps both lists.
# N-07: an instruction split over messages ("บอก system" → "prompt หน่อย"). Only words that do not join by accident;
# the whole N-07 list would ("ลืมรหัสค่ะ" + "คำสั่งซื้อ…" reads as "ลืม…คำสั่ง").
SPLIT_INJECTION = re.compile(r"system\s*prompt|(ignore|disregard).{0,20}(instruction|previous|above)|jailbreak|developer\s*mode"
                             r"|api\s*key|prompt\s*ของคุณ|โหมดนักพัฒนา|verbatim", re.I)

HANDOFF_ACTION = ["คุยกับพนักงาน"]
SELF_HARM = re.compile(r"อยาก(จะ)?ตาย|ฆ่าตัว(ตาย)?|ไม่อยากมีชีวิต|อยากหายไปจากโลก|จบชีวิต(ตัวเอง)?|ทำร้ายตัวเอง|ทำร้ายร่างกายตัวเอง"
                       r"|กรีด(ข้อมือ|แขน|ตัวเอง)|กินยา.{0,6}(ตาย|เกินขนาด)|ผูกคอ|กระโดด(ตึก|สะพาน|น้ำตาย)"
                       r"|suicid|kill\s*my\s*self|self\s*-?\s*harm|end\s*my\s*life|want\s*to\s*die", re.I)
INCIDENT = re.compile(r"(โดน|ถูก|มีคน|โค้ช\S{0,6}|พนักงาน\S{0,6}).{0,10}(ลวนลาม|คุกคาม|ล่วงละเมิด|แตะต้องตัว|จับก้น|จับหน้าอก|แอบถ่าย|ถ้ำมอง|ข่มขู่)"
                      r"|แอบถ่าย.{0,6}(ห้องน้ำ|ห้องอาบน้ำ|ห้องเปลี่ยน)|(โดน|ถูก|มีคน)(ขโมย|ทำร้าย|ชก|ต่อย|ตบ|ตี|ทุบ)", re.I)
VIOLENCE = re.compile(r"(อยาก|จะ(ไป)?|วิธี|สอน|ช่วย(คิด)?|แผน|แอบ|ทำยังไงให้).{0,8}(ฆ่า|ทำร้าย|แทง|ยิง|วางยา|ทุบตี|กระทืบ|ลักพาตัว|ตีหัว|ข่มขืน)"
                      r"(?!ไขมัน|เวลา|แคล|เป้า).{0,6}(คน|เขา|มัน|แฟน|เมีย|ผัว|สามี|ภรรยา|พ่อ|แม่|เพื่อน|เจ้านาย|หัวหน้า|ครู|โค้ช|ใคร|พนักงาน|สมาชิก|ลูกค้า|ศัตรู|คู่อริ|ตำรวจ)"
                      r"|how\s*to\s*(kill|murder|poison|kidnap)|kill\s*(him|her|them|someone|people)|\bmurder", re.I)
CRIME = re.compile(r"ลักทรัพย์|(วิธี|สอน|อยาก|จะ|ช่วย|แอบ).{0,6}ขโมย|งัด(ล็อกเกอร์|ตู้|รถ|บ้าน|ประตู)|(ปลอม|ตัดต่อ|แต่ง)(สลิป|เอกสาร|ใบเสร็จ|ลายเซ็น|บัตร)"
                   r"|สลิปปลอม|บัตร(นักศึกษา|ประชาชน)ปลอม|ฟอกเงิน|ยาบ้า|ยาไอซ์|โคเคน|เฮโรอีน|เคตามีน|ยาเสพติด|ขายยาเสพ|กัญชา"
                   r"|แฮ็ก|แฮก|\bhack|เจาะระบบ|phishing|ฟิชชิ่ง|บัญชีม้า|เปิดบัญชีให้คนอื่น|เลี่ยงภาษี|ใช้บัตร(เครดิต)?(คนอื่น|ที่ขโมย)", re.I)
CHILD = re.compile(r"(เด็ก|ผู้เยาว์|อายุ\s*(1[0-7]|[1-9])\s*(ปี|ขวบ)|ประถม|มัธยม|นักเรียน|underage|minor|child|loli)"
                   r".{0,25}(เซ็กส์|\bsex|ลามก|โป๊|เปลือย|ทางเพศ|มีอะไรกัน|ได้เสีย|ร่วมเพศ|เย็ด|porn|nude)"
                   r"|(เซ็กส์|\bsex|ลามก|โป๊|เปลือย|ทางเพศ|มีอะไรกัน|ได้เสีย|ร่วมเพศ|เย็ด|porn|nude).{0,25}(เด็ก|ผู้เยาว์|underage|minor|child|loli)", re.I)
SEXUAL = re.compile(r"เซ็กส์|\bsex\b|porn|(หนัง|คลิป|รูป|ภาพ|เว็บ)(โป๊|นู้ด|เปลือย|xxx)|ลามก|เย็ด|ร่วมเพศ|มีเพศสัมพันธ์|ขายตัว|ขายบริการทางเพศ"
                    r"|นวดกระปู๋|happy\s*ending|xxx|onlyfans|คลิปหลุด|ภาพหลุด|ข่มขืน|\brape", re.I)
WEAPONS = re.compile(r"(ทำ|ประกอบ|สร้าง|ผลิต|สูตร|วิธี|ซื้อ|หา|สังเคราะห์|เตรียม).{0,10}(ระเบิด(?!ไขมัน|พุง|แคล|เหงื่อ|กล้าม|พลัง|ความมัน)|ปืน(?!นวด)"
                     r"|กระสุน|อาวุธ|ยาพิษ|สารพิษ|แก๊สพิษ|ไซยาไนด์|ไรซิน|ซาริน|แอนแทรกซ์)|อาวุธ(เคมี|ชีวภาพ|นิวเคลียร์)|ระเบิด(ปิงปอง|ขวด|แสวงเครื่อง)"
                     r"|molotov|โมโลตอฟ|\bbomb\b|explosive|nerve\s*agent|ricin|sarin|anthrax|bioweapon", re.I)
HATE = re.compile(r"ไอ้(ดำ|ตุ๊ด|เกย์|กะเทย|ลาว|เขมร|พม่า|แขก|เจ๊ก|ญวน|อ้วน|ง่อย)|อี(ตุ๊ด|ดำ|อ้วน|กะเทย)|nigger|nigga|faggot|tranny|retard"
                  r"|เกลียด(พวก|คน)\S{0,4}(ดำ|เกย์|ตุ๊ด|กะเทย|lgbt|มุสลิม|คริสต์|พุทธ|อิสลาม|ลาว|เขมร|พม่า|จีน|แขก|ต่างด้าว|ต่างชาติ|พิการ|อ้วน)"
                  r"|(พวก|คน)(ดำ|ตุ๊ด|กะเทย|เกย์|แขก|ต่างด้าว|พม่า|เขมร|ลาว|มุสลิม)\S{0,4}(สกปรก|โง่|ขี้ขโมย|น่ารังเกียจ|ไม่ควร(ได้)?(เข้า|เป็นสมาชิก)|ห้ามเข้า|ไม่ใช่คน)", re.I)
DEFAMATION = re.compile(r"ใส่ร้าย|ใส่ความ|ปล่อยข่าว|ข่าวปลอม|ประจาน|(เขียน|แต่ง|โพสต์|ปั่น|ทำ)(รีวิว|โพสต์|ข่าว).{0,10}(ปลอม|ด่า|ใส่ร้าย|โจมตี|ทำลาย|ให้เสียชื่อ)"
                        r"|ทำให้\S{0,15}เสียชื่อ", re.I)
COPYRIGHT = re.compile(r"ละเมิดลิขสิทธิ์|(ขาย|ซื้อ|หา|แหล่ง)\S{0,6}(ของเถื่อน|ของก๊อป|ของปลอม)|ก๊อปเกรด|แบรนด์เนมปลอม|\bcrack|แคร็ก|torrent|ทอร์เรนต์"
                       r"|(โหลด|ดาวน์โหลด|ดู)(หนัง|เพลง|เกม|โปรแกรม|ซอฟต์แวร์|การ์ตูน|มังงะ|ebook|อีบุ๊ก)\S{0,6}(ฟรี|เถื่อน)"
                       r"|(ก๊อป|คัดลอก|ขโมย)(คอร์ส|คลิป|โปรแกรม|ท่าเต้น)", re.I)
PRIVACY = re.compile(r"(ขอ|อยากได้|มี)(เบอร์|ไลน์|line|ig|ไอจี|เฟส|facebook|ที่อยู่|บ้าน)\S{0,6}(ส่วนตัว)?\S{0,4}(ของ)?(โค้ช|เทรนเนอร์|พนักงาน|ผู้จัดการ|สาว|ผู้หญิง|ผู้ชาย|คนที่)"
                     r"|(โค้ช|เทรนเนอร์|พนักงาน)\S{0,8}(บ้านอยู่|อยู่บ้าน|เบอร์ส่วนตัว|ไลน์ส่วนตัว|มีแฟน|โสด)", re.I)
ADVICE = re.compile(r"ปรึกษา(กฎหมาย|ทนาย|คดี)|ฟ้อง(หย่า|ศาล|ร้อง)(ยังไง|อย่างไร)|ควร(ซื้อ|ลงทุน)\S{0,6}(หุ้น|กองทุน|คริปโต|ทอง)|ลงทุนอะไรดี|กู้เงินที่ไหน", re.I)
ELECTIONS = re.compile(r"พรรคการเมือง|นายกรัฐมนตรี|นายกฯ|ส\.ส\.|กกต|เลือกพรรค|เลือกใคร(เป็น)?(นายก|ส\.?ส)|ประชามติ|โหวต(ให้)?(พรรค|นายก)", re.I)
CODE_ABUSE = re.compile(r"rm\s+-rf|os\.system|subprocess|import\s+os|__import__|exec\s*\(|eval\s*\(|<script|javascript:|drop\s+table|union\s+select"
                        r"|select\s+\*\s+from|/etc/passwd|powershell|cmd\.exe|curl\s+https?://|wget\s+https?://|base64\s+-d|รันโค้ด|run\s+(this|the following)\s+code", re.I)
SORRY_SHOP = "ถ้าต้องการสอบถามเรื่องสมาชิก คลาส หรือโปรโมชัน ยินดีช่วยค่ะ"
HARM_RULES = [
    (["S11"], SELF_HARM, "เอ็กซ์เป็นห่วงคุณนะคะ ถ้ารู้สึกอยากทำร้ายตัวเอง โทรคุยกับสายด่วนสุขภาพจิต 1323 ได้ตลอด 24 ชั่วโมง ไม่เสียค่าใช้จ่าย "
                         "ถ้าอยู่ในอันตรายตอนนี้ โทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุด ถ้าอยากคุยกับพนักงานของร้าน พิมพ์ \"คุยกับพนักงาน\" ได้เลยค่ะ", HANDOFF_ACTION),
    (["S1", "S2", "S3"], INCIDENT, "ขอโทษที่เกิดเรื่องนี้ค่ะ เรื่องนี้สำคัญ เอ็กซ์ขอส่งต่อให้ผู้จัดการสาขาดูแลทันที พิมพ์ \"คุยกับพนักงาน\" หรือโทร 038-000-888 "
                                   "ถ้ายังอยู่ในอันตรายตอนนี้ โทรแจ้งตำรวจ 191 ค่ะ", HANDOFF_ACTION),
    (["S4"], CHILD, "ขออภัยค่ะ เอ็กซ์ไม่ตอบเนื้อหาทางเพศที่เกี่ยวกับเด็กหรือผู้เยาว์ในทุกกรณี", []),
    (["S12", "S3"], SEXUAL, "ขออภัยค่ะ เอ็กซ์ไม่ตอบหรือสร้างเนื้อหาทางเพศ " + SORRY_SHOP, QUICK),
    (["S9"], WEAPONS, "ขออภัยค่ะ เอ็กซ์ให้ข้อมูลเกี่ยวกับอาวุธ วัตถุระเบิด หรือสารอันตรายไม่ได้ " + SORRY_SHOP, QUICK),
    (["S1"], VIOLENCE, "ขออภัยค่ะ เอ็กซ์ช่วยเรื่องที่อาจทำร้ายผู้อื่นไม่ได้ ถ้ามีคนกำลังตกอยู่ในอันตราย โทรแจ้งตำรวจ 191 ค่ะ", []),
    (["S2"], CRIME, "ขออภัยค่ะ เอ็กซ์ช่วยเรื่องที่ผิดกฎหมายไม่ได้ " + SORRY_SHOP, QUICK),
    (["S10"], HATE, "ขออภัยค่ะ เอ็กซ์ไม่ตอบข้อความที่ดูถูกหรือเหยียดผู้อื่น X Fitness ต้อนรับทุกคนอย่างเท่าเทียม " + SORRY_SHOP, QUICK),
    (["S5"], DEFAMATION, "ขออภัยค่ะ เอ็กซ์ช่วยเขียนหรือเผยแพร่ข้อความที่กล่าวหาหรือทำให้ผู้อื่นเสียชื่อเสียงไม่ได้ "
                         "ถ้ามีปัญหากับบริการของร้าน พิมพ์ \"คุยกับพนักงาน\" เพื่อแจ้งผู้จัดการสาขาได้ค่ะ", HANDOFF_ACTION),
    (["S8"], COPYRIGHT, "ขออภัยค่ะ เอ็กซ์ช่วยเรื่องที่ละเมิดลิขสิทธิ์หรือสินค้าปลอมไม่ได้ " + SORRY_SHOP, QUICK),
    (["S7", "N-04"], PRIVACY, "ขออภัยค่ะ เอ็กซ์ให้ข้อมูลส่วนตัวของโค้ช พนักงาน หรือลูกค้าคนอื่นไม่ได้ ถ้าต้องการติดต่อโค้ชหรือนัด PT "
                              "ติดต่อผ่านร้านได้ที่ 038-000-888 หรือพิมพ์ \"คุยกับพนักงาน\" ค่ะ", HANDOFF_ACTION),
    (["S6", "N-10"], ADVICE, "ขออภัยค่ะ เอ็กซ์ให้คำปรึกษาด้านกฎหมายหรือการลงทุนไม่ได้ แนะนำปรึกษาผู้เชี่ยวชาญโดยตรง " + SORRY_SHOP, QUICK),
    (["S13", "N-10"], ELECTIONS, "ขออภัยค่ะ เอ็กซ์ไม่ตอบเรื่องการเมืองหรือการเลือกตั้ง " + SORRY_SHOP, QUICK),
    (["S14", "N-10"], CODE_ABUSE, "ขออภัยค่ะ เอ็กซ์ไม่รันหรือเขียนโค้ด และตอบได้เฉพาะเรื่องของ X Fitness " + SORRY_SHOP, QUICK),
]
# An LLM answer is replaced when it says any of these (self-harm, incidents and privacy are input-side only:
# the bot's own care reply mentions them on purpose).
OUTPUT_HARM = [(["S4"], CHILD), (["S12"], SEXUAL), (["S9"], WEAPONS), (["S1"], VIOLENCE), (["S10"], HATE)]

PAID_CLAIM = re.compile(r"(การ)?ชำระ(เงิน)?(เสร็จ(สมบูรณ์)?|สำเร็จ|เรียบร้อย|แล้ว)(แล้ว)?"         # N-05: only staff marks a payment as paid
                        r"|ได้รับ(เงิน|ยอด)(โอน)?(ของคุณ)?(แล้ว|เรียบร้อย(แล้ว)?|ครบ(แล้ว)?)")
PROMPT_LEAK = re.compile(r"## (ต้องทำ|ห้ามทำ|สถานะผู้ใช้|ข้อมูลอ้างอิง)")           # N-07: answer quotes the system prompt
HEALTH_VERDICT = re.compile(r"\s*\(?\s*(ซึ่ง)?(ถือว่า)?(อยู่ใน|สูงกว่า|ต่ำกว่า|เกิน)\s*(ค่า)?\s*(เกณฑ์|มาตรฐาน)(ปกติ|มาตรฐาน)?\s*\)?"
                            r"|ถือว่า(อ้วน|ผอม|ปกติ|น่าเป็นห่วง)|ควรอยู่(ที่|ระหว่าง)")   # N-06: no medical judgement
# "ไขมันค่อนข้างสูง": the verdict follows a body measure; only the verdict is cut, so "ค่อนข้างสูง" about a class stays
BODY_VERDICT = re.compile(r"((?:ไขมัน|น้ำหนัก|bmi|ความดัน|น้ำตาล|มวลกล้ามเนื้อ|รอบเอว)[^\n.]{0,20}?)\s*"
                          r"(?:ค่อนข้าง(?:สูง|ต่ำ|มาก|น้อย)|(?:สูง|ต่ำ|มาก|น้อย)เกินไป|(?:สูง|ต่ำ)กว่า(?:ปกติ|ค่าเฉลี่ย))", re.I)
MEASURE = re.compile(r"(?<![\d,.])(\d[\d,]*(?:\.\d+)?)\s*(?:%|เปอร์เซ็นต์|kg\b|กก\.?|กิโลกรัม|kcal|กิโลแคลอรี)", re.I)
PHONE = re.compile(r"(?<!\d)0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}(?!\d)")
BANK_ACCOUNT = re.compile(r"(?<!\d)\d{3}-\d-\d{5}-\d(?!\d)")
MONEY = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*บาท")
URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"']+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|co\.th|in\.th|th|io|app)\b", re.I)
TIME = re.compile(r"(?<![\d,.])([01]?\d|2[0-3])[:.]([0-5]\d)(?![\d.])")
SAFE_REPLY = "ขออภัยค่ะ เอ็กซ์ตอบเรื่องนี้ไม่ได้ พิมพ์ \"คุยกับพนักงาน\" หรือโทร 038-000-888 ได้เลยค่ะ"


def check_input(text: str, member_id: str | None = None, earlier: list[str] = ()) -> dict | None:
    """A fixed reply when the message falls in a Llama Guard hazard category (HARM_RULES) or breaks an input rule, else None (go on to the LLM).
    member_id = the verified member of this chat; asking about any other member is refused (N-04).
    earlier = the customer's previous 1–2 messages: an instruction split over them and this one is refused (N-07),
    but not when the earlier messages already held it on their own (they were refused then).
    Each rule sees the text in 3 forms, so "s y s t e m p r o m p t", "ｓｙｓｔｅｍ" and "sys-tem pr0mpt" all match."""
    for rules, pattern, answer, quick in HARM_RULES + INPUT_RULES:
        if any(pattern.search(form) for form in _forms(text)):
            return {"answer": answer, "sources": [], "rules": rules, "actions": quick}
    if _asks_other_member(_forms(text)[0], member_id):
        return {"answer": OTHER_MEMBER, "sources": [], "rules": ["N-04"], "actions": []}
    if earlier:
        before = " ".join(earlier)
        split = lambda t: any(SPLIT_INJECTION.search(form) for form in _forms(t))
        if split(f"{before} {text}") and not split(before):
            rules, _, answer, quick = INPUT_RULES[0]
            return {"answer": answer, "sources": [], "rules": rules, "actions": quick}
    return None


def _forms(text: str) -> tuple[str, str, str]:
    """Normalized text (full-width → normal, Thai digits → 0-9), that with spaces and - _ . * taken out, and that leet-decoded."""
    plain = unicodedata.normalize("NFKC", text).replace("ํา", "ำ").translate(THAI_DIGITS)   # NFKC splits sara am "ำ"
    squeezed = re.sub(r"[\s\-_.*·]+", "", plain)
    return plain, squeezed, squeezed.lower().translate(LEET)


def _asks_other_member(text: str, member_id: str | None) -> bool:
    """The message names a member code or a member's first name ("คุณณิชา") that is not the verified member's own."""
    own = (member_id or "").upper()
    if own and any(f"FN-{n}" != own for n in MEMBER_ID.findall(text)):
        return True                                                     # not verified yet: chat.verify_step asks for the phone digits
    return any(m["member_id"] != own and re.search(rf"(คุณ|ของ|น้อง|พี่)\s*{re.escape(m['first_name'])}", text)
               for m in business.table("members"))


def check_output(answer: str, known: str = "") -> tuple[str, list[str]]:
    """The answer with rule-breaking parts fixed, plus the codes of the rules that fired.

    known = what the LLM was given (member data, slip check, …). Every baht amount in the answer must appear there
    or anywhere in the knowledge base, otherwise the LLM made the number up (G-NUM). Same for web addresses (G-URL)
    and clock times (G-TIME): the LLM invented a shop website and a 05:00 opening time."""
    shop = business.table("business")
    answer = answer.translate(THAI_DIGITS)                                  # "๐๘๑-…" would slip past PHONE and MONEY
    if PROMPT_LEAK.search(answer) or _leaked(answer):
        return SAFE_REPLY, ["N-07"]
    for rules, pattern in OUTPUT_HARM:
        if pattern.search(answer):
            return SAFE_REPLY, rules
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
    if HEALTH_VERDICT.search(answer) or BODY_VERDICT.search(answer):
        answer, rules = BODY_VERDICT.sub(r"\1", HEALTH_VERDICT.sub("", answer)), rules + ["N-06"]
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
