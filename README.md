# X Fitness — Final Project แชตบอท

> วิชา 06048308 Intelligent Chatbot Development · ส่ง 17 ต.ค. 2569 · **แจ้งชื่อธุรกิจภายใน 3 ต.ค. 2569**
> ธุรกิจ: สตูดิโอฟิตเนสขนาดเล็ก "เอ็กซ์ ฟิตเนส (X Fitness)" ศรีราชา · ข้อมูลทั้งหมดเป็นข้อมูลจำลอง
> **เว็บหลัก (Render):** https://x-fitness-chatbot.onrender.com · หลังบ้าน https://x-fitness-chatbot.onrender.com/admin/ · LINE webhook `https://x-fitness-chatbot.onrender.com/api/line/webhook`

## โครงสร้างโฟลเดอร์

```text
final-project/
├── README.md                     ไฟล์นี้: ภาพรวม + ตารางครอบคลุมเกณฑ์ประเมิน
├── docs/
│   ├── Final Project.docx        โจทย์จากอาจารย์
│   ├── 01_business-profile.md    ชื่อธุรกิจ กลุ่มเป้าหมาย ข้อมูลพื้นฐาน เหตุผลที่เข้าเงื่อนไข
│   ├── 02_faq-top10.md           คำถามที่ถามบ่อย 10 เรื่อง + เฉลย
│   ├── 03_bot-rules.md           ข้อกำหนดต้องทำ 10 ข้อ / ห้ามทำ 10 ข้อ (มีรหัส D-xx, N-xx)
│   ├── 04_system-prompt.md       คำสั่งระบบฉบับร่าง + คำสั่งวิเคราะห์ภาพ
│   ├── 05_test-plan.md           (ยังไม่มี) ใช้ชุดทดสอบใน qa/ แทน
│   ├── 06_diagrams.md            แผนภาพสถาปัตยกรรม + การไหลของข้อมูล 1 ข้อความ (Mermaid)
│   ├── 07_demo-script.md         สคริปต์คลิปนำเสนอ
│   ├── 08_project-report.md      ต้นฉบับเอกสารพัฒนาโครงการ
│   ├── XFitness-Chatbot_*.docx/.pdf/.pptx   ไฟล์ส่งมอบ: เอกสารพัฒนาโครงการ + งานนำเสนอ
│   └── architecture.png          แผนภาพสถาปัตยกรรม (ใช้ในเอกสารและสไลด์)
├── qa/
│   ├── test-images/              ภาพทดสอบ 5 ภาพ (มีลายน้ำ "ภาพจำลองเพื่อการทดสอบ")
│   ├── x-fitness-test-cases.md   เอกสาร test case 40 กรณี (ต้นฉบับ แก้ได้): คำถาม 10 · ภาพ 5 · ความปลอดภัย 5 · ต้องทำ/ห้ามทำ 20
│   └── results/                  ผลทดสอบ: x-fitness-ui-results.md (Playwright + ภาพหน้าจอ) · x-fitness-api-results.md (สคริปต์ API)
├── data/
│   ├── knowledge-base/           คลังความรู้ 8 เอกสาร (~15 หน้า) สำหรับทำ RAG
│   └── db/                       ข้อมูลธุรกิจแบบ JSON 14 ไฟล์ (แพ็กเกจ คลาส ตาราง สมาชิกจำลอง 20 คน ฯลฯ)
├── mockup/
│   ├── index.html                เว็บไซต์ต้นแบบพร้อมวิดเจ็ตแชต เปิดด้วยเบราว์เซอร์ได้เลย
│   ├── admin/                    ระบบหลังบ้าน (login admin / 1234 · ไม่รัน backend = โหมดดูตัวอย่าง)
│   └── shared/                   db.js (ข้อมูลจาก data/db) + chat-store.js (ต่อ API กล่องแชต ใช้ร่วมกันทั้งหน้าเว็บและหลังบ้าน)
└── x-fitness/                    source code (รันได้ในตัว)
    ├── backend/                  FastAPI: บอท LightRAG + vision LLM + guardrail (/api/chat, /api/vision) + กล่องแชตใน SQLite + เสิร์ฟหน้าเว็บ
    ├── frontend/                 สำเนาของ mockup/ ที่ backend เสิร์ฟ
    ├── data/                     สำเนาของ data/
    └── test-images/              สำเนาของ qa/test-images/
```

## วิธีเปิด mockup

ดับเบิลคลิก `mockup/index.html` (ต้องต่ออินเทอร์เน็ตเพื่อโหลดฟอนต์) แชตดึงภาพทดสอบจาก `qa/test-images/`

- แชตเริ่มใน **โหมดจำลอง**: ตอบจากข้อมูลใน `data/db` ด้วยกฎในหน้าเว็บ ใช้ซ้อมและถ่ายคลิปสาธิต UI ได้ทันที
- เมื่อมี backend จริง กดไอคอนตั้งค่าในแชต → **เชื่อม Backend API** → ใส่ URL หน้าเว็บจะเรียก `POST /api/chat`, `POST /api/vision`, `GET /api/health` ตามแผนภาพ
- หน้าตั้งค่าในแชตมีสวิตช์จำลองเครือข่ายล่มและหมดเวลา ไว้ทดสอบสถานะ error

### ระบบหลังบ้าน (admin) และ backend

- **ดูหน้าตาอย่างเดียว:** ดับเบิลคลิก `mockup/admin/index.html` ล็อกอิน admin / 1234 ได้เลย เข้า**โหมดดูตัวอย่าง** มีแชตตัวอย่างให้ลองตอบ แต่ไม่บันทึกอะไร
- **ใช้งานจริง:** รัน backend ก่อน แล้วกล่องแชตจะอ่าน/เขียน SQLite
- `x-fitness/` เป็น source code ที่รันได้ในตัว: `frontend/` `data/` `test-images/` ในนั้น**คัดลอกมาจากราก** (`mockup/` `data/` `qa/test-images/`) ถ้าแก้ `mockup/` หรือ `data/` ที่ราก ให้คัดลอกไปทับอีกครั้ง เช่น `cp -r mockup/. x-fitness/frontend/` และ `cp -r data/. x-fitness/data/`

```bash
cd x-fitness/backend
pip install -r requirements.txt
cp .env.example .env          # ใส่ TYPHOON_API_KEY ในไฟล์ .env (ไฟล์นี้ไม่ถูก commit)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

เปิด `http://localhost:8000/` (หน้าเว็บ) และ `http://localhost:8000/admin/` (หลังบ้าน ล็อกอิน **admin / 1234** ตรวจที่เซิร์ฟเวอร์) · ลูกค้าเปิดจากมือถือได้ที่ `http://<IP เครื่องนี้>:8000/` ถ้าอยู่ Wi-Fi เดียวกัน

**LINE OA ตัวจริง** ใช้ Webhook URL = `https://x-fitness-chatbot.onrender.com/api/line/webhook` · ต้องใส่ `LINE_CHANNEL_SECRET` และ `LINE_CHANNEL_ACCESS_TOKEN` ใน Render → Environment ก่อน ไม่งั้น Verify ได้ 503

**ทดสอบ LINE OA จากเครื่องตัวเอง (Cloudflare Tunnel)** — ติดตั้งครั้งแรก `winget install --id Cloudflare.cloudflared` แล้วทำทุกครั้ง:

1. หน้าต่างที่ 1: `cd x-fitness/backend` แล้ว `uvicorn app.main:app --port 8000`
2. หน้าต่างที่ 2: `cloudflared tunnel --url http://localhost:8000` แล้วคัดลอก URL `https://….trycloudflare.com`
3. LINE Developers → Messaging API → Webhook URL = `<URL>/api/line/webhook` → **Verify**
4. เลิกใช้: `Ctrl+C` ทั้งสองหน้าต่าง

URL เปลี่ยนทุกครั้งที่เปิด tunnel ใหม่ · ขั้นตอนตั้งค่า LINE ครั้งแรก (สร้าง OA, Channel secret, access token) และวิธีแก้เมื่อ Verify ไม่ผ่าน ดู `x-fitness/README.md` หัวข้อ "เชื่อม LINE Official Account"

| เมนู | เชื่อม API | ทำอะไร |
|---|---|---|
| กล่องแชตลูกค้า | ✓ | รับเรื่อง ตอบลูกค้า ข้อความสำเร็จรูป ปิดเรื่องคืนให้บอท ดูข้อมูลสมาชิกข้างแชต |
| ภาพรวม · Leads · สมาชิก · การชำระเงิน · การจองคลาส · โปรโมชัน · ตั้งค่าบอท · รายงาน · ผู้ใช้และสิทธิ์ | ยัง | แสดงข้อมูลจาก `data/db` ปุ่มที่ยังไม่ต่อ API แจ้ง "เร็ว ๆ นี้" |
| คลังความรู้ (RAG) | ✓ | รายการเอกสารและสถานะดัชนี · ทดสอบค้น · อัปโหลด `.md` · สร้างดัชนีใหม่ |

**แชตลูกค้า**
- แชตใหม่ได้เลขเรื่อง (ticket) 10 ตัว ตัวอักษรสลับตัวเลข เช่น `K3M8P2Q7R5` เก็บใน localStorage ของลูกค้า รีโหลดหน้าแล้วกลับมาแชตเดิม ปุ่ม "เริ่มแชตใหม่" ออกเลขใหม่
- ข้อความทุกข้อความเก็บใน SQLite `x-fitness/backend/data/chat.sqlite3` · ไม่รัน backend บอทยังตอบได้ (โหมดจำลอง) แต่ส่งต่อพนักงานไม่ได้
- ทดสอบ: ลูกค้าพิมพ์ "คุยกับพนักงาน" → เข้ากล่องของ admin ภายใน 1–2 วินาที → admin ตอบ ข้อความขึ้นในแชตลูกค้า ระหว่างนั้นบอทหยุดตอบ จนกว่า admin จะกด "ปิดเรื่อง · คืนให้บอท"

**บอท** — เมื่อ `.env` มี `TYPHOON_API_KEY` หน้าเว็บสลับไปตอบด้วย LLM จริงเอง (ไม่มี key = โหมดจำลอง) · ใช้ key ของ Typhoon ตัวเดียว (แชต · อ่านภาพ · สร้างดัชนี LightRAG)

```text
ข้อความ (หน้าเว็บ หรือ LINE OA) → guard ขาเข้า → LightRAG ค้นคลังความรู้ → LLM ตอบ → guard ขาออก → ลูกค้า
ภาพ    → vision LLM อ่านเป็น JSON → (สลิป) ตรวจ 5 ข้อด้วยโค้ด → รวมเข้าข้อความข้างบน
```

| ส่วน | ไฟล์ | ทำอะไร |
|---|---|---|
| Guardrail | `x-fitness/backend/app/guard.py` | **ขาเข้า** ข้อความเปลี่ยนคำสั่งระบบ (N-07, N-08) · อาการฉุกเฉิน (D-07) · ยา/สารกระตุ้น (N-06) · นอกเรื่อง (N-10) ตอบด้วยข้อความตายตัว ไม่เรียก LLM · **ขาออก** ตัดคำว่า "ชำระสำเร็จ" (N-05) · ปิดเบอร์โทรที่ไม่ใช่ของร้าน (N-04) · ตัดคำประเมินสุขภาพเช่น "อยู่ในเกณฑ์ปกติ" (N-06) · คำตอบที่มีเลขบัญชีอื่น หลุดคำสั่งระบบ หรือมีจำนวนเงินที่ไม่มีในคลังความรู้ (G-NUM) เปลี่ยนเป็นข้อความปลอดภัยและเสนอส่งต่อพนักงาน · รหัสกฎส่งกลับใน `rules` |
| RAG | `x-fitness/backend/app/rag.py` | LightRAG: Typhoon สร้างกราฟความรู้ + เวกเตอร์จาก `data/knowledge-base` · embedding แบบ feature hashing ของกลุ่มตัวอักษร 2–3 ตัว (ไม่มีโมเดล ไม่ใช้ key) · ดัชนีสร้างไว้แล้วใน `x-fitness/rag-index/` ทำใหม่เฉพาะเอกสารที่เปลี่ยน · ไม่มี `TYPHOON_API_KEY` = ค้นด้วยคำแทน (`keyword_search.py`) |
| Vision | `x-fitness/backend/app/chat.py` `/api/vision` | `typhoon-ocr` อ่านข้อความในภาพ (`prompts/ocr.md` · ตอบ error ลองใหม่ 1 ครั้ง) → LLM แชตจัดเป็น JSON ตาม `prompts/vision.md` · typhoon-ocr ใช้คำสั่งให้ตอบ JSON ตรง ๆ ไม่ได้ (ทดสอบแล้ว error) · สลิปตรวจ 5 ข้อตาม KB-06 ด้วยโค้ด (`business.py`) |
| คำสั่งระบบ | `x-fitness/backend/app/prompts/system.md` | กฎต้องทำ/ห้ามทำ + ข้อมูลสมาชิกที่ยืนยันแล้ว + ประวัติแชต 8 ข้อความ |

ตั้งค่าผ่าน `x-fitness/backend/.env` (ดูตัวอย่างใน `.env.example`): `TYPHOON_API_KEY`, `XF_CHAT_MODEL`, `XF_VISION_MODEL`, `LINE_CHANNEL_SECRET` `LINE_CHANNEL_ACCESS_TOKEN`, `XF_EMBED_MODEL` `XF_EMBED_DIM` (หรือ `XF_EMBED_API_KEY` `XF_EMBED_BASE_URL` ถ้าจะใช้ embedding API), `XF_RAG_MODE`, `XF_ADMIN_USER`, `XF_ADMIN_PASS`, `XF_DB_PATH`, `XF_CORS_ORIGINS` · ทดสอบ backend: `cd x-fitness/backend && python -m pytest` (ไม่ต้องใช้ key — LightRAG ทดสอบด้วย LLM และ embedding ปลอม)


| Method | Path | ใช้ทำอะไร |
|---|---|---|
| GET | `/api/health` | ตรวจว่า backend ทำงาน และมี key ของ Typhoon หรือไม่ |
| POST | `/api/chat` | บอทตอบ (Typhoon + RAG) |
| POST | `/api/vision` | อ่านภาพ (Typhoon OCR) → JSON |
| GET | `/api/conversations/{ticket}` | ลูกค้าดึงแชตของตัวเอง |
| POST | `/api/conversations/{ticket}/messages` | บันทึกข้อความลูกค้า/บอท |
| POST | `/api/conversations/{ticket}/handoff` | ขอคุยกับพนักงาน |
| POST | `/api/admin/login` | ล็อกอิน ได้ token |
| GET | `/api/admin/conversations` | รายการแชตทั้งหมด |
| POST | `/api/admin/conversations/{ticket}/messages` | พนักงานตอบ |
| PATCH | `/api/admin/conversations/{ticket}` | รับเรื่อง / ปิดเรื่อง / อ่านแล้ว |
| DELETE | `/api/admin/conversations[/{ticket}]` | ลบแชต |
| POST | `/api/line/webhook` | รับข้อความ/รูปจาก LINE OA (ตรวจลายเซ็น) แล้วตอบกลับทาง LINE |
| GET | `/api/admin/kb` | รายการเอกสารคลังความรู้ + สถานะดัชนี |
| POST | `/api/admin/kb/search` | ทดสอบค้นคลังความรู้ (3 ส่วนที่ใกล้ที่สุด) |
| POST | `/api/admin/kb` | อัปโหลดเอกสาร `.md` (ไม่เกิน 200 KB) แล้วสร้างดัชนี |
| POST | `/api/admin/kb/reindex` | สร้างดัชนีใหม่เฉพาะเอกสารที่เปลี่ยน |

บัญชีทดสอบ (สมาชิกจำลอง)

| รหัสสมาชิก | เบอร์ 4 ตัวท้าย | ใช้ทดสอบ |
|---|---|---|
| FN-10003 | 5531 | สลิปถูกต้อง `01_slip_valid.png` (ยอดค้าง 990 บาท) |
| FN-10007 | 3364 | สลิปยอดไม่ตรง `02_slip_amount_mismatch.png` (ยอดค้าง 1,290 บาท) |
| FN-10004 | 7702 | นักศึกษา จองคลาส Ride ไม่ได้ |
| FN-10008 | 6158 | พักสมาชิกอยู่ จองคลาสไม่ได้ |
| FN-10006 | 9023 | รายปี แต้มเยอะ ใช้ทดสอบแลกของรางวัล |

## ตารางครอบคลุมเกณฑ์ประเมิน (Checklist)

### ต้นแบบแชตบอทที่ทำงานได้จริง

| เกณฑ์ | สิ่งที่เตรียมไว้แล้ว | สิ่งที่ต้องทำต่อ |
|---|---|---|
| LLM: ตอบชุดคำถามทดสอบถูกต้อง | ชุดคำถาม 10 ข้อพร้อมเฉลย `docs/05_test-plan.md` ส่วนที่ 1 | ต่อ LLM จริงแล้วรันเก็บผล |
| API: ทุก endpoint ในแผนภาพทำงาน | กำหนด 6 endpoint + ตัวอย่างคำขอ/ผลที่คาดหวัง (ส่วนที่ 6) | เขียน backend FastAPI |
| UI: สถานะกำลังประมวลผล + error | mockup แสดง 3 ขั้นตอนประมวลผล, error เครือข่าย/หมดเวลา/ไฟล์ใหญ่/ชนิดไฟล์ผิด/ข้อความยาวเกิน + ปุ่มลองใหม่ | ต่อกับ API จริง |
| RAG: ตอบจากคลังความรู้ภาษาไทย | คลังความรู้ภาษาไทย 8 เอกสาร มีรหัส KB-01 ถึง KB-08 สำหรับอ้างอิง | ใส่ `TYPHOON_API_KEY` แล้วรันเก็บผล (LightRAG เขียนแล้ว) |
| Prompt: สุ่มทดสอบต้องทำ/ห้ามทำ | กฎ 20 ข้อมีรหัส + ข้อความทดสอบครบทุกข้อ + คำสั่งสุ่ม (ส่วนที่ 5) | รันสุ่มแล้วกรอกผล |
| Safety: มาตรการป้องกัน | มาตรการ 4 ชั้น + ชุดทดสอบ 5 กรณี (ส่วนที่ 3) | guardrail ขาเข้า/ขาออกใน `x-fitness/backend/app/guard.py` มี test แล้ว · ยืนยันกับ LLM จริง |

### เอกสารและหลักฐานการทดสอบ

| เกณฑ์ | ไฟล์ |
|---|---|
| ชื่อธุรกิจ กลุ่มเป้าหมาย ข้อมูลพื้นฐาน | `docs/01_business-profile.md` |
| คำถามที่ถามบ่อย 10 เรื่อง | `docs/02_faq-top10.md` |
| ข้อกำหนดต้องทำ/ห้ามทำ | `docs/03_bot-rules.md` |
| บันทึกผลทดสอบ (คำถาม 10 · ภาพ 5 · ความปลอดภัย 5 · ปรับปรุง 3) | `docs/05_test-plan.md` |
| แผนภาพสถาปัตยกรรม | `docs/06_diagrams.md` แผนภาพที่ 1 |
| แผนภาพการไหลของข้อมูล | `docs/06_diagrams.md` แผนภาพที่ 2 |
| Source code ที่ทำงานซ้ำได้ | `x-fitness/backend/` + `requirements.txt` + วิธีรันในหัวข้อ "ระบบหลังบ้าน (admin) และ backend" |

## หมายเหตุสำหรับการทดสอบจริง

- ผลในโหมดจำลองใช้ซ้อมหน้าจอเท่านั้น **ห้ามนำไปกรอกเป็นผลทดสอบ LLM** ต้องรันกับ backend จริงแล้วบันทึกผลและเวลาตอบจริง
- ภาพทดสอบเป็นภาพจำลองที่มีลายน้ำ ห้ามใช้แทนเอกสารจริง
- วันที่ในข้อมูลอ้างอิงช่วงเดือนกันยายน–ตุลาคม 2569 โปร YEAR13 หมดเขต 31 ต.ค. 2569 หลังวันนั้นบอทจะตอบว่าหมดเขต (เป็นพฤติกรรมที่ถูกต้อง)
