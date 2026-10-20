from jobhunter.bot import process


class Boom:
    def handle(self, update):
        raise KeyError("message")


def test_process_survives_errors(capsys):
    process(Boom(), {"update_id": 1, "callback_query": {"data": "approve:t:1"}})
    out = capsys.readouterr().out
    assert "approve:t:1" in out
    assert "ERRO" in out