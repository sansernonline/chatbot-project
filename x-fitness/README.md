# X Fitness Chatbot — source code

แชตบอทของสตูดิโอฟิตเนส "เอ็กซ์ ฟิตเนส" ตอบจากคลังความรู้ด้วย LightRAG · อ่านภาพสลิป/ใบเสร็จ/ผลวัดด้วย vision LLM · มี guardrail ก่อนและหลัง LLM · ใช้ Typhoon key ตัวเดียว · คุยได้ทั้งหน้าเว็บและ LINE Official Account

```text
ข้อความ → guard ขาเข้า → LightRAG ค้นคลังความรู้ → Typhoon ตอบ → guard ขาออก → ลูกค้า
ภาพ    → typhoon-ocr อ่านเป็น JSON → (สลิป) ตรวจ 5 ข้อด้วยโค้ด → รวมเข้าข้อความข้างบน
```

## โครงโฟลเดอร์

```text
x-fitness/
├── backend/
│   ├── app/
│   │   ├── main.py            เปิดแอป · สร้างดัชนีตอนเริ่ม · เสิร์ฟ frontend/
│   │   ├── chat.py            ตัวบอท answer() · read_image() + POST /api/chat · /api/vision
│   │   ├── line.py            LINE OA: POST /api/line/webhook · ส่งคำตอบพนักงานกลับ LINE
│   │   ├── guard.py           guardrail ขาเข้า/ขาออก
│   │   ├── rag.py             LightRAG (ไม่มี key → keyword_search.py)
│   │   ├── knowledge.py       API หน้าคลังความรู้ของ admin
│   │   ├── conversations.py   กล่องแชตลูกค้า/admin (SQLite)
│   │   ├── business.py        ข้อมูลสมาชิก · ตรวจสลิป
│   │   ├── llm.py · config.py · auth.py · db.py
│   │   └── prompts/           system.md · vision.md
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/      ← copy จาก ../mockup/      (หน้าเว็บลูกค้า + admin/)
├── data/          ← copy จาก ../data/        (knowledge-base/ + db/)
├── test-images/   ← copy จาก ../test-images/
└── rag-index/      ดัชนี LightRAG ที่สร้างไว้แล้ว (commit ขึ้น git ให้ Render ไม่ต้องสร้างใหม่)
```

`frontend/` `data/` `test-images/` เป็นสำเนา ต้นฉบับอยู่ที่รากโปรเจกต์ แก้ที่รากแล้วคัดลอกมาทับ:

```bash
# รันจากรากโปรเจกต์ (chatbot-project/)
cp -r mockup/. x-fitness/frontend/
cp -r data/. x-fitness/data/
cp -r test-images/. x-fitness/test-images/
```

## รันในเครื่อง

ต้องมี Python 3.12 ขึ้นไป (ทดสอบกับ 3.13) และ API key สองตัว: Typhoon (https://playground.opentyphoon.ai) และ Gemini สำหรับ embedding (https://aistudio.google.com/apikey · ฟรี)

```bash
cd x-fitness/backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # แล้วใส่ TYPHOON_API_KEY และ XF_EMBED_API_KEY ในไฟล์ .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| เปิด | URL |
|---|---|
| หน้าเว็บ + แชตลูกค้า | http://localhost:8000/ |
| หลังบ้าน (admin / 1234) | http://localhost:8000/admin/ |
| ตรวจสถานะ | http://localhost:8000/api/health |
| เอกสาร API อัตโนมัติ | http://localhost:8000/docs |
| ลูกค้าเปิดจากมือถือ (Wi-Fi เดียวกัน) | `http://<IP เครื่องนี้>:8000/` |

**ครั้งแรกที่เปิด**

1. ถ้า `rag-index/` ยังไม่มี หรือสร้างด้วย embedding คนละตัว LightRAG จะให้ Typhoon อ่านเอกสาร 8 ไฟล์เพื่อสร้างกราฟความรู้ใหม่ ใช้เวลาไม่กี่นาที — ดูสถานะที่ admin → **คลังความรู้** (`กำลังสร้างดัชนี` → `พร้อมใช้`)
2. ระหว่างนั้นบอทตอบได้ แต่ข้อมูลอาจไม่ครบจนดัชนีเสร็จ · เปิดครั้งต่อไปทำเฉพาะเอกสารที่เปลี่ยน

ไม่มี `TYPHOON_API_KEY` → เซิร์ฟเวอร์ยังเปิดได้ หน้าเว็บสลับไปโหมดจำลอง (ตอบด้วยกฎในหน้าเว็บ) · guardrail ขาเข้าและหน้า admin ยังใช้ได้

## ทดสอบ

```bash
cd x-fitness/backend
python -m pytest
```

ไม่ต้องใช้ key และไม่ต่อเน็ต — test ปลอม LLM และ embedding เอง แม้ใน `.env` จะมี key ก็ไม่เรียก Typhoon จริง

## ตั้งค่า (`backend/.env`)

| ตัวแปร | ค่าเริ่มต้น | ใช้ทำอะไร |
|---|---|---|
| `TYPHOON_API_KEY` | — (ต้องใส่) | แชต · อ่านภาพ · สร้างดัชนี LightRAG |
| `XF_CHAT_MODEL` | `typhoon-v2.5-30b-a3b-instruct` | โมเดลตอบแชต |
| `XF_VISION_MODEL` | `typhoon-ocr` | โมเดลอ่านภาพ |
| `XF_EMBED_API_KEY` | — | key ของ Gemini สำหรับ embedding · ไม่ใส่ = รันโมเดลในเครื่องแทน (ใช้ RAM เพิ่ม ~560 MB เกินแผนฟรีของ Render) |
| `XF_EMBED_MODEL` / `XF_EMBED_DIM` | `gemini-embedding-001` / `3072` | ใช้ตอนมี `XF_EMBED_API_KEY` · เปลี่ยนแล้วดัชนีสร้างใหม่เอง |
| `XF_RAG_MODE` | `mix` | โหมดค้นของ LightRAG: `naive` `local` `global` `hybrid` `mix` |
| `XF_ADMIN_USER` / `XF_ADMIN_PASS` | `admin` / `1234` | บัญชีหลังบ้าน |
| `XF_DB_PATH` | `backend/data/chat.sqlite3` | ที่เก็บแชต |

## ข้อมูลที่ระบบสร้างเอง

| ที่อยู่ | คืออะไร | ลบได้ไหม |
|---|---|---|
| `backend/data/chat.sqlite3` | แชตทั้งหมด | ได้ — แชตหาย |
| `rag-index/` (**commit**) | ดัชนี LightRAG + `manifest.json` (จำว่าสร้างด้วย embedding ตัวไหน) | ได้ — เปิดใหม่สร้างใหม่ (เรียก Typhoon อีกรอบ) |
| `backend/data/models/` | โมเดล embedding ในเครื่อง (เฉพาะตอนไม่มี `XF_EMBED_API_KEY`) | ได้ |

## แก้ปัญหา

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| แชตตอบ "ยังไม่ได้ตั้งค่า TYPHOON_API_KEY" | ไม่มีไฟล์ `.env` หรือ key ว่าง | ใส่ key ใน `backend/.env` แล้วเปิดเซิร์ฟเวอร์ใหม่ |
| หน้า admin คลังความรู้ขึ้น "ยังไม่มีดัชนี" | สร้างดัชนีไม่สำเร็จ | ดู log ในหน้าต่าง uvicorn แล้วกด **สร้างดัชนีใหม่** |
| ขึ้น "ระบบไม่ตอบภายในเวลาที่กำหนด" | Typhoon ตอบช้าเกิน 40 วินาที | กดลองอีกครั้ง · ถ้าเป็นบ่อยลอง `XF_RAG_MODE=naive` (ไม่ต้องให้ LLM แยกคำค้นก่อน) |
| Gemini ตอบ 429 | เกินโควตาฟรี (100 ครั้ง/นาที · 1,000 ครั้ง/วัน) | รอแล้วลองใหม่ · ช่วงสร้างดัชนีเรียกถี่ที่สุด |

## เชื่อม LINE Official Account

บอทตัวเดียวกับหน้าเว็บ (guardrail · LightRAG · อ่านภาพ) ตอบใน LINE ได้ทั้งข้อความและรูป · แชต LINE ขึ้นในกล่องแชตหลังบ้านเหมือนแชตหน้าเว็บ (ชื่อ "ลูกค้า LINE")

| ลูกค้าพิมพ์ใน LINE | บอททำอะไร |
|---|---|
| คำถามทั่วไป | แสดงจุดกำลังพิมพ์ → ตอบจากคลังความรู้ · มีปุ่มตอบด่วน "คุยกับพนักงาน" เมื่อไม่มั่นใจ |
| รูปสลิป / ใบเสร็จ / ผลวัด / โปสเตอร์ | อ่านภาพแล้วตอบ · สลิปตรวจ 5 ข้อเหมือนหน้าเว็บ |
| `FN-10003 5531` (รหัสสมาชิก + เบอร์ 4 ตัวท้าย) | ยืนยันตัวตน แล้วถามแต้ม ยอดค้าง ส่งสลิปได้ |
| `คุยกับพนักงาน` | ส่งเรื่องเข้ากล่องแชตหลังบ้าน บอทหยุดตอบ · พนักงานตอบในหลังบ้าน ข้อความส่งเข้า LINE ลูกค้า · กด "ปิดเรื่อง · คืนให้บอท" แล้วบอทกลับมาตอบ |

**ตั้งค่า (ครั้งเดียว)**

1. https://developers.line.biz/console/ → สร้าง Provider → สร้าง channel แบบ **Messaging API** (ได้ LINE OA มาด้วย)
2. แท็บ Basic settings → คัดลอก **Channel secret** · แท็บ Messaging API → กด Issue **Channel access token (long-lived)**
3. ใส่ใน `backend/.env`: `LINE_CHANNEL_SECRET=...` และ `LINE_CHANNEL_ACCESS_TOKEN=...` แล้วเปิดเซิร์ฟเวอร์ใหม่ (`/api/health` ต้องได้ `"line": true`)
4. LINE ต้องเรียกเซิร์ฟเวอร์ผ่าน **HTTPS สาธารณะ**:
   - ในเครื่อง: `cloudflared tunnel --url http://localhost:8000` (ได้ URL `https://….trycloudflare.com` ฟรี ไม่ต้องสมัคร)
   - หรือใช้ URL ของ Render
5. แท็บ Messaging API → Webhook URL = `https://<URL ข้อ 4>/api/line/webhook` → กด **Verify** ต้องขึ้น Success → เปิด **Use webhook**
6. LINE Official Account Manager → การตอบกลับ → **ปิด**ข้อความตอบกลับอัตโนมัติและข้อความทักทาย (ไม่งั้นลูกค้าได้ 2 คำตอบ)
7. สแกน QR ในแท็บ Messaging API เพิ่มเพื่อน แล้วลองพิมพ์

ความปลอดภัย: ทุกคำขอต้องมีลายเซ็น `X-Line-Signature` ที่ถูกต้อง ไม่มี secret = ปิดช่องทาง LINE (ตอบ 503) ไม่รับคำขอใดเลย

## นำขึ้น Render (ฟรี)

ใช้แผนฟรี (RAM 512 MB · แอปนี้ใช้ราว 160 MB เมื่อ embedding เรียก Gemini) · ไฟล์ตั้งค่าคือ `render.yaml` ที่**รากของ repo** (Render อ่านจากตรงนั้น)

**1. สร้างดัชนีในเครื่อง ด้วย key ชุดเดียวกับที่จะใส่บน Render**

```bash
cd x-fitness/backend
python -m app.rag          # สร้าง/อัปเดต ../rag-index/ แล้วพิมพ์สถานะ ต้องได้ 'ready' ครบ 8 เอกสาร
```

**2. Commit และ push ขึ้น GitHub** — ต้องมี `render.yaml` และ `x-fitness/` (รวม `x-fitness/rag-index/`) · ห้ามมี `.env` (`.gitignore` กันไว้แล้ว)

**3. สร้างบริการบน Render**

1. https://dashboard.render.com → **New** → **Blueprint** → เลือก repo นี้
2. Render อ่าน `render.yaml` แล้วถามค่า 3 ตัว: `TYPHOON_API_KEY` · `XF_EMBED_API_KEY` (ตัวเดียวกับข้อ 1) · `XF_ADMIN_PASS` (ตั้งใหม่ อย่าใช้ 1234)
3. รอ build เสร็จ แล้วเปิด `https://<ชื่อบริการ>.onrender.com/api/health` ต้องเห็น `"llm": true` และ `"rag": "lightrag"`
4. เปิด `/admin/` → **คลังความรู้** ทุกเอกสารต้องเป็น `พร้อมใช้` — ถ้าเป็น `กำลังสร้างดัชนี` แปลว่า embedding บน Render ไม่ตรงกับตอนสร้าง กลับไปทำข้อ 1

**ข้อจำกัดของแผนฟรี**

| เรื่อง | ผล |
|---|---|
| ไม่มีคนใช้ 15 นาที เครื่องหลับ | คนแรกที่เข้ามาต้องรอเครื่องตื่นสักพัก |
| ไฟล์ไม่ถาวร | ทุกครั้งที่หลับหรือ deploy ใหม่ **แชตใน SQLite หาย** · ดัชนีไม่หายเพราะอยู่ใน git |
| แก้คลังความรู้ | แก้ `data/knowledge-base/` ที่ราก → copy มา `x-fitness/data/` → ทำข้อ 1–2 ใหม่ (อัปโหลดผ่านหน้า admin บน Render จะหายเมื่อเครื่องหลับ) |

## นำขึ้น Vercel

**ขึ้นได้ แต่ไม่ได้ทั้งแบบนี้** — Vercel รัน FastAPI เป็น serverless function: ไม่มีเครื่องเปิดค้าง และเขียนไฟล์ถาวรไม่ได้ ระบบนี้เก็บสามอย่างลงดิสก์

| ส่วน | บนเครื่อง/เซิร์ฟเวอร์ปกติ | บน Vercel |
|---|---|---|
| แชต (SQLite) | เก็บถาวร | หายเมื่อ function ถูกปิด และแต่ละ instance เห็นแชตไม่ตรงกัน — admin ไม่เห็นแชตลูกค้า |
| ดัชนี LightRAG | สร้างครั้งเดียว | สร้างใหม่ทุก cold start (เรียก Typhoon ทุกครั้ง ช้าและเสียโควตา) |
| login admin (เก็บในหน่วยความจำ) | ใช้ได้ | หลุดบ่อยเมื่อ request ไปคนละ instance |

ถ้าต้องใช้ Vercel ต้องแก้: สร้างดัชนี LightRAG ในเครื่องแล้ว commit ขึ้นไปแบบอ่านอย่างเดียว (แบบที่ repo chacharin/light-rag ทำ) · ย้ายแชตไปฐานข้อมูลภายนอก (เช่น Postgres) · เปลี่ยน login เป็น token ที่ตรวจได้โดยไม่ต้องจำ

**ใช้ Render ตามหัวข้อข้างบนแทน** — ไม่ต้องแก้โค้ด
