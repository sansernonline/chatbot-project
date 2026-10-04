# X Fitness Chatbot — แผนภาพสถาปัตยกรรมและการไหลของข้อมูล

> ผู้พัฒนา: 68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ · ฉบับ 4 ต.ค. 2569 · โค้ดอยู่ที่ `x-fitness/` · แผนภาพเขียนด้วย Mermaid (เปิดใน GitHub หรือ VS Code แล้วเห็นเป็นภาพ)

## แผนภาพที่ 1 — สถาปัตยกรรมระบบ

แอปเดียว (FastAPI) รับทั้งหน้าเว็บ หลังบ้าน และ LINE · ความฉลาดมาจาก Typhoon ผ่าน API · ความรู้ของร้านอยู่ในไฟล์ที่ commit มากับโค้ด

```mermaid
flowchart LR
    C["👤 ลูกค้า<br/>หน้าเว็บ / LINE"]
    S["🧑‍💼 พนักงาน<br/>หน้าหลังบ้าน /admin"]
    LINE["LINE Messaging API"]
    APP["X Fitness backend<br/>FastAPI · uvicorn<br/>(Render หรือเครื่องตัวเอง)"]
    KB[("คลังความรู้ 9 เอกสาร<br/>+ ดัชนี LightRAG<br/>rag-index/")]
    DB[("SQLite<br/>แชตทั้งหมด")]
    TY["Typhoon API<br/>typhoon-v2.5 · typhoon-ocr"]

    C -- "พิมพ์/ส่งภาพบนเว็บ (HTTPS)" --> APP
    C -- "ข้อความ/รูปใน LINE" --> LINE
    LINE -- "webhook + ลายเซ็น" --> APP
    APP -- "reply / push / จุดกำลังพิมพ์" --> LINE
    S -- "อ่านแชต ตอบลูกค้า จัดการคลังความรู้" --> APP
    APP -- "ค้นเอกสาร (LightRAG + ค้นด้วยคำ)" --> KB
    APP -- "บันทึก/อ่านแชต" --> DB
    APP -- "ตอบแชต · อ่านภาพ · แยกคำสำคัญ" --> TY
```

## แผนภาพที่ 2 — ส่วนประกอบภายใน backend

```mermaid
flowchart TB
    IN["คำถามลูกค้า<br/>/api/chat · /api/line/webhook"]
    G1["guard ขาเข้า<br/>guard.py"]
    R["ค้นคลังความรู้<br/>rag.py (LightRAG + hash embedding<br/>+ ค้นด้วยคำ)"]
    B["ข้อมูลร้าน + กฎร้าน + ตรวจสลิป<br/>business.py"]
    L["Typhoon ตอบ<br/>llm.py · prompts/system.md"]
    G2["guard ขาออก<br/>guard.py"]
    OUT["คำตอบ + แหล่งอ้างอิง + รหัสกฎ<br/>(+ ปุ่มคุยกับพนักงาน)"]

    IN -- "ข้อความ" --> G1
    G1 -- "ผิดกฎ: ข้อความตายตัว" --> OUT
    G1 -- "ผ่าน" --> R
    R -- "ท่อนเอกสาร + ความสัมพันธ์ในกราฟ" --> L
    B -- "ข้อมูลสมาชิกที่ยืนยันแล้ว · กฎร้าน · ผลตรวจสลิป" --> L
    L -- "คำตอบดิบ" --> G2
    G2 -- "แก้/แทนคำตอบที่ผิดกฎ" --> OUT
```

## แผนภาพที่ 3 — การไหลของข้อมูล 1 ข้อความ (ลูกค้าส่งสลิปบนหน้าเว็บ)

```mermaid
sequenceDiagram
    autonumber
    actor C as ลูกค้า (หน้าเว็บ)
    participant API as backend (FastAPI)
    participant TY as Typhoon API
    participant KB as คลังความรู้ (LightRAG)
    participant DB as SQLite

    C->>API: POST /api/conversations/{ticket}/messages (บันทึกข้อความลูกค้า)
    API->>DB: เก็บข้อความ
    C->>API: POST /api/vision (ภาพสลิป)
    API->>TY: typhoon-ocr อ่านข้อความในภาพ
    TY-->>API: ข้อความในสลิป
    API->>TY: จัดเป็น JSON (ยอด วันเวลา ผู้รับ เลขอ้างอิง)
    TY-->>API: {type: slip, amount: 990, …}
    API-->>C: ผลอ่านภาพ
    C->>API: POST /api/chat (ข้อความ + ผลอ่านภาพ + รหัสสมาชิก)
    API->>API: guard ขาเข้า → ตรวจสลิป 5 ข้อด้วยโค้ด
    API->>TY: แยกคำสำคัญจากคำถาม (LightRAG)
    API->>KB: ค้นท่อนเอกสาร + กราฟ + ค้นด้วยคำ
    KB-->>API: KB-06 การชำระเงินและสลิป …
    API->>TY: คำสั่งระบบ + ข้อมูลอ้างอิง + ผลตรวจสลิป + ประวัติแชต
    TY-->>API: คำตอบ
    API->>API: guard ขาออก (ไม่ให้บอกว่า "ชำระสำเร็จ" · จำนวนเงินต้องมีจริง)
    API-->>C: คำตอบ + KB-06 + สถานะ "รอพนักงานยืนยัน"
    C->>API: POST /api/conversations/{ticket}/messages (บันทึกคำตอบบอท)
    API->>DB: เก็บข้อความ
```

ทาง LINE ใช้ขั้นตอนเดียวกัน ต่างแค่ข้อความเข้าทาง `POST /api/line/webhook` (ตรวจลายเซ็น ตอบ 200 ทันที แล้วทำงานเบื้องหลัง) ภาพโหลดจาก LINE แทนการอัปโหลด และคำตอบส่งกลับด้วย reply API ของ LINE

## Endpoint ทั้งหมดในแผนภาพ

| # | Method · Path | ใครเรียก | ทำอะไร | ทดสอบที่ |
|---|---|---|---|---|
| 1 | GET `/api/health` | หน้าเว็บ · Render | สถานะระบบ โมเดล ตัวค้น LINE เปิดไหม | `tests/test_conversations.py` |
| 2 | POST `/api/chat` | หน้าเว็บ | บอทตอบ (guard → RAG → Typhoon → guard) | `tests/test_bot.py` · `eval/run.py` |
| 3 | POST `/api/vision` | หน้าเว็บ | อ่านภาพ → JSON | `tests/test_bot.py` · `eval/run.py` |
| 4 | GET `/api/conversations/{ticket}` | หน้าเว็บ | ลูกค้าดึงแชตของตัวเอง | `tests/test_conversations.py` |
| 5 | POST `/api/conversations/{ticket}/messages` | หน้าเว็บ | บันทึกข้อความลูกค้า/บอท | `tests/test_conversations.py` |
| 6 | POST `/api/conversations/{ticket}/handoff` | หน้าเว็บ | ขอคุยกับพนักงาน | `tests/test_conversations.py` |
| 7 | POST `/api/admin/login` | หลังบ้าน | ล็อกอินได้ token | `tests/test_conversations.py` |
| 8 | GET `/api/admin/conversations` | หลังบ้าน | รายการแชตทั้งหมด (เว็บ + LINE) | `tests/test_conversations.py` |
| 9 | POST `/api/admin/conversations/{ticket}/messages` | หลังบ้าน | พนักงานตอบ (แชต LINE ส่งเข้า LINE ด้วย) | `tests/test_conversations.py` · `tests/test_line.py` |
| 10 | PATCH `/api/admin/conversations/{ticket}` | หลังบ้าน | รับเรื่อง / ปิดเรื่อง / อ่านแล้ว | `tests/test_conversations.py` |
| 11 | DELETE `/api/admin/conversations/{ticket}` | หลังบ้าน | ลบแชต | `tests/test_conversations.py` |
| 12 | DELETE `/api/admin/conversations` | หลังบ้าน | ลบแชตทั้งหมด | `tests/test_conversations.py` |
| 13 | GET `/api/admin/kb` | หลังบ้าน | รายการเอกสารและสถานะดัชนี | `tests/test_knowledge.py` |
| 14 | POST `/api/admin/kb/search` | หลังบ้าน | ทดสอบค้นคลังความรู้ | `tests/test_knowledge.py` |
| 15 | POST `/api/admin/kb` | หลังบ้าน | อัปโหลดเอกสาร .md | `tests/test_knowledge.py` |
| 16 | POST `/api/admin/kb/reindex` | หลังบ้าน | สร้างดัชนีใหม่เฉพาะที่เปลี่ยน | `tests/test_knowledge.py` |
| 17 | POST `/api/line/webhook` | LINE | รับข้อความ/รูปจาก LINE | `tests/test_line.py` |

รัน test ทั้งชุด (ไม่ต้องใช้ key): `cd x-fitness/backend && python -m pytest`
