import html
import re

from pydantic import BaseModel, Field

from jobhunter.llm import LLM
from jobhunter.models import Job
from jobhunter.profile import Profile


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    course_compatible: bool
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str


def clean_description(raw: str, limit: int = 6000) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:limit]

def _join(items: list[str]) -> str:
    return "; ".join(items) if items else "não informado"

def build_prompt(job: Job, profile: Profile) -> str:
    return f"""\
Você é um recrutador sênior de tecnologia avaliando a adequação de um candidato a uma vaga.
Avalie com rigor e honestidade, sem inflar a nota. Responda SOMENTE com JSON no esquema pedido.

CANDIDATO
- Curso: {profile.course} (previsão de formatura: {profile.expected_graduation:%m/%Y})
- Habilidades: {", ".join(profile.skills)}
- Idiomas: {_join(profile.languages)}
- Experiência: {_join(profile.experience)}
- Projetos: {_join(profile.projects)}
- Resumo: {profile.summary}

VAGA
- Título: 
{job.title}
- Empresa: 
{job.company}
- Nível: 
{job.level.value}
- Modalidade: 
{job.modality.value}
- Descrição: 
{clean_description(job.description)}

CRITÉRIOS
- score de 0 a 100: 80+ candidatura muito forte; 60-79 vale tentar; abaixo de 60 fraca.
- course_compatible: false se a vaga exige curso ou área incompatível com o candidato.
- matched_skills e missing_skills: somente habilidades citadas pela vaga.
- summary: 1 a 2 frases em português explicando a nota.
- Não invente requisitos que não estão na descrição."""


def score_job(job: Job, profile: Profile, llm: LLM) -> MatchResult:
    return llm.generate_json(build_prompt(job, profile), MatchResult)