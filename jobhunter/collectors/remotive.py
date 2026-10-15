from datetime import datetime

import httpx

from jobhunter.classify import detect_level
from jobhunter.collectors.base import Collector
from jobhunter.models import Job, Modality

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveCollector(Collector):
    name = "remotive"

    def __init__(self, category: str = "software-dev", search: str = "",
                 client: httpx.Client | None = None):
        self.category = category
        self.search = search
        self.client = client or httpx.Client(timeout=30)

    def fetch(self) -> list[Job]:
        response = self.client.get(
            API_URL, params={"category": self.category, "search": self.search}
        )
        response.raise_for_status()
        return [self._to_job(item) for item in response.json().get("jobs", [])]

    def _to_job(self, item: dict) -> Job:
        published = item.get("publication_date")
        return Job(
            source=self.name,
            external_id=str(item["id"]),
            title=item["title"],
            company=item["company_name"],
            url=item["url"],
            level=detect_level(item["title"]),
            modality=Modality.REMOTE,
            location=item.get("candidate_required_location") or None,
            salary_text=item.get("salary") or None,
            description=item.get("description", ""),
            published_at=datetime.fromisoformat(published) if published else None,
        )