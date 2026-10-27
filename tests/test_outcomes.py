from jobhunter.progress import OUTCOME_STATUS, result_label


def test_frozen_postings_have_a_short_label():
    assert OUTCOME_STATUS["Vaga congelada pela empresa"] == "Congelada"
    assert result_label({"outcome": "Vaga congelada pela empresa"}) == "Congelada"


def test_unknown_outcome_text_is_shown_as_written():
    assert result_label({"outcome": "Algo novo"}) == "Algo novo"