"""Run the checklist test sets against the real bot and write the results table.

    cd x-fitness/backend
    python -m eval.run                  # questions + images + safety + 10 random do/don't rules
    python -m eval.run --rules all      # every rule test
    python -m eval.run --seed 7         # repeat a previous random draw

Needs TYPHOON_API_KEY in backend/.env and the committed rag-index. Uses a throwaway chat database.
Reads the cases from qa/x-fitness-test-cases.md; writes qa/results/x-fitness-api-results.md (+ .json).
"""
import argparse
import json
import random
import tempfile
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app import config, db, rag
from eval import testcases

QA_DIR = config.PROJECT_ROOT.parent / "qa"
CASES_FILE = QA_DIR / "x-fitness-test-cases.md"
OUT_DIR = QA_DIR / "results"


def check(spec: dict, res: dict, vision: dict | None = None) -> list[str]:
    """Reasons the response fails the spec (empty list = pass)."""
    answer = (res.get("answer") or "").replace(",", "")
    bad = []
    if spec.get("all") and (miss := [s for s in spec["all"] if s.replace(",", "") not in answer]):
        bad.append(f"ไม่มี {', '.join(miss)}")
    if spec.get("any") and not any(s.replace(",", "") in answer for s in spec["any"]):
        bad.append(f"ไม่มีคำใดใน {spec['any']}")
    if found := [s for s in spec.get("none", []) if s.replace(",", "") in answer]:
        bad.append(f"มีคำต้องห้าม {', '.join(found)}")
    if spec.get("rule") and spec["rule"] not in res.get("rules", []):
        bad.append(f"guard ไม่ทำงาน (ต้องมี {spec['rule']})")
    if spec.get("source") and spec["source"] not in res.get("sources", []):
        bad.append(f"ไม่อ้าง {spec['source']}")
    if "slip" in spec and (res.get("slip_check") or {}).get("ok") is not spec["slip"]:
        bad.append(f"ผลตรวจสลิปควรเป็น {spec['slip']}")
    for field, want in spec.get("vision", {}).items():
        got = (vision or {}).get(field)
        same = isinstance(want, (int, float)) and isinstance(got, (int, float)) and abs(got - want) < 0.01
        if not same and got != want:
            bad.append(f"อ่านภาพ {field}={got} (ควรเป็น {want})")
    if res.get("error"):
        bad.append(res["error"])
    return bad


class Bot:
    def __init__(self):
        config.DB_PATH = Path(tempfile.mkdtemp()) / "eval.sqlite3"
        db.init()
        from app.main import app
        self.client, self.n = TestClient(app), 0

    def ask(self, message: str, member: str | None = None, vision: dict | None = None) -> dict:
        self.n += 1
        session = "".join(f"{c}{d}" for c, d in zip("EVALTEST", f"{self.n:05d}"))[:10]   # fresh chat, no history
        r = self.client.post("/api/chat", json={"session_id": session, "message": message, "member_id": member, "vision": vision})
        return r.json() if r.status_code == 200 else {"answer": "", "error": f"HTTP {r.status_code}: {r.text[:120]}"}

    def read(self, image: Path) -> dict:
        r = self.client.post("/api/vision", files={"image": (image.name, image.read_bytes(), "image/png")})
        return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text[:120]}"}


def run(rule_sample: int | None, seed: int) -> dict:
    bot, results = Bot(), {}

    def record(suite, cid, label, expected, ask, spec, vision=None, extra_secs=0.0):
        t = time.time()
        res = ask()
        secs = round(time.time() - t + extra_secs, 1)
        bad = check(spec, res, vision)
        results.setdefault(suite, []).append({"id": cid, "input": label, "expected": expected, "answer": res.get("answer", ""),
                                              "analysis": analysis(res, vision), "pass": not bad, "why": "; ".join(bad),
                                              "seconds": secs, "sources": res.get("sources", []), "rules": res.get("rules", []),
                                              **({"vision": vision} if vision else {})})
        print(f"{'PASS' if not bad else 'FAIL'} {cid} {secs:>5}s {label[:50]}" + (f"  ← {'; '.join(bad)}" if bad else ""))

    cases = testcases.load(CASES_FILE)
    rules = [c for c in cases if c["suite"] == "rules"]
    picked = rules if rule_sample is None else random.Random(seed).sample(rules, min(rule_sample, len(rules)))
    for c in [c for c in cases if c["suite"] != "rules"] + picked:
        msg, member, label = c["message"], c["member"], f"\"{c['message']}\"" + (f" · สมาชิก {c['member']}" if c["member"] else "")
        vision, extra = None, 0.0
        if c["image"]:
            t = time.time()
            vision = bot.read(config.TEST_IMAGES_DIR / c["image"])               # response time includes reading the image
            extra, label = time.time() - t, f"ภาพ {c['image']} · " + label
        record(c["suite"], c["id"], label, c["expected"],
               lambda: bot.ask(msg, member, None if not vision or vision.get("error") else vision), c["spec"], vision, extra)
    return results


def analysis(res: dict, vision: dict | None) -> str:
    """What the system did, in words: what it read from the image, the slip check, which protection fired."""
    parts = []
    if vision:
        fields = {k: v for k, v in vision.items() if k not in ("raw_text", "type") and v not in (None, "", [])}
        parts.append(f"อ่านภาพเป็น {vision.get('type')}: " + ", ".join(f"{k}={v}" for k, v in list(fields.items())[:6]))
    if slip := res.get("slip_check"):
        passed = sum(c["pass"] for c in slip["checks"])
        failed = [c["rule"] for c in slip["checks"] if not c["pass"]]
        parts.append(f"ตรวจสลิปผ่าน {passed}/{len(slip['checks'])} ข้อ" + (f" ไม่ผ่าน: {'; '.join(failed)}" if failed else ""))
    if res.get("rules"):
        parts.append(f"guard ทำงาน: {', '.join(res['rules'])}")
    elif not vision:
        parts.append("ตอบโดย LLM จากคลังความรู้ (ไม่มี guard ทำงาน)")
    if res.get("actions"):
        parts.append(f"ปุ่มตอบด่วน: {', '.join(res['actions'])}")
    return " · ".join(parts)


SUITES = {  # key: (title, column heading for the result)
    "questions": ("1. ชุดคำถามทดสอบ 10 ข้อ", "ผลตอบของบอท"),
    "images": ("2. ชุดภาพทดสอบ 5 ภาพ", "ผลวิเคราะห์ (อ่านภาพ · ตรวจสลิป) และคำตอบ"),
    "safety": ("3. ชุดทดสอบความปลอดภัย 5 กรณี", "ผลวิเคราะห์ (มาตรการที่ทำงาน) และคำตอบ"),
    "rules": ("4. ภาคผนวก: สุ่มทดสอบรายการต้องทำ/ห้ามทำ", "ผลตอบของบอท"),
}


def report(results: dict, seed: int, sample: int | None) -> str:
    cell = lambda s: str(s).replace("|", "/").replace("\n", " ").strip()
    total = [r for rows in results.values() for r in rows]
    lines = ["# X Fitness Chatbot — ผลทดสอบผ่าน API", "",
             "| รายการ | ค่า |", "|---|---|",
             "| โครงงาน | X Fitness Chatbot — แชตบอทตอบลูกค้าสตูดิโอฟิตเนส เอ็กซ์ ฟิตเนส ศรีราชา |",
             "| ผู้พัฒนา | 68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ |",
             f"| วันเวลาที่ทดสอบ | {datetime.now():%Y-%m-%d %H:%M} |",
             f"| ระบบที่ทดสอบ | backend จริง (FastAPI) · LLM `{config.CHAT_MODEL}` · อ่านภาพ `{config.VISION_MODEL}` · ค้นคลังความรู้ {rag.engine()} |",
             f"| วิธีทดสอบ | `cd x-fitness/backend && python -m eval.run` ยิงคำถามเข้า `/api/chat` และ `/api/vision` แล้วตรวจคำตอบอัตโนมัติ · "
             f"สุ่มกฎ {'ทั้งหมด' if sample is None else f'{sample} ข้อ (seed {seed})'} |",
             "| เกณฑ์ผ่าน | คำตอบมีข้อมูลที่ต้องมีครบ ไม่มีข้อความต้องห้าม และมาตรการ (guard) ที่ควรทำงานได้ทำงาน — เกณฑ์แต่ละข้ออยู่ใน `qa/x-fitness-test-cases.md` |",
             "| เวลาตอบ | วินาที วัดจากส่งคำขอถึงได้คำตอบ (ภาพรวมเวลาอ่านภาพด้วย) |", "",
             "## สรุปผล", "", "| ชุดทดสอบ | ผ่าน | ไม่ผ่าน | เวลาตอบเฉลี่ย (วินาที) | เร็วสุด–ช้าสุด |", "|---|---|---|---|---|"]
    for key, (title, _) in SUITES.items():
        if rows := results.get(key, []):
            secs = [r["seconds"] for r in rows]
            ok = sum(r["pass"] for r in rows)
            lines.append(f"| {title.split('. ', 1)[1]} | {ok}/{len(rows)} | {len(rows) - ok} | {sum(secs) / len(secs):.1f} | {min(secs)}–{max(secs)} |")
    lines.append(f"| **รวม** | **{sum(r['pass'] for r in total)}/{len(total)}** | {sum(not r['pass'] for r in total)} | "
                 f"{sum(r['seconds'] for r in total) / len(total):.1f} | |")
    for key, (title, result_col) in SUITES.items():
        rows = results.get(key, [])
        if not rows:
            continue
        lines += ["", f"## {title}", "",
                  f"| รหัส | ข้อมูลเข้า | ผลที่คาดหวัง | {result_col} | ผ่าน/ไม่ผ่าน | เวลาตอบ (วินาที) | อ้างอิง |", "|---|---|---|---|---|---|---|"]
        for r in rows:
            got = cell(r["answer"])[:320]
            if key in ("images", "safety") and r["analysis"]:
                got = f"**{cell(r['analysis'])}** — {got}"
            verdict = "✅ ผ่าน" if r["pass"] else f"❌ ไม่ผ่าน — {cell(r['why'])}"
            lines.append(f"| {r['id']} | {cell(r['input'])} | {cell(r['expected'])} | {got} | {verdict} | {r['seconds']} | {' '.join(r['sources'])} |")
    lines += ["", "## หมายเหตุ", "",
              "- ผลตัดสินอัตโนมัติจากคำสำคัญ ควรให้ผู้ทดสอบอ่านคำตอบทวนก่อนสรุป",
              "- LLM และโมเดลอ่านภาพให้ผลต่างกันได้เล็กน้อยในแต่ละรอบ ควรรันซ้ำอย่างน้อย 2–3 รอบ",
              "- ข้อมูลร้าน สมาชิก และภาพทั้งหมดเป็นข้อมูลจำลอง"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rules", default="10", help="how many do/don't rule tests to draw at random, or 'all'")
    ap.add_argument("--seed", type=int, default=random.randrange(1000))
    a = ap.parse_args()
    sample = None if a.rules == "all" else int(a.rules)
    if not config.TYPHOON_API_KEY:
        raise SystemExit("ต้องใส่ TYPHOON_API_KEY ใน backend/.env ก่อน")
    print(f"seed {a.seed} · engine {rag.engine()}")
    results = run(sample, a.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "x-fitness-api-results.md").write_text(report(results, a.seed, sample), encoding="utf-8")
    (OUT_DIR / "x-fitness-api-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nเขียนผลที่ {OUT_DIR / 'x-fitness-api-results.md'}")
