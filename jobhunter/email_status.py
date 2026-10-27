import re
from enum import StrEnum

from jobhunter.filters import normalize


class Kind(StrEnum):
    RECEIVED = "recebida"
    ADVANCED = "avançou"
    ACTION = "ação necessária"
    MESSAGE = "mensagem do recrutador"
    REJECTED = "reprovada"
    ENDED = "encerrada"
    SENT = "enviada por e-mail"
    UNKNOWN = "verificar"
    IRRELEVANT = "irrelevante"


# Remetentes de propaganda e alertas: ignorados mesmo que o assunto pareça de candidatura.
IGNORED_DOMAINS = (
    "dio.me", "eureca.me", "infojobs.com.br", "glassdoor.com", "indeed.com",
    "ciadetalentos.com", "jobbol",
)
PLATFORMS = ("gupy", "linkedin", "greenhouse", "solides", "abler", "indeed", "glassdoor")

# Lista de permissão: só é candidatura o que bate com um destes padrões (sem acento, minúsculo).
# A ordem importa: o primeiro tipo que combinar vence.
_RULES: list[tuple[Kind, tuple[str, ...]]] = [
    (Kind.REJECTED, ("reprovac", "reprovad", "nao seguiremos", "nao foi selecionad")),
    (Kind.ENDED, ("processo seletivo finalizado", "processo seletivo encerrado")),
    (Kind.ADVANCED, ("voce avancou", "avancou de etapa", "aprovad", "parabens")),
    (Kind.ACTION, (
        "convocacao", "assessment", "conclua as etapas", "confirmar sua presenca",
        "confirme sua presenca", "convite para entrevista", "entrevista agendada", "agende",
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

_ADDRESS = re.compile(r"([\w.+-]+@[\w.-]+)")
_GUPY_MESSAGE = re.compile(r"^(.+?)\s+-\s+.+?Nova mensagem referente", re.IGNORECASE)
_SENT_TO = re.compile(r"candidatura foi enviada (?:à|a|ao|para)\s+(.+?)\s*$", re.IGNORECASE)


def address_of(from_header: str) -> str:
    match = _ADDRESS.search(from_header)
    return match.group(1).lower() if match else ""


def _ignored(domain: str) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in IGNORED_DOMAINS)


def _refine(snippet: str) -> Kind:
    """Assuntos genéricos: o trecho do e-mail decide o que ele realmente é."""
    text = normalize(snippet)
    if "nova mensagem referente" in text:
        return Kind.MESSAGE
    if any(t in text for t in ("infelizmente", "seguiremos com outros", "outros candidatos")):
        return Kind.REJECTED
    if any(t in text for t in ("recebemos seu curriculo", "recebemos sua candidatura")):
        return Kind.RECEIVED
    return Kind.UNKNOWN


def classify_email(
    subject: str, snippet: str = "", from_header: str = "", my_address: str = ""
) -> Kind:
    address = address_of(from_header)
    if _ignored(address.split("@")[-1]):
        return Kind.IRRELEVANT
    text = normalize(subject)
    if my_address and address == my_address.lower():
        return Kind.SENT if "candidatura" in text else Kind.IRRELEVANT
    for kind, terms in _RULES:
        if any(term in text for term in terms):
            return _refine(snippet) if kind is Kind.UNKNOWN else kind
    return Kind.IRRELEVANT


def guess_company(sender_name: str, sender_domain: str, subject: str, snippet: str) -> str:
    """Empresa estimada (pode errar): trecho da Gupy, assunto ou nome do remetente."""
    match = _GUPY_MESSAGE.match(snippet.strip())
    if match:
        return match.group(1).strip()
    if "greenhouse" in normalize(sender_domain) and "|" in subject:
        return subject.split("|")[0].strip()
    sent = _SENT_TO.search(subject)
    if sent:
        return sent.group(1).strip()
    if any(p in normalize(sender_name) for p in PLATFORMS):
        return ""  # o remetente é a própria plataforma (Gupy, LinkedIn...): não diz a empresa
    if sender_name:
        return sender_name  # a plataforma envia em nome da empresa: o nome é a empresa
    return "" if any(p in normalize(sender_domain) for p in PLATFORMS) else sender_domain