import httpx
import respx

from jobhunter.collectors.greenhouse import API_URL, GreenhouseCollector
from jobhunter.models import Level, Modality
from jobhunter.sources import Board

FAKE = {
    "jobs": [
        {
            "id": 1,
            "title": "Software Engineer Intern",
            "location": {"name": "Remote - Brazil"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "content": "&lt;p&gt;Python e SQL&lt;/p&gt;",
            "updated_at": "2026-10-20T10:00:00-03:00",
        },
        {"id": 2, "title": "Senior Engineer", "location": {"name": "Remote - Brazil"}},
        {"id": 3, "title": "Engineering Intern", "location": {"name": "Austin, TX"}},
    ]
}


@respx.mock
def test_filters_level_and_location():
    respx.get(API_URL.format(token="acme")).mock(return_value=httpx.Response(200, json=FAKE))
    jobs = GreenhouseCollector([Board(token="acme", company="Acme")], delay=0).fetch()

    assert [job.uid for job in jobs] == ["greenhouse:acme-1"]
    job = jobs[0]
    assert job.level == Level.INTERN
    assert job.modality == Modality.REMOTE
    assert job.company == "Acme"
    assert "<p>Python e SQL</p>" in job.description


@respx.mock
def test_any_location_keeps_other_cities():
    respx.get(API_URL.format(token="acme")).mock(return_value=httpx.Response(200, json=FAKE))
    jobs = GreenhouseCollector([Board(token="acme", any_location=True)], delay=0).fetch()

    assert sorted(job.uid for job in jobs) == ["greenhouse:acme-1", "greenhouse:acme-3"]


@respx.mock
def test_missing_board_is_reported_not_fatal():
    respx.get(API_URL.format(token="gone")).mock(return_value=httpx.Response(404, json={}))
    respx.get(API_URL.format(token="acme")).mock(return_value=httpx.Response(200, json=FAKE))
    collector = GreenhouseCollector([Board(token="gone"), Board(token="acme")], delay=0)

    assert len(collector.fetch()) == 1
    assert collector.errors == ["greenhouse/gone: HTTPStatusError"]