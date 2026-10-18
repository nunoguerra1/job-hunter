import os

import httpx
from dotenv import load_dotenv

API = "https://api.telegram.org"


class TelegramClient:
    def __init__(self, token: str | None = None, client: httpx.Client | None = None):
        self.token = token or os.environ["TELEGRAM_BOT_TOKEN"]
        self.http = client or httpx.Client(timeout=45)

    def _call(self, method: str, **payload):
        response = self.http.post(f"{API}/bot{self.token}/{method}", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            # não propaga a exceção original: a mensagem dela contém a URL com o token
            raise RuntimeError(
                f"Telegram '{method}' falhou com HTTP {error.response.status_code}"
            ) from None
        return response.json()["result"]

    def send_message(self, chat_id: int, text: str, buttons: list | None = None):
        payload: dict = {
            "chat_id": chat_id,
            "text": text[:4000],
            "disable_web_page_preview": True,
        }
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        return self._call("sendMessage", **payload)

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict]:
        payload: dict = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        return self._call("getUpdates", **payload)

    def answer_callback(self, callback_id: str, text: str = "") -> None:
        self._call("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def clear_buttons(self, chat_id: int, message_id: int) -> None:
        self._call(
            "editMessageReplyMarkup",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup={"inline_keyboard": []},
        )


if __name__ == "__main__":
    # Descobre o seu chat id: envie /start ao bot e rode este módulo.
    load_dotenv()
    seen = set()
    for update in TelegramClient().get_updates(timeout=0):
        chat = (update.get("message") or {}).get("chat")
        if chat and chat["id"] not in seen:
            seen.add(chat["id"])
            print(f"chat id: {chat['id']} ({chat.get('first_name', '')})")
    if not seen:
        print("Nenhuma mensagem encontrada. Envie /start ao seu bot e rode de novo.")