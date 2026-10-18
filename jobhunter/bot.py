import os
import sys

import httpx
from dotenv import load_dotenv

from jobhunter.review import Reviewer
from jobhunter.storage import JobStore
from jobhunter.telegram import TelegramClient


def main(notify_only: bool = False) -> None:
    load_dotenv()
    reviewer = Reviewer(
        tg=TelegramClient(),
        store=JobStore(),
        chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
    )
    sent = reviewer.notify_pending()
    print(f"{sent} candidaturas enviadas para revisão.")
    if notify_only:
        return
    print("Bot ouvindo o Telegram (Ctrl+C para parar)...")
    offset = None
    try:
        while True:
            try:
                updates = reviewer.tg.get_updates(offset)
            except httpx.TimeoutException:
                continue
            for update in updates:
                offset = update["update_id"] + 1
                reviewer.handle(update)
    except KeyboardInterrupt:
        print("\nBot encerrado.")


if __name__ == "__main__":
    main(notify_only="--notify-only" in sys.argv)