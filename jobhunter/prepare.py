import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google.genai import errors

from jobhunter.application import prepare_application, render_markdown
from jobhunter.filters import prefilter
from jobhunter.llm import GeminiClient, QuotaExhaustedError
from jobhunter.profile import load_profile
from jobhunter.storage import JobStore
from jobhunter.stories import load_story_bank

OUTPUT = Path("output")
MIN_SCORE = 70


def folder(uid: str) -> Path:
    return OUTPUT / uid.replace(":", "_")


def main(target: str = "3") -> None:
    load_dotenv()
    profile = load_profile()
    try:
        bank = load_story_bank()
    except (FileNotFoundError, ValueError) as error:
        print(f"Banco de histórias indisponível: {error}")
        return
    store = JobStore()
    scores = store.scores()
    jobs = {job.uid: job for job in store.all()}

    if ":" in target:  # um id específico, ex.: gupy:12511466
        selected = [jobs[target]] if target in jobs else []
    else:  # as N melhores ainda sem candidatura preparada
        eligible = [
            job
            for job in jobs.values()
            if job.uid in scores
            and scores[job.uid].course_compatible
            and scores[job.uid].score >= MIN_SCORE
            and prefilter(job, profile).keep
            and "banco de talentos" not in job.title.lower()
            and not folder(job.uid).exists()
        ]
        eligible.sort(key=lambda job: scores[job.uid].score, reverse=True)
        selected = eligible[: int(target)]

    if not selected:
        print("Nada para preparar.")
        return

    llm = GeminiClient()
    for job in selected:
        try:
            application = prepare_application(job, profile, bank, llm)
        except QuotaExhaustedError:
            print("Cota diária esgotada. Rode de novo mais tarde.")
            break
        except errors.APIError as error:
            print(f"  ERRO em '{job.title}': {error.code}")
            continue
        path = folder(job.uid)
        path.mkdir(parents=True, exist_ok=True)
        markdown = render_markdown(job, scores.get(job.uid), application)
        (path / "candidatura.md").write_text(markdown, encoding="utf-8")
        (path / "draft.json").write_text(application.model_dump_json(indent=2), encoding="utf-8")
        print(f"Preparada: {job.title} | {job.company} -> {path}")
        time.sleep(5)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "3")