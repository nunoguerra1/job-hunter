from jobhunter.mail import to_records
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