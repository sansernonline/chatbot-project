"""Demo admin login: one account from config, tokens kept in memory (cleared on restart)."""
import secrets

from fastapi import Header, HTTPException

from . import config

_tokens: set[str] = set()


def login(user: str, password: str) -> str | None:
    ok = secrets.compare_digest(user, config.ADMIN_USER) & secrets.compare_digest(password, config.ADMIN_PASS)
    if not ok:
        return None
    token = secrets.token_urlsafe(24)
    _tokens.add(token)
    return token


def require_admin(authorization: str = Header(default="")) -> None:
    if authorization.removeprefix("Bearer ") not in _tokens:
        raise HTTPException(401, "ต้องล็อกอินผู้ดูแลก่อน")
