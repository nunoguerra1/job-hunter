import sys
import time

from dotenv import load_dotenv
from google.genai import errors

from jobhunter.filters import prefilter
from jobhunter.llm import GeminiClient, QuotaExhaustedError
from jobhunter.match import BATCH_SIZE, score_batch
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


def main(limit: int = 40) -> None:
    load_dotenv()
    profile = load_profile()
    store = JobStore()
    llm = GeminiClient()
    scored = store.scores()
    pending = [j for j in store.all() if prefilter(j, profile).keep and j.uid not in scored]
    print(f"{len(pending)} vagas sem nota; avaliando até {limit}.")
    pending = pending[:limit]
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        try:
            results = score_batch(batch, profile, llm)
        except QuotaExhaustedError:
            print("Cota diária esgotada. As notas já feitas estão salvas; rode de novo mais tarde.")
            break
        except errors.APIError as error:
            print(f"  ERRO no lote ({error.code}); as vagas ficam para a próxima rodada")
            continue
        for job in batch:
            if job.uid in results:
                store.save_score(job.uid, results[job.uid])
                print(f"{results[job.uid].score:>3} | {job.title} | {job.company}")
        time.sleep(5)
    show_ranking(store)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)