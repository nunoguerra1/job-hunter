from jobhunter.application import (
    build_prompt,
    prepare_application,
    render_markdown,
    salary_answer,
)
from jobhunter.models import Job, Modality
from jobhunter.profile import load_profile
from jobhunter.stories import load_story_bank

PROFILE = load_profile("profile/profile.example.yaml")
BANK = load_story_bank("profile/story_bank.example.yaml", strict=False)


def make_job(description: str = "") -> Job:
    return Job(source="t", external_id="1", title="Estágio Dev", company="Acme", url="u",
               description=description)


class FakeLLM:
    def generate_json(self, prompt, schema):
        return schema(
            company_values=["inovação"],
            story_ids=["lideranca-dev", "nao-existe"],
            why_us="texto",
            cv_summary="resumo",
            cv_highlight_ids=["h-lideranca", "x"],
        )


def test_prepare_drops_unknown_ids():
    app = prepare_application(make_job(), PROFILE, BANK, FakeLLM())
    assert app.story_ids == ["lideranca-dev"]
    assert len(app.cv_highlights) == 1
    assert app.cv_highlight_ids == ["h-lideranca"]


def test_salary_answer_uses_job_salary():
    job = make_job("Bolsa auxílio de R$ 2.100,00 e vale refeição")
    assert "R$ 2.100,00" in salary_answer(job, PROFILE)


def test_salary_answer_uses_profile_floor():
    assert "R$ 1.200" in salary_answer(make_job(), PROFILE)


def test_render_marks_draft():
    app = prepare_application(make_job(), PROFILE, BANK, FakeLLM())
    assert "RASCUNHO" in render_markdown(make_job(), None, app)

def test_salary_relocation_is_negotiable():
    job = Job(source="t", external_id="1", title="Dev", company="c", url="u",
              modality=Modality.HYBRID, location="Barueri, São Paulo")
    assert salary_answer(job, PROFILE).startswith("A combinar")


def test_salary_remote_uses_floor():
    job = Job(source="t", external_id="1", title="Dev", company="c", url="u",
              modality=Modality.REMOTE)
    assert "R$ 1.200" in salary_answer(job, PROFILE)


def test_salary_onsite_in_home_city_uses_floor():
    job = Job(source="t", external_id="1", title="Dev", company="c", url="u",
              modality=Modality.ONSITE, location="Cornélio Procópio, Paraná")
    assert "R$ 1.200" in salary_answer(job, PROFILE)


def test_prompt_includes_motivation_and_bans_cliches():
    prompt = build_prompt(make_job(), PROFILE, BANK)
    assert "Motivação para buscar estágio" in prompt
    assert "contribuindo" in prompt  # lista de frases proibidas
    assert "Se nenhuma história sustenta um valor" in prompt