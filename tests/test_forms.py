import json

from jobhunter.forms import sanitize_url, save_snapshot, snapshot_path


def test_sanitize_url_drops_query_and_fragment():
    url = "https://a.gupy.io/job/abc?jobBoardSource=x&token=1#frag"
    assert sanitize_url(url) == "https://a.gupy.io/job/abc"


def test_snapshot_path_is_stable(tmp_path):
    assert snapshot_path("gupy:1", 2, tmp_path) == tmp_path / "gupy_1_2.json"


def test_save_snapshot_writes_json(tmp_path):
    path = save_snapshot({"fields": [{"label": "Nome"}]}, "gupy:1", 1, tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["fields"][0]["label"] == "Nome"