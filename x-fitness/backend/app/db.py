"""SQLite store for chat conversations.

The ticket is the conversation id: 10 characters, letter and digit alternating (e.g. K3M8P2Q7R5),
made by the customer's browser (frontend/shared/chat-store.js) and kept in its localStorage,
or derived from the LINE user id for LINE chats (line.py).
frontend/shared/chat-store.js apply() mirrors these rules for its optimistic cache.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
  id         TEXT PRIMARY KEY,
  ticket     TEXT UNIQUE,
  name       TEXT,
  member_id  TEXT,
  topic      TEXT,
  status     TEXT NOT NULL DEFAULT 'bot' CHECK (status IN ('bot','waiting','agent','closed')),
  agent      TEXT,
  seen_admin INTEGER NOT NULL DEFAULT 0,
  created    TEXT NOT NULL,
  updated    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  conv_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  sender  TEXT NOT NULL CHECK (sender IN ('user','bot','agent','system')),
  text    TEXT NOT NULL,
  by      TEXT,
  notify  INTEGER NOT NULL DEFAULT 0,
  at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_conv ON messages(conv_id, id);
CREATE TABLE IF NOT EXISTS line_users (   -- LINE chats: conversation id ↔ LINE user, so staff replies can be pushed back
  conv_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL UNIQUE
);
"""
PATCHABLE = {"name", "member_id", "topic", "status", "agent", "seen_admin"}


def now() -> str:
    """UTC ISO time in the same format as JavaScript's toISOString()."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as con:
        con.executescript(SCHEMA)


def _conv(con, cid: str) -> dict | None:
    row = con.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
    if not row:
        return None
    msgs = con.execute("SELECT sender, text, by, notify, at FROM messages WHERE conv_id = ? ORDER BY id", (cid,))
    return {**dict(row), "msgs": [
        {"from": m["sender"], "text": m["text"], "at": m["at"], **({"by": m["by"]} if m["by"] else {}), **({"notify": True} if m["notify"] else {})}
        for m in msgs]}


def _ensure(con, cid: str) -> None:
    t = now()
    con.execute("INSERT OR IGNORE INTO conversations (id, ticket, created, updated) VALUES (?, ?, ?, ?)", (cid, cid, t, t))


def _finish(con, cid: str, touch: bool = True) -> dict:
    if touch:
        con.execute("UPDATE conversations SET updated = ? WHERE id = ?", (now(), cid))
    con.commit()
    return _conv(con, cid)


def get(cid: str) -> dict | None:
    with closing(connect()) as con:
        return _conv(con, cid)


def list_all() -> list[dict]:
    with closing(connect()) as con:
        ids = [r[0] for r in con.execute("SELECT id FROM conversations ORDER BY updated DESC")]
        return [_conv(con, i) for i in ids]


def add_message(cid: str, sender: str, text: str, by: str | None = None, notify: bool = False, at: str | None = None) -> dict:
    with closing(connect()) as con:
        _ensure(con, cid)
        con.execute("INSERT INTO messages (conv_id, sender, text, by, notify, at) VALUES (?, ?, ?, ?, ?, ?)",
                    (cid, sender, text, by, int(notify), at or now()))
        return _finish(con, cid)


def patch(cid: str, fields: dict, touch: bool = True) -> dict:
    fields = {k: v for k, v in fields.items() if k in PATCHABLE}
    with closing(connect()) as con:
        _ensure(con, cid)
        if fields:
            con.execute(f"UPDATE conversations SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", (*fields.values(), cid))
        return _finish(con, cid, touch)


def handoff(cid: str, topic: str, name: str | None, member_id: str | None) -> dict:
    with closing(connect()) as con:
        _ensure(con, cid)
        con.execute("UPDATE conversations SET topic = ?, name = ?, member_id = ?, "
                    "status = CASE status WHEN 'agent' THEN 'agent' ELSE 'waiting' END WHERE id = ?",
                    (topic, name, member_id, cid))
        con.execute("INSERT INTO messages (conv_id, sender, text, at) VALUES (?, 'system', ?, ?)",
                    (cid, f"ลูกค้าขอคุยกับพนักงาน · {topic}", now()))
        return _finish(con, cid)


def delete(cid: str | None = None) -> None:
    """Delete one conversation, or all of them when cid is None."""
    with closing(connect()) as con:
        con.execute("DELETE FROM conversations" + (" WHERE id = ?" if cid else ""), (cid,) if cid else ())
        con.commit()


def link_line_user(cid: str, user_id: str) -> None:
    with closing(connect()) as con:
        _ensure(con, cid)
        con.execute("INSERT OR IGNORE INTO line_users (conv_id, user_id) VALUES (?, ?)", (cid, user_id))
        con.commit()


def line_user(cid: str) -> str | None:
    with closing(connect()) as con:
        row = con.execute("SELECT user_id FROM line_users WHERE conv_id = ?", (cid,)).fetchone()
        return row[0] if row else None
