from jobhunter.snap import redact


def test_redact_masks_contacts_and_names():
    text = "Olá, Nuno Guerra! nuno@gmail.com (18) 99696-4920 CPF 123.456.789-09"

    out = redact(text, ["Nuno", "Guerra"])

    assert "Nuno" not in out
    assert "Guerra" not in out
    assert "gmail" not in out
    assert "99696" not in out
    assert "123.456" not in out
    assert "[telefone]" in out


def test_redact_keeps_ordinary_text():
    assert redact("Etapa 2 de 4", ["Nuno"]) == "Etapa 2 de 4"

def test_redact_masks_phone_without_area_code():
    assert redact("Ligue 99696-4920 hoje", []) == "Ligue [telefone] hoje"


def test_redact_keeps_application_and_job_ids():
    text = "Ver andamento da candidatura769354813 vaga 12542291"

    assert redact(text, []) == text