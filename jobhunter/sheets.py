import os
from pathlib import Path

import gspread

from jobhunter.cost import CostTable, brl, estimate
from jobhunter.extract import extract_benefits, extract_salary
from jobhunter.match import MatchResult
from jobhunter.models import Job

HEADERS = [
    "Título", "Empresa", "Tipo de cargo", "Salário", "Benefícios", "Modalidade", "Local",
    "Custo de vida/mês", "Sobra estimada", "Nota", "Resumo da IA", "Prazo", "Etapas",
    "Status", "Link", "ID",
]
ID_COL = HEADERS.index("ID")
ETAPAS_COL = HEADERS.index("Etapas")
SUMMARY_COL = HEADERS.index("Resumo da IA")

COLUMN_WIDTHS = {
    "Título": 320, "Empresa": 200, "Tipo de cargo": 110, "Salário": 150,
    "Benefícios": 230, "Modalidade": 110, "Local": 200, "Custo de vida/mês": 130,
    "Sobra estimada": 190, "Nota": 60, "Resumo da IA": 420, "Prazo": 90, "Etapas": 70,
    "Status": 130, "Link": 200, "ID": 110,
}


def cost_columns(job: Job, table: CostTable | None, home_city: str) -> tuple[str, str]:
    if table is None:
        return "", ""
    result = estimate(job, home_city, table)
    cost = ("" if result.city_known else "~") + brl(result.cost)
    if result.surplus is None:
        return cost, f"salário não informado (precisa de ~{brl(result.cost)})"
    return cost, brl(result.surplus)


def job_to_row(
    job: Job, result: MatchResult, table: CostTable | None = None, home_city: str = ""
) -> list[str | int]:
    salary = job.salary_text or extract_salary(job.description) or "não informado"
    benefits = job.benefits or extract_benefits(job.description)
    talent_pool = "banco de talentos" in job.title.lower()
    cost, surplus = cost_columns(job, table, home_city)
    return [
        job.title,
        job.company,
        job.level.value,
        salary,
        ", ".join(benefits) or "não informado",
        job.modality.value,
        job.location or "",
        cost,
        surplus,
        result.score,
        result.summary,
        job.deadline.strftime("%d/%m/%Y") if job.deadline else "",
        "?/?",
        "Banco de talentos" if talent_pool else "Nova",
        job.url,
        job.uid,
    ]


def open_worksheet(title: str = "Vagas") -> gspread.Worksheet:
    path = Path(os.environ["GOOGLE_CREDENTIALS_PATH"])
    if not path.is_file():
        raise FileNotFoundError(
            f"Credenciais não encontradas em '{path.resolve()}'. "
            "Confira GOOGLE_CREDENTIALS_PATH no .env e o nome do arquivo."
        )
    client = gspread.service_account(filename=str(path))
    spreadsheet = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        first = spreadsheet.sheet1
        if not first.get_all_values():
            first.update_title(title)
            return first
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=len(HEADERS))


def sync(
    ws: gspread.Worksheet,
    entries: list[tuple[Job, MatchResult]],
    table: CostTable | None = None,
    home_city: str = "",
) -> int:
    """Acrescenta só as vagas novas, sem mexer nas linhas existentes (Status e Etapas são seus)."""
    values = ws.get_all_values()
    first = values[0] if values else []
    has_header = "ID" in first

    if not values or has_header:
        ws.update(range_name="A1", values=[HEADERS])
    else:
        ws.insert_rows([HEADERS], row=1)

    body = values[1:] if has_header else values
    existing = {row[ID_COL] for row in body if len(row) > ID_COL}

    new_rows = [
        job_to_row(job, result, table, home_city)
        for job, result in entries
        if job.uid not in existing
    ]
    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
    return len(new_rows)


def style_sheet(ws: gspread.Worksheet) -> None:
    """Cabeçalho destacado e congelado, filtros, larguras e quebra de linha no resumo."""
    sheet_id = ws.id
    columns = len(HEADERS)
    etapas = chr(ord("A") + ETAPAS_COL)
    ws.format(f"{etapas}2:{etapas}", {"numberFormat": {"type": "TEXT"}})

    requests: list[dict] = [
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": columns},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.11, "green": 0.23, "blue": 0.36},
                    "textFormat": {"bold": True,
                                   "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat,"
                          "horizontalAlignment,verticalAlignment)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "setBasicFilter": {
                "filter": {"range": {"sheetId": sheet_id, "startRowIndex": 0,
                                     "startColumnIndex": 0, "endColumnIndex": columns}}
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1,
                          "startColumnIndex": SUMMARY_COL, "endColumnIndex": SUMMARY_COL + 1},
                "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                "fields": "userEnteredFormat.wrapStrategy",
            }
        },
    ]
    for index, header in enumerate(HEADERS):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                          "startIndex": index, "endIndex": index + 1},
                "properties": {"pixelSize": COLUMN_WIDTHS.get(header, 130)},
                "fields": "pixelSize",
            }
        })
    ws.spreadsheet.batch_update({"requests": requests})