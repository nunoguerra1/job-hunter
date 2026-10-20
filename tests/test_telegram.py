import json

import httpx
import pytest
import respx

from jobhunter.telegram import TelegramClient


@respx.mock
def test_send_message_payload():
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )
    TelegramClient(token="TOKEN").send_message(42, "oi", [[{"text": "a", "callback_data": "b"}]])

    body = json.loads(route.calls[0].request.content)
    assert body["chat_id"] == 42
    assert body["reply_markup"]["inline_keyboard"][0][0]["text"] == "a"


@respx.mock
def test_error_does_not_leak_token():
    respx.post("https://api.telegram.org/botSECRET/sendMessage").mock(
        return_value=httpx.Response(401, json={})
    )
    with pytest.raises(RuntimeError) as info:
        TelegramClient(token="SECRET").send_message(42, "oi")

    assert "SECRET" not in str(info.value)

@respx.mock
def test_send_document_uploads_file(tmp_path):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.4 conteudo")
    route = respx.post("https://api.telegram.org/botTOKEN/sendDocument").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )
    TelegramClient(token="TOKEN").send_document(42, pdf, "Currículo")

    assert b"%PDF-1.4 conteudo" in route.calls[0].request.content