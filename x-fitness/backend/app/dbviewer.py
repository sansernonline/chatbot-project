"""Read-only view of the database for admin/dbviewer.html: every table with its data dictionary, and its rows page by page.

The connection is opened with mode=ro, so nothing here can change the data. Table names are checked against the
database's own list before they reach SQL. The data dictionary is datadict.json, kept in the database (db.FILES).
"""
import json
import sqlite3
from contextlib import closing

from fastapi import APIRouter, Depends, HTTPException, Query

from . import auth, config, db

router = APIRouter(prefix="/api/admin/db", tags=["back office"], dependencies=[Depends(auth.require_admin)])
GROUPS = ["shop", "chat", "system"]


def _read_only() -> sqlite3.Connection:
    db.init()                                                   # a fresh server makes its database first
    return sqlite3.connect(config.DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)


def _dictionary() -> dict:
    text = db.file_text("datadict.json")
    return json.loads(text) if text else {"groups": {}, "tables": {}}


def _tables(con) -> list[str]:
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]


@router.get("", summary="ดูฐานข้อมูล: ทุกตาราง จำนวนแถว คอลัมน์ และคำอธิบาย (อ่านอย่างเดียว)")
def tables():
    d = _dictionary()
    with closing(_read_only()) as con:
        out = []
        for name in _tables(con):
            info = d["tables"].get(name, {})
            cols = [{"name": c[1], "type": c[2] or "-", "about": info.get("columns", {}).get(c[1], "")}
                    for c in con.execute(f'PRAGMA table_info("{name}")')]
            out.append({"name": name, "group": info.get("group", "system"), "about": info.get("about", ""), "source": info.get("source", ""),
                        "rows": con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0], "columns": cols})
    order = list(d["tables"])
    out.sort(key=lambda t: (GROUPS.index(t["group"]) if t["group"] in GROUPS else 9, order.index(t["name"]) if t["name"] in order else 99))
    return {"file": config.DB_PATH.name, "size": config.DB_PATH.stat().st_size, "groups": d["groups"], "tables": out}


@router.get("/{name}", summary="ดูแถวในตาราง ทีละหน้า (อ่านอย่างเดียว)")
def rows(name: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with closing(_read_only()) as con:
        if name not in _tables(con):
            raise HTTPException(404, "ไม่มีตารางนี้")
        cur = con.execute(f'SELECT * FROM "{name}" ORDER BY rowid LIMIT ? OFFSET ?', (limit, offset))
        return {"name": name, "total": con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0], "offset": offset,
                "columns": [c[0] for c in cur.description], "rows": [list(r) for r in cur.fetchall()]}
