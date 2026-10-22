import time

import httpx

from jobhunter.classify import detect_level
from jobhunter.collectors.base import Collector
from jobhunter.collectors.common import (
    is_entry_level,
    modality_from_text,
    parse_date,
    strip_tags,
)
from jobhunter.models import Job

API_URL = "https://api.adzuna.com/v1/api/jobs/br/search/{page}"
PAGE_SIZE = 50


class AdzunaCollector(Collector):
    name = "adzuna"

    def __init__(
        self,
        app_id: str,
        app_key: str,
        queries: list[str],
        max_pages: int = 2,
        delay: float = 1.0,
        client: httpx.Client | None = None,
    ):
        self.app_id = app_id
        self.app_key = app_key
        self.queries = queries
        self.max_pages = max_pages
        self.delay = delay
        self.client = client or httpx.Client(timeout=30)
        self.errors: list[str] = []

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for query in self.queries:
            for page in range(1, self.max_pages + 1):
                params = {
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "what": query,
                    "results_per_page": PAGE_SIZE,
                    "content-type": "application/json",
                }
                try:
                    response = self.client.get(API_URL.format(page=page), params=params)
                    response.raise_for_status()
                    results = response.json().get("results", [])
                except (httpx.HTTPError, ValueError) as error:
                    # só o tipo do erro: a mensagem original carrega a URL com a chave
                    self.errors.append(f"adzuna '{query}': {type(error).__name__}")
                    break
                for item in results:
                    job = self._to_job(item)
                    if job:
                        jobs[job.uid] = job
                if len(results) < PAGE_SIZE:
                    break
                time.sleep(self.delay)
        return list(jobs.values())

    def _to_job(self, item: dict) -> Job | None:
        title = strip_tags(item.get("title", ""))
        if item.get("id") is None or not is_entry_level(title):
            return None
        description = strip_tags(item.get("description", ""))  # a Adzuna só manda um trecho
        company = (item.get("company") or {}).get("display_name")
        location = (item.get("location") or {}).get("display_name")
        return Job(
            source=self.name,
            external_id=str(item["id"]),
            title=title,
            company=company or "não informado",
            url=item.get("redirect_url", ""),
            level=detect_level(title),
            modality=modality_from_text(f"{title} {description}"),
            location=location,
            description=description,
            published_at=parse_date(item.get("created")),
        )