import sys
from collections.abc import Callable

from dotenv import load_dotenv

from jobhunter import digest, mail, prepare, score, sync
from jobhunter.__main__ import collect, summarize
from jobhunter.bot import main as notify
from jobhunter.storage import JobStore


def collect_step() -> None:
    store = JobStore()
    collect(store)
    summarize(store)


STEPS: list[tuple[str, str, Callable[[], None]]] = [
    ("collect", "Coleta de vagas", collect_step),
    ("mail", "E-mails", mail.sync_mail_to_db),
    ("score", "Nota de match (até 40 vagas)", lambda: score.main(40)),
    ("prepare", "Candidaturas (3 melhores)", lambda: prepare.main("3")),
    ("sync", "Planilha", sync.main),
    ("telegram", "Telegram (só envia)", lambda: notify(notify_only=True)),
    ("digest", "Resumo do dia (Telegram)", lambda: digest.main(["--send"])),
]


def parse_skips(argv: list[str]) -> set[str]:
    skipped: set[str] = set()
    for arg in argv:
        if arg.startswith("--skip="):
            skipped |= set(arg.removeprefix("--skip=").split(","))
    return skipped


def run_step(name: str, action: Callable[[], None]) -> bool:
    print(f"\n=== {name} ===")
    try:
        action()
    except Exception as error:  # um passo com falha não derruba os seguintes
        print(f"  FALHOU ({type(error).__name__}): {str(error)[:200]}")
        return False
    return True


def main(argv: list[str]) -> None:
    load_dotenv()
    skipped = parse_skips(argv)
    failed = []
    for key, name, action in STEPS:
        if key in skipped:
            print(f"\n=== {name}: pulado ===")
        elif not run_step(name, action):
            failed.append(name)
    result = "tudo certo." if not failed else "falhou em " + ", ".join(failed) + "."
    print(f"\nResumo: {result}")


if __name__ == "__main__":
    main(sys.argv[1:])