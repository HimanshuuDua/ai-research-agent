from agent.key_pool import get_brevo_api_keys, get_google_api_keys, get_resend_api_keys, get_smtp_accounts


def test_google_keys_from_multi(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEYS", "key-a, key-b")
    assert get_google_api_keys() == ["key-a", "key-b"]


def test_google_keys_fallback_single(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "single-key")
    monkeypatch.delenv("GOOGLE_API_KEYS", raising=False)
    assert get_google_api_keys() == ["single-key"]


def test_google_keys_split_comma_in_single_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEYS", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "key-a,key-b,key-c")
    assert get_google_api_keys() == ["key-a", "key-b", "key-c"]


def test_brevo_keys_split_comma_in_single_env(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEYS", raising=False)
    monkeypatch.setenv("BREVO_API_KEY", "brevo-a,brevo-b")
    assert get_brevo_api_keys() == ["brevo-a", "brevo-b"]


def test_smtp_multi_accounts_from_comma_lists(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "a@gmail.com,b@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pass-one,pass-two")
    monkeypatch.setenv("SMTP_FROM", "Agent A <a@gmail.com>,Agent B <b@gmail.com>")
    accounts = get_smtp_accounts()
    assert len(accounts) == 2
    assert accounts[0]["user"] == "a@gmail.com"
    assert accounts[1]["password"] == "pass-two"
