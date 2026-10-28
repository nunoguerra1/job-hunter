import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from jobhunter.filters import is_open, normalize
from jobhunter.followups import due_followups
from jobhunter.models import Job
from jobhunter.phases import current_and_next
from jobhunter.progress import incomplete_applications
from jobhunter.review import APPROVED, AWAITING
from jobhunter.storage import JobStore
from jobhunter.telegram import TelegramClient

OUTPUT = Path("output")
GOOD_SCORE = 80
SOON_DAYS = 3
FOLLOWUP_DAYS = 10
MAX_ITEMS = 5
MESSAGE_LIMIT = 3800
TEST_WORDS = ("prova", "teste", "case", "desafio", "raciocinio", "tecnic", "dinamica")

AWAITING_TITLE = "Aguardando a sua decisão no Telegram"
APPROVED_TITLE = "Aprovadas, ainda não enviadas"
SOON_TITLE = "Prazo nos próximos 3 dias"
INCOMPLETE_TITLE = "Candidaturas incompletas na Gupy (0/n)"
NEXT_TEST_TITLE = "Próxima fase com prova ou teste"
WAITING_TITLE = "Sem resposta há 10 dias ou mais"
FRESH_TITLE = "Boas vagas (nota 80+) sem candidatura preparada"

HINTS = {
    AWAITING_TITLE: "decidir: python -m jobhunter.bot",
    APPROVED_TITLE: (
        "enviar: python -m jobhunter.apply fill <id> (Gupy); nas outras, abra o link e "
        "depois rode apply mark <id>"
    ),
    INCOMPLETE_TITLE: "concluir em 'Minhas candidaturas', Ver andamento",
    FRESH_TITLE: "preparar: python -m jobhunter.prepare <id>",
}


def _where(job: Job) -> str:
    place = job.modality.value
    if job.location:
        place += f", {job.location.split(',')[0]}"
    return place


def _line(job: Job, *extra: str) -> str:
    parts = [job.title[:70], job.company[:40], _where(job), *extra]
    return " | ".join(part for part in parts if part)


def _waiting_for(uid: str, times: dict[str, str], now: datetime) -> str:
    moment = times.get(uid)
    if not moment:
        return ""
    days = (now - datetime.fromisoformat(moment)).days
    if days < 1:
        return "hoje"
    return f"há {days} dia{'s' if days != 1 else ''}"


def _clip(items: list[str]) -> list[str]:
    extra = len(items) - MAX_ITEMS
    return items[:MAX_ITEMS] + ([f"... e mais {extra}"] if extra > 0 else [])


def _with_status(jobs: list[Job], statuses: dict[str, str], wanted: str) -> list[Job]:
    return [job for job in jobs if statuses.get(job.uid) == wanted]


def upcoming_tests(store: JobStore) -> list[str]:
    """Candidaturas em andamento cuja próxima fase parece uma prova ou teste."""
    names_by_id = store.gupy_phases()
    items = []
    for row in store.gupy_applications():
        if row["tab"] != "Em andamento":
            continue
        names = names_by_id.get(row["application_id"], [])
        _here, ahead = current_and_next(row["current"], names)
        if ahead and any(word in normalize(ahead) for word in TEST_WORDS):
            stage = f"{row['current']}/{row['total']}"
            items.append(f"{row['company'][:30]} | próxima: {ahead} ({stage})")
    return items


def build_sections(
    store: JobStore, today: date, output: Path, now: datetime | None
) -> list[tuple[str, list[str]]]:
    reference = now or datetime.now(UTC)
    jobs = [job for job in store.all() if is_open(job, today)]
    statuses = store.statuses()
    scores = store.scores()
    times = store.status_times()
    awaiting = _with_status(jobs, statuses, AWAITING)
    approved = _with_status(jobs, statuses, APPROVED)

    limit = today + timedelta(days=SOON_DAYS)
    due_soon = [job for job in awaiting + approved if job.deadline and job.deadline.date() <= limit]
    due_soon.sort(key=lambda job: job.deadline)

    incomplete = [
        f"{row['company'][:30]} | {row['title'][:60]}"
        for row in incomplete_applications(store.gupy_applications())
    ]
    waiting = [
        f"{days} dias | {_line(job, job.uid)}"
        for job, days in due_followups(store, FOLLOWUP_DAYS, now)
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
        (
            AWAITING_TITLE,
            [_line(job, _waiting_for(job.uid, times, reference), job.uid) for job in awaiting],
        ),
        (
            APPROVED_TITLE,
            [_line(job, _waiting_for(job.uid, times, reference), job.uid) for job in approved],
        ),
        (
            SOON_TITLE,
            [f"prazo {job.deadline:%d/%m} | {_line(job, job.uid)}" for job in due_soon],
        ),
        (INCOMPLETE_TITLE, incomplete),
        (NEXT_TEST_TITLE, upcoming_tests(store)),
        (WAITING_TITLE, waiting),
        (FRESH_TITLE, [f"{score} | {_line(job, job.uid)}" for score, job in fresh]),
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
        if title in HINTS:
            lines.append(f"  -> {HINTS[title]}")
    return "\n".join(lines)


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """O Telegram aceita ~4096 caracteres por mensagem: divide nas quebras de linha."""
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def main(argv: list[str]) -> None:
    load_dotenv()
    text = build_digest(JobStore())
    print(text)
    if "--send" in argv:
        client = TelegramClient()
        chat_id = int(os.environ["TELEGRAM_CHAT_ID"])
        for chunk in split_message(text):
            client.send_message(chat_id, chunk)
        print("\nEnviado ao Telegram.")


if __name__ == "__main__":
    main(sys.argv[1:])