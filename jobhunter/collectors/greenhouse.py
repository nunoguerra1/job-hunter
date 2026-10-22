import html
import time

import httpx

from jobhunter.classify import detect_level
from jobhunter.collectors.base import Collector
from jobhunter.collectors.common import (
    accepts_location,
    is_entry_level,
    modality_from_text,
    parse_date,
)
from jobhunter.models import Job
from jobhunter.sources import Board

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseCollector(Collector):
    name = "greenhouse"

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
                    API_URL.format(token=board.token), params={"content": "true"}
                )
                response.raise_for_status()
                items = response.json().get("jobs", [])
            except (httpx.HTTPError, ValueError) as error:
                self.errors.append(f"greenhouse/{board.token}: {type(error).__name__}")
                continue
            jobs.extend(self._to_jobs(board, items))
            time.sleep(self.delay)
        return jobs

    def _to_jobs(self, board: Board, items: list[dict]) -> list[Job]:
        jobs = []
        for item in items:
            title = item.get("title", "")
            location = (item.get("location") or {}).get("name", "")
            if item.get("id") is None or not is_entry_level(title):
                continue
            if not board.any_location and not accepts_location(location):
                continue
            jobs.append(
                Job(
                    source=self.name,
                    external_id=f"{board.token}-{item['id']}",
                    title=title,
                    company=board.company or board.token,
                    url=item.get("absolute_url", ""),
                    level=detect_level(title),
                    modality=modality_from_text(f"{location} {title}"),
                    location=location or None,
                    description=html.unescape(item.get("content", "")),
                    published_at=parse_date(item.get("updated_at")),
                )
            )
        return jobs