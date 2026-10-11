"""X Fitness backend: chatbot for the website (/api/chat, /api/vision) and LINE (/api/line/webhook), admin inbox and knowledge base, serves frontend/.

Run from the backend folder:  uvicorn app.main:app --reload
Then open http://localhost:8000/ (site) and http://localhost:8000/admin/ (back office).
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import backoffice, chat, config, conversations, db, knowledge, line, rag

@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(rag.reindex())     # index new/changed knowledge documents without delaying start-up
    yield
    task.cancel()

db.init()
TAGS = [
    {"name": "bot", "description": "แชตบอท: ถามตอบ และอ่านภาพ (หน้าเว็บเรียกใช้)"},
    {"name": "customer chat", "description": "แชตของลูกค้า: อ่าน บันทึกข้อความ ขอคุยกับพนักงาน"},
    {"name": "LINE", "description": "รับข้อความจาก LINE OA"},
    {"name": "admin inbox", "description": "หลังบ้าน: ล็อกอิน และกล่องแชต · กด Authorize ใส่ token จาก /api/admin/login"},
    {"name": "back office", "description": "หลังบ้าน: การชำระเงินและสลิป · การจองคลาส · โปรโมชัน · ภาพรวม · รีเซ็ตข้อมูลทดสอบ"},
    {"name": "knowledge", "description": "หลังบ้าน: คลังความรู้ LightRAG ดัชนี ทดสอบค้น และกราฟความรู้"},
    {"name": "web data", "description": "ข้อมูลร้านจากฐานข้อมูล ให้หน้าเว็บแสดง (แพ็กเกจ คลาส ตาราง โปร ฯลฯ)"},
    {"name": "system", "description": "สถานะระบบ"},
]
app = FastAPI(title="X Fitness API", version="0.3.0", lifespan=lifespan, openapi_tags=TAGS,
              description="API ของแชตบอท X Fitness (ข้อมูลจำลองทั้งหมด) · เว็บลูกค้า `/` · หลังบ้าน `/admin/` · "
                          "endpoint ที่ขึ้นต้น /api/admin ต้องล็อกอิน: เรียก `POST /api/admin/login` แล้วกด **Authorize** ใส่ token")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health", tags=["system"], summary="สถานะระบบ: โมเดล ตัวค้น และ LINE พร้อมไหม")
def health():
    return {"status": "ok", "chat_store": "sqlite", "llm": bool(config.TYPHOON_API_KEY), "model": config.CHAT_MODEL,
            "vision_model": config.VISION_MODEL, "rag": rag.engine(),
            "line": bool(config.LINE_CHANNEL_SECRET and config.LINE_CHANNEL_ACCESS_TOKEN)}

app.include_router(conversations.customer)
app.include_router(conversations.admin)
app.include_router(backoffice.router)
app.include_router(backoffice.web)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(line.router)

# static files last so /api/* wins; ../qa is referenced by the site
app.mount("/qa", StaticFiles(directory=config.TEST_IMAGES_DIR), name="qa")
app.mount("/documents", StaticFiles(directory=config.DOCS_DIR, html=True), name="documents")
app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
