import sys
import time

from dotenv import load_dotenv
from google.genai import errors

from jobhunter.filters import prefilter
from jobhunter.llm import GeminiClient
from jobhunter.match import score_job
from jobhunter.profile import load_profile
from jobhunter.storage import JobStore


def main(limit: int = 5) -> None:
    load_dotenv()
    profile = load_profile()
    llm = GeminiClient()
    candidates = [j for j in JobStore().all() if prefilter(j, profile).keep][:limit]
    for job in candidates:
        try:
            result = score_job(job, profile, llm)
        except errors.APIError as error:
            print(f"  ERRO ao avaliar '{job.title}': {error.code}")
            continue
        print(f"{result.score:>3} | {job.title} | {job.company} | {job.modality.value}")
        print(f"      {result.summary}")
        print(f"      faltam: {', '.join(result.missing_skills) or '-'}")
        time.sleep(5)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)