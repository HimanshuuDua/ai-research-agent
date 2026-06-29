from agent.key_pool import get_brevo_api_keys, get_google_api_keys, get_resend_api_keys


def test_google_keys_from_multi(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEYS", "key-a, key-b")
    assert get_google_api_keys() == ["key-a", "key-b"]


def test_google_keys_fallback_single(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "single-key")
    monkeypatch.delenv("GOOGLE_API_KEYS", raising=False)
    assert get_google_api_keys() == ["single-key"]
