"""Build the 10-minute demo deck as one HTML file that opens offline.

    python docs/deck/build.py

Reads slides.html + shell.html + content.py, takes the 20 demo cases (10 questions, 5 images, 5 safety)
from qa/report/results/x-fitness-ui-results.md, embeds the test images and screenshots, and writes
docs/XFitness-Chatbot_Presentation-Deck.html. Needs Pillow."""
import base64, io, json, math, re, sys
from html import escape as html_escape, unescape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "qa/report/results/x-fitness-ui-results.md"
IMAGES = ROOT / "x-fitness/qa"
OUT = ROOT / "docs/XFitness-Chatbot_Presentation-Deck.html"
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
        shot = re.search(r"\(screenshots/([^)]+)\)", line)
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


def kb_cards(docs: dict) -> dict:
    return {k: dict(path=f"x-fitness/data/knowledge-base/{d['file']}", tags=[[k, "red"], [d["size"], ""]],
                    what=html_escape(d["title"]), code=d["excerpt"]) for k, d in docs.items()}


def graph() -> tuple[str, dict]:
    """The centre entity and its first 12 neighbours (all weights are 1.0) from the real graphml → (svg, cards)."""
    g = (RAG_INDEX / "graph_chunk_entity_relation.graphml").read_text(encoding="utf-8")
    fields = lambda body: {k: unescape(v) for k, v in re.findall(r'<data key="(d\d+)">(.*?)</data>', body, re.S)}
    nodes = {unescape(i): fields(b) for i, b in re.findall(r'<node id="(.*?)">(.*?)</node>', g, re.S)}
    c, edges = content.GRAPH_CENTER, []
    for src, dst, body in re.findall(r'<edge source="(.*?)" target="(.*?)">(.*?)</edge>', g, re.S):
        src, dst = unescape(src), unescape(dst)
        if c in (src, dst):
            d = fields(body)
            edges.append((float(d.get("d7", 0)), dst if src == c else src, d))
    edges = sorted(edges, key=lambda e: -e[0])[:12]
    first = lambda s: s.split("<SEP>")[0]
    node = lambda n: nodes.get(n, {})
    cards = {"c": dict(path=f'node "{c}"', tags=[[node(c).get("d1", ""), "blue"], [f"แสดง {len(edges)} เส้น", ""]],
                       what=html_escape(first(node(c).get("d2", ""))),
                       code=f'<node id="{c}">\n  type: {node(c).get("d1")}\n  source_id: {node(c).get("d3", "")}')}
    W, H, R = 900, 600, 235
    pts = []
    for n, (_, name, d) in enumerate(edges):
        a = 2 * math.pi * n / len(edges) - math.pi / 2
        pts.append((W / 2 + R * 1.5 * math.cos(a), H / 2 + R * math.sin(a), name))
        cards[f"n{n}"] = dict(path=f'edge "{c}" — "{name}"', tags=[[d.get("d9", ""), "red"], [first(d.get("d10", "")), ""]],
                              what=html_escape(d.get("d8", "")),
                              code=f'node "{name}" ({node(name).get("d1", "")})\n' + first(node(name).get("d2", ""))[:300])
    label = lambda t: html_escape(t if len(t) <= 14 else t[:13] + "…")
    svg = [f'<svg class="graph" viewBox="0 0 {W} {H}" width="100%" height="100%">']
    svg += [f'<line x1="{W / 2}" y1="{H / 2}" x2="{x:.0f}" y2="{y:.0f}" pathLength="1" style="--i:{n}"/>' for n, (x, y, _) in enumerate(pts)]
    svg += [f'<g data-pick="graph" data-key="n{n}" style="--i:{n}"><circle cx="{x:.0f}" cy="{y:.0f}" r="30"/>'
            f'<text x="{x:.0f}" y="{y + 52:.0f}" text-anchor="middle">{label(name)}</text></g>' for n, (x, y, name) in enumerate(pts)]
    svg.append(f'<g data-pick="graph" data-key="c"><circle cx="{W / 2}" cy="{H / 2}" r="62" style="stroke:#ff2536"/>'
               f'<text x="{W / 2}" y="{H / 2 + 6}" text-anchor="middle" style="font-weight:700;font-size:18px">{html_escape(c)}</text></g></svg>')
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

    marker = lambda i, color: (f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" '
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
    """One flowchart from content.FLOWS[name]: boxes + arrows (straight, down-first or across-first, or the bottom bus)."""
    f = content.FLOWS[name]
    W, H, NW, NH = f["w"], f["h"], f["nw"], f["nh"]
    pos = {k: (x, y) for k, _, _, x, y, _ in f["nodes"]}

    def path(a: str, b: str, bus: bool, across: bool = False) -> tuple[str, float, float, str]:
        (ax, ay), (bx, by) = pos[a], pos[b]
        if bus:                                                    # an early exit runs along the bottom to the end box
            return f"M{ax + NW / 2},{ay + NH} V{H - 14} H{bx + NW / 2} V{by + NH + 4}", 0, 0, "start"
        if ay == by:
            x1, x2 = (ax + NW, bx - 4) if bx > ax else (ax, bx + NW + 4)
            ly = ay - 8 if abs(x2 - x1) < 40 else ay + NH / 2 - 10   # gap too narrow: label sits above the boxes
            return f"M{x1},{ay + NH / 2} L{x2},{by + NH / 2}", (x1 + x2) / 2, ly, "middle"
        if ax == bx:
            y1, y2 = (ay + NH, by - 4) if by > ay else (ay, by + NH + 4)
            return f"M{ax + NW / 2},{y1} L{bx + NW / 2},{y2}", ax + NW / 2 + 10, (y1 + y2) / 2 + 6, "start"
        if by > ay and not across:                                 # down first, then across, then down into the box
            mid = (ay + NH + by) / 2
            return f"M{ax + NW / 2},{ay + NH} V{mid} H{bx + NW / 2} V{by - 4}", (ax + bx + NW) / 2, mid - 8, "middle"
        mid = (ax + NW + bx) / 2 if bx > ax else (ax + bx + NW) / 2   # across first, then up/down, then across into the box
        x1, x2 = (ax + NW, bx - 4) if bx > ax else (ax, bx + NW + 4)
        return f"M{x1},{ay + NH / 2} H{mid} V{by + NH / 2} H{x2}", mid + 8, (ay + by + NH) / 2, "start"

    marker = lambda i, color: (f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" '
                               f'markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')
    svg = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{marker(f"fh-{name}", "#8a8a92")}{marker(f"fhr-{name}", "#ff2536")}</defs>']
    for a, b, label, *flag in f["edges"]:
        d, lx, ly, anchor = path(a, b, flag == ["bus"], flag == ["across"])
        svg.append(f'<path id="fl-{name}-{a}-{b}" d="{d}" style="marker-end:url(#fh-{name})" data-red="url(#fhr-{name})"/>')
        if label:
            svg.append(f'<text x="{lx}" y="{ly}" text-anchor="{anchor}">{html_escape(label)}</text>')
    svg.append("</svg>")
    boxes = [f'<div class="fnode {shape}" data-f="{k}" style="left:{x}px;top:{y}px;width:{NW}px;height:{NH}px">'
             f'<b>{html_escape(t)}</b><span>{html_escape(sub)}</span></div>' for k, t, sub, x, y, shape in f["nodes"]]
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
                 ("img-ocr", "ocr", "ok", "อ่านตัวอักษรในภาพ"), ("ocr-json", "json", "ok", c["vision"][:110]),
                 ("json-type", "type", "hit", f"ชนิด {kind}")]
        if kind == "slip":
            ok = "ผ่านทุกเกณฑ์" in c["a"] or "ผ่านครบ" in c["a"]
            steps += [("type-slip", "slip", "hit", "ตรวจ 5 ข้อด้วยโค้ด", {"slip": "ผ่านครบ 5 ข้อ" if ok else "ไม่ผ่านข้อ 3: ยอดเงินไม่ตรงยอดค้าง"}),
                      ("slip-pass", "pass", "ok", "ผ่าน → รอพนักงานยืนยัน") if ok else ("slip-fail", "fail", "stop", "ยอดไม่ตรง → บอกยอดที่ขาด + ปุ่มคุยกับพนักงาน")]
        else:
            steps += [("type-other", "other", "ok", "ตอบจากตัวเลขในภาพและข้อมูลร้าน")]
        out["vision"].append(walk(f"{cid} {label}", steps, sec=c["sec"], answer=c["a"]))
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
    data = dict(line=line_data(every), cards=dict(arch=cards({k: v | ({"code": excerpt(content.ARCH_CODE[k])} if k in content.ARCH_CODE else {}) for k, v in content.ARCH.items()}), rag=cards(content.RAG), tree=cards(content.TREE),
                           kb=kb_cards(docs), graph=graph_cards, replies=reply_cards, rules20=rules20(every)),
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
