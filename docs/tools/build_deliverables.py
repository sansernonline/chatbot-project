"""Build the course deliverables from docs/08_project-report.md (the source of truth).

    python docs/tools/build_deliverables.py

1. refresh section 5 of the markdown with the latest Playwright results (qa/results/x-fitness-ui-results.json)
2. markdown → docs/deliverables/XFitness-Chatbot_Project-Report_v1.0.docx (+ .pdf via Word)
3. slides  → docs/deliverables/XFitness-Chatbot_Presentation_v1.0.pptx (+ .pdf via PowerPoint)
PDF export needs Microsoft Word/PowerPoint (Windows). Edit the markdown or the SLIDES list, then run again.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
ROOT = DOCS.parent
sys.path.insert(0, str(Path(__file__).parent))
from brandkit import BrandDoc, keep_with_next, use_brand  # noqa: E402
from brandkit_pptx import BrandDeck  # noqa: E402

SOURCE = DOCS / "08_project-report.md"
RESULTS = ROOT / "qa" / "results" / "x-fitness-ui-results.json"
SHOTS = ROOT / "qa" / "results" / "screenshots"
OUT = DOCS / "deliverables"
NAME = "XFitness-Chatbot_{}_v1.0"
use_brand(brand="E10613", brand_2="FF2536", brand_deep="8E0A12", brand_tint="FDECEC", brand_tint_2="FEF6F6")


# -- 1 · results tables into the markdown --------------------------------------------------------
def results_markdown() -> str:
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    cell = lambda s, n=170: re.sub(r"\s+", " ", str(s)).replace("|", "/").strip()[:n]
    total = [x for rows in r.values() for x in rows]
    ok = sum(x["pass"] for x in total)
    lines = [f"ผลรวม **ผ่าน {ok}/{len(total)} กรณี** · เวลาตอบเฉลี่ย {sum(x['seconds'] for x in total) / len(total):.1f} วินาที "
             f"(คำถาม {sum(x['pass'] for x in r['questions'])}/{len(r['questions'])} · ภาพ {sum(x['pass'] for x in r['images'])}/{len(r['images'])} · "
             f"ความปลอดภัย {sum(x['pass'] for x in r['safety'])}/{len(r['safety'])} · ต้องทำ/ห้ามทำ {sum(x['pass'] for x in r.get('rules', []))}/{len(r.get('rules', []))})", ""]
    for key, title, col in [("questions", "5.1 ชุดคำถามทดสอบ 10 ข้อ", "ผลตอบ"), ("images", "5.2 ชุดภาพทดสอบ 5 ภาพ", "ผลวิเคราะห์"),
                            ("safety", "5.3 ชุดทดสอบความปลอดภัย 5 กรณี", "ผลวิเคราะห์")]:
        lines += [f"## {title}", "", f"| รหัส | ข้อมูลเข้า | {col} | ผ่าน/ไม่ผ่าน | เวลา (วินาที) |", "|---|---|---|---|---|"]
        for x in r[key]:
            inp = (f"ภาพ {x['image']} · " if x.get("image") else "") + x["message"] + (f" · สมาชิก {x['member']}" if x.get("member") else "")
            got = x["answer"]
            if key == "images" and x.get("vision"):
                v = {k: x["vision"].get(k) for k in ("type", "amount", "total", "body_fat_pct", "promo_code") if x["vision"].get(k) is not None}
                got = "อ่านภาพ " + ", ".join(f"{k}={val}" for k, val in v.items()) + " — " + got
            if key == "safety":
                got = (f"guard {', '.join(x['rules'])} — " if x["rules"] else "LLM ปฏิเสธเอง — ") + got
            lines.append(f"| {x['id']} | {cell(inp, 80)} | {cell(got)} | {'ผ่าน' if x['pass'] else 'ไม่ผ่าน'} | {x['seconds']} |")
        lines.append("")
    return "\n".join(lines)


def refresh_source() -> str:
    md = SOURCE.read_text(encoding="utf-8")
    md = re.sub(r"(<!-- RESULTS:START -->).*?(<!-- RESULTS:END -->)", lambda m: f"{m.group(1)}\n{results_markdown()}\n{m.group(2)}", md, flags=re.S)
    SOURCE.write_text(md, encoding="utf-8")
    return md


# -- 2 · markdown → Word ------------------------------------------------------------------------
def inline(text: str) -> list[tuple[str, dict]]:
    """**bold** and `code` → brandkit rich() parts."""
    parts = []
    for piece in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if piece.startswith("**"):
            parts.append((piece[2:-2], {"bold": True, "color": "text"}))
        elif piece.startswith("`"):
            parts.append((piece[1:-1], {"mono": True, "color": "brand_deep"}))
        elif piece:
            parts.append((piece, {"color": "text_body"}))
    return parts


def widths(rows: list[list[str]], total=9360) -> list[int]:
    """Column widths from each column's longest text (compressed), so ids and names never wrap mid-word."""
    longest = [max(min(len(r[i]), 120) for r in rows) for i in range(len(rows[0]))]
    raw = [max(n, 14) ** 0.7 for n in longest]          # compress the range: short columns (ids, names) keep room
    raw[0] *= 1.35                                       # first column holds names/labels: Thai names must not break
    w = [int(total * n / sum(raw)) for n in raw]
    w[-1] += total - sum(w)
    return w


def before_table(lines: list[str], i: int) -> bool:
    nxt = next((l for l in lines[i + 1:] if l.strip()), "")
    return nxt.startswith("|")


def build_docx(md: str) -> Path:
    front, body = re.match(r"---\n(.*?)\n---\n(.*)", md, re.S).groups()
    meta = dict(line.split(": ", 1) for line in front.splitlines())
    doc = BrandDoc()
    doc.cover(meta["title"].split(" — ")[0], subtitle=meta["title"].split(" — ")[1],
              meta=f"{meta['subtitle']}  •  {meta['meta']}",
              note="ผู้พัฒนา: 68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ")
    doc.toc()
    lines, i, fig = body.splitlines(), 0, 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("# "):
            doc.h1(line[2:])
        elif line.startswith("## "):
            doc.h2(line[3:])
        elif line.startswith("### "):
            doc.h3(line[4:])
        elif line.startswith("> "):
            t = doc.callout("note", "หมายเหตุ", re.sub(r"[*`]", "", line[2:]))
            if before_table(lines, i):
                for par in t.rows[0].cells[0].paragraphs:
                    keep_with_next(par)
        elif m := re.match(r"!\[(.*?)\]\((.*?)\)", line):
            fig += 1
            doc.figure(str(DOCS / m.group(2)), m.group(1), width_cm=17, number=fig)
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| :]+\|$", lines[i]):
                    block.append([c.strip().replace("`", "") for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, rows = block[0], block[1:]
            rows = [[re.sub(r"\*\*", "", c) for c in r] for r in rows]
            t = doc.table(head, rows, widths=widths(block), zebra=len(rows) > 6, first_col_bold=True)
            if len(rows) <= 8:                                  # short tables stay on one page with their heading
                for row in t.rows[:-1]:
                    for c in row.cells:
                        for par in c.paragraphs:
                            keep_with_next(par)
            continue
        elif re.match(r"\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]).replace("`", ""))
                i += 1
            doc.bullets(items, style="List Number")
            continue
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:].replace("`", "").replace("**", ""))
                i += 1
            doc.bullets(items)
            continue
        else:
            par = doc.rich(inline(line))
            if before_table(lines, i):                      # an intro line stays on the page of its table
                keep_with_next(par)
        i += 1
    path = OUT / f"{NAME.format('Project-Report')}.docx"
    doc.save(str(path))
    return path


# -- 3 · slides (headline = the conclusion of the slide) ------------------------------------------
def build_pptx(md: str) -> Path:
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    ok = lambda k: f"{sum(x['pass'] for x in r[k])}/{len(r[k])}"
    avg = lambda k: f"{sum(x['seconds'] for x in r[k]) / len(r[k]):.1f} วินาที"
    shot = lambda cid: next(p for p in SHOTS.glob(f"*-{cid}.png"))
    d = BrandDeck()
    d.title_slide("X Fitness Chatbot", "ผู้ช่วยตอบลูกค้าสตูดิโอฟิตเนส — ตอบจากข้อมูลจริง และไม่ถูกหลอก",
                  "68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ · 06048308 Intelligent Chatbot Development · ตุลาคม 2569")
    d.table_slide("ผู้พัฒนา 2 คน: ฝั่งธุรกิจและข้อมูล · ฝั่งระบบและการทดสอบ", ["ใคร", "ทำอะไร", "ได้อะไร"], [
        ["เบญจมาภรณ์ เจียนเกาะ\n68076040", "วิเคราะห์ธุรกิจ · เขียนคลังความรู้ · กฎต้องทำ/ห้ามทำ · ออกแบบชุดทดสอบ · คลิป", "คลังความรู้ 9 เอกสาร · กฎ 20 ข้อ · test case 40 กรณี"],
        ["สรรเสริญ มากเจริญ\n68076065", "สถาปัตยกรรม · backend · LightRAG + Typhoon · guardrail · LINE OA · deploy · ทดสอบอัตโนมัติ", "ระบบบนเว็บและ LINE · ผลทดสอบอัตโนมัติ"],
        ["ร่วมกัน", "ทดสอบ ตรวจคำตอบ ปรับปรุง · อัดคลิปสาธิต", "บอทผ่าน 40/40 ผ่านหน้าเว็บจริง"],
    ], col_widths=[2, 5, 4], subtitle="ร่างการแบ่งงาน — แก้ให้ตรงกับที่ทำจริงก่อนนำเสนอ")
    d.section("ธุรกิจ: เอ็กซ์ ฟิตเนส ศรีราชา", kicker="ส่วนที่ 1")
    d.bullets_slide("สตูดิโอเล็กที่ลูกค้าถามเรื่องเดิมซ้ำทุกวัน รวมถึงนอกเวลา", [
        "สตูดิโอฟิตเนสสาขาเดียว ใจกลางศรีราชา เปิดปี 2567 (ข้อมูลจำลอง)",
        "เปิด จ.–ศ. 06:00–22:00 · ส.–อา. 08:00–20:00",
        "ถามซ้ำ: ราคา · ตารางคลาส · การจอง · นโยบายคืนเงิน",
        "ส่งภาพมาให้ตรวจ: สลิป · ใบเสร็จ · ผลวัดร่างกาย · โปสเตอร์",
        "บอทต้องตอบตรงข้อมูลร้าน และไม่ตัดสินใจแทนร้าน",
    ])
    d.table_slide("ลูกค้า 3 กลุ่ม ถามคนละเรื่อง", ["กลุ่ม", "ลักษณะ", "มักถามเรื่อง"], [
        ["คนทำงาน 22–45 ปี", "ออฟฟิศ · นิคมอุตสาหกรรม", "ราคา · คลาสเย็น · ส่งสลิป"],
        ["นักเรียนนักศึกษา", "งบจำกัด แพ็กเกจ 790 บาท", "คลาสที่เข้าได้ · ผู้ปกครองเซ็น"],
        ["มือใหม่", "อยากได้คลาสกลุ่มและโค้ช", "คลาสเริ่มต้น · ทดลองฟรี · PT"],
    ], col_widths=[3, 4, 4])
    d.kpi_slide("ข้อมูลที่บอทต้องตอบให้ถูก มีมากกว่า 30 รายการ", [
        ("5", "แพ็กเกจสมาชิก\n150–9,900 บาท"), ("8", "คลาสกลุ่ม\n29 รอบ/สัปดาห์"), ("6", "เทรนเนอร์\nPT 4 แพ็กเกจ"), ("7", "สินค้าในร้าน\n+ บริการเสริม 4")],
        subtitle="ทั้งหมดอยู่ในคลังความรู้ 9 เอกสาร (KB-01 ถึง KB-09)")
    d.bullets_slide("นโยบายสำคัญ: บอทบอกได้ แต่อนุมัติเองไม่ได้", [
        "คืนเงิน · ส่วนลดพิเศษ ต้องให้ผู้จัดการอนุมัติ",
        "สลิปผ่าน 5 ข้อ = \"รอพนักงานยืนยัน\" ไม่ใช่ \"ชำระแล้ว\"",
        "ข้อมูลสมาชิกบอกเฉพาะเจ้าของ หลังยืนยันตัวตน",
        "โปรที่หมดเขตใช้ไม่ได้ แม้มีโปสเตอร์",
        "ไม่วินิจฉัยโรค ไม่แนะนำยา ฉุกเฉินโทร 1669",
    ])
    d.section("องค์ประกอบของระบบ", kicker="ส่วนที่ 2")
    d.image_slide("แอปเดียวรับทุกช่องทาง ความฉลาดเรียกจาก Typhoon", str(DOCS / "figures" / "architecture.png"),
                  caption="หน้าเว็บ + LINE OA → FastAPI บน Render → LightRAG + Typhoon · ข้อมูลร้านและดัชนี deploy มากับโค้ด")
    d.bullets_slide("ทุกคำตอบผ่านด่านกันความเสี่ยง ทั้งก่อนและหลัง AI", [
        "Guardrail ขาเข้า: หลอกเปลี่ยนคำสั่ง · ยา · นอกเรื่อง → ปฏิเสธทันที",
        "LightRAG + ค้นด้วยคำ: ดึงเอกสารที่เกี่ยวกับคำถาม",
        "กฎร้าน + ตรวจสลิปด้วยโค้ด: ไม่ให้ AI ตัดสินเรื่องเงิน",
        "Typhoon ตอบภาษาไทย พร้อมแหล่งอ้างอิง KB-xx",
        "Guardrail ขาออก: ราคาแต่ง · \"ชำระสำเร็จ\" · ข้อมูลคนอื่น",
    ])
    d.table_slide("เลือกเทคโนโลยีจากข้อจำกัดจริง", ["ส่วน", "เลือก", "เพราะ"], [
        ["LLM + อ่านภาพ", "Typhoon v2.5 + typhoon-ocr", "ภาษาไทยดี · key เดียวใช้ทั้งคู่"],
        ["ค้นความรู้", "LightRAG + hash embedding", "RAM ~250 MB · ค้นถูก 12/12"],
        ["Backend", "FastAPI + SQLite", "แอปเดียว ไม่ต้องตั้งฐานข้อมูลแยก"],
        ["Deploy", "Render แผนฟรี", "ดัชนีสร้างไว้ก่อน commit มากับโค้ด"],
    ], col_widths=[2, 3, 4])
    d.section("ผลการทดสอบ", kicker="ส่วนที่ 3")
    d.kpi_slide("ผ่านทุกกรณีเมื่อทดสอบผ่านหน้าเว็บจริงด้วย Playwright", [
        (ok("questions"), f"คำถามทดสอบ\n{avg('questions')}"), (ok("images"), f"ภาพทดสอบ\n{avg('images')}"),
        (ok("safety"), f"ความปลอดภัย\n{avg('safety')}"), (ok("rules"), f"กฎต้องทำ/ห้ามทำ\n{avg('rules')}")],
        subtitle="ชุดทดสอบ qa/x-fitness-test-cases.md · ผลเต็มและภาพหน้าจอ qa/results/")
    d.image_slide("สลิปโอนขาด: บอกยอดที่ขาด แล้วส่งต่อพนักงาน", str(shot("I02")),
                  caption="สมาชิก FN-10007 ค้าง 1,290 บาท โอน 690 บาท → ขาด 600 บาท · ไม่ยืนยันการชำระเอง")
    d.image_slide("อ้างเป็นผู้จัดการขอลด 50%: ปฏิเสธก่อนถึง AI", str(shot("S02")),
                  caption="guard ขาเข้า N-07 N-08 ทำงาน · ใช้เวลาไม่ถึง 1 วินาที")
    d.table_slide("ทดสอบแล้วเจอปัญหาจริง และแก้ได้ทุกข้อ", ["พบ", "แก้"], [
        ["แต่งราคา \"2,500 บาท\"", "guard ตรวจจำนวนเงินกับคลังความรู้"],
        ["อ่านภาพไม่ได้ 3/5", "แยก OCR → LLM จัด JSON + ลองซ้ำ"],
        ["\"นักเรียนเล่น Ride\" ตอบว่าได้", "ค้นแบบ hybrid + กฎร้านในโค้ด"],
        ["แต่งว่า \"ส่งถึงบ้านได้\"", "กฎร้าน: ไม่มีจัดส่ง/ผ่อน/ฝากเด็ก"],
        ["เว็บส่งคำว่า \"แอดมิน\" ให้พนักงาน", "ส่งต่อเฉพาะเมื่อขอคุยจริง (พบโดย Playwright)"],
    ], col_widths=[4, 5], subtitle="รายการเต็ม 9 ข้อ อยู่ในเอกสารการพัฒนา หัวข้อ 6")
    d.quote_slide("เรื่องสำคัญตรวจด้วยโค้ด ไม่ปล่อยให้ AI ตัดสินเอง — บอทจึงตอบจากข้อมูลจริงและไม่ถูกหลอก",
                  "X Fitness Chatbot · ขอบคุณครับ/ค่ะ")
    path = OUT / f"{NAME.format('Presentation')}.pptx"
    d.save(str(path))
    return path


# -- 4 · PDF through Office ---------------------------------------------------------------------
def to_pdf(path: Path) -> Path:
    pdf = path.with_suffix(".pdf")
    if path.suffix == ".docx":
        ps = (f"$w=New-Object -ComObject Word.Application; $d=$w.Documents.Open('{path}'); $d.Fields.Update() | Out-Null; "
              f"$d.TablesOfContents | ForEach-Object {{ $_.Update() }}; $d.Save(); $d.SaveAs2('{pdf}', 17); $d.Close(); $w.Quit()")
    else:
        ps = (f"$p=New-Object -ComObject PowerPoint.Application; $d=$p.Presentations.Open('{path}', $true, $false, $false); "
              f"$d.SaveAs('{pdf}', 32); $d.Close(); $p.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return pdf


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    md = refresh_source()
    for built in (build_docx(md), build_pptx(md)):
        print("wrote", built.relative_to(ROOT), "→", to_pdf(built).name)
