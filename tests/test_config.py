from agent.config import get_missing_env_keys


def test_missing_env_keys_resend_when_empty(monkeypatch):
    monkeypatch.delenv("EMAIL_PROVIDER", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    for key in [
        "GOOGLE_API_KEY",
        "SERPAPI_API_KEY",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
        "RESEND_TO_EMAIL",
    ]:
        monkeypatch.delenv(key, raising=False)
    assert len(get_missing_env_keys()) == 5


def test_missing_env_keys_smtp_when_empty(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    for key in [
        "GOOGLE_API_KEY",
        "SERPAPI_API_KEY",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "RESEND_TO_EMAIL",
    ]:
        monkeypatch.delenv(key, raising=False)
    assert len(get_missing_env_keys()) == 5


def test_missing_env_keys_smtp_when_set(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("SMTP_USER", "you@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("RESEND_TO_EMAIL", "friend@example.com")
    assert get_missing_env_keys() == []


def test_missing_env_keys_resend_when_set(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("RESEND_API_KEY", "test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "from@test.com")
    monkeypatch.setenv("RESEND_TO_EMAIL", "to@test.com")
    assert get_missing_env_keys() == []
