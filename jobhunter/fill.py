from dataclasses import dataclass, field

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from jobhunter.answers import Plan

# Este módulo NUNCA clica em "Salvar e continuar" nem em enviar: só marca opções e escreve texto.
CHOOSE_JS = r"""
({key, kind, wanted}) => {
  const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const labelOf = el => {
    if (el.labels && el.labels.length) return el.labels[0].innerText;
    const wrap = el.closest('label');
    return wrap ? wrap.innerText : (el.getAttribute('aria-label') || '');
  };
  const inputs = kind === 'multi'
    ? [...document.querySelectorAll('input[type=checkbox]')]
        .filter(el => el.name.startsWith(key + '-'))
    : [...document.getElementsByName(key)];
  const target = inputs.find(el => norm(labelOf(el)) === norm(wanted));
  if (!target) return false;
  if (!target.checked) target.click();
  return target.checked;
}
"""

TAG_TEXT_JS = r"""
({key}) => {
  const el = [...document.getElementsByName(key)]
    .find(e => ['TEXTAREA', 'INPUT', 'SELECT'].includes(e.tagName));
  if (!el) return false;
  document.querySelectorAll('[data-jh-target]').forEach(n => n.removeAttribute('data-jh-target'));
  el.setAttribute('data-jh-target', '1');
  return true;
}
"""

HIGHLIGHT_JS = r"""
({key, kind}) => {
  const els = kind === 'multi'
    ? [...document.querySelectorAll('input[type=checkbox]')]
        .filter(el => el.name.startsWith(key + '-'))
    : [...document.getElementsByName(key)];
  els.forEach(el => {
    const box = el.closest('label') || el.parentElement;
    box.style.outline = '3px solid #e11d48';
    box.style.outlineOffset = '2px';
  });
  if (els.length) els[0].scrollIntoView({block: 'center'});
  return els.length > 0;
}
"""

BANNER_JS = r"""
(message) => {
  let banner = document.getElementById('jh-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'jh-banner';
    banner.style.cssText = 'position:fixed;top:8px;right:8px;z-index:99999;background:#111;'
      + 'color:#fff;padding:10px 14px;border-radius:8px;font:13px Arial;max-width:340px;'
      + 'box-shadow:0 2px 8px rgba(0,0,0,.4)';
    document.body.appendChild(banner);
  }
  banner.textContent = message;
}
"""


@dataclass
class FillResult:
    filled: list[Plan] = field(default_factory=list)
    pending: list[Plan] = field(default_factory=list)  # sem regra ou sensível: com você
    failed: list[Plan] = field(default_factory=list)  # tinha regra, mas o campo não foi achado


def _fill(page: Page, plan: Plan) -> bool:
    try:
        if plan.kind in {"single", "multi"}:
            return all(
                page.evaluate(CHOOSE_JS, {"key": plan.key, "kind": plan.kind, "wanted": value})
                for value in plan.values
            )
        if not page.evaluate(TAG_TEXT_JS, {"key": plan.key}):
            return False
        target = page.locator('[data-jh-target="1"]')
        if plan.kind == "select":
            target.select_option(label=plan.values[0])
        else:
            target.fill(plan.values[0])
        return True
    except PlaywrightError:
        return False


def fill_step(page: Page, plans: list[Plan]) -> FillResult:
    result = FillResult()
    for plan in plans:
        if plan.action != "fill":
            result.pending.append(plan)
        elif _fill(page, plan):
            result.filled.append(plan)
        else:
            result.failed.append(plan)
    for plan in [*result.pending, *result.failed]:
        page.evaluate(HIGHLIGHT_JS, {"key": plan.key, "kind": plan.kind})
    mine = len(result.pending) + len(result.failed)
    page.evaluate(
        BANNER_JS,
        f"Preenchi {len(result.filled)} campo(s). {mine} em vermelho são com você. "
        "Depois clique você mesmo em 'Salvar e continuar'.",
    )
    return result