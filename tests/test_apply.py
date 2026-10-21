from jobhunter.apply import approved_jobs
from jobhunter.models import Job
from jobhunter.review import APPLIED, APPROVED
from jobhunter.storage import JobStore


def test_approved_jobs_excludes_applied():
    store = JobStore(":memory:")
    jobs = [
        Job(source="t", external_id=str(i), title="Dev", company="c", url="u") for i in (1, 2, 3)
    ]
    store.add_new(jobs)
    store.set_status("t:1", APPROVED)
    store.set_status("t:2", APPLIED)

    assert [job.uid for job in approved_jobs(store)] == ["t:1"]