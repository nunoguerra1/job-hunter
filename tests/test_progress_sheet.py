from jobhunter.progress_sheet import (
    GUPY_HEADERS,
    stage_text,
    sync_gupy_tab,
    sync_outcomes,
    sync_progress,
)
from jobhunter.sheets import ETAPAS_COL, HEADERS, ID_COL, STATUS_COL

REJECTED = "Você não avançou nesse processo"
CLOSED = "Vaga encerrada pela empresa"


class FakeWorksheet:
    def __init__(self, rows=()):
        self.values = [HEADERS, *rows]
        self.formats = []

    def get_all_values(self):
        return self.values

    def batch_update(self, data):
        for item in data:
            column = ord(item["range"][0]) - ord("A")
            row = int(item["range"][1:]) - 1
            self.values[row][column] = item["values"][0][0]

    def clear(self):
        self.values = []

    def format(self, range_name, fmt):
        self.formats.append(range_name)

    def update(self, range_name, values):
        self.values = [list(row) for row in values]


def sheet_row(uid: str, stage: str = "", status: str = "") -> list[str]:
    row = [""] * len(HEADERS)
    row[ID_COL] = uid
    row[ETAPAS_COL] = stage
    row[STATUS_COL] = status
    return row


def application(**kwargs) -> dict:
    base = {
        "application_id": "10", "company": "Zenvia", "title": "Dev", "location": "-",
        "workplace": "Remoto", "contract": "Efetivo", "current": 1, "total": 7,
        "tab": "Em andamento", "job_uid": "gupy:1", "outcome": "",
    }
    return {**base, **kwargs}


def test_stage_text():
    assert stage_text(application()) == "1/7"
    assert stage_text(application(current=None, total=None)) == ""


def test_sync_progress_writes_only_system_values():
    ws = FakeWorksheet([
        sheet_row("gupy:1", "?/?"),
        sheet_row("gupy:2", "Entrevista marcada"),
        sheet_row("gupy:3", "1/7"),
    ])
    apps = [
        application(),
        application(application_id="11", job_uid="gupy:2"),
        application(application_id="12", job_uid="gupy:3", current=2),
    ]

    assert sync_progress(ws, apps) == 2
    assert ws.values[1][ETAPAS_COL] == "1/7"
    assert ws.values[2][ETAPAS_COL] == "Entrevista marcada"
    assert ws.values[3][ETAPAS_COL] == "2/7"
    assert sync_progress(ws, apps) == 0


def test_sync_outcomes_only_changes_system_statuses():
    ws = FakeWorksheet([
        sheet_row("gupy:1", status="Enviada"),
        sheet_row("gupy:2", status="Entrevista"),
        sheet_row("gupy:3", status="Enviada"),
    ])
    apps = [
        application(job_uid="gupy:1", outcome=REJECTED),
        application(application_id="11", job_uid="gupy:2", outcome=REJECTED),
        application(application_id="12", job_uid="gupy:3", outcome=CLOSED),
    ]

    assert sync_outcomes(ws, apps) == 2
    assert ws.values[1][STATUS_COL] == "Reprovada"
    assert ws.values[2][STATUS_COL] == "Entrevista"
    assert ws.values[3][STATUS_COL] == "Encerrada"
    assert sync_outcomes(ws, apps) == 0


def test_sync_gupy_tab_rewrites_everything_as_text():
    ws = FakeWorksheet()
    apps = [application(outcome=REJECTED)]
    phases = {"10": ["Currículo", "Pré-entrevista"]}

    assert sync_gupy_tab(ws, apps, phases) == 1
    assert ws.values[0] == GUPY_HEADERS
    assert ws.values[1][5] == "1/7"
    assert ws.values[1][6] == "Currículo"
    assert ws.values[1][7] == "Pré-entrevista"
    assert ws.values[1][9] == REJECTED
    assert "F2:F" in ws.formats

def test_gupy_tab_flags_unfinished_applications():
    ws = FakeWorksheet()

    sync_gupy_tab(ws, [application(current=0, total=4)], {"10": ["Currículo", "Entrevista"]})

    assert ws.values[1][6] == "Candidatura incompleta"
    assert ws.values[1][7] == "Currículo"