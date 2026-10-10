"""Guard replies live in data/guard/replies.md; the codes in guard.py must stay listed in docs/03_bot-rules.md."""
import re
from pathlib import Path

import pytest

from app import config, guard

GUARD_SOURCE = Path(guard.__file__).read_text(encoding="utf-8")
RULES_DOC = Path(__file__).resolve().parents[3] / "docs" / "03_bot-rules.md"


def test_reply_file_format(tmp_path):
    f = tmp_path / "replies.md"
    f.write_text("# notes\n- not a reply\n\n## X-01 — note\n\nline one\nline two\nปุ่ม: a · b\n\n## X-02\n\nno buttons\n", encoding="utf-8")
    assert guard.load_replies(f) == {"X-01": ("line one line two", ["a", "b"]), "X-02": ("no buttons", [])}


def test_every_reply_is_used_and_not_empty():
    replies = guard.load_replies(config.GUARD_REPLIES)
    assert all(text for text, _ in replies.values())
    unused = [k for k in replies if f'R["{k}"]' not in GUARD_SOURCE]
    assert not unused, f"replies.md has codes guard.py never uses: {unused}"


@pytest.mark.skipif(not RULES_DOC.exists(), reason="docs/ is outside the deployed app")
def test_rule_codes_are_documented():
    codes = set(re.findall(r'"((?:D|N)-\d\d|S\d{1,2}|G-[A-Z]+)"', GUARD_SOURCE))
    assert len(codes) > 20                                                   # the pattern still finds the codes
    doc = RULES_DOC.read_text(encoding="utf-8")
    missing = sorted(c for c in codes if not re.search(rf"\b{re.escape(c)}\b", doc))
    assert not missing, f"codes in guard.py but not in docs/03_bot-rules.md: {missing}"
