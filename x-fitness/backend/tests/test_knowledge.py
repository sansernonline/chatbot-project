"""Knowledge base admin API, and LightRAG wiring run offline with a fake LLM and the real hash embedding."""
import asyncio

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config, rag


@pytest.fixture
def admin(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "chat.sqlite3")
    from app import db
    from app.main import app
    db.init()
    client = TestClient(app)
    token = client.post("/api/admin/login", json={"user": "admin", "password": "1234"}).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_kb_needs_login(admin):
    assert admin.get("/api/admin/kb", headers={"Authorization": ""}).status_code == 401


def test_kb_list_and_search(admin):
    docs = admin.get("/api/admin/kb").json()
    assert docs["engine"] == "keyword" and len(docs["docs"]) == 9 and docs["docs"][0]["doc_id"] == "KB-01"
    hits = admin.post("/api/admin/kb/search", json={"q": "ยกเลิกสมาชิกต้องแจ้งกี่วัน"}).json()["hits"]
    assert len(hits) == 3 and hits[0]["doc_id"] == "KB-05"


def test_kb_upload_rejects_bad_files(admin):
    assert admin.post("/api/admin/kb", files={"file": ("../x.md", b"hi", "text/markdown")}).status_code == 415
    assert admin.post("/api/admin/kb", files={"file": ("a.pdf", b"%PDF", "application/pdf")}).status_code == 415
    assert admin.post("/api/admin/kb", files={"file": ("big.md", b"x" * 300_000, "text/markdown")}).status_code == 413


def test_lightrag_index_and_context_offline(tmp_path, monkeypatch):
    async def fake_llm(prompt, system_prompt=None, history_messages=None, **kw):
        return "<|COMPLETE|>"                       # no entities: LightRAG still indexes the text chunks

    monkeypatch.setattr(config, "TYPHOON_API_KEY", "test")    # turns LightRAG on; the LLM itself is faked below
    monkeypatch.setattr(config, "EMBED_DIM", 32)
    monkeypatch.setattr(config, "RAG_DIR", tmp_path / "lightrag")
    monkeypatch.setattr(config, "RAG_MODE", "naive")
    monkeypatch.setattr(rag, "_llm", fake_llm)
    monkeypatch.setattr(rag, "_rag", None)

    async def run():
        await rag.reindex()
        assert all(d["status"] == "ready" for d in rag.docs())
        text, sources = await rag.context("การชำระเงิน")
        assert sources and all(s.startswith("KB-") for s in sources)
        await rag._rag.finalize_storages()

        # index built with another embedding model (e.g. local model, server uses Gemini): rebuilt, not mixed
        monkeypatch.setattr(config, "EMBED_MODEL", "other-model")
        monkeypatch.setattr(rag, "_rag", None)
        assert all(d["status"] == "not_indexed" for d in rag.docs())
        await rag.reindex()
        assert all(d["status"] == "ready" for d in rag.docs())
        await rag._rag.finalize_storages()
    asyncio.run(run())


def test_hash_embed_similar_wording_scores_higher():
    v = rag.hash_embed(["ค่าสมาชิกรายเดือน 1,290 บาท", "ค่าสมาชิกรายเดือนเท่าไหร่", "ห้ามถ่ายรูปสมาชิกคนอื่น"], dim=1024)
    assert np.allclose(np.linalg.norm(v, axis=1), 1) and v[0] @ v[1] > v[0] @ v[2] + 0.2
    assert np.array_equal(v, rag.hash_embed(["ค่าสมาชิกรายเดือน 1,290 บาท", "ค่าสมาชิกรายเดือนเท่าไหร่", "ห้ามถ่ายรูปสมาชิกคนอื่น"], dim=1024))
