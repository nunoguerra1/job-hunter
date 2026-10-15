from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from jobhunter.models import Modality


class AreaPreference(BaseModel):
    name: str
    weight: int = Field(ge=1, le=10)
    keywords: list[str]


class Profile(BaseModel):
    name: str
    course: str
    expected_graduation: date
    city: str
    state: str
    min_salary: int | None = None
    summary: str = ""
    modalities: list[Modality]
    skills: list[str]
    areas: list[AreaPreference]
    excluded_title_keywords: list[str] = Field(default_factory=list)


def load_profile(path: str = "profile/profile.yaml") -> Profile:
    with Path(path).open(encoding="utf-8") as file:
        return Profile.model_validate(yaml.safe_load(file))