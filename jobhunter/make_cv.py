import re
import sys
from pathlib import Path

from jobhunter.application import Application
from jobhunter.cv import Cv, load_cv
from jobhunter.cv_render import LAYOUTS, render_html
from jobhunter.pdf import html_to_pdf

OUTPUT = Path("output")
_PAGE = re.compile(rb"/Type\s*/Page(?![s\w])")


def count_pages(pdf: Path) -> int:
    return max(1, len(_PAGE.findall(pdf.read_bytes())))


def build_pdf(folder: Path, cv: Cv) -> tuple[Path, int]:
    """Gera o PDF no primeiro layout que cabe em 1 página; devolve o caminho e o nº de páginas."""
    app = Application.model_validate_json((folder / "draft.json").read_text(encoding="utf-8"))
    pdf_path = folder / "curriculo.pdf"
    pages = 0
    for layout in LAYOUTS:
        html_to_pdf(render_html(cv, app.cv_summary, app.cv_highlight_ids, layout), pdf_path)
        pages = count_pages(pdf_path)
        if pages <= 1:
            break
    return pdf_path, pages


def main(target: str = "all") -> None:
    try:
        cv = load_cv()
    except (FileNotFoundError, ValueError) as error:
        print(f"Currículo-base indisponível: {error}")
        return
    if target == "all":  # só as que ainda não têm PDF
        folders = [
            folder
            for folder in sorted(OUTPUT.glob("*"))
            if (folder / "draft.json").exists() and not (folder / "curriculo.pdf").exists()
        ]
    else:  # uma vaga específica, regenera mesmo se já existir
        folder = OUTPUT / target.replace(":", "_")
        folders = [folder] if (folder / "draft.json").exists() else []
    if not folders:
        print("Nada para gerar.")
        return
    for folder in folders:
        path, pages = build_pdf(folder, cv)
        note = "" if pages <= 1 else f" (ATENÇÃO: {pages} páginas mesmo no layout mais compacto)"
        print(f"PDF gerado: {path}{note}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")