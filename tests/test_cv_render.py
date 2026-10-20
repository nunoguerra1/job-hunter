import pytest
from playwright.sync_api import Error as PlaywrightError

from jobhunter.cv import load_cv
from jobhunter.cv_render import render_html
from jobhunter.pdf import html_to_pdf

CV = load_cv("profile/cv_base.example.yaml", strict=False)


def test_render_uses_summary_and_prioritizes_bullets():
    html = render_html(CV, summary="Resumo sob medida", preferred_ids=["h-engenharia"])

    assert "Resumo sob medida" in html
    assert html.index("Padronização de práticas") < html.index("Liderança de subdiretoria")


def test_render_escapes_html():
    html = render_html(CV.model_copy(update={"name": "<b>X</b>"}))

    assert "<b>X</b>" not in html
    assert "&lt;b&gt;X&lt;/b&gt;" in html


def test_pdf_is_generated(tmp_path):
    try:
        html_to_pdf("<p>oi</p>", tmp_path / "x.pdf")
    except PlaywrightError:
        pytest.skip("Chromium não instalado neste ambiente")

    assert (tmp_path / "x.pdf").read_bytes().startswith(b"%PDF")