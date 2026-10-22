import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from jobhunter.answers import load_answers, plan_step
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


def approved_jobs(store: JobStore) -> list[Job]:
    statuses = store.statuses()
    return [job for job in store.all() if statuses.get(job.uid) == APPROVED and is_open(job)]


def page_is_closed(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CLOSED_MARKERS)


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
        print("Navegue até uma etapa de perguntas. Eu preencho só o que está nas suas regras,")
        print("marco em vermelho o que é com você e NUNCA clico em 'Salvar e continuar' nem em")
        print("enviar: isso é seu.")
        while True:
            if input("Enter preenche a etapa atual, 'q' encerra: ").strip().lower() == "q":
                break
            open_pages = [p for p in context.pages if not p.is_closed()]
            if finish_application(store, uid, input("Você enviou esta candidatura? (s/N) ")):
                print(f"Marcada como enviada: {uid}")
            if not open_pages:
                print("  nenhuma aba aberta; encerrando.")
                break
            try:
                data = capture(open_pages[-1])
                plans = plan_step(data.get("questions", []), answers, values)
                if not plans:
                    print("  nenhuma pergunta encontrada nesta etapa.")
                    continue
                print_fill(fill_step(open_pages[-1], plans))
            except PlaywrightError as error:
                print(f"  não consegui preencher ({type(error).__name__}).")
                print("  Espere a página carregar e aperte Enter de novo.")


def main(argv: list[str]) -> None:
    command = argv[0] if argv else ""
    if command == "login":
        login()
    elif command == "list":
        list_approved(JobStore())
    elif command == "check":
        check_open(JobStore())
    elif command == "mark" and len(argv) > 1:
        mark_applied(JobStore(), argv[1])
    elif command == "inspect" and len(argv) > 1:
        inspect_form(JobStore(), argv[1])
    elif command == "fill" and len(argv) > 1:
        fill_job(JobStore(), argv[1])
    else:
        print(
            "Uso: python -m jobhunter.apply "
            "[login | list | check | mark <id> | inspect <id> | fill <id>]"
        )


if __name__ == "__main__":
    main(sys.argv[1:])