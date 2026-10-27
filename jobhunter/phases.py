import re
import time

from playwright.sync_api import Error as PlaywrightError

from jobhunter.browser import persistent_browser
from jobhunter.forms import capture_text
from jobhunter.progress import LINKS_JS, URL, ensure_applications_page, hosts_from_links
from jobhunter.storage import JobStore

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


def read_phases(page, store: JobStore, pause: float = 1.0) -> int:
    hosts = hosts_from_links(page.evaluate(LINKS_JS))  # aba "Em andamento", que abre primeiro
    rows = [
        row
        for row in store.gupy_applications()
        if row["tab"] == "Em andamento" and row["application_id"] in hosts
    ]
    read = 0
    for row in rows:
        application_id = row["application_id"]
        url = f"https://{hosts[application_id]}/candidates/applications/{application_id}"
        try:
            page.goto(url, wait_until="domcontentloaded")
            text = capture_text(page, limit=100_000)["text"]
        except PlaywrightError as error:
            print(f"  não consegui ler #{application_id} ({type(error).__name__})")
            continue
        names = parse_phases(text)
        company = row["company"][:28]
        if not names:
            print(f"  {company}: nenhuma fase reconhecida")
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
        read = read_phases(page, store)
    print(f"\n{read} candidaturas com as fases lidas. Rode: python -m jobhunter.sync")


if __name__ == "__main__":
    main()