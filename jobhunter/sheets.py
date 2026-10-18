import os

import gspread

from jobhunter.match import MatchResult
from jobhunter.models import Job

HEADERS = [
    "Vaga", "Empresa", "Cargo", "Salário", "Benefícios", "Modalidade", "Local",
    "Nota", "Resumo da IA", "Prazo", "Etapas", "Status", "Link", "ID",
]
_ETAPAS_COL = chr(ord("A") + HEADERS.index("Etapas"))
_ID_COL = HEADERS.index("ID")


def job_to_row(job: Job, result: MatchResult) -> list[str | int]:
    return [
        job.title,
        job.company,
        job.level.value,
        job.salary_text or "não informado",
        ", ".join(job.benefits) or "não informado",
        job.modality.value,
        job.location or "",
        result.score,
        result.summary,
        job.deadline.strftime("%d/%m/%Y") if job.deadline else "",
        "?/?",
        "Nova",
        job.url,
        job.uid,
    ]


def open_worksheet(title: str = "Vagas") -> gspread.Worksheet:
    client = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS_PATH"])
    spreadsheet = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=len(HEADERS))


def sync(ws: gspread.Worksheet, entries: list[tuple[Job, MatchResult]]) -> int:
    """Acrescenta só as vagas novas, sem mexer nas linhas existentes (Status e Etapas são seus)."""
    values = ws.get_all_values()
    if not values:
        ws.update(range_name="A1", values=[HEADERS])
        ws.freeze(rows=1)
        # Etapas como texto, para o Sheets não transformar "1/7" em data
        ws.format(f"{_ETAPAS_COL}2:{_ETAPAS_COL}", {"numberFormat": {"type": "TEXT"}})
        existing: set[str] = set()
    else:
        existing = {row[_ID_COL] for row in values[1:] if len(row) > _ID_COL}
    new_rows = [job_to_row(job, result) for job, result in entries if job.uid not in existing]
    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
    return len(new_rows)