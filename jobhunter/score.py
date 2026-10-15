import sys
import time

from dotenv import load_dotenv
from google.genai import errors

from jobhunter.filters import prefilter
from jobhunter.llm import GeminiClient
from jobhunter.match import score_job
from jobhunter.profile import load_profile
from jobhunter.storage import JobStore


def show_ranking(store: JobStore) -> None:
    scores = store.scores()
    ranked = sorted(
        ((scores[job.uid], job) for job in store.all() if job.uid in scores),
        key=lambda pair: pair[0].score,
        reverse=True,
    )
    print("\nRanking (cursos compatíveis):")
    for result, job in [p for p in ranked if p[0].course_compatible][:10]:
        print(f"{result.score:>3} | {job.title} | {job.company} | {job.modality.value}")


def main(limit: int = 20) -> None:
    load_dotenv()
    profile = load_profile()
    store = JobStore()
    llm = GeminiClient()
    scored = store.scores()
    pending = [j for j in store.all() if prefilter(j, profile).keep and j.uid not in scored]
    print(f"{len(pending)} vagas sem nota; avaliando até {limit}.")
    for job in pending[:limit]:
        try:
            result = score_job(job, profile, llm)
        except errors.APIError as error:
            print(f"  ERRO ao avaliar '{job.title}': {error.code}")
            continue
        store.save_score(job.uid, result)
        print(f"{result.score:>3} | {job.title} | {job.company} | {job.modality.value}")
        time.sleep(5)
    show_ranking(store)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)