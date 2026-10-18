from jobhunter.match import MatchResult
from jobhunter.models import Job
from jobhunter.storage import JobStore


def _job(external_id: str) -> Job:
    return Job(source="t", external_id=external_id, title="Dev", company="Acme", url="u")


def test_add_new_ignores_duplicates():
    store = JobStore(":memory:")
    assert len(store.add_new([_job("1"), _job("2")])) == 2
    assert len(store.add_new([_job("2"), _job("3")])) == 1
    assert len(store.all()) == 3

def test_save_and_load_score():
    store = JobStore(":memory:")
    result = MatchResult(
        score=80, course_compatible=True, matched_skills=[], missing_skills=[], summary="ok"
    )
    store.save_score("t:1", result)
    assert store.scores()["t:1"].score == 80

def test_status_roundtrip():
    store = JobStore(":memory:")
    store.set_status("t:1", "awaiting")
    store.set_status("t:1", "approved")
    assert store.statuses() == {"t:1": "approved"}