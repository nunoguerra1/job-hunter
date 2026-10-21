import os
import sys
import time

import httpx
from dotenv import load_dotenv

from jobhunter.review import Reviewer
from jobhunter.storage import JobStore
from jobhunter.telegram import TelegramClient


def process(reviewer, update: dict) -> None:
    """Processa um update sem nunca derrubar o bot e mostrando o que aconteceu."""
    kind = "clique" if "callback_query" in update else "mensagem"
    detail = (update.get("callback_query") or {}).get("data", "")
    print(f"  recebido: {kind} {detail}".rstrip())
    try:
        reviewer.handle(update)
    except (KeyError, RuntimeError, httpx.HTTPError) as error:
        print(f"  ERRO ao processar ({type(error).__name__}): {error}")


def main(notify_only: bool = False, resend: str | None = None) -> None:
    load_dotenv()
    reviewer = Reviewer(
        tg=TelegramClient(),
        store=JobStore(),
        chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
    )
    if resend:
        ok = reviewer.resend(resend)
        print(f"Reenviada: {resend}" if ok else f"Sem rascunho preparado para '{resend}'.")
    sent = reviewer.notify_pending()
    print(f"{sent} candidaturas enviadas para revisão.")
    if notify_only:
        print("Modo --notify-only: os botões NÃO funcionam até rodar o bot sem essa opção.")
        return
    print("Bot ouvindo o Telegram (Ctrl+C para parar)...")
    offset = None
    try:
        while True:
            try:
                updates = reviewer.tg.get_updates(offset)
            except httpx.TimeoutException:
                continue
            except (RuntimeError, httpx.HTTPError) as error:
                hint = " Há outra instância do bot rodando?" if "409" in str(error) else ""
                print(f"  ERRO ao consultar o Telegram: {error}.{hint} Nova tentativa em 10s.")
                time.sleep(10)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                process(reviewer, update)
    except KeyboardInterrupt:
        print("\nBot encerrado.")


if __name__ == "__main__":
    args = sys.argv[1:]
    target = args[args.index("--resend") + 1] if "--resend" in args[:-1] else None
    main(notify_only="--notify-only" in args, resend=target)