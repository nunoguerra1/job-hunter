from datetime import date, datetime

from jobhunter.filters import is_open, prefilter
from jobhunter.models import Job
from jobhunter.profile import load_profile

PROFILE = load_profile("profile/profile.example.yaml")
TODAY = date(2026, 10, 15)


def make_job(title: str, **kwargs) -> Job:
    return Job(source="t", external_id="1", title=title, company="c", url="u", **kwargs)


def test_keeps_dev_job():
    result = prefilter(make_job("Estágio em Desenvolvimento Full Stack"), PROFILE, TODAY)
    assert result.keep and result.area == "desenvolvimento"


def test_rejects_support():
    result = prefilter(make_job("Estágio em Suporte Técnico de TI"), PROFILE, TODAY)
    assert not result.keep and "suporte" in result.reason


def test_rejects_pcd():
    assert not prefilter(make_job("Estágio Desenvolvedor", pcd=True), PROFILE, TODAY).keep


def test_rejects_expired():
    job = make_job("Estágio Desenvolvedor", deadline=datetime(2026, 1, 1))
    assert prefilter(job, PROFILE, TODAY).reason == "prazo vencido"


def test_rejects_non_it():
    job = make_job("Estágio Superior Não Obrigatório (Desenvolvimento Humano)")
    assert prefilter(job, PROFILE, TODAY).reason == "fora de TI"


def test_rejects_senior():
    assert not prefilter(make_job("Desenvolvedor Python Sênior"), PROFILE, TODAY).keep


def test_keeps_by_description_skills():
    job = make_job("Estágio no time de Produto", description="Stack: Python, React e SQL")
    result = prefilter(job, PROFILE, TODAY)
    assert result.keep and "descrição" in result.area

def test_is_open_compares_with_deadline():
    assert not is_open(make_job("x", deadline=datetime(2026, 10, 14)), TODAY)
    assert is_open(make_job("x", deadline=datetime(2026, 10, 15)), TODAY)
    assert is_open(make_job("x"), TODAY)  # sem prazo informado