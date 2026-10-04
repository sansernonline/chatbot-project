"""Render docs/figures/src/*.html to docs/figures/*.png (2x for print). Run: python docs/tools/render_figures.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

SRC = Path(__file__).resolve().parents[1] / "figures" / "src"
with sync_playwright() as p:
    browser = p.chromium.launch()
    for html in sorted(SRC.glob("*.html")):
        page = browser.new_page(viewport={"width": 1600, "height": 840}, device_scale_factor=2)
        page.goto(html.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        out = SRC.parent / f"{html.stem}.png"
        page.screenshot(path=str(out), full_page=True)
        print("wrote", out.name)
    browser.close()
