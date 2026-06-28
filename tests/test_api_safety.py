import pytest
from fastapi.testclient import TestClient

from api.index import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google")
    monkeypatch.setenv("SERPAPI_API_KEY", "test-serp")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("RESEND_TO_EMAIL", "receiver@gmail.com")
    return TestClient(app)


def test_health_includes_config_warnings(client, monkeypatch):
    monkeypatch.setenv("RESEND_TO_EMAIL", "smtp")
    response = client.get("/api/health")
    assert response.status_code == 503


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


def test_upload_rejects_missing_filename(client):
    response = client.post(
        "/api/upload",
        files={"file": ("", b"hello", "text/plain")},
    )
    assert response.status_code in {400, 422}
