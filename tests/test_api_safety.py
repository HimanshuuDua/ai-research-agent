import pytest
from fastapi.testclient import TestClient

from api.index import app, merge_recipients_from_prompt


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google")
    monkeypatch.setenv("SERPAPI_API_KEY", "test-serp")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("RESEND_TO_EMAIL", "receiver@gmail.com")
    return TestClient(app)


def test_health_ok_without_public_emails(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "email_recipients" not in data
    assert data["gemini_key_count"] >= 1
    assert "gemini_rotation_ready" in data
    assert "email_account_count" in data
    assert "email_rotation_ready" in data


def test_session_history_empty(client):
    response = client.get("/api/session/history")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert "session_key" in data


def test_chat_requires_email_in_full_mode(client):
    response = client.post(
        "/api/chat",
        json={"prompt": "email me a summary", "mode": "full", "email_recipients": ""},
    )
    assert response.status_code == 400
    assert "email" in response.json()["detail"]["error"].lower()


def test_chat_rejects_invalid_mode(client):
    response = client.post("/api/chat", json={"prompt": "hello", "mode": "invalid"})
    assert response.status_code == 400


def test_chat_rejects_invalid_recipient(client):
    response = client.post(
        "/api/chat",
        json={"prompt": "hello", "mode": "search_only", "email_recipients": "not-an-email"},
    )
    assert response.status_code == 400
    assert "Invalid email" in response.json()["detail"]["error"]


def test_chat_rejects_oversized_prompt(client):
    response = client.post(
        "/api/chat",
        json={"prompt": "x" * 9000, "mode": "search_only"},
    )
    assert response.status_code == 422


def test_merge_recipients_from_prompt():
    merged = merge_recipients_from_prompt(
        "Email the summary to himanshuudua@gmail.com please",
        ["spammaker81@gmail.com"],
    )
    assert "spammaker81@gmail.com" in merged
    assert "himanshuudua@gmail.com" in merged


def test_upload_rejects_missing_filename(client):
    response = client.post(
        "/api/upload",
        files={"file": ("", b"hello", "text/plain")},
    )
    assert response.status_code in {400, 422}
