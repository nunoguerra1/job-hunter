from jobhunter.phases import (
    current_and_next,
    parse_phases,
    save_debug,
    stage_label,
    wait_for_phases,
)
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

class SlowPage:
    """Página que ainda está montando: devolve um texto diferente a cada leitura."""

    url = "https://zenvia.gupy.io/candidates/applications/1"

    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0

    def wait_for_load_state(self, state, timeout):
        pass

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, script):
        text = self.texts[min(self.calls, len(self.texts) - 1)]
        self.calls += 1
        return text

    def title(self):
        return "Gupy"


def test_wait_for_phases_waits_for_the_list_to_render():
    page = SlowPage(["Carregando...", ZENVIA])

    names, text = wait_for_phases(page, tries=5)

    assert names == NAMES
    assert page.calls == 2
    assert "Currículo" in text


def test_wait_for_phases_gives_up_with_the_last_text():
    page = SlowPage(["Entre com seu e-mail"])

    assert wait_for_phases(page, tries=3) == ([], "Entre com seu e-mail")
    assert page.calls == 3


def test_save_debug_redacts_personal_data(tmp_path):
    path = save_debug("10", "Olá Nuno, nuno@gmail.com", ["Nuno"], tmp_path)
    content = path.read_text(encoding="utf-8")

    assert path.name == "fases_10.txt"
    assert "Nuno" not in content
    assert "gmail" not in content

def test_stage_label_handles_quick_applications():
    assert stage_label({"current": None, "total": None}) == "candidatura rápida"
    assert stage_label({"current": 1, "total": 7}) == "1/7"