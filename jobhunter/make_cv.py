import sys
from pathlib import Path

from jobhunter.application import Application
from jobhunter.cv import Cv, load_cv
from jobhunter.cv_render import render_html
from jobhunter.pdf import html_to_pdf

OUTPUT = Path("output")


def build_pdf(folder: Path, cv: Cv) -> Path:
    app = Application.model_validate_json((folder / "draft.json").read_text(encoding="utf-8"))
    pdf_path = folder / "curriculo.pdf"
    html_to_pdf(render_html(cv, app.cv_summary, app.cv_highlight_ids), pdf_path)
    return pdf_path


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
        print(f"PDF gerado: {build_pdf(folder, cv)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")