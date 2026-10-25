import re
import sys
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from jobhunter.browser import persistent_browser
from jobhunter.filters import normalize
from jobhunter.forms import capture_text
from jobhunter.models import Job
from jobhunter.review import APPLIED, APPROVED, AWAITING
from jobhunter.storage import JobStore

URL = "https://portal.gupy.io/my/applications"
TABS = ["Em andamento", "Em banco de talentos", "Finalizadas"]
TALENT_POOL = "Em banco de talentos"
ENGAGED = {AWAITING, APPROVED, APPLIED}
LINKS_JS = """
() => [...document.querySelectorAll('a[href*="/candidates/applications/"]')].map(a => a.href)
"""

_ID = re.compile(r"^Ver andamento da candidatura\s*(\d+)$")
_FOOTER = re.compile(r"^Candidatura (\d+) de (\d+)\.$")
_STAGE = re.compile(r"^(\d+)/(\d+)$")
_HREF = re.compile(r"https?://([^/]+)/candidates/applications/(\d+)")
_BOUNDARIES = ("Já concluiu uma etapa", "Em andamento", "Em banco de talentos", "Finalizadas")
_WORKPLACES = {"Remoto", "Híbrido", "Presencial"}
_MARKERS = {"Também p/ PcD", "Seu Progresso"}


@dataclass
class Card:
    application_id: str
    company: str
    title: str
    location: str = ""
    workplace: str = ""
    contract: str = ""
    current: int | None = None
    total: int | None = None
    tab: str = "Em andamento"
    host: str = ""


def _is_marker(line: str) -> bool:
    return line in _MARKERS or line.startswith("Essa é uma vaga") or bool(_STAGE.match(line))


def _build(buffer: list[str], application_id: str, tab: str) -> Card | None:
    if len(buffer) < 2:
        return None
    company, title, rest = buffer[0], buffer[1], buffer[2:]
    workplace = next((line for line in rest if line in _WORKPLACES), "")
    location = rest[0] if rest and rest[0] not in _WORKPLACES else ""
    contract = ""
    if workplace:
        after = rest[rest.index(workplace) + 1 :]
        contract = next((line for line in after if not _is_marker(line)), "")
    stage = next(filter(None, (_STAGE.match(line) for line in rest)), None)
    return Card(
        application_id=application_id,
        company=company,
        title=title,
        location=location,
        workplace=workplace,
        contract=contract,
        current=int(stage.group(1)) if stage else None,
        total=int(stage.group(2)) if stage else None,
        tab=tab,
    )


def parse_cards(text: str, tab: str) -> tuple[list[Card], int | None]:
    """Lê o texto da tela 'Minhas candidaturas'. Devolve os cartões e o total que a Gupy anuncia."""
    cards: list[Card] = []
    buffer: list[str] = []
    announced: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        footer = _FOOTER.match(line)
        if footer:
            announced = int(footer.group(2))
            buffer = []
        elif line.startswith(_BOUNDARIES):
            buffer = []
        elif found := _ID.match(line):
            card = _build(buffer, found.group(1), tab)
            if card:
                cards.append(card)
            buffer = []
        else:
            buffer.append(line)
    return cards, announced


def hosts_from_links(hrefs: list[str]) -> dict[str, str]:
    """Número da candidatura -> endereço da empresa (ex.: zenvia.gupy.io), a partir dos links."""
    hosts: dict[str, str] = {}
    for href in hrefs:
        match = _HREF.search(href)
        if match:
            hosts[match.group(2)] = match.group(1).lower()
    return hosts


def _single(group: list[Job], statuses: dict[str, str]) -> Job | None:
    if len(group) == 1:
        return group[0]
    engaged = [job for job in group if statuses.get(job.uid) in ENGAGED]
    return engaged[0] if len(engaged) == 1 else None


def match_job_uid(card: Card, jobs: list[Job], statuses: dict[str, str]) -> tuple[str, str]:
    """Liga a candidatura a uma vaga do banco. Na dúvida, não liga (devolve vazio)."""
    title = normalize(card.title)
    same_title = [j for j in jobs if j.source == "gupy" and normalize(j.title) == title]
    if card.host:
        on_host = [j for j in same_title if urlsplit(j.url).hostname == card.host]
        pick = _single(on_host, statuses)
        if pick:
            return pick.uid, "link da empresa"
    company = normalize(card.company)
    group = [j for j in same_title if normalize(j.company) == company]
    # Se há outra vaga de mesmo título que você aprovou, o nome da empresa não basta.
    outside = [j for j in same_title if j not in group and statuses.get(j.uid) in ENGAGED]
    pick = _single(group, statuses) if group and not outside else None
    return (pick.uid, "nome da empresa") if pick else ("", "")


def record_cards(store: JobStore, cards: list[Card]) -> None:
    jobs = store.all()
    statuses = store.statuses()
    rows = []
    for card in cards:
        uid, _how = match_job_uid(card, jobs, statuses)
        rows.append({**asdict(card), "job_uid": uid})
    store.save_gupy_applications(rows)


def mark_applied_jobs(store: JobStore) -> list[str]:
    """Candidatura que aparece na sua lista da Gupy é candidatura enviada."""
    statuses = store.statuses()
    marked = []
    for row in store.gupy_applications():
        uid = row["job_uid"]
        if uid and row["tab"] != TALENT_POOL and statuses.get(uid) != APPLIED:
            store.set_status(uid, APPLIED)
            statuses[uid] = APPLIED
            marked.append(uid)
    return marked


def open_tab(page: Page, label: str) -> bool:
    try:
        page.get_by_role("tab", name=label).first.click(timeout=4000)
    except PlaywrightError:
        try:
            page.get_by_text(label, exact=True).first.click(timeout=4000)
        except PlaywrightError:
            return False
    page.wait_for_timeout(1500)
    return True


def read_tab(page: Page, tab: str) -> tuple[list[Card], int | None]:
    data = capture_text(page, limit=100_000)
    cards, announced = parse_cards(data["text"], tab)
    hosts = hosts_from_links(page.evaluate(LINKS_JS))
    for card in cards:
        card.host = hosts.get(card.application_id, "")
    return cards, announced


def collect(page: Page) -> list[Card]:
    cards: dict[str, Card] = {}
    for index, tab in enumerate(TABS):
        if index and not open_tab(page, tab):
            print(f"  aba '{tab}': não consegui abrir; pulei.")
            continue
        found, announced = read_tab(page, tab)
        note = ""
        if announced and len(found) < announced:
            note = f" (a Gupy anuncia {announced}: pode haver mais páginas)"
        print(f"  aba '{tab}': {len(found)} candidaturas{note}")
        for card in found:
            cards.setdefault(card.application_id, card)
    return list(cards.values())


def print_report(store: JobStore) -> None:
    rows = store.gupy_applications()
    print(f"\n{len(rows)} candidaturas na sua conta da Gupy:")
    for row in rows:
        stage = f"{row['current']}/{row['total']}" if row["current"] is not None else "-"
        target = row["job_uid"] or f"sem vaga ligada (candidatura {row['application_id']})"
        print(f"  {stage:>4} | {row['company'][:26]} | {row['title'][:36]} | {target}")
    unlinked = sum(1 for row in rows if not row["job_uid"])
    if unlinked:
        print(f"\n{unlinked} sem vaga ligada: normal para candidaturas feitas fora do sistema.")
        print("Para ligar à mão:")
        print("  python -m jobhunter.progress link <id da vaga> <id da candidatura>")

def ensure_applications_page(page: Page, ask=input) -> bool:
    """Abre 'Minhas candidaturas'. Se não estiver logado, deixa o navegador aberto para o login."""
    for attempt in range(2):
        try:
            page.wait_for_selector("text=Minhas candidaturas", timeout=20000)
            if "/my/applications" in page.url:
                return True
        except PlaywrightError:
            pass
        if attempt == 0:
            print("Não encontrei a lista 'Minhas candidaturas'. Você não está logado.")
            print("Faça login na janela do Chromium (ela fica aberta).")
            ask("Depois de logar, aperte Enter aqui... ")
            page.goto(URL, wait_until="domcontentloaded")
    return False

def main(argv: list[str]) -> None:
    store = JobStore()
    if argv and argv[0] == "link":
        if len(argv) < 3:
            print("Uso: python -m jobhunter.progress link <id da vaga> <id da candidatura>")
            return
        linked = store.link_gupy_application(argv[2], argv[1])
        print("Ligação salva." if linked else "Candidatura não encontrada: rode sem 'link'.")
        return
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        if not ensure_applications_page(page):
            print("Ainda não consegui abrir 'Minhas candidaturas'. Rode de novo depois de logar.")
            return
        page.wait_for_timeout(2500)
        cards = collect(page)
    if not cards:
        print("Nenhuma candidatura lida.")
        return
    record_cards(store, cards)
    marked = mark_applied_jobs(store)
    print_report(store)
    if marked:
        print("\nMarquei como enviadas (a Gupy confirma a candidatura): " + ", ".join(marked))
        print("Se alguma estiver errada, 'python -m jobhunter.bot --resend <id>' a recoloca")
        print("em revisão (só funciona para vagas que já têm candidatura preparada).")


if __name__ == "__main__":
    main(sys.argv[1:])