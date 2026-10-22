import sys

from dotenv import load_dotenv

from jobhunter.cost import load_costs
from jobhunter.filters import prefilter
from jobhunter.profile import load_profile
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
    ws = open_worksheet()
    if rebuild:
        reset_sheet(ws)
    added = sync(ws, entries, table=load_costs(), home_city=profile.city)
    expired = mark_expired(ws)
    updated = sync_statuses(ws, store.statuses())
    style_sheet(ws)
    print(f"{len(entries)} vagas elegíveis (nota >= {min_score}); {added} novas na planilha.")
    if expired:
        print(f"{expired} vagas marcadas como Encerrada (prazo vencido).")
    if updated:
        print(f"{updated} status atualizados a partir das suas decisões no Telegram.")

    emails = store.emails()
    if emails:
        mail_ws = open_worksheet("Candidaturas")
        added_mail = sync_mail(mail_ws, emails, store.all())
        mail_ws.freeze(rows=1)
        print(f"{added_mail} e-mails novos na aba Candidaturas.")


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    main(int(args[0]) if args else MIN_SCORE, rebuild="--rebuild" in sys.argv)