import json

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from jobhunter.forms import capture, sanitize_url, save_snapshot, snapshot_path


def test_sanitize_url_drops_query_and_fragment():
    url = "https://a.gupy.io/job/abc?jobBoardSource=x&token=1#frag"
    assert sanitize_url(url) == "https://a.gupy.io/job/abc"


def test_snapshot_path_is_stable(tmp_path):
    assert snapshot_path("gupy:1", 2, tmp_path) == tmp_path / "gupy_1_2.json"


def test_save_snapshot_writes_json(tmp_path):
    path = save_snapshot({"fields": [{"label": "Nome"}]}, "gupy:1", 1, tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["fields"][0]["label"] == "Nome"


HTML = """
<div><p>Qual o seu nível de escolaridade?</p>
  <label><input type="radio" name="question-1"> Ensino médio</label>
  <label><input type="radio" name="question-1"> Ensino superior cursando</label></div>
<div><p>Você tem disponibilidade para trabalho híbrido?</p>
  <label><input type="radio" name="question-2"> Sim</label>
  <label><input type="radio" name="question-2"> Não</label></div>
<div><p>Qual o seu nível de SQL?</p>
  <label><input type="checkbox" name="checkbox-3-0"> Básico</label>
  <label><input type="checkbox" name="checkbox-3-1"> Avançado</label></div>
<div><p>Qual a sua pretensão salarial?</p>
  <textarea name="Qual a sua pretensão salarial (CLT)?" placeholder="Digite aqui"></textarea></div>
"""

HTML_NESTED = """
<main>
  <section>
    <div><h3>Qual o seu nível de escolaridade?</h3></div>
    <div><label><input type="radio" name="question-1"> Ensino médio</label></div>
    <div><label><input type="radio" name="question-1"> Ensino superior cursando</label></div>
  </section>
  <section>
    <h3>Você tem CNH?</h3>
    <div><label><input type="radio" name="question-2"> Sim</label>
         <label><input type="radio" name="question-2"> Não</label></div>
  </section>
</main>
"""


def capture_html(html: str) -> dict:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content(html)
                return capture(page)
            finally:
                browser.close()
    except PlaywrightError:
        pytest.skip("Chromium não instalado neste ambiente")


def test_capture_extracts_question_text_for_each_group():
    questions = capture_html(HTML)["questions"]
    by_question = {q["question"]: q for q in questions}

    school = by_question["Qual o seu nível de escolaridade?"]
    assert school["kind"] == "single"
    assert school["options"] == ["Ensino médio", "Ensino superior cursando"]
    assert by_question["Você tem disponibilidade para trabalho híbrido?"]["options"] == [
        "Sim",
        "Não",
    ]
    sql = by_question["Qual o seu nível de SQL?"]
    assert sql["kind"] == "multi"
    assert sql["options"] == ["Básico", "Avançado"]
    assert by_question["Qual a sua pretensão salarial (CLT)?"]["kind"] == "text"


def test_capture_finds_question_text_in_nested_blocks():
    questions = capture_html(HTML_NESTED)["questions"]
    by_question = {q["question"]: q for q in questions}

    assert by_question["Qual o seu nível de escolaridade?"]["options"] == [
        "Ensino médio",
        "Ensino superior cursando",
    ]
    assert by_question["Você tem CNH?"]["options"] == ["Sim", "Não"]

class FlakyPage:
    """Simula uma página em navegação: as primeiras leituras falham."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def wait_for_load_state(self, state, timeout):
        pass

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, script):
        self.calls += 1
        if self.calls <= self.failures:
            raise PlaywrightError("Execution context was destroyed")
        return {"url": "https://a.gupy.io/x?token=1", "fields": [], "buttons": []}


def test_capture_retries_after_navigation():
    data = capture(FlakyPage(failures=2))

    assert data["url"] == "https://a.gupy.io/x"


def test_capture_gives_up_after_attempts():
    with pytest.raises(PlaywrightError):
        capture(FlakyPage(failures=10), attempts=3)