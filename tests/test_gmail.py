from jobhunter.gmail import recent_headers, sender_domain, sender_name


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeMessages:
    def list(self, **kwargs):
        return FakeRequest({"messages": [{"id": "1", "threadId": "t1"}]})

    def get(self, **kwargs):
        assert kwargs["format"] == "metadata"  # nunca busca o corpo completo do e-mail
        return FakeRequest({
            "snippet": "Recebemos sua candidatura.",
            "payload": {"headers": [
                {"name": "From", "value": "Acme RH <rh@acme.gupy.io>"},
                {"name": "Subject", "value": "Sua candidatura foi recebida"},
                {"name": "Date", "value": "Tue, 20 Oct 2026 10:00:00 -0300"},
            ]},
        })


class FakeUsers:
    def messages(self):
        return FakeMessages()


class FakeService:
    def users(self):
        return FakeUsers()


def test_sender_domain():
    assert sender_domain("Acme RH <rh@Acme.gupy.io>") == "acme.gupy.io"
    assert sender_domain("sem endereço") == ""


def test_sender_name():
    assert sender_name("Acme RH <rh@acme.gupy.io>") == "Acme RH"
    assert sender_name('"Itaú" <rh@itau.com.br>') == "Itaú"
    assert sender_name("rh@acme.com") == ""


def test_recent_headers_reads_only_metadata():
    rows = recent_headers(FakeService())

    assert rows == [{
        "id": "1",
        "thread": "t1",
        "from": "Acme RH <rh@acme.gupy.io>",
        "subject": "Sua candidatura foi recebida",
        "date": "Tue, 20 Oct 2026 10:00:00 -0300",
        "snippet": "Recebemos sua candidatura.",
    }]