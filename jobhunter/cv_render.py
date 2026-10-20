from jinja2 import Template

from jobhunter.cv import MAX_EXPERIENCE_BULLETS, MAX_PROJECT_BULLETS, Cv, pick_bullets

CSS = """
@page { size: A4; margin: 14mm 16mm; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.35;
       color: #111; }
h1 { font-size: 20pt; margin: 0; text-align: center; letter-spacing: 1px; }
.title, .contacts { text-align: center; margin: 2px 0; }
.contacts { font-size: 9pt; color: #333; }
h2 { font-size: 10.5pt; text-transform: uppercase; border-bottom: 1px solid #333;
     margin: 12px 0 6px; padding-bottom: 2px; }
.entry { margin-bottom: 7px; break-inside: avoid; }
.row { display: flex; justify-content: space-between; }
.role { font-style: italic; }
.muted { color: #444; font-size: 9pt; }
ul { margin: 3px 0 0; padding-left: 16px; }
li { margin-bottom: 2px; }
p { margin: 4px 0; }
.skills { margin: 2px 0; }
"""

TEMPLATE = Template(
    """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{{ cv.name }} - Currículo</title>
<style>{{ css|safe }}</style>
</head>
<body>
<h1>{{ cv.name }}</h1>
<p class="title">{{ cv.title }}</p>
<p class="contacts">{{ cv.contacts|join(" • ") }}</p>

<h2>Resumo profissional</h2>
<p>{{ summary }}</p>

<h2>Experiência profissional</h2>
{% for exp, bullets in experience %}
<div class="entry">
  <div class="row"><b>{{ exp.company }}</b><span>{{ exp.period }}</span></div>
  <div class="role">{{ exp.role }}</div>
  <ul>{% for b in bullets %}<li>{{ b.text }}</li>{% endfor %}</ul>
</div>
{% endfor %}

<h2>Projetos</h2>
{% for project, bullets in projects %}
<div class="entry">
  <div>
    <b>{{ project.name }}</b>
    {% if project.subtitle %} – {{ project.subtitle }}{% endif %}
  </div>
  {% if project.links %}<div class="muted">{{ project.links|join(" • ") }}</div>{% endif %}
  <ul>{% for b in bullets %}<li>{{ b.text }}</li>{% endfor %}</ul>
</div>
{% endfor %}

<h2>Formação e certificações</h2>
<div class="row"><b>{{ cv.education.course }}</b><span>{{ cv.education.period }}</span></div>
<div class="role">{{ cv.education.school }}</div>
{% for cert in cv.education.certifications %}<div>Certificação: {{ cert }}</div>{% endfor %}

<h2>Conhecimentos</h2>
{% for category, items in cv.skills.items() %}
<p class="skills"><b>{{ category }}:</b> {{ items|join(" | ") }}</p>
{% endfor %}
</body>
</html>""",
    autoescape=True,
)


def render_html(
    cv: Cv, summary: str | None = None, preferred_ids: list[str] | None = None
) -> str:
    preferred = preferred_ids or []
    experience = [
        (item, pick_bullets(item.bullets, preferred, MAX_EXPERIENCE_BULLETS))
        for item in cv.experience
    ]
    projects = [
        (item, pick_bullets(item.bullets, preferred, MAX_PROJECT_BULLETS))
        for item in cv.projects
    ]
    return TEMPLATE.render(
        cv=cv, css=CSS, summary=summary or cv.summary, experience=experience, projects=projects
    )