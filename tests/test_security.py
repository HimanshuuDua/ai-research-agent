from agent.security import sanitize_assistant_output


def test_redacts_google_api_key():
    text = "Your key is AIzaSyDfakeKeyForTestingPurposesOnly123456"
    result = sanitize_assistant_output(text)
    assert "AIzaSy" not in result
    assert "[redacted]" in result


def test_refuses_credential_dump():
    text = "smtp_password=secret123 and google_api_key=abc"
    result = sanitize_assistant_output(text)
    assert "secret123" not in result.lower() or "can't share" in result.lower()
