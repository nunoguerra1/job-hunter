from pathlib import Path

import yaml
from pydantic import BaseModel

PLACEHOLDER = "PREENCHER"


class Story(BaseModel):
    id: str
    tags: list[str]
    situation: str
    task: str
    action: str
    result: str


class Highlight(BaseModel):
    id: str
    text: str


class StoryBank(BaseModel):
    stories: list[Story]
    cv_highlights: list[Highlight]

    def all_texts(self) -> list[str]:
        texts = [h.text for h in self.cv_highlights]
        for story in self.stories:
            texts += [story.situation, story.task, story.action, story.result]
        return texts


def load_story_bank(path: str = "profile/story_bank.yaml", strict: bool = True) -> StoryBank:
    with Path(path).open(encoding="utf-8") as file:
        bank = StoryBank.model_validate(yaml.safe_load(file))
    if strict and any(PLACEHOLDER in text for text in bank.all_texts()):
        raise ValueError(
            f"{path} ainda tem campos '{PLACEHOLDER}'. Complete com dados reais antes de usar."
        )
    return bank