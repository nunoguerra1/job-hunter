import hashlib
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from jobhunter.browser import persistent_browser
from jobhunter.filters import normalize
from jobhunter.forms import capture_text
from jobhunter.models import Job
from jobhunter.profile import load_profile
from jobhunter.review import APPLIED, APPROVED, AWAITING
from jobhunter.snap import redact
from jobhunter.storage import JobStore

URL = "https://portal.gupy.io/my/applications"
TABS = ["Em andamento", "Em banco de talentos", "Finalizadas"]
TALENT_POOL = "Em banco de talentos"
ENGAGED = {AWAITING, APPROVED, APPLIED}
DUMP_DIR = Path("data/pages")
MAX_PAGES = 20
LINKS_JS = """
() => [...document.querySelectorAll('a[href*="/candidates/applications/"]')].map(a => a.href)
"""
OUTCOME_STATUS = {
    "Você não avançou nesse processo": "Reprovada",
    "Vaga encerrada pela empresa": "Encerrada",
    "Vaga congelada pela empresa": "Congelada",
}

_ID = re.compile(r"^Ver andamento da candidatura\s*(\d+)$")
_FOOTER = re.compile(r"^Candidatura (\d+) de (\d+)\.$")
_STAGE = re.compile(r"^(\d+)/(\d+)$")
_HREF = re.compile(r"https?://([^/]+)/candidates/applications/(\d+)")
_BOUNDARIES = (
    "Já concluiu uma etapa",
    "As inscrições em bancos de",
    "Você sabia que o retorno",
    "Está com dúvidas sobre",
    "Em andamento",
    "Em banco de talentos",
    "Finalizadas",
)
_WORKPLACES = {"Remoto", "Híbrido", "Presencial"}
_MARKERS = {"Também p/ PcD", "Seu Progresso", "Banco de Talentos"}


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
    outcome: str = ""


def _is_marker(line: str) -> bool:
    return line in _MARKERS or line.startswith("Essa é uma vaga") or bool(_STAGE.match(line))


def _build(buffer: list[str], application_id: str, tab: str) -> Card | None:
    """Cartão com número (abas 'Em andamento' e 'Em banco de talentos')."""
    if len(buffer) < 2:
        return None
    company, title, rest = buffer[0], buffer[1], buffer[2:]
    workplace = next((line for line in rest if line in _WORKPLACES), "")
    first = rest[0] if rest else ""
    location = first if first and first not in _WORKPLACES and not _is_marker(first) else ""
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


def _build_finished(buffer: list[str], tab: str) -> Card | None:
    """Cartão sem número (aba Finalizadas): lê de trás para frente, a partir da modalidade."""
    index = next((i for i, line in enumerate(buffer) if line in _WORKPLACES), None)
    if index is None or index < 3:
        return None
    company, title, location = buffer[index - 3 : index]
    contract = next((line for line in buffer[index + 1 :] if not _is_marker(line)), "")
    leading = buffer[: index - 3]
    outcome = next((line for line in reversed(leading) if line in OUTCOME_STATUS), "")
    if not outcome and leading:
        outcome = leading[-1]
    return Card(
        application_id="",
        company=company,
        title=title,
        location=location,
        workplace=buffer[index],
        contract=contract,
        tab=tab,
        outcome=outcome,
    )


def parse_cards(text: str, tab: str) -> tuple[list[Card], int | None]:
    """Lê o texto de 'Minhas candidaturas'. Devolve os cartões e o total anunciado na página."""
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
            finished = _build_finished(buffer, tab)
            if finished:
                cards.append(finished)
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


def ids_in_order(hrefs: list[str]) -> list[str]:
    ordered: list[str] = []
    for href in hrefs:
        match = _HREF.search(href)
        if match and match.group(2) not in ordered:
            ordered.append(match.group(2))
    return ordered


def hosts_from_links(hrefs: list[str]) -> dict[str, str]:
    """Número da candidatura -> endereço da empresa (ex.: zenvia.gupy.io), a partir dos links."""
    hosts: dict[str, str] = {}
    for href in hrefs:
        match = _HREF.search(href)
        if match:
            hosts[match.group(2)] = match.group(1).lower()
    return hosts


def assign_ids(cards: list[Card], link_ids: list[str]) -> None:
    """Cartões sem número: usa os links da página se baterem um a um; senão, um código estável."""
    idless = [card for card in cards if not card.application_id]
    if not idless:
        return
    known = {card.application_id for card in cards if card.application_id}
    free = [application_id for application_id in link_ids if application_id not in known]
    if len(free) == len(idless):
        for card, application_id in zip(idless, free, strict=True):
            card.application_id = application_id
        return
    for card in idless:
        key = normalize(f"{card.company}|{card.title}|{card.location}")
        card.application_id = "f" + hashlib.sha1(key.encode()).hexdigest()[:10]


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
    matched = [(card, match_job_uid(card, jobs, statuses)[0]) for card in cards]
    claims = Counter(uid for _, uid in matched if uid)
    # Dois cartões que reivindicam a mesma vaga: não se liga nenhum (na dúvida, não liga).
    rows = [
        {**asdict(card), "job_uid": uid if uid and claims[uid] == 1 else ""}
        for card, uid in matched
    ]
    store.save_gupy_applications(rows)


def mark_applied_jobs(store: JobStore) -> list[str]:
    """Candidatura que aparece na sua lista da Gupy (e foi finalizada) é candidatura enviada."""
    statuses = store.statuses()
    marked = []
    for row in store.gupy_applications():
        uid = row["job_uid"]
        if not uid or row["tab"] == TALENT_POOL or row["current"] == 0:
            continue  # 0/n: a candidatura foi iniciada, mas ainda não foi finalizada
        if statuses.get(uid) != APPLIED:
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


def has_next_page(text: str, current: int) -> bool:
    """A paginação aparece depois do último cartão: '1 2 3 4 5 … 8'."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    footers = [i for i, line in enumerate(lines) if _FOOTER.match(line)]
    if not footers:
        return False
    tail: list[str] = []
    for line in lines[footers[-1] + 1 :]:
        if not (line.isdigit() or line == "…"):
            break
        tail.append(line)
    return str(current + 1) in tail


def go_to_page(page: Page, number: int) -> bool:
    """Clica no número da página. Só clica em números: nunca em 'Desistir' nem em cartões."""
    label = str(number)
    for locator in (
        page.get_by_role("button", name=label, exact=True),
        page.get_by_role("link", name=label, exact=True),
        page.get_by_text(label, exact=True),
    ):
        try:
            locator.last.click(timeout=3000)
        except PlaywrightError:
            continue
        page.wait_for_timeout(2000)
        return True
    return False


def read_tab(page: Page, tab: str) -> tuple[list[Card], int | None, str]:
    data = capture_text(page, limit=100_000)
    cards, announced = parse_cards(data["text"], tab)
    hrefs = page.evaluate(LINKS_JS)
    assign_ids(cards, ids_in_order(hrefs))
    hosts = hosts_from_links(hrefs)
    for card in cards:
        card.host = hosts.get(card.application_id, "")
    return cards, announced, data["text"]


def _new_cards(found: list[Card], seen: dict[str, Card]) -> list[Card]:
    return [card for card in found if card.application_id not in seen]


def collect(page: Page) -> list[Card]:
    cards: dict[str, Card] = {}
    for index, tab in enumerate(TABS):
        if index and not open_tab(page, tab):
            print(f"  aba '{tab}': não consegui abrir; pulei.")
            continue
        total = 0
        number = 1
        for number in range(1, MAX_PAGES + 1):
            found, _announced, text = read_tab(page, tab)
            fresh = _new_cards(found, cards)
            if not fresh and number > 1:  # a página pode não ter terminado de trocar
                page.wait_for_timeout(2500)
                found, _announced, text = read_tab(page, tab)
                fresh = _new_cards(found, cards)
            for card in fresh:
                cards[card.application_id] = card
            total += len(fresh)
            if not fresh or not has_next_page(text, number) or not go_to_page(page, number + 1):
                break
        print(f"  aba '{tab}': {total} candidaturas ({number} página(s) lida(s))")
    return list(cards.values())


def dump_tabs(
    page, names: list[str], folder: Path = DUMP_DIR, opener=open_tab, reader=capture_text
) -> list[Path]:
    """Salva o texto de cada aba (com máscara de dados pessoais) para eu ver o formato real."""
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for index, tab in enumerate(TABS, start=1):
        if index > 1 and not opener(page, tab):
            print(f"  aba '{tab}': não consegui abrir; pulei.")
            continue
        data = reader(page, limit=100_000)
        body = redact(data["text"], names)
        path = folder / f"aba_{index}.txt"
        path.write_text(f"{data['url']}\n{tab}\n\n{body}", encoding="utf-8")
        saved.append(path)
    return saved

def incomplete_applications(rows: list[dict]) -> list[dict]:
    """Em andamento com 0/n: pelo que vi na Vendemmia, a candidatura ainda não foi finalizada."""
    return [row for row in rows if row["tab"] == "Em andamento" and row["current"] == 0]

def result_label(row: dict) -> str:
    """Resultado em palavras curtas; texto que ainda não conheço aparece como foi escrito."""
    return OUTCOME_STATUS.get(row["outcome"]) or row["outcome"]


def summarize_finished(rows: list[dict], key: str) -> dict[str, Counter]:
    groups: dict[str, Counter] = {}
    for row in rows:
        if row["tab"] != "Finalizadas":
            continue
        name = row[key] or "não informado"
        result = result_label(row) or "sem resultado"
        groups.setdefault(name, Counter())[result] += 1
    return groups


def print_stats(store: JobStore) -> None:
    rows = store.gupy_applications()
    if not rows:
        print("Nenhuma candidatura lida ainda. Rode: python -m jobhunter.progress")
        return
    print("Reprovada: a empresa avaliou e disse não. Encerrada: a empresa fechou a vaga.")
    print("O resultado não diz até que etapa você chegou.")
    for key, title in (("contract", "tipo de contrato"), ("workplace", "modalidade")):
        print(f"\nFinalizadas por {title}:")
        groups = summarize_finished(rows, key)
        for name, counter in sorted(groups.items(), key=lambda item: -sum(item[1].values())):
            detail = ", ".join(f"{label} {count}" for label, count in counter.most_common())
            print(f"  {name}: {sum(counter.values())} | {detail}")
    stages = Counter(
        f"{r['current']}/{r['total']}"
        for r in rows
        if r["tab"] == "Em andamento" and r["current"] is not None
    )
    if stages:
        print("\nEtapa atual: " + ", ".join(f"{s} ({n})" for s, n in stages.items()))


def print_report(store: JobStore) -> None:
    rows = store.gupy_applications()
    print(f"\n{len(rows)} candidaturas na sua conta da Gupy:")
    for row in rows:
        stage = f"{row['current']}/{row['total']}" if row["current"] is not None else "-"
        target = row["job_uid"] or f"sem vaga ligada (#{row['application_id']})"
        company, title = row["company"][:26], row["title"][:36]
        line = f"  {stage:>4} | {company} | {title} | {target}"
        result = result_label(row)
        print(f"{line} | {result}" if result else line)
    results = Counter(result_label(row) for row in rows if row["outcome"])
    if results:
        print("\nResultados: " + " | ".join(f"{name} {count}" for name, count in results.items()))
    known = set(OUTCOME_STATUS) | {""}
    unknown = sorted({row["outcome"] for row in rows if row["outcome"] not in known})
    if unknown:
        print("Textos de resultado que ainda não conheço: " + " | ".join(unknown))
    blank = sum(1 for row in rows if row["tab"] == "Finalizadas" and not row["outcome"])
    if blank:
        print(f"{blank} finalizadas sem nenhum texto de resultado.")
    pending = incomplete_applications(rows)
    if pending:
        print(f"\nATENÇÃO: {len(pending)} candidatura(s) com 0/n:")
        for row in pending:
            print(f"  {row['company'][:28]} | {row['title'][:44]} | #{row['application_id']}")
        print("A Vendemmia ficou em 0/4 até você terminar as perguntas e enviar. Confira")
        print("em 'Ver andamento' se falta algo nesta(s); a empresa só avalia as finalizadas.")
    unlinked = sum(1 for row in rows if not row["job_uid"])
    if unlinked:
        print(f"\n{unlinked} sem vaga ligada: normal para candidaturas feitas fora do sistema.")
        print("Para ligar à mão (ou desfazer com '-' no lugar do id da vaga):")
        print("  python -m jobhunter.progress link <id da vaga> <número da candidatura>")


def _where(page: Page) -> str:
    parts = urlsplit(page.url)
    return f"{parts.hostname}{parts.path}"  # sem parâmetros, que podem carregar tokens


def _goto(page: Page, url: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded")
    except PlaywrightError:
        pass  # outra navegação já estava em andamento (ex.: o redirecionamento do login)


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
            print(f"Página atual: {_where(page)}")
            print("Faça login na janela do Chromium (ela fica aberta).")
            ask("Depois de logar, aperte Enter aqui... ")
            if "/my/applications" not in page.url:
                _goto(page, URL)
    return False


def main(argv: list[str]) -> None:
    store = JobStore()
    if argv and argv[0] == "link":
        if len(argv) < 3:
            print("Uso: python -m jobhunter.progress link <id da vaga> <número da candidatura>")
            print("     (use '-' no lugar do id da vaga para desfazer a ligação)")
            return
        job_uid = "" if argv[1] == "-" else argv[1]
        linked = store.link_gupy_application(argv[2], job_uid)
        print("Ligação salva." if linked else "Candidatura não encontrada: rode sem 'link'.")
        return
    if argv and argv[0] == "stats":
        print_stats(store)
        return
    dump = bool(argv) and argv[0] == "dump"
    try:
        names = load_profile().name.split()
    except FileNotFoundError:
        names = []
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        _goto(page, URL)
        if not ensure_applications_page(page):
            print("Ainda não consegui abrir 'Minhas candidaturas'. Rode de novo depois de logar.")
            return
        page.wait_for_timeout(2500)
        saved = dump_tabs(page, names) if dump else []
        cards = [] if dump else collect(page)
    if dump:
        for path in saved:
            print(f"salvo: {path}")
        print("Abra cada arquivo, apague o que for pessoal e cole o conteúdo aqui.")
        return
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