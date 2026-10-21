from jobhunter.answers import Answers, Rule, load_answers, plan_question, plan_step

VENDEMMIA = [
    {"key": "question-6340611", "kind": "single",
     "question": "Qual é a sua escolaridade atual?",
     "options": ["Ensino médio completo", "Ensino superior cursando",
                 "Ensino superior completo"]},
    {"key": "checkbox-6340612", "kind": "multi",
     "question": "Qual seu nível de conhecimento com: Python, SQL e Javascript?",
     "options": ["Básico", "Intermediário", "Avançado",
                 "Ainda não tenho conhecimento ou nunca trabalhei"]},
    {"key": "question-6340613", "kind": "single",
     "question": ("Você já desenvolveu projetos envolvendo Inteligência Artificial "
                  "generativa ou integração com APIs de IA?"),
     "options": ["Sim", "Não"]},
    {"key": "question-6340615", "kind": "single",
     "question": ("Você está estudando ou já concluiu curso superior? (para essa posição, "
                  "será necessário comprovação de estudo ou conclusão)"),
     "options": ["Sim", "Não"]},
    {"key": "question-6340616", "kind": "single",
     "question": ("Essa oportunidade é para atuar no bairro da Vila Olímpia - SP. "
                  "Você tem fácil acesso a região?"),
     "options": ["Sim", "Não"]},
    {"key": "pacote", "kind": "text",
     "question": ("Por favor, nos passe seu pacote atual de remuneração e benefícios "
                  "(informar se é CLT), e qual a sua pretensão salarial (CLT):"),
     "options": []},
]


def test_example_rules_fill_only_what_is_safe():
    answers = load_answers("profile/answers.example.yaml")
    plans = plan_step(VENDEMMIA, answers, {})

    assert [p.action for p in plans] == ["fill", "human", "human", "fill", "human", "human"]
    assert plans[0].values == ["Ensino superior cursando"]
    assert plans[3].values == ["Sim"]


def test_sensitive_question_needs_force():
    question = VENDEMMIA[4]
    soft = Answers(rules=[Rule(when=["acesso"], choose=["Sim"])])
    forced = Answers(rules=[Rule(when=["acesso"], choose=["Sim"], force=True)])

    assert plan_question(question, soft, {}).action == "human"
    assert plan_question(question, forced, {}).action == "fill"


def test_text_rule_uses_draft_placeholders():
    question = {"key": "k", "kind": "text",
                "question": "Por que você quer trabalhar conosco?", "options": []}
    answers = load_answers("profile/answers.example.yaml")

    assert plan_question(question, answers, {"why_us": "meu texto"}).values == ["meu texto"]
    assert plan_question(question, answers, {}).action == "human"


def test_unknown_option_falls_back_to_human():
    answers = Answers(rules=[Rule(when=["escolaridade"], choose=["Doutorado"])])
    plan = plan_question(VENDEMMIA[0], answers, {})

    assert plan.action == "human"
    assert "Doutorado" in plan.reason


def test_ask_rule_always_defers_to_user():
    answers = Answers(rules=[Rule(when=["escolaridade"], choose=["Ensino superior cursando"],
                                  ask=True)])

    assert plan_question(VENDEMMIA[0], answers, {}).action == "human"