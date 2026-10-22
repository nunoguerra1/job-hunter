import httpx
import respx

from jobhunter.collectors.adzuna import API_URL, AdzunaCollector
from jobhunter.models import Modality

FAKE = {
    "results": [
        {
            "id": "111",
            "title": "Estágio em <strong>Desenvolvimento</strong> Python",
            "company": {"display_name": "Acme"},
            "location": {"display_name": "São Paulo, SP"},
            "description": "Vaga <strong>home office</strong> para estudantes",
            "redirect_url": "https://www.adzuna.com.br/land/ad/111",
            "created": "2026-10-20T10:00:00Z",
        },
        {"id": "222", "title": "Desenvolvedor Sênior", "company": {"display_name": "X"}},
    ]
}


@respx.mock
def test_adzuna_cleans_filters_and_dedups():
    respx.get(API_URL.format(page=1)).mock(return_value=httpx.Response(200, json=FAKE))
    collector = AdzunaCollector("ID", "KEY", ["estágio", "python"], max_pages=1, delay=0)
    jobs = collector.fetch()

    assert len(jobs) == 1  # a vaga sênior sai e a repetida nas duas consultas conta uma vez
    job = jobs[0]
    assert job.uid == "adzuna:111"
    assert job.title == "Estágio em Desenvolvimento Python"
    assert job.modality == Modality.REMOTE
    assert job.company == "Acme"


@respx.mock
def test_adzuna_error_does_not_leak_credentials():
    respx.get(API_URL.format(page=1)).mock(return_value=httpx.Response(401, json={}))
    collector = AdzunaCollector("ID", "SECRETKEY", ["estágio"], max_pages=1, delay=0)

    assert collector.fetch() == []
    assert collector.errors == ["adzuna 'estágio': HTTPStatusError"]
    assert "SECRETKEY" not in " ".join(collector.errors)