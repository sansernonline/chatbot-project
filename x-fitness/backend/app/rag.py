"""Retrieval over data/knowledge-base/*.md with LightRAG (knowledge graph + vector search).

LightRAG uses the chat LLM (Typhoon) to pull entities and relations out of each document once, at indexing time,
and hash_embed() (Thai word + character n-gram hashing with a synonym list, no model) for vectors. Index files live in x-fitness/rag-index/ (committed) and are reused
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
from collections import Counter
from functools import lru_cache

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from pythainlp.corpus import thai_stopwords
from pythainlp.tokenize import word_tokenize

from . import config, keyword_search

log = logging.getLogger(__name__)
MIN_KEYWORD_SCORE = 0.08            # keyword fallback: below this a chunk is not cited (and the bot is likely unsure)
KEYWORD_BACKUP = 2                  # keyword-search chunks added to LightRAG results (hybrid search)
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
    """Feature hashing of Thai words + character 2-3-grams: no model, no API, ~70 MB RAM (pythainlp's word list).

    1. synonyms.json adds the knowledge base's own term when a text uses another name for it ("ครูฝึก" → "เทรนเนอร์ส่วนตัว PT โค้ช")
    2. features: words cut by pythainlp newmm (stopwords dropped) weigh 2, character 2-3-grams 0.5 (they still match typos
       and words the dictionary splits differently)
    3. each feature goes to one of `dim` slots (crc32 → slot, one bit → +1/-1 so collisions cancel out), its count damped with
       log1p, then the vector is scaled to length 1, so cosine similarity = how many weighted features two texts share.
    Right document first on 60 customer-style questions written independently: 46/60 (characters only: 32/60, MiniLM model: 43/60)."""
    dim = dim or config.EMBED_DIM
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for row, text in zip(out, texts):
        for feature, weight in _features(text).items():
            h = zlib.crc32(feature.encode())
            row[h % dim] += np.log1p(weight) * (1.0 if h & 0x80000000 else -1.0)
        row /= np.linalg.norm(row) or 1.0
    return out


def _features(text: str) -> Counter:
    s = re.sub(r"\s+", " ", text.lower())
    s += "".join(f" {term}" for term, pattern in _synonyms() if pattern.search(s))
    feats = Counter()
    for n in (2, 3):
        for i in range(len(s) - n + 1):
            feats[s[i:i + n]] += 0.5
    for word in word_tokenize(s, engine="newmm", keep_whitespace=False):
        if word.isdigit() or (len(word) > 1 and word not in _STOPWORDS):
            feats["w:" + word] += 2.0
    return feats


_STOPWORDS = frozenset(thai_stopwords()) | {"ค่ะ", "ครับ", "คะ", "ไหม", "มั้ย", "หน่อย", "ยังไง", "อะไร", "บ้าง"}


@lru_cache(maxsize=None)
def _synonyms() -> list[tuple[str, re.Pattern]]:
    """(knowledge base term, pattern of the other names customers use) from data/db/synonyms.json."""
    items = json.loads(config.SYNONYMS_FILE.read_text(encoding="utf-8"))["items"]
    word = lambda v: rf"\b{re.escape(v)}\b" if v.isascii() else re.escape(v)     # "pt" must not match inside "prompt"
    return [(term.lower(), re.compile("|".join(map(word, names)), re.I)) for term, names in items.items()]


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
    """Settings an index is built with; when they change, the whole index is rebuilt (same hash on Windows CRLF and Linux LF)."""
    synonyms = config.SYNONYMS_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    synonyms = "" if config.EMBED_API_KEY else ":syn" + hashlib.md5(synonyms.encode()).hexdigest()[:8]
    return f"{config.EMBED_MODEL}:{config.EMBED_DIM}:chunk{config.RAG_CHUNK_TOKENS}{synonyms}"


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
    # hybrid search: LightRAG searches with keywords Typhoon pulls out of the question, and those can be wrong
    # ("นักเรียนเล่น Ride" → "การเล่นเกม"); keyword search on the customer's own words backs it up.
    found = [(c.get("file_path"), c.get("content", "")) for c in chunks]
    found += [(c.doc_id, c.text) for s, c in keyword_search.index().search(query, KEYWORD_BACKUP) if s >= MIN_KEYWORD_SCORE]
    text = "\n\n".join(f"[{doc_id}]\n{content}" for doc_id, content in found)
    if relations:
        text += "\n\n[ความสัมพันธ์จากกราฟความรู้]\n" + "\n".join(f"- {r['src_id']} → {r['tgt_id']}: {r.get('description', '')}" for r in relations)
    return text, list(dict.fromkeys(doc_id for doc_id, _ in found if doc_id))


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
