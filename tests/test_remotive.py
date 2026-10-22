import httpx
import respx

from jobhunter.collectors.remotive import API_URL, RemotiveCollector
from jobhunter.models import Level, Modality


def item(job_id: int, title: str, location: str) -> dict:
    return {
        "id": job_id,
        "title": title,
        "company_name": "Acme",
        "url": f"https://remotive.com/job/{job_id}",
        "candidate_required_location": location,
        "salary": "",
        "description": "<p>desc</p>",
        "publication_date": "2026-10-10T12:00:00",
    }


@respx.mock
def test_fetch_normalizes_jobs():
    payload = {"jobs": [item(1, "Python Intern", "Brazil")]}
    respx.get(API_URL).mock(return_value=httpx.Response(200, json=payload))
    jobs = RemotiveCollector().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.uid == "remotive:1"
    assert job.level == Level.INTERN
    assert job.modality == Modality.REMOTE
    assert job.salary_text is None
    assert job.location == "Brazil"


@respx.mock
def test_keeps_only_entry_level_in_reachable_locations():
    payload = {
        "jobs": [
            item(1, "Python Intern", "Worldwide"),
            item(2, "Senior Engineer", "Worldwide"),
            item(3, "Backend Intern", "USA Only"),
        ]
    }
    respx.get(API_URL).mock(return_value=httpx.Response(200, json=payload))

    assert [job.uid for job in RemotiveCollector().fetch()] == ["remotive:1"]