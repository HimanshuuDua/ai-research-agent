from agent.config import get_google_key_warnings, is_valid_google_ai_studio_key


def test_valid_ai_studio_key():
    assert is_valid_google_ai_studio_key("AIzaSyDfakeKeyForTestingPurposesOnly123456")


def test_rejects_oauth_style_key():
    assert not is_valid_google_ai_studio_key("AQ.Ab8RN6KBBUQ5l2iYIV9ubOqZ76yXi4W1A")


def test_google_key_format_warning(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "AQ.token-one,AQ.token-two")
    warnings = get_google_key_warnings()
    assert len(warnings) == 1
    assert warnings[0]["code"] == "invalid_google_api_key_format"
    assert "AIza" in warnings[0]["message"]
