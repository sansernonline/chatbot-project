# X Fitness Chatbot — source code

แชตบอทของสตูดิโอฟิตเนส "เอ็กซ์ ฟิตเนส" ตอบจากคลังความรู้ด้วย LightRAG · อ่านภาพสลิป/ใบเสร็จ/ผลวัดด้วย vision LLM · มี guardrail ก่อนและหลัง LLM · ใช้ Typhoon key ตัวเดียว · คุยได้ทั้งหน้าเว็บและ LINE Official Account

**เว็บหลัก (Render):** https://x-fitness-chatbot.onrender.com · หลังบ้าน https://x-fitness-chatbot.onrender.com/admin/ · สถานะ https://x-fitness-chatbot.onrender.com/api/health

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
│   │   ├── business.py        ข้อมูลสมาชิก · ตรวจสลิป · กฎสำคัญที่โค้ดแนบให้ LLM (RULES)
│   │   ├── llm.py · config.py · auth.py · db.py
│   │   └── prompts/           system.md · vision.md
│   ├── tests/              pytest (ไม่ต้องใช้ key)
│   ├── eval/               ทดสอบผ่าน API กับ Typhoon จริง: อ่าน qa/x-fitness-test-cases.md → qa/results/x-fitness-api-results.md
│   ├── requirements.txt
│   └── .env.example
├── e2e/           ทดสอบผ่านหน้าเว็บด้วย Playwright (ไม่แตะโค้ดแชตบอท) — ดู e2e/README.md
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

ต้องมี Python 3.12 ขึ้นไป (ทดสอบกับ 3.13) และ API key ตัวเดียวของ Typhoon (https://playground.opentyphoon.ai)

```bash
cd x-fitness/backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # แล้วใส่ TYPHOON_API_KEY ในไฟล์ .env
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

ไม่ต้องใช้ key และไม่ต่อเน็ต — test ปลอม LLM และ LINE เอง (embedding ใช้ของจริงเพราะเป็นสูตรคำนวณ) แม้ใน `.env` จะมี key ก็ไม่เรียก Typhoon จริง

**ชุดทดสอบตาม checklist ของวิชา** (ใช้ Typhoon จริง ต้องมี key): คำถาม 10 ข้อ · ภาพ 5 ภาพ · ความปลอดภัย 5 กรณี · สุ่มกฎต้องทำ/ห้ามทำ 10 ข้อ

```bash
python -m eval.run              # อ่าน ../../qa/x-fitness-test-cases.md → เขียน ../../qa/results/x-fitness-api-results.md
python -m eval.run --rules all  # ทดสอบกฎครบ 20 ข้อ
```

ชุดทดสอบ (แก้/เพิ่มได้) อยู่ที่ `qa/x-fitness-test-cases.md` · ทดสอบผ่านหน้าเว็บด้วย Playwright ดู `e2e/README.md` · กฎแต่ละข้ออธิบายใน `docs/03_bot-rules.md`

## ตั้งค่า (`backend/.env`)

| ตัวแปร | ค่าเริ่มต้น | ใช้ทำอะไร |
|---|---|---|
| `TYPHOON_API_KEY` | — (ต้องใส่) | แชต · อ่านภาพ · สร้างดัชนี LightRAG |
| `XF_CHAT_MODEL` | `typhoon-v2.5-30b-a3b-instruct` | โมเดลตอบแชต |
| `XF_VISION_MODEL` | `typhoon-ocr` | โมเดลอ่านภาพ |
| `XF_EMBED_API_KEY` | — (ไม่ต้องใส่) | ไม่ใส่ = embedding แบบนับกลุ่มตัวอักษร (`rag.hash_embed` ไม่มีโมเดล ไม่ใช้ RAM) · ใส่ key ของ Gemini = ค้นตามความหมายผ่าน API · เปลี่ยนแล้วดัชนีสร้างใหม่เอง |
| `XF_RAG_CHUNK_TOKENS` / `XF_RAG_LLM_MAX_TOKENS` | `500` / `8192` | ขนาดท่อนเอกสาร และความยาวคำตอบตอน Typhoon ดึงความรู้ · เปลี่ยนขนาดท่อนแล้วดัชนีสร้างใหม่เอง |
| `XF_RAG_MODE` | `mix` | โหมดค้นของ LightRAG: `naive` `local` `global` `hybrid` `mix` |
| `XF_ADMIN_USER` / `XF_ADMIN_PASS` | `admin` / `1234` | บัญชีหลังบ้าน |
| `XF_DB_PATH` | `backend/data/chat.sqlite3` | ที่เก็บแชต |

## ข้อมูลที่ระบบสร้างเอง

| ที่อยู่ | คืออะไร | ลบได้ไหม |
|---|---|---|
| `backend/data/chat.sqlite3` | แชตทั้งหมด | ได้ — แชตหาย |
| `rag-index/` (**commit**) | ดัชนี LightRAG + `manifest.json` (จำว่าสร้างด้วย embedding ตัวไหน) | ได้ — เปิดใหม่สร้างใหม่ (เรียก Typhoon อีกรอบ) |

## แก้ปัญหา

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| แชตตอบ "ยังไม่ได้ตั้งค่า TYPHOON_API_KEY" | ไม่มีไฟล์ `.env` หรือ key ว่าง | ใส่ key ใน `backend/.env` แล้วเปิดเซิร์ฟเวอร์ใหม่ |
| หน้า admin คลังความรู้ขึ้น "ยังไม่มีดัชนี" | สร้างดัชนีไม่สำเร็จ | ดู log ในหน้าต่าง uvicorn แล้วกด **สร้างดัชนีใหม่** |
| ขึ้น "ระบบไม่ตอบภายในเวลาที่กำหนด" | Typhoon ตอบช้าเกิน 40 วินาที | กดลองอีกครั้ง · ถ้าเป็นบ่อยลอง `XF_RAG_MODE=naive` (ไม่ต้องให้ LLM แยกคำค้นก่อน) |

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
   - หรือใช้ Render (ตัวหลัก): `https://x-fitness-chatbot.onrender.com` — ใส่ key ข้อ 3 ใน Render → **Environment** แทน `.env` แล้ว deploy ใหม่
5. แท็บ Messaging API → Webhook URL = `https://<URL ข้อ 4>/api/line/webhook` → กด **Verify** ต้องขึ้น Success → เปิด **Use webhook**
6. LINE Official Account Manager → การตอบกลับ → **ปิด**ข้อความตอบกลับอัตโนมัติและข้อความทักทาย (ไม่งั้นลูกค้าได้ 2 คำตอบ)
7. สแกน QR ในแท็บ Messaging API เพิ่มเพื่อน แล้วลองพิมพ์

ความปลอดภัย: ทุกคำขอต้องมีลายเซ็น `X-Line-Signature` ที่ถูกต้อง ไม่มี secret = ปิดช่องทาง LINE (ตอบ 503) ไม่รับคำขอใดเลย

## นำขึ้น Render (ฟรี)

ใช้แผนฟรี (RAM 512 MB · แอปนี้ใช้ราว 160 MB เพราะ embedding เป็นสูตรคำนวณ ไม่ต้องโหลดโมเดล) · ไฟล์ตั้งค่าคือ `render.yaml` ที่**รากของ repo** (Render อ่านจากตรงนั้น)

**1. สร้างดัชนีในเครื่อง** (ตั้งค่า embedding ให้เหมือนบน Render — ปกติคือไม่ใส่ `XF_EMBED_API_KEY` ทั้งสองที่)

```bash
cd x-fitness/backend
python -m app.rag          # สร้าง/อัปเดต ../rag-index/ แล้วพิมพ์สถานะ ต้องได้ 'ready' ครบ 8 เอกสาร
```

**2. Commit และ push ขึ้น GitHub** — ต้องมี `render.yaml` และ `x-fitness/` (รวม `x-fitness/rag-index/`) · ห้ามมี `.env` (`.gitignore` กันไว้แล้ว)

**3. สร้างบริการบน Render**

1. https://dashboard.render.com → **New** → **Blueprint** → เลือก repo นี้
2. Render อ่าน `render.yaml` แล้วถามค่า: `TYPHOON_API_KEY` · `XF_ADMIN_PASS` (ตั้งใหม่ อย่าใช้ 1234) · `XF_EMBED_API_KEY` และค่าของ LINE เว้นว่างได้ (ใส่ทีหลังใน **Environment** · ถ้าเว้นไว้ LINE webhook ตอบ 503)
3. รอ build เสร็จ แล้วเปิด `https://x-fitness-chatbot.onrender.com/api/health` ต้องเห็น `"llm": true` และ `"rag": "lightrag"`
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

## ความรู้: embedding แบบ "Feature hashing ของ character n-gram"

LightRAG ต้องแปลงข้อความเป็นชุดตัวเลข (embedding) เพื่อค้นหา ระบบนี้ใช้สูตรคำนวณแทนโมเดล AI:

1. ตัดข้อความเป็นกลุ่มตัวอักษรต่อกันทีละ 2 และ 3 ตัว (character n-gram) เช่น "ค่าสมา" → `ค่` `่า` `าส` `สม` `มา` `ค่า` `่าส` …
2. แต่ละกลุ่มผ่านฟังก์ชันแฮช (crc32) ได้เลขช่อง 1 ใน 1,024 ช่อง แล้วบวกหรือลบ 1 ในช่องนั้น (เครื่องหมายมาจากแฮชเช่นกัน ช่วยให้กลุ่มที่บังเอิญชนช่องเดียวกันหักล้างกันแทนที่จะสะสม) — นี่คือ **feature hashing** หรือ **hashing trick**
3. ปรับความยาวเวกเตอร์เป็น 1 แล้ววัดความใกล้ด้วย **cosine similarity** — ข้อความที่มีกลุ่มตัวอักษรร่วมกันมากจะได้คะแนนสูง

| | Feature hashing (ใช้อยู่) | Embedding จากโมเดล (เช่น Gemini, MiniLM) |
|---|---|---|
| ประเภท | lexical / sparse — วัด "คำที่ใช้" | dense / semantic — วัด "ความหมาย" |
| ต้องมี | สูตร ~15 บรรทัดใน `rag.py` | โมเดล AI (รันเองใช้ RAM ~560 MB หรือเรียก API) |
| ภาษาไทย | ได้ ไม่ต้องตัดคำ | ได้ |
| จุดอ่อน | ถามด้วยคำที่ไม่มีในเอกสารเลยจะไม่เจอ → เอกสารจึงใส่ "ชื่อเรียกอื่น" ไว้ | ใหญ่ หรือต้องมี key |
| วัดกับคำถามทดสอบ 12 ข้อ | ถูก 12/12 | MiniLM ถูก 11/12 |

คำค้นที่เกี่ยวข้อง: hashing vectorizer (scikit-learn `HashingVectorizer(analyzer="char", ngram_range=(2, 3))`), bag of character n-grams, TF-IDF, BM25, sparse retrieval
