from jobhunter.models import Job, Level, Modality


def test_job_uid_combines_source_and_id():
    job = Job(source="remotive", external_id="42", title="Dev", company="Acme",
              url="https://example.com/42")
    assert job.uid == "remotive:42"


def test_job_defaults():
    job = Job(source="x", external_id="1", title="t", company="c", url="u")
    assert job.level == Level.OTHER
    assert job.modality == Modality.UNKNOWN
    assert job.benefits == []