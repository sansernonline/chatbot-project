"""Settings read from environment variables (or backend/.env); defaults suit a local demo."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / "backend" / ".env")

DB_PATH = Path(os.getenv("XF_DB_PATH", PROJECT_ROOT / "backend" / "data" / "chat.sqlite3"))
ADMIN_USER = os.getenv("XF_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("XF_ADMIN_PASS", "1234")
CORS_ORIGINS = os.getenv("XF_CORS_ORIGINS", "*").split(",")  # "*" lets the site opened as file:// call the API
WEB_DIR = PROJECT_ROOT / "frontend"  # copied from the root mockup/ folder
TEST_IMAGES_DIR = PROJECT_ROOT / "test-images"
KB_DIR = PROJECT_ROOT / "data" / "knowledge-base"
DATA_DIR = PROJECT_ROOT / "data" / "db"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Typhoon (OpenAI-compatible API) answers chats, reads images and builds the LightRAG index — https://docs.opentyphoon.ai
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "")
TYPHOON_BASE_URL = os.getenv("TYPHOON_BASE_URL", "https://api.opentyphoon.ai/v1")
CHAT_MODEL = os.getenv("XF_CHAT_MODEL", "typhoon-v2.5-30b-a3b-instruct")
VISION_MODEL = os.getenv("XF_VISION_MODEL", "typhoon-ocr")
LLM_TIMEOUT_S = float(os.getenv("XF_LLM_TIMEOUT_S", "25"))

# LINE Official Account (Messaging API) — both empty = LINE channel off
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# LightRAG embeddings. With XF_EMBED_API_KEY: an OpenAI-compatible embedding API (Gemini by default, free tier).
# Without it: a small multilingual model run on this machine (downloaded once, ~220 MB, needs ~560 MB more RAM).
EMBED_API_KEY = os.getenv("XF_EMBED_API_KEY", "")
if EMBED_API_KEY:
    EMBED_BASE_URL = os.getenv("XF_EMBED_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    EMBED_MODEL = os.getenv("XF_EMBED_MODEL", "gemini-embedding-001")
    EMBED_DIM = int(os.getenv("XF_EMBED_DIM", "3072"))
else:
    EMBED_BASE_URL = ""
    EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBED_DIM = 384
MODELS_DIR = PROJECT_ROOT / "backend" / "data" / "models"
RAG_DIR = Path(os.getenv("XF_RAG_DIR", PROJECT_ROOT / "rag-index"))  # committed, so a fresh server (Render) does not rebuild it
RAG_MODE = os.getenv("XF_RAG_MODE", "mix")         # LightRAG query mode: naive · local · global · hybrid · mix
RAG_LLM_MAX_TOKENS = int(os.getenv("XF_RAG_LLM_MAX_TOKENS", "8192"))  # answer length for LightRAG extraction calls
RAG_CHUNK_TOKENS = int(os.getenv("XF_RAG_CHUNK_TOKENS", "500"))       # small chunks: Thai entity lists fit in one answer
RAG_TOP_K = int(os.getenv("XF_RAG_TOP_K", "4"))
