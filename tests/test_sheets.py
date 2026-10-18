from datetime import datetime

from jobhunter.match import MatchResult
from jobhunter.models import Job
from jobhunter.sheets import HEADERS, ID_COL, sync


class FakeWorksheet:
    def __init__(self):
        self.values: list[list[str]] = []

    def get_all_values(self):
        return self.values

    def update(self, range_name, values):
        self.values[: len(values)] = [list(row) for row in values]

    def insert_rows(self, rows, row):
        self.values[row - 1 : row - 1] = [list(r) for r in rows]

    def append_rows(self, rows, value_input_option):
        self.values.extend([[str(cell) for cell in row] for row in rows])


def make(external_id: str, score: int):
    job = Job(source="t", external_id=external_id, title="Dev", company="Acme", url="u",
              deadline=datetime(2026, 11, 30))
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