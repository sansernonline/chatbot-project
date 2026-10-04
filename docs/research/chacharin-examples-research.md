# Research: ตัวอย่างแชตบอทจาก GitHub ของ chacharin

> อ่านเมื่อ 4 ต.ค. 2569 จาก branch `main` ของทั้ง 4 repo · อ่านโค้ดอย่างเดียว ไม่ได้รัน

## สรุป 5 บรรทัด

1. ไม่มี repo ไหนฝัง LightRAG ไว้ในโค้ดแอปตัวเอง — [2] รัน LightRAG เป็นเซิร์ฟเวอร์ใน Docker ส่วน [3] เรียกเซิร์ฟเวอร์นั้นผ่าน HTTP
2. ทุก repo เรียก LLM ผ่าน OpenRouter ซึ่งเป็น API แบบเดียวกับ OpenAI (OpenAI-compatible) · embedding ใช้ `openai/text-embedding-3-large` [2]
3. Vision ที่ง่ายที่สุดอยู่ใน [1]: ส่งภาพเป็น base64 ใน `image_url` · ให้ตอบเป็น JSON อย่างเดียว · ตัด ``` ที่ครอบออก · ถ้าแปลงเป็น JSON ไม่ได้ ถามซ้ำ 1 ครั้ง
4. Guardrail ทุก repo พึ่ง prompt อย่างเดียว ไม่มีโค้ดกรอง — [4] เพิ่มแค่ "ข้อความสำรองที่กำหนดไว้ตายตัว + แจ้งแอดมิน"
5. โปรเจกต์นี้ใช้ LightRAG แบบ library ใน FastAPI ตัวเดียว (ไม่ต้องเพิ่มเซิร์ฟเวอร์ตัวที่สอง) และเพิ่ม guardrail ในโค้ดทั้งขาเข้าและขาออก

## เทียบ 4 repo

| Repo | ทำอะไร | LLM / embedding | RAG | Vision | Guardrail |
|---|---|---|---|---|---|
| [1] chatbot-with-image-bill | FastAPI ไฟล์เดียว อ่านใบเสร็จลง CSV | OpenRouter (โมเดลตั้งใน env) | ใส่ CSV ทั้งไฟล์ใน prompt | ✓ base64 + JSON + ถามซ้ำ 1 ครั้ง | prompt อย่างเดียว |
| [2] light-rag | สำเนา LightRAG 1.5.8 + ข้อมูลระเบียบภาษาไทย รันเป็นเซิร์ฟเวอร์ | OpenRouter `gpt-4o-mini` · `text-embedding-3-large` (3072 มิติ) | LightRAG server `POST /query` | ✗ | `user_prompt` บังคับตอบจากคลังเท่านั้น |
| [3] mcp-lightrag | MCP server 33 tools เรียก LightRAG server | — | ผ่าน HTTP (`X-API-Key`) | ✗ | ไม่มีการกรอง มี audit log |
| [4] LineOA-LLM-Chatbot | LINE webhook บน Vercel | OpenRouter `gpt-4o-mini` | ความรู้อยู่ใน prompt | ✗ | ข้อความสำรองตายตัว → push แจ้งแอดมิน |

## หยิบมาใช้

| รหัส | จาก | ใช้ที่ |
|---|---|---|
| IMP-01 | [2] ตัวอย่าง `lightrag_openai_compatible_demo.py` — `LightRAG(working_dir, llm_model_func, EmbeddingFunc(...))` → `initialize_storages()` → `ainsert` / `aquery` | `x-fitness/backend/app/rag.py` |
| IMP-02 | [1] ภาพ base64 + ตอบ JSON + ตัด ``` | `/api/vision` ใน `x-fitness/backend/app/chat.py` |
| IMP-03 | [4] คำตอบที่บอทไม่มั่นใจ → เสนอส่งต่อพนักงาน | `actions: ["คุยกับพนักงาน"]` (มีอยู่แล้ว) |

## ไม่หยิบ

- รัน LightRAG เป็นเซิร์ฟเวอร์แยก [2][3] — เพิ่มบริการที่ต้องดูแลอีกตัว โดยข้อมูลมีแค่ 8 เอกสาร
- ใส่ความรู้ทั้งหมดใน prompt [1][4] — โจทย์รายวิชาต้องมี RAG

## แหล่งอ้างอิง

1. https://github.com/chacharin/chatbot-with-image-bill
2. https://github.com/chacharin/light-rag
3. https://github.com/chacharin/mcp-lightrag
4. https://github.com/chacharin/LineOA-LLM-Chatbot
