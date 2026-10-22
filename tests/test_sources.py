from jobhunter.sources import Sources, find_board, load_sources


def test_find_board_greenhouse():
    url = "https://boards.greenhouse.io/c6bank/jobs/123"
    assert find_board(url) == ("greenhouse", "c6bank")
    url = "https://job-boards.greenhouse.io/acme/jobs/1?gh_src=x"
    assert find_board(url) == ("greenhouse", "acme")


def test_find_board_lever():
    assert find_board("https://jobs.lever.co/acme/0a1b2c") == ("lever", "acme")


def test_find_board_unknown_ats():
    assert find_board("https://empresa.gupy.io/job/abc") is None


def test_missing_config_gives_empty_sources(tmp_path):
    assert load_sources(str(tmp_path / "nao-existe.yaml")) == Sources()


def test_shipped_config_loads():
    sources = load_sources("config/sources.yaml")
    assert sources.adzuna.queries