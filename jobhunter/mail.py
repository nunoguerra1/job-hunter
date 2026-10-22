import sys
from email.utils import parsedate_to_datetime

from jobhunter.email_status import Kind, classify_email
from jobhunter.gmail import get_service, recent_headers, sender_domain, sender_name


def short_date(raw: str) -> str:
    try:
        return f"{parsedate_to_datetime(raw):%d/%m}"
    except (TypeError, ValueError):
        return raw[:11]


def inspect_mail(limit: int = 60, snippets: bool = False, show_all: bool = False) -> None:
    rows = recent_headers(get_service(), max_results=limit)
    ignored = 0
    for row in rows:
        kind = classify_email(row["subject"])
        if kind is Kind.IRRELEVANT and not show_all:
            ignored += 1
            continue
        name = sender_name(row["from"]) or sender_domain(row["from"])
        print(f"{short_date(row['date'])} | {kind.value} | {name} | {row['subject']}")
        if snippets and kind is Kind.UNKNOWN and row["snippet"]:
            print(f"      trecho: {row['snippet'][:160]}")
    print(f"\n{len(rows) - ignored} relevantes; {ignored} ignorados (propaganda e alertas).")


def main(argv: list[str]) -> None:
    if argv and argv[0] == "inspect":
        options = argv[1:]
        limit = int(next((item for item in options if item.isdigit()), 60))
        inspect_mail(limit, snippets="--snippets" in options, show_all="--all" in options)
    else:
        print("Uso: python -m jobhunter.mail inspect [quantidade] [--snippets] [--all]")


if __name__ == "__main__":
    main(sys.argv[1:])