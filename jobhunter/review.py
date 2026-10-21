from dataclasses import dataclass
from pathlib import Path

from jobhunter.application import Application
from jobhunter.filters import is_open
from jobhunter.match import MatchResult
from jobhunter.models import Job
from jobhunter.storage import JobStore
from jobhunter.telegram import TelegramClient

AWAITING = "awaiting"
APPROVED = "approved"
DISCARDED = "discarded"
APPLIED = "applied"
EXPIRED = "expired"
CLOSED = "closed"


def format_review(job: Job, result: MatchResult | None, app: Application) -> str:
    place = job.modality.value + (f" · {job.location}" if job.location else "")
    score = f"⭐ Nota {result.score}/100\n" if result else ""
    return (
        f"📋 {job.title}\n🏢 {job.company}\n📍 {place}\n{score}"
        f"💰 {app.salary_answer}\n🔗 {job.url}\n\n"
        f"✍️ Por que você quer trabalhar conosco?\n\n{app.why_us}"
    )


def review_buttons(uid: str) -> list[list[dict]]:
    return [[
        {"text": "✅ Aprovar", "callback_data": f"approve:{uid}"},
        {"text": "✏️ Editar", "callback_data": f"edit:{uid}"},
        {"text": "🗑 Descartar", "callback_data": f"discard:{uid}"},
    ]]


@dataclass
class Reviewer:
    tg: TelegramClient
    store: JobStore
    chat_id: int
    output: Path = Path("output")
    editing: str | None = None  # uid aguardando o novo texto

    def _draft_path(self, uid: str) -> Path:
        return self.output / uid.replace(":", "_") / "draft.json"

    def _load(self, uid: str) -> Application:
        return Application.model_validate_json(self._draft_path(uid).read_text(encoding="utf-8"))

    def _save(self, uid: str, app: Application) -> None:
        self._draft_path(uid).write_text(app.model_dump_json(indent=2), encoding="utf-8")

    def _job(self, uid: str) -> Job | None:
        return next((job for job in self.store.all() if job.uid == uid), None)

    def send_review(self, job: Job, with_cv: bool = True) -> None:
        app = self._load(job.uid)
        result = self.store.scores().get(job.uid)
        pdf = self._draft_path(job.uid).with_name("curriculo.pdf")
        if with_cv and pdf.exists():  # o PDF vai antes, para os botões ficarem no fim da conversa
            self.tg.send_document(self.chat_id, pdf, "Currículo desta candidatura")
        self.tg.send_message(self.chat_id, format_review(job, result, app), review_buttons(job.uid))

    def notify_pending(self) -> int:
        """Envia para revisão as candidaturas preparadas que ainda não foram enviadas."""
        statuses = self.store.statuses()
        sent = 0
        for job in self.store.all():
            if job.uid in statuses or not self._draft_path(job.uid).exists():
                continue
            if not is_open(job):
                self.store.set_status(job.uid, EXPIRED)  # prazo vencido: nem vai para revisão
                continue
            self.send_review(job)
            self.store.set_status(job.uid, AWAITING)
            sent += 1
        return sent

    def resend(self, uid: str) -> bool:
        """Reenvia uma candidatura já preparada, mesmo que ela já tenha sido notificada."""
        job = self._job(uid)
        if not job or not is_open(job) or not self._draft_path(uid).exists():
            return False
        self.send_review(job)
        self.store.set_status(uid, AWAITING)
        return True

    def _decide(self, uid: str, status: str, label: str, message_id: int) -> None:
        self.store.set_status(uid, status)
        self.tg.clear_buttons(self.chat_id, message_id)
        job = self._job(uid)
        self.tg.send_message(self.chat_id, f"{label}: {job.title if job else uid}")

    def handle(self, update: dict) -> None:
        query = update.get("callback_query")
        if query:
            message = query.get("message")
            if not message or message["chat"]["id"] != self.chat_id:
                return  # ignora qualquer pessoa que não seja você
            self.tg.answer_callback(query["id"])
            action, _, uid = query["data"].partition(":")
            message_id = message["message_id"]
            if action == "approve":
                self._decide(uid, APPROVED, "✅ Aprovada", message_id)
            elif action == "discard":
                self._decide(uid, DISCARDED, "🗑 Descartada", message_id)
            elif action == "edit":
                self.editing = uid
                self.tg.clear_buttons(self.chat_id, message_id)
                self.tg.send_message(
                    self.chat_id,
                    "✏️ Envie, em uma única mensagem, o novo texto de "
                    "'Por que você quer trabalhar conosco?'. Para desistir, envie /cancelar.",
                )
            return

        message = update.get("message")
        if not message or message["chat"]["id"] != self.chat_id:
            return
        text = (message.get("text") or "").strip()
        if not self.editing or not text:
            return
        uid, self.editing = self.editing, None
        if text == "/cancelar":
            self.tg.send_message(self.chat_id, "Edição cancelada.")
        else:
            app = self._load(uid)
            app.why_us = text
            self._save(uid, app)
        job = self._job(uid)
        if job:
            self.send_review(job, with_cv=False)