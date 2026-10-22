from enum import StrEnum

from jobhunter.filters import normalize


class Kind(StrEnum):
    RECEIVED = "recebida"
    ADVANCED = "avançou"
    ACTION = "ação necessária"
    ENDED = "encerrada"
    UNKNOWN = "verificar"
    IRRELEVANT = "irrelevante"


# Lista de permissão: só é candidatura o que bate com um destes padrões (sem acento e minúsculo).
# A ordem importa: o primeiro tipo que combinar vence.
_RULES: list[tuple[Kind, tuple[str, ...]]] = [
    (Kind.ENDED, (
        "reprovac", "reprovad", "processo seletivo finalizado", "processo seletivo encerrado",
        "nao seguiremos", "nao foi selecionad",
    )),
    (Kind.ADVANCED, ("voce avancou", "avancou de etapa", "aprovad", "parabens")),
    (Kind.ACTION, (
        "convocacao", "assessment", "link de acesso", "conclua as etapas",
        "confirmar sua presenca", "confirme sua presenca", "entrevista", "agende",
    )),
    (Kind.RECEIVED, (
        "inscricao recebida", "candidatura recebida", "recebemos sua candidatura",
        "candidatura efetuada", "candidatura foi enviada", "candidatura enviada",
    )),
    (Kind.UNKNOWN, (
        "retorno do processo seletivo", "retorno - processo seletivo", "chegaram noticias",
        "atualizacao sobre o processo seletivo", "candidatura para",
    )),
]


def classify_email(subject: str) -> Kind:
    text = normalize(subject)
    for kind, terms in _RULES:
        if any(term in text for term in terms):
            return kind
    return Kind.IRRELEVANT