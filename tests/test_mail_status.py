from jobhunter.mail_status import latest_progress, sync_mail_status
from jobhunter.models import Job
from jobhunter.sheets import HEADERS, ID_COL, STATUS_COL


class FakeWorksheet:
    def __init__(self, rows):
        self.values = [HEADERS, *rows]

    def get_all_values(self):
        return self.values

    def batch_update(self, data):
        for item in data:
            column = ord(item["range"][0]) - ord("A")
            row = int(item["range"][1:]) - 1
            self.values[row][column] = item["values"][0][0]


def sheet_row(uid: str, status: str) -> list[str]:
    row = [""] * len(HEADERS)
    row[ID_COL] = uid
    row[STATUS_COL] = status
    return row


def job(external_id: str, company: str) -> Job:
    return Job(source="t", external_id=external_id, title="Dev", company=company, url="u")


def email(kind: str, company: str, day: int) -> dict:
    return {
        "id": f"m{day}",
        "thread": "t",
        "sent_at": f"2026-10-{day:02d}T12:00:00+00:00",
        "kind": kind,
        "sender": company,
        "subject": "Atualização",
        "company": company,
    }


JOBS = [job("1", "Zenvia Jobs"), job("2", "Nelogica Sistemas")]


def test_latest_email_wins_and_unknown_kinds_are_ignored():
    emails = [
        email("recebida", "Zenvia Jobs", 10),
        email("avançou", "Zenvia Jobs", 12),
        email("verificar", "Zenvia Jobs", 14),
    ]

    assert latest_progress(emails, JOBS) == {"t:1": "Avançou de etapa"}


def test_updates_only_system_statuses():
    ws = FakeWorksheet([sheet_row("t:1", "Enviada"), sheet_row("t:2", "Entrevista")])
    emails = [email("reprovada", "Zenvia Jobs", 12), email("reprovada", "Nelogica Sistemas", 12)]

    assert sync_mail_status(ws, emails, JOBS) == 1
    assert ws.values[1][STATUS_COL] == "Reprovada"
    assert ws.values[2][STATUS_COL] == "Entrevista"  # você anotou à mão: não mexe
    assert sync_mail_status(ws, emails, JOBS) == 0  # estado final não é sobrescrito


def test_ambiguous_company_is_skipped():
    jobs = [job("1", "Michelin Connected"), job("2", "Michelin Fleet")]

    assert latest_progress([email("reprovada", "Michelin", 12)], jobs) == {}


def test_matches_when_the_job_company_has_a_slogan():
    jobs = [job("1", "Venha trabalhar na Zenvia")]

    assert latest_progress([email("recebida", "Zenvia", 12)], jobs) == {
        "t:1": "Recebida pela empresa"
    }