from datetime import UTC, date, datetime, timedelta

from jobhunter.digest import (
    APPROVED_TITLE,
    AWAITING_TITLE,
    FRESH_TITLE,
    INCOMPLETE_TITLE,
    NEXT_TEST_TITLE,
    SOON_TITLE,
    WAITING_TITLE,
    build_digest,
)
from jobhunter.match import MatchResult
from jobhunter.models import Job
from jobhunter.storage import JobStore

TODAY = date(2026, 10, 27)


def job(external_id: str, title: str, **kwargs) -> Job:
    return Job(
        source="t", external_id=external_id, title=title, company="Acme Corp", url="u", **kwargs
    )


def score(points: int) -> MatchResult:
    return MatchResult(
        score=points, course_compatible=True, matched_skills=[], missing_skills=[], summary="ok"
    )


def make_store() -> JobStore:
    store = JobStore(":memory:")
    store.add_new(
        [
            job("1", "Estágio Aguardando"),
            job("2", "Estágio Aprovado", deadline=datetime(2026, 10, 29)),
            job("3", "Estágio Excelente"),
            job("4", "Estágio Vencido", deadline=datetime(2026, 10, 1)),
            job("5", "Banco de Talentos Bom"),
        ]
    )
    store.set_status("t:1", "awaiting")
    store.set_status("t:2", "approved")
    store.set_status("t:4", "approved")
    store.save_score("t:3", score(90))
    store.save_score("t:5", score(95))
    return store


def test_digest_lists_what_needs_action(tmp_path):
    text = build_digest(make_store(), today=TODAY, output=tmp_path)

    assert f"{AWAITING_TITLE} (1):" in text
    assert "Estágio Aguardando" in text
    assert f"{APPROVED_TITLE} (1):" in text
    assert f"{SOON_TITLE} (1):" in text
    assert "prazo 29/10" in text
    assert f"{FRESH_TITLE} (1):" in text
    assert "90 | Estágio Excelente" in text
    assert "t:3" in text


def test_digest_skips_expired_talent_pools_and_prepared_jobs(tmp_path):
    (tmp_path / "t_3").mkdir()

    text = build_digest(make_store(), today=TODAY, output=tmp_path)

    assert "Estágio Vencido" not in text
    assert "Banco de Talentos Bom" not in text
    assert FRESH_TITLE not in text


def test_digest_with_nothing_to_do(tmp_path):
    text = build_digest(JobStore(":memory:"), today=TODAY, output=tmp_path)

    assert "Nada pendente hoje." in text


def test_digest_clips_long_lists(tmp_path):
    store = JobStore(":memory:")
    store.add_new([job(str(number), f"Vaga {number}") for number in range(7)])
    for number in range(7):
        store.set_status(f"t:{number}", "awaiting")

    text = build_digest(store, today=TODAY, output=tmp_path)

    assert f"{AWAITING_TITLE} (7):" in text
    assert "... e mais 2" in text


def test_digest_flags_unfinished_gupy_applications(tmp_path):
    store = JobStore(":memory:")
    store.save_gupy_applications(
        [
            {
                "application_id": "1", "company": "Bemobi Wave", "title": "Backend",
                "location": "", "workplace": "Remoto", "contract": "Estágio", "current": 0,
                "total": 6, "tab": "Em andamento", "job_uid": "", "outcome": "",
            }
        ]
    )

    text = build_digest(store, today=TODAY, output=tmp_path)

    assert f"{INCOMPLETE_TITLE} (1):" in text
    assert "Bemobi Wave" in text


def test_digest_lists_applications_without_answer(tmp_path):
    store = JobStore(":memory:")
    store.add_new([job("9", "Estágio Enviado")])
    store.set_status("t:9", "applied")
    later = datetime.now(UTC) + timedelta(days=15)

    text = build_digest(store, today=TODAY, output=tmp_path, now=later)

    assert f"{WAITING_TITLE} (1):" in text
    assert "15 dias | Estágio Enviado" in text

def test_digest_flags_an_upcoming_test_phase(tmp_path):
    store = JobStore(":memory:")
    store.save_gupy_applications(
        [
            {
                "application_id": "1", "company": "Nomus", "title": "Estágio Software",
                "location": "", "workplace": "Remoto", "contract": "Estágio", "current": 1,
                "total": 4, "tab": "Em andamento", "job_uid": "", "outcome": "",
            }
        ]
    )
    store.save_gupy_phases("1", ["Currículo", "Prova técnica", "Entrevista", "Final"])

    text = build_digest(store, today=TODAY, output=tmp_path)

    assert f"{NEXT_TEST_TITLE} (1):" in text
    assert "Nomus | próxima: Prova técnica (1/4)" in text