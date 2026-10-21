import sys

from jobhunter.browser import persistent_browser
from jobhunter.models import Job
from jobhunter.review import APPLIED, APPROVED
from jobhunter.storage import JobStore

LOGIN_URL = "https://portal.gupy.io/"


def approved_jobs(store: JobStore) -> list[Job]:
    statuses = store.statuses()
    return [job for job in store.all() if statuses.get(job.uid) == APPROVED]


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
        print(f"{job.uid} | {job.title} | {job.company}\n    {job.url}")


def mark_applied(store: JobStore, uid: str) -> None:
    if uid not in {job.uid for job in store.all()}:
        print(f"Vaga '{uid}' não encontrada.")
        return
    store.set_status(uid, APPLIED)
    print(f"Marcada como enviada: {uid}")


def main(argv: list[str]) -> None:
    command = argv[0] if argv else ""
    if command == "login":
        login()
    elif command == "list":
        list_approved(JobStore())
    elif command == "mark" and len(argv) > 1:
        mark_applied(JobStore(), argv[1])
    else:
        print("Uso: python -m jobhunter.apply [login | list | mark <id>]")


if __name__ == "__main__":
    main(sys.argv[1:])