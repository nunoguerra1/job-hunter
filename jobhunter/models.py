from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Modality(str, Enum):
    REMOTE = "home office"
    ONSITE = "presencial"
    HYBRID = "híbrida"
    UNKNOWN = "não informado"


class Level(str, Enum):
    INTERN = "estágio"
    TRAINEE = "trainee"
    JUNIOR = "júnior"
    OTHER = "outro"


class Job(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    url: str
    level: Level = Level.OTHER
    modality: Modality = Modality.UNKNOWN
    location: str | None = None
    salary_text: str | None = None
    benefits: list[str] = Field(default_factory=list)
    description: str = ""
    published_at: datetime | None = None

    @property
    def uid(self) -> str:
        """Identificador único global, usado para deduplicar."""
        return f"{self.source}:{self.external_id}"