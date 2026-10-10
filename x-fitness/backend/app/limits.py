"""Abuse limits checked in code before any model call, kept in memory (one server process; a restart clears them).

1. Messages per minute: every website message, image and LINE message costs a Typhoon call (and LightRAG work), so
   one client firing messages in a loop could use up the API quota. Website = per IP, LINE = per LINE user.
2. Member code guessing: chat.MAX_VERIFY_FAILS counts wrong phone digits per chat, but the website makes up its own
   session_id, so a new chat started the count again. This count is per member code, across every chat and the
   member_id/phone_last4 fields of /api/chat: after VERIFY_MAX_FAILS wrong tries the code is locked for VERIFY_LOCK_MIN.
"""
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from . import config

TOO_FAST = "ส่งข้อความถี่เกินไปค่ะ รอสักครู่แล้วพิมพ์ใหม่อีกครั้ง หรือโทร 038-000-888"
_hits: dict[str, deque] = defaultdict(deque)                  # key → times of recent hits
_lock = threading.Lock()


def allow(key: str, limit: int, window_s: float = 60.0, now: float | None = None) -> bool:
    """True and counts the hit when the key has had fewer than `limit` hits in the last `window_s` seconds."""
    now = time.monotonic() if now is None else now
    with _lock:
        hits = _hits[key]
        while hits and hits[0] <= now - window_s:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        if len(_hits) > 10_000:                                # many one-off clients: drop the keys with no recent hits
            for k in [k for k, v in _hits.items() if not v or v[-1] <= now - 3600]:
                del _hits[k]
        return True


def client_ip(request: Request) -> str:
    """The caller's IP. Behind Render's proxy every request comes from the proxy, so the real client is the last
    X-Forwarded-For entry (the one the proxy added; earlier entries are whatever the client sent)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.rsplit(",", 1)[-1].strip() or (request.client.host if request.client else "unknown")


def _code(member_code: str) -> str:
    """'fn 10003', 'FN-10003' → 'FN-10003' so every spelling shares one count."""
    m = re.search(r"(\d{5})", member_code or "")
    return f"FN-{m.group(1)}" if m else (member_code or "").upper()


def verify_locked(member_code: str, now: float | None = None) -> bool:
    now = time.monotonic() if now is None else now
    with _lock:
        fails = _hits.get("verify:" + _code(member_code), ())
        return sum(t > now - config.VERIFY_LOCK_MIN * 60 for t in fails) >= config.VERIFY_MAX_FAILS


def verify_failed(member_code: str, now: float | None = None) -> None:
    with _lock:
        _hits["verify:" + _code(member_code)].append(time.monotonic() if now is None else now)


def verify_ok(member_code: str) -> None:
    with _lock:
        _hits.pop("verify:" + _code(member_code), None)


def reset() -> None:
    """Forget every count (tests)."""
    with _lock:
        _hits.clear()
