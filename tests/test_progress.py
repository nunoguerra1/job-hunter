from dataclasses import asdict

from playwright.sync_api import Error as PlaywrightError

from jobhunter.models import Job
from jobhunter.progress import (
    URL,
    Card,
    dump_tabs,
    ensure_applications_page,
    hosts_from_links,
    mark_applied_jobs,
    match_job_uid,
    parse_cards,
    record_cards,
)
from jobhunter.storage import JobStore

SAMPLE = """Minhas candidaturas
Em andamento
Em banco de talentos
Finalizadas

Já concluiu uma etapa e ainda está aguardando? Saiba mais

Venha trabalhar na Zenvia

Desenvolvedor(a) Operações Júnior (remoto)
Não informado
Remoto
Efetivo
Também p/ PcD
Seu Progresso

1/7

Ver andamento da candidatura769354813
Ver andamento
Desistir
Candidatura 1 de 3.

Vendemmia Logística Integrada

Desenvolvedor Júnior
São Paulo - SP
Híbrido
Efetivo
Também p/ PcD
Seu Progresso

0/4

Ver andamento da candidatura768552042
Ver andamento
Desistir
Candidatura 2 de 3.

Instituto de Pesquisas Eldorado

Estágio em Desenvolvimento de Software / Data Mining
Não informado
Remoto
Estágio

Essa é uma vaga de candidatura rápida

Ver andamento da candidatura763693778
Ver andamento
Candidatura 3 de 3.
"""


def make_card(**kwargs) -> Card:
    base = {"application_id": "10", "company": "Zenvia Jobs", "title": "Dev Júnior"}
    return Card(**{**base, **kwargs})


def gupy_job(external_id: str, company: str, title: str, source: str = "gupy") -> Job:
    return Job(
        source=source,
        external_id=external_id,
        title=title,
        company=company,
        url="https://zenvia.gupy.io/job/abc",
    )


def test_parse_cards_reads_progress_and_details():
    cards, announced = parse_cards(SAMPLE, "Em andamento")

    assert announced == 3
    assert [c.application_id for c in cards] == ["769354813", "768552042", "763693778"]
    zenvia = cards[0]
    assert zenvia.company == "Venha trabalhar na Zenvia"
    assert zenvia.title == "Desenvolvedor(a) Operações Júnior (remoto)"
    assert (zenvia.current, zenvia.total) == (1, 7)
    assert zenvia.workplace == "Remoto"
    assert zenvia.contract == "Efetivo"
    vendemmia = cards[1]
    assert vendemmia.location == "São Paulo - SP"
    assert (vendemmia.current, vendemmia.total) == (0, 4)
    quick = cards[2]
    assert quick.current is None
    assert quick.contract == "Estágio"


def test_hosts_from_links():
    hrefs = ["https://zenvia.gupy.io/candidates/applications/769354813", "https://x.com/o"]

    assert hosts_from_links(hrefs) == {"769354813": "zenvia.gupy.io"}


def test_host_match_prefers_the_job_you_engaged_with():
    posting_a = gupy_job("1", "Zenvia Jobs", "Dev Júnior")
    posting_b = gupy_job("2", "Venha trabalhar na Zenvia", "Dev Júnior")
    card = make_card(company="Venha trabalhar na Zenvia", host="zenvia.gupy.io")

    result = match_job_uid(card, [posting_a, posting_b], {"gupy:1": "approved"})

    assert result == ("gupy:1", "link da empresa")


def test_without_host_an_engaged_twin_blocks_the_company_guess():
    posting_a = gupy_job("1", "Zenvia Jobs", "Dev Júnior")
    posting_b = gupy_job("2", "Venha trabalhar na Zenvia", "Dev Júnior")
    card = make_card(company="Venha trabalhar na Zenvia")

    result = match_job_uid(card, [posting_a, posting_b], {"gupy:1": "approved"})

    assert result == ("", "")


def test_unique_company_and_title_matches():
    posting = gupy_job("2", "Venha trabalhar na Zenvia", "Dev Júnior")
    card = make_card(company="Venha trabalhar na Zenvia")

    assert match_job_uid(card, [posting], {}) == ("gupy:2", "nome da empresa")


def test_other_sources_are_ignored():
    posting = gupy_job("2", "Zenvia Jobs", "Dev Júnior", source="adzuna")

    assert match_job_uid(make_card(host="zenvia.gupy.io"), [posting], {}) == ("", "")


def test_record_cards_links_and_marks_applied():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Dev Júnior")])
    store.set_status("gupy:1", "approved")

    record_cards(store, [make_card(host="zenvia.gupy.io", current=1, total=7)])

    assert store.gupy_applications()[0]["job_uid"] == "gupy:1"
    assert mark_applied_jobs(store) == ["gupy:1"]
    assert store.statuses()["gupy:1"] == "applied"
    assert mark_applied_jobs(store) == []


def test_talent_pool_is_not_marked_as_applied():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Dev Júnior")])

    record_cards(store, [make_card(host="zenvia.gupy.io", tab="Em banco de talentos")])

    assert store.gupy_applications()[0]["job_uid"] == "gupy:1"
    assert mark_applied_jobs(store) == []


def test_manual_link_survives_the_next_read():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Outro título")])
    card = make_card(company="Outra empresa")
    record_cards(store, [card])

    assert store.gupy_applications()[0]["job_uid"] == ""
    assert store.link_gupy_application("10", "gupy:1")
    record_cards(store, [card])

    assert store.gupy_applications()[0]["job_uid"] == "gupy:1"

class FakePage:
    def __init__(self, failures: int, url: str):
        self.failures = failures
        self.url = url
        self.calls = 0

    def wait_for_selector(self, selector, timeout):
        self.calls += 1
        if self.calls <= self.failures:
            raise PlaywrightError("timeout")

    def goto(self, url, wait_until):
        self.url = url


def test_logged_in_user_is_not_asked_anything():
    asked = []

    assert ensure_applications_page(FakePage(0, URL), ask=asked.append)
    assert asked == []


def test_logged_out_user_gets_time_to_log_in():
    asked = []
    page = FakePage(1, "https://portal.gupy.io/login")

    assert ensure_applications_page(page, ask=asked.append)
    assert len(asked) == 1


def test_gives_up_after_one_chance_to_log_in():
    asked = []

    assert not ensure_applications_page(FakePage(9, "https://x"), ask=asked.append)
    assert len(asked) == 1

TALENT_POOL_SAMPLE = """Minhas candidaturas
Em andamento
Em banco de talentos
Finalizadas
As inscrições em bancos de talentos não geram candidaturas a vagas específicas.
Vivo (Telefônica Brasil)

Talentos em Tecnologia
Não informado
Remoto
Efetivo
Ver andamento da candidatura757675121
Ver andamento
Candidatura 1 de 1.
"""


def test_parse_cards_ignores_the_talent_pool_banner():
    cards, _ = parse_cards(TALENT_POOL_SAMPLE, "Em banco de talentos")

    assert cards[0].company == "Vivo (Telefônica Brasil)"
    assert cards[0].title == "Talentos em Tecnologia"


def test_two_cards_claiming_the_same_job_are_left_unlinked():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Dev Júnior")])
    cards = [
        make_card(application_id="10", host="zenvia.gupy.io"),
        make_card(application_id="11", host="zenvia.gupy.io"),
    ]

    record_cards(store, cards)

    assert [row["job_uid"] for row in store.gupy_applications()] == ["", ""]


def test_old_automatic_links_do_not_stick():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Outro título")])
    card = make_card(company="Outra empresa")
    store.save_gupy_applications([{**asdict(card), "job_uid": "gupy:1"}])  # ligação automática

    record_cards(store, [card])

    assert store.gupy_applications()[0]["job_uid"] == ""


def test_manual_link_can_be_undone():
    store = JobStore(":memory:")
    store.add_new([gupy_job("1", "Zenvia Jobs", "Outro título")])
    card = make_card(company="Outra empresa")
    record_cards(store, [card])

    assert store.link_gupy_application("10", "gupy:1")
    assert store.link_gupy_application("10", "")
    record_cards(store, [card])

    assert store.gupy_applications()[0]["job_uid"] == ""


def test_dump_tabs_saves_redacted_text(tmp_path):
    def reader(page, limit):
        return {"url": "https://portal.gupy.io/my/applications", "text": "Olá Nuno 99696-4920"}

    saved = dump_tabs(object(), ["Nuno"], tmp_path, opener=lambda page, tab: True, reader=reader)

    assert [path.name for path in saved] == ["aba_1.txt", "aba_2.txt", "aba_3.txt"]
    content = saved[0].read_text(encoding="utf-8")
    assert "Nuno" not in content
    assert "99696" not in content


def test_dump_tabs_skips_tabs_that_do_not_open(tmp_path):
    def reader(page, limit):
        return {"url": "u", "text": "texto"}

    saved = dump_tabs(
        object(), [], tmp_path, opener=lambda page, tab: tab != "Finalizadas", reader=reader
    )

    assert [path.name for path in saved] == ["aba_1.txt", "aba_2.txt"]