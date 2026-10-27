import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from jobhunter.filters import is_open
from jobhunter.followups import due_followups
from jobhunter.models import Job
from jobhunter.progress import incomplete_applications
from jobhunter.review import APPROVED, AWAITING
from jobhunter.storage import JobStore
from jobhunter.telegram import TelegramClient

OUTPUT = Path("output")
GOOD_SCORE = 80
SOON_DAYS = 3
FOLLOWUP_DAYS = 10
MAX_ITEMS = 5

AWAITING_TITLE = "Aguardando a sua decisão no Telegram"
APPROVED_TITLE = "Aprovadas, ainda não enviadas"
SOON_TITLE = "Prazo nos próximos 3 dias"
INCOMPLETE_TITLE = "Candidaturas incompletas na Gupy (0/n)"
WAITING_TITLE = "Sem resposta há 10 dias ou mais"
FRESH_TITLE = "Boas vagas (nota 80+) sem candidatura preparada"


def _line(job: Job) -> str:
    return f"{job.title[:60]} | {job.company[:30]}"


def _clip(items: list[str]) -> list[str]:
    extra = len(items) - MAX_ITEMS
    return items[:MAX_ITEMS] + ([f"... e mais {extra}"] if extra > 0 else [])


def _with_status(jobs: list[Job], statuses: dict[str, str], wanted: str) -> list[Job]:
    return [job for job in jobs if statuses.get(job.uid) == wanted]


def build_sections(
    store: JobStore, today: date, output: Path, now: datetime | None
) -> list[tuple[str, list[str]]]:
    jobs = [job for job in store.all() if is_open(job, today)]
    statuses = store.statuses()
    scores = store.scores()
    awaiting = _with_status(jobs, statuses, AWAITING)
    approved = _with_status(jobs, statuses, APPROVED)

    limit = today + timedelta(days=SOON_DAYS)
    due_soon = [job for job in awaiting + approved if job.deadline and job.deadline.date() <= limit]
    due_soon.sort(key=lambda job: job.deadline)

    incomplete = [
        f"{row['company'][:30]} | {row['title'][:50]}"
        for row in incomplete_applications(store.gupy_applications())
    ]
    waiting = [
        f"{days} dias | {_line(job)}" for job, days in due_followups(store, FOLLOWUP_DAYS, now)
    ]

    fresh = [
        (scores[job.uid].score, job)
        for job in jobs
        if job.uid in scores
        and job.uid not in statuses
        and scores[job.uid].course_compatible
        and scores[job.uid].score >= GOOD_SCORE
        and "banco de talentos" not in job.title.lower()
        and not (output / job.uid.replace(":", "_")).exists()
    ]
    fresh.sort(key=lambda item: item[0], reverse=True)

    return [
        (AWAITING_TITLE, [_line(job) for job in awaiting]),
        (APPROVED_TITLE, [_line(job) for job in approved]),
        (SOON_TITLE, [f"prazo {job.deadline:%d/%m} | {_line(job)}" for job in due_soon]),
        (INCOMPLETE_TITLE, incomplete),
        (WAITING_TITLE, waiting),
        (FRESH_TITLE, [f"{score} | {_line(job)} | {job.uid}" for score, job in fresh]),
    ]


def build_digest(
    store: JobStore,
    today: date | None = None,
    output: Path = OUTPUT,
    now: datetime | None = None,
) -> str:
    today = today or date.today()
    filled = [(t, items) for t, items in build_sections(store, today, output, now) if items]
    lines = [f"Resumo do dia ({today:%d/%m})"]
    if not filled:
        lines.append("\nNada pendente hoje.")
    for title, items in filled:
        lines.append(f"\n{title} ({len(items)}):")
        lines.extend(f"- {item}" for item in _clip(items))
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    load_dotenv()
    text = build_digest(JobStore())
    print(text)
    if "--send" in argv:
        TelegramClient().send_message(int(os.environ["TELEGRAM_CHAT_ID"]), text)
        print("\nEnviado ao Telegram.")


if __name__ == "__main__":
    main(sys.argv[1:])