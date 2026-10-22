import httpx
import respx

from jobhunter.collectors.lever import API_URL, LeverCollector
from jobhunter.models import Modality
from jobhunter.sources import Board

FAKE = [
    {
        "id": "abc",
        "text": "Estágio em Desenvolvimento",
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "createdAt": 1792000000000,
        "workplaceType": "remote",
        "categories": {"location": "Brazil", "allLocations": ["Brazil"]},
        "descriptionPlain": "Python, SQL e APIs",
    },
    {"id": "def", "text": "Staff Engineer", "categories": {"location": "Brazil"}},
    {"id": "ghi", "text": "Intern", "categories": {"location": "Berlin"}},
]


@respx.mock
def test_lever_filters_and_normalizes():
    respx.get(API_URL.format(site="acme")).mock(return_value=httpx.Response(200, json=FAKE))
    jobs = LeverCollector([Board(token="acme", company="Acme")], delay=0).fetch()

    assert [job.uid for job in jobs] == ["lever:acme-abc"]
    job = jobs[0]
    assert job.modality == Modality.REMOTE
    assert job.published_at is not None
    assert job.description == "Python, SQL e APIs"


@respx.mock
def test_lever_error_payload_is_reported():
    respx.get(API_URL.format(site="gone")).mock(
        return_value=httpx.Response(200, json={"ok": False})
    )
    collector = LeverCollector([Board(token="gone")], delay=0)

    assert collector.fetch() == []
    assert collector.errors == ["lever/gone: ValueError"]