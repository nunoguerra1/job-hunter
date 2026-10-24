import sys

from dotenv import load_dotenv

from jobhunter.cost import load_costs
from jobhunter.filters import prefilter
from jobhunter.mail_status import sync_mail_status
from jobhunter.profile import load_profile
from jobhunter.progress_sheet import sync_gupy_tab, sync_progress
from jobhunter.review import APPLIED
from jobhunter.sheets import (
    mark_expired,
    open_worksheet,
    reset_sheet,
    style_sheet,
    sync,
    sync_mail,
    sync_statuses,
)
from jobhunter.storage import JobStore

MIN_SCORE = 60


def main(min_score: int = MIN_SCORE, rebuild: bool = False) -> None:
    load_dotenv()
    profile = load_profile()
    store = JobStore()
    scores = store.scores()
    entries = [
        (job, scores[job.uid])
        for job in store.all()
        if job.uid in scores
        and scores[job.uid].course_compatible
        and scores[job.uid].score >= min_score
        and prefilter(job, profile).keep
    ]
    entries.sort(key=lambda entry: entry[1].score, reverse=True)
    statuses = store.statuses()
    applied_jobs = [job for job in store.all() if statuses.get(job.uid) == APPLIED]
    emails = store.emails()
    applications = store.gupy_applications()

    ws = open_worksheet()
    if rebuild:
        reset_sheet(ws)
    added = sync(ws, entries, table=load_costs(), home_city=profile.city)
    expired = mark_expired(ws)
    updated = sync_statuses(ws, statuses)
    progressed = sync_mail_status(ws, emails, applied_jobs)
    style_sheet(ws)
    staged = sync_progress(ws, applications)
    print(f"{len(entries)} vagas elegíveis (nota >= {min_score}); {added} novas na planilha.")
    if expired:
        print(f"{expired} vagas marcadas como Encerrada (prazo vencido).")
    if updated:
        print(f"{updated} status atualizados a partir das suas decisões no Telegram.")
    if progressed:
        print(f"{progressed} vagas com andamento atualizado a partir dos e-mails.")
    if staged:
        print(f"{staged} vagas com a etapa atual (ex.: 1/7) atualizada pela Gupy.")

    if emails:
        mail_ws = open_worksheet("Candidaturas")
        added_mail = sync_mail(mail_ws, emails, applied_jobs)
        mail_ws.freeze(rows=1)
        print(f"{added_mail} e-mails novos na aba Candidaturas.")
    if applications:
        gupy_ws = open_worksheet("Gupy")
        sync_gupy_tab(gupy_ws, applications)
        gupy_ws.freeze(rows=1)
        print(f"{len(applications)} candidaturas na aba Gupy.")


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    main(int(args[0]) if args else MIN_SCORE, rebuild="--rebuild" in sys.argv)