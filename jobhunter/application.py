from pydantic import BaseModel

from jobhunter.extract import extract_salary
from jobhunter.filters import normalize
from jobhunter.llm import LLM
from jobhunter.match import MatchResult, _candidate_block, _job_block
from jobhunter.models import Job, Modality
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

RULES = """REGRAS GERAIS
- Use SOMENTE fatos das histórias, do perfil, da motivação e da vaga. Não invente números,
  cargos, tecnologias nem motivações.
- company_values: de 3 a 5 valores que a descrição evidencia, com as palavras da empresa.
  Se a descrição não mostrar nenhum, devolva lista vazia.
- story_ids: 2 histórias que provem os 2 valores mais fortes da vaga. Prefira histórias
  com resultado concreto.

REGRAS DO why_us (3 parágrafos, 900 a 1.100 caracteres no total)
1. Gancho: um desafio, produto ou atividade ESPECÍFICA da vaga, ligado a algo concreto que o
   candidato já fez. Não elogie a empresa e não parafraseie o marketing dela.
2. Prova: no máximo 2 valores, cada um sustentado por uma história que REALMENTE o demonstre:
   inovação = projetos próprios, uso de IA, tecnologias novas; qualidade = testes e
   padronização; respeito às pessoas = capacitação e seleção; senso de dono = liderança e
   entrega ponta a ponta. Se nenhuma história sustenta um valor, NÃO cite esse valor.
   Cada valor vem com o que o candidato fez e o resultado, sem frases como "sustento o
   valor de".
3. Motivação: explique em uma frase, com palavras próprias e como ESCOLHA (quer estar no
   código, em um time de produto, e leva a visão de gestão como diferencial). Nunca de forma
   defensiva, sem "mesmo já tendo" nem pedidos de desculpa.
4. Fechamento: 1 ou 2 entregas dos primeiros meses, só com atividades que aparecem na vaga
   E que o candidato comprovadamente já fez nas histórias ou no perfil. Não prometa
   documentação nem outras tarefas sem base.

PROIBIDO: "ambiente ideal", "reflete a visão que busco", "perfeitamente", "contribuindo
ativamente", "de forma autônoma", "líder do mercado", "sempre sonhei", "empresa de renome"
e qualquer elogio genérico à empresa.

cv_summary: 2 frases. A primeira diz quem é (curso, cargo e a evolução, quando as histórias
mostrarem). A segunda liga a experiência à vaga. Só fatos do perfil.
cv_highlight_ids: de 4 a 6 ids, do mais ao menos relevante PARA ESTA VAGA; inclua um de
liderança quando existir."""


def build_prompt(job: Job, profile: Profile, bank: StoryBank) -> str:
    stories = "\n".join(
        f"[{s.id}] tags: {', '.join(s.tags)} | Situação: {s.situation} | Tarefa: {s.task} "
        f"| Ação: {s.action} | Resultado: {s.result}"
        for s in bank.stories
    )
    highlights = "\n".join(f"[{h.id}] {h.text}" for h in bank.cv_highlights)
    motivation = profile.motivation or "não informada"
    return (
        f"{INTRO}\n\n{_candidate_block(profile)}\n"
        f"- Motivação para buscar estágio (palavras do candidato): {motivation}\n\n"
        f"HISTÓRIAS DISPONÍVEIS\n{stories}\n\n"
        f"CV_HIGHLIGHTS DISPONÍVEIS\n{highlights}\n\n"
        f"VAGA\n{_job_block(job, 5000)}\n\n{RULES}"
    )


def _same_city(location: str | None, home_city: str) -> bool:
    if not location:
        return False
    return normalize(location.split(",")[0].strip()) == normalize(home_city.strip())


def salary_answer(job: Job, profile: Profile) -> str:
    """Regra fixa, sem IA: nunca inventa valor."""
    stated = job.salary_text or extract_salary(job.description)
    if stated:
        return f"Estou de acordo com a bolsa-auxílio prevista na vaga ({stated})."
    relocation = job.modality in {Modality.ONSITE, Modality.HYBRID} and not _same_city(
        job.location, profile.city
    )
    if relocation:
        return "A combinar, de acordo com a faixa prevista pela empresa para o programa."
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