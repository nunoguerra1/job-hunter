from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Modality(StrEnum):
    REMOTE = "home office"
    ONSITE = "presencial"
    HYBRID = "híbrida"
    UNKNOWN = "não informado"


class Level(StrEnum):
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
    deadline: datetime | None = None
    pcd: bool = False  # marcada pela Gupy como vaga para PcD

    @property
    def uid(self) -> str:
        """Identificador único global, usado para deduplicar."""
        return f"{self.source}:{self.external_id}"