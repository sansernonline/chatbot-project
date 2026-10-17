"""Text of every clickable card in the deck: real file, what it does, size, a real excerpt.
Sizes and counts were measured on 2026-10-10 (see docs/BUILD-PLAN.md). Edit here, then run build.py."""

# tag colours: "" grey · "red" · "ok" green · "blue"
ARCH = {
    "web": dict(path="x-fitness/frontend/index.html",
        tags=[("1,401 บรรทัด", ""), ("HTML + JS ไฟล์เดียว", "blue")],
        what="หน้าเว็บร้านและกล่องแชตของลูกค้า พิมพ์ข้อความแล้วส่งไป <b>POST /api/chat</b> ถ้าแนบภาพจะส่งไป <b>/api/vision</b> ก่อน รอคำตอบนานสุด 40 วินาที",
        code="const r = await fetchT(base + '/api/chat', {\n  method: 'POST',\n  body: JSON.stringify({ session_id: SID, message: text,\n                         member_id, phone_last4, vision })\n}, 40000);"),
    "lineapp": dict(path="แอป LINE บนมือถือลูกค้า → LINE Platform",
        tags=[("ช่องทางที่ 2", "blue"), ("ส่ง webhook มาที่ร้าน", "")],
        what="ลูกค้าแชตกับ LINE OA ของร้าน LINE ส่งข้อความต่อมาที่ <b>/api/line/webhook</b> แล้วได้คำตอบจากบอทตัวเดียวกับหน้าเว็บ",
        code="Webhook URL\nhttps://x-fitness-chatbot.onrender.com/api/line/webhook"),
    "admin": dict(path="x-fitness/frontend/admin/",
        tags=[("5 ไฟล์ · 852 บรรทัด", ""), ("ต้องล็อกอิน", "red")],
        what="หลังบ้านของพนักงาน: กล่องแชตรับเรื่องต่อจากบอท · ยืนยันสลิป · การจอง · โปรโมชัน · คลังความรู้และกราฟความรู้",
        code="admin/index.html   52   โครงหน้า\nadmin/inbox.js    172   กล่องแชต ตอบลูกค้า\nadmin/pages.js    335   สลิป จอง โปร แดชบอร์ด KB\nadmin/admin.js     92   ล็อกอิน เมนู\nadmin/admin.css   201"),
    "main": dict(path="x-fitness/backend/app/main.py",
        tags=[("51 บรรทัด", ""), ("FastAPI", "blue")],
        what="จุดเริ่มของเซิร์ฟเวอร์: รวม router ทุกตัว ตั้ง CORS เสิร์ฟหน้าเว็บ และสั่ง LightRAG สร้างดัชนีเบื้องหลังตอนเปิดเครื่อง",
        code="GET  /api/health\nPOST /api/chat          ← ข้อความจากหน้าเว็บ\nPOST /api/vision        ← ภาพ PNG/JPG ≤ 5 MB\nPOST /api/line/webhook  ← ข้อความจาก LINE\n/api/admin/...          ← หลังบ้าน (ต้องล็อกอิน)\n/                       ← เสิร์ฟ frontend/"),
    "linepy": dict(path="x-fitness/backend/app/line.py",
        tags=[("132 บรรทัด", ""), ("ตรวจลายเซ็น HMAC", "red")],
        what="รับ webhook จาก LINE: ตรวจลายเซ็นก่อน (ผิด = 401) ตอบ 200 ทันทีแล้วทำงานเบื้องหลัง ข้อความไป <b>chat.answer()</b> ภาพไป <b>chat.read_image()</b> ถ้าพนักงานรับเรื่องอยู่ บอทจะเงียบ",
        code="X-Line-Signature → HMAC-SHA256 ตรวจ\nuser id → SHA-256 → เลขเรื่อง (โชว์ในหลังบ้าน)\nข้อความ → chat.answer() → LINE reply API"),
    "backoffice": dict(path="x-fitness/backend/app/backoffice.py",
        tags=[("160 บรรทัด", ""), ("ต้องล็อกอิน", "red")],
        what="API ของหลังบ้าน: เก็บสลิปที่ลูกค้าส่ง 90 วัน · เปลี่ยนสถานะการชำระ การจอง โปรโมชัน · แดชบอร์ด · ล้างข้อมูลทดสอบก่อนสาธิต",
        code="PATCH /api/admin/payments/{id}\nPATCH /api/admin/bookings/{id}\nGET   /api/admin/dashboard\nPOST  /api/admin/test-data/reset   ← กดก่อนสาธิต"),
    "chat": dict(path="x-fitness/backend/app/chat.py",
        tags=[("220 บรรทัด", ""), ("หัวใจของบอท", "red")],
        what="ฟังก์ชัน <b>answer()</b> ใช้ร่วมกันทั้งหน้าเว็บและ LINE: guard ขาเข้า → ยืนยันสมาชิก → LightRAG ค้น → กฎร้านจากโค้ด → Typhoon ตอบ → guard ขาออก",
        code="# guard จับได้ → ตอบเลย ไม่เรียก AI\nif blocked := guard.check_input(text, ...):\n    return blocked\n# FN-xxxxx + เบอร์ 4 ตัวท้าย\nif step := verify_step(text, ...):\n    return step\ncontext, sources = await rag.context(text)\n# กฎร้านที่โค้ดคำนวณ ใส่ใน prompt\nrules = business.rules_for(text, ...)"),
    "guard": dict(path="x-fitness/backend/app/guard.py + data/guard/replies.md",
        tags=[("266 บรรทัด", ""), ("22 ข้อความตอบ", "blue"), ("S1–S14 · N-xx · G-xx", "red")],
        what="ด่านกรองด้วยโค้ด ไม่ใช่ AI: ขาเข้าจับหลอกเปลี่ยนคำสั่ง ถามข้อมูลคนอื่น ขอยา และหมวดอันตราย S1–S14 แล้วตอบด้วยข้อความตายตัวใน 0.4 วินาที ขาออกจับตัวเลข ลิงก์ เวลา หรือเลขบัญชีที่ AI แต่งขึ้น",
        code="## N-07 — หลอกเปลี่ยนคำสั่ง · อ้างเป็นผู้ดูแล\nขออภัยครับ เอ็กซ์ไม่สามารถเปิดเผยหรือเปลี่ยนคำสั่ง\nการทำงานได้ ...\nปุ่ม: ราคาสมาชิก · ตารางคลาส"),
    "business": dict(path="x-fitness/backend/app/business.py + data/db/*.json",
        tags=[("165 บรรทัด", ""), ("15 ไฟล์ข้อมูล", "blue")],
        what="กฎที่ต้องแม่นยำทำด้วยโค้ด ไม่ปล่อยให้ AI คิด: ตรวจสลิป 5 ข้อ · หาข้อมูลสมาชิก · คำนวณแต้ม · โปรไหนหมดเขต ข้อมูลร้านอยู่ในไฟล์ JSON",
        code="members.json      20   schedule.json  29\nbookings.json     16   classes.json    8\npayments.json      7   packages.json   5\npromotions.json    5   trainers.json   6\nsynonyms.json  47 คำ  business.json  ข้อมูลร้าน"),
    "rag": dict(path="x-fitness/backend/app/rag.py → x-fitness/data/rag-index/",
        tags=[("223 บรรทัด", ""), ("LightRAG", "blue"), ("ดัชนี ~10 MB", "")],
        what="ค้นความรู้แบบ <b>mix</b>: กราฟความรู้ 500 entity 551 ความสัมพันธ์ + เวกเตอร์ของ 30 ชิ้นข้อความ แล้วเสริมด้วยค้นคำ (TF-IDF) รายละเอียดอยู่หน้าถัดไป",
        code="QueryParam(mode=\"mix\", chunk_top_k=8, top_k=10)\n→ ชิ้นข้อความที่ตรงที่สุด 8 ชิ้น\n→ ความสัมพันธ์ในกราฟ 10 เส้น\n→ ใส่เป็น \"ข้อมูลอ้างอิง\" ใน prompt"),
    "typhoon": dict(path="api.opentyphoon.ai/v1 (เรียกจาก app/llm.py 39 บรรทัด)",
        tags=[("typhoon-v2.5-30b-a3b-instruct", "blue"), ("typhoon-ocr", "blue")],
        what="AI ภาษาไทยของ SCB 10X เรียกผ่าน httpx ตรง ๆ ไม่ใช้ SDK ใช้ 3 งาน: ตอบแชต · อ่านภาพ (OCR แล้วแปลงเป็น JSON) · สกัด entity ตอนสร้างดัชนี LightRAG",
        code="prompts/system.md  (32 บรรทัด)\nคุณคือ \"เอ็กซ์\" ผู้ช่วยแชตของ เอ็กซ์ ฟิตเนส (X Fitness)\n...\n## ต้องทำ\n- ตอบจาก \"ข้อมูลอ้างอิง\" ด้านล่างเท่านั้น"),
    "db": dict(path="x-fitness/backend/app/db.py → backend/data/xfitness_db.sqlite3",
        tags=[("241 บรรทัด", ""), ("SQLite", "blue")],
        what="เก็บบทสนทนา ข้อความ การผูก LINE user สถานะที่พนักงานแก้ และสลิป เลขเรื่อง 10 ตัวอักษร เช่น K3M8P2Q7R5 ใช้ตามเรื่องในหลังบ้าน",
        code="conversations · messages · line_users\noverrides · uploads · slips"),
}

RAG = {
    "src": dict(path="x-fitness/data/knowledge-base/  (9 ไฟล์ · 62 KB)",
        tags=[("ไฟล์ต้นทาง", "blue"), ("Markdown", "")],
        what="ความรู้ของร้านที่คนเขียน แก้ไฟล์นี้ = บอทรู้ใหม่ เพิ่มไฟล์ได้จากหน้า admin → คลังความรู้",
        code="01_general-hours.md            6.7 KB  เวลาเปิด ที่ตั้ง\n02_membership-pricing.md       9.4 KB  แพ็กเกจ ราคา\n03_classes-schedule.md         9.5 KB  8 คลาส ตาราง\n04_personal-training.md        5.7 KB  PT\n05_membership-policies.md      6.3 KB  พัก ยกเลิก คืนเงิน\n06_payment-slip.md             5.3 KB  ชำระเงิน สลิป\n07_promotions-points-products  8.0 KB  โปร แต้ม สินค้า\n08_gym-rules-safety-privacy    6.9 KB  กฎ ความปลอดภัย\n09_customer-service.md         4.0 KB  ติดต่อพนักงาน"),
    "chunk": dict(path="rag.py → LightRAG(chunk_token_size=500)",
        tags=[("ขั้น 1", "red"), ("30 ชิ้น", "")],
        what="ตัดแต่ละเอกสารเป็นชิ้นละ 500 token ติดรหัสเอกสารไว้หน้าชิ้น ทำเฉพาะเอกสารที่เปลี่ยน (เทียบ hash ใน manifest.json)",
        code="[KB-02] แพ็กเกจสมาชิก ราคา และเงื่อนไขการสมัคร\n\n# แพ็กเกจสมาชิก\nค่าสมาชิก (ราคาแพ็กเกจ) ค่าสมาชิกรายเดือน รายปี\nและรายวัน มีดังนี้ เอ็กซ์ ฟิตเนส มีแพ็กเกจสมาชิก 5 แบบ ..."),
    "extract": dict(path="Typhoon typhoon-v2.5-30b-a3b-instruct",
        tags=[("ขั้น 2", "red"), ("ใช้ AI", "blue")],
        what="ให้ AI อ่านทีละชิ้นแล้วดึง <b>entity</b> (สิ่งของ คน แพ็กเกจ) และ <b>ความสัมพันธ์</b> ระหว่างกัน ได้ 500 entity 551 ความสัมพันธ์ ผลที่ AI ตอบเก็บใน cache เพื่อไม่ต้องจ่ายซ้ำ",
        code="addon_params={\"language\": \"Thai\"}\nllm_model_func=_llm   # เรียก Typhoon"),
    "embed": dict(path="rag.py → hash_embed()  thai-word-hash:1024",
        tags=[("ขั้น 3", "red"), ("ไม่ใช้ AI · ไม่เสียเงิน", "ok")],
        what="แปลงข้อความเป็นเวกเตอร์ 1,024 มิติด้วยการ hash คำไทย (ตัดคำด้วย PyThaiNLP) + กลุ่มตัวอักษร + คำพ้องใน synonyms.json ทำในเครื่อง ไม่ต้องมี API key ถ้าใส่ XF_EMBED_API_KEY จะสลับไปใช้ gemini-embedding-001",
        code="EmbeddingFunc(embedding_dim=1024, func=_embed)\n\"embedder\": \"thai-word-hash:1024:chunk500:synfb9fdb23\""),
    "graphml": dict(path="rag-index/graph_chunk_entity_relation.graphml  (624 KB)",
        tags=[("ไฟล์ปลายทาง", "ok"), ("500 โหนด · 551 เส้น", "")],
        what="กราฟความรู้ แต่ละโหนดคือ entity พร้อมคำอธิบายและชิ้นข้อความที่มา แต่ละเส้นคือความสัมพันธ์ ดูเป็นภาพได้ที่ admin → กราฟความรู้",
        code="<node id=\"เอ็กซ์ ฟิตเนส\">\n  <data key=\"d1\">organization</data>\n  <data key=\"d2\">สตูดิโอฟิตเนสขนาดเล็กที่มีสาขาเดียว\n    ตั้งอยู่ใจกลางศรีราชา ...</data>\n  <data key=\"d3\">KB-02-chunk-000<SEP>KB-01-chunk-000</data>\n<edge source=\"เอ็กซ์ ฟิตเนส\" target=\"บัตรรายวัน\">\n  <data key=\"d8\">... บัตรรายวัน ราคา 150 บาทต่อครั้ง</data>"),
    "vdb": dict(path="rag-index/vdb_chunks.json · vdb_entities.json · vdb_relationships.json",
        tags=[("ไฟล์ปลายทาง", "ok"), ("281 KB · 3.26 MB · 3.56 MB", "")],
        what="เวกเตอร์ของชิ้นข้อความ 30 · entity 500 · ความสัมพันธ์ 551 ใช้หาสิ่งที่ความหมายใกล้คำถาม เวกเตอร์เก็บเป็น base64 เพื่อประหยัดที่",
        code="{\"embedding_dim\": 1024,\n \"data\": [{\"__id__\": \"KB-02-chunk-000\",\n           \"content\": \"[KB-02] แพ็กเกจสมาชิก ...\",\n           \"vector\": \"eJxVVTuII0cQbTCC49bBZjaH...\"}],\n \"matrix\": \"DwJXvA8CV7wPAle8...\"}"),
    "kv": dict(path="rag-index/kv_store_*.json  (8 ไฟล์)",
        tags=[("ไฟล์ปลายทาง", "ok"), ("cache 2.3 MB", "")],
        what="ตารางคู่ key-value: ข้อความเต็มของแต่ละชิ้น · เอกสารเต็ม · entity ไหนมาจากชิ้นไหน · สถานะการสร้างดัชนี · cache คำตอบของ AI 459 รายการ",
        code="kv_store_text_chunks.json      84 KB  30 ชิ้น\nkv_store_full_docs.json        64 KB   9 เอกสาร\nkv_store_entity_chunks.json   125 KB  entity → ชิ้น\nkv_store_relation_chunks.json 172 KB  เส้น → ชิ้น\nkv_store_llm_response_cache  2.30 MB  459 รายการ\nmanifest.json                 509 B   hash ของ 9 เอกสาร"),
    "query": dict(path="ตอนลูกค้าถาม: rag.context(คำถาม)",
        tags=[("mix mode", "blue"), ("+ ค้นคำ TF-IDF", "")],
        what="คำถามถูกแปลงเป็นเวกเตอร์แบบเดียวกัน แล้วหาทั้งชิ้นข้อความที่ใกล้ (8 ชิ้น) และความสัมพันธ์ในกราฟ (10 เส้น) เสริมด้วยค้นคำแบบ 2–3 ตัวอักษร ผลที่ได้กลายเป็น \"ข้อมูลอ้างอิง\" ที่ AI ต้องตอบตาม",
        code="คำถาม: \"PT 10 ครั้งราคาเท่าไหร่\"\n→ KB-04-chunk-000  (แพ็กเกจ PT)\n→ PT 10 ครั้ง —ราคา→ 8,000 บาท\n→ Typhoon ตอบ: \"แพ็กเกจ PT 10 ครั้ง ราคา 8,000 บาท ...\""),
}

TREE = {
    "root": dict(path="x-fitness/", tags=[("Render rootDir", "blue")],
        what="แอปทั้งตัวอยู่โฟลเดอร์เดียว Render ใช้โฟลเดอร์นี้ deploy เป็นบริการเดียว ฟรี ที่สิงคโปร์",
        code="buildCommand: pip install -r backend/requirements.txt\nstartCommand: cd backend && uvicorn app.main:app\nhealthCheckPath: /api/health"),
    "app": dict(path="x-fitness/backend/app/  (15 ไฟล์ · 1,911 บรรทัด)", tags=[("Python · FastAPI", "blue")],
        what="โค้ดฝั่งเซิร์ฟเวอร์ แยก 1 ไฟล์ 1 หน้าที่",
        code="main.py 51        chat.py 220      guard.py 266\nrag.py 223        business.py 165  line.py 132\nbackoffice.py 160 db.py 241        llm.py 39\nconfig.py 56      limits.py 72     auth.py 26\nknowledge.py 72   keyword_search.py 81\nconversations.py 107"),
    "prompts": dict(path="x-fitness/backend/app/prompts/", tags=[("3 ไฟล์", "")],
        what="คำสั่งที่ส่งให้ AI แยกจากโค้ด แก้ได้โดยไม่แตะ Python",
        code="system.md  32 บรรทัด  บุคลิก + ต้องทำ/ห้ามทำ\nvision.md  15 บรรทัด  ข้อความจากภาพ → JSON\nocr.md      1 บรรทัด  อ่านข้อความทั้งหมดในภาพ"),
    "tests": dict(path="x-fitness/backend/tests/ · e2e/", tags=[("pytest 98 ฟังก์ชัน", "ok"), ("Playwright 40 กรณี", "ok")],
        what="ทดสอบ 2 ระดับ: pytest ทดสอบโค้ดทีละส่วน · Playwright เปิดเบราว์เซอร์จริง พิมพ์และแนบภาพเหมือนลูกค้า แล้วเก็บภาพหน้าจอทุกกรณี",
        code="test_bot 43  test_backoffice 13  test_line 9\ntest_conversations 8  test_limits 8\ntest_guard14 7  test_knowledge 7  test_guard_replies 3\n\ne2e: npm test → 40 กรณี ~3 นาที"),
    "frontend": ARCH["web"] | dict(path="x-fitness/frontend/  (index.html · admin/ · shared/)"),
    "kb": RAG["src"],
    "db": ARCH["business"],
    "guarddata": dict(path="x-fitness/data/guard/replies.md", tags=[("12.9 KB · 22 หัวข้อ", "")],
        what="ข้อความตอบตายตัวของ guard ทุกกฎ พร้อมปุ่มตอบด่วน แก้ถ้อยคำได้โดยไม่แตะโค้ด",
        code=ARCH["guard"]["code"]),
    "ragindex": RAG["kv"] | dict(path="x-fitness/data/rag-index/  (13 ไฟล์ · ~10 MB)", what="ดัชนี LightRAG ที่สร้างแล้ว commit ไว้ใน git เพื่อให้ Render เปิดเครื่องแล้วใช้ได้ทันที ไม่ต้องเรียก AI สร้างใหม่"),
    "images": dict(path="x-fitness/qa/", tags=[("5 ภาพหลัก + 63 ภาพเสริม", "")],
        what="ภาพทดสอบ: สลิปถูก · สลิปยอดไม่ตรง · ผลวัดร่างกาย · ใบเสร็จ · โปสเตอร์โปรหมดเขต (ใช้ในหน้าสาธิตภาพ)",
        code="01_slip_valid.png\n02_slip_amount_mismatch.png\n03_body_scan.png\n04_receipt.png\n05_promo_poster_expired.png"),
}

# demo extras the results file does not hold: which cases to run live, and the image used
LIVE = {"Q03", "Q09", "Q10", "I01", "I05", "S01", "S03"}
# architecture diagram (page "arch"): boxes, arrows and the walk-through. Checked against the imports in
# x-fitness/backend/app/*.py on 2026-10-10: chat → guard · business · rag · llm · db · backoffice, rag → llm (Typhoon),
# business → db, line → chat. Columns: 0 channel · 1 entry · 2 bot · 3 helpers · 4 storage / outside.
ARCH_NODES = [  # key, title, file, column, row (0–4), outside system?
    ("web", "หน้าเว็บลูกค้า", "frontend/index.html", 0, 0, False),
    ("lineapp", "LINE OA", "มือถือลูกค้า", 0, 2, True),
    ("admin", "หลังบ้าน", "frontend/admin/", 0, 4, False),
    ("main", "API", "main.py", 1, 0, False),
    ("linepy", "LINE webhook", "line.py", 1, 2, False),
    ("backoffice", "API หลังบ้าน", "backoffice · conversations", 1, 4, False),
    ("chat", "บอท answer()", "chat.py", 2, 2, False),
    ("guard", "Guardrail", "guard.py", 3, 0, False),
    ("rag", "LightRAG", "rag.py", 3, 1, False),
    ("llm", "เรียก AI", "llm.py", 3, 2, False),
    ("business", "กฎร้าน", "business.py", 3, 3, False),
    ("db", "SQLite", "db.py · data/db", 3, 4, False),
    ("ragindex", "ดัชนี", "rag-index/", 4, 1, False),
    ("typhoon", "Typhoon AI", "api.opentyphoon.ai", 4, 2, True),
]
ARCH_EDGES = [  # from, to
    ("web", "main"), ("lineapp", "linepy"), ("admin", "backoffice"),
    ("main", "chat"), ("linepy", "chat"), ("backoffice", "db"),
    ("chat", "guard"), ("chat", "rag"), ("chat", "llm"), ("chat", "business"), ("chat", "db"),
    ("rag", "ragindex"), ("rag", "typhoon"), ("llm", "typhoon"), ("business", "db"),
]
ARCH_TOUR = [  # edges lit in turn (from>to, "<" = travelling back, "|" = at the same time), box to open, what to say
    (["web>main|lineapp>linepy"], "web", "ลูกค้าพิมพ์ในหน้าเว็บ (POST /api/chat) หรือใน LINE (webhook ตรวจลายเซ็นก่อน) เข้าพร้อมกันได้"),
    (["main>chat|linepy>chat"], "chat", "ทั้ง 2 ทางจำกัด 30 ข้อความ/นาที แล้วเรียก chat.answer() ฟังก์ชันเดียวกัน"),
    (["chat>guard"], "guard", "① guard ขาเข้า: ตรวจข้อความนี้รวมกับ 2 ข้อความก่อนหน้า ถ้าหลอกหรืออันตราย ตอบข้อความตายตัวแล้วจบตรงนี้"),
    (["chat>business"], "business", "② ยืนยันสมาชิก: ถ้าพิมพ์รหัส FN-xxxxx ตรวจกับเบอร์ 4 ตัวท้าย"),
    (["chat>rag"], "rag", "③ LightRAG ค้นคลังความรู้"),
    (["rag>typhoon"], "typhoon", "LightRAG ให้ Typhoon ดึงคำสำคัญของคำถาม (เก็บ cache ไว้)"),
    (["rag>ragindex"], "ragindex", "ค้นกราฟความรู้และเวกเตอร์ใน rag-index/ → ข้อมูลอ้างอิง"),
    (["chat>business", "business>db"], "business", "④ กฎร้านจากโค้ด: ตรวจสลิป 5 ข้อ แต้ม โปรหมดเขต จากข้อมูลร้าน"),
    (["chat>db"], "db", "อ่าน 8 ข้อความล่าสุดของแชตนี้จาก SQLite"),
    (["chat>llm", "llm>typhoon"], "typhoon", "⑤ Typhoon เขียนคำตอบจาก system.md + ข้อมูลอ้างอิง + กฎร้าน"),
    (["chat>guard"], "guard", "⑥ guard ขาออก: ตัดตัวเลข ลิงก์ เวลา เลขบัญชี ที่ AI แต่งขึ้น"),
    (["main<chat|linepy<chat", "web<main|lineapp<linepy"], "web", "คำตอบย้อนกลับทางเดิม: หน้าเว็บได้คำตอบ + เอกสารอ้างอิง + รหัสกฎ · LINE ได้ผ่าน reply API"),
    (["admin>backoffice", "backoffice>db"], "backoffice", "พนักงานเห็นแชตและสลิปในหลังบ้าน แล้วตอบต่อได้"),
]

# rag-index/ file → what it holds (sizes are read from disk at build time)
INDEX_DESC = {
    "graph_chunk_entity_relation.graphml": "กราฟความรู้: 500 โหนด 551 เส้น",
    "vdb_chunks.json": "เวกเตอร์ของชิ้นข้อความ 30 ชิ้น",
    "vdb_entities.json": "เวกเตอร์ของ entity 500 ตัว",
    "vdb_relationships.json": "เวกเตอร์ของความสัมพันธ์ 551 เส้น",
    "kv_store_text_chunks.json": "ข้อความเต็มของ 30 ชิ้น",
    "kv_store_full_docs.json": "เอกสารเต็ม 9 ไฟล์",
    "kv_store_full_entities.json": "entity ของแต่ละเอกสาร",
    "kv_store_full_relations.json": "ความสัมพันธ์ของแต่ละเอกสาร",
    "kv_store_entity_chunks.json": "entity → มาจากชิ้นไหน",
    "kv_store_relation_chunks.json": "เส้น → มาจากชิ้นไหน",
    "kv_store_doc_status.json": "สถานะการสร้างดัชนีรายเอกสาร",
    "kv_store_llm_response_cache.json": "cache คำตอบ AI 459 รายการ ไม่ต้องจ่ายซ้ำ",
    "manifest.json": "ชื่อ embedder + hash ของ 9 เอกสาร",
}
GRAPH_CENTER = "เอ็กซ์ ฟิตเนส"
GRAPH_STORY = dict(   # page 18: one real question followed through two edges of rag-index/graph_chunk_entity_relation.graphml
    q="แพ็กนักเรียนปั่นจักรยานได้ไหม", src="KB-02 · KB-03", hub="นักเรียน/นักศึกษา", hit="Ride", hit_label="เข้าไม่ได้",
    more=[("Yoga Flow", "เข้าได้"), ("Boxing Fit", "เข้าได้"), ("Dance Cardio", "เข้าได้"), ("ค่าแรกเข้า", "ไม่ต้องจ่าย"),
          ("ค่าธรรมเนียมยกเลิก 500 บาท", "ยกเลิกก่อน 6 เดือน")],
    names={"ค่าธรรมเนียมยกเลิก 500 บาท": "ค่ายกเลิก 500 บาท", "นักเรียน/นักศึกษา": "นักเรียน/นักศึกษา"},
    what='เริ่มที่จุด <b>นักเรียน/นักศึกษา</b> แล้วเดินเส้น <b>ไม่สามารถเข้าร่วม → Ride</b> '
         'บอทจึงตอบว่าเข้า Ride ไม่ได้ และบอกต่อได้ว่าคลาสไหนเข้าได้')
MEMBER_HINT = {"I01": "พิมพ์ก่อน: FN-10003 5531 (ยืนยันสมาชิก)", "I02": "พิมพ์ก่อน: FN-10007 3364 (ยืนยันสมาชิก)"}

# boxes added when the diagram was checked against the imports
ARCH["llm"] = dict(path="x-fitness/backend/app/llm.py", tags=[("39 บรรทัด", ""), ("httpx ไม่ใช้ SDK", "blue")],
    what="ตัวกลางเรียก Typhoon: <b>chat()</b> สำหรับตอบแชต และ <b>vision()</b> สำหรับอ่านภาพ ถ้าเรียกไม่สำเร็จ ส่ง LLMError ให้หน้าเว็บแจ้งลูกค้า",
    code="POST https://api.opentyphoon.ai/v1/chat/completions\nmodel: typhoon-v2.5-30b-a3b-instruct  (แชต)\nmodel: typhoon-ocr                     (อ่านภาพ)")
ARCH["ragindex"] = RAG["kv"] | dict(path="x-fitness/data/rag-index/  (13 ไฟล์ · ~10 MB)",
    what="ดัชนีที่ LightRAG สร้างไว้: กราฟความรู้ 500 entity · เวกเตอร์ 1,024 มิติ · ข้อความ 30 ชิ้น อ่านทุกครั้งที่ค้น")
ARCH["backoffice"] = ARCH["backoffice"] | dict(path="x-fitness/backend/app/backoffice.py · conversations.py · knowledge.py",
    what="API ของหลังบ้าน: กล่องแชต (conversations.py) · สลิป การจอง โปรโมชัน แดชบอร์ด (backoffice.py) · คลังความรู้ (knowledge.py) ทุกตัวต้องล็อกอิน")

# inner content of the two big boxes on the vision flowchart (facts from prompts/vision.md and business.check_slip)
VISION_TYPES = ('<table class="ftab">'
    '<tr><td><i>slip</i> สลิป</td><td>ยอด · ผู้รับ · เลขบัญชี · วันเวลา · เลขอ้างอิง</td><td>→ ④ ตรวจ 5 ข้อ</td></tr>'
    '<tr><td><i>receipt</i> ใบเสร็จ</td><td>เลขที่ · วันที่ · รายการ · ยอดรวม</td><td>→ answer()</td></tr>'
    '<tr><td><i>body_scan</i> ผลวัด</td><td>น้ำหนัก · กล้ามเนื้อ · ไขมัน · BMI · BMR</td><td>→ บอกค่า ไม่ประเมิน</td></tr>'
    '<tr><td><i>promo_poster</i> โปสเตอร์</td><td>ชื่อโปร · โค้ด · วันเริ่ม–หมดเขต</td><td>→ เทียบกับวันนี้</td></tr>'
    '<tr><td><i>other</i> ภาพอื่น</td><td>สรุปสั้น ๆ + ข้อความที่อ่านได้</td><td>→ answer()</td></tr></table>')
SLIP_CHECKS = ('<ol class="flist"><li>ชื่อบัญชีผู้รับเป็น <em>บจก. เอ็กซ์ ฟิตเนส</em></li><li>เลขบัญชีผู้รับลงท้าย <em>4521-0</em></li>'
    '<li>ยอดเงิน<em>ตรงกับยอดค้าง</em>ของสมาชิก</li><li>วันที่โอนห่างวันครบกำหนด<em>ไม่เกิน 7 วัน</em></li>'
    '<li>เลขอ้างอิง<em>ไม่เคยใช้</em>กับสลิปอื่น</li></ol><p class="fnote">ยืนยันสมาชิกก่อน · สลิป "โอนไม่สำเร็จ" ไม่ผ่านเสมอ</p>')
# flowcharts. Each: box size, canvas size, boxes (key, title, sub, x, y, shape) and arrows (from, to, label, "bus" = route
# along the bottom back to the end box). shape: end · step · check (can stop the message) · exit · data · ext (outside system).
# Arrows are drawn by build.py: same row → straight · target lower → down first · target higher → across first.
FLOWS = {
  "flow": dict(w=1664, h=492, nw=170, nh=88, nodes=[      # chat.answer(), checked against app/chat.py
    ("in", "ข้อความเข้า", "เว็บ หรือ LINE", 0, 190, "end"),
    ("g1", "① guard ขาเข้า", "check_input", 210, 190, "check"),
    ("g2", "② ยืนยันสมาชิก", "verify_step", 420, 190, "check"),
    ("rag", "③ LightRAG ค้น", "rag.context", 630, 190, "step"),
    ("rules", "④ กฎร้าน", "rules_for · check_slip", 840, 190, "step"),
    ("llm", "⑤ Typhoon ตอบ", "llm.chat", 1050, 190, "step"),
    ("g6", "⑥ guard ขาออก", "check_output", 1260, 190, "check"),
    ("out", "ส่งคำตอบ", "+ ปุ่มตอบด่วน", 1470, 190, "end"),
    ("x1", "ตอบข้อความตายตัว", "replies.md · ไม่เรียก AI", 210, 370, "exit"),
    ("x2", "ถาม/ยืนยันรหัส", "FN-xxxxx + เบอร์ 4 ตัว", 420, 370, "exit"),
    ("x6", "ตอบข้อความปลอดภัย", "+ ปุ่มคุยกับพนักงาน", 1260, 370, "exit"),
    ("idx", "rag-index/", "กราฟ + เวกเตอร์", 630, 0, "data"),
    ("db", "ข้อมูลร้าน", "data/db · SQLite", 840, 0, "data"),
    ("ty", "Typhoon API", "+ system.md", 1050, 0, "ext")],
   edges=[("in", "g1", ""), ("g1", "g2", "ผ่าน"), ("g2", "rag", ""), ("rag", "rules", ""), ("rules", "llm", ""),
    ("llm", "g6", ""), ("g6", "out", "ผ่าน"), ("g1", "x1", "จับได้"), ("g2", "x2", "พิมพ์รหัส"), ("g6", "x6", "แต่ง/ผิดกฎ"),
    ("x1", "out", "", "bus"), ("x2", "out", "", "bus"), ("x6", "out", "", "bus"),
    ("idx", "rag", ""), ("db", "rules", ""), ("ty", "llm", "")]),
  "rag": dict(w=1664, h=424, nw=250, nh=66, nodes=[       # app/rag.py: reindex() at start-up, context() per question
    ("kb", "เอกสาร 9 ฉบับ", "KB-01–KB-09 · 62 KB", 0, 0, "data"),
    ("chunk", "① หั่นเป็นท่อน", "500 token ซ้อน 100 → 30 ท่อน", 350, 0, "step"),
    ("extract", "② Typhoon ดึง entity", "500 entity · 551 ความสัมพันธ์", 700, 0, "ext"),
    ("embed", "③ hash embedding", "1,024 มิติ ในเครื่อง ไม่ใช้โมเดล", 1050, 0, "step"),
    ("store", "rag-index/", "กราฟ .graphml + เวกเตอร์ 3 ชุด", 1400, 0, "data"),
    ("q", "คำถามลูกค้า", "ข้อความเดิมของลูกค้า", 0, 220, "end"),
    ("kw", "Typhoon แตกคำค้น", "คำหัวข้อ + ชื่อเฉพาะ · มี cache", 350, 220, "ext"),
    ("local", "local · เดินกราฟจาก entity", "ชื่อเฉพาะ → entity → เส้นรอบ ๆ", 700, 112, "step"),
    ("global", "global · ค้นความสัมพันธ์", "คำหัวข้อ → ความสัมพันธ์ที่ใกล้", 700, 184, "step"),
    ("naive", "naive · เวกเตอร์ของท่อน", "ทั้งประโยค → ท่อนที่ใกล้", 700, 256, "step"),
    ("kws", "ค้นด้วยคำ (โค้ดของเรา)", "คำเดิมของลูกค้า ไม่ผ่าน AI", 700, 328, "step"),
    ("ctx", "รวมเป็นข้อมูลอ้างอิง", "8 ท่อน + เส้น ≤ 10 + ค้นคำ 2 ท่อน", 1050, 220, "step"),
    ("ans", "Typhoon ตอบ", "รหัส KB-xx แสดงใต้คำตอบ", 1400, 220, "ext")],
   edges=[("kb", "chunk", ""), ("chunk", "extract", ""), ("extract", "embed", ""), ("embed", "store", ""),
    ("q", "kw", ""), ("kw", "local", "", "across"), ("kw", "global", "", "across"), ("kw", "naive", "", "across"), ("q", "kws", "", "bus"),
    ("local", "ctx", "", "across"), ("global", "ctx", "", "across"), ("naive", "ctx", "", "across"), ("kws", "ctx", "", "across"),
    ("ctx", "ans", ""), ("store", "local", "อ่านดัชนี")]),
  "vision": dict(w=1664, h=484, nw=210, nh=64, nodes=[    # chat.vision() + read_image() + answer(), business.check_slip()
    ("img", "ภาพจากลูกค้า", "เว็บ หรือ LINE", 0, 0, "end"),
    ("gate", "① ตรวจไฟล์", "PNG/JPG ≤ 5 MB", 262, 0, "check"),
    ("ocr", "② typhoon-ocr", "อ่านตัวอักษร · ลองซ้ำ 1 ครั้ง", 524, 0, "ext"),
    ("json", "③ จัดเป็น JSON", "Typhoon เลือกชนิด + ดึงช่อง", 786, 0, "ext"),
    ("type", "ภาพชนิดไหน", "Typhoon เลือก 1 ชนิด", 1050, 0, "check", dict(w=614, h=220, html=VISION_TYPES)),
    ("slip", "④ ตรวจสลิป 5 ข้อ", "check_slip() · โค้ด ไม่ใช่ AI", 1050, 270, "step", dict(w=430, h=214, html=SLIP_CHECKS)),
    ("pass", "ผ่านครบ 5/5", "รอพนักงานยืนยัน", 1510, 270, "exit", dict(w=154, h=96)),
    ("fail", "ไม่ผ่าน", "บอกยอดที่ขาด + ปุ่มพนักงาน", 1510, 388, "exit", dict(w=154, h=96)),
    ("answer", "④ answer() ตอบ", "ตัวเลขในภาพ + ข้อมูลร้าน", 524, 300, "step"),
    ("gout", "⑤ guard ขาออก", "ตัดตัวเลขที่ไม่มีที่มา", 262, 300, "check"),
    ("reply", "ส่งคำตอบ", "+ ปุ่มพนักงานถ้าต้องส่งต่อ", 0, 300, "end"),
    ("xfile", "ปฏิเสธไฟล์", "ชนิดผิด · เกิน 5 MB · ส่งถี่", 262, 130, "exit"),
    ("xocr", "อ่านภาพไม่สำเร็จ", "OCR ขัดข้อง 2 ครั้ง → ส่งใหม่", 524, 130, "exit")],
   edges=[("img", "gate", ""), ("gate", "ocr", "ผ่าน"), ("ocr", "json", ""), ("json", "type", ""),
    ("type", "slip", "slip"), ("slip", "pass", "", "across"), ("slip", "fail", "", "across"),
    ("type", "answer", "ชนิดอื่น", "across"), ("answer", "gout", ""), ("gout", "reply", ""),
    ("gate", "xfile", "ไม่ผ่าน"), ("ocr", "xocr", "ขัดข้อง")]),
  "line": dict(w=1664, h=500, nw=184, nh=92, nodes=[      # app/line.py
    ("user", "ลูกค้า LINE", "ข้อความหรือภาพ", 0, 210, "end"),
    ("plat", "LINE Platform", "ส่ง webhook", 210, 210, "ext"),
    ("sig", "① ลายเซ็น", "HMAC ถูกไหม", 420, 210, "check"),
    ("ack", "② ตอบ 200", "ทำต่อเบื้องหลัง", 630, 210, "step"),
    ("ticket", "③ เลขเรื่อง", "user id → SHA-256", 840, 210, "step"),
    ("busy", "④ พนักงานรับ", "waiting/agent", 1050, 210, "check"),
    ("bot", "⑤ answer()", "ภาพ → read_image", 1260, 210, "step"),
    ("reply", "⑥ reply API", "ตอบใน LINE", 1470, 210, "end"),
    ("x401", "ปฏิเสธ 401", "ไม่ใช่ LINE ส่งมา", 420, 390, "exit"),
    ("quiet", "บอทเงียบ", "พนักงานตอบด้วย push", 1050, 390, "exit"),
    ("inbox", "กล่องแชตหลังบ้าน", "เห็นทุกข้อความ", 840, 20, "data")],
   edges=[("user", "plat", ""), ("plat", "sig", ""), ("sig", "ack", "ถูก"), ("ack", "ticket", ""), ("ticket", "busy", ""),
    ("busy", "bot", "ไม่"), ("bot", "reply", ""), ("sig", "x401", "ผิด"), ("busy", "quiet", "ใช่"), ("ticket", "inbox", "บันทึก")]),
}
FLOW_WALKS = {   # walks that do not come from the test results (facts from the code)
  "rag": [("สร้างดัชนี (ตอนเปิดเครื่อง)", [
      (None, "kb", "ok", "อ่าน 9 ไฟล์ เฉพาะไฟล์ที่ hash เปลี่ยนจาก manifest.json"),
      ("kb-chunk", "chunk", "ok", "หั่นท่อนละ 500 token ซ้อนกัน 100 ได้ 30 ท่อน"),
      ("chunk-extract", "extract", "hit", "Typhoon อ่านทีละท่อน ดึง entity 500 ตัว ความสัมพันธ์ 551 เส้น เช่น นักเรียน/นักศึกษา → ไม่สามารถเข้าร่วม → Ride"),
      ("extract-embed", "embed", "ok", "แปลงท่อน entity และความสัมพันธ์เป็นเวกเตอร์ 1,024 มิติในเครื่อง ไม่ใช้ AI"),
      ("embed-store", "store", "ok", "เขียนกราฟ เวกเตอร์ 3 ชุด และ cache ลง rag-index/ 13 ไฟล์ commit มากับโค้ด")]),
    ('"แพ็กนักเรียนปั่นจักรยานได้ไหม"', [   # keywords from rag-index/kv_store_llm_response_cache.json; hits from running
      # rag.context's search offline on the committed index (cache hits only, no Typhoon call), 10/10/2569
      (None, "q", "ok", '"แอดมินคะ แพ็กนักเรียนปั่นจักรยานได้ไหม"'),
      ("q-kw", "kw", "hit", "Typhoon คืนคำค้น 2 ชุด · คำหัวข้อ (เรื่องที่ถาม ใช้หาเส้นในกราฟ): การขี่จักรยาน, กิจกรรมนักเรียน · ชื่อเฉพาะ (ใช้หาวงกลม): แพ็กนักเรียน",
       {"kw": "หัวข้อ: การขี่จักรยาน, กิจกรรมนักเรียน · ชื่อเฉพาะ: แพ็กนักเรียน"}),
      ("kw-local|kw-global|kw-naive|q-kws|store-local", "local|global|naive|kws|store", "ok",
       "ค้น 4 ทางพร้อมกันจาก rag-index/ ได้กลับมา: entity 18 ตัว · ความสัมพันธ์ 26 เส้น · ท่อนข้อความ 7 ท่อน · ค้นคำ 2 ท่อน",
       {"local": "entity: นักเรียน/นักศึกษา · บัตรนักเรียน · Student · อายุ 15–25 ปี · คลาส Ride",
        "global": "เส้น: นักเรียน/นักศึกษา เข้า Ride ไม่ได้ · เข้า Boxing Fit, Yoga Flow ได้",
        "naive": "ท่อน 7: KB-02 แพ็กนักศึกษา · KB-03 ใครเข้าคลาสได้ · KB-01, 04, 05",
        "kws": "KB-03 ใครเข้าคลาสได้บ้าง · KB-04 โค้ชของเรา (คะแนน 0.18 ทั้งคู่)"}),
      ("local-ctx|global-ctx|naive-ctx|kws-ctx", "ctx", "ok",
       "รวมให้พอดี prompt: ท่อนข้อความ 7 + ความสัมพันธ์ 10 เส้นแรก + ค้นคำ 2 ท่อน เนื้อเอกสารขึ้นก่อน แล้วตามด้วยเส้นจากกราฟ",
       {"ctx": "KB-03 · KB-01 · KB-02 · KB-04 · KB-05 + 10 เส้น"}),
      ("ctx-ans", "ans", "hit", '"นักเรียน/นักศึกษาใช้แพ็กเกจนี้เข้าคลาส Ride (ปั่นจักรยาน) ไม่ได้ครับ แต่เข้าคลาสอื่นได้ 7 คลาส"')])],
  "line": [("ข้อความปกติ", [
      (None, "user", "ok", "ลูกค้าพิมพ์ในแชต 1:1 ของ LINE OA"), ("user-plat", "plat", "ok", "LINE ส่ง webhook มาที่ร้าน"),
      ("plat-sig", "sig", "ok", "ลายเซ็นถูก"), ("sig-ack", "ack", "ok", "ตอบ 200 ทันที แล้วทำงานเบื้องหลัง"),
      ("ack-ticket", "ticket", "ok", "แปลง user id เป็นเลขเรื่อง"), ("ticket-inbox", "inbox", "ok", "บันทึกข้อความให้พนักงานเห็น"),
      ("ticket-busy", "busy", "ok", "ไม่มีพนักงานรับเรื่อง"), ("busy-bot", "bot", "hit", "เรียก chat.answer() ตัวเดียวกับหน้าเว็บ"),
      ("bot-reply", "reply", "ok", "ส่งคำตอบผ่าน reply API")]),
    ("พนักงานรับเรื่องอยู่", [
      (None, "user", "ok", "ลูกค้าพิมพ์ต่อหลังกด \"คุยกับพนักงาน\""), ("user-plat", "plat", "ok", "LINE ส่ง webhook"),
      ("plat-sig", "sig", "ok", "ลายเซ็นถูก"), ("sig-ack", "ack", "ok", "ตอบ 200 ทันที"), ("ack-ticket", "ticket", "ok", "หาเลขเรื่องเดิม"),
      ("ticket-inbox", "inbox", "ok", "ข้อความขึ้นในกล่องแชต"), ("ticket-busy", "busy", "stop", "สถานะ waiting/agent"),
      ("busy-quiet", "quiet", "hit", "บอทไม่ตอบ พนักงานตอบจากหลังบ้าน ส่งด้วย push")]),
    ("ข้อความปลอม", [
      (None, "user", "ok", "มีคนยิงเข้า webhook เอง ไม่ผ่าน LINE"), ("plat-sig", "sig", "stop", "ลายเซ็นไม่ตรง"),
      ("sig-x401", "x401", "hit", "ตอบ 401 ไม่ทำอะไรต่อ")])],
}
FLOW_CASES = [("Q07", "ถามราคา"), ("N-01", "ถามสิ่งที่ร้านไม่มี"), ("S01", "หลอกขอ system prompt"),
              ("I02", "ส่งสลิปยอดไม่ครบ"), ("FN-10003 5531", "ยืนยันสมาชิก")]

# code shown under each architecture box: read from the real files at build time, so it never drifts from the code.
# (file under x-fitness/backend/app, regex of the first line, number of lines — None = every line that matches)
ARCH_CODE = {
    "main": [("main.py", r"^@asynccontextmanager", 6), ("main.py", r"^app\.include_router\(conversations\.customer", 7)],
    "linepy": [("line.py", r"^async def webhook", 11)],
    "chat": [("chat.py", r"^async def answer", 1), ("chat.py", r"^    if blocked := guard\.check_input", 4),
             ("chat.py", r"^        context, sources = await rag\.context", 1), ("chat.py", r"^    if rules := business\.rules_for", 1),
             ("chat.py", r"^            slip = business\.check_slip", 1), ("chat.py", r"^    system = prompt\(", 2),
             ("chat.py", r"^    reply, rules = guard\.check_output", 1), ("chat.py", r"^    needs_staff = ", 1)],
    "guard": [("guard.py", r"^def check_input", 1), ("guard.py", r"^    for rules, pattern, answer, quick", 11), ("guard.py", r"^def _forms", 1),
              ("guard.py", r"^    plain = unicodedata", 3)],
    "business": [("business.py", r"^def check_slip", 1), ("business.py", r"^    checks = \[", 7)],
    "rag": [("rag.py", r"^async def context", 1), ("rag.py", r"^    rag = await _get\(\)", 4), ("rag.py", r"^    if relations:", 3)],
    "llm": [("llm.py", r"^def chat", 5), ("llm.py", r"^def _post", 6)],
    "db": [("db.py", r"^CREATE TABLE IF NOT EXISTS", None)],
    "backoffice": [("backoffice.py", r"^@router\.(get|patch|post)", None)],
}
