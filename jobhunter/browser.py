import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright
from playwright.sync_api import Error as PlaywrightError

PROFILE_DIR = Path("data/browser_profile")
COOKIES_FILE = Path("data/browser_cookies.json")


def read_cookies(path: Path = COOKIES_FILE) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def write_cookies(cookies: list[dict], path: Path = COOKIES_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")


def restore_session(context, path: Path = COOKIES_FILE) -> None:
    """Devolve ao navegador os cookies da última vez (inclusive os de sessão)."""
    cookies = read_cookies(path)
    if not cookies:
        return
    try:
        context.add_cookies(cookies)
    except PlaywrightError:
        pass  # cookie inválido: segue sem restaurar


def save_session(context, path: Path = COOKIES_FILE) -> None:
    try:
        cookies = context.storage_state()["cookies"]
    except PlaywrightError:
        return  # o navegador já foi fechado à mão: não há o que salvar
    write_cookies(cookies, path)


@contextmanager
def persistent_browser() -> Iterator[BrowserContext]:
    """Chromium visível com perfil salvo em disco; o login também é guardado ao sair."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
        )
        restore_session(context)
        try:
            yield context
        finally:
            save_session(context)
            context.close()