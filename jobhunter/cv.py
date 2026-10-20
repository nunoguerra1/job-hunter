from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

PLACEHOLDER = "PREENCHER"
MAX_EXPERIENCE_BULLETS = 4
MAX_PROJECT_BULLETS = 3


class Bullet(BaseModel):
    text: str
    id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def from_string(cls, value):
        return {"text": value} if isinstance(value, str) else value


class Experience(BaseModel):
    company: str
    role: str
    period: str
    bullets: list[Bullet]


class Project(BaseModel):
    name: str
    subtitle: str = ""
    links: list[str] = Field(default_factory=list)
    bullets: list[Bullet]


class Education(BaseModel):
    course: str
    period: str
    school: str
    certifications: list[str] = Field(default_factory=list)


class Cv(BaseModel):
    name: str
    title: str
    contacts: list[str]
    summary: str
    experience: list[Experience]
    projects: list[Project]
    education: Education
    skills: dict[str, list[str]]

    def all_texts(self) -> list[str]:
        texts = [*self.contacts, self.summary]
        for item in [*self.experience, *self.projects]:
            texts += [bullet.text for bullet in item.bullets]
        return texts


def load_cv(path: str = "profile/cv_base.yaml", strict: bool = True) -> Cv:
    with Path(path).open(encoding="utf-8") as file:
        cv = Cv.model_validate(yaml.safe_load(file))
    if strict and any(PLACEHOLDER in text for text in cv.all_texts()):
        raise ValueError(f"{path} ainda tem campos '{PLACEHOLDER}'. Complete antes de gerar PDFs.")
    return cv


def pick_bullets(bullets: list[Bullet], preferred_ids: list[str], limit: int) -> list[Bullet]:
    """Os bullets preferidos vêm primeiro (na ordem pedida); o resto mantém a ordem original."""
    rank = {bullet_id: position for position, bullet_id in enumerate(preferred_ids)}
    ordered = sorted(bullets, key=lambda bullet: rank.get(bullet.id, len(rank)))
    return ordered[:limit]