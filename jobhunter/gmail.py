import re
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CLIENT_FILE = Path("credentials/gmail_oauth_client.json")
TOKEN_FILE = Path("credentials/gmail_token.json")
JOB_QUERY = (
    "newer_than:60d (from:gupy OR subject:candidatura OR subject:\"processo seletivo\" "
    "OR subject:vaga OR subject:entrevista OR subject:estágio)"
)
_ADDRESS = re.compile(r"@([\w.-]+)")
_NAME = re.compile(r'^\s*"?([^"<]+?)"?\s*<')

def get_service():
    """Autoriza (abre o navegador na primeira vez) e devolve o cliente do Gmail."""
    if not CLIENT_FILE.exists():
        raise FileNotFoundError(
            f"Credenciais OAuth não encontradas em '{CLIENT_FILE.resolve()}'. "
            "Baixe o JSON do Google Cloud e salve com esse nome."
        )
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None  # autorização expirada ou revogada: pede de novo
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def sender_domain(from_header: str) -> str:
    match = _ADDRESS.search(from_header)
    return match.group(1).lower() if match else ""

def sender_name(from_header: str) -> str:
    match = _NAME.match(from_header)
    return match.group(1).strip() if match else ""

def recent_headers(service, query: str = JOB_QUERY, max_results: int = 60) -> list[dict]:
    """Só cabeçalhos (remetente, assunto, data): o corpo dos e-mails nunca é lido."""
    listing = (
        service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    )
    results = []
    for item in listing.get("messages", []):
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = {
            h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])
        }
        results.append({
            "id": item["id"],
            "thread": item.get("threadId", ""),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "snippet": message.get("snippet", ""),
        })
    return results