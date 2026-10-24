import re

import gspread

from jobhunter.sheets import ETAPAS_COL, ID_COL

GUPY_HEADERS = [
    "Empresa", "Vaga", "Local", "Modalidade", "Contrato", "Etapa", "Aba da Gupy",
    "Vaga na planilha", "ID da candidatura",
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


def _gupy_row(application: dict) -> list[str]:
    return [
        application["company"],
        application["title"],
        application["location"],
        application["workplace"],
        application["contract"],
        stage_text(application),
        application["tab"],
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