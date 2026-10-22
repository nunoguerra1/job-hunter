import sys
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from jobhunter.email_status import Kind, classify_email, guess_company
from jobhunter.gmail import get_service, my_address, recent_headers, sender_domain, sender_name
from jobhunter.storage import JobStore


def iso_date(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return datetime(1970, 1, 1, tzinfo=UTC).isoformat()


def short_date(raw: str) -> str:
    return f"{datetime.fromisoformat(iso_date(raw)):%d/%m}"


def to_records(rows: list[dict], me: str) -> list[dict]:
    """Classifica os e-mails e descarta o ruído. Guarda só cabeçalhos e a classificação."""
    records = []
    for row in rows:
        kind = classify_email(row["subject"], row["snippet"], row["from"], me)
        if kind is Kind.IRRELEVANT:
            continue
        name = sender_name(row["from"])
        domain = sender_domain(row["from"])
        records.append({
            "id": row["id"],
            "thread": row["thread"],
            "sent_at": iso_date(row["date"]),
            "kind": kind.value,
            "sender": name or domain,
            "subject": row["subject"],
            "company": guess_company(name, domain, row["subject"], row["snippet"]),
        })
    return records


def inspect_mail(limit: int = 60, snippets: bool = False, show_all: bool = False) -> None:
    service = get_service()
    me = my_address(service)
    rows = recent_headers(service, max_results=limit)
    ignored = 0
    for row in rows:
        kind = classify_email(row["subject"], row["snippet"], row["from"], me)
        if kind is Kind.IRRELEVANT and not show_all:
            ignored += 1
            continue
        name = sender_name(row["from"]) or sender_domain(row["from"])
        print(f"{short_date(row['date'])} | {kind.value} | {name} | {row['subject']}")
        if snippets and kind is Kind.UNKNOWN and row["snippet"]:
            print(f"      trecho: {row['snippet'][:160]}")
    print(f"\n{len(rows) - ignored} relevantes; {ignored} ignorados (propaganda e alertas).")


def sync_mail_to_db(limit: int = 200) -> None:
    service = get_service()
    records = to_records(recent_headers(service, max_results=limit), my_address(service))
    store = JobStore()
    added = store.add_emails(records)
    print(f"{len(records)} e-mails relevantes; {added} novos no banco.")
    unclear = [r for r in records if r["kind"] in {Kind.UNKNOWN.value, Kind.MESSAGE.value}]
    for record in unclear:
        print(f"  abra e leia: {record['kind']} | {record['company'] or record['sender']}")


def main(argv: list[str]) -> None:
    options = argv[1:]
    limit = next((int(item) for item in options if item.isdigit()), None)
    if argv and argv[0] == "inspect":
        inspect_mail(limit or 60, snippets="--snippets" in options, show_all="--all" in options)
    elif argv and argv[0] == "sync":
        sync_mail_to_db(limit or 200)
    else:
        print("Uso: python -m jobhunter.mail [inspect [qtd] [--snippets] [--all] | sync [qtd]]")


if __name__ == "__main__":
    main(sys.argv[1:])