from agent.config import get_email_recipients


def test_email_recipients_single(monkeypatch):
    monkeypatch.setenv("RESEND_TO_EMAIL", "a@test.com")
    assert get_email_recipients() == ["a@test.com"]


def test_email_recipients_multiple(monkeypatch):
    monkeypatch.setenv("RESEND_TO_EMAIL", "a@test.com, b@test.com , c@test.com")
    assert get_email_recipients() == ["a@test.com", "b@test.com", "c@test.com"]
