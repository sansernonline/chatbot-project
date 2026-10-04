"""Keyword search over data/knowledge-base/*.md — the fallback rag.py uses when no embedding API key is set.

Each "## heading" section becomes a chunk (long ones are split by paragraph).
Vectors are TF-IDF over character 2-3-grams, which works for Thai without a word tokenizer,
needs no embedding API, and is plenty for ~15 pages.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import config

MAX_CHUNK_CHARS = 1200
# question words appear in every query but say nothing about the topic
QUESTION_WORDS = re.compile(r"เท่าไหร่|เท่าไร|ได้ไหม|ไหม|มั้ย|กี่โมง|กี่วัน|กี่|อะไร|ยังไง|อย่างไร|เมื่อไหร่|ครับ|ค่ะ|คะ|นะ|หน่อย|บ้าง")


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    heading: str
    text: str


def _front_matter(md: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", md, re.S)
    if not m:
        return {}, md
    meta = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in meta.items()}, md[m.end():]


def load_chunks(kb_dir: Path) -> list[Chunk]:
    chunks = []
    for path in sorted(kb_dir.glob("*.md")):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        doc_id, title = meta.get("doc_id", path.stem), meta.get("title", path.stem)
        for section in re.split(r"\n(?=## )", body):
            heading = section.splitlines()[0].lstrip("# ").strip() if section.startswith("## ") else title
            parts, buf = [], ""
            for para in section.split("\n\n"):
                if buf and len(buf) + len(para) > MAX_CHUNK_CHARS:
                    parts.append(buf)
                    buf = ""
                buf += para + "\n\n"
            parts.append(buf)
            chunks += [Chunk(doc_id, title, heading, p.strip()) for p in parts if len(p.strip()) > 40]
    return chunks


def _grams(text: str) -> Counter:
    s = re.sub(r"\s+", " ", text.lower())
    return Counter(s[i:i + n] for n in (2, 3) for i in range(len(s) - n + 1))


class Index:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        counts = [_grams(f"{c.title} {c.heading} {c.heading} {c.text}") for c in chunks]
        df = Counter(g for c in counts for g in c)
        self.idf = {g: math.log((1 + len(chunks)) / (1 + n)) + 1 for g, n in df.items()}
        self.vecs = [self._weigh(c) for c in counts]

    def _weigh(self, counts: Counter) -> dict:
        v = {g: (1 + math.log(n)) * self.idf.get(g, 0) for g, n in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {g: x / norm for g, x in v.items()}

    def search(self, query: str, k: int = 4) -> list[tuple[float, Chunk]]:
        q = self._weigh(_grams(QUESTION_WORDS.sub(" ", query)))
        scored = [(sum(w * vec.get(g, 0) for g, w in q.items()), c) for vec, c in zip(self.vecs, self.chunks)]
        return sorted(scored, key=lambda x: -x[0])[:k]


@lru_cache(maxsize=1)
def index() -> Index:
    return Index(load_chunks(config.KB_DIR))
