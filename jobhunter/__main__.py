from collections import Counter

import httpx

from jobhunter.collectors.base import Collector
from jobhunter.collectors.gupy import GupyCollector
from jobhunter.collectors.remotive import RemotiveCollector
from jobhunter.filters import prefilter
from jobhunter.profile import load_profile
from jobhunter.storage import JobStore

KEYWORDS = [
    "estágio desenvolvimento",
    "estágio desenvolvedor",
    "estágio software",
    "estágio full stack",
    "estágio backend",
    "estágio frontend",
    "estágio dados",
    "estágio inteligência artificial",
    "estágio tecnologia",
    "trainee tecnologia",
    "desenvolvedor júnior",
    "programador júnior",
    "analista de sistemas júnior",
]


def collect(store: JobStore) -> None:
    collectors: list[Collector] = [
        GupyCollector(KEYWORDS, max_pages=5),
        GupyCollector(KEYWORDS[:7], workplace_type="remote", max_pages=5),
        RemotiveCollector(search="intern"),
    ]
    for collector in collectors:
        try:
            jobs = collector.fetch()
        except (httpx.HTTPError, ValueError) as error:
            print(f"[{collector.name}] ERRO: {error}")
            continue
        new = store.add_new(jobs)
        print(f"[{collector.name}] {len(jobs)} coletadas, {len(new)} novas")


def summarize(store: JobStore) -> None:
    jobs = store.all()
    print(f"\nTotal no banco: {len(jobs)}")
    try:
        profile = load_profile()
    except FileNotFoundError:
        print("profile/profile.yaml não encontrado; pulando o pré-filtro.")
        return
    results = [(job, prefilter(job, profile)) for job in jobs]
    kept = [(job, result) for job, result in results if result.keep]
    print(f"Passaram no pré-filtro: {len(kept)}")
    rejected = Counter(result.reason for _, result in results if not result.keep)
    for reason, count in rejected.most_common():
        print(f"  descartadas ({reason}): {count}")
    print("\nAmostra das que passaram:")
    for job, result in kept[:10]:
        print(f"  [{result.area}] {job.title} | {job.company} | {job.modality.value}")


def main() -> None:
    store = JobStore()
    collect(store)
    summarize(store)


if __name__ == "__main__":
    main()