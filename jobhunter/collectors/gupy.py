import time
from datetime import datetime

import httpx

from jobhunter.classify import detect_level
from jobhunter.collectors.base import Collector
from jobhunter.models import Job, Level, Modality

API_URL = "https://portal.gupy.io/api/job-search/jobs"
PAGE_SIZE = 10

_MODALITY = {
    "remote": Modality.REMOTE,
    "hybrid": Modality.HYBRID,
    "on-site": Modality.ONSITE,
}


class GupyCollector(Collector):
    name = "gupy"

    def __init__(
        self,
        keywords: list[str],
        workplace_type: str | None = None,
        max_pages: int = 3,
        delay: float = 1.0,
        client: httpx.Client | None = None,
    ):
        self.keywords = keywords
        self.workplace_type = workplace_type
        self.max_pages = max_pages
        self.delay = delay
        self.client = client or httpx.Client(timeout=30)

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for keyword in self.keywords:
            for page in range(self.max_pages):
                params = {"jobName": keyword, "limit": PAGE_SIZE, "offset": page * PAGE_SIZE}
                if self.workplace_type:
                    params["workplaceType"] = self.workplace_type
                response = self.client.get(API_URL, params=params)
                response.raise_for_status()
                payload = response.json()
                if "data" not in payload:
                    raise ValueError(f"Resposta da Gupy fora do formato esperado: {list(payload)}")
                data = payload["data"]
                for item in data:
                    job = self._to_job(item)
                    jobs[job.uid] = job
                if len(data) < PAGE_SIZE:
                    break
                time.sleep(self.delay)
        return list(jobs.values())

    def _to_job(self, item: dict) -> Job:
        title = item.get("name", "")
        level = Level.INTERN if "internship" in str(item.get("type", "")) else detect_level(title)
        modality = _MODALITY.get(item.get("workplaceType") or "", Modality.UNKNOWN)
        location = ", ".join(p for p in (item.get("city"), item.get("state")) if p)
        return Job(
            source=self.name,
            external_id=str(item["id"]),
            title=title,
            company=item.get("careerPageName") or item.get("companyName") or "não informado",
            url=item.get("jobUrl") or item.get("applyUrl") or "",
            level=level,
            modality=modality,
            location=location or None,
            description=item.get("description", ""),
            published_at=_parse_date(item.get("publishedDate")),
            deadline=_parse_date(item.get("applicationDeadline")),
            pcd=bool(item.get("disabilities")),
        )


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None