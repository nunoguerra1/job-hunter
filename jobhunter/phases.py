import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError

from jobhunter.browser import persistent_browser
from jobhunter.forms import capture_text
from jobhunter.profile import load_profile
from jobhunter.progress import LINKS_JS, URL, ensure_applications_page, hosts_from_links
from jobhunter.snap import redact
from jobhunter.storage import JobStore

DEBUG_DIR = Path("data/pages")
MAX_DEBUG_FILES = 2
_COUNT = re.compile(r"candidat[oa]s?\b", re.IGNORECASE)
_NUMBER = re.compile(r"^\d{1,2}$")


def parse_phases(text: str) -> list[str]:
    """Nomes das fases, na ordem. Cada fase é: número, nome e uma linha de 'pessoas candidatas'."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    phases: list[str] = []
    for index in range(len(lines) - 2):
        if not _NUMBER.match(lines[index]) or int(lines[index]) != len(phases) + 1:
            continue
        if _COUNT.search(lines[index + 2]):
            phases.append(lines[index + 1])
    return phases


def current_and_next(current: int | None, names: list[str]) -> tuple[str, str]:
    """Fase atual e próxima, assumindo que o numerador de 'n/m' é o número da fase atual."""
    if current is None or not names:
        return "", ""
    here = names[current - 1] if 1 <= current <= len(names) else ""
    ahead = names[current] if 0 <= current < len(names) else ""
    return here, ahead


def wait_for_phases(page, tries: int = 8, pause_ms: int = 1000) -> tuple[list[str], str]:
    """A Gupy monta a lista de fases no navegador: espera aparecer antes de desistir."""
    text = ""
    for _ in range(tries):
        text = capture_text(page, limit=100_000)["text"]
        names = parse_phases(text)
        if names:
            return names, text
        page.wait_for_timeout(pause_ms)
    return [], text


def where(page) -> str:
    parts = urlsplit(page.url)
    return f"{parts.hostname}{parts.path}"  # sem parâmetros, que podem carregar tokens


def save_debug(
    application_id: str, text: str, person_names: list[str], folder: Path = DEBUG_DIR
) -> Path:
    """Guarda o texto da página, com máscara de dados pessoais, para eu ver o formato real."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"fases_{application_id}.txt"
    path.write_text(redact(text, person_names), encoding="utf-8")
    return path


def read_phases(page, store: JobStore, person_names: list[str], pause: float = 1.0) -> int:
    hosts = hosts_from_links(page.evaluate(LINKS_JS))  # aba "Em andamento", que abre primeiro
    rows = [
        row
        for row in store.gupy_applications()
        if row["tab"] == "Em andamento" and row["application_id"] in hosts
    ]
    read = 0
    saved_debug = 0
    for row in rows:
        application_id = row["application_id"]
        url = f"https://{hosts[application_id]}/candidates/applications/{application_id}"
        company = row["company"][:28]
        try:
            page.goto(url, wait_until="domcontentloaded")
            names, text = wait_for_phases(page)
        except PlaywrightError as error:
            print(f"  não consegui ler #{application_id} ({type(error).__name__})")
            continue
        if not names:
            hint = ""
            if saved_debug < MAX_DEBUG_FILES:
                hint = f"; texto salvo em {save_debug(application_id, text, person_names)}"
                saved_debug += 1
            print(
                f"  {company}: nenhuma fase reconhecida "
                f"(parou em {where(page)}, {len(text)} caracteres{hint})"
            )
            continue
        store.save_gupy_phases(application_id, names)
        here, ahead = current_and_next(row["current"], names)
        note = "" if row["total"] in (None, len(names)) else f" (a Gupy diz {row['total']})"
        stage = f"{row['current']}/{row['total']}"
        print(f"  {company} | {stage} | agora: {here or '-'} | próxima: {ahead or '-'}{note}")
        read += 1
        time.sleep(pause)
    return read


def main() -> None:
    store = JobStore()
    if not store.gupy_applications():
        print("Rode antes: python -m jobhunter.progress")
        return
    try:
        person_names = load_profile().name.split()
    except FileNotFoundError:
        person_names = []
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded")
        except PlaywrightError:
            pass  # outra navegação já estava em andamento
        if not ensure_applications_page(page):
            print("Ainda não consegui abrir 'Minhas candidaturas'. Rode de novo depois de logar.")
            return
        page.wait_for_timeout(2500)
        read = read_phases(page, store, person_names)
    print(f"\n{read} candidaturas com as fases lidas. Rode: python -m jobhunter.sync")


if __name__ == "__main__":
    main()