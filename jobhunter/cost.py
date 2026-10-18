import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel

from jobhunter.extract import extract_salary
from jobhunter.filters import normalize
from jobhunter.models import Job, Modality

_FIRST_MONEY = re.compile(r"R\$\s?(\d+(?:\.\d{3})*)")


class CityCost(BaseModel):
    rent: int
    food: int
    transport: int
    other: int

    @property
    def total(self) -> int:
        return self.rent + self.food + self.transport + self.other


class CostTable:
    def __init__(self, default: CityCost, cities: dict[str, CityCost]):
        self.default = default
        self.cities = {normalize(name): cost for name, cost in cities.items()}

    def get(self, city: str | None) -> tuple[CityCost, bool]:
        """Devolve o custo e se a cidade foi encontrada na tabela (senão, usa a média)."""
        if city:
            key = normalize(city.split(",")[0].strip())
            if key in self.cities:
                return self.cities[key], True
        return self.default, False


@dataclass
class Estimate:
    cost: int
    city_known: bool
    salary: int | None
    surplus: int | None


def load_costs(path: str = "config/cost_of_living.yaml") -> CostTable:
    with Path(path).open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    return CostTable(
        default=CityCost(**raw["default"]),
        cities={name: CityCost(**values) for name, values in raw["cities"].items()},
    )


def parse_salary(text: str | None) -> int | None:
    """Primeiro valor em reais do texto (no caso de faixa, o menor)."""
    if not text:
        return None
    match = _FIRST_MONEY.search(text)
    return int(match.group(1).replace(".", "")) if match else None


def estimate(job: Job, home_city: str, table: CostTable) -> Estimate:
    city = home_city if job.modality == Modality.REMOTE else job.location
    cost_info, known = table.get(city)
    salary = parse_salary(job.salary_text or extract_salary(job.description))
    cost = cost_info.total
    return Estimate(cost, known, salary, salary - cost if salary is not None else None)


def brl(value: int) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}R$ {abs(value):,}".replace(",", ".")