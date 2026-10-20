import pytest

from jobhunter.cv import Bullet, load_cv, pick_bullets

EXAMPLE = "profile/cv_base.example.yaml"
BULLETS = [Bullet(text="a", id="x"), Bullet(text="b", id="y"), Bullet(text="c")]


def test_pick_bullets_puts_preferred_first_and_limits():
    picked = pick_bullets(BULLETS, ["y", "x"], limit=2)
    assert [bullet.text for bullet in picked] == ["b", "a"]


def test_pick_bullets_keeps_order_without_preferences():
    assert [bullet.text for bullet in pick_bullets(BULLETS, [], limit=3)] == ["a", "b", "c"]


def test_bullet_accepts_plain_string():
    assert Bullet.model_validate("texto").text == "texto"


def test_example_loads_when_not_strict():
    cv = load_cv(EXAMPLE, strict=False)
    assert cv.experience[0].bullets[0].id == "h-lideranca"


def test_strict_rejects_placeholders():
    with pytest.raises(ValueError):
        load_cv(EXAMPLE)