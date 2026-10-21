import pytest
from playwright.sync_api import Error as PlaywrightError

from jobhunter.cv import load_cv
from jobhunter.cv_render import LAYOUTS, Layout, render_html
from jobhunter.make_cv import count_pages
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

def test_compact_layout_has_fewer_bullets():
    full = render_html(CV, layout=LAYOUTS[0])
    compact = render_html(CV, layout=Layout(9, 2, 2))

    assert compact.count("<li>") < full.count("<li>")


def test_count_pages(tmp_path):
    long_html = "<p>linha</p>" * 300
    try:
        html_to_pdf("<p>curto</p>", tmp_path / "a.pdf")
        html_to_pdf(long_html, tmp_path / "b.pdf")
    except PlaywrightError:
        pytest.skip("Chromium não instalado neste ambiente")

    assert count_pages(tmp_path / "a.pdf") == 1
    assert count_pages(tmp_path / "b.pdf") > 1