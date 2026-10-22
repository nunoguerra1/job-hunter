import sys

import httpx

from jobhunter.collectors.greenhouse import API_URL as GREENHOUSE_URL
from jobhunter.collectors.lever import API_URL as LEVER_URL
from jobhunter.sources import find_board


def titles_of(kind: str, data) -> list[str]:
    if kind == "greenhouse" and isinstance(data, dict):
        return [job.get("title", "") for job in data.get("jobs", [])]
    if kind == "lever" and isinstance(data, list):
        return [job.get("text", "") for job in data]
    return []


def find(url: str) -> None:
    board = find_board(url)
    if not board:
        print("Não reconheci Greenhouse nem Lever neste link. Tente o link de uma vaga.")
        return
    kind, token = board
    print(f"{kind}: código '{token}'.")
    print(f"Confirme com: python -m jobhunter.boards check {kind} {token}")


def check(kind: str, token: str) -> None:
    if kind == "greenhouse":
        url, params = GREENHOUSE_URL.format(token=token), {}
    elif kind == "lever":
        url, params = LEVER_URL.format(site=token), {"mode": "json"}
    else:
        print("O tipo deve ser 'greenhouse' ou 'lever'.")
        return
    try:
        response = httpx.get(url, params=params, timeout=30)
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        print(f"Falhou: {type(error).__name__}")
        return
    titles = titles_of(kind, data)
    print(f"HTTP {response.status_code}: {len(titles)} vagas no quadro '{token}'.")
    for title in titles[:8]:
        print(f"  - {title}")


def main(argv: list[str]) -> None:
    if len(argv) >= 2 and argv[0] == "find":
        find(argv[1])
    elif len(argv) >= 3 and argv[0] == "check":
        check(argv[1], argv[2])
    else:
        print("Uso: python -m jobhunter.boards [find <link da vaga> | check <tipo> <código>]")


if __name__ == "__main__":
    main(sys.argv[1:])