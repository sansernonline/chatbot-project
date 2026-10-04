"""Render rich-menu.html -> rich-menu.png (2500x1686) and rich-menu.jpg, the size LINE accepts."""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2500, "height": 1686})
    page.goto((HERE / "rich-menu.html").as_uri(), wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.screenshot(path=HERE / "rich-menu.png")
    page.screenshot(path=HERE / "rich-menu.jpg", type="jpeg", quality=90)
    browser.close()

for name in ("rich-menu.png", "rich-menu.jpg"):
    print(name, round((HERE / name).stat().st_size / 1024), "KB (LINE limit 1024 KB)")
