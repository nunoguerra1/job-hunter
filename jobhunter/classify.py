import re

from jobhunter.models import Level

_PATTERNS: list[tuple[Level, re.Pattern[str]]] = [
    (Level.INTERN, re.compile(r"\b(est[áa]gi[oá]rio|est[áa]gio|intern(ship)?)\b", re.I)),
    (Level.TRAINEE, re.compile(r"\btrainee\b", re.I)),
    (Level.JUNIOR, re.compile(r"\b(j[úu]nior|junior|jr\.?|entry[- ]level)\b", re.I)),
]


def detect_level(title: str) -> Level:
    for level, pattern in _PATTERNS:
        if pattern.search(title):
            return level
    return Level.OTHER

_PCD = re.compile(r"\b(pcds?|pessoas? com defici[eê]ncia)\b", re.I)


def is_pcd_title(title: str) -> bool:
    """Vagas exclusivas para PcD costumam dizer isso no título."""
    return _PCD.search(title) is not None