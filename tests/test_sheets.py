from datetime import date, datetime

from jobhunter.match import MatchResult
from jobhunter.models import Job
from jobhunter.sheets import (
    HEADERS,
    ID_COL,
    MAIL_HEADERS,
    STATUS_COL,
    job_to_row,
    mark_expired,
    match_job,
    reset_sheet,
    sync,
    sync_mail,
    sync_statuses,
)


class FakeSpreadsheet:
    def __init__(self):
        self.requests: list[dict] = []

    def batch_update(self, body):
        self.requests.extend(body["requests"])


class FakeWorksheet:
    id = 7

    def __init__(self):
        self.values: list[list[str]] = []
        self.spreadsheet = FakeSpreadsheet()

    def get_all_values(self):
        return self.values

    def update(self, range_name, values):
        self.values[: len(values)] = [list(row) for row in values]

    def insert_rows(self, rows, row):
        self.values[row - 1 : row - 1] = [list(r) for r in rows]

    def append_rows(self, rows, value_input_option):
        self.values.extend([[str(cell) for cell in row] for row in rows])

    def clear(self):
        self.values = []

    def batch_update(self, data):
        for item in data:
            column = ord(item["range"][0]) - ord("A")
            row = int(item["range"][1:]) - 1
            self.values[row][column] = item["values"][0][0]


def make(external_id: str, score: int):
    job = Job(source="t", external_id=external_id, title="Dev", company="Acme", url="u",
              deadline=datetime(2026, 11, 30), published_at=datetime(2026, 10, 1))
    result = MatchResult(score=score, course_compatible=True, matched_skills=[],
                         missing_skills=[], summary="ok")
    return job, result


def test_sync_appends_only_new_jobs():
    ws = FakeWorksheet()
    entries = [make("1", 90), make("2", 70)]

    assert sync(ws, entries) == 2
    assert ws.values[0] == HEADERS
    assert len(ws.values) == 3

    assert sync(ws, [*entries, make("3", 80)]) == 1
    assert ws.values[-1][ID_COL] == "t:3"


def test_sync_inserts_header_when_missing():
    ws = FakeWorksheet()
    ws.values = [["Vaga antiga", "x"]]
    sync(ws, [make("1", 90)])

    assert ws.values[0] == HEADERS
    assert ws.values[1][0] == "Vaga antiga"
    assert len(ws.values) == 3


def test_sync_refreshes_old_header_names():
    ws = FakeWorksheet()
    ws.values = [["Vaga"] + ["x"] * (ID_COL - 1) + ["ID"]]
    sync(ws, [make("1", 90)])

    assert ws.values[0] == HEADERS
    assert len(ws.values) == 2


def test_reset_sheet_clears_values_and_formatting():
    ws = FakeWorksheet()
    ws.values = [["lixo"]]
    reset_sheet(ws)

    assert ws.values == []
    request = ws.spreadsheet.requests[0]["updateCells"]
    assert request["fields"] == "userEnteredFormat"
    assert request["range"] == {"sheetId": 7}

def test_mark_expired_marks_only_new_rows():
    ws = FakeWorksheet()
    sync(ws, [make("1", 90)])  # prazo 30/11/2026

    assert mark_expired(ws, today=date(2026, 12, 1)) == 1
    assert ws.values[1][STATUS_COL] == "Encerrada"


def test_mark_expired_respects_manual_status():
    ws = FakeWorksheet()
    sync(ws, [make("1", 90)])
    ws.values[1][STATUS_COL] = "Enviada"

    assert mark_expired(ws, today=date(2026, 12, 1)) == 0
    assert ws.values[1][STATUS_COL] == "Enviada"

def test_sync_statuses_updates_system_labels_only():
    ws = FakeWorksheet()
    sync(ws, [make("1", 90), make("2", 80), make("3", 70)])
    ws.values[3][STATUS_COL] = "Entrevista"

    updated = sync_statuses(ws, {"t:1": "approved", "t:2": "applied", "t:3": "discarded"})

    assert updated == 2
    assert ws.values[1][STATUS_COL] == "Aprovada"
    assert ws.values[2][STATUS_COL] == "Enviada"
    assert ws.values[3][STATUS_COL] == "Entrevista"

def test_row_includes_publication_date():
    job, result = make("1", 90)

    assert job_to_row(job, result)[HEADERS.index("Publicada")] == "01/10/2026"

def test_match_job_requires_a_single_company_match():
    jobs = [
        Job(source="t", external_id="1", title="Dev", company="Vendemmia Logística Integrada",
            url="u"),
        Job(source="t", external_id="2", title="QA", company="Michelin", url="u"),
        Job(source="t", external_id="3", title="Dev", company="Michelin", url="u"),
    ]

    assert match_job("Vendemmia Logística Integrada", "Inscrição recebida", jobs) == "t:1"
    assert match_job("Michelin", "x", jobs) == ""  # ambígua: duas vagas da mesma empresa
    assert match_job("Outra", "x", jobs) == ""


def test_sync_mail_appends_new_emails_only():
    ws = FakeWorksheet()
    emails = [{
        "id": "m1", "thread": "t", "sent_at": "2026-10-21T13:00:00+00:00",
        "kind": "reprovada", "sender": "ITAU", "subject": "Reprovação", "company": "ITAU",
    }]

    assert sync_mail(ws, emails, []) == 1
    assert sync_mail(ws, emails, []) == 0
    assert ws.values[0] == MAIL_HEADERS
    assert ws.values[1][1] == "reprovada"

def test_match_job_matches_company_with_slogan():
    jobs = [
        Job(source="t", external_id="1", title="Dev", company="Venha trabalhar na Zenvia", url="u")
    ]

    assert match_job("Zenvia", "Inscrição recebida", jobs) == "t:1"