from jobhunter import weekly


def test_weekly_steps_run_in_order():
    keys = [key for key, _name, _action in weekly.build_steps([])]

    assert keys == ["progress", "phases", "mail", "sync", "digest"]


def test_weekly_forwards_send_to_the_digest(monkeypatch):
    calls = []
    monkeypatch.setattr(weekly.digest, "main", calls.append)
    steps = {key: action for key, _name, action in weekly.build_steps(["--send"])}

    steps["digest"]()

    assert calls == [["--send"]]