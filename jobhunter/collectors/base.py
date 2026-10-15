from abc import ABC, abstractmethod

from jobhunter.models import Job


class Collector(ABC):
    """Todo coletor de vagas implementa fetch() e devolve vagas normalizadas."""

    name: str

    @abstractmethod
    def fetch(self) -> list[Job]:
        ...