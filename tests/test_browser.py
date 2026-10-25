from playwright.sync_api import Error as PlaywrightError

from jobhunter.browser import read_cookies, restore_session, save_session, write_cookies

COOKIES = [{"name": "sid", "value": "x", "domain": ".gupy.io", "path": "/", "expires": -1}]


class FakeContext:
    def __init__(self, state=None, fail_add=False):
        self.state = state
        self.fail_add = fail_add
        self.added = []

    def storage_state(self):
        if self.state is None:
            raise PlaywrightError("closed")
        return self.state

    def add_cookies(self, cookies):
        if self.fail_add:
            raise PlaywrightError("bad cookie")
        self.added.extend(cookies)


def test_cookies_roundtrip(tmp_path):
    path = tmp_path / "cookies.json"

    write_cookies(COOKIES, path)

    assert read_cookies(path) == COOKIES


def test_read_cookies_tolerates_missing_or_broken_files(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{isto não é json", encoding="utf-8")

    assert read_cookies(tmp_path / "nao-existe.json") == []
    assert read_cookies(broken) == []


def test_save_then_restore_session(tmp_path):
    path = tmp_path / "cookies.json"
    save_session(FakeContext({"cookies": COOKIES, "origins": []}), path)
    fresh = FakeContext()

    restore_session(fresh, path)

    assert fresh.added == COOKIES


def test_save_session_ignores_a_closed_browser(tmp_path):
    path = tmp_path / "cookies.json"

    save_session(FakeContext(None), path)

    assert not path.exists()


def test_restore_ignores_invalid_cookies(tmp_path):
    path = tmp_path / "cookies.json"
    write_cookies(COOKIES, path)

    restore_session(FakeContext(fail_add=True), path)  # não deve levantar erro