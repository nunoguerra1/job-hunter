import re

import gspread

from jobhunter.mail_status import UPDATABLE
from jobhunter.progress import OUTCOME_STATUS
from jobhunter.sheets import ETAPAS_COL, ID_COL, STATUS_COL

GUPY_HEADERS = [
    "Empresa", "Vaga", "Local", "Modalidade", "Contrato", "Etapa", "Aba da Gupy",
    "Resultado", "Vaga na planilha", "ID da candidatura",
]
STAGE_COL = GUPY_HEADERS.index("Etapa")
_SYSTEM_STAGE = re.compile(r"\d+/\d+")


def stage_text(row: dict) -> str:
    if row["current"] is None or row["total"] is None:
        return ""
    return f"{row['current']}/{row['total']}"


def sync_progress(ws: gspread.Worksheet, applications: list[dict]) -> int:
    """Escreve 'n/m' em Etapas nas vagas ligadas a uma candidatura da Gupy."""
    stages = {a["job_uid"]: stage_text(a) for a in applications if a["job_uid"] and stage_text(a)}
    letter = chr(ord("A") + ETAPAS_COL)
    updates = []
    for number, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) <= max(ID_COL, ETAPAS_COL):
            continue
        stage = stages.get(row[ID_COL])
        current = row[ETAPAS_COL]
        writable = current in {"", "?/?"} or bool(_SYSTEM_STAGE.fullmatch(current))
        if stage and current != stage and writable:
            updates.append({"range": f"{letter}{number}", "values": [[stage]]})
    if updates:
        ws.batch_update(updates)
    return len(updates)


def sync_outcomes(ws: gspread.Worksheet, applications: list[dict]) -> int:
    """Reprovada ou Encerrada, vindo da aba Finalizadas da Gupy (só sobre status do sistema)."""
    labels = {
        a["job_uid"]: OUTCOME_STATUS[a["outcome"]]
        for a in applications
        if a["job_uid"] and a["outcome"] in OUTCOME_STATUS
    }
    letter = chr(ord("A") + STATUS_COL)
    updates = []
    for number, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) <= max(ID_COL, STATUS_COL):
            continue
        label = labels.get(row[ID_COL])
        if label and row[STATUS_COL] in UPDATABLE and row[STATUS_COL] != label:
            updates.append({"range": f"{letter}{number}", "values": [[label]]})
    if updates:
        ws.batch_update(updates)
    return len(updates)


def _gupy_row(application: dict) -> list[str]:
    return [
        application["company"],
        application["title"],
        application["location"],
        application["workplace"],
        application["contract"],
        stage_text(application),
        application["tab"],
        application["outcome"],
        application["job_uid"],
        application["application_id"],
    ]


def sync_gupy_tab(ws: gspread.Worksheet, applications: list[dict]) -> int:
    rows = [_gupy_row(application) for application in applications]
    letter = chr(ord("A") + STAGE_COL)
    ws.clear()
    ws.format(f"{letter}2:{letter}", {"numberFormat": {"type": "TEXT"}})
    ws.update(range_name="A1", values=[GUPY_HEADERS, *rows])
    return len(rows)