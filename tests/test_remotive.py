import httpx
import respx

from jobhunter.collectors.remotive import API_URL, RemotiveCollector
from jobhunter.models import Level, Modality

FAKE = {
    "jobs": [
        {
            "id": 1,
            "title": "Python Intern",
            "company_name": "Acme",
            "url": "https://remotive.com/job/1",
            "candidate_required_location": "Brazil",
            "salary": "",
            "description": "<p>desc</p>",
            "publication_date": "2026-10-10T12:00:00",
        }
    ]
}


@respx.mock
def test_fetch_normalizes_jobs():
    respx.get(API_URL).mock(return_value=httpx.Response(200, json=FAKE))
    jobs = RemotiveCollector().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.uid == "remotive:1"
    assert job.level == Level.INTERN
    assert job.modality == Modality.REMOTE
    assert job.salary_text is None
    assert job.location == "Brazil"