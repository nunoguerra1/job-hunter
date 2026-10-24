from jobhunter.mail import link_report, to_records
from jobhunter.models import Job
from jobhunter.storage import JobStore

ROWS = [
    {"id": "1", "thread": "t1", "from": "ITAU UNIBANCO S.A. <rh@itau.com.br>",
     "subject": "Reprovação etapa de testes - Estágio Itaú 2026",
     "date": "Wed, 21 Oct 2026 10:00:00 -0300", "snippet": ""},
    {"id": "2", "thread": "t2", "from": "DIO <contato@dio.me>",
     "subject": "Nuno, treine a entrevista da sua primeira vaga",
     "date": "Wed, 21 Oct 2026 11:00:00 -0300", "snippet": ""},
]


def test_to_records_drops_noise_and_keeps_kind():
    records = to_records(ROWS, "eu@gmail.com")

    assert [record["id"] for record in records] == ["1"]
    assert records[0]["kind"] == "reprovada"
    assert records[0]["company"] == "ITAU UNIBANCO S.A."
    assert records[0]["sent_at"] == "2026-10-21T13:00:00+00:00"


def test_emails_are_stored_once():
    store = JobStore(":memory:")
    records = to_records(ROWS, "eu@gmail.com")

    assert store.add_emails(records) == 1
    assert store.add_emails(records) == 0
    assert store.emails()[0]["kind"] == "reprovada"


def email_record(email_id: str, company: str) -> dict:
    return {
        "id": email_id,
        "thread": "t",
        "sent_at": "2026-10-21T13:00:00+00:00",
        "kind": "recebida",
        "sender": company,
        "subject": "Inscrição recebida",
        "company": company,
    }


def test_link_report_shows_matches_and_gaps(capsys):
    store = JobStore(":memory:")
    job = Job(source="t", external_id="1", title="Estágio Dev", company="Zenvia Jobs", url="u")
    store.add_new([job])
    store.add_emails([email_record("1", "Zenvia Jobs"), email_record("2", "Outra Empresa")])

    link_report(store)
    out = capsys.readouterr().out

    assert "-> t:1" in out
    assert "sem correspondência única" in out