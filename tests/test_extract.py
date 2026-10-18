from jobhunter.extract import extract_benefits, extract_salary


def test_extract_salary_single_value():
    assert extract_salary("Bolsa auxílio de R$ 2.100,00 + vale refeição") == "R$ 2.100,00"


def test_extract_salary_range():
    text = "Bolsa-auxílio: R$ 1.800,00 a R$ 2.000,00 por mês"
    assert extract_salary(text) == "R$ 1.800,00 a R$ 2.000,00"


def test_extract_salary_absent():
    assert extract_salary("Venha crescer com a gente! Bolsa compatível com o mercado.") is None


def test_extract_benefits():
    text = "Benefícios: Vale-refeição, plano de saúde e Gympass"
    assert extract_benefits(text) == ["Vale-refeição", "Plano de saúde", "Gympass/Wellhub"]