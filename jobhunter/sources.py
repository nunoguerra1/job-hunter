import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Board(BaseModel):
    token: str
    company: str | None = None
    any_location: bool = False


class AdzunaConfig(BaseModel):
    queries: list[str] = Field(default_factory=list)
    max_pages: int = 2


class Sources(BaseModel):
    greenhouse: list[Board] = Field(default_factory=list)
    lever: list[Board] = Field(default_factory=list)
    adzuna: AdzunaConfig = Field(default_factory=AdzunaConfig)


_GREENHOUSE = re.compile(
    r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([\w-]+)", re.IGNORECASE
)
_LEVER = re.compile(r"jobs\.lever\.co/([\w-]+)", re.IGNORECASE)


def load_sources(path: str = "config/sources.yaml") -> Sources:
    file = Path(path)
    if not file.exists():
        return Sources()
    with file.open(encoding="utf-8") as handle:
        return Sources.model_validate(yaml.safe_load(handle) or {})


def find_board(url: str) -> tuple[str, str] | None:
    """Reconhece o quadro de vagas (Greenhouse ou Lever) a partir do link de uma vaga."""
    for kind, pattern in (("greenhouse", _GREENHOUSE), ("lever", _LEVER)):
        match = pattern.search(url)
        if match:
            return kind, match.group(1)
    return None