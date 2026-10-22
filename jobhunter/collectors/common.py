import html
import re
from datetime import UTC, datetime

from jobhunter.classify import detect_level
from jobhunter.filters import normalize
from jobhunter.models import Level, Modality

BRAZIL_TERMS = ("brasil", "brazil", "latam", "latin america", "america latina", "anywhere")
HYBRID_TERMS = ("hybrid", "hibrido")
REMOTE_TERMS = ("remote", "remoto", "home office", "teletrabalho", "anywhere")


def accepts_location(location: str) -> bool:
    """Para empresas globais: o local precisa citar Brasil, LATAM ou 'anywhere'."""
    text = normalize(location)
    return any(term in text for term in BRAZIL_TERMS)


def modality_from_text(text: str) -> Modality:
    lowered = normalize(text)
    if any(term in lowered for term in HYBRID_TERMS):
        return Modality.HYBRID
    if any(term in lowered for term in REMOTE_TERMS):
        return Modality.REMOTE
    return Modality.UNKNOWN


def is_entry_level(title: str) -> bool:
    """Estágio, trainee ou júnior, pelo título. Corta as centenas de vagas sêniores."""
    return detect_level(title) is not Level.OTHER


def strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def from_millis(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)