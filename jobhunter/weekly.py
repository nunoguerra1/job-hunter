import sys
from collections.abc import Callable

from dotenv import load_dotenv

from jobhunter import digest, mail, phases, progress, sync
from jobhunter.daily import parse_skips, run_step


def build_steps(argv: list[str]) -> list[tuple[str, str, Callable[[], None]]]:
    send = ["--send"] if "--send" in argv else []
    return [
        ("progress", "Gupy: candidaturas, etapas e resultados", lambda: progress.main([])),
        ("phases", "Gupy: fases de cada candidatura", phases.main),
        ("mail", "E-mails", mail.sync_mail_to_db),
        ("sync", "Planilha", sync.main),
        ("digest", "Resumo", lambda: digest.main(send)),
    ]


def main(argv: list[str]) -> None:
    load_dotenv()
    skipped = parse_skips(argv)
    failed = []
    for key, name, action in build_steps(argv):
        if key in skipped:
            print(f"\n=== {name}: pulado ===")
        elif not run_step(name, action):
            failed.append(name)
    result = "tudo certo." if not failed else "falhou em " + ", ".join(failed) + "."
    print(f"\nResumo: {result}")


if __name__ == "__main__":
    main(sys.argv[1:])