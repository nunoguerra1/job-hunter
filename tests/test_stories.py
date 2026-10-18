import pytest

from jobhunter.stories import load_story_bank

EXAMPLE = "profile/story_bank.example.yaml"


def test_example_loads_when_not_strict():
    bank = load_story_bank(EXAMPLE, strict=False)
    assert bank.stories[0].id == "lideranca-dev"
    assert bank.cv_highlights[0].id == "h-lideranca"


def test_strict_rejects_placeholders():
    with pytest.raises(ValueError):
        load_story_bank(EXAMPLE)