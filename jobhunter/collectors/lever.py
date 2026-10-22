import time

import httpx

from jobhunter.classify import detect_level
from jobhunter.collectors.base import Collector
from jobhunter.collectors.common import (
    accepts_location,
    from_millis,
    is_entry_level,
    modality_from_text,
)
from jobhunter.models import Job, Modality
from jobhunter.sources import Board

API_URL = "https://api.lever.co/v0/postings/{site}"

_WORKPLACE = {
    "remote": Modality.REMOTE,
    "hybrid": Modality.HYBRID,
    "on-site": Modality.ONSITE,
}


class LeverCollector(Collector):
    name = "lever"

    def __init__(
        self, boards: list[Board], delay: float = 0.5, client: httpx.Client | None = None
    ):
        self.boards = boards
        self.delay = delay
        self.client = client or httpx.Client(timeout=30)
        self.errors: list[str] = []

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        for board in self.boards:
            try:
                response = self.client.get(
                    API_URL.format(site=board.token), params={"mode": "json"}
                )
                response.raise_for_status()
                items = response.json()
                if not isinstance(items, list):
                    raise ValueError("resposta inesperada")
            except (httpx.HTTPError, ValueError) as error:
                self.errors.append(f"lever/{board.token}: {type(error).__name__}")
                continue
            jobs.extend(self._to_jobs(board, items))
            time.sleep(self.delay)
        return jobs

    def _to_jobs(self, board: Board, items: list[dict]) -> list[Job]:
        jobs = []
        for item in items:
            title = item.get("text", "")
            categories = item.get("categories") or {}
            locations = [categories.get("location") or "", *(categories.get("allLocations") or [])]
            if not item.get("id") or not is_entry_level(title):
                continue
            if not board.any_location and not any(accepts_location(loc) for loc in locations):
                continue
            modality = _WORKPLACE.get(item.get("workplaceType") or "") or modality_from_text(
                " ".join(locations)
            )
            jobs.append(
                Job(
                    source=self.name,
                    external_id=f"{board.token}-{item['id']}",
                    title=title,
                    company=board.company or board.token,
                    url=item.get("hostedUrl", ""),
                    level=detect_level(title),
                    modality=modality,
                    location=categories.get("location") or None,
                    description=item.get("descriptionPlain") or item.get("description", ""),
                    published_at=from_millis(item.get("createdAt")),
                )
            )
        return jobs