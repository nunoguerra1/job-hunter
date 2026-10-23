from datetime import UTC, datetime, timedelta

from jobhunter.followups import due_followups
from jobhunter.models import Job
from jobhunter.review import APPLIED
from jobhunter.storage import JobStore


def make_store() -> JobStore:
    store = JobStore(":memory:")
    job = Job(source="t", external_id="1", title="Dev", company="Zenvia Jobs", url="u")
    store.add_new([job])
    store.set_status("t:1", APPLIED)
    return store


def news_email(sent_at: datetime) -> dict:
    return {
        "id": "m1",
        "thread": "t",
        "sent_at": sent_at.isoformat(),
        "kind": "avançou",
        "sender": "Zenvia",
        "subject": "Atualização",
        "company": "Zenvia Jobs",
    }


def test_applied_job_without_news_is_due():
    store = make_store()
    later = datetime.now(UTC) + timedelta(days=15)

    due = due_followups(store, days=10, now=later)

    assert [(job.uid, waited) for job, waited in due] == [("t:1", 15)]


def test_recent_application_is_not_due():
    store = make_store()

    assert due_followups(store, days=10, now=datetime.now(UTC) + timedelta(days=3)) == []


def test_news_after_applying_clears_the_follow_up():
    store = make_store()
    store.add_emails([news_email(datetime.now(UTC) + timedelta(days=2))])

    assert due_followups(store, days=10, now=datetime.now(UTC) + timedelta(days=15)) == []


def test_old_news_before_applying_does_not_count():
    store = make_store()
    store.add_emails([news_email(datetime.now(UTC) - timedelta(days=30))])

    assert len(due_followups(store, days=10, now=datetime.now(UTC) + timedelta(days=15))) == 1