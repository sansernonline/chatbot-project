"""X Fitness backend: chatbot for the website (/api/chat, /api/vision) and LINE (/api/line/webhook), admin inbox and knowledge base, serves frontend/.

Run from the backend folder:  uvicorn app.main:app --reload
Then open http://localhost:8000/ (site) and http://localhost:8000/admin/ (back office).
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import chat, config, conversations, db, knowledge, line, rag

@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(rag.reindex())     # index new/changed knowledge documents without delaying start-up
    yield
    task.cancel()

db.init()
app = FastAPI(title="X Fitness API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "ok", "chat_store": "sqlite", "llm": bool(config.TYPHOON_API_KEY), "model": config.CHAT_MODEL,
            "vision_model": config.VISION_MODEL, "rag": rag.engine(),
            "line": bool(config.LINE_CHANNEL_SECRET and config.LINE_CHANNEL_ACCESS_TOKEN)}

app.include_router(conversations.customer)
app.include_router(conversations.admin)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(line.router)

# static files last so /api/* wins; ../test-images is referenced by the site
app.mount("/test-images", StaticFiles(directory=config.TEST_IMAGES_DIR), name="test-images")
app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
