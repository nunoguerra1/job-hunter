from jobhunter.match import MatchResult, clean_description, score_job
from jobhunter.models import Job
from jobhunter.profile import load_profile

PROFILE = load_profile("profile/profile.example.yaml")


class FakeLLM:
    def __init__(self):
        self.prompts: list[str] = []

    def generate_json(self, prompt, schema):
        self.prompts.append(prompt)
        return schema(
            score=85,
            course_compatible=True,
            matched_skills=["python"],
            missing_skills=[],
            summary="ok",
        )


def test_score_job_uses_fake_llm_and_hides_name():
    job = Job(source="t", external_id="1", title="Estágio Python", company="Acme", url="u")
    llm = FakeLLM()
    result = score_job(job, PROFILE, llm)

    assert isinstance(result, MatchResult)
    assert result.score == 85
    assert "Estágio Python" in llm.prompts[0]
    assert "Inglês (avançado)" in llm.prompts[0]
    assert PROFILE.name not in llm.prompts[0]


def test_clean_description_strips_html_and_entities():
    assert clean_description("<p>Olá&nbsp;mundo</p>") == "Olá mundo"