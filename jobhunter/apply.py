import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from jobhunter.answers import Plan, load_answers, plan_step
from jobhunter.application import Application
from jobhunter.browser import persistent_browser
from jobhunter.fill import FillResult, fill_step
from jobhunter.filters import is_open
from jobhunter.forms import capture, save_snapshot
from jobhunter.models import Job
from jobhunter.review import APPLIED, APPROVED, AWAITING, CLOSED
from jobhunter.storage import JobStore

LOGIN_URL = "https://portal.gupy.io/"
CLOSED_MARKERS = ("inscrições encerradas", "candidaturas encerradas")
GUPY_HOSTS = ("gupy.io", "gupy.com.br")
UNANSWERED = Path("data/unanswered.jsonl")


def approved_jobs(store: JobStore) -> list[Job]:
    statuses = store.statuses()
    return [job for job in store.all() if statuses.get(job.uid) == APPROVED and is_open(job)]


def page_is_closed(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CLOSED_MARKERS)


def is_gupy_url(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    return any(host == base or host.endswith("." + base) for base in GUPY_HOSTS)


def job_is_closed(page: Page, url: str) -> bool:
    page.goto(url, wait_until="domcontentloaded")
    try:
        page.wait_for_selector("h1", timeout=15000)
    except PlaywrightError:
        return False  # não deu para ler a página: não presume encerrada
    return page_is_closed(page.inner_text("body"))


def login() -> None:
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(LOGIN_URL)
        input("Faça login na Gupy na janela aberta e depois aperte Enter aqui... ")
    print("Sessão salva em data/browser_profile.")


def list_approved(store: JobStore) -> None:
    jobs = approved_jobs(store)
    if not jobs:
        print("Nenhuma candidatura aprovada aguardando envio.")
        return
    for job in jobs:
        prazo = f"{job.deadline:%d/%m/%Y}" if job.deadline else "sem prazo"
        print(f"{job.uid} | {job.title} | {job.company} | prazo {prazo}\n    {job.url}")


def mark_applied(store: JobStore, uid: str) -> None:
    if uid not in {job.uid for job in store.all()}:
        print(f"Vaga '{uid}' não encontrada.")
        return
    store.set_status(uid, APPLIED)
    print(f"Marcada como enviada: {uid}")


def status_report(store: JobStore) -> None:
    statuses = store.statuses()
    if not statuses:
        print("Nenhuma candidatura com status ainda.")
        return
    counts = Counter(statuses.values()).most_common()
    print("Resumo: " + " | ".join(f"{name} {count}" for name, count in counts))
    jobs = {job.uid: job for job in store.all()}
    groups = ((APPLIED, "Enviadas"), (APPROVED, "Aprovadas e ainda não enviadas"))
    for wanted, label in groups:
        rows = [jobs[uid] for uid in statuses if statuses[uid] == wanted and uid in jobs]
        if rows:
            print(f"\n{label}:")
            for job in rows:
                print(f"  {job.uid} | {job.title} | {job.company}")


def check_open(store: JobStore) -> None:
    """Visita as vagas em revisão ou aprovadas e marca como 'closed' as já encerradas."""
    statuses = store.statuses()
    jobs = [job for job in store.all() if statuses.get(job.uid) in {AWAITING, APPROVED}]
    if not jobs:
        print("Nada para verificar.")
        return
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            for job in jobs:
                try:
                    closed = job_is_closed(page, job.url)
                except PlaywrightError as error:
                    print(f"não foi possível verificar: {job.title} ({type(error).__name__})")
                    continue
                if closed:
                    store.set_status(job.uid, CLOSED)
                    print(f"ENCERRADA: {job.title} | {job.company}")
                else:
                    print(f"aberta: {job.title} | {job.company}")
        finally:
            browser.close()


def inspect_form(store: JobStore, uid: str) -> None:
    job = next((j for j in store.all() if j.uid == uid), None)
    if not job:
        print(f"Vaga '{uid}' não encontrada.")
        return
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        if job_is_closed(page, job.url):
            store.set_status(uid, CLOSED)
            print("Esta vaga está ENCERRADA. Marquei como 'closed' e parei.")
            return
        print("Navegue pela candidatura. Em cada etapa, espere a tela terminar de carregar,")
        print("volte aqui e aperte Enter para capturar. Pare ANTES do botão final de envio.")
        step = 1
        while True:
            answer = input(f"Etapa {step}: Enter captura a tela atual, 'q' encerra: ").strip()
            if answer.lower() == "q":
                break
            open_pages = [p for p in context.pages if not p.is_closed()]
            if not open_pages:
                print("  nenhuma aba aberta; encerrando.")
                break
            try:
                data = capture(open_pages[-1])
            except PlaywrightError as error:
                print(f"  não consegui capturar ({type(error).__name__}). Espere a página")
                print("  terminar de carregar e aperte Enter de novo.")
                continue
            print(f"  capturado: {save_snapshot(data, uid, step)}")
            step += 1


def draft_context(uid: str, output: Path = Path("output")) -> dict[str, str]:
    """Textos já gerados e aprovados, usados nos {placeholders} do answers.yaml."""
    path = output / uid.replace(":", "_") / "draft.json"
    if not path.exists():
        return {}
    app = Application.model_validate_json(path.read_text(encoding="utf-8"))
    return {
        "why_us": app.why_us,
        "salary_answer": app.salary_answer,
        "cv_summary": app.cv_summary,
    }


def print_fill(result: FillResult) -> None:
    mine = [*result.pending, *result.failed]
    print(f"  preenchidas: {len(result.filled)} | com você: {len(mine)}")
    for plan in result.filled:
        shown = ", ".join(plan.values)
        print(f"   [ok] {plan.question[:70]} -> {shown[:50]}")
    for plan in mine:
        print(f"   [ ! ] {plan.question[:70]} ({plan.reason})")


def log_unanswered(plans: list[Plan], questions: list[dict], path: Path = UNANSWERED) -> int:
    """Guarda as perguntas sem regra, para você decidir depois quais viram regra."""
    options = {q["key"]: q.get("options", []) for q in questions}
    rows = [p for p in plans if p.action == "human" and p.reason == "sem regra"]
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for plan in rows:
            record = {"question": plan.question, "options": options.get(plan.key, [])}
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(rows)


def gaps(path: Path = UNANSWERED) -> None:
    if not path.exists():
        print("Nenhuma pergunta sem regra registrada ainda.")
        return
    counts: Counter[str] = Counter()
    options: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            counts[record["question"]] += 1
            options[record["question"]] = record.get("options", [])
    print("Perguntas sem regra (as mais frequentes primeiro):")
    for question, times in counts.most_common(20):
        print(f"{times}x | {question}")
        if options[question]:
            print("      opções: " + " / ".join(options[question]))
    print("\nPara automatizar uma, crie uma regra em profile/answers.yaml (só se for verdade).")


def finish_application(store: JobStore, uid: str, answer: str) -> bool:
    """Só marca como enviada se você confirmar que clicou em enviar."""
    if answer.strip().lower() in {"s", "sim", "y", "yes"}:
        store.set_status(uid, APPLIED)
        return True
    return False


def fill_job(store: JobStore, uid: str) -> None:
    job = next((j for j in store.all() if j.uid == uid), None)
    if not job:
        print(f"Vaga '{uid}' não encontrada.")
        return
    try:
        answers = load_answers()
    except FileNotFoundError:
        print("profile/answers.yaml não encontrado. Copie profile/answers.example.yaml e ajuste.")
        return
    values = draft_context(uid)
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        if job_is_closed(page, job.url):
            store.set_status(uid, CLOSED)
            print("Esta vaga está ENCERRADA. Marquei como 'closed' e parei.")
            return
        print("Navegue até a candidatura. Comandos (digite e aperte Enter):")
        print("  (vazio)  preenche a etapa atual, só em páginas da Gupy")
        print("  s        já me candidatei: marca como enviada e sai")
        print("  q        sai sem marcar nada")
        print("Eu nunca clico em 'Salvar e continuar' nem em enviar: isso é seu.")
        while True:
            command = input("> ").strip().lower()
            if command == "q":
                print("Saí sem marcar. Se você enviou, rode:")
                print(f"  python -m jobhunter.apply mark {uid}")
                break
            if finish_application(store, uid, command):
                print(f"Marcada como enviada: {uid}")
                break
            if command:
                print("  comando desconhecido: use Enter, 's' ou 'q'.")
                continue
            open_pages = [p for p in context.pages if not p.is_closed()]
            if not open_pages:
                print("  nenhuma aba aberta; encerrando.")
                break
            current = open_pages[-1]  # a Gupy pode abrir a candidatura em outra aba
            if not is_gupy_url(current.url):
                print("  esta aba não é da Gupy: nada preenchido.")
                print("  Candidate-se à mão e depois digite 's'.")
                continue
            try:
                data = capture(current)
                questions = data.get("questions", [])
                plans = plan_step(questions, answers, values)
                if not plans:
                    print("  nenhuma pergunta encontrada nesta etapa.")
                    continue
                print_fill(fill_step(current, plans))
                log_unanswered(plans, questions)
            except PlaywrightError as error:
                print(f"  não consegui preencher ({type(error).__name__}).")
                print("  Espere a página carregar e aperte Enter de novo.")


def main(argv: list[str]) -> None:
    command = argv[0] if argv else ""
    if command == "login":
        login()
    elif command == "list":
        list_approved(JobStore())
    elif command == "status":
        status_report(JobStore())
    elif command == "check":
        check_open(JobStore())
    elif command == "mark" and len(argv) > 1:
        mark_applied(JobStore(), argv[1])
    elif command == "inspect" and len(argv) > 1:
        inspect_form(JobStore(), argv[1])
    elif command == "fill" and len(argv) > 1:
        fill_job(JobStore(), argv[1])
    elif command == "gaps":
        gaps()
    else:
        print(
            "Uso: python -m jobhunter.apply "
            "[login | list | status | check | mark <id> | inspect <id> | fill <id> | gaps]"
        )


if __name__ == "__main__":
    main(sys.argv[1:])