import pytest

from jobhunter.classify import detect_level
from jobhunter.models import Level


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Estagiário de Dados", Level.INTERN),
        ("Software Engineering Intern", Level.INTERN),
        ("Programa Trainee 2027", Level.TRAINEE),
        ("Desenvolvedor Python Júnior", Level.JUNIOR),
        ("Backend Developer Jr", Level.JUNIOR),
        ("Senior Data Engineer", Level.OTHER),
    ],
)
def test_detect_level(title, expected):
    assert detect_level(title) == expected