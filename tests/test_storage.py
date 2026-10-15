from jobhunter.models import Job
from jobhunter.storage import JobStore


def _job(external_id: str) -> Job:
    return Job(source="t", external_id=external_id, title="Dev", company="Acme", url="u")


def test_add_new_ignores_duplicates():
    store = JobStore(":memory:")
    assert len(store.add_new([_job("1"), _job("2")])) == 2
    assert len(store.add_new([_job("2"), _job("3")])) == 1
    assert len(store.all()) == 3