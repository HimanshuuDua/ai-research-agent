from unittest.mock import MagicMock, patch

import smtplib

from agent.config import get_email_provider, validate_outbound_recipients
from agent.email_delivery import deliver_email, verify_smtp_login


def test_smtp_provider_allows_any_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    assert get_email_provider() == "smtp"
    assert validate_outbound_recipients(["anyone@example.com", "other@test.com"]) is None


def test_brevo_provider_allows_any_recipient(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "brevo")
    assert get_email_provider() == "brevo"
    assert validate_outbound_recipients(["anyone@example.com"]) is None


@patch("agent.email_delivery._smtp_connect")
def test_deliver_email_via_smtp(mock_connect, monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app password")

    server = MagicMock()
    mock_connect.return_value = server

    result = deliver_email(["friend@example.com"], "Hello", "Test body")
    assert "friend@example.com" in result
    assert "SMTP" in result
    mock_connect.assert_called_once()
    server.sendmail.assert_called_once()
    server.quit.assert_called_once()


@patch("agent.email_delivery._smtp_connect")
def test_deliver_email_rotates_smtp_accounts(mock_connect, monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "first@gmail.com,second@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pass-one,pass-two")

    server = MagicMock()
    mock_connect.side_effect = [
        smtplib.SMTPAuthenticationError(535, b"Daily limit exceeded"),
        server,
    ]

    result = deliver_email(["friend@example.com"], "Hello", "Test body")
    assert "friend@example.com" in result
    assert mock_connect.call_count == 2
    assert mock_connect.call_args_list[1].args[2] == "second@gmail.com"


@patch("agent.email_delivery._smtp_connect")
def test_smtp_password_strips_spaces(mock_connect, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")

    server = MagicMock()
    mock_connect.return_value = server
    verify_smtp_login()

    assert mock_connect.call_args.args[3] == "abcdefghijklmnop"
