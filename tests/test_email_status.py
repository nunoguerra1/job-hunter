import pytest

from jobhunter.email_status import Kind, classify_email, guess_company

ME = "eu@gmail.com"
GUPY = "Empresa <no-reply@gupy.com.br>"

CASES = [
    # (assunto, trecho, remetente, esperado)
    ("Inscrição recebida para a vaga Desenvolvedor Júnior", "", GUPY, Kind.RECEIVED),
    ("Candidatura recebida com sucesso!", "", GUPY, Kind.RECEIVED),
    ("C6 Bank | Recebemos sua candidatura!", "", "x <a@us.greenhouse-mail.io>", Kind.RECEIVED),
    ("Nuno, sua candidatura foi enviada à Infinite Cloud", "", "L <a@linkedin.com>", Kind.RECEIVED),
    ("ERRATA: você avançou de etapa no Programa de Estágio TOTVS 2026", "", GUPY, Kind.ADVANCED),
    ("Convocação para Assessments Localiza", "", GUPY, Kind.ACTION),
    ("Últimas horas para confirmar sua presença! | Processo Seletivo", "", GUPY, Kind.ACTION),
    ("Visagio Talentos - Conclua as etapas online!", "", GUPY, Kind.ACTION),
    ("Chegou o seu link de acesso!", "", GUPY, Kind.IRRELEVANT),
    ("Reprovação etapa de testes - Estágio Itaú 2026", "", GUPY, Kind.REJECTED),
    ("Processo Seletivo Finalizado", "", GUPY, Kind.ENDED),
    ("Processo seletivo encerrado", "", GUPY, Kind.ENDED),
    ("Nuno, treine a entrevista da sua primeira vaga", "", "DIO <contato@dio.me>",
     Kind.IRRELEVANT),
    ("Dúvidas sobre o processo seletivo? vem pro Videocast!", "", "E <a@eureca.me>",
     Kind.IRRELEVANT),
    ("Estágio Em Dados na Vertem e 4 outras vagas", "", "G <a@glassdoor.com>", Kind.IRRELEVANT),
    ("Meetup Itaú Tech 2026 | Inscrições abertas!", "", "I <a@inbound.gupy.com.br>",
     Kind.IRRELEVANT),
    ("Nuno, candidate-se agora à vaga de Estágio", "", "L <a@linkedin.com>", Kind.IRRELEVANT),
    # e-mails enviados por você
    ("Candidatura para Estágio FOP no The Best", "Olá, meu nome é", f"Nuno <{ME}>", Kind.SENT),
    # assuntos genéricos: o trecho decide
    ("RE: Candidatura para Estágio FOP no The Best",
     "Recebemos seu currículo e, após a análise, entraremos em contato.",
     "Ana <ana@ogrupothebest.com>", Kind.RECEIVED),
    ("Retorno do Processo Seletivo",
     "RNP - Estagiário de Engenharia de IA Nova mensagem referente à vaga X: Olá",
     GUPY, Kind.MESSAGE),
    ("Atualização sobre o processo seletivo",
     "Infelizmente seguiremos com outros candidatos neste momento.",
     "Academia <a@academiadouniversitario.com.br>", Kind.REJECTED),
    ("Atualização sobre o processo seletivo",
     "Agradecemos seu interesse na oportunidade de Programa de Estágio",
     "Academia <a@academiadouniversitario.com.br>", Kind.UNKNOWN),
]


@pytest.mark.parametrize(("subject", "snippet", "sender", "expected"), CASES)
def test_classify_email(subject, snippet, sender, expected):
    assert classify_email(subject, snippet, sender, ME) == expected


def test_guess_company_from_gupy_message_snippet():
    snippet = (
        "COIMEX ADMINISTRADORA - Assistente de Desenvolvimento "
        "Nova mensagem referente à vaga X"
    )

    assert guess_company("Gupy", "gupy.com.br", "Chegaram notícias", snippet) == (
        "COIMEX ADMINISTRADORA"
    )


def test_guess_company_greenhouse_subject():
    subject = "C6 Bank | Recebemos sua candidatura!"

    assert guess_company("x", "us.greenhouse-mail.io", subject, "") == "C6 Bank"


def test_guess_company_platform_sender_is_unknown():
    assert guess_company("LinkedIn", "linkedin.com", "sua candidatura foi enviada", "") == ""


def test_guess_company_uses_sender_name():
    assert guess_company("ITAU UNIBANCO S.A.", "itau.com.br", "Reprovação", "") == (
        "ITAU UNIBANCO S.A."
    )

def test_guess_company_uses_the_name_when_a_platform_sends_for_the_company():
    name = "Vendemmia Logística Integrada"

    assert guess_company(name, "gupy.com.br", "Inscrição recebida", "") == name


def test_guess_company_from_linkedin_subject():
    subject = "Nuno, sua candidatura foi enviada à Infinite Cloud"

    assert guess_company("LinkedIn", "linkedin.com", subject, "") == "Infinite Cloud"


def test_guess_company_platform_domain_without_name_is_unknown():
    assert guess_company("", "gupy.com.br", "Algo", "") == ""

def test_reminder_to_finish_the_application_is_not_an_unclear_e_mail():
    snippet = (
        "Olá Nuno, tudo bem? Você se inscreveu na vaga Desenvolvedor Júnior há três dias, "
        "mas ainda não finalizou a sua candidatura."
    )

    assert classify_email("Retorno do Processo Seletivo", snippet, GUPY, ME) == Kind.INCOMPLETE
    assert classify_email("Finalize sua candidatura!", "", GUPY, ME) == Kind.INCOMPLETE