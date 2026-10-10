"""Admin endpoints for the knowledge base page (frontend/admin → คลังความรู้): list, test search, upload, rebuild index, graph."""
import re
import xml.etree.ElementTree as ET   # reads our own LightRAG output (data/rag-index/), not uploaded files

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import auth, config, rag

router = APIRouter(prefix="/api/admin/kb", tags=["knowledge"], dependencies=[Depends(auth.require_admin)])
MAX_DOC_BYTES = 200 * 1024


class Query(BaseModel):
    q: str = Field(min_length=1, max_length=300)


@router.get("", summary="รายการเอกสารในคลังความรู้ และสถานะดัชนี")
def list_docs():
    return {"engine": rag.engine(), "docs": rag.docs()}


GRAPHML = "{http://graphml.graphdrawing.org/xmlns}"


@router.get("/graph", summary="กราฟความรู้ของ LightRAG: entity กับความสัมพันธ์ พร้อมเอกสาร KB ที่มา (ใช้วาดหน้า กราฟความรู้)")
def graph():
    path = config.RAG_DIR / "graph_chunk_entity_relation.graphml"
    if not path.exists():
        raise HTTPException(404, "ยังไม่มีกราฟความรู้ ต้องสร้างดัชนีก่อน")
    root = ET.parse(path).getroot()
    names = {k.get("id"): k.get("attr.name") for k in root.iter(GRAPHML + "key")}
    fields = lambda el: {names[d.get("key")]: d.text or "" for d in el.iter(GRAPHML + "data")}
    docs = lambda f: sorted(set(filter(None, f.get("file_path", "").split("<SEP>"))))
    edges = [{"source": e.get("source"), "target": e.get("target"), "keywords": f.get("keywords", ""),
              "description": f.get("description", "")[:300], "docs": docs(f)}
             for e in root.iter(GRAPHML + "edge") for f in [fields(e)]]
    degree = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    nodes = [{"id": n.get("id"), "type": f.get("entity_type", "UNKNOWN"), "description": f.get("description", "")[:300],
              "docs": docs(f), "degree": degree.get(n.get("id"), 0)} for n in root.iter(GRAPHML + "node") for f in [fields(n)]]
    return {"nodes": nodes, "edges": edges}


@router.post("/search", summary="ทดสอบค้นคลังความรู้ (3 ส่วนที่ใกล้ที่สุด)")
async def search(body: Query):
    return {"engine": rag.engine(), "hits": await rag.search(body.q, 3)}


@router.post("/reindex", status_code=202, summary="สร้างดัชนี LightRAG ใหม่ (ทำเบื้องหลัง)")
def reindex(tasks: BackgroundTasks):
    tasks.add_task(rag.reindex)
    return {"status": "started"}


@router.post("", status_code=201, summary="อัปโหลดเอกสาร .md เข้าคลังความรู้")
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
