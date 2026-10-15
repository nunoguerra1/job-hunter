import httpx

from jobhunter.collectors.base import Collector
from jobhunter.collectors.gupy import GupyCollector
from jobhunter.collectors.remotive import RemotiveCollector
from jobhunter.storage import JobStore

KEYWORDS = [
    "estágio desenvolvimento",
    "estágio dados",
    "estágio tecnologia",
    "trainee tecnologia",
    "desenvolvedor júnior",
]


def main() -> None:
    store = JobStore()
    collectors: list[Collector] = [
        GupyCollector(KEYWORDS),
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
    print(f"Total no banco: {len(store.all())}")


if __name__ == "__main__":
    main()