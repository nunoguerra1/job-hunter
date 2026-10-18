from jobhunter.application import prepare_application, render_markdown, salary_answer
from jobhunter.models import Job
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


def test_salary_answer_uses_job_salary():
    job = make_job("Bolsa auxílio de R$ 2.100,00 e vale refeição")
    assert "R$ 2.100,00" in salary_answer(job, PROFILE)


def test_salary_answer_uses_profile_floor():
    assert "R$ 1.200" in salary_answer(make_job(), PROFILE)


def test_render_marks_draft():
    app = prepare_application(make_job(), PROFILE, BANK, FakeLLM())
    assert "RASCUNHO" in render_markdown(make_job(), None, app)