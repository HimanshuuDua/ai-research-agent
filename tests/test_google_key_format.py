from agent.config import get_google_key_warnings, is_valid_google_ai_studio_key


def test_valid_ai_studio_key():
    assert is_valid_google_ai_studio_key("AIzaSyDfakeKeyForTestingPurposesOnly123456")


def test_valid_auth_key():
    assert is_valid_google_ai_studio_key("AQ." + "FakeAuthKeyForTestingPurposesOnly1234567890")


def test_rejects_garbage_key():
    assert not is_valid_google_ai_studio_key("not-a-real-key")


def test_google_key_format_warning(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "garbage-one,garbage-two")
    warnings = get_google_key_warnings()
    assert len(warnings) == 1
    assert warnings[0]["code"] == "invalid_google_api_key_format"
