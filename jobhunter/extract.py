import re

from jobhunter.match import clean_description

_MONEY = r"R\$\s?\d+(?:\.\d{3})*(?:,\d{2})?"
_SALARY = re.compile(
    r"(?:bolsa[\s-]*aux[íi]lio|bolsa|sal[áa]rio|remunera[çc][ãa]o)"
    rf"[^$]{{0,40}}?({_MONEY}(?:\s*(?:até|a|à|-|–)\s*{_MONEY})?)",
    re.I,
)

_BENEFITS = {
    "Vale-refeição": r"vale[\s-]*refei[çc][ãa]o|\bvr\b",
    "Vale-alimentação": r"vale[\s-]*alimenta[çc][ãa]o|\bva\b",
    "Vale-transporte": r"vale[\s-]*transporte|\bvt\b",
    "Plano de saúde": r"plano de sa[úu]de|assist[êe]ncia m[ée]dica",
    "Plano odontológico": r"plano odontol[óo]gico|assist[êe]ncia odontol[óo]gica",
    "Seguro de vida": r"seguro de vida",
    "Gympass/Wellhub": r"gympass|wellhub|totalpass",
    "Auxílio home office": r"aux[íi]lio[\s-]*home[\s-]*office",
    "Recesso remunerado": r"recesso",
}


def extract_salary(description: str) -> str | None:
    match = _SALARY.search(clean_description(description))
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def extract_benefits(description: str) -> list[str]:
    text = clean_description(description)
    return [name for name, pattern in _BENEFITS.items() if re.search(pattern, text, re.I)]