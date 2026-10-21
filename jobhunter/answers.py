import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from jobhunter.filters import normalize

SENSITIVE_TERMS = [
    "remuneracao", "salario", "salarial", "pretensao", "bolsa", "beneficio", "beneficios",
    "mudanca", "mudar", "residir", "residencia", "morar", "disponibilidade", "acesso",
    "localizacao", "regiao", "deslocamento", "viajar", "viagens", "cidade",
    "cnh", "habilitacao", "veiculo",
    "deficiencia", "pcd", "laudo", "saude",
    "cpf", "rg", "passaporte", "nacionalidade", "estado civil",
    "genero", "raca", "etnia", "orientacao sexual", "religiao",
    "antecedentes", "criminal", "parentes", "parentesco",
]
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class Rule(BaseModel):
    when: list[str]
    choose: list[str] = Field(default_factory=list)
    text: str | None = None
    ask: bool = False
    force: bool = False


class Answers(BaseModel):
    rules: list[Rule] = Field(default_factory=list)


@dataclass
class Plan:
    key: str
    kind: str
    question: str
    action: str  # "fill" ou "human"
    values: list[str]
    reason: str


def load_answers(path: str = "profile/answers.yaml") -> Answers:
    with Path(path).open(encoding="utf-8") as file:
        return Answers.model_validate(yaml.safe_load(file) or {})


def is_sensitive(question: str) -> bool:
    text = normalize(question)
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in SENSITIVE_TERMS)


def _human(q: dict, reason: str) -> Plan:
    return Plan(q["key"], q["kind"], q["question"], "human", [], reason)


def plan_question(q: dict, answers: Answers, context: dict[str, str]) -> Plan:
    text = normalize(q["question"])
    rule = next((r for r in answers.rules if all(normalize(w) in text for w in r.when)), None)
    if rule is None:
        return _human(q, "sem regra")
    if rule.ask:
        return _human(q, "marcada para você responder")
    if is_sensitive(q["question"]) and not rule.force:
        return _human(q, "assunto sensível: responda você")

    if q["kind"] == "text":
        if not rule.text:
            return _human(q, "regra sem 'text'")
        missing = [name for name in _PLACEHOLDER.findall(rule.text) if not context.get(name)]
        if missing:
            return _human(q, "sem valor para " + ", ".join(missing))
        value = _PLACEHOLDER.sub(lambda m: context[m.group(1)], rule.text)
        return Plan(q["key"], "text", q["question"], "fill", [value], "regra")

    if not rule.choose:
        return _human(q, "regra sem 'choose'")
    options = {normalize(option): option for option in q["options"]}
    unknown = [c for c in rule.choose if normalize(c) not in options]
    if unknown:
        return _human(q, "opção não encontrada: " + ", ".join(unknown))
    if q["kind"] in {"single", "select"} and len(rule.choose) != 1:
        return _human(q, "esta pergunta aceita só 1 opção")
    values = [options[normalize(c)] for c in rule.choose]
    return Plan(q["key"], q["kind"], q["question"], "fill", values, "regra")


def plan_step(questions: list[dict], answers: Answers, context: dict[str, str]) -> list[Plan]:
    return [plan_question(q, answers, context) for q in questions]