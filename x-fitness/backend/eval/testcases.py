"""Read test cases from a case file (qa/report/x-fitness-test-cases.md, the same file the Playwright tests read)
or from the folder holding the central library (qa/1-questions.md 2-images.md 3-safety.md).

Each table row under "## 1." … "## 3." is one case ("###" sub-headings stay in the same suite):
| รหัส | ข้อความ | ภาพ | สมาชิก | ผลที่คาดหวัง | ต้องมีทุกคำ | ต้องมีอย่างน้อย 1 คำ | ห้ามมี | ตรวจเพิ่ม |
Lists are separated by " ; " and "-" means empty.
"""
import re
from pathlib import Path

SUITES = {"1": "questions", "2": "images", "3": "safety"}


def _list(cell: str) -> list[str]:
    return [] if cell in ("", "-") else [x.strip() for x in cell.split(" ; ") if x.strip()]


def _value(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def _spec(must_all: str, must_any: str, must_not: str, extra: str) -> dict:
    spec = {"all": _list(must_all), "any": _list(must_any), "none": _list(must_not), "vision": {}}
    for item in _list(extra):
        key, _, val = item.partition("=")
        if key == "guard":
            spec["rule"] = val
        elif key == "อ้างอิง":
            spec["source"] = val
        elif key == "สลิปผ่าน":
            spec["slip"] = val == "ใช่"
        elif key.startswith("ภาพ."):
            spec["vision"][key[4:]] = _value(val)
    return spec


def load(path: Path) -> list[dict]:
    if path.is_dir():                                   # the library: 1-questions.md 2-images.md 3-safety.md
        return [c for f in sorted(path.glob("[0-9]-*.md")) for c in load(f)]
    cases, suite = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## (\d)\.", line):
            suite = SUITES.get(m.group(1))
        elif suite and line.startswith("| ") and not line.startswith(("| รหัส", "|---")):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 9:
                raise ValueError(f"{path.name}: ต้องมี 9 ช่อง: {line[:80]}")
            cid, message, image, member, expected, *checks = cells
            cases.append({"suite": suite, "id": cid, "message": message, "image": None if image == "-" else image,
                          "member": None if member == "-" else member, "expected": expected, "spec": _spec(*checks)})
    return cases
