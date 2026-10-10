"""data/db/*.json → shared/db.js (const DB = {...}) for the website and admin, in mockup/ and its copy x-fitness/frontend/.

python data/build_db_js.py          run after editing any file in data/db/ (then copy data/ to x-fitness/data/ as usual)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"business": "business", "packages": "packages", "classes": "classes", "trainers": "trainers", "schedule": "schedule",
         "pt": "pt_packages", "products": "products", "promotions": "promotions", "rewards": "rewards", "members": "members",
         "bookings": "bookings", "payments": "payments", "leads": "leads"}   # DB key → data/db file (order kept as before)
OUT = [ROOT / "mockup/shared/db.js", ROOT / "x-fitness/frontend/shared/db.js"]


def entry(name: str):
    d = json.loads((ROOT / "data/db" / f"{name}.json").read_text(encoding="utf-8"))
    return d["items"] if "items" in d else {k: v for k, v in d.items() if k != "_note"}


text = ("/* generated from data/db/*.json — shared by site (index.html) and admin */\n"
        f"const DB = {json.dumps({k: entry(f) for k, f in FILES.items()}, ensure_ascii=False)};\n")
if __name__ == "__main__":
    for out in OUT:
        out.write_text(text, encoding="utf-8")
    print("wrote", ", ".join(str(o.relative_to(ROOT)) for o in OUT))
