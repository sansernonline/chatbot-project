"""Pick the report test set from the central library: questions 10 · images 5 · safety 5.

    python qa/tools/build_report_set.py

Reads qa/1-questions.md 2-images.md 3-safety.md, writes qa/report/x-fitness-test-cases.md. Never edit the output —
change a row in the library, or change the picked ids in REPORT below, then run this again.
"""
from pathlib import Path

QA = Path(__file__).resolve().parents[1]
OUT = QA / "report" / "x-fitness-test-cases.md"

# suite: (library file, heading, ids to pick — the order here is the order in the report)
REPORT = {
    "1": ("1-questions.md", "ชุดคำถามทดสอบ", [f"Q{i:02d}" for i in range(1, 11)]),
    "2": ("2-images.md", "ชุดภาพทดสอบ", [f"I{i:02d}" for i in range(1, 6)]),
    "3": ("3-safety.md", "ชุดทดสอบความปลอดภัย", [f"S{i:02d}" for i in range(1, 6)]),
}
SIZE = {"1": 10, "2": 5, "3": 5}                                             # what the course asks for
HEAD = ["| รหัส | ข้อความที่ลูกค้าพิมพ์ | ภาพที่แนบ | สมาชิก | ผลที่คาดหวัง | ต้องมีทุกคำ | ต้องมีอย่างน้อย 1 คำ | ห้ามมี | ตรวจเพิ่ม |",
        "|---|---|---|---|---|---|---|---|---|"]

INTRO = """# X Fitness Chatbot — เอกสาร Test Case (ชุดทำรายงาน)

> ผู้พัฒนา: 68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ · ข้อมูลทั้งหมดเป็นข้อมูลจำลอง
> **ไฟล์นี้หยิบมาจากคลังกลาง `qa/1-questions.md` `qa/2-images.md` `qa/3-safety.md` — อย่าแก้มือ** แก้แถวในคลัง (หรือเปลี่ยนรหัสที่หยิบใน `qa/tools/build_report_set.py`) แล้วรัน `python qa/tools/build_report_set.py`

ชุดตามข้อกำหนดวิชา: คำถาม 10 ข้อ · ภาพ 5 ภาพ · ความปลอดภัย 5 กรณี

| ต้องการ | คำสั่ง | ผลที่ได้ |
|---|---|---|
| ทดสอบชุดนี้ผ่าน API (เร็ว ตรวจผลตรวจสลิปได้) | `cd x-fitness/backend && python -m eval.run` | `qa/report/results/x-fitness-api-results.md` |
| ทดสอบชุดนี้ผ่านหน้าเว็บ (Playwright เหมือนลูกค้า) | `cd x-fitness/e2e && npm test` | `qa/report/results/x-fitness-ui-results.md` + ภาพหน้าจอ |
| ทดสอบระบบรวม: สุ่มหมวดละ 100 ข้อจากคลัง | `cd x-fitness/backend && python -m eval.run --system --sample 100 --seed 1` | `qa/system/results/x-fitness-system-api-results.md` |
| สร้างแถว "สร้างจากข้อมูลร้าน" ในคลังใหม่ (หลังแก้ `data/db/*.json`) | `python qa/tools/make_bulk_cases.py` | คลังกลาง |

วิธีเขียนแถว (ใช้เหมือนกันทั้งคลังและไฟล์นี้):

- **รหัส** Q/I/S ชุดหลัก · D-xx/N-xx กฎต้องทำ/ห้ามทำใน `docs/03_bot-rules.md` · XI/XS ชุดหาจุดอ่อน · BQ/BI/BS/BO สร้างจากสคริปต์
- **ภาพที่แนบ** ชื่อไฟล์ใน `qa/test-images/` · **สมาชิก** รหัสสมาชิกที่ยืนยันตัวตนก่อนถาม (เบอร์ 4 ตัวท้ายดึงจากข้อมูลจำลอง) · `-` = ไม่มี
- **ต้องมีทุกคำ / ต้องมีอย่างน้อย 1 คำ / ห้ามมี** คั่นหลายคำด้วย ` ; ` · ตัวเลขเทียบโดยไม่สนใจจุลภาค (1,290 = 1290)
- **ตรวจเพิ่ม** คั่นด้วย ` ; ` : `guard=N-07` รหัสกฎที่ต้องทำงาน · `อ้างอิง=KB-04` เอกสารที่ต้องอ้าง · `ภาพ.amount=990` ค่าที่อ่านจากภาพ · `สลิปผ่าน=ใช่` ผลตรวจสลิป (ตรวจได้เฉพาะสคริปต์ API)
- ผลที่คาดหวังที่ขึ้นต้นว่า "จุดเสี่ยง" ตั้งใจเขียนเพื่อยืนยันช่องโหว่ที่สงสัย อาจไม่ผ่านได้"""


def rows(path: Path) -> dict[str, list[str]]:
    """id → table rows of one library file (a list, because an id can repeat, e.g. D-04 asked twice)."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith(("| รหัส", "|---")):
            out.setdefault(line.split("|")[1].strip(), []).append(line)
    return out


def main():
    lines, counts = [INTRO], []
    for n, (name, title, ids) in REPORT.items():
        found = rows(QA / name)
        if missing := [i for i in ids if i not in found]:
            raise SystemExit(f"{name}: ไม่พบรหัส {', '.join(missing)}")
        picked = [r for i in ids for r in found[i]]
        if len(picked) != SIZE[n]:
            raise SystemExit(f"หมวด {n} ต้องมี {SIZE[n]} ข้อ แต่หยิบได้ {len(picked)}")
        lines += ["", f"## {n}. {title}", "", *HEAD, *picked]
        counts.append(f"{title} {len(picked)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {' · '.join(counts)}")


if __name__ == "__main__":
    main()
