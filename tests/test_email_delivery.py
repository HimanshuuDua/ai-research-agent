from unittest.mock import MagicMock, patch

from agent.config import get_email_provider, validate_outbound_recipients
from agent.email_delivery import deliver_email


def test_smtp_provider_allows_any_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    assert get_email_provider() == "smtp"
    assert validate_outbound_recipients(["anyone@example.com", "other@test.com"]) is None


@patch("agent.email_delivery.smtplib.SMTP")
def test_deliver_email_via_smtp(mock_smtp, monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")

    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server

    result = deliver_email(["friend@example.com"], "Hello", "Test body")
    assert "friend@example.com" in result
    assert "SMTP" in result
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("sender@gmail.com", "app-password")
    server.sendmail.assert_called_once()
