from jobhunter.cost import CityCost, CostTable, brl, estimate, load_costs, parse_salary
from jobhunter.models import Job, Modality

TABLE = CostTable(
    default=CityCost(rent=1500, food=850, transport=300, other=500),
    cities={"Campinas": CityCost(rent=1700, food=850, transport=300, other=500)},
)


def make_job(modality: Modality, location: str | None, salary: str | None = None) -> Job:
    return Job(source="t", external_id="1", title="Dev", company="c", url="u",
               modality=modality, location=location, salary_text=salary)


def test_parse_salary():
    assert parse_salary("R$ 2.100,00") == 2100
    assert parse_salary("R$ 1.800,00 a R$ 2.000,00") == 1800
    assert parse_salary("R$ 900") == 900
    assert parse_salary(None) is None


def test_onsite_uses_job_city():
    result = estimate(make_job(Modality.ONSITE, "Campinas, São Paulo", "R$ 2.500,00"),
                      "Londrina", TABLE)
    assert result.cost == 3350
    assert result.city_known
    assert result.surplus == -850


def test_remote_uses_home_city():
    result = estimate(make_job(Modality.REMOTE, None), "Campinas", TABLE)
    assert result.cost == 3350


def test_unknown_city_falls_back_to_default():
    result = estimate(make_job(Modality.ONSITE, "Xanadu, GO"), "Campinas", TABLE)
    assert result.cost == 3150
    assert not result.city_known
    assert result.surplus is None


def test_brl():
    assert brl(1500) == "R$ 1.500"
    assert brl(-400) == "-R$ 400"


def test_config_file_loads():
    table = load_costs()
    cost, known = table.get("Campinas, São Paulo")
    assert known
    assert cost.total > 0