from jobhunter.daily import parse_skips, run_step


def test_run_step_survives_failure(capsys):
    def boom():
        raise RuntimeError("falhou")

    assert run_step("x", boom) is False
    assert "FALHOU" in capsys.readouterr().out


def test_run_step_reports_success():
    assert run_step("x", lambda: None) is True


def test_parse_skips():
    assert parse_skips(["--skip=mail,prepare", "--outra"]) == {"mail", "prepare"}