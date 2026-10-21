import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from jobhunter.answers import Plan
from jobhunter.fill import fill_step

HTML = """
<div><p>Escolaridade?</p>
  <label><input type="radio" name="question-1"> Ensino médio</label>
  <label><input type="radio" name="question-1"> Ensino superior cursando</label></div>
<div><p>Nível?</p>
  <label><input type="checkbox" name="checkbox-2-0"> Básico</label>
  <label><input type="checkbox" name="checkbox-2-1"> Avançado</label></div>
<textarea name="Por que você quer trabalhar conosco?"></textarea>
<div><p>CNH?</p>
  <label><input type="radio" name="question-4"> Sim</label>
  <label><input type="radio" name="question-4"> Não</label></div>
<button id="next">Salvar e continuar</button>
<script>
  document.getElementById('next').addEventListener('click', () => { window.__clicked = true; });
</script>
"""

READ_STATE = """() => ({
  school: [...document.getElementsByName('question-1')].map(e => e.checked),
  levels: [...document.querySelectorAll('input[type=checkbox]')].map(e => e.checked),
  text: document.querySelector('textarea').value,
  cnh: [...document.getElementsByName('question-4')].map(e => e.checked),
  flagged: document.getElementsByName('question-4')[0].closest('label').style.outline,
  clicked: window.__clicked === true
})"""

PLANS = [
    Plan("question-1", "single", "Escolaridade?", "fill", ["Ensino superior cursando"], "regra"),
    Plan("checkbox-2", "multi", "Nível?", "fill", ["Avançado"], "regra"),
    Plan("Por que você quer trabalhar conosco?", "text", "Por que?", "fill", ["Texto"], "regra"),
    Plan("question-4", "single", "CNH?", "human", [], "assunto sensível"),
]


def test_fill_marks_known_fields_flags_the_rest_and_never_clicks_next():
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content(HTML)
                result = fill_step(page, PLANS)
                state = page.evaluate(READ_STATE)
            finally:
                browser.close()
    except PlaywrightError:
        pytest.skip("Chromium não instalado neste ambiente")

    assert len(result.filled) == 3
    assert len(result.pending) == 1
    assert state["school"] == [False, True]
    assert state["levels"] == [False, True]
    assert state["text"] == "Texto"
    assert state["cnh"] == [False, False]
    assert state["flagged"] != ""
    assert state["clicked"] is False