"""Build the 10-minute demo deck as one HTML file that opens offline.

    python docs/deck/build.py

Reads slides.html + shell.html + content.py, takes the 20 demo cases (10 questions, 5 images, 5 safety)
from qa/report/results/x-fitness-ui-results.md, embeds the test images and screenshots, and writes
docs/XFitness-Chatbot_Presentation-Deck-v1.5.html. Needs Pillow."""
import base64, io, json, math, re, sys
from html import escape as html_escape, unescape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "qa/report/results/x-fitness-ui-results.md"
IMAGES = ROOT / "x-fitness/qa"
OUT = ROOT / "docs/XFitness-Chatbot_Presentation-Deck-v1.5.html"
KB = ROOT / "x-fitness/data/knowledge-base"
RAG_INDEX = ROOT / "x-fitness/data/rag-index"
REPLIES = ROOT / "x-fitness/data/guard/replies.md"
sys.path.insert(0, str(HERE))
import content  # noqa: E402


def data_uri(path: Path, width: int) -> str:
    """Downscaled JPEG so 25 images stay small."""
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def png_uri(path: Path) -> str:
    """Original image, so live OCR in the playground reads the same pixels as the tests did."""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


CODES = re.compile(r"\b(S\d{1,2}|[NDG]-\d\d|G-[A-Z]+)\b")


def cases() -> tuple[dict, dict]:
    """All 40 rows of the results table → (demo sets Q/I/S with screenshots, every case by id for the playgrounds)."""
    sets, every = {"q": [], "img": [], "safe": []}, {}
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| ([QIS]\d\d|[DN]-\d\d) \|", line)
        if not m:
            continue
        cid, given, expect, shown, verdict, sec, *rest = [c.strip() for c in line.strip("|").split(" | ")]
        if "ผ่าน" not in verdict or "ไม่ผ่าน" in verdict:
            sys.exit(f"{cid} did not pass in {RESULTS.name} — the deck only shows passed cases")
        badges, answer = [], shown
        if shown.startswith("**"):                       # "**อ่านภาพ: … / guard ทำงาน: …** — answer"
            head, _, answer = shown[2:].partition("** — ")
            badges = [b.strip() for b in head.split(" · ")]
        quoted = re.findall(r'"([^"]+)"', given)
        case = dict(id=cid, q=quoted[0] if quoted else given, expect=expect, a=answer.replace("<br>", "\n"),
                    sec=sec, sources=rest[0] if rest else "", badges=badges, live=cid in content.LIVE, hint=content.MEMBER_HINT.get(cid, ""))
        guard = next((b for b in badges if b.startswith("guard")), "")
        buttons = next((b.split(": ", 1)[1] for b in badges if b.startswith("ปุ่ม")), "")
        seen = next((b.split(": ", 1)[1] for b in badges if b.startswith("อ่านภาพ")), "")
        play = dict(q=case["q"], a=case["a"], sec=sec, src=case["sources"].split(), rules=CODES.findall(guard),
                    actions=[x.strip() for x in buttons.split(",") if x.strip()], vision=seen, hint=case["hint"])
        if cid[0] == "I":
            name = re.search(r"(\d\d_[\w]+\.png)", given).group(1)
            play["img"], play["imgPath"] = png_uri(IMAGES / name), f"x-fitness/qa/{name}"
        key = cid + ("b" if cid in every else "")     # D-04 and N-09 have 2 cases each
        every[key] = play
        if cid[0] in "DN":
            continue
        shot = re.search(r"screenshots/([^)\"\s]+\.png)", line)   # [ภาพ](screenshots/x.png) or <img src="screenshots/x.png">
        if shot:
            case["shot"] = data_uri(RESULTS.parent / "screenshots" / shot.group(1), 480)
        if cid[0] == "I":
            name = re.search(r"(\d\d_[\w]+\.png)", given).group(1)
            case["img"], case["imgPath"] = play["img"], play["imgPath"]
        sets[{"Q": "q", "I": "img", "S": "safe"}[cid[0]]].append(case)
    counts = {k: len(v) for k, v in sets.items()}
    if counts != {"q": 10, "img": 5, "safe": 5}:
        sys.exit(f"expected 10/5/5 cases, found {counts}")
    if len(every) != 40:
        sys.exit(f"expected 40 cases, found {len(every)}")
    return sets, every


def canned() -> dict:
    """Offline answers for member verification, built from the real reply text in chat.py and members.json."""
    code = (ROOT / "x-fitness/backend/app/chat.py").read_text(encoding="utf-8")
    const = lambda name: re.search(rf'^{name} = "(.*)"$', code, re.M).group(1)
    done = re.search(r'f"(ยืนยันตัวตนแล้วครับ[^"]*)"', code).group(1)
    members = json.loads((ROOT / "x-fitness/data/db/members.json").read_text(encoding="utf-8"))["items"]
    out = {}
    for mid, last4 in (("FN-10003", "5531"), ("FN-10007", "3364")):
        m = next(x for x in members if x["member_id"] == mid)
        out[f"{mid} {last4}"] = dict(a=done.replace("{member['first_name']}", m["first_name"]), rules=["D-04"],
                                     actions=["แต้มของฉัน", "ยอดค้างชำระ"], member=dict(member_id=mid, phone_last4=last4), sec="")
        out[mid] = dict(a=const("ASK_LAST4").replace("{code}", mid), rules=["D-04"], sec="")
    out["FN-10003 1111"] = dict(a=const("VERIFY_FAILED"), rules=["D-04"], sec="")
    return out


def kb_docs() -> dict:
    """knowledge-base/*.md → {KB-01: {file, title, size, excerpt}} straight from the files."""
    docs = {}
    for f in sorted(KB.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        meta = dict(re.findall(r"^(doc_id|title): (.+)$", text, re.M))
        body = [l for l in text.split("---", 2)[-1].splitlines() if l.strip() and not l.startswith(">")]
        docs[meta["doc_id"]] = dict(file=f.name, title=meta["title"], size=f"{f.stat().st_size / 1024:.1f} KB",
                                    excerpt="\n".join(body[:12]))
    return docs


DB_FILE = ROOT / "x-fitness/data/xfitness_db.sqlite3"
DB_DICT = ROOT / "x-fitness/data/db/datadict.json"
DB_GROUP = {"shop": ("ข้อมูลร้าน", "red"), "chat": ("แชต", "blue"), "system": ("ระบบ", "")}


def db_tables() -> list[dict]:
    """Every table of the ready-made database with its data dictionary, row count and first row."""
    import sqlite3
    from contextlib import closing
    d = json.loads(DB_DICT.read_text(encoding="utf-8"))
    with closing(sqlite3.connect(DB_FILE)) as con:
        out = []
        for name, info in d["tables"].items():
            cur = con.execute(f'SELECT * FROM "{name}" ORDER BY rowid LIMIT 1')
            cols, first = [c[0] for c in cur.description], cur.fetchone()
            types = {c[1]: c[2] for c in con.execute(f'PRAGMA table_info("{name}")')}
            out.append(dict(name=name, rows=con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0], cols=cols, types=types,
                            first=dict(zip(cols, first)) if first else None, **info))
    return out


def db_cards(tables: list[dict]) -> dict:
    def code(t):
        w = max(len(c) for c in t["cols"])
        lines = [f'{c:<{w}}  {t["types"][c] or "-":<7}  {t["columns"].get(c, "")}' for c in t["cols"]]
        if t["first"]:
            lines += ["", "ตัวอย่าง 1 แถว:"] + [f"{c:<{w}}  {str(v)[:60]}" for c, v in t["first"].items() if v is not None]
        return "\n".join(lines)
    return {t["name"]: dict(path=f'xfitness_db.sqlite3 › {t["name"]}', tags=[list(DB_GROUP[t["group"]]), [f'{t["rows"]} แถว · {len(t["cols"])} คอลัมน์', ""]],
                            what=html_escape(f'{t["about"]} · ที่มา: {t["source"]}'), code=code(t)) for t in tables}


def db_list(tables: list[dict]) -> str:
    out = []
    for g, (label, _) in DB_GROUP.items():
        rows = [t for t in tables if t["group"] == g]
        out.append(f'<h6>{label} · {len(rows)} ตาราง · {sum(t["rows"] for t in rows):,} แถว</h6>'
                   + "".join(f'<div data-pick="db" data-key="{t["name"]}"><b>{t["name"]}</b><span>{t["rows"]}</span></div>' for t in rows))
    return "".join(out)


def kb_cards(docs: dict) -> dict:
    return {k: dict(path=f"x-fitness/data/knowledge-base/{d['file']}", tags=[[k, "red"], [d["size"], ""]],
                    what=html_escape(d["title"]), code=d["excerpt"]) for k, d in docs.items()}


def graph() -> tuple[str, dict]:
    """Two hops of the real graphml: the centre entity with 12 neighbours, then the student package with its own
    neighbours, so one customer question can be followed edge by edge (content.GRAPH_STORY) → (svg, cards)."""
    g = (RAG_INDEX / "graph_chunk_entity_relation.graphml").read_text(encoding="utf-8")
    fields = lambda body: {k: unescape(v) for k, v in re.findall(r'<data key="(d\d+)">(.*?)</data>', body, re.S)}
    nodes = {unescape(i): fields(b) for i, b in re.findall(r'<node id="(.*?)">(.*?)</node>', g, re.S)}
    edges = {}
    for src, dst, body in re.findall(r'<edge source="(.*?)" target="(.*?)">(.*?)</edge>', g, re.S):
        edges[frozenset((unescape(src), unescape(dst)))] = fields(body)
    near = lambda n: [next(iter(k - {n})) for k in edges if n in k and len(k) == 2]
    st = content.GRAPH_STORY
    c, hub, hit = content.GRAPH_CENTER, st["hub"], st["hit"]
    ring = [hub] + [n for n in near(c) if n != hub][:11]
    hop2 = [hit] + [n for n, _ in st["more"]]
    first = lambda s: s.split("<SEP>")[0]
    node = lambda n: nodes.get(n, {})
    edge = lambda a, z: edges[frozenset((a, z))]
    card = lambda a, z: dict(path=f'edge "{a}" — "{z}"', tags=[[edge(a, z).get("d9", ""), "red"], [first(edge(a, z).get("d10", "")), ""]],
                             what=html_escape(edge(a, z).get("d8", "")),
                             code=f'node "{z}" ({node(z).get("d1", "")})\n' + first(node(z).get("d2", ""))[:300])
    cards = {"q": dict(path=f'ลูกค้าถาม: "{st["q"]}"', tags=[["เดิน 2 เส้น", "red"], [st["src"], ""]], what=st["what"],
                       code=f'เส้นที่ 1  {c} → {hub}  ({edge(c, hub).get("d9", "").split(",")[0]})\n'
                            f'เส้นที่ 2  {hub} → {hit}  ({edge(hub, hit).get("d9", "").split(",")[0]})'),
             "c": dict(path=f'node "{c}"', tags=[[node(c).get("d1", ""), "blue"], [f"โยงตรงกับ {len(near(c))} จุด", ""]],
                       what=html_escape(first(node(c).get("d2", ""))), code=f'<node id="{c}">\n  type: {node(c).get("d1")}')}
    W, H, (cx, cy), R = 1000, 600, (300, 312), 225
    short = lambda s: html_escape(st["names"].get(s, s if len(s) <= 15 else s[:14] + "…"))
    svg = [f'<svg class="graph" viewBox="0 0 {W} {H}" width="100%" height="100%">']
    pos1 = []
    for n, name in enumerate(ring):                                   # hop 1: the hub sits at 3 o'clock, nearest hop 2
        a = 2 * math.pi * n / len(ring)
        pos1.append((cx + R * math.cos(a), cy + R * math.sin(a) * 0.86, name))
        cards[f"n{n}"] = card(c, name)
    hx, hy = pos1[0][0], pos1[0][1]
    ys = [cy] + [72, 150, 228, 400, 478][:len(hop2) - 1]
    pos2 = [(800, y, name) for y, name in zip(ys, hop2)]
    for n, (_, _, name) in enumerate(pos2):
        cards[f"s{n}"] = card(hub, name)
    def seg(x1, y1, r1, x2, y2, r2):
        d = math.hypot(x2 - x1, y2 - y1)
        return (f'x1="{x1 + (x2 - x1) * r1 / d:.0f}" y1="{y1 + (y2 - y1) * r1 / d:.0f}" '
                f'x2="{x2 - (x2 - x1) * r2 / d:.0f}" y2="{y2 - (y2 - y1) * r2 / d:.0f}"')
    ring_seg = [seg(cx, cy, 56, x, y, 30 if n == 0 else 24) for n, (x, y, _) in enumerate(pos1)]
    hop_seg = [seg(hx, hy, 30, x, y, 20) for x, y, _ in pos2]
    # gray base lines; a red copy of each runs over it when its end node (or the question) is picked
    svg += [f'<line {s} pathLength="1" style="--i:{n}"/>' for n, s in enumerate(ring_seg)]
    svg += [f'<line class="hop2" {s} pathLength="1" style="--i:{len(ring_seg) + j}"/>' for j, s in enumerate(hop_seg)]
    on_hub = " ".join(["n0", "q"] + [f"s{j}" for j in range(len(pos2))])
    svg += [f'<line class="ov" {s} pathLength="1" data-hot="graph" data-on="{on_hub if n == 0 else f"n{n}"}"/>' for n, s in enumerate(ring_seg)]
    svg += [f'<line class="ov seg2" {s} pathLength="1" data-hot="graph" data-on="s{j}{" q" if j == 0 else ""}"/>' for j, s in enumerate(hop_seg)]
    labels = [st["hit_label"]] + [lab for _, lab in st["more"]]
    for n, ((x, y, _), lab) in enumerate(zip(pos2, labels)):
        svg.append(f'<text class="elab{" no" if n == 0 else ""}" x="{(hx + x) / 2 + 10:.0f}" y="{(hy + y) / 2 - 8:.0f}" text-anchor="middle">{html_escape(lab)}</text>')
    svg += [f'<g data-pick="graph" data-key="n{n}" style="--i:{n}"{" class=\"hub\"" if n == 0 else ""}><circle cx="{x:.0f}" cy="{y:.0f}" r="{30 if n == 0 else 24}"/>'
            f'<text x="{x:.0f}" y="{y + (50 if n == 0 else 44):.0f}" text-anchor="middle">{short(name)}</text></g>' for n, (x, y, name) in enumerate(pos1)]
    svg += [f'<g data-pick="graph" data-key="s{n}" class="h2{" hit" if n == 0 else ""}"><circle cx="{x}" cy="{y}" r="20"/>'
            f'<text x="{x + 30}" y="{y + 6}">{short(name)}</text></g>' for n, (x, y, name) in enumerate(pos2)]
    svg.append(f'<g data-pick="graph" data-key="c"><circle cx="{cx}" cy="{cy}" r="56" style="stroke:#ff2536"/>'
               f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" style="font-weight:700;font-size:18px">{html_escape(c)}</text></g>')
    svg.insert(1, f'<g data-pick="graph" data-key="q" class="ask"><rect x="8" y="8" width="420" height="70" rx="12"/>'
                  f'<text x="26" y="35" class="k">ลูกค้าถาม · คลิกดูทางที่ LightRAG เดิน</text>'
                  f'<text x="26" y="64" class="v">"{html_escape(st["q"])}"</text></g>')
    svg.append(f'<text x="8" y="{H - 10}" class="legend"><tspan fill="#8a8a92">●</tspan> ชั้นที่ 1 โยงกับร้านตรง ๆ ({len(near(c))} จุด แสดง 12)'
               f'   <tspan fill="#5b8bd0">●</tspan> ชั้นที่ 2 โยงผ่าน "{html_escape(hub)}" ({len(near(hub))} จุด แสดง {len(hop2)})</text></svg>')
    return "".join(svg), cards


def line_chat(every: dict) -> str:
    """LINE OA demo page: LINE-style phone with the real rich menu (assets/rich-menu) laid over its tap areas."""
    menu = json.loads((ROOT / "assets/rich-menu/rich-menu.json").read_text(encoding="utf-8"))
    W, H = menu["size"]["width"], menu["size"]["height"]
    pct = lambda b: f'left:{b["x"] / W * 100:.2f}%;top:{b["y"] / H * 100:.2f}%;width:{b["width"] / W * 100:.2f}%;height:{b["height"] / H * 100:.2f}%'
    taps = "".join(f'<button type="button" class="rm" data-i="{n}" title="{html_escape(a["action"]["text"])}" style="{pct(a["bounds"])}"></button>'
                   for n, a in enumerate(menu["areas"]))
    return (f'<div class="lphone" id="lphone"><div class="lhead"><span>‹</span><b>X Fitness</b><span class="conn off"></span></div>'
            f'<div class="llog"></div><div class="lbar" title="เปิด/ปิดเมนู">{html_escape(menu["chatBarText"])} <span>▾</span></div>'
            f'<div class="rmenu"><img src="{data_uri(ROOT / "assets/rich-menu/rich-menu.jpg", 840)}" alt="rich menu">{taps}</div></div>')


def line_data(every: dict) -> dict:
    """What the LINE page plays. Offline answers are tested ones (nearest case, named in "note"); the handoff reply is line.py's own."""
    menu = json.loads((ROOT / "assets/rich-menu/rich-menu.json").read_text(encoding="utf-8"))
    code = (ROOT / "x-fitness/backend/app/line.py").read_text(encoding="utf-8")
    handoff = "".join(re.findall(r'"([^"]*)"', re.search(r'chat\.HANDOFF in text:.*?"answer": (".*?"\s*\n\s*".*?")', code, re.S).group(1)))
    v, slip = canned()["FN-10003 5531"], data_uri(ROOT / every["I01"]["imgPath"], 200)
    a = lambda k: {"a": every[k]["a"]}
    offline = {  # rich-menu text → (steps after the customer's tap, where the answer comes from)
        "แพ็กเกจและราคา": ([a("Q02")], "ไม่มีผลทดสอบของข้อความนี้ ใช้คำตอบ Q02 ที่ใกล้ที่สุด"),
        "ตารางคลาส": ([a("Q10")], "ไม่มีผลทดสอบของข้อความนี้ ใช้คำตอบ Q10 ที่ใกล้ที่สุด"),
        "โปรโมชันตอนนี้มีอะไรบ้าง": ([a("Q09")], "คำตอบจากผลทดสอบ Q09 (ถามแบบเดียวกัน)"),
        "ส่งสลิปชำระเงิน": ([{"img": slip}, a("I01")], "ส่งภาพสลิปต่อ แล้วใช้คำตอบจากผลทดสอบ I01"),
        "ขอดูข้อมูลสมาชิกของฉัน": ([{"u": "FN-10003 5531"}, {"a": v["a"], "acts": v["actions"]}], "ยืนยันสมาชิกก่อน คำตอบจากโค้ด chat.py"),
        "คุยกับพนักงาน": ([{"a": handoff}], "ข้อความตายตัวใน line.py · ส่งเรื่องเข้ากล่องแชตหลังบ้าน"),
    }
    buttons = [dict(text=x["action"]["text"], steps=offline[x["action"]["text"]][0], note=offline[x["action"]["text"]][1],
                    live=x["action"]["text"] != "คุยกับพนักงาน") for x in menu["areas"]]
    script = [{"u": "FN-10003 5531"}, {"a": v["a"], "acts": v["actions"]}, {"u": every["Q01"]["q"]}, a("Q01"),
              {"img": slip}, a("I01")]
    return dict(buttons=buttons, script=script)


def replies() -> dict:
    """data/guard/replies.md "## code — note" sections → cards (reply text + quick-reply buttons)."""
    out = {}
    text = REPLIES.read_text(encoding="utf-8")
    for n, (head, body) in enumerate(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", text, re.M | re.S)):
        lines = [l for l in body.strip().splitlines() if l.strip() and not l.startswith("#")]
        buttons = [l for l in lines if l.startswith("ปุ่ม:")]
        code, _, note = head.partition(" — ")
        out[f"r{n}"] = dict(path=f"x-fitness/data/guard/replies.md · ## {head}",
                            tags=[[code, "red"]] + ([[buttons[0], ""]] if buttons else []),
                            what=html_escape(note or code), code=" ".join(l for l in lines if l not in buttons))
    return out


def index_table() -> str:
    """rag-index/ files with their size on disk, biggest first."""
    rows = []
    for f in sorted(RAG_INDEX.iterdir(), key=lambda p: -p.stat().st_size):
        b = f.stat().st_size
        size = f"{b / 1e6:.2f} MB" if b > 1e6 else f"{b / 1024:.0f} KB" if b > 1024 else f"{b} B"
        rows.append(f'<tr><td class="m">{f.name}</td><td class="m" style="text-align:right">{size}</td>'
                    f'<td>{html_escape(content.INDEX_DESC.get(f.name, ""))}</td></tr>')
    return "".join(rows)


def retrieval_table(q_cases: list, docs: dict) -> str:
    """Q01–Q10 → the first 3 documents found (column "อ้างอิง" of the results file)."""
    rows = []
    for c in q_cases:
        src = [s for s in c["sources"].split() if s in docs][:3]
        tags = " ".join(f'<span class="tag {"red" if i == 0 else ""}">{s}</span>' for i, s in enumerate(src))
        top = html_escape(docs[src[0]]["title"]) if src else ""
        rows.append(f'<tr><td class="m">{c["id"]}</td><td>{html_escape(c["q"])}</td><td>{tags}</td>'
                    f'<td style="font-size:20px;color:var(--muted)">{top}</td></tr>')
    return "".join(rows)


def rules20(every: dict) -> dict:
    """The 20 do/don't cases (D-01…D-09, N-01…N-10) as clickable cards."""
    return {k: dict(path=f"qa/report/results/x-fitness-ui-results.md · {k}", tags=[[k, "red"], [f"{c['sec']} วินาที", ""], ["ผ่าน", "ok"]] + [[r, ""] for r in c["rules"]],
                    what=html_escape(c["q"]), code=c["a"]) for k, c in every.items() if k[0] in "DN"}


def arch_diagram() -> str:
    """Boxes and arrows of the architecture page from content.ARCH_NODES / ARCH_EDGES (5 columns × 5 rows)."""
    W, H, NW, NH, DX, DY = 1060, 575, 170, 60, 222, 128
    pos = {k: (col * DX, row * DY) for k, _, _, col, row, _ in content.ARCH_NODES}

    def path(a: str, b: str) -> str:
        (ax, ay), (bx, by) = pos[a], pos[b]
        if ax == bx:                                   # same column: straight down or up
            y1, y2 = (ay + NH, by) if by > ay else (ay, by + NH)
            return f"M{ax + NW / 2},{y1} L{bx + NW / 2},{y2 - 4 if by > ay else y2 + 4}"
        x1, x2 = (ax + NW, bx - 4) if bx > ax else (ax, bx + NW + 4)
        y1, y2, mid = ay + NH / 2, by + NH / 2, (x1 + x2) / 2
        return f"M{x1},{y1} H{mid} V{y2} H{x2}"            # across, up/down, across: straight lines only

    marker = lambda i, color: (f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" '
                               f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}" stroke="none"/></marker>')
    svg = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{marker("ah", "#8a8a92")}{marker("ahr", "#ff2536")}{marker("ahb", "#ff2536").replace('orient="auto"', 'orient="auto-start-reverse"')}</defs>']
    svg += [f'<path id="e-{a}-{b}" data-hot="arch" data-on="{a} {b}" d="{path(a, b)}"/>' for a, b in content.ARCH_EDGES]
    svg.append("</svg>")
    boxes = [f'<div class="node{" ext" if ext else ""}" data-pick="arch" data-key="{k}" '
             f'style="left:{pos[k][0]}px;top:{pos[k][1]}px;width:{NW}px{";border-color:#7a1d24" if k == "chat" else ""}">'
             f'<b>{html_escape(title)}</b><span>{html_escape(file)}</span></div>' for k, title, file, _, _, ext in content.ARCH_NODES]
    return "".join(svg) + "".join(boxes)


def tour() -> list:
    edges = {f"{a}>{b}" for a, b in content.ARCH_EDGES}
    for lit, _, _ in content.ARCH_TOUR:                # every step must light an arrow that exists
        for e in (x for group in lit for x in group.split("|")):
            a, b = re.split("[<>]", e)
            if f"{a}>{b}" not in edges:
                sys.exit(f"tour step uses a missing arrow: {e}")
    return [dict(edges=lit, node=node, text=text) for lit, node, text in content.ARCH_TOUR]


def flow_diagram(name: str) -> str:
    """One flowchart from content.FLOWS[name]: boxes + arrows (straight, down-first or across-first, or the bottom bus).
    A node may end with dict(w=, h=, html=) for a bigger box that holds a list or table."""
    f = content.FLOWS[name]
    W, H, NW, NH = f["w"], f["h"], f["nw"], f["nh"]
    box = {k: (x, y, *(((more[0].get("w", NW), more[0].get("h", NH))) if more else (NW, NH)))
           for k, _, _, x, y, _, *more in f["nodes"]}

    def path(a: str, b: str, bus: bool, across: bool = False) -> tuple[str, float, float, str]:
        (ax, ay, aw, ah), (bx, by, bw, bh) = box[a], box[b]
        if bus:                                                    # an early exit runs along the bottom to the end box
            return f"M{ax + aw / 2},{ay + ah} V{H - 14} H{bx + bw / 2} V{by + bh + 4}", 0, 0, "start"
        top, bottom, left, right = max(ay, by), min(ay + ah, by + bh), max(ax, bx), min(ax + aw, bx + bw)
        if not across and top < bottom and (bx >= ax + aw or bx + bw <= ax):    # side by side: straight across
            y = (top + bottom) / 2
            x1, x2 = (ax + aw, bx - 4) if bx > ax else (ax, bx + bw + 4)
            ly = top - 8 if abs(x2 - x1) < 40 else y - 10      # gap too narrow: label sits above the boxes
            return f"M{x1},{y} L{x2},{y}", (x1 + x2) / 2, ly, "middle"
        if not across and left < right and (by >= ay + ah or by + bh <= ay):    # stacked: straight up or down
            x = (left + right) / 2
            y1, y2 = (ay + ah, by - 4) if by > ay else (ay, by + bh + 4)
            return f"M{x},{y1} L{x},{y2}", x + 10, (y1 + y2) / 2 + 6, "start"
        if by > ay and not across:                                 # down first, then across, then down into the box
            mid = (ay + ah + by) / 2
            return f"M{ax + aw / 2},{ay + ah} V{mid} H{bx + bw / 2} V{by - 4}", (ax + aw / 2 + bx + bw / 2) / 2, mid - 8, "middle"
        x1, x2 = (ax + aw, bx - 4) if bx > ax else (ax, bx + bw + 4)   # across first, then up/down, then across into the box
        mid = (ax + aw + bx) / 2 if bx > ax else (ax + bx + bw) / 2
        d = f"M{x1},{ay + ah / 2} H{mid} V{by + bh / 2} H{x2}"
        if bx < ax:                                                # going left: label on the last stretch, clear of the source box
            return d, (mid + x2) / 2, by + bh / 2 - 10, "middle"
        return d, mid + 8, (ay + ah / 2 + by + bh / 2) / 2, "start"

    marker = lambda i, color: (f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" '
                               f'markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')
    svg = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{marker(f"fh-{name}", "#8a8a92")}{marker(f"fhr-{name}", "#ff2536")}</defs>']
    for a, b, label, *flag in f["edges"]:
        d, lx, ly, anchor = path(a, b, flag == ["bus"], flag == ["across"])
        svg.append(f'<path id="fl-{name}-{a}-{b}" d="{d}" style="marker-end:url(#fh-{name})" data-red="url(#fhr-{name})"/>')
        if label:
            svg.append(f'<text x="{lx}" y="{ly}" text-anchor="{anchor}">{html_escape(label)}</text>')
    svg.append("</svg>")
    boxes = [f'<div class="fnode {shape}{" fbig" if more else ""}" data-f="{k}" style="left:{x}px;top:{y}px;width:{box[k][2]}px;height:{box[k][3]}px">'
             f'<b>{html_escape(t)}</b><span>{html_escape(sub)}</span>{more[0].get("html", "") if more else ""}</div>'
             for k, t, sub, x, y, shape, *more in f["nodes"]]
    return f'<div class="flowmap" data-flow="{name}" style="width:{W}px;height:{H}px">{"".join(svg)}{"".join(boxes)}</div>'


def flow_walks(every: dict, canned_: dict) -> dict:
    """Walks per flowchart: tested cases for "flow" and "vision", the code facts in content.FLOW_WALKS for the rest."""
    walk = lambda label, steps, **more: dict(label=label, steps=[dict(e=e, n=n, c=c, t=t, **({"x": x[0]} if x else {}))   # x = text shown in boxes
                                                                for e, n, c, t, *x in steps], **more)
    out = {k: [walk(label, steps) for label, steps in v] for k, v in content.FLOW_WALKS.items()}
    q = every["Q07"]
    out["rag"].append(walk(f'ตอนลูกค้าถาม Q07', [
        (None, "q", "ok", f'"{q["q"]}"'), ("q-kw", "kw", "hit", "Typhoon แตกคำค้นเป็นคำหัวข้อและชื่อเฉพาะ (มี cache)"),
        ("kw-local|kw-global|kw-naive|q-kws|store-local", "local|global|naive|kws|store", "ok",
         "ค้น 4 ทางพร้อมกันจาก rag-index/: เดินกราฟ · ค้นความสัมพันธ์ · เวกเตอร์ของท่อน · ค้นด้วยคำเดิม"),
        ("local-ctx|global-ctx|naive-ctx|kws-ctx", "ctx", "ok", "รวมผลทั้ง 4 ทางเป็นข้อมูลอ้างอิง เอกสารอันดับต้น: " + " · ".join(q["src"][:3])),
        ("ctx-ans", "ans", "hit", "Typhoon เขียนคำตอบจากข้อมูลอ้างอิง")], sec=q["sec"], answer=q["a"]))
    out["vision"] = []
    for cid, label in (("I01", "สลิปผ่าน"), ("I02", "สลิปยอดขาด"), ("I04", "ใบเสร็จ"), ("I05", "โปสเตอร์หมดเขต")):
        c = every[cid]
        kind = c["vision"].split(",")[0].replace("type=", "")
        steps = [(None, "img", "ok", c["imgPath"].split("/")[-1] + (" · " + c["hint"].split(": ")[1] if c["hint"] else "")),
                 ("img-gate", "gate", "ok", "ไฟล์ PNG ไม่เกิน 5 MB ผ่าน"),
                 ("gate-ocr", "ocr", "ok", "อ่านตัวอักษรในภาพ"), ("ocr-json", "json", "ok", c["vision"][:110]),
                 ("json-type", "type", "hit", f"ชนิด {kind}")]
        if kind == "slip":
            ok = "ผ่านทุกเกณฑ์" in c["a"] or "ผ่านครบ" in c["a"]
            steps += [("type-slip", "slip", "hit", "ตรวจ 5 ข้อด้วยโค้ด", {"slip": "ผ่านครบ 5 ข้อ" if ok else "ไม่ผ่านข้อ 3: ยอดเงินไม่ตรงยอดค้าง"}),
                      ("slip-pass", "pass", "ok", "ผ่าน → รอพนักงานยืนยัน") if ok else ("slip-fail", "fail", "stop", "ยอดไม่ตรง → บอกยอดที่ขาด + ปุ่มคุยกับพนักงาน")]
        else:
            steps += [("type-answer", "answer", "ok", "ส่งตัวเลขในภาพไปให้ answer() ตอบคู่กับข้อมูลร้าน"),
                      ("answer-gout", "gout", "hit", "ตรวจคำตอบก่อนส่ง" + (": ตัวเลขในโปสเตอร์ไม่นับเป็นราคาของร้าน" if kind == "promo_poster" else ": ตัวเลขทุกตัวต้องมีในภาพหรือข้อมูลร้าน")),
                      ("gout-reply", "reply", "ok", "ส่งคำตอบให้ลูกค้า")]
        out["vision"].append(walk(f"{cid} {label}", steps, sec=c["sec"], answer=c["a"]))
    out["vision"].append(walk("ไฟล์ PDF ถูกปฏิเสธ", [                   # chat.vision(): checked before any AI call (code facts, not a test case)
        (None, "img", "ok", "ลูกค้าแนบไฟล์ใบเสร็จ.pdf"),
        ("img-gate", "gate", "stop", "ไม่ใช่ PNG/JPG → หน้าเว็บเตือนก่อนส่ง และ /api/vision ตอบ 415 ซ้ำอีกชั้น"),
        ("gate-xfile", "xfile", "stop", "ตอบทันที ไม่เรียก typhoon-ocr และไม่เสียโควตา AI")],
        answer="รองรับเฉพาะภาพ JPG หรือ PNG ไม่เกิน 5 MB · ส่งถี่เกิน 6 ภาพต่อนาทีก็ถูกปฏิเสธเหมือนกัน (429)"))
    return out


def flow_cases(every: dict, canned_: dict) -> list:
    """The way each example really went through chat.answer(), from the results file (same rules as the playground)."""
    out = []
    for key, label in content.FLOW_CASES:
        c = every.get(key) or dict(canned_[key], q=key, src=[], vision="", hint="", actions=canned_[key].get("actions", []))
        rules, src = c.get("rules", []), c.get("src", [])
        step = lambda e, n, cls, text: dict(e=e, n=n, c=cls, t=text)
        steps = [step(None, "in", "ok", f'ลูกค้าพิมพ์ "{c["q"]}"' + (" + แนบภาพ" if c.get("vision") else ""))]
        if "D-04" in rules:
            steps += [step("in-g1", "g1", "ok", "ผ่าน"), step("g1-g2", "g2", "hit", "พิมพ์รหัสสมาชิก + เบอร์ 4 ตัวท้าย"),
                      step("g2-x2", "x2", "hit", "ตรงกัน → ยืนยันแล้ว จำไว้ในแชตนี้ ไม่ต้องเรียก AI"), step("x2-out", "out", "ok", "ส่งคำตอบ")]
        elif rules and not src:
            steps += [step("in-g1", "g1", "stop", "จับได้ " + " ".join(rules)),
                      step("g1-x1", "x1", "hit", "ตอบข้อความตายตัวจาก replies.md ไม่เรียก AI"), step("x1-out", "out", "ok", "ส่งคำตอบ")]
        else:
            cut = [r for r in rules if r.startswith("G-")]
            seen = c["vision"].split(",")[0].replace("type=", "") if c.get("vision") else ""
            steps += [step("in-g1", "g1", "ok", "ผ่าน"),
                      step("g1-g2", "g2", "hit" if c.get("hint") else "ok",
                           "ยืนยัน FN-" + c["hint"].split("FN-")[1].split(" ")[0] + " แล้ว" if c.get("hint") else "ไม่ได้ถามเรื่องส่วนตัว ไม่ต้องยืนยัน"),
                      step("g2-rag", "rag", "ok", "ค้นเจอ " + " ".join(src[:3])), step("idx-rag", "idx", "ok", "อ่านกราฟและเวกเตอร์"),
                      step("rag-rules", "rules", "hit" if seen else "ok", f"อ่านภาพได้ {seen} → ตรวจสลิป 5 ข้อ" if seen else "ตรวจกฎร้านที่เกี่ยวกับคำถาม"),
                      step("db-rules", "db", "ok", "อ่านข้อมูลร้านและยอดค้าง" if seen else "อ่านข้อมูลร้าน"),
                      step("rules-llm", "llm", "ok", "เขียนคำตอบจากข้อมูลอ้างอิง"), step("ty-llm", "ty", "ok", "เรียก Typhoon")]
            steps += ([step("llm-g6", "g6", "stop", "ตัด " + " ".join(cut)), step("g6-x6", "x6", "hit", "ตอบข้อความปลอดภัย"), step("x6-out", "out", "ok", "ส่งคำตอบ")]
                      if cut else [step("llm-g6", "g6", "ok", "ผ่าน ไม่มีตัวเลข ลิงก์ เวลาที่แต่ง"), step("g6-out", "out", "ok", "ส่งคำตอบ")])
        acts = c.get("actions") or []
        out.append(dict(label=f"{key} {label}" if key in every else label, steps=steps, sec=c["sec"], answer=c["a"], acts=acts))
    return out


def excerpt(specs: list) -> str:
    """Real lines from x-fitness/backend/app: each spec = (file, regex of the first line, line count or None = all matches)."""
    out, last = [], None
    for file, pattern, count in specs:
        lines = (ROOT / "x-fitness/backend/app" / file).read_text(encoding="utf-8").splitlines()
        hits = [i for i, l in enumerate(lines) if re.search(pattern, l)]
        if not hits:
            sys.exit(f"ARCH_CODE: no line matches {pattern!r} in {file}")
        picked = [lines[i] for i in hits] if count is None else lines[hits[0]:hits[0] + count]
        picked = [re.sub(r"\s{2,}#\s.*$", "", l) for l in picked]        # trailing comments: the slide has no room
        head = "    …" if file == last else ("\n" if out else "") + f"# {file} บรรทัด {hits[0] + 1}"   # same file again: a gap, not a new header
        out.append(head + "\n" + "\n".join(picked))
        last = file
    return "\n".join(out)


def cards(group: dict) -> dict:
    return {k: dict(v, tags=[list(t) for t in v["tags"]]) for k, v in group.items()}


def main() -> None:
    docs, (demo, every) = kb_docs(), cases()
    svg, graph_cards = graph()
    reply_cards = replies()
    for c in every.values():         # do/don't rows record only the answer: a fixed guard reply tells which rule fired
        if not c["rules"]:
            c["rules"] = [r["tags"][0][0].split("-ยา")[0].split("-อาหาร")[0] for r in reply_cards.values()
                          if r["code"][:40] and c["a"].startswith(r["code"][:40])][:1]
    tables = db_tables()
    data = dict(line=line_data(every), cards=dict(arch=cards({k: v | ({"code": excerpt(content.ARCH_CODE[k])} if k in content.ARCH_CODE else {}) for k, v in content.ARCH.items()}), rag=cards(content.RAG), tree=cards(content.TREE),
                           kb=kb_cards(docs), graph=graph_cards, replies=reply_cards, rules20=rules20(every), db=db_cards(tables)),
                demo=demo, all=every, tour=tour(), flows={**flow_walks(every, canned()), "flow": flow_cases(every, canned())}, canned=canned(), kb={k: d["title"] for k, d in docs.items()})
    html = (HERE / "shell.html").read_text(encoding="utf-8")
    slides = (HERE / "slides.html").read_text(encoding="utf-8")
    slides = slides.replace(
        'id="qr-web" style="width:260px;height:260px;background:#fff;border-radius:12px;padding:12px"></div>',
        'id="qr-web" style="width:260px;height:260px;background:#fff;border-radius:12px;padding:16px">'
        + (HERE / "qr-web.svg").read_text(encoding="utf-8") + "</div>")
    cut = lambda text, n=95: text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"
    slides = re.sub(r"<!--(Q|A|SEC|IMG):([\w-]+)-->", lambda m: {
        "Q": lambda c: html_escape(c["q"]), "A": lambda c: html_escape(cut(c["a"])), "SEC": lambda c: c["sec"],
        "IMG": lambda c: f'<img src="{c["img"]}" alt="ภาพทดสอบ">'}[m.group(1)](every[m.group(2)]), slides)
    slides = re.sub(r"<!--FLOW:(\w+)-->", lambda m: flow_diagram(m.group(1)), slides)
    slides = (slides.replace("<!--GRAPH-->", svg).replace("<!--ARCH-->", arch_diagram()).replace("<!--INDEXFILES-->", index_table())
              .replace("<!--RETRIEVAL-->", retrieval_table(demo["q"], docs))
              .replace("<!--LINECHAT-->", line_chat(every)).replace("<!--SYSTEMPROMPT-->", html_escape((ROOT / "x-fitness/backend/app/prompts/system.md").read_text(encoding="utf-8")))
              .replace("<!--RULESLIST-->", "".join(f'<div data-pick="rules20" data-key="{k}"><b>{k}</b>{html_escape(c["q"])}</div>'
                                                   for k, c in every.items() if k[0] in "DN"))
              .replace("<!--DBLIST-->", db_list(tables)).replace("<!--DBSIZE-->", f"{DB_FILE.stat().st_size // 1024} KB")
              .replace("<!--KBLIST-->", "".join(f'<div data-pick="kb" data-key="{k}"><b>{k}</b>{html_escape(d["title"])}</div>'
                                                for k, d in docs.items()))
              .replace("<!--REPLYLIST-->", "".join(f'<div data-pick="replies" data-key="{k}"><b>{html_escape(r["tags"][0][0])}</b>{r["what"]}</div>'
                                                   for k, r in reply_cards.items())))
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")   # keep "</script>" out of the script
    html = (html.replace("/*PLAYCSS*/", (HERE / "play.css").read_text(encoding="utf-8"))
                .replace("/*PLAYJS*/", (HERE / "play.js").read_text(encoding="utf-8")))
    html = html.replace("<!--SLIDES-->", slides).replace("/*DATA*/null", payload)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)} · {OUT.stat().st_size / 1e6:.1f} MB · {slides.count('<section')} หน้า · "
          + " · ".join(f"{k} {len(v)}" for k, v in data["demo"].items()))


if __name__ == "__main__":
    main()
