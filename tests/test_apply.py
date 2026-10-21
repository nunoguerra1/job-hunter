from datetime import datetime

from jobhunter.apply import approved_jobs, page_is_closed
from jobhunter.models import Job
from jobhunter.review import APPLIED, APPROVED
from jobhunter.storage import JobStore


def make_job(external_id: str, **kwargs) -> Job:
    return Job(source="t", external_id=external_id, title="Dev", company="c", url="u", **kwargs)


def test_approved_jobs_excludes_applied():
    store = JobStore(":memory:")
    store.add_new([make_job(str(i)) for i in (1, 2, 3)])
    store.set_status("t:1", APPROVED)
    store.set_status("t:2", APPLIED)

    assert [job.uid for job in approved_jobs(store)] == ["t:1"]


def test_approved_jobs_hides_expired():
    store = JobStore(":memory:")
    store.add_new([make_job("1", deadline=datetime(2020, 1, 1))])
    store.set_status("t:1", APPROVED)

    assert approved_jobs(store) == []


def test_page_is_closed():
    assert page_is_closed("Candidaturas encerradas\nEstágio em Tecnologia")
    assert page_is_closed("INSCRIÇÕES ENCERRADAS")
    assert not page_is_closed("Candidatar-se agora. Inscrições até 28/10")