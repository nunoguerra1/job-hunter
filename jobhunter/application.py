from pydantic import BaseModel

from jobhunter.extract import extract_salary
from jobhunter.llm import LLM
from jobhunter.match import MatchResult, _candidate_block, _job_block
from jobhunter.models import Job
from jobhunter.profile import Profile
from jobhunter.stories import StoryBank


class Draft(BaseModel):
    company_values: list[str]
    story_ids: list[str]
    why_us: str
    cv_summary: str
    cv_highlight_ids: list[str]


class Application(BaseModel):
    company_values: list[str]
    story_ids: list[str]
    why_us: str
    cv_summary: str
    cv_highlights: list[str]
    salary_answer: str


INTRO = (
    "Você é um recrutador sênior de RH ajudando um candidato a se candidatar a uma vaga.\n"
    "Responda SOMENTE com JSON no esquema pedido."
)

RULES = """REGRAS
- company_values: 3 a 5 valores ou traços de cultura que a descrição da vaga evidencia
  (ex.: inovação, ownership, impacto social). Se a descrição não mostrar nenhum,
  devolva lista vazia e NÃO invente valores.
- story_ids: 1 ou 2 ids de histórias que melhor provam os valores da empresa.
- why_us: resposta para "Por que você quer trabalhar conosco?", em primeira pessoa,
  3 parágrafos curtos (cerca de 900 a 1.100 caracteres): (1) gancho específico sobre a
  empresa ou a vaga, (2) prova prática usando as histórias escolhidas, (3) fechamento
  com o que o candidato quer construir e entregar.
- Tom profissional e natural. Proibido: clichês ("sempre sonhei", "empresa de renome")
  e adjetivos vazios.
- Use SOMENTE fatos das histórias, do perfil e da vaga. Não invente números, cargos
  ou tecnologias.
- cv_summary: 2 a 3 frases de resumo profissional adaptado à vaga, só com fatos do perfil.
- cv_highlight_ids: de 4 a 6 ids de cv_highlights, do mais ao menos relevante."""


def build_prompt(job: Job, profile: Profile, bank: StoryBank) -> str:
    stories = "\n".join(
        f"[{s.id}] tags: {', '.join(s.tags)} | Situação: {s.situation} | Tarefa: {s.task} "
        f"| Ação: {s.action} | Resultado: {s.result}"
        for s in bank.stories
    )
    highlights = "\n".join(f"[{h.id}] {h.text}" for h in bank.cv_highlights)
    return (
        f"{INTRO}\n\n{_candidate_block(profile)}\n\n"
        f"HISTÓRIAS DISPONÍVEIS\n{stories}\n\n"
        f"CV_HIGHLIGHTS DISPONÍVEIS\n{highlights}\n\n"
        f"VAGA\n{_job_block(job, 5000)}\n\n{RULES}"
    )


def salary_answer(job: Job, profile: Profile) -> str:
    """Regra fixa, sem IA: nunca inventa valor."""
    stated = job.salary_text or extract_salary(job.description)
    if stated:
        return f"Estou de acordo com a bolsa-auxílio prevista na vaga ({stated})."
    if profile.min_salary:
        value = f"{profile.min_salary:,}".replace(",", ".")
        return (
            f"Minha pretensão é de R$ {value} mensais, "
            "aberto a conversar conforme benefícios e carga horária."
        )
    return "A combinar, de acordo com a faixa prevista pela empresa."


def prepare_application(job: Job, profile: Profile, bank: StoryBank, llm: LLM) -> Application:
    draft = llm.generate_json(build_prompt(job, profile, bank), Draft)
    known_stories = {story.id for story in bank.stories}
    highlights = {h.id: h.text for h in bank.cv_highlights}
    chosen = [highlights[i] for i in draft.cv_highlight_ids if i in highlights]
    return Application(
        company_values=draft.company_values,
        story_ids=[i for i in draft.story_ids if i in known_stories],
        why_us=draft.why_us,
        cv_summary=draft.cv_summary,
        cv_highlights=chosen or list(highlights.values())[:5],
        salary_answer=salary_answer(job, profile),
    )


def render_markdown(job: Job, result: MatchResult | None, app: Application) -> str:
    values = ", ".join(app.company_values) or "não identificados na descrição"
    highlights = "\n".join(f"- {text}" for text in app.cv_highlights)
    score = f"{result.score}/100 - {result.summary}" if result else "sem nota"
    return f"""# {job.title} - {job.company}

> RASCUNHO gerado por IA. Revise tudo antes de enviar.

- Link: {job.url}
- Nota de match: {score}
- Valores identificados: {values}

## Por que você quer trabalhar conosco?

{app.why_us}

## Pretensão salarial

{app.salary_answer}

## Resumo profissional (currículo)

{app.cv_summary}

## Destaques do currículo

{highlights}
"""