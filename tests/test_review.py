from jobhunter.application import Application
from jobhunter.match import MatchResult
from jobhunter.models import Job, Modality
from jobhunter.review import Reviewer
from jobhunter.storage import JobStore


class FakeTG:
    def __init__(self):
        self.sent = []
        self.answered = []
        self.cleared = []
        self.docs = []

    def send_message(self, chat_id, text, buttons=None):
        self.sent.append((chat_id, text, buttons))

    def answer_callback(self, callback_id, text=""):
        self.answered.append(callback_id)

    def clear_buttons(self, chat_id, message_id):
        self.cleared.append(message_id)

    def send_document(self, chat_id, path, caption=""):
        self.docs.append(path.name)


def setup(tmp_path):
    store = JobStore(":memory:")
    job = Job(source="t", external_id="1", title="Estágio Dev", company="Acme",
              url="https://x", modality=Modality.REMOTE)
    store.add_new([job])
    store.save_score(job.uid, MatchResult(score=90, course_compatible=True, matched_skills=[],
                                          missing_skills=[], summary="ok"))
    app = Application(company_values=["inovação"], story_ids=[], why_us="texto original",
                      cv_summary="r", cv_highlights=["h"], salary_answer="A combinar")
    folder = tmp_path / "t_1"
    folder.mkdir()
    (folder / "draft.json").write_text(app.model_dump_json(), encoding="utf-8")
    tg = FakeTG()
    return Reviewer(tg=tg, store=store, chat_id=42, output=tmp_path), tg, store


def callback(data, chat=42):
    return {"update_id": 1, "callback_query": {
        "id": "cb", "data": data, "message": {"message_id": 9, "chat": {"id": chat}}}}


def test_notify_sends_once_with_buttons(tmp_path):
    reviewer, tg, store = setup(tmp_path)

    assert reviewer.notify_pending() == 1
    assert reviewer.notify_pending() == 0
    assert "texto original" in tg.sent[0][1]
    assert len(tg.sent[0][2][0]) == 3
    assert store.statuses()["t:1"] == "awaiting"


def test_approve_and_discard_update_status(tmp_path):
    reviewer, tg, store = setup(tmp_path)
    reviewer.notify_pending()

    reviewer.handle(callback("approve:t:1"))
    assert store.statuses()["t:1"] == "approved"

    reviewer.handle(callback("discard:t:1"))
    assert store.statuses()["t:1"] == "discarded"


def test_other_chats_are_ignored(tmp_path):
    reviewer, tg, store = setup(tmp_path)
    reviewer.notify_pending()

    reviewer.handle(callback("approve:t:1", chat=99))
    assert store.statuses()["t:1"] == "awaiting"
    assert tg.answered == []


def test_edit_flow_replaces_text_and_resends(tmp_path):
    reviewer, tg, store = setup(tmp_path)
    reviewer.notify_pending()

    reviewer.handle(callback("edit:t:1"))
    reviewer.handle({"update_id": 2, "message": {"chat": {"id": 42}, "text": "novo texto"}})

    saved = Application.model_validate_json((tmp_path / "t_1" / "draft.json").read_text("utf-8"))
    assert saved.why_us == "novo texto"
    assert "novo texto" in tg.sent[-1][1]
    assert store.statuses()["t:1"] == "awaiting"

def test_review_sends_cv_pdf_before_message(tmp_path):
    reviewer, tg, store = setup(tmp_path)
    (tmp_path / "t_1" / "curriculo.pdf").write_bytes(b"%PDF")

    reviewer.notify_pending()

    assert tg.docs == ["curriculo.pdf"]
    assert len(tg.sent) == 1

def test_resend_sends_again_even_if_already_notified(tmp_path):
    reviewer, tg, store = setup(tmp_path)
    reviewer.notify_pending()

    assert reviewer.resend("t:1")
    assert len(tg.sent) == 2
    assert not reviewer.resend("t:404")