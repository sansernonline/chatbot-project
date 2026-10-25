"""Copy everything x-fitness/ needs from the project root, then build the ready-made database. Run before committing.

    python x-fitness/tools/build_dist.py          # from anywhere in the project

What it does, in order:
  1. data/db/*.json → mockup/shared/db.js (the website's offline data, data/build_db_js.py)
  2. mockup/ → frontend/ · data/knowledge-base, guard → data/ · qa/test-images → qa/ (data/db/*.json is not copied: step 4 puts it in the database)
  3. the newest version of each deck/report in docs/ → documents/ (copied as they are)
  4. data/db/*.json at the project root → data/db/xfitness_db.sqlite3 (every table, shop data, sample chats, synonyms, data dictionary)
  5. warns when the knowledge base changed but data/rag-index/ was not rebuilt (that needs Typhoon: python -m app.rag)
Nothing is deleted: files that exist only in x-fitness/ (data/rag-index/, documents/index.html) stay.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]          # x-fitness/
ROOT = APP.parent
BACKEND = APP / "backend"
PY = next((p for p in [BACKEND / ".venv/Scripts/python.exe", BACKEND / ".venv/bin/python"] if p.exists()), Path(sys.executable))
COPIES = [("mockup", "frontend"), ("data/knowledge-base", "data/knowledge-base"),
          ("data/guard", "data/guard"), ("qa/test-images", "qa")]
VERSIONED = re.compile(r"XFitness-Chatbot_(.+?)-v(\d+(?:\.\d+)*)\.(html|pptx|docx)$")   # docs/XFitness-Chatbot_Presentation-v1.2.pptx


def run(*args, cwd=ROOT, show=None):
    print("  $", show or " ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def newest_documents() -> dict[str, Path]:
    """documents/ name → newest docs/ file, e.g. XFitness-Chatbot_Presentation.pptx → docs/…-v1.2.pptx"""
    best = {}
    for f in (ROOT / "docs").iterdir():
        if m := VERSIONED.match(f.name):
            name, version = f"XFitness-Chatbot_{m[1]}.{m[3]}", tuple(int(n) for n in m[2].split("."))
            if name not in best or version > best[name][0]:
                best[name] = (version, f)
    return {name: f for name, (_, f) in best.items()}


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)   # keep our lines in order with the commands' own output
    print("1. offline data for the website")
    run(PY, "data/build_db_js.py")
    print("2. copy from the project root")
    for src, dst in COPIES:
        shutil.copytree(ROOT / src, APP / dst, dirs_exist_ok=True)
        print(f"  {src}/ → x-fitness/{dst}/")
    print("3. decks and report")
    for name, f in sorted(newest_documents().items()):
        shutil.copy2(f, APP / "documents" / name)
        print(f"  docs/{f.name} → x-fitness/documents/{name}")
    print("4. ready-made database")
    run(PY, "-m", "app.db", cwd=BACKEND)
    print("5. knowledge index")
    run(PY, "-c", "from app import rag; old = rag._manifest(); new = {d: v['hash'] for d, v in rag.kb_files().items()}; "
                  "stale = sorted(d for d in new if old.get(d) != new[d]); "
                  "print('  data/rag-index/ is up to date' if not stale else '  WARNING: rebuild data/rag-index/ (python -m app.rag) for ' + ', '.join(stale))",
        cwd=BACKEND, show="compare data/knowledge-base with data/rag-index/manifest.json")
    print("done — check `git status`, then commit")


if __name__ == "__main__":
    main()
