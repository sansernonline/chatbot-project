"""Retrieval over data/knowledge-base/*.md with LightRAG (knowledge graph + vector search).

LightRAG uses the chat LLM (Typhoon) to pull entities and relations out of each document once, at indexing time,
and hash_embed() (character n-gram hashing, no model) for vectors. Index files live in x-fitness/rag-index/ (committed) and are reused
across restarts; only documents whose content changed are indexed again (tracked in manifest.json).
Without TYPHOON_API_KEY the same functions fall back to keyword search (keyword_search.py).
"""
import asyncio
import hashlib
import json
import logging
import re
import shutil
import zlib

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from . import config, keyword_search

log = logging.getLogger(__name__)
MIN_KEYWORD_SCORE = 0.08            # keyword fallback: below this a chunk is not cited (and the bot is likely unsure)
_rag: LightRAG | None = None
_lock = asyncio.Lock()
_indexing = False


def engine() -> str:
    return "lightrag" if config.TYPHOON_API_KEY else "keyword"


def kb_files() -> dict[str, dict]:
    """doc_id → {file, title, text, index_text, hash} for every knowledge base document.

    index_text is what LightRAG reads: the title on top, without the YAML front matter and the "mock data" note
    (both would otherwise become chunk text and entities)."""
    docs = {}
    for path in sorted(config.KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")    # same hash on Windows (CRLF) and Linux (LF)
        meta, body = keyword_search._front_matter(text)
        doc_id, title = meta.get("doc_id", path.stem), meta.get("title", path.stem)
        body = "\n".join(line for line in body.splitlines() if not line.startswith("> ข้อมูลจำลอง"))
        docs[doc_id] = {"file": path.name, "title": title, "text": text, "index_text": f"[{doc_id}] {title}\n{body}",
                        "hash": hashlib.md5(text.encode()).hexdigest()}
    return docs


async def _llm(prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs) -> str:
    kwargs.setdefault("max_tokens", config.RAG_LLM_MAX_TOKENS)   # LightRAG sends none; Typhoon's default cuts entity lists short
    return await openai_complete_if_cache(config.CHAT_MODEL, prompt, system_prompt=system_prompt,
                                          history_messages=history_messages or [], api_key=config.TYPHOON_API_KEY,
                                          base_url=config.TYPHOON_BASE_URL, **kwargs)


async def _embed(texts: list[str]):
    if config.EMBED_API_KEY:
        return await openai_embed.func(texts, model=config.EMBED_MODEL, api_key=config.EMBED_API_KEY, base_url=config.EMBED_BASE_URL)
    return hash_embed(texts)


def hash_embed(texts: list[str], dim: int | None = None) -> np.ndarray:
    """Feature hashing of character 2-3-grams: no model, no API, ~0 MB RAM, works for Thai without word splitting.

    Each n-gram goes to one of `dim` slots (crc32 → slot, one bit → +1/-1 so collisions cancel out),
    then the vector is scaled to length 1, so cosine similarity = how many n-grams two texts share.
    It matches wording, not meaning; the knowledge base lists the other names customers use to make up for that."""
    dim = dim or config.EMBED_DIM
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for row, text in zip(out, texts):
        s = re.sub(r"\s+", " ", text.lower())
        for n in (2, 3):
            for i in range(len(s) - n + 1):
                h = zlib.crc32(s[i:i + n].encode())
                row[h % dim] += 1.0 if h & 0x80000000 else -1.0
        row /= np.linalg.norm(row) or 1.0
    return out


async def _get() -> LightRAG:
    global _rag
    async with _lock:
        if _rag is None:
            config.RAG_DIR.mkdir(parents=True, exist_ok=True)
            rag = LightRAG(working_dir=str(config.RAG_DIR), llm_model_func=_llm, llm_model_name=config.CHAT_MODEL, chunk_token_size=config.RAG_CHUNK_TOKENS,
                           embedding_func=EmbeddingFunc(embedding_dim=config.EMBED_DIM, max_token_size=8192, func=_embed),
                           addon_params={"language": "Thai"},
                           vector_db_storage_cls_kwargs={"cosine_better_than_threshold": config.RAG_MIN_SIMILARITY})
            await rag.initialize_storages()
            _rag = rag
    return _rag


def _embedder() -> str:
    """Settings an index is built with; when they change, the whole index is rebuilt."""
    return f"{config.EMBED_MODEL}:{config.EMBED_DIM}:chunk{config.RAG_CHUNK_TOKENS}"


def _manifest() -> dict:
    """doc_id → content hash of each indexed document; empty when the index was built with another embedding model."""
    path = config.RAG_DIR / "manifest.json"
    m = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return m.get("docs", {}) if m.get("embedder") == _embedder() else {}


def _save(done: dict) -> None:
    (config.RAG_DIR / "manifest.json").write_text(json.dumps({"embedder": _embedder(), "docs": done}, indent=1), encoding="utf-8")


async def reindex() -> None:
    """Bring the LightRAG index in line with data/knowledge-base: add new/changed documents, drop removed ones."""
    global _indexing
    if engine() != "lightrag" or _indexing:
        keyword_search.index.cache_clear()
        return
    _indexing = True
    try:
        if _rag is None and not _manifest() and config.RAG_DIR.exists():
            shutil.rmtree(config.RAG_DIR)             # built with another embedding model (vector sizes differ): start over
        rag, done, docs = await _get(), _manifest(), kb_files()
        for doc_id in [d for d in done if docs.get(d, {}).get("hash") != done[d]]:
            await rag.adelete_by_doc_id(doc_id)
            done.pop(doc_id)
            _save(done)
        for doc_id, d in docs.items():
            if doc_id not in done:
                await rag.ainsert(d["index_text"], ids=doc_id, file_paths=doc_id)   # no front matter / disclaimer
                status = str((await rag.doc_status.get_by_id(doc_id) or {}).get("status", "")).lower()
                if not status.endswith("processed"):         # ainsert logs failures instead of raising
                    log.error("LightRAG could not index %s (status %s); will retry on next start", doc_id, status)
                    await rag.adelete_by_doc_id(doc_id)
                    continue
                done[doc_id] = d["hash"]
                _save(done)
    except Exception:
        log.exception("LightRAG indexing failed")
    finally:
        _indexing = False
        keyword_search.index.cache_clear()


def docs() -> list[dict]:
    done = _manifest() if engine() == "lightrag" else {}
    status = lambda doc_id, h: "keyword" if engine() == "keyword" else "ready" if done.get(doc_id) == h else "indexing" if _indexing else "not_indexed"
    return [{"doc_id": i, "file": d["file"], "title": d["title"], "status": status(i, d["hash"])} for i, d in kb_files().items()]


async def context(query: str) -> tuple[str, list[str]]:
    """Knowledge for the LLM prompt and the document ids it came from (empty list = nothing relevant found)."""
    if engine() == "keyword":
        hits = keyword_search.index().search(query, config.RAG_TOP_K)
        text = "\n\n".join(f"[{c.doc_id}] {c.title} › {c.heading}\n{c.text}" for _, c in hits)
        return text, list(dict.fromkeys(c.doc_id for s, c in hits if s >= MIN_KEYWORD_SCORE))
    # LightRAG finds the chunks (vector + knowledge graph); we lay them out ourselves: document text first because it is
    # the source of truth, then a few graph relations. Its default layout put LLM-written entity summaries first,
    # and Typhoon followed those over exceptions written in the documents.
    rag = await _get()
    data = (await rag.aquery_data(query, param=QueryParam(mode=config.RAG_MODE, top_k=10, chunk_top_k=config.RAG_TOP_K,
                                                          max_total_tokens=8000))).get("data", {})
    chunks, relations = data.get("chunks", []), data.get("relationships", [])[:10]
    text = "\n\n".join(f"[{c.get('file_path')}]\n{c.get('content', '')}" for c in chunks)
    if relations:
        text += "\n\n[ความสัมพันธ์จากกราฟความรู้]\n" + "\n".join(f"- {r['src_id']} → {r['tgt_id']}: {r.get('description', '')}" for r in relations)
    return text, list(dict.fromkeys(c.get("file_path") for c in chunks if c.get("file_path")))


async def search(query: str, k: int = 3) -> list[dict]:
    """Top chunks for the admin's test search."""
    if engine() == "keyword":
        return [{"doc_id": c.doc_id, "score": round(s, 2), "text": c.text[:200]} for s, c in keyword_search.index().search(query, k)]
    rag = await _get()
    data = await rag.aquery_data(query, param=QueryParam(mode=config.RAG_MODE, chunk_top_k=k))
    return [{"doc_id": c.get("file_path"), "score": None, "text": c.get("content", "")[:200]}
            for c in data.get("data", {}).get("chunks", [])[:k]]


async def _build() -> None:
    await reindex()
    if _rag:
        await _rag.finalize_storages()
    print({d["doc_id"]: d["status"] for d in docs()})


if __name__ == "__main__":                            # python -m app.rag  → build/update the index, then exit
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_build())
