import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from jobhunter.browser import persistent_browser
from jobhunter.forms import capture_text
from jobhunter.profile import load_profile

START_URL = "https://portal.gupy.io/"
OUTPUT = Path("data/pages")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PHONE = re.compile(r"(?<!\d)(?:\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}|9?\d{4}[-\s]\d{4})(?!\d)")


def redact(text: str, names: list[str]) -> str:
    """Mascara e-mail, CPF, telefone e as partes do seu nome. Revise o arquivo mesmo assim."""
    text = _EMAIL.sub("[e-mail]", text)
    text = _CPF.sub("[cpf]", text)
    text = _PHONE.sub("[telefone]", text)
    for name in names:
        if len(name) >= 3:
            text = re.sub(re.escape(name), "[nome]", text, flags=re.IGNORECASE)
    return text


def main() -> None:
    try:
        names = load_profile().name.split()
    except FileNotFoundError:
        names = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with persistent_browser() as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(START_URL)
        print("Navegue até a tela que quer registrar. Com ela carregada, volte aqui:")
        print("Enter captura a tela atual, 'q' encerra.")
        step = 1
        while True:
            if input(f"Tela {step}: Enter captura, 'q' encerra: ").strip().lower() == "q":
                break
            open_pages = [p for p in context.pages if not p.is_closed()]
            if not open_pages:
                print("  nenhuma aba aberta; encerrando.")
                break
            try:
                data = capture_text(open_pages[-1])
            except PlaywrightError as error:
                print(f"  não consegui capturar ({type(error).__name__}). Espere carregar.")
                continue
            body = redact(data["text"], names)
            path = OUTPUT / f"tela_{step}.txt"
            path.write_text(f"{data['url']}\n{data['title']}\n\n{body}", encoding="utf-8")
            print(f"  salvo: {path}")
            step += 1


if __name__ == "__main__":
    main()