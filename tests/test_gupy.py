import httpx
import respx

from jobhunter.collectors.gupy import API_URL, GupyCollector
from jobhunter.models import Level, Modality

FAKE = {
    "data": [
        {
            "id": 100,
            "name": "Estagiário de Dados",
            "careerPageName": "Empresa X",
            "jobUrl": "https://empresax.gupy.io/job/abc",
            "workplaceType": "hybrid",
            "city": "Curitiba",
            "state": "Paraná",
            "type": "vacancy_type_internship",
            "publishedDate": "2026-10-10T12:00:00.000Z",
            "description": "desc",
            "applicationDeadline": "2026-11-30T00:00:00.000Z",
            "disabilities": True,
        }
    ]
}


@respx.mock
def test_fetch_normalizes_and_dedups():
    respx.get(API_URL).mock(return_value=httpx.Response(200, json=FAKE))
    collector = GupyCollector(keywords=["estágio", "dados"], max_pages=1, delay=0)
    jobs = collector.fetch()

    assert len(jobs) == 1  # mesma vaga nas duas palavras-chave
    job = jobs[0]
    assert job.uid == "gupy:100"
    assert job.level == Level.INTERN
    assert job.modality == Modality.HYBRID
    assert job.location == "Curitiba, Paraná"
    assert job.company == "Empresa X"
    assert job.deadline is not None
    assert job.pcd is True