from datetime import datetime

from jobhunter.answers import Plan
from jobhunter.application import Application
from jobhunter.apply import (
    approved_jobs,
    draft_context,
    finish_application,
    gaps,
    is_gupy_url,
    log_unanswered,
    page_is_closed,
    status_report,
)
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


def test_is_gupy_url():
    assert is_gupy_url("https://vendemmia.gupy.io/job/abc")
    assert is_gupy_url("https://portal.gupy.io/")
    assert not is_gupy_url("https://www.adzuna.com.br/land/ad/1")
    assert not is_gupy_url("https://evilgupy.io/x")


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


def test_status_report_lists_applied(capsys):
    store = JobStore(":memory:")
    store.add_new([make_job("1"), make_job("2")])
    store.set_status("t:1", APPLIED)
    store.set_status("t:2", APPROVED)

    status_report(store)
    out = capsys.readouterr().out

    assert "applied 1" in out
    assert "Enviadas" in out
    assert "t:1" in out


def test_log_unanswered_and_gaps(tmp_path, capsys):
    path = tmp_path / "unanswered.jsonl"
    plans = [
        Plan("k1", "single", "Você tem CNH?", "human", [], "assunto sensível: responda você"),
        Plan("k2", "single", "Quanto tempo de Python?", "human", [], "sem regra"),
    ]
    questions = [{"key": "k2", "options": ["Menos de 1 ano", "Mais de 1 ano"]}]

    assert log_unanswered(plans, questions, path) == 1
    log_unanswered(plans, questions, path)
    gaps(path)
    out = capsys.readouterr().out

    assert "2x | Quanto tempo de Python?" in out
    assert "Mais de 1 ano" in out
    assert "CNH" not in out