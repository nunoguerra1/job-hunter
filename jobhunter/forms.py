import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Page

FORMS_DIR = Path("data/forms")

# Lê só a ESTRUTURA da página (rótulos, tipos, opções, botões), nunca os valores digitados.
FIELDS_JS = """
() => {
  const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const labelFor = el => {
    if (el.labels && el.labels.length) return el.labels[0].innerText.trim();
    const aria = el.getAttribute('aria-label');
    if (aria) return aria.trim();
    const by = el.getAttribute('aria-labelledby');
    if (by) { const n = document.getElementById(by); if (n) return n.innerText.trim(); }
    const wrap = el.closest('label');
    if (wrap) return wrap.innerText.trim();
    return (el.placeholder || '').trim();
  };
  const fields = [...document.querySelectorAll('input, textarea, select')]
    .filter(el => el.type !== 'hidden' && visible(el))
    .map(el => ({
      tag: el.tagName.toLowerCase(),
      type: el.type || '',
      name: el.name || '',
      id: el.id || '',
      label: labelFor(el).slice(0, 200),
      required: el.required || el.getAttribute('aria-required') === 'true',
      options: el.tagName === 'SELECT'
        ? [...el.options].map(o => o.text.trim()).slice(0, 30) : []
    }));
  const buttons = [...document.querySelectorAll('button, a[role=button], [type=submit]')]
    .filter(visible)
    .map(b => (b.innerText || b.value || '').trim())
    .filter(Boolean)
    .slice(0, 30);
  return {url: location.href, title: document.title, fields, buttons};
}
"""


def sanitize_url(url: str) -> str:
    """Remove query string e fragmento, que podem carregar tokens."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def snapshot_path(uid: str, step: int, folder: Path = FORMS_DIR) -> Path:
    return folder / f"{uid.replace(':', '_')}_{step}.json"


def capture(page: Page) -> dict:
    data = page.evaluate(FIELDS_JS)
    data["url"] = sanitize_url(data["url"])
    return data


def save_snapshot(data: dict, uid: str, step: int, folder: Path = FORMS_DIR) -> Path:
    path = snapshot_path(uid, step, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path