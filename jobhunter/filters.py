import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from jobhunter.models import Job, Modality
from jobhunter.profile import Profile

SENIOR_TERMS = [
    "senior", "pleno", "especialista", "lead", "tech lead", "coordenador", "gerente",
]
MIN_SKILL_HITS = 2


@dataclass
class FilterResult:
    keep: bool
    reason: str | None = None
    area: str | None = None


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _contains(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(normalize(term))}\b", text) is not None

def is_open(job: Job, today: date | None = None) -> bool:
    """Falso quando o prazo de inscrição já passou. Sem prazo informado, presume aberta."""
    today = today or date.today()
    return not (job.deadline and job.deadline.date() < today)

def prefilter(job: Job, profile: Profile, today: date | None = None) -> FilterResult:
    today = today or date.today()
    title = normalize(job.title)

    if job.pcd:
        return FilterResult(False, "vaga PcD")
    if not is_open(job, today):
        return FilterResult(False, "prazo vencido")
    if job.modality != Modality.UNKNOWN and job.modality not in profile.modalities:
        return FilterResult(False, "modalidade não aceita")
    if any(_contains(title, t) for t in profile.excluded_title_keywords):
        return FilterResult(False, "área excluída (suporte)")
    if any(_contains(title, t) for t in SENIOR_TERMS):
        return FilterResult(False, "nível acima do seu")

    for area in sorted(profile.areas, key=lambda a: a.weight, reverse=True):
        if any(_contains(title, k) for k in area.keywords):
            return FilterResult(True, area=area.name)

    description = normalize(job.description)
    hits = sum(1 for skill in profile.skills if _contains(description, skill))
    if hits >= MIN_SKILL_HITS:
        return FilterResult(True, area="indefinida (pela descrição)")

    return FilterResult(False, "fora de TI")