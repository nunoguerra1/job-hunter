import gspread

from jobhunter.models import Job
from jobhunter.sheets import ID_COL, STATUS_COL, match_job

EMAIL_STATUS = {
    "recebida": "Recebida pela empresa",
    "avançou": "Avançou de etapa",
    "ação necessária": "Ação necessária",
    "mensagem do recrutador": "Mensagem do recrutador",
    "reprovada": "Reprovada",
    "encerrada": "Encerrada",
}
# Só se atualiza o que o próprio sistema escreveu. Se você anotou outra coisa
# (Entrevista, Teste...), nada é sobrescrito.
UPDATABLE = {
    "Enviada",
    "Recebida pela empresa",
    "Avançou de etapa",
    "Ação necessária",
    "Mensagem do recrutador",
}


def latest_progress(emails: list[dict], jobs: list[Job]) -> dict[str, str]:
    """Último andamento por vaga, só quando o e-mail se liga a UMA vaga sem ambiguidade."""
    progress: dict[str, str] = {}
    for email in sorted(emails, key=lambda item: item["sent_at"]):
        label = EMAIL_STATUS.get(email["kind"])
        if not label:
            continue
        uid = match_job(email["company"], email["subject"], jobs)
        if uid:
            progress[uid] = label
    return progress


def sync_mail_status(ws: gspread.Worksheet, emails: list[dict], jobs: list[Job]) -> int:
    progress = latest_progress(emails, jobs)
    letter = chr(ord("A") + STATUS_COL)
    updates = []
    for number, row in enumerate(ws.get_all_values()[1:], start=2):
        if len(row) <= max(ID_COL, STATUS_COL):
            continue
        label = progress.get(row[ID_COL])
        if label and row[STATUS_COL] in UPDATABLE and row[STATUS_COL] != label:
            updates.append({"range": f"{letter}{number}", "values": [[label]]})
    if updates:
        ws.batch_update(updates)
    return len(updates)