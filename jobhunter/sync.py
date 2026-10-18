import sys

from dotenv import load_dotenv

from jobhunter.filters import prefilter
from jobhunter.profile import load_profile
from jobhunter.sheets import open_worksheet, style_sheet, sync
from jobhunter.storage import JobStore

MIN_SCORE = 60


def main(min_score: int = MIN_SCORE) -> None:
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
    added = sync(ws, entries)
    style_sheet(ws)
    print(f"{len(entries)} vagas elegíveis (nota >= {min_score}); {added} novas na planilha.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else MIN_SCORE)