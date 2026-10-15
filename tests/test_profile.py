from jobhunter.models import Modality
from jobhunter.profile import load_profile


def test_example_profile_is_valid():
    profile = load_profile("profile/profile.example.yaml")
    assert profile.areas[0].name == "desenvolvimento"
    assert Modality.REMOTE in profile.modalities
    assert "suporte" in profile.excluded_title_keywords