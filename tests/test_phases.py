from jobhunter.phases import current_and_next, parse_phases
from jobhunter.storage import JobStore

ZENVIA = """Gupy

Desenvolvedor(a) Operações Júnior (remoto)

Acompanhe abaixo o andamento de cada etapa do seu processo seletivo.

Seu progresso
1/7

Dica da Gupy: Enquanto aguarda os próximos passos, que tal conferir dicas?

A última movimentação de pessoas candidatas nesta vaga aconteceu há 3 dias.

1
Currículo
Mais de 100 pessoas candidatas nesta etapa.
Ver
2
Pré-entrevista
Nenhuma pessoa candidata nesta etapa.
3
Entrevista RH
Nenhuma pessoa candidata nesta etapa.
4
Teste de Raciocínio Lógico
Entre 1-10 pessoas candidatas nesta etapa.
5
Entrevista Gestor
Nenhuma pessoa candidata nesta etapa.
6
Carta Oferta
Nenhuma pessoa candidata nesta etapa.
7
Final
Nenhuma pessoa candidata nesta etapa.
Gupy 2026. Todos os direitos reservados. v5.61.0
?
27
"""

NAMES = [
    "Currículo",
    "Pré-entrevista",
    "Entrevista RH",
    "Teste de Raciocínio Lógico",
    "Entrevista Gestor",
    "Carta Oferta",
    "Final",
]


def test_parse_phases_reads_the_real_zenvia_page():
    assert parse_phases(ZENVIA) == NAMES


def test_parse_phases_ignores_unrelated_numbers():
    assert parse_phases("27\nMais de 100\nCandidatura 1 de 12.") == []


def test_current_and_next():
    assert current_and_next(1, NAMES) == ("Currículo", "Pré-entrevista")
    assert current_and_next(0, NAMES) == ("", "Currículo")
    assert current_and_next(7, NAMES) == ("Final", "")
    assert current_and_next(None, NAMES) == ("", "")
    assert current_and_next(3, []) == ("", "")


def test_phases_roundtrip():
    store = JobStore(":memory:")

    store.save_gupy_phases("10", NAMES)

    assert store.gupy_phases() == {"10": NAMES}