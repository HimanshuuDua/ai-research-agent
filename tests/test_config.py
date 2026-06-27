from agent.config import get_missing_env_keys


def test_missing_env_keys_when_empty(monkeypatch):
    for key in [
        "GOOGLE_API_KEY",
        "SERPAPI_API_KEY",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
        "RESEND_TO_EMAIL",
    ]:
        monkeypatch.delenv(key, raising=False)
    assert len(get_missing_env_keys()) == 5


def test_missing_env_keys_when_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("RESEND_API_KEY", "test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "from@test.com")
    monkeypatch.setenv("RESEND_TO_EMAIL", "to@test.com")
    assert get_missing_env_keys() == []
