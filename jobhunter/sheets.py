import os
from datetime import date, datetime
from pathlib import Path

import gspread

from jobhunter.cost import CostTable, brl, estimate
from jobhunter.extract import extract_benefits, extract_salary
from jobhunter.filters import normalize
from jobhunter.match import MatchResult
from jobhunter.models import Job

HEADERS = [
    "Título", "Empresa", "Tipo de cargo", "Salário", "Benefícios", "Modalidade", "Local",
    "Custo de vida/mês", "Sobra estimada", "Nota", "Resumo da IA", "Publicada", "Prazo",
    "Etapas", "Status", "Link", "ID",
]
MAIL_HEADERS = [
    "Data", "Situação", "Empresa/remetente (estimado)", "Assunto", "Vaga na planilha",
    "ID do e-mail",
]
MAIL_ID_COL = MAIL_HEADERS.index("ID do e-mail")
ID_COL = HEADERS.index("ID")
ETAPAS_COL = HEADERS.index("Etapas")
SUMMARY_COL = HEADERS.index("Resumo da IA")

STATUS_COL = HEADERS.index("Status")
PRAZO_COL = HEADERS.index("Prazo")
SYSTEM_STATUSES = {"", "Nova", "Banco de talentos", "Em revisão", "Aprovada", "Descartada"}
STATUS_LABELS = {
    "awaiting": "Em revisão",
    "approved": "Aprovada",
    "discarded": "Descartada",
    "applied": "Enviada",
    "expired": "Encerrada",
    "closed": "Encerrada",
}

COLUMN_WIDTHS = {
    "Título": 320, "Empresa": 200, "Tipo de cargo": 110, "Salário": 150,
    "Benefícios": 230, "Modalidade": 110, "Local": 200, "Custo de vida/mês": 150,
    "Sobra estimada": 200, "Nota": 60, "Resumo da IA": 420, "Prazo": 90, "Etapas": 70,
    "Status": 130, "Link": 200, "ID": 110, "Publicada": 90
}


def cost_columns(job: Job, table: CostTable | None, home_city: str) -> tuple[str, str]:
    if table is None:
        return "", ""
    result = estimate(job, home_city, table)
    cost = ("" if result.city_known else "~") + brl(result.cost)
    if result.surplus is None:
        return cost, f"sem salário: precisa ~{brl(result.cost)}"
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
        job.published_at.strftime("%d/%m/%Y") if job.published_at else "",
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

def reset_sheet(ws: gspread.Worksheet) -> None:
    """Limpa valores E formatação (ws.clear() sozinho deixa a formatação antiga para trás)."""
    ws.clear()
    ws.spreadsheet.batch_update({"requests": [
        {"updateCells": {"range": {"sheetId": ws.id}, "fields": "userEnteredFormat"}},
    ]})

def mark_expired(ws: gspread.Worksheet, today: date | None = None) -> int:
    """Marca como 'Encerrada' as linhas ainda 'Nova' cujo prazo já passou."""
    today = today or date.today()
    letter = chr(ord("A") + STATUS_COL)
    updates = []
    for number, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) <= max(STATUS_COL, PRAZO_COL) or row[STATUS_COL] not in {"Nova", ""}:
            continue
        try:
            deadline = datetime.strptime(row[PRAZO_COL], "%d/%m/%Y").date()
        except ValueError:
            continue
        if deadline < today:
            updates.append({"range": f"{letter}{number}", "values": [["Encerrada"]]})
    if updates:
        ws.batch_update(updates)
    return len(updates)

def sync_statuses(ws: gspread.Worksheet, statuses: dict[str, str]) -> int:
    """Reflete o status do banco na planilha, sem sobrescrever o que você editou à mão."""
    letter = chr(ord("A") + STATUS_COL)
    updates = []
    for number, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) <= max(ID_COL, STATUS_COL):
            continue
        label = STATUS_LABELS.get(statuses.get(row[ID_COL], ""))
        if label and row[STATUS_COL] in SYSTEM_STATUSES and row[STATUS_COL] != label:
            updates.append({"range": f"{letter}{number}", "values": [[label]]})
    if updates:
        ws.batch_update(updates)
    return len(updates)

def match_job(company: str, subject: str, jobs: list[Job]) -> str:
    """UID da vaga cuja empresa aparece no e-mail; vazio se for ambíguo ou não houver."""
    haystack = normalize(f"{company} {subject}")
    matches = {
        job.uid for job in jobs
        if len(normalize(job.company)) >= 5 and normalize(job.company) in haystack
    }
    return next(iter(matches)) if len(matches) == 1 else ""


def sync_mail(ws: gspread.Worksheet, emails: list[dict], jobs: list[Job]) -> int:
    """Acrescenta só os e-mails novos na aba de candidaturas, sem mexer nas linhas antigas."""
    values = ws.get_all_values()
    if not values or values[0] != MAIL_HEADERS:
        ws.update(range_name="A1", values=[MAIL_HEADERS])
    existing = {row[MAIL_ID_COL] for row in values[1:] if len(row) > MAIL_ID_COL}
    rows = [
        [
            f"{datetime.fromisoformat(email['sent_at']):%d/%m/%Y}",
            email["kind"],
            email["company"] or email["sender"],
            email["subject"],
            match_job(email["company"], email["subject"], jobs),
            email["id"],
        ]
        for email in emails
        if email["id"] not in existing
    ]
    if rows:
        ws.append_rows(rows, value_input_option="RAW")
    return len(rows)

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
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 1}
        }
    })
    ws.spreadsheet.batch_update({"requests": requests})