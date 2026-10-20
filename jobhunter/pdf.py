from pathlib import Path

from playwright.sync_api import sync_playwright


def html_to_pdf(html: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=str(path), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()