"""One SQLite database for everything the server keeps: chat conversations, slips, and the business tables.

The business tables (members, packages, payments, promotions, …) are made from data/db/*.json, which stays the
seed kept in git: on start-up, and whenever those files change, they are loaded again (seed_business). Staff
changes from the admin page are written to the tables, so they last until the next reload or "reset test data".

The ticket is the conversation id: 10 characters, letter and digit alternating (e.g. K3M8P2Q7R5),
made by the customer's browser (frontend/shared/chat-store.js) and kept in its localStorage,
or derived from the LINE user id for LINE chats (line.py).
frontend/shared/chat-store.js apply() mirrors these rules for its optimistic cache.
"""
import hashlib
import json
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
-- back office (backoffice.py): customer slips; the business tables themselves are made from data/db/*.json (seed_business)
DROP TABLE IF EXISTS overrides;           -- older versions kept admin changes here; they now go straight into the tables
CREATE TABLE IF NOT EXISTS settings (     -- single values from data/db: business.json, rewards.json and rules such as payments' slip_rule
  source TEXT NOT NULL,
  key    TEXT NOT NULL,
  value  JSON NOT NULL,
  PRIMARY KEY (source, key)
);
CREATE TABLE IF NOT EXISTS seed (         -- fingerprint of the data/db files last loaded
  id    INTEGER PRIMARY KEY CHECK (id = 1),
  hash  TEXT NOT NULL,
  at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS uploads (       -- a slip image read by /api/vision (or LINE), waiting for answer() to tie it to a payment
  id      TEXT PRIMARY KEY,
  conv_id TEXT,
  file    TEXT NOT NULL,
  at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS slips (         -- a slip tied to a member's payment, shown to staff on the payments page
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id TEXT NOT NULL,
  member_id  TEXT NOT NULL,
  conv_id    TEXT,
  file       TEXT NOT NULL,
  reference  TEXT,
  amount     REAL,
  ok         INTEGER NOT NULL,
  checks     TEXT NOT NULL,
  at         TEXT NOT NULL
);
"""
PATCHABLE = {"name", "member_id", "topic", "status", "agent", "seen_admin"}


def now() -> str:
    """UTC ISO time in the same format as JavaScript's toISOString()."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


_ready: set[str] = set()   # database files whose tables exist (tests switch DB_PATH per test)


def connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if str(config.DB_PATH) not in _ready:
        con.executescript(SCHEMA)
        _ready.add(str(config.DB_PATH))
        seed_business(con)
    return con


def init() -> None:
    connect().close()


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


# ---------- back office ----------

def add_upload(upload_id: str, conv_id: str | None, file: str) -> None:
    with closing(connect()) as con:
        con.execute("INSERT INTO uploads (id, conv_id, file, at) VALUES (?, ?, ?, ?)", (upload_id, conv_id, file, now()))
        con.commit()


def take_upload(upload_id: str, conv_id: str) -> str | None:
    """The file of an upload made in this chat, removed from uploads (it becomes a slip); None for another chat's id."""
    with closing(connect()) as con:
        row = con.execute("SELECT file FROM uploads WHERE id = ? AND conv_id = ?", (upload_id, conv_id)).fetchone()
        if row:
            con.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
            con.commit()
        return row[0] if row else None


def add_slip(payment_id: str, member_id: str, conv_id: str, file: str, reference: str | None, amount: float | None,
             ok: bool, checks: str) -> int:
    with closing(connect()) as con:
        cur = con.execute("INSERT INTO slips (payment_id, member_id, conv_id, file, reference, amount, ok, checks, at) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (payment_id, member_id, conv_id, file, reference, amount, int(ok), checks, now()))
        con.commit()
        return cur.lastrowid


def slips() -> list[dict]:
    with closing(connect()) as con:
        return [dict(r) for r in con.execute("SELECT * FROM slips ORDER BY id")]


def slip(slip_id: int) -> dict | None:
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM slips WHERE id = ?", (slip_id,)).fetchone()
        return dict(row) if row else None


def old_files(before: str) -> list[str]:
    """Slip and upload files older than `before` (ISO time), removed from the tables."""
    with closing(connect()) as con:
        files = [r[0] for r in con.execute("SELECT file FROM slips WHERE at < ? UNION ALL SELECT file FROM uploads WHERE at < ?", (before, before))]
        con.execute("DELETE FROM slips WHERE at < ?", (before,))
        con.execute("DELETE FROM uploads WHERE at < ?", (before,))
        con.commit()
        return files


def reset_backoffice() -> list[str]:
    """Back to the seed data: business tables reloaded from data/db, slips and uploads forgotten. Returns the image files to delete."""
    with closing(connect()) as con:
        files = [r[0] for r in con.execute("SELECT file FROM slips UNION ALL SELECT file FROM uploads")]
        con.executescript("DELETE FROM slips; DELETE FROM uploads;")
        seed_business(con, force=True)
        return files


# ---------- business tables (from data/db/*.json) ----------
# One table per file that has "items" (columns from the item fields: whole numbers INTEGER, decimals REAL, text TEXT,
# lists and objects JSON; the first field is the key). Files that are one object, and the other top-level fields of
# the rest, go into settings. synonyms.json is not business data: the knowledge index reads it (rag.py).
TABLES = ["business", "packages", "classes", "trainers", "schedule", "pt_packages", "products", "promotions",
          "rewards", "members", "bookings", "payments", "leads", "receipts"]
SQL_TYPE = {bool: "INTEGER", int: "INTEGER", float: "REAL", str: "TEXT", list: "JSON", dict: "JSON"}


def _seed_files() -> dict[str, dict]:
    return {name: json.loads((config.DATA_DIR / f"{name}.json").read_text(encoding="utf-8")) for name in TABLES}


def seed_business(con, force: bool = False) -> bool:
    """Load data/db/*.json into the business tables when the files changed since the last load (or force).
    Returns True when it loaded. Staff changes are lost on a reload, which is what "reset test data" wants."""
    files = _seed_files()
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    row = con.execute("SELECT hash FROM seed WHERE id = 1").fetchone()
    if row and row[0] == digest and not force:
        return False
    con.execute("DELETE FROM settings")
    for name, data in files.items():
        for key, value in data.items():
            if key not in ("items", "_note"):
                con.execute("INSERT INTO settings (source, key, value) VALUES (?, ?, ?)", (name, key, json.dumps(value, ensure_ascii=False)))
        con.execute(f'DROP TABLE IF EXISTS "{name}"')
        if "items" not in data:
            continue
        cols = {}
        for item in data["items"]:
            for k, v in item.items():
                kind = SQL_TYPE[type(v)]
                cols[k] = "REAL" if {cols.get(k), kind} == {"INTEGER", "REAL"} else cols.get(k, kind)   # 990 and 990.5 → REAL
        first, *rest = cols
        con.execute(f'CREATE TABLE "{name}" ("{first}" {cols[first]} PRIMARY KEY, ' + ", ".join(f'"{c}" {cols[c]}' for c in rest) + ")")
        for item in data["items"]:
            keys = list(item)
            con.execute(f'INSERT INTO "{name}" ({", ".join(f"{chr(34)}{k}{chr(34)}" for k in keys)}) VALUES ({", ".join("?" * len(keys))})',
                        [json.dumps(item[k], ensure_ascii=False) if isinstance(item[k], (list, dict)) else item[k] for k in keys])
    con.execute("INSERT INTO seed (id, hash, at) VALUES (1, ?, ?) ON CONFLICT (id) DO UPDATE SET hash = excluded.hash, at = excluded.at", (digest, now()))
    con.commit()
    return True


def business_table(name: str):
    """A business table as the JSON had it: a list of dicts (empty fields left out), or the object for business/rewards."""
    if name not in TABLES:
        raise KeyError(name)
    with closing(connect()) as con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone():
            return {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT key, value FROM settings WHERE source = ? ORDER BY rowid", (name,))}
        kinds = {c["name"]: c["type"] for c in con.execute(f'PRAGMA table_info("{name}")')}
        rows = con.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
        return [{k: json.loads(r[k]) if kinds[k] == "JSON" else r[k] for k in r.keys() if r[k] is not None} for r in rows]


def setting(source: str, key: str):
    with closing(connect()) as con:
        row = con.execute("SELECT value FROM settings WHERE source = ? AND key = ?", (source, key)).fetchone()
        return json.loads(row[0]) if row else None


def set_status(name: str, item_id: str, status: str) -> bool:
    """Staff change from the admin page. False when the row does not exist."""
    if name not in ("payments", "bookings", "promotions"):
        raise KeyError(name)
    with closing(connect()) as con:
        n = con.execute(f'UPDATE "{name}" SET status = ? WHERE id = ?', (status, item_id)).rowcount
        con.commit()
        return n > 0
