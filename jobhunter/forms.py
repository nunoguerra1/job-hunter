import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Error as PlaywrightError
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
  const inputs = [...document.querySelectorAll('input, textarea, select')]
    .filter(el => el.type !== 'hidden' && visible(el));
  const keyOf = el => (el.type === 'checkbox' ? el.name.replace(/-\\d+$/, '') : el.name)
    || el.id || ('idx' + inputs.indexOf(el));

  const commonAncestor = els => {
    let node = els[0].parentElement;
    while (node && !els.every(e => node.contains(e))) node = node.parentElement;
    return node;
  };
  const otherInputs = (node, key) =>
    inputs.filter(i => node.contains(i) && keyOf(i) !== key).length;
  // Sobe do grupo de opções até o bloco que contém SÓ essa pergunta (o enunciado fica nele).
  const blockOf = (els, key) => {
    let node = commonAncestor(els);
    while (node && node.parentElement && node.parentElement !== document.body
           && otherInputs(node.parentElement, key) === 0
           && node.parentElement.innerText.length < 700) {
      node = node.parentElement;
    }
    return node;
  };
  const onlyLabels = (line, labels) => {
    const sorted = labels.filter(Boolean).sort((a, b) => b.length - a.length);
    let rest = line;
    let progressed = true;
    while (rest && progressed) {
      progressed = false;
      for (const label of sorted) {
        if (rest.startsWith(label)) {
          rest = rest.slice(label.length).trim();
          progressed = true;
          break;
        }
      }
    }
    return rest === '';
  };
  const questionText = (els, key, labels) => {
    const block = blockOf(els, key);
    const lines = (block ? block.innerText : '').split('\\n').map(s => s.trim())
      .filter(Boolean).filter(line => !onlyLabels(line, labels));
    return lines.slice(0, 3).join(' | ').slice(0, 400);
  };
  const isRequired = els =>
    els.some(e => e.required || e.getAttribute('aria-required') === 'true');

  const fields = inputs.map(el => ({
    tag: el.tagName.toLowerCase(),
    type: el.type || '',
    name: el.name || '',
    id: el.id || '',
    label: labelFor(el).slice(0, 200),
    required: isRequired([el]),
    options: el.tagName === 'SELECT'
      ? [...el.options].map(o => o.text.trim()).slice(0, 30) : []
  }));

  const groups = new Map();
  inputs.filter(el => el.type === 'radio' || el.type === 'checkbox').forEach(el => {
    const key = keyOf(el);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(el);
  });
  const questions = [...groups.entries()].map(([key, els]) => {
    const labels = els.map(labelFor);
    return {
      key,
      kind: els[0].type === 'radio' ? 'single' : 'multi',
      question: questionText(els, key, labels),
      options: labels,
      required: isRequired(els)
    };
  });
  inputs.filter(el => !['radio', 'checkbox', 'file', 'button', 'submit'].includes(el.type))
    .forEach(el => {
      const key = keyOf(el);
      const label = labelFor(el);
      const named = el.name && el.name.length > 25 ? el.name : '';
      questions.push({
        key,
        kind: el.tagName === 'SELECT' ? 'select' : 'text',
        question: named || questionText([el], key, [label]),
        options: el.tagName === 'SELECT'
          ? [...el.options].map(o => o.text.trim()).slice(0, 30) : [],
        required: isRequired([el])
      });
    });

  const buttons = [...document.querySelectorAll('button, a[role=button], [type=submit]')]
    .filter(visible)
    .map(b => (b.innerText || b.value || '').trim())
    .filter(Boolean)
    .slice(0, 30);
  return {url: location.href, title: document.title, fields, questions, buttons};
}
"""


def sanitize_url(url: str) -> str:
    """Remove query string e fragmento, que podem carregar tokens."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def snapshot_path(uid: str, step: int, folder: Path = FORMS_DIR) -> Path:
    return folder / f"{uid.replace(':', '_')}_{step}.json"

_NUMBER = re.compile(r"^\s*(\d+)\s*[.)\-]\s*")

def clean_question(raw: str) -> tuple[str, int | None, bool]:
    """Separa a numeração ('1.') e o marcador de obrigatória ('*') do enunciado."""
    text = raw.strip()
    required = text.endswith("*")
    text = text.rstrip("*").strip()
    match = _NUMBER.match(text)
    number = int(match.group(1)) if match else None
    if match:
        text = text[match.end() :].strip()
    return text, number, required


def normalize_questions(questions: list[dict]) -> list[dict]:
    for item in questions:
        text, number, starred = clean_question(item["question"])
        item["raw"] = item["question"]
        item["question"] = text
        item["number"] = number
        item["required"] = bool(item.get("required")) or starred
    return questions

def capture(page: Page, attempts: int = 6) -> dict:
    """Captura a estrutura da página, esperando uma navegação em andamento terminar."""
    last_error: PlaywrightError | None = None
    for _ in range(attempts):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(800)  # deixa a tela montar (a Gupy renderiza no navegador)
            data = page.evaluate(FIELDS_JS)
        except PlaywrightError as error:
            last_error = error
            page.wait_for_timeout(1500)
            continue
        data["url"] = sanitize_url(data["url"])
        normalize_questions(data.get("questions", []))
        return data
    raise last_error or RuntimeError("falha ao capturar a página")


def save_snapshot(data: dict, uid: str, step: int, folder: Path = FORMS_DIR) -> Path:
    path = snapshot_path(uid, step, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path