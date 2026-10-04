"""Admin endpoints for the knowledge base page (frontend/admin → คลังความรู้): list, test search, upload, rebuild index."""
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import auth, config, rag

router = APIRouter(prefix="/api/admin/kb", tags=["knowledge"], dependencies=[Depends(auth.require_admin)])
MAX_DOC_BYTES = 200 * 1024


class Query(BaseModel):
    q: str = Field(min_length=1, max_length=300)


@router.get("")
def list_docs():
    return {"engine": rag.engine(), "docs": rag.docs()}


@router.post("/search")
async def search(body: Query):
    return {"engine": rag.engine(), "hits": await rag.search(body.q, 3)}


@router.post("/reindex", status_code=202)
def reindex(tasks: BackgroundTasks):
    tasks.add_task(rag.reindex)
    return {"status": "started"}


@router.post("", status_code=201)
async def upload(tasks: BackgroundTasks, file: UploadFile = File(...)):
    name = file.filename or ""
    if not re.fullmatch(r"[\w-]{1,60}\.md", name):
        raise HTTPException(415, "รองรับเฉพาะไฟล์ .md ชื่อภาษาอังกฤษ ตัวเลข - หรือ _")
    data = await file.read()
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "ไฟล์ใหญ่เกิน 200 KB")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "ไฟล์ต้องเป็น UTF-8")
    (config.KB_DIR / name).write_bytes(data)
    tasks.add_task(rag.reindex)
    return {"file": name, "status": "indexing"}
