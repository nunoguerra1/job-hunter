import pytest

from jobhunter.email_status import Kind, classify_email

CASES = [
    ("Inscrição recebida para a vaga Desenvolvedor Júnior", Kind.RECEIVED),
    ("Candidatura recebida com sucesso!", Kind.RECEIVED),
    ("C6 Bank | Recebemos sua candidatura!", Kind.RECEIVED),
    ("Nuno, sua candidatura foi enviada à Infinite Cloud", Kind.RECEIVED),
    ("Candidatura efetuada em 025/2025 (LAB)- Estágio", Kind.RECEIVED),
    ("ERRATA: você avançou de etapa no Programa de Estágio TOTVS 2026", Kind.ADVANCED),
    ("Convocação para Assessments Localiza", Kind.ACTION),
    ("Últimas horas para confirmar sua presença! | Processo Seletivo", Kind.ACTION),
    ("Chegou o seu link de acesso!", Kind.ACTION),
    ("Visagio Talentos - Conclua as etapas online!", Kind.ACTION),
    ("Reprovação etapa de testes - Estágio Itaú 2026", Kind.ENDED),
    ("Você foi reprovado no processo", Kind.ENDED),
    ("Processo Seletivo Finalizado", Kind.ENDED),
    ("Processo seletivo encerrado", Kind.ENDED),
    ("Retorno do Processo Seletivo", Kind.UNKNOWN),
    ("Retorno - Processo Seletivo Grupo Boticário", Kind.UNKNOWN),
    ("Chegaram notícias sobre sua candidatura", Kind.UNKNOWN),
    ("Atualização sobre o processo seletivo", Kind.UNKNOWN),
    ("RE: Candidatura para Estágio FOP no The Best", Kind.UNKNOWN),
    ("Dúvidas sobre o processo seletivo? vem pro Videocast!", Kind.IRRELEVANT),
    ("Nuno, candidate-se agora à vaga de Estágio em Automação", Kind.IRRELEVANT),
    ("Estágio Em Dados na Vertem e 4 outras vagas em São Paulo", Kind.IRRELEVANT),
    ("Meetup Itaú Tech 2026 | Inscrições abertas!", Kind.IRRELEVANT),
    ("Último dia para se inscrever no Programa de Associate", Kind.IRRELEVANT),
]


@pytest.mark.parametrize(("subject", "expected"), CASES)
def test_classify_email(subject, expected):
    assert classify_email(subject) == expected