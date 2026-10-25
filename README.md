# X Fitness Chatbot — Final Project

> วิชา 06048308 Intelligent Chatbot Development · สตูดิโอฟิตเนสจำลอง "เอ็กซ์ ฟิตเนส" ศรีราชา (ข้อมูลทั้งหมดเป็นข้อมูลจำลอง)
> **เว็บจริง:** https://x-fitness-chatbot.onrender.com · หลังบ้าน `/admin/` (admin / ตั้งใน Render) · เอกสาร `/documents/` · LINE webhook `/api/line/webhook`

แชตบอทตอบลูกค้าทั้งหน้าเว็บและ LINE: ตอบจากคลังความรู้ (LightRAG + Typhoon) อ่านภาพสลิป ปฏิเสธเรื่องที่ไม่ควรตอบ และส่งต่อพนักงาน
เรื่องเงินและข้อมูลสมาชิกตัดสินด้วยโค้ด ไม่ใช่ AI

## โฟลเดอร์

| โฟลเดอร์ | มีอะไร |
|---|---|
| `x-fitness/` | **source code ที่รันได้** (backend FastAPI + หน้าเว็บ + ฐานข้อมูลพร้อมใช้ + ดัชนี LightRAG) · วิธีรันละเอียดอยู่ใน `x-fitness/README.md` |
| `mockup/` | ต้นฉบับหน้าเว็บและหลังบ้าน ดับเบิลคลิก `mockup/index.html` ดูได้เลย (ไม่มี backend = โหมดจำลอง) |
| `data/` | ต้นฉบับข้อมูล: `knowledge-base/` คลังความรู้ 9 ไฟล์ · `db/*.json` ข้อมูลร้าน + `datadict.json` คำอธิบายทุกคอลัมน์ · `guard/replies.md` ข้อความปฏิเสธ |
| `qa/` | ชุดทดสอบ 2,690 ข้อ (`1-questions.md` `2-images.md` `3-safety.md`) · ผลทดสอบใน `report/` `guardrail/` `system/` |
| `docs/` | รายงาน (`08_project-report.md` + .docx) · สไลด์ (.html · .pptx) · กฎบอท `03_bot-rules.md` · แผนภาพ `06_diagrams.md` |

แก้ไฟล์ใน `mockup/` `data/` `qa/test-images/` หรือ `docs/` แล้ว **รัน build ก่อน commit** (ดูด้านล่าง) ระบบคัดลอกเข้า `x-fitness/` และสร้างฐานข้อมูลใหม่ให้

## รัน

เริ่มที่รากโปรเจกต์ (โฟลเดอร์ที่มี README นี้) · ต้องมี Python 3.12+ และ `TYPHOON_API_KEY`

```bash
python x-fitness/tools/build_dist.py     # คัดลอกจากรากเข้า x-fitness/ + สร้าง x-fitness/data/db/xfitness_db.sqlite3 (JSON เทลงฐานข้อมูล ไม่คัดลอก)
cd x-fitness/backend
pip install -r requirements.txt
cp .env.example .env                     # Windows: copy .env.example .env  แล้วใส่ TYPHOON_API_KEY
uvicorn app.main:app --port 8000
```

| เปิด | URL |
|---|---|
| หน้าเว็บ + แชต | http://localhost:8000/ |
| หลังบ้าน (admin / 1234) | http://localhost:8000/admin/ |
| ดูฐานข้อมูล · ดูกราฟความรู้ (อ่านอย่างเดียว) | `/admin/dbviewer.html` · `/admin/graphviewer.html` |
| เอกสารโครงงาน · API (Swagger) | `/documents/` · `/docs` |

## ทดสอบ

| ชุด | คำสั่ง (จาก `x-fitness/`) | ต้องใช้ |
|---|---|---|
| ตรวจโค้ด (pytest) | `cd backend && python -m pytest` | ไม่ต้องใช้ key |
| ผ่าน API กับบอทจริง | `cd backend && python -m eval.run` | `TYPHOON_API_KEY` |
| **ผ่านหน้าเว็บด้วย Playwright** | `cd e2e && npm install && npx playwright install chromium && npm test` | backend ที่รันอยู่ หรือให้ Playwright เปิดเอง · ชุด 20 ข้อ ~2 นาที |

ผลทดสอบเขียนลง `qa/report/results/` พร้อมภาพหน้าจอ · ตัวเลือกเพิ่ม (เลือกชุด สุ่มจากคลัง ทดสอบเว็บจริง) อยู่ใน `x-fitness/e2e/README.md`

## บัญชีทดสอบ (สมาชิกจำลอง)

ในแชตพิมพ์รหัสสมาชิกตามด้วยเบอร์ 4 ตัวท้าย เช่น `FN-10003 5531`

| รหัส | 4 ตัวท้าย | ใช้ทดสอบ |
|---|---|---|
| FN-10003 | 5531 | สลิปถูกต้อง `01_slip_valid.png` (ค้าง 990 บาท) |
| FN-10007 | 3364 | สลิปยอดไม่ตรง `02_slip_amount_mismatch.png` (ค้าง 1,290 บาท) |
| FN-10004 | 7702 | นักศึกษา เข้าคลาส Ride ไม่ได้ |
| FN-10008 | 6158 | พักสมาชิกอยู่ |
| FN-10006 | 9023 | รายปี แต้มเยอะ |

## หมายเหตุ

- คำตอบในโหมดจำลอง (ไม่มี backend หรือไม่มี key) ใช้ซ้อมหน้าจอเท่านั้น ไม่ใช่ผลทดสอบ LLM
- เว็บจริงบน Render ล้างข้อมูลที่เกิดใหม่ทุกครั้งที่ restart แล้วกลับไปใช้ฐานข้อมูลพร้อมใช้ที่ commit ไว้
- โปร YEAR13 หมดเขต 31 ต.ค. 2569 หลังวันนั้นบอทตอบว่าหมดเขต ซึ่งถูกต้อง
