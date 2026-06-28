from agent.config import get_email_config_warnings, get_valid_email_recipients, is_valid_email


def test_is_valid_email():
    assert is_valid_email("user@example.com")
    assert not is_valid_email("smtp")
    assert not is_valid_email("bad@")


def test_invalid_resend_to_email_warning(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    monkeypatch.setenv("RESEND_TO_EMAIL", "smtp")
    warnings = get_email_config_warnings()
    assert any(w["code"] == "invalid_recipients" for w in warnings)
    assert get_valid_email_recipients() == []


def test_smtp_missing_password_warning(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "you@gmail.com")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setenv("RESEND_TO_EMAIL", "you@gmail.com")
    warnings = get_email_config_warnings()
    assert any(w["code"] == "smtp_missing_password" for w in warnings)
