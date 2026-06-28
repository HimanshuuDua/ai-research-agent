from agent.config import (
    get_email_recipients,
    is_resend_test_mode,
    validate_outbound_recipients,
)


def test_email_recipients_single(monkeypatch):
    monkeypatch.setenv("RESEND_TO_EMAIL", "a@test.com")
    assert get_email_recipients() == ["a@test.com"]


def test_email_recipients_multiple(monkeypatch):
    monkeypatch.setenv("RESEND_TO_EMAIL", "a@test.com, b@test.com , c@test.com")
    assert get_email_recipients() == ["a@test.com", "b@test.com", "c@test.com"]


def test_test_mode_blocks_other_recipients(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    monkeypatch.setenv("RESEND_ACCOUNT_EMAIL", "owner@test.com")
    error = validate_outbound_recipients(["owner@test.com", "other@test.com"])
    assert error is not None
    assert "other@test.com" in error


def test_production_mode_allows_any_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "AI Agent <notify@mydomain.com>")
    assert is_resend_test_mode() is False
    assert validate_outbound_recipients(["anyone@test.com"]) is None


def test_smtp_mode_allows_any_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    assert validate_outbound_recipients(["anyone@test.com", "other@test.com"]) is None


def test_invalid_recipient_blocked(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    error = validate_outbound_recipients(["not-an-email"])
    assert error and "Invalid email" in error

