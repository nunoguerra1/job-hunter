from jobhunter.gmail import recent_headers, sender_domain


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeMessages:
    def list(self, **kwargs):
        return FakeRequest({"messages": [{"id": "1"}]})

    def get(self, **kwargs):
        assert kwargs["format"] == "metadata"  # nunca busca o corpo do e-mail
        return FakeRequest({"payload": {"headers": [
            {"name": "From", "value": "Acme RH <rh@acme.gupy.io>"},
            {"name": "Subject", "value": "Sua candidatura foi recebida"},
            {"name": "Date", "value": "Tue, 20 Oct 2026 10:00:00 -0300"},
        ]}})


class FakeUsers:
    def messages(self):
        return FakeMessages()


class FakeService:
    def users(self):
        return FakeUsers()


def test_sender_domain():
    assert sender_domain("Acme RH <rh@Acme.gupy.io>") == "acme.gupy.io"
    assert sender_domain("sem endereço") == ""


def test_recent_headers_reads_only_metadata():
    rows = recent_headers(FakeService())

    assert rows == [{
        "id": "1",
        "from": "Acme RH <rh@acme.gupy.io>",
        "subject": "Sua candidatura foi recebida",
        "date": "Tue, 20 Oct 2026 10:00:00 -0300",
    }]