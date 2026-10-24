import sys
from datetime import UTC, datetime

from jobhunter.models import Job
from jobhunter.review import APPLIED
from jobhunter.sheets import match_job
from jobhunter.storage import JobStore

NEWS_KINDS = {"avançou", "ação necessária", "mensagem do recrutador", "reprovada", "encerrada"}


def due_followups(
    store: JobStore, days: int = 10, now: datetime | None = None
) -> list[tuple[Job, int]]:
    """Candidaturas enviadas há `days` dias ou mais, sem e-mail de andamento depois do envio."""
    now = now or datetime.now(UTC)
    jobs = store.all()
    statuses = store.statuses()
    by_uid = {job.uid: job for job in jobs}
    applied_jobs = [job for job in jobs if statuses.get(job.uid) == APPLIED]
    applied_at = {uid: datetime.fromisoformat(v) for uid, v in store.status_times().items()}

    news: dict[str, datetime] = {}
    for email in store.emails():
        if email["kind"] not in NEWS_KINDS:
            continue
        uid = match_job(email["company"], email["subject"], applied_jobs)
        if uid:
            moment = datetime.fromisoformat(email["sent_at"])
            news[uid] = max(news.get(uid, moment), moment)

    due = []
    for uid, status in statuses.items():
        if status != APPLIED or uid not in by_uid:
            continue
        if uid in news and news[uid] >= applied_at[uid]:
            continue
        waited = (now - applied_at[uid]).days
        if waited >= days:
            due.append((by_uid[uid], waited))
    return sorted(due, key=lambda item: item[1], reverse=True)


def main(argv: list[str]) -> None:
    days = int(argv[0]) if argv and argv[0].isdigit() else 10
    due = due_followups(JobStore(), days)
    if not due:
        print(f"Nenhuma candidatura enviada há {days} dias ou mais sem resposta.")
        return
    print(f"Sem resposta há {days} dias ou mais (a checagem é aproximada):")
    for job, waited in due:
        print(f"  {waited} dias | {job.uid} | {job.title} | {job.company}\n    {job.url}")
    print("\nUma mensagem curta e educada é bem-vinda; evite mandar mais de uma.")


if __name__ == "__main__":
    main(sys.argv[1:])