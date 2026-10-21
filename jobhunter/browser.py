from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright

PROFILE_DIR = Path("data/browser_profile")


@contextmanager
def persistent_browser() -> Iterator[BrowserContext]:
    """Chromium visível com perfil salvo em disco: o login fica guardado entre execuções."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
        )
        try:
            yield context
        finally:
            context.close()