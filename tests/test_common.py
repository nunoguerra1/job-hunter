from jobhunter.collectors.common import accepts_location, is_entry_level, modality_from_text
from jobhunter.models import Modality


def test_accepts_only_brazil_friendly_locations():
    assert accepts_location("Remote - Brazil")
    assert accepts_location("LATAM")
    assert accepts_location("Anywhere")
    assert accepts_location("Worldwide")
    assert not accepts_location("Remote - US")
    assert not accepts_location("")


def test_modality_from_text():
    assert modality_from_text("Remote - Brazil") == Modality.REMOTE
    assert modality_from_text("Híbrido em São Paulo") == Modality.HYBRID
    assert modality_from_text("São Paulo, SP") == Modality.UNKNOWN


def test_is_entry_level_by_title():
    assert is_entry_level("Software Engineer Intern")
    assert is_entry_level("Desenvolvedor Júnior")
    assert not is_entry_level("Senior Engineer")