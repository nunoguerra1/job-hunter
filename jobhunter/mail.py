import sys

from jobhunter.gmail import get_service, recent_headers, sender_domain


def inspect_mail(limit: int = 60) -> None:
    rows = recent_headers(get_service(), max_results=limit)
    if not rows:
        print("Nenhum e-mail de vagas encontrado nos últimos 60 dias.")
        return
    for row in rows:
        print(f"{row['date'][:16]} | {sender_domain(row['from'])} | {row['subject']}")


def main(argv: list[str]) -> None:
    if argv and argv[0] == "inspect":
        inspect_mail(int(argv[1]) if len(argv) > 1 else 60)
    else:
        print("Uso: python -m jobhunter.mail inspect [quantidade]")


if __name__ == "__main__":
    main(sys.argv[1:])