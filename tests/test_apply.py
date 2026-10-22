from datetime import datetime

from jobhunter.application import Application
from jobhunter.apply import approved_jobs, draft_context, finish_application, page_is_closed
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

def test_draft_context_reads_generated_texts(tmp_path):
    folder = tmp_path / "t_1"
    folder.mkdir()
    app = Application(company_values=[], story_ids=[], why_us="meu texto", cv_summary="resumo",
                      cv_highlights=["h"], salary_answer="A combinar")
    (folder / "draft.json").write_text(app.model_dump_json(), encoding="utf-8")

    assert draft_context("t:1", tmp_path)["why_us"] == "meu texto"
    assert draft_context("t:404", tmp_path) == {}

def test_finish_application_requires_explicit_yes():
    store = JobStore(":memory:")
    store.add_new([make_job("1")])

    assert not finish_application(store, "t:1", "")
    assert store.statuses() == {}
    assert finish_application(store, "t:1", "s")
    assert store.statuses()["t:1"] == "applied"